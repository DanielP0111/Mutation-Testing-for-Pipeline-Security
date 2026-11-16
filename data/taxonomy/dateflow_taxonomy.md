# Dataflow Pattern Taxonomy Specification

## 1. Overview and Design Rationale
While build phases identify *where* and *when* an adversary intervenes during the software lifecycle, the **Dataflow Pattern** formalizes *how* malicious instructions, data, and side-effects propagate through the build graph. 

We identify **13 standardized, mutually exclusive dataflow categories** based on empirical attack analysis across open-source ecosystems, enterprise build networks, and CI/CD pipelines.

---

## 2. Standardized Dataflow Categories

### 1. `dependency_injection`
* **Definition:** Introduction of an unauthorized direct or transitive dependency into an application manifest, lockfile, or subproject configuration.
* **Propagation Route:** Package Manifest / Wrap File $\rightarrow$ Package Manager Resolution $\rightarrow$ Build Workspace.
* **Examples:** Typosquatting, dependency confusion, transitive dependency tampering (e.g., `event-stream`, `PyTorch Nightly`).

### 2. `code_insertion`
* **Definition:** Injection of macro expansions, configure-time hooks, or conditional build logic that dynamically generates payload code during build initialization.
* **Propagation Route:** Build Configuration Manifest $\rightarrow$ Macro Expander $\rightarrow$ Generated Build Rule / Header.
* **Examples:** GNU Autotools M4 macro injection (`XZ Utils`), linker flag hooking (`-Wl,--wrap`).

### 3. `build_script_tampering`
* **Definition:** Modification of declarative build manifests or build orchestrator scripts to alter targets, compiler flags, or dependency paths.
* **Propagation Route:** Project Configuration (e.g., `meson.build`, `CMakeLists.txt`, `build.xml`) $\rightarrow$ Build Generator $\rightarrow$ Ninja Execution Graph.
* **Examples:** NetBeans IDE XML tampering (`Octopus Scanner`), rogue CMake `Find*.cmake` override.

### 4. `source_swap`
* **Definition:** Interception of compiler execution via active worker process monitoring, transiently substituting clean source code on disk with a backdoored variant immediately prior to compiler read operations and restoring clean source post-compilation.
* **Propagation Route:** Host Memory Monitor $\rightarrow$ Working Tree File System $\rightarrow$ Compiler Frontend.
* **Examples:** SolarWinds `SUNBURST` (Sunspot injector).

### 5. `compiler_injection`
* **Definition:** Direct subversion of the compiler, assembler, or language toolchain binary, causing clean source code to be compiled into backdoored object files without disk-level source modification.
* **Propagation Route:** Compromised Toolchain Binary $\rightarrow$ Abstract Syntax Tree / Intermediate Representation $\rightarrow$ Machine Code Emission.
* **Examples:** `Reflections on Trusting Trust`, `XcodeGhost`, `Delphi Induc Virus`.

### 6. `runtime_injection`
* **Definition:** Direct injection of compiled shellcode, backdoored C-runtime routines, or unauthorized static archive libraries into target binaries during linker execution.
* **Propagation Route:** Toolchain CRT Library $\rightarrow$ Linker Symbol Resolution $\rightarrow$ Final Binary Executable.
* **Examples:** `CCleaner (Piriform)`, `ShadowPad`.

### 7. `source_tampering`
* **Definition:** Direct, unauthorized commits or patches to upstream source code repositories using stolen credentials, compromised version control servers, or deceptive review practices.
* **Propagation Route:** Remote VCS Server $\rightarrow$ Repository Pull $\rightarrow$ Local Source Tree $\rightarrow$ Compilation.
* **Examples:** `PHP Git Source Tampering`, `Trojan Source (Bidi Unicode)`, `Linux Kernel Hypocrite Commits`.

### 8. `credential_exfiltration`
* **Definition:** Modification of pipeline utilities, build scripts, or lifecycle hooks to capture environment variables, runner credentials, or deployment keys and transmit them to external infrastructure.
* **Propagation Route:** Runner Process Memory / Environment $\rightarrow$ Outbound Network Request $\rightarrow$ Attacker C2 Infrastructure.
* **Examples:** `Codecov Bash Uploader`, `PyPI ctx & phpass`, `cross-env`.

### 9. `memory_harvesting`
* **Definition:** Extraction of secrets, tokens, or cached cryptographic material from shared multi-tenant runner memory, daemon caches, or unpurged build workspace state.
* **Propagation Route:** Unprivileged Process / PR Job $\rightarrow$ Daemon Process Memory / Host Socket $\rightarrow$ Local Storage / Exfiltration.
* **Examples:** `Travis CI Secret Leakage`, `CircleCI Token Breach`, `Jenkins args4j arbitrary file read`.

### 10. `binary_tampering`
* **Definition:** Post-compilation modification of compiled binaries, setup installers, or dynamic libraries prior to digital code-signing or release distribution.
* **Propagation Route:** Staging Workspace $\rightarrow$ Binary Hex/Section Modification $\rightarrow$ Code Signing Authority $\rightarrow$ Release Artifact.
* **Examples:** `ASUS Live Update (ShadowHammer)`, `NotPetya (MeDoc)`.

### 11. `library_substitution`
* **Definition:** Swapping of clean bundled shared dynamic libraries (e.g., `.dll`, `.so`, `.dylib`) within the release staging directory prior to packaging or container creation.
* **Propagation Route:** Build Staging Directory $\rightarrow$ Third-Party Dynamic Library File Replacement $\rightarrow$ Final Distribution Bundle.
* **Examples:** `3CX DesktopApp` (`ffmpeg.dll` replacement).

### 12. `tarball_injection`
* **Definition:** Modification of distributed archive packages, release tarballs, or package registry blobs on build mirrors such that distributed artifacts diverge from version-controlled source trees.
* **Propagation Route:** Release Packaging Worker $\rightarrow$ Tarball Creation $\rightarrow$ Distribution Mirror.
* **Examples:** `Webmin Backdoor` (CVE-2019-15107), `Gentoo GitHub Mirror Compromise`.

### 13. `script_injection`
* **Definition:** Exploitation of unescaped context variables in CI/CD runner YAML definitions or package lifecycle hooks to achieve arbitrary shell command execution.
* **Propagation Route:** Untrusted Event Trigger (PR Title / Commit Message) $\rightarrow$ CI Template Engine $\rightarrow$ Shell Execution Environment.
* **Examples:** `GitHub Actions Template Injection (PPE)`, `Autotools configure.ac Command Injection`.
