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
from src.engine.template_filler import resolve_effect
from src.engine import load_operators, fill_template, generate_mutant
from src.engine.validator import validate_mutant, classify_runs
from src.engine.harness_runner import run_in_harness, load_run, DEFAULT_TESTS, check_docker
from src.engine import foreman_spec
from src.engine import sandbox as sbx
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


def _load_or_run_baseline(target_root: Path, baseline_dir: Path, tests, wrap_mode,
                          foreman_spec: str | None = None) -> dict:
    """Reuse an existing baseline run if one is there; otherwise build it now."""
    if (baseline_dir / "status.json").exists():
        if foreman_spec and not (baseline_dir / "foreman_info.txt").exists():
            raise SystemExit(f"--foreman needs a baseline built under Foreman; {baseline_dir} "
                             "was not. Pass a new --baseline dir and it will be built.")
        print(f"using existing baseline in {baseline_dir}")
        return load_run(str(baseline_dir))
    print(f"no baseline in {baseline_dir}; building clean target in the harness"
          + (" under Foreman" if foreman_spec else "") + "...")
    return run_in_harness(str(target_root), str(baseline_dir),
                          tests=tests, wrap_mode=wrap_mode, foreman_spec=foreman_spec)


def _prepare_sandbox(target_root: Path, out_root: Path, tests, wrap_mode,
                     network_phases) -> dict:
    """Learn the sandbox policy from a clean LEARN-mode build, then rebuild the
    clean target under it (false-positive check). Both dirs are reused if present."""
    learn_dir = out_root / "_sandbox_learn"
    if (learn_dir / "status.json").exists():
        learn_run = sbx.load_sandbox_run(str(learn_dir))
    else:
        print("sandbox: learning per-phase write policy from a clean build...")
        learn_run = sbx.run_in_sandbox(str(target_root), str(learn_dir), policy=None,
                                       tests=tests, wrap_mode=wrap_mode)
    st = learn_run.get("status", {})
    if st.get("compile_rc") != 0 or learn_run["sandbox"]["errors"]:
        raise SystemExit(f"sandbox: clean LEARN build failed ({st}); see {learn_dir}")
    policy = sbx.learn_policy(learn_run)
    (out_root / "sandbox_policy.json").write_text(json.dumps(policy, indent=2), encoding="utf-8")
    n = {p: len(v["write_files"]) + len(v["create_in"]) for p, v in policy["phases"].items()}
    print(f"sandbox: learned policy -> {out_root / 'sandbox_policy.json'} (writable entries per phase: {n})")

    fp_dir = out_root / "_sandbox_clean_check"
    if (fp_dir / "status.json").exists():
        fp_run = sbx.load_sandbox_run(str(fp_dir))
    else:
        print("sandbox: rebuilding the clean target under the policy (false-positive check)...")
        fp_run = sbx.run_in_sandbox(str(target_root), str(fp_dir), policy=policy,
                                    tests=tests, wrap_mode=wrap_mode,
                                    network_phases=network_phases)
    problems = sbx.clean_check(fp_run, learn_run)
    if problems:
        # A sandbox that breaks the clean build would "prevent" every mutant.
        raise SystemExit("sandbox: clean build FAILS under the policy (false positive): "
                         + "; ".join(problems) + f"\n  see {fp_dir}")
    print(f"sandbox: clean rebuild passes under the policy "
          f"({sum(r == 'OK' for r in fp_run['tests'].values())} tests OK, 0 false positives)")
    return {"policy": policy, "run": fp_run}


