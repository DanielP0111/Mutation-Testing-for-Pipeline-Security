# Placement Rules — Dependency-Aware Scheme

Owned by David, ask if any questions arise. Documents the preconditions and dataflow 
constraints for `src/placement/dependency_aware.py`, verified against real Meson projects
(GLib 2.80.0) and a minimal isolated reproduction, both run with Meson 1.12.1.

## What this scheme targets

Dependency-aware placement looks only at `parsed_project["wrap_files"]` —
the supply-chain surface where a `.wrap` file controls what code a
`dependency()` fallback pulls into the build. It does not yet use
`parsed_project["dependencies"]` (name-based targeting of plain
`dependency()` calls with no wrap backing them); that's a natural extension
once config-aware placement (Phase 3) needs it too.

## Preconditions

1. **A field only applies to the wrap type that actually has it.**
   `source_url` and `source_hash` are literal lines inside a `[wrap-file]`
   section. `wrap_parser.py` also *synthesizes* a `source_url` value for
   `[wrap-git]` entries (copied from their `url =` line) so downstream code
   has one uniform field to read — but that value is never an actual
   `source_url = ...` line in the file. Treating it as a candidate would
   silently rewrite a git clone URL under the wrong field name, which
   doesn't match what the operators themselves state as a precondition
   ("project has at least one `[wrap-file]` subproject with a `source_url`"),
   and meson would then try to `git clone` the attacker URL instead of
   downloading it — which hangs rather than failing fast.
   The first pass didn't filter by wrap type, and
   running the real pipeline against GLib (which has 6 `[wrap-git]` entries
   alongside 2 `[wrap-file]` ones) generated 8 URL-swap candidates instead of
   2, and `meson setup --validate` hung for 2+ minutes trying to git-clone
   bogus URLs for the wrap-git entries. Fixed by restricting `source_url` /
   `source_hash` candidates to `wrap["type"] == "wrap-file"`.

2. **The operator's `scheme` must match.** `find_dependency_candidates()`
   returns `[]` immediately for any operator whose `scheme` isn't
   `dependency_aware` or `all` — config-aware and adversarial operators are
   not this module's job.

3. **The wrap must actually have the targeted field set.** A `[wrap-file]`
   entry with no `source_hash` line (legal — the field is optional in the
   wrap format) is not a candidate for a hash-field operator.

## Dataflow constraint: op_001 alone does not produce a valid mutant

This is the real, verified dependency the PDF asked me to document — and
the mechanism turned out to be slightly different from what op_002's own
description assumes, which is worth flagging to Debora.

**Setup:** a minimal Meson project with a `required: true` dependency
falling back to a `[wrap-file]` subproject, tested two ways: against real
GLib wrap files, and against an isolated local wrap (so the result doesn't
depend on network access to an attacker-controlled domain, which this
environment can't reach anyway).

**op_001 alone (URL swapped, `source_hash` left unchanged):**
`meson setup` fails outright —
```
ERROR: Incorrect hash for source:
 <original hash> expected
 <new content's hash> actual.
```
A URL swap by itself is caught by
Meson's own integrity check, because the `source_hash` field still names
the *original* file's hash, and the substituted content doesn't match it.

**op_002 alone, or op_001 + op_002 (`source_hash` deleted entirely):**
this is where the behavior differs from op_002's stated description
("Meson skips integrity verification when `source_hash` is absent"). On
**Meson 1.12.1** (current, `pip install meson`), that's no longer true —
`source_hash` is a required key for a `[wrap-file]` section, and omitting
it is a hard configure error:
```
ERROR: Missing key 'source_hash' in mylib.wrap
```
Deleting the hash doesn't bypass verification on current Meson — it
continues to fail. **This looks like an operator spec written
against older Meson semantics; possibly tell Debora**,

**What actually produces a valid, undetected-by-Meson mutant:** swapping
`source_url` to attacker-controlled content *and* recomputing `source_hash`
to match that new content's real sha256 (verified directly: `meson setup`
then succeeds and resolves the dependency to the substituted subproject).
That's the real operator pairing this benchmark needs — op_001 plus a
hash-*recompute* step, not a hash-*removal* step. Not built as that's
Debora's and Daniel's layer, not placement, but placement candidates expose 
both `source_url` and `source_hash` as independently targetable fields, 
so the engine can already combine them once the operator spec is updated.

## Environment constraint: a satisfied system dependency hides the wrap entirely

Found while testing against real GLib: both of its `[wrap-file]` entries
(`zlib`, `pcre2`) are also available as system packages in this build
environment (`zlib1g-dev`, `libpcre2-dev`). When `dependency('zlib', ...)`
finds a system library via pkg-config, Meson **never reads the wrap file at
all** — the fallback branch isn't taken, so mutating `zlib.wrap` has zero
effect on `meson setup`, and the mutant reports `setup-valid` for a reason
that has nothing to do with the mutation surviving review. It was simply
never exercised.

A "setup-valid" result on a dependency-aware mutant
only means something if the target's build is actually forced through the
fallback path (e.g. `--wrap-mode=forcefallback`, or a target/dependency
pair where no system package satisfies the dependency). Otherwise the
benchmark will silently undercount how often these mutations are even
tested, let alone caught.

## Verified end-to-end against GLib 2.80.0

With the type-filter fix in place:

```
$ python scripts/run_pipeline.py --target data/targets/gnome-glib \
    --operators data/operators --out data/benchmark --validate
generated 4 mutant(s): 4 applied, 4 setup-valid
  - gnome-glib_wrap_source_url_swap_0001  (subprojects/pcre2.wrap)
  - gnome-glib_wrap_source_url_swap_0002  (subprojects/zlib.wrap)
  - gnome-glib_wrap_hash_removal_0003     (subprojects/pcre2.wrap)
  - gnome-glib_wrap_hash_removal_0004     (subprojects/zlib.wrap)
```
All 4 report `setup-valid` here. Per the environment constraint above,
that's because this machine's system zlib/pcre2 satisfy the dependency
before Meson ever looks at the wrap, not because the mutations would
survive a forced fallback. NumPy's wraps were not checked yet (not cloned
in this pass); same type-filtering logic applies.

## Extending this module later

`_FIELD_PLACEHOLDERS` and `_WRAP_FILE_ONLY_FIELDS` at the top of
`dependency_aware.py` are the two places a new wrap-field operator needs to
touch. Scanning `parsed_project["dependencies"]` for name-based targeting
(e.g. an operator that doesn't care which specific wrap, just "some
dependency by this name") is the planned extension once it's needed.
