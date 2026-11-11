"""
src/engine/harness_runner.py

Runs a project (clean target or mutant) through the Docker build harness and
loads the results. The container does the build; this module only launches it
and parses what it wrote (see harness/run_build.sh for the output files).

Requires Docker and the harness image:
    docker build -t pipeline-harness harness/
"""

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
HARNESS_DIR = REPO_ROOT / "harness"
DEFAULT_IMAGE = "pipeline-harness"
DEFAULT_TESTS = ("t0000-basic", "t0001-init", "t1007-hash-object", "t-hash")


# `docker run` exit codes that mean the harness itself never ran, as opposed to
# a build that ran and failed: 125 = Docker daemon error (daemon died, image
# gone, bad mount), 126 = container command could not be invoked, 127 = command
# not found in the image.
DOCKER_INFRA_RCS = {125: "Docker daemon error", 126: "command not invokable",
                    127: "command not found in image"}


class HarnessUnavailable(RuntimeError):
    """The container never ran, so there are no results to record."""


def check_docker(image: str = DEFAULT_IMAGE, timeout: int = 15) -> None:
    """
    Fail fast if the harness cannot run: Docker CLI missing, daemon unreachable
    (Docker Desktop closed), or the harness image not built.

    Without this, every `docker run` fails, every run dir loads empty, and the
    classifier scores every mutant setup_failed with "0 false positives" -- a
    run that looks successful but is garbage (seen Oct 30). Exits the process
    with a clear message instead.
    """
    def fail(msg: str) -> None:
        sys.exit(f"ERROR: {msg}")

    try:
        info = subprocess.run(["docker", "info", "--format", "{{.ServerVersion}}"],
                              capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        fail("docker not found on PATH. Install Docker Desktop and retry.")
    except subprocess.TimeoutExpired:
        fail(f"`docker info` did not answer within {timeout}s. "
             "Is Docker Desktop still starting? Wait for it and retry.")
    if info.returncode != 0:
        detail = (info.stderr or info.stdout).strip().splitlines()
        fail("Docker is not reachable. Start Docker Desktop and retry."
             + (f"\n  docker info: {detail[-1]}" if detail else ""))

    try:
        img = subprocess.run(["docker", "image", "inspect", image],
                             capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        fail(f"`docker image inspect {image}` timed out.")
    if img.returncode != 0:
        fail(f"harness image '{image}' not found. Build it first:\n"
             f"  docker build -t {image} harness/")


def run_in_harness(
    source_dir: str,
    out_dir: str,
    *,
    tests: tuple[str, ...] | list[str] = DEFAULT_TESTS,
    network: bool = False,
    wrap_mode: str | None = None,
    image: str = DEFAULT_IMAGE,
    timeout: int = 3600,
    foreman_spec: str | None = None,
) -> dict:
    """
    Build and test `source_dir` in the harness container; return load_run(out_dir).

    network=False runs with --network none (the mock attacker server on
    127.0.0.1 still works). Use network=True only for the first baseline run,
    so subprojects can be downloaded into the target's packagecache.
    """
    src = Path(source_dir).resolve()
    out = Path(out_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)

    cmd = ["docker", "run", "--rm"]
    if not network:
        cmd += ["--network", "none"]
    cmd += ["-e", f"TESTS={' '.join(tests)}"]
    if wrap_mode:
        cmd += ["-e", f"WRAP_MODE={wrap_mode}"]
    if foreman_spec:
        # Foreman decides "accessed" from file access times, so /src must record
        # every read: a tmpfs mounted with strictatime (Docker's default overlay
        # uses relatime, which would hide repeat reads). Foreman itself is the
        # vendored, unmodified copy in third_party/foreman.
        cmd += ["--tmpfs", "/src:rw,exec,strictatime,size=16g",
                "-e", "FOREMAN_SPEC=/work/foreman_spec.json",
                "-v", f"{Path(foreman_spec).resolve()}:/work/foreman_spec.json:ro",
                "-v", f"{REPO_ROOT / 'third_party' / 'foreman'}:/work/foreman:ro"]
    cmd += [
        "-v", f"{HARNESS_DIR}:/work/harness:ro",
        "-v", f"{src}:/work/target:ro",
        "-v", f"{out}:/work/out",
        image, "bash", "/work/harness/run_build.sh",
    ]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        (out / "docker.log").write_text(proc.stdout + proc.stderr, encoding="utf-8")
    except FileNotFoundError:
        raise HarnessUnavailable("docker not found on PATH; is Docker Desktop running?")
    except subprocess.TimeoutExpired:
        (out / "docker.log").write_text(f"timed out after {timeout}s", encoding="utf-8")
    else:
        if proc.returncode in DOCKER_INFRA_RCS:
            # Mid-run guard: Docker died (or the image broke) after the
            # preflight passed. This run dir would load empty and be scored
            # setup_failed, so stop the whole run instead of recording it.
            # status.json is never written here, so a rerun redoes this dir.
            tail = (proc.stderr or proc.stdout).strip().splitlines()
            raise HarnessUnavailable(
                f"docker run exited {proc.returncode} "
                f"({DOCKER_INFRA_RCS[proc.returncode]}) for {src} -> {out}; "
                "the harness did not run, so nothing was recorded. "
                "Check Docker Desktop and rerun."
                + (f"\n  docker: {tail[-1]}" if tail else ""))

    return load_run(str(out))


def load_run(out_dir: str) -> dict:
    """
    Parse a harness output folder into a plain dict:

        {
          "status":  {"fetch_rc", "setup_rc", "compile_rc", "test_rc"} or {},
          "hashes":  {relative_path: sha256},
          "tests":   {test_name: "OK" | "FAIL" | ...},
          "markers": [paths of PWNED_* files],
          "requests": [lines from the mock attacker server log],
        }

    Missing files load as empty values, so a run that died early still parses.
    """
    out = Path(out_dir)

    def read(name: str) -> str:
        p = out / name
        return p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""

    status = json.loads(read("status.json") or "{}")

    hashes = {}
    for line in read("hashes.txt").splitlines():
        parts = line.split(None, 1)
        if len(parts) == 2:
            hashes[parts[1].strip()] = parts[0]

    tests = {}
    for line in read("testlog.json").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if "name" in rec and "result" in rec:
            tests[rec["name"]] = rec["result"]

    return {
        "status": status,
        "hashes": hashes,
        "tests": tests,
        "markers": [l for l in read("markers.txt").splitlines() if l.strip()],
        "requests": [l for l in read("mock_server.log").splitlines() if l.strip()],
        "foreman_warnings": [l for l in read("foreman_warnings.txt").splitlines() if l.strip()],
    }
