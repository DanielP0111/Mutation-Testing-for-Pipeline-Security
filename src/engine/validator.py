"""
src/engine/validator.py

Two jobs:

1. validate_mutant(): quick local check that `meson setup` accepts a mutant
   (the old milestone check; still used by run_pipeline.py --validate).

2. classify_run() / classify_runs(): the attack-effect oracle. Compares a
   mutant's harness run with the clean baseline run (both from
   harness_runner.load_run()) and assigns a validity level:

       setup_failed < setup_valid < build_valid < effective

   setup_failed  `meson setup` failed (or the run died before it).
   setup_valid   setup passed but compile failed, or a baseline-passing test
                 now fails that the operator did not say it would break.
   build_valid   compiled, and every test that passed in the baseline still
                 passes (except tests the operator lists in tests_may_fail).
   effective     build_valid AND the operator's declared effect is observed.
                 Only effective mutants are scored against defenses.

   Each effect type is checked in its own evidence file, always as a diff
   against the baseline:

       file_write       markers.txt      new PWNED_* marker (baseline: none)
       network_fetch    mock_server.log  new request to the mock server
       env_exfil        mock_server.log  request containing the canary secret
       artifact_diff    hashes.txt       an output hash differs from baseline
       test_input_swap  hashes.txt       same as artifact_diff (fixture linked
                                         into an output changes its hash)
"""

import shutil
import subprocess
import tempfile
from pathlib import Path


