# scripts/

**Purpose:** Helper scripts for setup tasks, running the benchmark generator, and executing the PipelineSave evaluation. These are one-off or batch operations that don't belong in the reusable library code in `src/`.

---

## Files

| Script | What it does | When to run it |
|---|---|---|
| `setup_targets.sh` | Clones the three target Meson projects at pinned versions | Once, at the start of the project |
| `generate_mutant.py` | Generates a single mutant (for testing the engine during development) | During Phase 2 and 3 development |
| `generate_benchmark.sh` | Runs the full benchmark generation — all projects × operators × schemes | Once in Phase 4 when the engine is complete |
| `setup_pipelinesave.sh` | Installs and configures PipelineSave | Once at the start of Phase 5 |
| `run_evaluation.py` | Runs PipelineSave against every mutant in `data/benchmark/` and writes results to `data/evaluation/` | Once in Phase 5 |

---

## `setup_targets.sh`

Clones git, NumPy, and SciPy at specific, pinned commit hashes so every team member works with identical code:

```bash
bash scripts/setup_targets.sh
```

After running this you will have:
- `data/targets/git/` — git source
- `data/targets/numpy/` — NumPy source
- `data/targets/scipy/` — SciPy source

The target project source trees are listed in `.gitignore` — they are large and should not be committed. Run this script whenever you set up a new machine or fresh clone.

---

## `generate_mutant.py`

Generates one mutant for a specific combination of project, operator, scheme, and difficulty. Use this while the engine is under development to test that it works correctly before running the full benchmark.

```bash
python scripts/generate_mutant.py \
  --project data/targets/git \
  --operator data/operators/OP-001-wrap-url-replacement.yaml \
  --scheme dependency_aware \
  --difficulty 2 \
  --out data/benchmark/git/
```

Output: a new subdirectory in `data/benchmark/git/` with the modified build file and a `mutant.json` metadata file.

---

## `generate_benchmark.sh`

Runs the full benchmark generation pipeline. Loops over all three projects, all operator specs in `data/operators/`, all three placement schemes, and all four difficulty levels, skipping invalid combinations (e.g., an operator that requires a wrap file, applied to a project with no wrap files).

```bash
bash scripts/generate_benchmark.sh
```

This calls `src/engine/mutant_generator.py` repeatedly and also updates `data/benchmark/index.json` with an entry for every generated mutant.

**Warning:** This may take a while on the first run. Run it only when the engine and all operators are complete (end of Phase 4).

---

## `setup_pipelinesave.sh`

Downloads and installs PipelineSave in the local environment so that `run_evaluation.py` can call it. Run this once at the beginning of Phase 5 (week of Dec 3).

```bash
bash scripts/setup_pipelinesave.sh
```

Check the script comments for any configuration needed (e.g., an API key or specific install path).

---

## `run_evaluation.py`

Reads every entry in `data/benchmark/index.json`, runs PipelineSave against each mutant's build files, and records the outcome (`BLOCKED`, `DETECTED`, or `MISSED`).

```bash
python scripts/run_evaluation.py \
  --index data/benchmark/index.json \
  --targets data/targets/ \
  --out data/evaluation/results.csv
```

After this completes:
- `data/evaluation/results.csv` has one row per mutant with the PipelineSave outcome.
- `data/evaluation/results_annotated.json` is `index.json` with the `pipelinesave_result` field filled in.

This script may take a significant amount of time depending on how many mutants are in the benchmark and how fast PipelineSave runs. Consider running it overnight.
