#!/usr/bin/env python3
"""
scripts/trace_mutant.py

Walks ONE mutant through every stage of the pipeline, printing the real
artifacts each stage produced. Made for the mechanistic walkthrough video,
but also handy for debugging a single mutant.

    python scripts/trace_mutant.py                      # all stages, op_013 mutant
    python scripts/trace_mutant.py --stage 3            # one stage (for a video scene)
    python scripts/trace_mutant.py --pause              # wait for Enter between stages
    python scripts/trace_mutant.py --mutant git_netbeans_build_script_tampering_0011

Stages:
  0 overview   1 taxonomy   2 operator   3 placement   4 mutant
  5 harness    6 oracle     7 defense    8 caveat (wrap no-ops)   9 summary

Defaults can also come from TRACE_MUTANT / TRACE_BENCHMARK / TRACE_BASELINE /
TRACE_COLOR (the video build script sets these so on-screen commands stay short).

Reads existing results (data/benchmark, data/evaluation/baseline); nothing
is rebuilt. Stages 3 and 7 re-run placement and the wrap integrity check
live, because both take well under a second.
"""

import argparse
import contextlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DEFAULT_MUTANT = "git_configure_marker_injection_0017"

# ---------------------------------------------------------------- output ---

USE_COLOR = sys.stdout.isatty()


def c(text, code):
    return f"\033[{code}m{text}\033[0m" if USE_COLOR else str(text)


def bold(t): return c(t, "1")
def dim(t): return c(t, "2")
def green(t): return c(t, "32")
def red(t): return c(t, "31")
def yellow(t): return c(t, "33")
def cyan(t): return c(t, "36")


def header(num, title, subtitle):
    bar = "━" * 72
    print()
    print(cyan(bar))
    print(bold(cyan(f" STAGE {num} · {title.upper()}")))
    print(dim(f" {subtitle}"))
    print(cyan(bar))


def kv(key, value, width=20):
    print(f"  {dim(key.ljust(width))} {value}")


def note(text):
    print(f"  {yellow('→')} {text}")


def show_file_ref(path):
    try:
        rel = Path(path).resolve().relative_to(ROOT)
    except ValueError:
        rel = path
    print(dim(f"  file: {rel}"))


# ----------------------------------------------------------------- data ---