def validate_mutant(mutant_dir: str, timeout: int = 300) -> dict:
    """
    Run `meson setup` on a mutant project and report the outcome.

    Args:
        mutant_dir: path to the mutant project root (must contain meson.build).
        timeout:    seconds before the setup is abandoned.

    Returns:
        {
            "setup_ok":   bool,        # True iff meson setup returned 0
            "returncode": int | None,  # None if meson missing or timed out
            "status":     str,         # "valid" | "invalid" | "error" | "skipped"
            "log_tail":   str,         # last lines of meson output (for triage)
        }
    """
    root = Path(mutant_dir)
    if not (root / "meson.build").exists():
        return {
            "setup_ok": False,
            "returncode": None,
            "status": "skipped",
            "log_tail": "no top-level meson.build found",
        }

    if shutil.which("meson") is None:
        return {
            "setup_ok": False,
            "returncode": None,
            "status": "error",
            "log_tail": "meson not found on PATH",
        }

    build_dir = tempfile.mkdtemp(prefix="meson_validate_")
    try:
        proc = subprocess.run(
            ["meson", "setup", build_dir, str(root), "--wipe"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        ok = proc.returncode == 0
        output = (proc.stdout or "") + (proc.stderr or "")
        return {
            "setup_ok": ok,
            "returncode": proc.returncode,
            "status": "valid" if ok else "invalid",
            "log_tail": "\n".join(output.strip().splitlines()[-25:]),
        }
    except subprocess.TimeoutExpired:
        return {
            "setup_ok": False,
            "returncode": None,
            "status": "error",
            "log_tail": f"meson setup timed out after {timeout}s",
        }
    finally:
        shutil.rmtree(build_dir, ignore_errors=True)


# ===========================================================================
# Attack-effect oracle
# ===========================================================================

LEVELS = ("setup_failed", "setup_valid", "build_valid", "effective")
OBSERVABLES = ("file_write", "network_fetch", "env_exfil",
               "artifact_diff", "test_input_swap")

# Must match CANARY_SECRET in harness/run_build.sh.
CANARY_SECRET = "CANARY_SECRET_7f3a91"


def _rank(level: str) -> int:
    return LEVELS.index(level)


def newly_failing_tests(mutant_run: dict, baseline_run: dict) -> list[str]:
    """Tests that were OK in the baseline but are not OK (or missing) now."""
    base = baseline_run.get("tests", {})
    mut = mutant_run.get("tests", {})
    return sorted(name for name, res in base.items()
                  if res == "OK" and mut.get(name) != "OK")


def _changed_artifacts(mutant_run: dict, baseline_run: dict) -> list[str]:
    base = baseline_run.get("hashes", {})
    mut = mutant_run.get("hashes", {})
    return sorted(path for path in set(base) | set(mut)
                  if base.get(path) != mut.get(path))


def _new_items(mutant_list: list, baseline_list: list) -> list:
    seen = set(baseline_list)
    return [x for x in mutant_list if x not in seen]


def check_effect(mutant_run: dict, baseline_run: dict, effect: dict) -> dict:
    """
    Decide whether the operator's declared effect shows up in the mutant run.

    effect = {"observable": <one of OBSERVABLES>,
              "check": {optional narrowing keys, see below}}

    check keys (all optional):
      marker        substring the marker path must contain (file_write)
      request_path  substring the request line must contain
                    (network_fetch, env_exfil)
      contains      substring the request line must contain; env_exfil
                    defaults to CANARY_SECRET
      artifact      artifact path (as in hashes.txt, e.g. "build/git") whose
                    hash must differ (artifact_diff, test_input_swap)

    Returns {"observed": bool, "evidence": [str, ...]}.
    """
    obs = effect.get("observable")
    check = effect.get("check") or {}

    if obs == "file_write":
        hits = _new_items(mutant_run.get("markers", []),
                          baseline_run.get("markers", []))
        if check.get("marker"):
            hits = [h for h in hits if check["marker"] in h]

    elif obs in ("network_fetch", "env_exfil"):
        hits = _new_items(mutant_run.get("requests", []),
                          baseline_run.get("requests", []))
        if check.get("request_path"):
            hits = [h for h in hits if check["request_path"] in h]
        needle = check.get("contains") or (CANARY_SECRET if obs == "env_exfil" else None)
        if needle:
            hits = [h for h in hits if needle in h]

    elif obs in ("artifact_diff", "test_input_swap"):
        hits = _changed_artifacts(mutant_run, baseline_run)
        if check.get("artifact"):
            hits = [h for h in hits if h == check["artifact"]]

    else:
        raise ValueError(f"unknown effect observable {obs!r}; expected one of {OBSERVABLES}")

    return {"observed": bool(hits), "evidence": hits}


def classify_run(mutant_run: dict, baseline_run: dict, effect: dict | None = None) -> dict:
    """
    Assign a validity level to ONE harness run of a mutant.

    Args:
        mutant_run:   load_run() output for the mutant.
        baseline_run: load_run() output for the clean build of the same target.
        effect:       the operator's "effect" block, or None. Without one the
                      mutant can reach build_valid at most.

    Returns:
        {
          "level":         one of LEVELS,
          "reason":        short human-readable explanation,
          "newly_failing": tests OK in baseline, not OK here,
          "effect":        check_effect() result, or None if not checked,
        }

    Raises:
        ValueError if the baseline itself did not compile (nothing to compare to).
    """
    if baseline_run.get("status", {}).get("compile_rc") != 0:
        raise ValueError("baseline run did not compile; rerun the baseline first")

    status = mutant_run.get("status", {})
    failing = newly_failing_tests(mutant_run, baseline_run)
    result = {"level": "setup_failed", "reason": "", "newly_failing": failing,
              "effect": None}

    if status.get("setup_rc") != 0:
        result["reason"] = f"meson setup failed (rc={status.get('setup_rc')})"
        return result

    result["level"] = "setup_valid"
    if status.get("compile_rc") != 0:
        result["reason"] = f"meson compile failed (rc={status.get('compile_rc')})"
        return result

    allowed = set(((effect or {}).get("check") or {}).get("tests_may_fail", []))
    unexpected = [t for t in failing if t not in allowed]
    if unexpected:
        result["reason"] = "baseline-passing tests now fail: " + ", ".join(unexpected)
        return result

    result["level"] = "build_valid"
    if not effect:
        result["reason"] = "built; operator declares no effect, so it cannot be effective"
        return result

    eff = check_effect(mutant_run, baseline_run, effect)
    result["effect"] = eff
    if eff["observed"]:
        result["level"] = "effective"
        result["reason"] = f"{effect['observable']} observed"
    else:
        result["reason"] = f"built, but {effect['observable']} not observed"
    return result


def classify_runs(mutant_runs: list[dict], baseline_run: dict,
                  effect: dict | None = None) -> dict:
    """
    Classify repeated runs of the same mutant (the plan calls for 3).

    The final level is the LOWEST level any run reached, so a mutant only
    counts as effective if it was effective every time. If runs disagree the
    mutant is marked flaky, and it should be excluded or investigated rather
    than scored.

    Returns {"level", "flaky", "runs": [classify_run() result, ...]}.
    """
    if not mutant_runs:
        raise ValueError("classify_runs needs at least one run")
    runs = [classify_run(r, baseline_run, effect) for r in mutant_runs]
    levels = {r["level"] for r in runs}
    final = min(levels, key=_rank)
    return {"level": final, "flaky": len(levels) > 1, "runs": runs}
