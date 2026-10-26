#!/usr/bin/env python3
"""
scripts/run_pipeline.py

End-to-end mutation pipeline driver:

    parse target  ->  find candidates  ->  fill template  ->  generate mutant
    ->  (optional) validate with meson setup
    ->  (optional) build + test in the Docker harness and classify against the
        clean baseline (setup_failed / setup_valid / build_valid / effective)
    ->  write mutant + metadata.json

Placement source:
  By default the driver calls src.placement.find_candidates (David's package).
  While those modules are still stubs it returns nothing, so --reference-placement
  switches to the engine's built-in dependency-aware reference placement, letting
  the full pipeline run today. Drop the flag once src/placement/ is implemented.

Usage:
    python scripts/run_pipeline.py \
        --target data/targets/demo_app \
        --operators data/operators \
        --out data/benchmark \
        --validate --reference-placement

    # Full oracle in the Docker harness (needs: docker build -t pipeline-harness harness/)
    python scripts/run_pipeline.py \
        --target data/targets/git \
        --operators data/operators \
        --out data/benchmark \
        --harness --baseline data/evaluation/baseline --reference-placement
"""

import argparse
import json
import sys
from pathlib import Path

# Make the repo root importable when run as a script.
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.parser import parse_project
from src.engine import load_operators, fill_template, generate_mutant
from src.engine.validator import validate_mutant, classify_runs
from src.engine.harness_runner import run_in_harness, load_run, DEFAULT_TESTS
from src.engine.reference_placement import reference_find_candidates
from src.placement import find_candidates as placement_find_candidates
from src.engine.defense_runner import (
    learn_manifests, run_defenses, available as available_defenses)


def _unified_diff(original_root: Path, mutant_rec: dict) -> str:
    import difflib

    rel = mutant_rec["file_path"]
    orig_file = original_root / rel
    mut_file = Path(mutant_rec["mutant_dir"]) / rel
    try:
        a = orig_file.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
        b = mut_file.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    except OSError:
        return ""
    return "".join(
        difflib.unified_diff(a, b, fromfile=f"a/{rel}", tofile=f"b/{rel}")
    )


def _load_or_run_baseline(target_root: Path, baseline_dir: Path, tests, wrap_mode) -> dict:
    """Reuse an existing baseline run if one is there; otherwise build it now."""
    if (baseline_dir / "status.json").exists():
        print(f"using existing baseline in {baseline_dir}")
        return load_run(str(baseline_dir))
    print(f"no baseline in {baseline_dir}; building clean target in the harness...")
    return run_in_harness(str(target_root), str(baseline_dir),
                          tests=tests, wrap_mode=wrap_mode)


def run(target: str, operators_dir: str, out_dir: str,
        validate: bool, use_reference: bool,
        harness: bool = False, baseline: str | None = None, runs: int = 3,
        tests=DEFAULT_TESTS, wrap_mode: str | None = None,
        defenses: list[str] | None = None) -> list[dict]:
    target_root = Path(target).resolve()
    parsed = parse_project(str(target_root))
    operators = load_operators(operators_dir)
    out_root = Path(out_dir)
    out_root.mkdir(parents=True, exist_ok=True)

    target_name = target_root.name
    results = []
    counter = 0

    defenses = defenses or []
    defense_manifests = learn_manifests(defenses, target_root) if defenses else {}
    if defenses:
        print(f"defenses enabled: {', '.join(defenses)}")

    baseline_run = None
    if harness:
        baseline_dir = Path(baseline) if baseline else out_root / "_baseline"
        baseline_run = _load_or_run_baseline(target_root, baseline_dir.resolve(),
                                             tests, wrap_mode)
        if baseline_run.get("status", {}).get("compile_rc") != 0:
            raise SystemExit(f"baseline in {baseline_dir} did not compile; "
                             "fix the clean build before running mutants")

    for operator in operators:
        candidates = placement_find_candidates(parsed, operator)
        if not candidates and use_reference:
            candidates = reference_find_candidates(parsed, operator)

        for candidate in candidates:
            counter += 1
            filled = fill_template(operator, candidate)
            mutant_name = f"{target_name}_{operator['id']}_{counter:04d}"
            mutant_dir = out_root / mutant_name

            record = generate_mutant(str(target_root), filled, str(mutant_dir))

            if validate and record["applied"]:
                record["validation"] = validate_mutant(record["mutant_dir"])
            else:
                record["validation"] = {"status": "skipped", "setup_ok": False,
                                        "returncode": None, "log_tail": ""}

            effect = operator.get("effect")
            if harness and record["applied"]:
                # Run outputs live outside the mutant dir so later runs
                # don't copy earlier results into the build.
                runs_root = out_root / "_runs" / mutant_name
                mutant_runs = [
                    run_in_harness(record["mutant_dir"], str(runs_root / f"run{i}"),
                                   tests=tests, wrap_mode=wrap_mode)
                    for i in range(1, runs + 1)
                ]
                record["validity"] = classify_runs(mutant_runs, baseline_run, effect)
                if effect and effect.get("requires"):
                    record["validity"]["note"] = (
                        "operator requires " + ", ".join(effect["requires"]) +
                        "; single-operator mutants may not reach effective")
            elif harness:
                record["validity"] = {"level": "not_generated", "flaky": False, "runs": []}

            if defenses:
                record["defenses"] = (
                    run_defenses(defenses, record["mutant_dir"], defense_manifests)
                    if record["applied"] else [])

            # Provenance alongside the mutant.
            diff = _unified_diff(target_root, record)
            (mutant_dir / "metadata.json").write_text(
                json.dumps(record, indent=2), encoding="utf-8"
            )
            if diff:
                (mutant_dir / "change.diff").write_text(diff, encoding="utf-8")

            results.append(record)

    return results