def load_json(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default


def read_lines(path):
    try:
        return [l.rstrip("\n") for l in open(path) if l.strip()]
    except OSError:
        return []


def read_testlog(path):
    out = {}
    try:
        for line in open(path):
            line = line.strip()
            if line:
                rec = json.loads(line)
                out[rec["name"]] = rec.get("result")
    except (OSError, json.JSONDecodeError):
        pass
    return out


class Ctx:
    def __init__(self, args):
        self.args = args
        self.bench = ROOT / args.benchmark
        self.mutant_dir = self.bench / args.mutant
        self.runs_dir = self.bench / "_runs" / args.mutant
        self.baseline = ROOT / args.baseline
        self.target = ROOT / args.target
        self.meta = load_json(self.mutant_dir / "metadata.json")
        if self.meta is None:
            sys.exit(f"no metadata.json in {self.mutant_dir} — run the pipeline first, "
                     f"or pick a mutant from: {', '.join(sorted(p.name for p in self.bench.iterdir() if p.is_dir() and not p.name.startswith('_')))}")
        self.operator, self.operator_path = self._find_operator()

    def _find_operator(self):
        for p in sorted((ROOT / "data" / "operators").glob("*.json")):
            d = load_json(p)
            if d and d.get("id") == self.meta.get("operator_id"):
                return d, p
        return {}, None

    def run(self, i):
        return self.runs_dir / f"run{i}"


# --------------------------------------------------------------- stages ---

def stage_overview(ctx):
    header(0, "Overview", "One mutant, traced from the real-world attack to the defense verdict")
    m = ctx.meta
    kv("mutant", bold(ctx.args.mutant))
    kv("operator", f"{m.get('operator_id')}  ({m.get('operator_name')})")
    kv("target project", f"{ctx.target.relative_to(ROOT)}  (git, Meson build)")
    kv("final verdict", verdict_str(m.get("validity", {}).get("level")))
    print()
    print("  " + "  →  ".join(["taxonomy", "operator", "placement", "mutant",
                              "harness", "oracle", "defense"]))


def kappa(pairs):
    n = len(pairs)
    if not n:
        return None, 0, 0
    agree = sum(a == b for a, b in pairs)
    po = agree / n
    cats = {a for a, _ in pairs} | {b for _, b in pairs}
    pe = sum((sum(a == k for a, _ in pairs) / n) * (sum(b == k for _, b in pairs) / n)
             for k in cats)
    k = 1.0 if pe == 1 else (po - pe) / (1 - pe)
    return k, agree, n


def stage_taxonomy(ctx):
    header(1, "Taxonomy", "Documented real-world incidents, each labeled with the build phase it hit")
    attacks = load_json(ROOT / "data" / "taxonomy" / "attacks.json", [])
    cited = ctx.operator.get("source_attacks", [])
    print(f"  This operator models: {', '.join(cited) or '(none listed)'}")
    print()
    for name in cited:
        key = name.split("(")[0].strip().lower()
        hit = next((a for a in attacks if key and (key in a.get("name", "").lower()
                    or a.get("name", "").lower().split()[0] in key)), None)
        if not hit:
            print(f"  {yellow('?')} {name}: not found in attacks.json")
            continue
        print(f"  {bold(hit['id'])}  {bold(hit['name'])} ({hit.get('year', '?')})")
        kv("build phase", hit.get("build_phase"), 18)
        kv("attack vector", hit.get("attack_vector"), 18)
        kv("dataflow pattern", hit.get("dataflow_pattern"), 18)
        print()
    show_file_ref(ROOT / "data" / "taxonomy" / "attacks.json")

    doc = ROOT / "docs" / "inter_rater_reliability.md"
    pairs = []
    for line in read_lines(doc):
        cells = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(cells) >= 5 and cells[0].startswith("ATK-"):
            pairs.append((cells[2], cells[3]))
    k, agree, n = kappa(pairs)
    if n:
        print()
        note(f"Phase labels double-coded blind: {agree}/{n} agree, Cohen's κ = {k:.2f}")
        show_file_ref(doc)


def stage_operator(ctx):
    header(2, "Operator", "The attack mechanism, abstracted into a reusable JSON injection rule")
    op = ctx.operator
    if not op:
        print(red("  operator spec not found"))
        return
    loc = op.get("injection_location", {})
    kv("id", bold(op.get("id")))
    kv("target_build_phase", op.get("target_build_phase"))
    kv("scheme", op.get("scheme"))
    kv("mode", op.get("mode"))
    kv("injection_location", f"file_glob={loc.get('file_glob')}  field={loc.get('field')}")
    kv("placeholders", ", ".join(op.get("placeholders", {})) or "-")
    kv("attacker_values", json.dumps(op.get("attacker_values", {})))
    print(f"  {dim('template'.ljust(20))}")
    for k2, v in op.get("template", {}).items():
        print(f"      {k2}: {green(v)}")
    eff = op.get("effect")
    if eff:
        kv("effect", bold(f"{eff.get('observable')}  check={json.dumps(eff.get('check', {}))}"))
    else:
        kv("effect", red("none — this operator can never be classified 'effective'"))
    show_file_ref(ctx.operator_path)


def stage_placement(ctx):
    header(3, "Placement", "Find every spot in the target this operator can be injected (run live)")
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            from src.parser import parse_project
            from src.engine import fill_template
            from src.engine.reference_placement import reference_find_candidates
            from src.placement import find_candidates
            parsed = parse_project(str(ctx.target))
            cands = find_candidates(parsed, ctx.operator) or reference_find_candidates(parsed, ctx.operator)
    except Exception as e:  # keep the walkthrough going even if imports fail
        print(red(f"  placement could not run here: {e}"))
        return
    print(f"  parsed target: {len(parsed.get('wrap_files', []))} wrap files, "
          f"meson.build at project root")
    print(f"  candidates found: {bold(len(cands))}")
    for cand in cands[:6]:
        print(f"    • {cand['file_path']}  (field: {cand['field']})")
    if cands:
        filled = fill_template(ctx.operator, cands[0])
        print()
        print("  first candidate, template filled in:")
        kv("file_path", filled.get("file_path"))
        kv("mode", ctx.operator.get("mode"))
        kv("replacement_value", green(filled.get("replacement_value")))
    else:
        note("zero candidates — this operator produces no mutants on this target")


def stage_mutant(ctx):
    header(4, "Mutant", "A full copy of the target with exactly ONE change applied")
    m = ctx.meta
    kv("mutant dir", str(ctx.mutant_dir.relative_to(ROOT)))
    kv("changed file", m.get("file_path"))
    kv("mode", m.get("mode"))
    kv("applied", green("yes") if m.get("applied") else red("no"))
    print()
    print("  change.diff:")
    for line in read_lines(ctx.mutant_dir / "change.diff"):
        if line.startswith("+") and not line.startswith("+++"):
            print("    " + green(line))
        elif line.startswith("-") and not line.startswith("---"):
            print("    " + red(line))
        else:
            print("    " + dim(line))
    show_file_ref(ctx.mutant_dir / "metadata.json")


def stage_harness(ctx):
    header(5, "Harness", "Build + test the mutant in Docker, network off, mock attacker server on")
    print(dim("  docker run --rm --network none -e TESTS=... -e WRAP_MODE=forcefallback \\"))
    print(dim("    -v harness:/work/harness:ro -v <mutant>:/work/target:ro -v <out>:/work/out \\"))
    print(dim("    pipeline-harness bash /work/harness/run_build.sh"))
    print()
    print("  inside the container: mock server :8000 → meson subprojects download →")
    print("  meson setup → meson compile → hash outputs → meson test → scan for PWNED_*")
    print()
    r1 = ctx.run(1)
    st = load_json(r1 / "status.json", {})
    kv("exit codes (run1)", "  ".join(f"{k.replace('_rc', '')}={v}" for k, v in st.items()))
    tests = read_testlog(r1 / "testlog.json")
    kv("tests", "  ".join(f"{t}:{green(r) if r == 'OK' else red(r)}" for t, r in tests.items()) or "-")
    kv("output hashes", f"{len(read_lines(r1 / 'hashes.txt'))} files hashed")
    kv("mock server", f"{len(read_lines(r1 / 'mock_server.log'))} request(s)")
    marks = read_lines(r1 / "markers.txt")
    kv("markers", ", ".join(yellow(x) for x in marks) or "none")
    n_runs = len([p for p in ctx.runs_dir.glob("run*") if p.is_dir()])
    note(f"repeated {n_runs}× to catch flaky builds")
    show_file_ref(r1)


def stage_oracle(ctx):
    header(6, "Oracle", "Diff the mutant's evidence against a clean baseline build of the same target")
    b, r1 = ctx.baseline, ctx.run(1)
    bst, mst = load_json(b / "status.json", {}), load_json(r1 / "status.json", {})
    bt, mt = read_testlog(b / "testlog.json"), read_testlog(r1 / "testlog.json")
    bm, mm = set(read_lines(b / "markers.txt")), set(read_lines(r1 / "markers.txt"))
    breq, mreq = set(read_lines(b / "mock_server.log")), set(read_lines(r1 / "mock_server.log"))
    bh = dict(reversed(l.split(None, 1)) for l in read_lines(b / "hashes.txt") if len(l.split(None, 1)) == 2)
    mh = dict(reversed(l.split(None, 1)) for l in read_lines(r1 / "hashes.txt") if len(l.split(None, 1)) == 2)

    newly_failing = [t for t, r in bt.items() if r == "OK" and mt.get(t) != "OK"]
    changed_hashes = [f for f in bh if f in mh and bh[f] != mh[f]]
    new_marks, new_reqs = sorted(mm - bm), sorted(mreq - breq)

    w = 22
    print(f"  {'check'.ljust(w)} {'baseline'.ljust(16)} {'mutant'.ljust(16)} difference")
    print(dim("  " + "─" * 68))

    def row(name, base, mut, diff):
        print(f"  {name.ljust(w)} {str(base).ljust(16)} {str(mut).ljust(16)} {diff}")

    row("setup / compile rc", f"{bst.get('setup_rc')} / {bst.get('compile_rc')}",
        f"{mst.get('setup_rc')} / {mst.get('compile_rc')}", "same" if
        (bst.get('setup_rc'), bst.get('compile_rc')) == (mst.get('setup_rc'), mst.get('compile_rc')) else red("differs"))
    row("tests passing", sum(r == "OK" for r in bt.values()), sum(r == "OK" for r in mt.values()),
        red(f"{len(newly_failing)} newly failing") if newly_failing else "none newly failing")
    row("PWNED_* markers", len(bm), len(mm), yellow(f"+{len(new_marks)} new") if new_marks else "none new")
    row("mock-server requests", len(breq), len(mreq), yellow(f"+{len(new_reqs)} new") if new_reqs else "none new")
    row("output hashes changed", "", "", yellow(f"{len(changed_hashes)} changed") if changed_hashes else "none")
    only_b, only_m = set(bh) - set(mh), set(mh) - set(bh)
    if only_b or only_m:
        print()
        print(red(f"  ! baseline and mutant hashed different outputs (+{len(only_m)} / -{len(only_b)} files):"))
        print(red("    the baseline was built with different settings (e.g. without --wrap-mode=forcefallback),"))
        print(red("    so hash comparisons are not meaningful until the baseline is rebuilt the same way."))
    print()
    print("  ladder:  setup_failed  <  setup_valid  <  build_valid  <  " + bold("effective"))
    eff = ctx.operator.get("effect") or {}
    print(f"  declared effect: {eff.get('observable', 'none')}  {json.dumps(eff.get('check', {}))}")
    print()
    v = ctx.meta.get("validity", {})
    for i, run in enumerate(v.get("runs", []), 1):
        ev = ", ".join(run.get("effect", {}).get("evidence", [])) or "-"
        print(f"  run{i}: {verdict_str(run.get('level'))}  ({run.get('reason')})  evidence: {ev}")
    flaky = v.get("flaky")
    note(f"final level = lowest of the runs → {verdict_str(v.get('level'))}"
         f"{'  (FLAKY)' if flaky else ''}")


def verdict_str(level):
    colors = {"effective": green, "build_valid": cyan, "setup_valid": yellow, "setup_failed": red}
    return bold(colors.get(level, str)(level or "unknown"))


def stage_defense(ctx):
    header(7, "Defense", "Each defense plug-in returns {blocked, flags} for the mutant")
    recs = ctx.meta.get("defenses", [])
    for d in recs:
        verdict = red("BLOCKED") if d.get("blocked") else green("ALLOWED")
        kv(d.get("name"), f"{verdict}  flags={d.get('flags')}  (recorded in metadata.json)")
    if not recs:
        print("  no defenses were enabled for this run")

    script = ROOT / "scripts" / "defenses" / "wrap_integrity_check.py"
    if script.exists():
        print()
        print("  re-running wrap_integrity_check live:")
        with tempfile.TemporaryDirectory() as td:
            man = os.path.join(td, "manifest.json")
            subprocess.run([sys.executable, str(script), "--learn", "--target", str(ctx.target),
                            "--manifest", man], capture_output=True, text=True)
            print(dim(f"    1. learn  — trusted URLs + hashes from clean {ctx.target.name}"))
            out = subprocess.run([sys.executable, str(script), "--target", str(ctx.mutant_dir),
                                  "--manifest", man], capture_output=True, text=True)
            print(dim("    2. check  — compare the mutant's wrap files to the manifest"))
            print("    " + (out.stdout.strip() or out.stderr.strip()))
    lvl = ctx.meta.get("validity", {}).get("level")
    print()
    if lvl == "effective":
        note("this mutant is effective, so this verdict counts toward the defense's score")
    else:
        note(f"this mutant is {lvl}, so by our rule it is NOT scored against defenses")


def stage_caveat(ctx):
    header(8, "Caveat", "Why the 15 wrap mutants were no-ops in this run")
    lines = read_lines(ctx.baseline / "fetch.log")
    already = [l for l in lines if "Already downloaded" in l]
    subdirs = sorted(p.name for p in (ctx.target / "subprojects").iterdir()
                     if p.is_dir() and p.name != "packagecache") if (ctx.target / "subprojects").exists() else []
    kv("unpacked deps", ", ".join(subdirs) or "none")
    kv("baseline fetch.log", f"{len(already)} × \"Already downloaded\"")
    for l in lines[:12]:
        if "Download" in l or "Already" in l:
            print("    " + dim(l.split("\x1b[K")[-1][:90]))
    print()
    note("Meson never re-reads a wrap whose dependency is already unpacked,")
    note("so edits to source_url / source_hash change nothing in the build.")
    note("fix: build from a copy without the unpacked folders (keep packagecache/).")


def stage_summary(ctx):
    header(9, "Summary", "What this one trace shows")
    m, op = ctx.meta, ctx.operator
    print(f"  {', '.join(op.get('source_attacks', []))}")
    print(f"    → operator {op.get('id')} ({op.get('target_build_phase')}, {op.get('mode')})")
    print(f"    → 1 change to {m.get('file_path')}")
    print(f"    → built + tested in Docker ×{len(m.get('validity', {}).get('runs', []))}")
    print(f"    → oracle: {verdict_str(m.get('validity', {}).get('level'))}")
    for d in m.get("defenses", []):
        print(f"    → {d['name']}: {'blocked' if d.get('blocked') else 'allowed'}")


STAGES = [stage_overview, stage_taxonomy, stage_operator, stage_placement, stage_mutant,
          stage_harness, stage_oracle, stage_defense, stage_caveat, stage_summary]


def main():
    global USE_COLOR
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mutant", default=os.environ.get("TRACE_MUTANT", DEFAULT_MUTANT))
    ap.add_argument("--benchmark", default=os.environ.get("TRACE_BENCHMARK", "data/benchmark"))
    ap.add_argument("--baseline", default=os.environ.get("TRACE_BASELINE", "data/evaluation/baseline"))
    ap.add_argument("--target", default="data/targets/git")
    ap.add_argument("--stage", type=int, action="append",
                    help="stage number(s) to show (repeatable); default all")
    ap.add_argument("--pause", action="store_true", help="wait for Enter between stages")
    ap.add_argument("--color", choices=["auto", "always", "never"],
                    default=os.environ.get("TRACE_COLOR", "auto"))
    args = ap.parse_args()
    USE_COLOR = {"always": True, "never": False}.get(args.color, sys.stdout.isatty())

    ctx = Ctx(args)
    stages = args.stage or list(range(len(STAGES)))
    for i, n in enumerate(stages):
        STAGES[n](ctx)
        if args.pause and i < len(stages) - 1:
            input(dim("\n  [Enter] next stage "))
    print()


if __name__ == "__main__":
    main()
