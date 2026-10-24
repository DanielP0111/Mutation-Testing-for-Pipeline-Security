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
