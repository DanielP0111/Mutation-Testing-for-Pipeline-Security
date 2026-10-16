#!/usr/bin/env python3
"""
scripts/run_baseline.py

Build and test the CLEAN target in the Docker harness, using the same
harness/run_build.sh that mutants use, and write the outputs the classifier
compares against (status.json, hashes.txt, testlog.json, markers.txt,
mock_server.log).

Runs with --network none by default (the offline check). Use --network only
if subprojects must be downloaded first.

    python scripts/run_baseline.py --target data/targets/git \
        --out data/evaluation/baseline

    # reproducibility check: build twice and compare hashes
    python scripts/run_baseline.py --target data/targets/git \
        --out data/evaluation/baseline --repeat 2
"""

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.engine.harness_runner import run_in_harness, DEFAULT_TESTS


def main() -> int:
    ap = argparse.ArgumentParser(description="Clean-build baseline in the harness.")
    ap.add_argument("--target", default="data/targets/git")
    ap.add_argument("--out", default="data/evaluation/baseline")
    ap.add_argument("--tests", default=" ".join(DEFAULT_TESTS))
    ap.add_argument("--wrap-mode", default=None)
    ap.add_argument("--network", action="store_true",
                    help="allow network (default: --network none)")
    ap.add_argument("--repeat", type=int, default=1,
                    help="extra runs go to <out>_run2, _run3... and hashes are compared")
    args = ap.parse_args()

    out = Path(args.out)
    outs = [out] + [out.with_name(f"{out.name}_run{i}") for i in range(2, args.repeat + 1)]
    runs = []
    for o in outs:
        run = run_in_harness(args.target, str(o), tests=tuple(args.tests.split()),
                             network=args.network, wrap_mode=args.wrap_mode)
        runs.append(run)
        print(f"{o}: status={json.dumps(run['status'])} "
              f"artifacts={len(run['hashes'])} "
              f"tests={sum(v == 'OK' for v in run['tests'].values())}/{len(run['tests'])} OK "
              f"markers={len(run['markers'])} requests={len(run['requests'])}")

    ok = True
    first = runs[0]
    if first["status"].get("compile_rc") != 0:
        print("FAIL: clean build did not compile"); ok = False
    if any(v != "OK" for v in first["tests"].values()):
        print("FAIL: some baseline tests did not pass"); ok = False
    if first["markers"] or first["requests"]:
        print("FAIL: clean build produced markers or mock-server requests"); ok = False
    for o, r in zip(outs[1:], runs[1:]):
        if r["hashes"] != first["hashes"]:
            diff = sorted(k for k in set(r["hashes"]) | set(first["hashes"])
                          if r["hashes"].get(k) != first["hashes"].get(k))
            print(f"FAIL: hashes in {o} differ from {outs[0]}: {diff}"); ok = False
    print("baseline OK" if ok else "baseline NOT usable")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