def main() -> int:
    ap = argparse.ArgumentParser(description="Run the mutation pipeline.")
    ap.add_argument("--target", required=True, help="path to a target Meson project")
    ap.add_argument("--operators", default="data/operators", help="operators dir")
    ap.add_argument("--out", default="data/benchmark", help="output benchmark dir")
    ap.add_argument("--validate", action="store_true", help="run meson setup on mutants")
    ap.add_argument("--reference-placement", action="store_true",
                    help="use the engine's built-in reference placement as a fallback")
    ap.add_argument("--harness", action="store_true",
                    help="build/test each mutant in the Docker harness and classify it")
    ap.add_argument("--baseline", default=None,
                    help="baseline run dir to reuse (built here if missing; "
                         "default <out>/_baseline)")
    ap.add_argument("--runs", type=int, default=3,
                    help="harness runs per mutant (lowest level wins; default 3)")
    ap.add_argument("--tests", default=" ".join(DEFAULT_TESTS),
                    help="space-separated meson test names to run")
    ap.add_argument("--wrap-mode", default=None,
                    help="meson --wrap-mode, e.g. forcefallback for wrap operators")
    ap.add_argument("--defense", action="append", default=[], metavar="NAME",
                    help="static defense to run against each mutant (repeatable); "
                         "available: " + (", ".join(available_defenses()) or "none"))
    args = ap.parse_args()

    results = run(args.target, args.operators, args.out,
                  args.validate, args.reference_placement,
                  harness=args.harness, baseline=args.baseline, runs=args.runs,
                  tests=tuple(args.tests.split()), wrap_mode=args.wrap_mode,
                  defenses=args.defense)

    applied = sum(1 for r in results if r["applied"])
    valid = sum(1 for r in results
                if r.get("validation", {}).get("setup_ok"))
    print(f"generated {len(results)} mutant(s): {applied} applied, "
          f"{valid} setup-valid")
    if args.harness:
        from collections import Counter
        levels = Counter(r.get("validity", {}).get("level") for r in results)
        flaky = sum(1 for r in results if r.get("validity", {}).get("flaky"))
        print("validity levels: " + ", ".join(f"{k}={v}" for k, v in sorted(levels.items())) +
              f" (flaky={flaky})")
    if args.defense:
        applied_n = sum(1 for r in results if r.get("applied"))
        for name in args.defense:
            blocked = sum(1 for r in results if r.get("applied") and any(
                d["name"] == name and d["blocked"] for d in r.get("defenses", [])))
            print(f"defense {name}: blocked {blocked}/{applied_n} applied mutant(s)")
    for r in results:
        v = r.get("validation", {}).get("status", "n/a")
        lvl = r.get("validity", {}).get("level", "n/a")
        print(f"  - {Path(r['mutant_dir']).name}: applied={r['applied']} "
              f"field={r['field']} mode={r['mode']} validation={v} validity={lvl}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
