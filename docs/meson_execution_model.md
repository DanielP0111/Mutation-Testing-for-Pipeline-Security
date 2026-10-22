# Meson Execution Model, Wrap System & Injection Hook Points

Phase 1 deliverable for the *Adversarial Mutation Testing of Build-Pipeline Security Defenses* project. It explains how Meson executes a build, how it fetches dependencies through the wrap system, and how configuration branches change what gets built. It also maps where in that pipeline a mutation (a planted attack) can realistically be placed.

## 1. Meson's Execution Model

Meson splits a build into two sharply different kinds of work: a **configure stage** that reads the system and the project's `meson.build` files and writes a fixed plan, and a **compile/install stage** to execute that plan. This split matters for security, as anything added in at configure time (a resolved dependency, an evaluated `if` branch, a generated file list) will now quietly propagate into every later stage without further review.

1. **Parse**: `meson setup` reads every `meson.build` top to bottom, in Meson's own declarative DSL. Calls like `project()`, `dependency()`, `executable()`, and `custom_target()` are *recorded*, not yet run.
2. **Resolve options**: `get_option()` calls are filled in from `meson_options.txt` / `meson.options` defaults, overridden by any `-Dname=value` flags passed to `meson setup`. These values are cached in the build directory.
3. **Fetch dependencies (wrap resolution)**: any `dependency()` call that falls back to a subproject with a matching `.wrap` file triggers Meson's wrap system to download, verify, and extract that subproject (full detail in Section 2).
4. **Run configure-time checks**: compiler detection, header/library checks (`compiler.has_header()`, `dependency()` lookups via pkg-config), and feature probing. Results are baked into the build graph.
5. **Write `build.ninja`**: `meson setup` finishes by emitting the complete, fixed dependency graph for the build. Nothing from here on re-reads `meson.build` unless setup is re-run.
6. **Compile**: `ninja` (or `meson compile`) walks `build.ninja`. Compilers and linkers run, and any `custom_target()` steps execute here, not at configure time.
7. **Test**: `meson test` runs the project's declared tests against the compiled artifacts.
8. **Install**: `meson install` copies the installable outputs to the target prefix, optionally running `meson.add_install_script()` hooks.

**Stages 1–4 (configure) are mainly decision-making phases**, while stages 6–8 (compile/test/install) are meant to carry them out. Actions like a mutation placed in `meson.build`, a wrap file, or an option branch during configure will eventually reach compile, test, and install. This is why those configure-time artifacts are the highest-value hook points (Section 4).

## 2. Wrap System

The wrap system is Meson's dependency-fetch mechanism. Its rough equivalent would be pip or npm, but for subprojects (C/C++ libraries) that a project vendors directly into its source tree instead of linking against a system install. It's the most attack-relevant part of Meson's pipeline, because it is exactly the mechanism XZ Utils and similar real-world attacks have exploited. A wrap file decides what code enters the build and where it comes from.

**The wrap file** is named `<name>.wrap`, placed in the parent project's `subprojects/` directory. Related local files go in `subprojects/packagefiles/` (local archives, overlay directories, diff files), and downloaded archives are cached in `subprojects/packagecache/`.

**Structure (INI format):**

