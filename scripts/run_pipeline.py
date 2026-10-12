#!/usr/bin/env python3
"""
scripts/run_pipeline.py

End-to-end mutation pipeline driver:

    parse target  ->  find candidates  ->  fill template  ->  generate mutant
    ->  (optional) validate with meson setup  ->  write mutant + metadata.json

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
from src.engine.validator import validate_mutant
from src.engine.reference_placement import reference_find_candidates
from src.placement import find_candidates as placement_find_candidates


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


def run(target: str, operators_dir: str, out_dir: str,
        validate: bool, use_reference: bool) -> list[dict]:
    target_root = Path(target).resolve()
    parsed = parse_project(str(target_root))
    operators = load_operators(operators_dir)
    out_root = Path(out_dir)
    out_root.mkdir(parents=True, exist_ok=True)

    target_name = target_root.name
    results = []
    counter = 0

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
    args = ap.parse_args()

    results = run(args.target, args.operators, args.out,
                  args.validate, args.reference_placement)

    applied = sum(1 for r in results if r["applied"])
    valid = sum(1 for r in results
                if r.get("validation", {}).get("setup_ok"))
    print(f"generated {len(results)} mutant(s): {applied} applied, "
          f"{valid} setup-valid")
    for r in results:
        v = r.get("validation", {}).get("status", "n/a")
        print(f"  - {Path(r['mutant_dir']).name}: applied={r['applied']} "
              f"field={r['field']} mode={r['mode']} validation={v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
