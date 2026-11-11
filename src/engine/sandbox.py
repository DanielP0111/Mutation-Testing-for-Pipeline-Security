"""
src/engine/sandbox.py

Per-phase isolation sandbox: an ENFORCING defense, unlike Foreman (which runs
the whole build in one container and only warns). Our own design; not
PipelineSave's sandbox.

Each step.sh phase (fetch, setup, compile, test) runs in its own container
(harness/sandbox_phase.sh): --network none, a private /tmp discarded after the
phase, no capabilities, and the build step running as an unprivileged user
for whom /src is read-only except build/ and the paths the policy lets that
phase write. The policy is learned from a clean build run in LEARN mode (all
of /src writable, every write recorded per phase).

Outcomes for a mutant whose plain harness run was effective
(sandbox_outcome()):

    prevented    the declared effect never showed up, not even inside the phase
                 (the payload could not run, or failed, e.g. a write was denied)
    confined     the effect showed up INSIDE a phase but did not outlive it
                 (e.g. op_005 writes /tmp/PWNED_*: the payload ran, and the
                 marker was discarded with the phase's /tmp)
    not_blocked  the effect escaped the phase and the oracle saw it

"blocked" = prevented or confined, i.e. the declared effect is not observed by
the oracle outside the phase. Confined is NOT prevention: the payload ran and
could read whatever its phase could (source, the canary in its environment).
Report the two separately.

Network: the attacker server is outside the sandbox, so with no network a
request cannot escape. The mock server still runs inside every phase (on
loopback) so we can see the attempt, but only phases listed in
network_phases count its requests as escaped. Default: none (all phases
--network none, as in the plain harness).

Known gap: build/ is shared between phases by design, so a payload that hides
state in build/ (e.g. write in setup, read in compile) gets through.
"""
from __future__ import annotations

import json
import subprocess
import uuid
from pathlib import Path

from src.engine.harness_runner import (DEFAULT_IMAGE, DEFAULT_TESTS, DOCKER_INFRA_RCS,
                                       HARNESS_DIR, HarnessUnavailable, load_run)
from src.engine.validator import check_effect

PHASES = ("fetch", "setup", "compile", "test")
STEPS = ("prepare",) + PHASES + ("finish",)
OUTCOMES = ("prevented", "confined", "not_blocked")
BUILDER_CAPS = ("CHOWN", "DAC_OVERRIDE", "FOWNER", "SETUID", "SETGID", "KILL")


def phase_cmd(step: str, *, volume: str, src: Path, out: Path, policy_path: Path | None,
              tests, wrap_mode, image: str, network: bool, name: str) -> list[str]:
    """docker run command for one sandbox step (exposed for tests)."""
    cmd = ["docker", "run", "--rm", "--name", name]
    if not network:
        cmd += ["--network", "none"]
    # Root needs these caps for chown/observation; the build step itself drops
    # all of them (setpriv --inh-caps=-all) and cannot regain them.
    cmd += ["--cap-drop", "ALL"] + [a for c in BUILDER_CAPS for a in ("--cap-add", c)]
    cmd += ["--security-opt", "no-new-privileges",
            "--tmpfs", "/tmp:rw,exec,size=8g",
            "-e", f"TESTS={' '.join(tests)}"]
    if wrap_mode:
        cmd += ["-e", f"WRAP_MODE={wrap_mode}"]
    cmd += ["-v", f"{volume}:/src",
            "-v", f"{HARNESS_DIR}:/work/harness:ro",
            "-v", f"{out}:/work/out"]
    if step == "prepare":
        cmd += ["-v", f"{src}:/work/target:ro"]
    if policy_path is not None and step in PHASES:
        cmd += ["-v", f"{policy_path}:/work/policy.json:ro"]
    cmd += [image, "bash", "/work/harness/sandbox_phase.sh", step]
    return cmd