- **Type header**: exactly one of `[wrap-file]`, `[wrap-git]`, `[wrap-hg]`, `[wrap-svn]`.
- **Common fields**: `directory` (the subproject's folder name), `patch_url` / `patch_filename` / `patch_hash` (a downloaded overlay archive, usually supplying the Meson build definition the upstream project lacks), `patch_directory` (a local overlay), `diff_files`, `method` (`meson`, `cmake`, or `cargo`).
- **`[wrap-file]` fields**: `source_url` / `source_fallback_url` (download locations), `source_filename`, `source_hash` (a sha256 checksum, skipped if absent).
- **`[wrap-git]` fields**: `url` and `revision` (both required), and in addition `depth`, `push-url`, `clone-recursive`.
- **`[provide]` section**: lets a plain `dependency('foo')` call automatically fall back to this wrap without the caller naming it explicitly.

**Resolution sequence** (happens during `meson setup`, triggered the first time a `dependency()` call needs this wrap):

1. **Fetch**: download `source_url`, falling back to `source_fallback_url`, or use a cached/local `source_filename`.
2. **Verify**: check against `source_hash`, *only if that field is set*.
3. **Extract**: unpack into `subprojects/<directory>`.
4. **Overlay**: apply the `patch_*` archive or `patch_directory`, which commonly injects the Meson build files for an upstream project that doesn't ship its own.
5. **Diff**: apply any `diff_files` with `patch -p1` or `git`.
6. **Build as a normal subproject**: from here, fetched code is indistinguishable from hand-written project source; it compiles and links like everything else.

## 3. Configuration Branches

Meson projects declare tunable options in `meson_options.txt`, or `meson.options` in newer Meson. Each option has a type, those being boolean, combo, feature, string, or array, and a default. `meson.build` then reads them with `get_option('name')` and uses the result inside `if` / `elif` / `endif` blocks to conditionally add source files, dependencies, or `custom_target()` steps.

- **The value comes from**: an option's default, overridden by `-Dname=value` on `meson setup`, or changed later with `meson configure -Dname=value` (re-triggers the relevant parts of configure without a full re-setup).
- **Inspecting the current configuration**: `meson introspect --buildoptions builddir` lists every option and its current value for a given build directory.
- Because branches are evaluated once, at configure time, any mutation hidden inside `if get_option('some_feature') ... endif` only ever executes (and only ever gets exercised by a defense tool) if that option is actually enabled for the build being tested. An attack planted in a branch that nobody turns on is invisible but untested, and thus will tells us nothing about a defense's real effectiveness. This is the problem configuration-aware placement (from Phase 3) exists to solve. Verifying that an injection point sits inside a branch that is reachable under at least one realistic and valid configuration of the target project, before counting it as part of the benchmark.

## 4. Hook Point Map

Each row is a place in the Section 1 pipeline where a potential real-world-style mutation can be planted, which build phase it belongs to, and the known attack pattern it corresponds to. The plan is for these to map directly onto Rejoice's attack-category taxonomy, and become the `injection_location` values in Debora's operator schema.

| Build Phase | Hook Point | What Could Be Changed | Matches Attack Category |
| --- | --- | --- | --- |
| Parse | `command=` argument of `custom_target()`, `run_command()`, or `generator()` in `meson.build` | Append an extra shell command alongside the legitimate one | Command injection |
| Parse | `environment()` calls setting `PATH`, `LD_LIBRARY_PATH`, or passing through secrets | Leak environment variables (API keys, tokens, SSH keys) during the build | Environment exfiltration |
| Resolve options | `if get_option('x') ... endif` branches | Plant a mutation inside a branch that is config-gated and rarely exercised | Configuration-aware placement |
| Fetch dependencies | `url=` / `source_url=` line in `subprojects/*.wrap` | Swap to a lookalike or attacker-controlled domain | Dependency URL substitution (XZ Utils) |
| Fetch dependencies | `source_hash` field — or its absence | Omit or weaken the checksum so a tampered archive passes unflagged | Supply-chain integrity bypass |
| Fetch dependencies | `patch_url` / `patch_directory` overlay | Inject malicious build files during the overlay step, invisible in the upstream source tree itself | Overlay/patch injection |
| Compile | Output of a `custom_target()` generator step | Have a generated source file produce backdoored output only at build time | Build-time code generation tampering (SolarWinds-style) |
| Test | Test command, script, or fixture data | Corrupt the test oracle so malicious behavior passes CI | Test-input attack (hides detection) |
| Install | `install_data()` / `meson.add_install_script()` | Install something different from what was compiled and tested | Final-stage substitution |

## Notes for team members:

This document contains a direct input to three teammates:

- **David:** hook points above are what gets turned into dependency graphs per attack, and into the first dependency-aware placement script.
- **Debora:** the "Matches Attack Category" column lines up with your operator catalog's categories, and each hook point's file/field description is a ready-made `injection_location` value for the operator schema.
- **Daniel:** your parser specifically looks for lines containing `dependency(`, `subproject(`, `custom_target(`, or `url =` in wrap files. These are hook points 1, 4, and 7 above, confirming that the engine and this map are aligned before more work is built.

Ref: [Wrap dependency system manual](https://mesonbuild.com/Wrap-dependency-system-manual.html) · [Understanding Meson (NumPy docs)](https://numpy.org/devdocs/building/understanding_meson.html)
