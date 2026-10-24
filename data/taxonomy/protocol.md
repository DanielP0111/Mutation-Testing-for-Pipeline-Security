# Build Pipeline Attack Collection Protocol

## 1. Objective
Establish an empirical, reproducible taxonomy of real-world build pipeline attacks to inform the design of mutation testing operators and evaluate build-pipeline security defenses (specifically PipelineSave).

## 2. Information Sources
Primary data collection targeted four authoritative repositories and vulnerability disclosure channels:
1. **NIST National Vulnerability Database (NVD):** `nvd.nist.gov`
2. **CISA Known Exploited Vulnerabilities (KEV) Catalog & Cyber Advisories:** `cisa.gov`
3. **GitHub Security Advisory Database:** `github.com/advisories`
4. **Trail of Bits Research Publications:** `blog.trailofbits.com`
5. **Authoritative Incident Post-Mortems:** Mandiant, Cisco Talos, Orca Security, and GitHub Security Lab reports.

## 3. Search Terms & Queries
* **NVD / CVE:** `"build pipeline"`, `"compiler injection"`, `"trojanized build"`, `"build runner"`, specific CVE queries (`CVE-2024-3094`, `CVE-2020-10148`, `CVE-2019-15107`, `CVE-2023-42793`).
* **GitHub Advisories:** `type:malware "preinstall"`, `supply chain "build script"`, `"actions injection"`, `"untrusted pull request"`.
* **CISA KEV / Alerts:** `"TeamCity"`, `"SolarWinds"`, `"Xcode"`, `"supply chain"`.
* **Trail of Bits:** `site:blog.trailofbits.com "pipeline" OR "CI/CD" OR "GitHub Actions"`, `"poisoned pipeline execution"`.

## 4. Eligibility Criteria

### Inclusion Criteria (Must meet all):
* **Temporal Scope:** Attack executed between upstream source commit and final client delivery.
* **Pipeline Mechanism:** The malicious modification targeted dependency resolution, build configuration scripts, compilers/linkers, CI test execution runners, or post-compilation release packaging.
* **Verifiable Evidence:** Incident is documented by a recognized CVE, government cyber advisory, package registry security notice, or vendor post-mortem.

### Exclusion Criteria (Any disqualifies):
* **Application-layer Runtime Vulnerabilities:** SQL injection, Cross-Site Scripting (XSS), or standard web business-logic flaws.
* **Independent Endpoint Malware:** Off-the-shelf crimeware or phishing attachments that do not intercept a software build lifecycle.
* **Generic Infrastructure Intrusions:** Unauthorized network pivot or database dump that did not tamper with build artifacts, CI jobs, or build scripts.

## 5. Selection Funnel & Systematic Screening Counts
* **Records Identified via Initial Keyword Search:** 48 candidate incidents
* **Records Excluded After Abstract / Summary Review:** 27 records
  * *Reason 1: Post-deployment application runtime flaws (14)*
  * *Reason 2: Corporate network lateral movement without pipeline tampering (9)*
  * *Reason 3: Theoretical vulnerabilities without documented real-world exploitation (4)*
* **Full Incidents Assessed for Pipeline Tampering:** 21 candidate incidents
* **Confirmed Incidents Included in Master Taxonomy:** 15 verified build pipeline attacks
* **Representative Incidents Abstracted for Operator Prototype:** 7 attacks
* **Held-Out Incidents Reserved for Benchmark Defense Evaluation:** 4 attacks

## 6. Taxonomy Controlled Vocabularies
To ensure consistency across the taxonomy database (`attacks.json`), operator specifications, and benchmark evaluations, every attack record is classified using restricted, mutually exclusive vocabularies.

### 6.1 Standardized Build Phases (`build_phase`)
Each attack is assigned to exactly one build phase representing the primary stage where malicious intervention occurs:

1. **`dependency_fetch`**: Tampering occurs during the acquisition, resolution, or downloading of remote packages, modules, or source dependencies prior to configuration.
2. **`configure`**: Tampering targets build generation systems, macro resolution, environment probing, or metadata/project descriptors (e.g., `./configure`, CMake, Autotools, or Meson initialization).
3. **`compile`**: Tampering intercepts source code files, compiler binaries, toolchains, or linking stages during object translation.
4. **`test`**: Tampering abuses test execution runners, test harnesses, or reporting utilities to harvest runner secrets or execute commands during CI/CD test phases.
5. **`package_release`**: Tampering modifies compiled binaries, packaged artifacts, installers, or distribution tarballs post-compilation, often prior to digital signature generation or registry publication.

---
### 6.2 Dataflow Patterns (`dataflow_pattern`)
The mechanism by which the payload is introduced, activated, or exfiltrated is classified under one of the following 13 predefined categories:

* **`code_insertion`**: Injects macro expansions, scripts, or hooks that conditionally synthesize payload code during build initialization.
* **`dependency_injection`**: Introduces a malicious direct or transitive dependency into an application manifest or dependency tree.
* **`build_script_tampering`**: Directly modifies build automation configuration files (e.g., XML descriptors, Makefiles, or build manifests) to inject tasks.
* **`source_swap`**: Intercepts active compiler or worker processes to temporarily replace clean source code on disk with a backdoored variant immediately prior to compiler read operations.
* **`compiler_injection`**: Compromises the native compiler, assembler, or toolchain binary to automatically inject payloads into output object files without modifying source files.
* **`runtime_injection`**: Statically links trojanized routines or runtime libraries directly into clean application binaries during final assembly.
* **`source_tampering`**: Commits malicious source logic directly to upstream source repositories via compromised committer or server credentials.
* **`credential_exfiltration`**: Modifies pipeline utilities or install hooks to transmit runner environment variables, deployment tokens, or secrets to external attacker infrastructure.
* **`memory_harvesting`**: Abuses multi-tenant or shared CI runner execution memory and unpurged build caches to harvest sensitive credentials.
* **`binary_tampering`**: Modifies compiled executables or installer archives on staging servers prior to digital certificate signing.
* **`library_substitution`**: Replaces bundled third-party dynamic libraries (e.g., `.dll`, `.so`) within application staging directories before installer packaging.
* **`tarball_injection`**: Directly alters the contents of a released source tarball or distribution package on build mirrors such that it diverges from the git repository.
* **`script_injection`**: Exploits unescaped CI/CD runner context expressions (e.g., GitHub Actions template injection) to execute arbitrary commands inside workflow steps.
