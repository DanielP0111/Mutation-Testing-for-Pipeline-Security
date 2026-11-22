# Benign Build-Script Commit Baseline (Corpus: 32 Commits)

To evaluate the false-positive rate and specificity of PipelineSave, we curated **32 verified non-malicious commits** modifying `meson.build` across the benchmark's two active Meson target projects (`git` and `gnome-glib`).

| ID | Project | Commit | Target File | Change Type | Description |
| :--- | :---: | :---: | :--- | :--- | :--- |
| BEN-001 | **git** | [`4315717`](https://github.com/git/git/commit/4315717) | `meson.build` | `source_addition` | connected: add incremental connectivity check via rev-list |
| BEN-002 | **git** | [`cc839a9`](https://github.com/git/git/commit/cc839a9) | `meson.build` | `test_target_optimization` | meson: don't recompile git-remote-http(1) multiple times for tests |
| BEN-003 | **git** | [`d9e19a5`](https://github.com/git/git/commit/d9e19a5) | `meson.build` | `build_target_optimization` | meson: avoid recompiling HTTP sources several times |
| BEN-004 | **git** | [`cae5d9e`](https://github.com/git/git/commit/cae5d9e) | `meson.build` | `platform_build_config` | mingw: allow git.exe to be used instead of the Git wrapper |
| BEN-005 | **git** | [`86c0e33`](https://github.com/git/git/commit/86c0e33) | `meson.build` | `compat_source_addition` | compat/posix: introduce writev(3p) wrapper |
| BEN-006 | **git** | [`12a19ee`](https://github.com/git/git/commit/12a19ee) | `meson.build` | `source_addition` | transport: add client support for object-info |
| BEN-007 | **git** | [`8fe629c`](https://github.com/git/git/commit/8fe629c) | `meson.build` | `fuzzer_build_support` | meson: support building fuzzers with libFuzzer |
| BEN-008 | **git** | [`18a81af`](https://github.com/git/git/commit/18a81af) | `meson.build` | `source_list_fix` | meson: restore hook-list.h to builtin_sources |
| BEN-009 | **git** | [`c71a121`](https://github.com/git/git/commit/c71a121) | `meson.build` | `subsystem_refactor` | packfile: move packed source into odb/ subsystem |
| BEN-010 | **git** | [`cf86a18`](https://github.com/git/git/commit/cf86a18) | `meson.build` | `source_addition` | packfile: split out packfile list logic |
| BEN-011 | **git** | [`814f039`](https://github.com/git/git/commit/814f039) | `meson.build` | `subsystem_refactor` | odb/source-loose: move loose source into odb/ subsystem |
| BEN-012 | **git** | [`032d403`](https://github.com/git/git/commit/032d403) | `meson.build` | `source_addition` | odb: introduce in-memory source |
| BEN-013 | **git** | [`6f07f4d`](https://github.com/git/git/commit/6f07f4d) | `meson.build` | `header_refactor` | odb: split struct odb_transaction into separate header |
| BEN-014 | **git** | [`0e4d290`](https://github.com/git/git/commit/0e4d290) | `meson.build` | `compiler_compat_flag` | build: tolerate use of _Generic from glibc 2.43 with Clang |
| BEN-015 | **git** | [`cefceda`](https://github.com/git/git/commit/cefceda) | `meson.build` | `build_plumbing_cleanup` | mingw: drop the build-system plumbing for nedmalloc |
| BEN-016 | **git** | [`c9eb040`](https://github.com/git/git/commit/c9eb040) | `meson.build` | `dependency_removal` | mingw: stop using nedmalloc |
| BEN-017 | **gnome-glib** | [`7151295`](https://github.com/GNOME/glib/commit/7151295) | `meson.build` | `feature_detection` | gspawn: use posix_spawn when closing file descriptors |
| BEN-018 | **gnome-glib** | [`7a85047`](https://github.com/GNOME/glib/commit/7a85047) | `meson.build` | `compiler_warning_flag` | build: Add -Wduplicated-cond |
| BEN-019 | **gnome-glib** | [`743c24d`](https://github.com/GNOME/glib/commit/743c24d) | `meson.build` | `compiler_check` | Check size_t using specific pointer warning |
| BEN-020 | **gnome-glib** | [`2765801`](https://github.com/GNOME/glib/commit/2765801) | `meson.build` | `platform_feature_check` | OpenBSD: account for IP_RECVTOS not being available |
| BEN-021 | **gnome-glib** | [`44650db`](https://github.com/GNOME/glib/commit/44650db) | `meson.build` | `platform_feature_check` | Implement g_get_process_executable_dir() on OpenBSD |
| BEN-022 | **gnome-glib** | [`2eb5d39`](https://github.com/GNOME/glib/commit/2eb5d39) | `meson.build` | `platform_feature_check` | Do not use recvmmsg and sendmmsg on AIX and IBM i |
| BEN-023 | **gnome-glib** | [`0ec3f4c`](https://github.com/GNOME/glib/commit/0ec3f4c) | `meson.build` | `platform_version_bump` | win32: require Windows 10+ and deprecate UWP-only apps |
| BEN-024 | **gnome-glib** | [`5eaf23f`](https://github.com/GNOME/glib/commit/5eaf23f) | `meson.build` | `toolchain_version_check` | win32:mingw64: require MINGW-w64 >= 12.0.0 |
| BEN-025 | **gnome-glib** | [`9243157`](https://github.com/GNOME/glib/commit/9243157) | `meson.build` | `compiler_standard_compat` | gio: Keep GBusActionGroup headers compatible with C99 |
| BEN-026 | **gnome-glib** | [`328b065`](https://github.com/GNOME/glib/commit/328b065) | `meson.build` | `build_option_validation` | build: Do not support building with both tracing and tsan enabled |
| BEN-027 | **gnome-glib** | [`e29631e`](https://github.com/GNOME/glib/commit/e29631e) | `meson.build` | `sanitizer_config` | girepository: Disable ASAN when building our typelib |
| BEN-028 | **gnome-glib** | [`057f4b5`](https://github.com/GNOME/glib/commit/057f4b5) | `meson.build` | `build_tool_config` | girepository: Always use currently built GLib to run g-ir-scanner |
| BEN-029 | **gnome-glib** | [`7382a3a`](https://github.com/GNOME/glib/commit/7382a3a) | `meson.build` | `sanitizer_config` | build: Preload sanitizer libraries before than any other library |
| BEN-030 | **gnome-glib** | [`7285595`](https://github.com/GNOME/glib/commit/7285595) | `meson.build` | `test_env_config` | build/tests: Automatically set ASAN_OPTIONS if preloading is required |
| BEN-031 | **gnome-glib** | [`e8473f2`](https://github.com/GNOME/glib/commit/e8473f2) | `meson.build` | `build_variable_config` | build: Define the preload variable name and separator globally |
| BEN-032 | **gnome-glib** | [`49f1dee`](https://github.com/GNOME/glib/commit/49f1dee) | `meson.build` | `platform_macro_define` | Meson: Define O_CLOEXEC as O_NOINHERIT on Windows |
