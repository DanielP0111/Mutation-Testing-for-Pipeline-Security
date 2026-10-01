# src/

**Purpose:** All Python source code for the project — the Meson parser, mutation engine, and placement algorithms.

Nothing gets hardcoded here with project-specific values. The code reads its inputs (operator specs, build files, placement parameters) from `data/` and writes its outputs (mutants, results) back to `data/`. This keeps the code reusable across all three target projects.

---

## Structure

```
src/
├── parser/
│   ├── meson_parser.py       # Reads meson.build files and extracts their structure
│   └── wrap_parser.py        # Reads .wrap dependency files
│
├── placement/
│   ├── dependency_aware.py   # Finds injection sites in dependency declarations
│   ├── config_aware.py       # Finds injection sites in conditional (if/endif) blocks
│   ├── adversarial.py        # Combines both for high-difficulty placements
│   ├── difficulty.py         # Assigns a difficulty rating (1–4) to each candidate site
│   └── placer_api.py         # Unified interface: given a project + operator → placement candidates
│
├── engine/
│   ├── mutant_generator.py   # Applies an operator at a chosen location; writes the mutant
│   └── template_filler.py    # Fills {{PLACEHOLDER}} fields in operator specs with real values
│
└── requirements.txt          # Python package dependencies (e.g., pyyaml, lark)
```

---

## What Each File Does

### `parser/meson_parser.py`
Reads a `meson.build` file and extracts a structured description of its contents: what dependencies are declared, what conditional blocks exist, and where the key parts are located (which line numbers). The placement algorithms use this to find potential injection sites.

**Owner: Daniel** — write this first; everything else depends on it.

### `parser/wrap_parser.py`
Reads a Meson `.wrap` file (found in the `subprojects/` folder of any Meson project) and extracts its fields: the download URL, expected file hash, and patch directory. Wrap files are a primary target for dependency-injection attacks.

**Owner: Daniel**

### `placement/dependency_aware.py`
Looks at the dependency graph of a project — every library it downloads — and finds spots where a URL-replacement or dependency-poisoning attack could be injected. Uses `meson introspect` and the wrap parser to map dependencies.

**Owner: David**

### `placement/config_aware.py`
Scans `meson.build` files for `if`/`elif`/`endif` conditional blocks and ranks them as injection candidates. Injecting inside a rarely-triggered branch is a common evasion technique.

**Owner: David**

### `placement/adversarial.py`
Combines dependency and configuration data to find compound injection sites — places that are both dependency-related and inside a conditional, making detection harder.

**Owner: David**

### `placement/difficulty.py`
Given a candidate injection site, returns a difficulty rating (1–4):
- **1 (Trivial):** Obvious change in a visible, frequently-executed location
- **2 (Moderate):** Less visible location, plausible-looking value
- **3 (Difficult):** Inside a conditional or rarely-executed path
- **4 (Sophisticated):** Multi-layered evasion; mirrors legitimate build patterns closely

**Owner: David**

### `placement/placer_api.py`
The single entry point the engine calls. Takes a project path and an operator spec, and returns a list of placement candidates across all three schemes. The engine picks from this list.

**Owner: David**

### `engine/mutant_generator.py`
The core transformation. Takes a parsed build file, an operator spec, and a chosen placement location, and produces a modified copy of the build file with the attack injected. Writes the result to `data/benchmark/`.

**Owner: Daniel**

### `engine/template_filler.py`
Operator specs use `{{PLACEHOLDER}}` fields instead of hard-coded values (e.g., `{{WRAP_FILE}}`, `{{MALICIOUS_URL}}`). This module resolves those placeholders using real values from the target project being mutated.

**Owner: Daniel**

---

## How the Pieces Connect

```
meson_parser.py  ──┐
wrap_parser.py   ──┼──► placer_api.py ──► mutant_generator.py ──► data/benchmark/
operator spec    ──┘         │
                     template_filler.py
```

1. Parser reads the target project's build files.
2. Placer finds candidate injection sites (using all three schemes).
3. Template filler resolves the operator's placeholder fields with real values.
4. Mutant generator applies the transformation and writes the output.

---

## Running the Engine

```bash
# Single mutant (for development and testing)
python scripts/generate_mutant.py \
  --project data/targets/git \
  --operator data/operators/OP-001-wrap-url-replacement.yaml \
  --scheme dependency_aware \
  --difficulty 2

# Full benchmark
bash scripts/generate_benchmark.sh
```

---

## Dependencies

Install with:

```bash
pip install -r src/requirements.txt
```

Key packages:
- `pyyaml` — reading operator spec YAML files
- `lark` — parsing Meson build file syntax (grammar-based parser)
- `pytest` — running the test suite in `tests/`