def run_in_sandbox(source_dir: str, out_dir: str, *, policy: dict | None = None,
                   tests=DEFAULT_TESTS, wrap_mode: str | None = None,
                   image: str = DEFAULT_IMAGE, timeout: int = 3600,
                   network_phases=()) -> dict:
    """
    Build and test `source_dir` phase by phase in the sandbox; return
    load_sandbox_run(out_dir). policy=None runs in LEARN mode.
    """
    src = Path(source_dir).resolve()
    out = Path(out_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    policy_path = None
    if policy is not None:
        policy_path = out / "sandbox_policy.json"
        policy_path.write_text(json.dumps(policy, indent=2), encoding="utf-8")
    (out / "sandbox_mode.txt").write_text(
        ("enforce" if policy is not None else "learn")
        + f"\nnetwork_phases={','.join(network_phases)}\n", encoding="utf-8")

    tag = uuid.uuid4().hex[:12]
    volume = f"pmt-sandbox-{tag}"
    log = out / "docker.log"
    log.write_text("", encoding="utf-8")
    _docker(["volume", "create", volume])
    try:
        for step in STEPS:
            name = f"pmt-sbx-{tag}-{step}"
            cmd = phase_cmd(step, volume=volume, src=src, out=out, policy_path=policy_path,
                            tests=tests, wrap_mode=wrap_mode, image=image,
                            network=step in network_phases, name=name)
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            except subprocess.TimeoutExpired:
                subprocess.run(["docker", "rm", "-f", name], capture_output=True)
                _append(log, f"[{step}] timed out after {timeout}s\n")
                if step in PHASES:
                    (out / f"{step}.rc").write_text("-1\n", encoding="utf-8")
                continue
            _append(log, f"[{step}] rc={proc.returncode}\n{proc.stdout}{proc.stderr}")
            if proc.returncode in DOCKER_INFRA_RCS:
                raise HarnessUnavailable(
                    f"sandbox step {step}: docker run exited {proc.returncode} "
                    f"({DOCKER_INFRA_RCS[proc.returncode]}) for {src} -> {out}; "
                    "nothing was recorded. Check Docker Desktop and rerun.")
            if proc.returncode != 0:
                # The root part of sandbox_phase.sh failed: a harness problem,
                # not a mutant result. Keep going so finish writes status.json,
                # but flag the run so it is not scored silently.
                _append(out / "sandbox_errors.txt", f"{step}: rc={proc.returncode}\n")
    finally:
        _docker(["volume", "rm", "-f", volume], check=False)
    return load_sandbox_run(str(out))


def load_sandbox_run(out_dir: str) -> dict:
    """
    load_run() plus sandbox evidence. Escaped (what the oracle scores):
    markers.txt (PWNED_* left in /src), hashes, and requests only from
    network-enabled phases. In-phase: every marker/request seen inside any
    phase, under run["inphase"].
    """
    out = Path(out_dir)
    run = load_run(out_dir)
    mode = _read(out / "sandbox_mode.txt").splitlines()
    net = set()
    for line in mode:
        if line.startswith("network_phases="):
            net = {p for p in line.split("=", 1)[1].split(",") if p}
    phases, in_markers, in_requests, escaped_requests = {}, [], [], []
    for p in PHASES:
        markers = _lines(out / f"sandbox_{p}_markers.txt")
        requests = _lines(out / f"sandbox_{p}_requests.log")
        changes_txt = _read(out / f"sandbox_{p}_changes.json")
        phases[p] = {"markers": markers, "requests": requests,
                     "changes": json.loads(changes_txt) if changes_txt else {}}
        in_markers += [m for m in markers if m not in in_markers]
        in_requests += requests
        if p in net:
            escaped_requests += requests
    run["requests"] = escaped_requests
    run["sandbox"] = {"mode": mode[0] if mode else "", "network_phases": sorted(net),
                      "phases": phases, "errors": _lines(out / "sandbox_errors.txt")}
    run["inphase"] = {"markers": in_markers, "requests": in_requests}
    return run


def learn_policy(learn_run: dict) -> dict:
    """Per-phase write policy from a LEARN-mode clean run."""
    phases = {}
    for p in PHASES:
        ch = learn_run.get("sandbox", {}).get("phases", {}).get(p, {}).get("changes", {})
        create_in = sorted({str(Path(c).parent) for c in ch.get("created", [])})
        phases[p] = {"write_files": sorted(ch.get("modified", [])), "create_in": create_in}
    return {"policy": "each phase may write build/, the files it rewrote in the clean "
                      "build, and new entries in the directories it created entries in; "
                      "the rest of /src is read-only to the build",
            "phases": phases}


def sandbox_outcome(mutant_run: dict, clean_run: dict, effect: dict | None) -> dict:
    """
    Score one sandboxed mutant run against the sandboxed clean run (both from
    load_sandbox_run). Returns {"outcome", "blocked", "reason", "evidence"}.
    """
    status = mutant_run.get("status", {})
    built = f"setup_rc={status.get('setup_rc')} compile_rc={status.get('compile_rc')}"
    if mutant_run.get("sandbox", {}).get("errors"):
        return {"outcome": "error", "blocked": False, "evidence": mutant_run["sandbox"]["errors"],
                "reason": "sandbox harness error; rerun before scoring"}
    if not effect:
        return {"outcome": "n/a", "blocked": False, "evidence": [],
                "reason": "operator declares no effect"}

    escaped = check_effect(mutant_run, clean_run, effect)
    if escaped["observed"]:
        return {"outcome": "not_blocked", "blocked": False, "evidence": escaped["evidence"],
                "reason": f"{effect['observable']} escaped the phase ({built})"}

    def inphase(run):
        return {**run, "markers": run.get("inphase", {}).get("markers", []),
                "requests": run.get("inphase", {}).get("requests", [])}
    ran = check_effect(inphase(mutant_run), inphase(clean_run), effect)
    if ran["observed"]:
        return {"outcome": "confined", "blocked": True, "evidence": ran["evidence"],
                "reason": f"{effect['observable']} seen inside the phase only; discarded with it"}
    return {"outcome": "prevented", "blocked": True, "evidence": [],
            "reason": f"{effect['observable']} never observed, even inside a phase ({built})"}


def clean_check(fp_run: dict, learn_run: dict) -> list[str]:
    """False-positive check: problems with the CLEAN target under the enforced policy."""
    problems = []
    st = fp_run.get("status", {})
    for k in ("fetch_rc", "setup_rc", "compile_rc", "test_rc"):
        if st.get(k) != 0:
            problems.append(f"{k}={st.get(k)}")
    want = {t for t, r in learn_run.get("tests", {}).items() if r == "OK"}
    got = {t for t, r in fp_run.get("tests", {}).items() if r == "OK"}
    if want - got:
        problems.append("tests failing under the policy: " + ", ".join(sorted(want - got)))
    if not want:
        problems.append("learn run passed no tests")
    if fp_run.get("markers") or fp_run.get("inphase", {}).get("markers"):
        problems.append("markers in a clean build")
    problems += [f"sandbox error: {e}" for e in fp_run.get("sandbox", {}).get("errors", [])]
    return problems


def _docker(args, check=True):
    try:
        p = subprocess.run(["docker", *args], capture_output=True, text=True, timeout=60)
    except FileNotFoundError:
        raise HarnessUnavailable("docker not found on PATH; is Docker Desktop running?")
    if check and p.returncode != 0:
        raise HarnessUnavailable(f"docker {' '.join(args)} failed: {(p.stderr or p.stdout).strip()}")
    return p


def _append(path: Path, text: str) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(text)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def _lines(path: Path) -> list[str]:
    return [l for l in _read(path).splitlines() if l.strip()]
