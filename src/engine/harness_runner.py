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
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
HARNESS_DIR = REPO_ROOT / "harness"
DEFAULT_IMAGE = "pipeline-harness"
DEFAULT_TESTS = ("t0000-basic", "t0001-init", "t1007-hash-object", "t-hash")


def run_in_harness(
    source_dir: str,
    out_dir: str,
    *,
    tests: tuple[str, ...] | list[str] = DEFAULT_TESTS,
    network: bool = False,
    wrap_mode: str | None = None,
    image: str = DEFAULT_IMAGE,
    timeout: int = 3600,
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
        raise RuntimeError("docker not found on PATH; is Docker Desktop running?")
    except subprocess.TimeoutExpired:
        (out / "docker.log").write_text(f"timed out after {timeout}s", encoding="utf-8")

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
    }
