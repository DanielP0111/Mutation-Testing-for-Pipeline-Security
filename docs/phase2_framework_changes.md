# Phase 2 framework changes (Daniel)

What landed in the engine this round, and what Debora/David need to know.

## New capability
- **Operators load from JSON or YAML** (`src/engine/operator_loader.py`). Debora's
  JSON schema is the source of truth; YAML still works for quick drafts.
- **Three change modes** in the generator: `replace`, `delete_line`, `insert_after`.
- **Mutant validation** (`src/engine/validator.py`): runs `meson setup` on each
  mutant; a mutant is "setup-valid" when Meson configures it (exit 0).
- **End-to-end driver** (`scripts/run_pipeline.py`): parse → place → fill →
  generate → validate → write `metadata.json` + `change.diff` per mutant.
- **Offline demo target** (`data/targets/demo_app/`) so the pipeline runs with no
  network and no large clones.

## Schema v2 (`data/schemas/operator_schema.json`) — Debora
Added the fields the engine reads, on top of the original six:
`name`, `scheme`, `mode`, structured `injection_location {file_glob, field}`,
`placeholders`, `attacker_values`, and `template {file_path, replacement_value}`.
`target_build_phase` is now an enum of the 5 phases
(`dependency_fetch | configure | compile | test | package_release`).
Two worked operators are in `data/operators/` (op_001 URL swap, op_002 hash
removal) — use them as templates for the rest.

## Placement — David
`src/placement/dependency_aware.py` etc. are still the real home for placement.
Until they're implemented, the driver falls back to
`src/engine/reference_placement.py` (dependency-aware wrap fields only) when run
with `--reference-placement`. Your `find_dependency_candidates()` must return the
same candidate shape (`scheme, file_path, field, current_value, placeholder_map`);
once it does, drop the flag and the driver uses your code with no other change.

## Parser additions
`parse_project()` now also returns `build_calls` (custom_target / run_command /
generator / subproject) and `option_reads` (get_option names) — the hook-point
surfaces from your Meson doc, ready for config-aware placement.
`wrap_parser` now handles `[wrap-git]` (url, optional directory) and reports a
`type` field.

## Run it
```bash
pip install -r src/requirements.txt && pip install meson ninja
pytest tests/ -v                     # 33 tests
python scripts/run_pipeline.py --target data/targets/demo_app \
  --operators data/operators --out data/benchmark --validate --reference-placement
```