def run(target: str, operators_dir: str, out_dir: str,
        validate: bool, use_reference: bool,
        harness: bool = False, baseline: str | None = None, runs: int = 3,
        tests=DEFAULT_TESTS, wrap_mode: str | None = None,
        defenses: list[str] | None = None,
        only: set[str] | None = None,
        foreman: str | None = None,
        sandbox: bool = False, sandbox_network_phases=()) -> list[dict]:
    target_root = Path(target).resolve()
    parsed = parse_project(str(target_root))
    operators = load_operators(operators_dir)
    if only:
        operators = [o for o in operators if o.get("id") in only]
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
                                             tests, wrap_mode, foreman_spec=foreman)
        if baseline_run.get("status", {}).get("compile_rc") != 0:
            raise SystemExit(f"baseline in {baseline_dir} did not compile; "
                             "fix the clean build before running mutants")
        if foreman:
            spec = foreman_spec.load_spec(foreman)
            if foreman_spec.needs_learning(spec):
                gran = foreman_spec.learn_granularity(spec)
                learned = foreman_spec.learn_from_info(baseline_dir / "foreman_info.txt",
                                                       target_root, granularity=gran)
                foreman = str((out_root / "foreman_spec_learned.json").resolve())
                Path(foreman).write_text(json.dumps(learned, indent=2), encoding="utf-8")
                print(f"foreman: learned {gran}-level phase permissions from the clean build -> {foreman}")
            else:
                foreman = str(Path(foreman).resolve())
            # False-positive check: rebuild the CLEAN target under the final spec.
            # Its warnings are noise (not attacks); they are reported and
            # subtracted from every mutant's warnings.
            fp_dir = out_root / "_foreman_clean_check"
            if not (fp_dir / "status.json").exists():
                print("foreman: rebuilding the clean target under the spec to measure false positives...")
                run_in_harness(str(target_root), str(fp_dir), tests=tests,
                               wrap_mode=wrap_mode, foreman_spec=foreman)
            fp_run = load_run(str(fp_dir))
            baseline_run["foreman_warnings"] = fp_run.get("foreman_warnings", [])
            print(f"foreman: {len(baseline_run['foreman_warnings'])} warning(s) on the clean rebuild "
                  f"(false positives; see {fp_dir}/foreman_warnings.txt)")

    sbx_clean = None
    if harness and sandbox:
        sbx_clean = _prepare_sandbox(target_root, out_root, tests, wrap_mode,
                                     sandbox_network_phases)

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

            effect = resolve_effect(operator, candidate)
            if harness and record["applied"]:
                # Run outputs live outside the mutant dir so later runs
                # don't copy earlier results into the build.
                runs_root = out_root / "_runs" / mutant_name
                mutant_runs = [
                    run_in_harness(record["mutant_dir"], str(runs_root / f"run{i}"),
                                   tests=tests, wrap_mode=wrap_mode, foreman_spec=foreman)
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
            if foreman and harness and record["applied"]:
                # Foreman is a detector that runs during the build: a mutant is
                # detected if any run produced a warning the clean build did not.
                base_w = set(baseline_run.get("foreman_warnings", []))
                new_w = sorted({w for r in mutant_runs for w in r.get("foreman_warnings", [])} - base_w)
                record.setdefault("defenses", []).append({
                    "name": "foreman", "mode": "detect", "blocked": False,
                    "detected": bool(new_w), "flags": new_w[:50],
                    "spec": foreman})

            if sbx_clean and record["applied"]:
                # Enforcing defense: build the mutant phase by phase in the
                # sandbox and see whether its declared effect escapes a phase.
                sbx_run = sbx.run_in_sandbox(
                    record["mutant_dir"], str(out_root / "_runs" / mutant_name / "sandbox"),
                    policy=sbx_clean["policy"], tests=tests, wrap_mode=wrap_mode,
                    network_phases=sandbox_network_phases)
                o = sbx.sandbox_outcome(sbx_run, sbx_clean["run"], effect)
                record.setdefault("defenses", []).append({
                    "name": "sandbox", "mode": "enforce", **o,
                    "network_phases": list(sandbox_network_phases)})

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
    ap.add_argument("--foreman", default=None, metavar="SPEC",
                    help="run every harness build under Foreman (Pappas & Gazzillo) with this "
                         "phase spec; a spec with no permissions is learned from the clean build. "
                         "Needs --harness and a baseline dir built under Foreman.")
    ap.add_argument("--sandbox", action="store_true",
                    help="also build each mutant in the per-phase isolation sandbox "
                         "(enforcing defense; policy learned from a clean build)")
    ap.add_argument("--sandbox-network-phase", action="append", default=[],
                    choices=("fetch", "setup", "compile", "test"), metavar="PHASE",
                    help="give this sandbox phase network access, so its mock-server "
                         "requests count as escaped (repeatable; default: none)")
    ap.add_argument("--only", action="append", default=[], metavar="OP",
                    help="run only this operator (file prefix like op_013, or its id); repeatable")
    args = ap.parse_args()
    if args.sandbox and not args.harness:
        ap.error("--sandbox needs --harness")
    if args.foreman and not args.harness:
        ap.error("--foreman needs --harness (Foreman runs inside the harness build)")

    if args.harness:
        check_docker()  # fail fast: a dead daemon would score every mutant setup_failed

    only = set()
    for tok in args.only:
        for f in sorted(Path(args.operators).glob("*.json")):
            try:
                op_id = json.loads(f.read_text(encoding="utf-8")).get("id")
            except (OSError, json.JSONDecodeError):
                continue
            if f.name.startswith(tok) or op_id == tok:
                only.add(op_id)
    if args.only and not only:
        raise SystemExit(f"--only matched no operator in {args.operators}: {', '.join(args.only)}")

    results = run(args.target, args.operators, args.out,
                  args.validate, args.reference_placement,
                  harness=args.harness, baseline=args.baseline, runs=args.runs,
                  tests=tuple(args.tests.split()), wrap_mode=args.wrap_mode,
                  defenses=args.defense, only=only or None, foreman=args.foreman,
                  sandbox=args.sandbox,
                  sandbox_network_phases=tuple(args.sandbox_network_phase))

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
    if args.foreman:
        eff = [r for r in results if r.get("validity", {}).get("level") == "effective"]
        det = sum(1 for r in eff if any(d["name"] == "foreman" and d.get("detected")
                                        for d in r.get("defenses", [])))
        print(f"defense foreman: detected {det}/{len(eff)} effective mutant(s)")
    if args.sandbox:
        from collections import Counter
        eff = [r for r in results if r.get("validity", {}).get("level") == "effective"]
        oc = Counter(next((d["outcome"] for d in r.get("defenses", []) if d["name"] == "sandbox"),
                          "missing") for r in eff)
        print(f"defense sandbox: blocked {oc['prevented'] + oc['confined']}/{len(eff)} effective "
              f"mutant(s) (prevented={oc['prevented']}, confined={oc['confined']}, "
              f"not_blocked={oc['not_blocked']}, error={oc['error']})")
    if args.defense:
        applied = [r for r in results if r.get("applied")]
        eff = [r for r in applied if r.get("validity", {}).get("level") == "effective"]
        for name in args.defense:
            def blocked(r):
                return any(d["name"] == name and d["blocked"] for d in r.get("defenses", []))
            if args.harness:
                # Scored only on effective mutants (methodology 2.5): blocking a
                # mutant that never worked is not a defense success.
                print(f"defense {name}: blocked {sum(map(blocked, eff))}/{len(eff)} effective mutant(s)"
                      f"  [{sum(map(blocked, applied))}/{len(applied)} of all applied, incl. non-effective]")
            else:
                print(f"defense {name}: blocked {sum(map(blocked, applied))}/{len(applied)} applied mutant(s)"
                      " (no --harness, so effectiveness is unknown)")
    for r in results:
        v = r.get("validation", {}).get("status", "n/a")
        lvl = r.get("validity", {}).get("level", "n/a")
        print(f"  - {Path(r['mutant_dir']).name}: applied={r['applied']} "
              f"field={r['field']} mode={r['mode']} validation={v} validity={lvl}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
