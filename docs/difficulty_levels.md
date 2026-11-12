# Difficulty / Obfuscation Scale

Owned by David. Implemented in `src/placement/difficulty.py`
(`assign_difficulty`). Scores how hard a placed mutation is for a defense
tool or human reviewer to notice — not how damaging it is. 

## The four levels

| Level | Meaning | Who it maps to in this codebase |
|-------|---------|----------------------------------|
| 1 | Main code path, no guards, obvious field — e.g. a top-level `source_url` or `source_hash` in a `[wrap-file]` entry. Anyone reading the file sees it, it executes on every build. | `dependency_aware` candidate, `field` in `{source_url, source_hash}` |
| 2 | Either inside exactly one (unnested) conditional branch, or targeting a non-obvious field. The attack only runs under one gating condition, or isn't the field a reviewer would think to check first. | `dependency_aware` candidate with a field other than `source_url`/`source_hash`; **or** `config_aware` candidate at nesting depth 1 |
| 3 | Nested conditional (depth >= 2) — the branch only executes when *two or more* conditions line up (e.g. `if linux and if feature-x`) — or an adversarial placement that combines a dependency-surface change with a conditional guard. | `config_aware` candidate at depth >= 2; any `adversarial` candidate |
| 4 | Deeply nested *and* platform-specific, sitting in a branch that's rarely exercised in practice. Hardest to find by reading, and easy to miss in CI if that platform/option combination isn't part of the normal test matrix. | `config_aware` or `adversarial` candidate with depth >= 2 **and** a platform guard (e.g. `host_machine.system() == 'windows'`) |

## Why nesting and platform-guards drive the scale and not just scheme

A reviewer (or an automated defense like Foreman) scanning a build file
reads top to bottom. A top-level assignment is seen on the first pass. A
single `if` branch is still something a reviewer who reads the whole file
will hit. A *nested* branch — `if host_machine.system() == 'linux' /
if get_option('feature-x') / <injection> / endif / endif` — requires both
conditions to be true simultaneously to even execute, so:

- it's less likely to be exercised during ordinary CI runs that don't set
  every option combination, which is exactly the "planted but never
  tested" risk flagged in `docs/meson_execution_model.md`;
- a reviewer has to mentally track two levels of state to realize the
  branch is reachable at all;
- a defense tool that only instruments the default build configuration
  (most do) will simply never execute that code path, so it reports
  nothing to analyze.

Platform-specificity compounds this: a `windows`-only branch is invisible
to a review or CI pipeline running only on Linux, independent of nesting.

## Worked examples

```
# Level 1 — op_001 target
[wrap-file]
source_url = https://zlib.net/zlib-1.3.tar.gz   # <- literal, top-level, obvious field
```

```meson
# Level 2 — single, unnested conditional (tests/fixtures/conditional.meson.build)
if host_machine.system() == 'linux'
  linux_dep = dependency('liburing', required : true)   # depth 1
endif
```

```meson
# Level 3 — nested conditional (same fixture, inner block)
if host_machine.system() == 'linux'
  if get_option('feature-x')
    extra_dep = dependency('libfoo', required : false)  # depth 2
  endif
endif
```

```meson
# Level 4 — nested AND platform-guarded
if host_machine.system() == 'windows'
  if get_option('feature-y')
    # depth 2, platform_guard = 'windows' -> difficulty 4
  endif
endif
```

## How a candidate carries this information

`assign_difficulty(candidate, parsed_project)` reads:

- `candidate["scheme"]` — `dependency_aware`, `config_aware`, or
  `adversarial`.
- `candidate["field"]` — for `dependency_aware`, whether it's one of the
  "obvious" wrap fields (`source_url`, `source_hash`) or something else.
- `candidate["depth"]` and `candidate["platform_guard"]` — for
  `config_aware`/`adversarial`, the nesting depth and (if any) the
  platform the branch is guarded on. These are produced by
  `config_aware.analyze_branch_reachability()`, which is implemented and
  tested (see `tests/test_placement.py`), but is not currently wired into
  `find_config_candidates()` — see **`docs/config_aware_status.md`** for
  why, and what the team/instructor need to decide before that's turned
  on. Until it is, no real `config_aware` candidates flow through the
  live pipeline, so `assign_difficulty`'s `config_aware`/`adversarial`
  branch is exercised today only by direct unit tests with synthetic
  candidate dicts, not by `scripts/run_pipeline.py` runs.

## Precedent in the dependency-aware scheme

`data/placement_rules.md` already noted (Phase 2) that a `dependency_aware`
mutant can report `setup-valid` for reasons that have nothing to do with
the mutation surviving review — e.g. a system package satisfying the
dependency before Meson ever reads the wrap. The same caution applies here:
a `config_aware` mutant's difficulty rating describes how hard the
*placement* is to spot, not whether the branch is actually exercised by a
given CI run. `analyze_branch_reachability()`'s reachability verdict is the
piece that answers the second question, and the two should be reported
together once real `config_aware` candidates exist.
