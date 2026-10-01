# data/

**Purpose:** All data files for the project — attack records, operator specs, the target Meson projects, generated mutants, and evaluation results.

The code in `src/` reads from here and writes back here. Nothing in this folder is meant to be run directly.

---

## Structure

```
data/
├── taxonomy/                     # Rejoice — real-world attack records
│   ├── attacks.json              # Primary database: 50+ attack records
│   ├── attacks.csv               # Same data as a spreadsheet
│   └── sources.md                # Bibliography of sources used
│
├── operators/                    # Debora — mutation operator specs
│   ├── index.json                # Catalog of all operators
│   ├── OP-001-wrap-url-replacement.yaml
│   ├── OP-002-configure-branch-injection.yaml
│   └── ...                       # One file per operator (15+ total)
│
├── targets/                      # The 3 Meson projects used as test subjects
│   ├── setup_notes.md            # Which versions to clone and why
│   ├── git/                      # git source (cloned by scripts/setup_targets.sh)
│   ├── numpy/                    # NumPy source (cloned by scripts/setup_targets.sh)
│   └── scipy/                    # SciPy source (cloned by scripts/setup_targets.sh)
│
├── benchmark/                    # Daniel — auto-generated mutant files
│   ├── index.json                # Master catalog of all 500+ mutants
│   ├── git/                      # Mutants for the git project
│   ├── numpy/                    # Mutants for the NumPy project
│   └── scipy/                    # Mutants for the SciPy project
│
└── evaluation/                   # Phase 5 — PipelineSave results
    ├── results.csv               # Raw results: one row per mutant
    └── results_annotated.json    # index.json with outcomes filled in
```

---

## data/taxonomy/

**Owner: Rejoice.** Contains structured records of real-world pipeline attacks that have actually happened. These feed into the operator design process.

Each entry in `attacks.json` looks like this:

```json
{
  "id": "ATK-001",
  "name": "XZ Utils Backdoor",
  "year": 2024,
  "cve": "CVE-2024-3094",
  "source_url": "https://nvd.nist.gov/vuln/detail/CVE-2024-3094",
  "build_phase": "configure",
  "attack_vector": "Malicious autoconf macro injected via upstream maintainer compromise",
  "dataflow_pattern": "code_insertion",
  "detection_difficulty": 4,
  "notes": "Conditional activation based on environment; only triggered in specific build contexts"
}
```

**`build_phase`** must be one of: `fetch`, `configure`, `compile`, `test`, `package`  
**`detection_difficulty`** is 1 (obvious) to 4 (very stealthy)

**Goal:** ≥ 50 records by Oct 28, covering all 5 build phases.

---

## data/operators/

**Owner: Debora.** Contains mutation operator specification files — abstract, reusable attack templates.

Each `.yaml` file describes one operator. Example:

```yaml
id: OP-001
name: Wrap URL Replacement
build_phase: fetch
dataflow_pattern: dependency_injection
difficulty_range: [1, 3]
description: >
  Replaces a legitimate dependency download URL in a Meson wrap file
  with an attacker-controlled URL.
attack_taxonomy_ids: [ATK-007, ATK-019]
template:
  target_file: "{{WRAP_FILE}}"
  target_field: "source_url"
  replacement: "{{MALICIOUS_URL}}"
placeholders:
  WRAP_FILE:
    description: Path to the .wrap file to modify
    type: file_path
  MALICIOUS_URL:
    description: Attacker-controlled URL
    type: url
    example: "https://evil.example.com/malicious-zlib.tar.gz"
```

`{{PLACEHOLDER}}` fields get filled in by `src/engine/template_filler.py` at generation time with real values from the target project.

**Goal:** ≥ 15 operators by Nov 18, covering all build phases.

---

## data/targets/

**Shared setup.** The three open-source projects used as test subjects. They are not committed to the repo — they are cloned locally by running `bash scripts/setup_targets.sh`.

| Project | Why we use it |
|---|---|
| **git** | Rich set of `.wrap` dependency files; good for fetch-phase attacks |
| **NumPy** | Complex C/Cython build with many configuration branches |
| **SciPy** | Most complex Meson configuration of the three; many platform-detection branches |

All three use Meson as their build system, which is what our engine targets.

---

## data/benchmark/

**Owner: Daniel (auto-generated).** Do not add files here by hand. The engine writes all mutants here via `bash scripts/generate_benchmark.sh`.

Each mutant gets its own subdirectory named `{operator}_{scheme}_{difficulty}_{id}/`. Inside:
- The modified build file(s) (e.g., a patched `meson.build` or `.wrap` file)
- A `mutant.json` metadata file

`index.json` is the master catalog — one entry per mutant, tracking operator, scheme, difficulty, project, and (after evaluation) the PipelineSave outcome.

**Goal:** ≥ 500 labeled mutants by Dec 2.

---

## data/evaluation/

**Shared (Phase 5).** Written by `scripts/run_evaluation.py` after PipelineSave is run against the benchmark.

`results.csv` has one row per mutant:
```
mutant_id, project, operator_id, scheme, difficulty, pipelinesave_result
git-OP001-dep-d1-001, git, OP-001, dependency_aware, 1, MISSED
```

`pipelinesave_result` is one of: `BLOCKED`, `DETECTED`, `MISSED`
