# Benign Build-Script Commit Baseline (Corpus: 32 Commits)

To evaluate the false-positive rate and specificity of PipelineSave, we curated **32 verified non-malicious commits** modifying build manifests across the benchmark's three target Meson projects (`git`, `numpy`, `scipy`).

| ID | Project | Target File | Change Type | Description | Diff Snippet |
| :--- | :---: | :--- | :--- | :--- | :--- |
| BEN-001 | **git** | `meson.build` | `compiler_flag_update` | Add -Wno-unused-parameter to suppression flags for legacy submodules | `+ add_project_arguments('-Wno-unused-parameter', language: 'c')` |
| BEN-002 | **git** | `meson.build` | `path_normalization` | Fix install_dir prefix resolution on macOS homebrew environments | `- install_dir: get_option('prefix') / 'bin'<br>+ install_dir: get_option('bindir')` |
| BEN-003 | **git** | `meson.build` | `dependency_lookup` | Probe for libpcre2 dependency with fallback to builtin subproject wrap | `+ pcre2_dep = dependency('libpcre2-8', required: get_option('pcre2'))` |
| BEN-004 | **git** | `meson_options.txt` | `build_option` | Introduce curl option to enable or disable HTTP transport protocol support | `+ option('curl', type: 'feature', value: 'auto', description: 'Build with cURL support')` |
| BEN-005 | **git** | `meson.build` | `custom_target` | Generate command-list.h using perl script from documentation catalog | `+ custom_target('command-list.h', output: 'command-list.h', input: 'command-list.txt', command: [perl, '@INPUT@', '@OUTPUT@'])` |
| BEN-006 | **git** | `t/meson.build` | `test_suite_definition` | Register standard shell regression test suite targets in meson test | `+ test('t0000-basic', test_runner, args: ['t0000-basic.sh'], suite: 'unit')` |
| BEN-007 | **git** | `meson.build` | `header_check` | Add check for sys/poll.h header existence via cc.has_header() | `+ if cc.has_header('sys/poll.h')<br>+   conf_data.set('HAVE_POLL_H', 1)<br>+ endif` |
| BEN-008 | **git** | `meson.build` | `sanitizer_config` | Conditionally append AddressSanitizer and UndefinedBehaviorSanitizer flags | `+ if get_option('b_sanitize') != 'none'<br>+   add_project_arguments('-DDEBUG', language: 'c')<br>+ endif` |
| BEN-009 | **git** | `subprojects/zlib.wrap` | `wrap_revision_bump` | Bump fallback zlib wrap version to v1.3.1 patch release | `- revision = v1.3<br>+ revision = v1.3.1` |
| BEN-010 | **git** | `meson.build` | `library_target` | Split common git objects into separate static library libgit_common | `+ libgit = static_library('git', libgit_sources, dependencies: libgit_deps)` |
| BEN-011 | **numpy** | `subprojects/lapack.wrap` | `dependency_version_bump` | Bump OpenBLAS dependency revision in wrap file to 0.3.26 | `- revision = v0.3.25<br>+ revision = v0.3.26` |
| BEN-012 | **numpy** | `numpy/meson.build` | `source_addition` | Add new SIMD dispatch source files to C compilation target | `+ 'core/src/common/simd_dispatch.c',` |
| BEN-013 | **numpy** | `meson.build` | `python_extension_module` | Use py.extension_module with limited API Py_LIMITED_API flag | `+ py.extension_module('_multiarray_umath', sources, c_args: ['-DPy_LIMITED_API=0x03090000'])` |
| BEN-014 | **numpy** | `numpy/core/meson.build` | `generator_definition` | Add code generator for generate_umath.py C header templating | `+ umath_gen = generator(py, output: '@BASENAME@.c', arguments: [generate_umath, '@INPUT@', '@OUTPUT@'])` |
| BEN-015 | **numpy** | `meson.build` | `blas_lapack_detection` | Improve MKL library detection order across Linux and Windows systems | `+ mkl_dep = dependency('mkl-dynamic-lp64-iomp', required: false)` |
| BEN-016 | **numpy** | `numpy/random/meson.build` | `cython_compiler_args` | Pass --cplus and language level 3 compiler directives to Cython invocations | `+ cython_args: ['-3', '--fast-fail', '-X', 'boundscheck=False']` |
| BEN-017 | **numpy** | `meson_options.txt` | `simd_option` | Add allow-nodata option to permit building without pre-compiled SIMD baseline | `+ option('cpu-baseline', type: 'string', value: 'min', description: 'Minimal set of required CPU SIMD features')` |
| BEN-018 | **numpy** | `numpy/tests/meson.build` | `test_env_setup` | Set PYTHONPATH in meson test environment to point to build directory wheel | `+ env: {'PYTHONPATH': meson.project_build_root()}` |
| BEN-019 | **numpy** | `meson.build` | `install_headers` | Install NumPy C API headers to py.get_install_dir() / 'numpy/core/include' | `+ install_headers(numpy_nodist_headers, subdir: 'numpy/core/include/numpy')` |
| BEN-020 | **numpy** | `meson.build` | `compiler_warning_level` | Elevate default warning level to 2 with -Werror=implicit-function-declaration | `+ default_options: ['warning_level=2', 'c_std=c99']` |
| BEN-021 | **numpy** | `numpy/linalg/meson.build` | `include_directories` | Include OpenBLAS headers directory in lapack_lite extension module | `+ include_directories: [incdir_core, incdir_numpy]` |
| BEN-022 | **scipy** | `meson.build` | `option_configuration` | Expose use-g77-abi build option for legacy Fortran ABI compatibility | `+ option('use-g77-abi', type: 'boolean', value: false, description: 'Compile with g77 ABI')` |
| BEN-023 | **scipy** | `meson.build` | `test_target_definition` | Register automated linalg benchmark test runner in meson test | `+ test('linalg-benchmark', py, args: ['-m', 'pytest', 'scipy/linalg/tests'])` |
| BEN-024 | **scipy** | `scipy/meson.build` | `fortran_compiler_detection` | Detect GNU gfortran vs LLVM flang and set Fortran module directory argument | `+ fc = meson.get_compiler('fortran')<br>+ if fc.get_id() == 'gcc'<br>+   add_project_arguments('-fno-underscoring', language: 'fortran')` |
| BEN-025 | **scipy** | `scipy/spatial/meson.build` | `cpp_std_override` | Set C++14 standard requirement for QHull spatial triangulation extensions | `+ override_options: ['cpp_std=c++14']` |
| BEN-026 | **scipy** | `scipy/optimize/meson.build` | `custom_target_f2py` | Wrap legacy Fortran MINPACK routine via numpy f2py custom_target | `+ custom_target('minpack_module', output: ['_minpackmodule.c'], input: 'minpack.pyf', command: [py, f2py, '@INPUT@'])` |
| BEN-027 | **scipy** | `scipy/sparse/linalg/meson.build` | `subproject_arpack` | Configure ARPACK subproject dependency with Fortran 90 fallback | `+ arpack_dep = dependency('arpack', fallback: ['arpack-ng', 'arpack_dep'])` |
| BEN-028 | **scipy** | `scipy/interpolate/meson.build` | `source_compilation_unit` | Compile fitpack B-spline interpolation evaluation C wrappers | `+ py.extension_module('_fitpack', fitpack_sources, dependencies: [py_dep, np_dep])` |
| BEN-029 | **scipy** | `meson.build` | `openmp_detection` | Add optional OpenMP dependency check with fallback to sequential execution | `+ openmp_dep = dependency('openmp', required: false)` |
| BEN-030 | **scipy** | `scipy/signal/meson.build` | `cython_binding` | Compile signal convolution and filter design Cython extensions | `+ py.extension_module('_sigtools', 'sigtools.pyx', dependencies: [py_dep, np_dep])` |
| BEN-031 | **scipy** | `meson.build` | `wheel_installation_path` | Ensure pure Python packages install under site-packages subdir | `+ py.install_sources(scipy_py_sources, subdir: 'scipy')` |
| BEN-032 | **scipy** | `subprojects/highs.wrap` | `wrap_patch_directory` | Add patch_directory to HiGHS linear programming solver wrap file | `+ patch_directory = highs-patches<br>+ diff_files = highs-fix-includes.patch` |
