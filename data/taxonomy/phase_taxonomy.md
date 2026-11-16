# Build Phase Taxonomy Specification

## 1. Overview and Design Rationale
In modern software supply chain pipelines, security evaluations frequently model the build process as an atomic transition from source repository to published artifact. However, build automation systems (such as Meson, CMake, Autotools, and Make) execute multi-stage lifecycle pipelines where adversarial tampering can occur at discrete phases. 

To formalize this lifecycle, we define five mutually exclusive build phases aligned directly with Meson build orchestrations and POSIX build pipeline models:
1. `dependency_fetch`
2. `configure`
3. `compile`
4. `test`
5. `package_release`

---

## 2. Phase Definitions and Meson Mappings

### Phase 1: `dependency_fetch`
* **Definition:** The phase responsible for discovering, resolving, and downloading external dependencies, subprojects, libraries, and language package ecosystem components before build system initialization.
* **Meson Build Analog:** Subproject acquisition via Meson WrapDB (`subprojects/*.wrap`), `wrap-git`, `wrap-file`, and dependency discovery via `dependency('foo')`.
* **Adversarial Mechanism:** Dependency confusion, typosquatting, expired domain takeover, and repository compromise leading to malicious code insertion prior to project configuration.
* **Representative Incidents:** `event-stream` (GHSA-mh6f-8j2x-4483), `PyTorch Nightly Dependency Confusion`, `PyPI ctx & phpass`.

### Phase 2: `configure`
* **Definition:** The phase responsible for evaluating build system configuration scripts, resolving build options, checking system headers/compiler flags, evaluating macros, and generating backend execution build graphs (e.g., Ninja build files).
* **Meson Build Analog:** Execution of `meson setup builddir/`, evaluation of `meson.build` root manifests, `meson_options.txt`, `run_command()`, `meson.add_postconf_script()`, and wrap patch application.
* **Adversarial Mechanism:** Injecting malicious build macros, tampering with build configuration descriptors (XML/Makefiles), overriding compiler flags, and redirecting dependency resolution paths during generation.
* **Representative Incidents:** `XZ Utils Backdoor` (CVE-2024-3094), `Octopus Scanner`, `CMake FindPackage Poisoning`.

### Phase 3: `compile`
* **Definition:** The phase responsible for preprocessing, compiling, and linking source code files into target object files, shared/static libraries, and executables.
* **Meson Build Analog:** Backend compilation jobs executed via `ninja -C builddir/`, invoking native compilers (`gcc`, `clang`, `msvc`, `rustc`), custom generators (`generator()`), and custom build targets (`custom_target()`).
* **Adversarial Mechanism:** Active worker process monitoring, transient source file swapping, compromised toolchain/compiler binaries, and malicious symbol wrapping during linker execution.
* **Representative Incidents:** `SolarWinds SUNBURST` (CISA AA20-352A), `XcodeGhost`, `CCleaner`, `PHP Git Source Tampering`.

### Phase 4: `test`
* **Definition:** The phase responsible for executing automated test suites, quality gates, regression runners, and coverage-reporting harnesses within local or CI/CD test runners.
* **Meson Build Analog:** Test harness execution triggered via `meson test -C builddir/`, executing test binaries defined via `test()`, benchmark runners via `benchmark()`, and test wrapper scripts.
* **Adversarial Mechanism:** Executing arbitrary commands inside CI runner steps, exfiltrating CI environment variables and runner credentials, tampering with test exit codes (coverage falsification), and container escapes.
* **Representative Incidents:** `Codecov Bash Uploader`, `Travis CI Secret Leakage`, `GitHub Actions Template Injection (PPE)`, `TeamCity Auth Bypass` (CVE-2023-42793).

### Phase 5: `package_release`
* **Definition:** The phase responsible for assembling final deployment archives, staging release directories, bundling dynamic libraries, applying digital code-signing certificates, and uploading release packages to distribution channels.
* **Meson Build Analog:** Execution of `meson install -C builddir/`, tarball generation via `meson dist`, and downstream release staging scripts.
* **Adversarial Mechanism:** Modifying binary artifacts post-compilation, replacing bundled third-party libraries, appending shellcode to signed executables, and tarball staging discrepancies diverging from git source.
* **Representative Incidents:** `ASUS Live Update (ShadowHammer)`, `3CX DesktopApp`, `Webmin Backdoor` (CVE-2019-15107), `NotPetya (MeDoc)`.
