# Taxonomy Sources Bibliography (`sources.md`)

This document serves as the formal bibliography and audit trail for all **50 real-world software supply chain and build pipeline attacks** cataloged in `attacks.json` and `attacks.csv`.

---

## 1. Primary Vulnerability Databases & Government Advisories
* **NIST National Vulnerability Database (NVD) & MITRE CVE:**
  * `ATK-011` XZ Utils Backdoor: [CVE-2024-3094](https://nvd.nist.gov/vuln/detail/CVE-2024-3094)
  * `ATK-027` Trojan Source (Bidi Unicode): [CVE-2021-42574](https://trojansource.org/)
  * `ATK-043` Webmin Backdoor: [CVE-2019-15107](https://nvd.nist.gov/vuln/detail/cve-2019-15107)

* **CISA Known Exploited Vulnerabilities (KEV) & Cyber Advisories:**
  * `ATK-021` SolarWinds SUNBURST: [CISA Advisory AA20-352A](https://www.cisa.gov/news-events/cybersecurity-advisories/aa20-352a)
  * `ATK-022` XcodeGhost Compiler Compromise: [US-CERT Alert TA15-266A](https://www.cisa.gov/news-events/alerts/2015/09/23/malicious-xcode-compiler)
  * `ATK-032` Travis CI Secret Leakage: [CISA KEV Catalog](https://www.cisa.gov/known-exploited-vulnerabilities-catalog)
  * `ATK-035` JetBrains TeamCity Auth Bypass: [CISA Advisory AA23-347A](https://www.cisa.gov/news-events/cybersecurity-advisories/aa23-347a)
  * `ATK-038` Jenkins CLI Arbitrary File Read: [CISA KEV Catalog](https://www.cisa.gov/known-exploited-vulnerabilities-catalog)
  * `ATK-041` ASUS Live Update (ShadowHammer): [CISA KEV Catalog](https://www.cisa.gov/known-exploited-vulnerabilities-catalog)
  * `ATK-042` 3CX DesktopApp Compromise: [CISA Alert AA23-090A](https://www.cisa.gov/news-events/alerts/2023/03/30/threat-actors-compromise-3cx-desktop-application)
  * `ATK-044` NotPetya (MeDoc Update Server): [CISA Advisory AA18-046A](https://www.cisa.gov/news-events/cybersecurity-advisories/aa18-046a)

* **GitHub Advisory Database:**
  * `ATK-001` event-stream / Copay: [GHSA-mh6f-8j2x-4483](https://github.com/advisories/GHSA-mh6f-8j2x-4483)
  * `ATK-003` ua-parser-js Lifecycle Hijack: [GHSA-pjwm-rvh2-c87w](https://github.com/advisories/GHSA-pjwm-rvh2-c87w)
  * `ATK-007` rc npm Compromise: [GHSA-g2q5-5433-rhrf](https://github.com/advisories/GHSA-g2q5-5433-rhrf)
  * `ATK-031` Codecov Bash Uploader Exfiltration: [GitHub Advisory / Action Repo](https://github.com/codecov/codecov-action)

---

## 2. Threat Intelligence, Vendor Disclosures & Security Research
* **Trail of Bits Research:**
  * `ATK-033` GitHub Actions Template Injection: [Supply Chain Attacks Exploiting Assumptions](https://blog.trailofbits.com/2025/09/24/supply-chain-attacks-are-exploiting-our-assumptions/)
  * `ATK-040` CI/CD Pipeline & Package Integrity Flaws: [Package Managers Have an Integrity Problem](https://blog.trailofbits.com/2024/10/14/package-managers-have-an-integrity-problem/)

* **Industry Post-Mortems & Security Reports:**
  * `ATK-002` PyPI ctx & phpass: [Orca Security Analysis](https://orca.security/resources/blog/python-supply-chain-attack-ctx-phpass/)
  * `ATK-004` PyTorch Nightly Dependency Confusion: [PyTorch Security Disclosure](https://pytorch.org/blog/compromised-nightly-dependency/)
  * `ATK-005` colors.js & faker.js Sabotage: [Snyk Open Source Analysis](https://snyk.io/blog/open-source-npm-packages-colors-faker/)
  * `ATK-006` npm node-ipc Protestware: [Snyk Security Vulnerability Report](https://snyk.io/blog/peacenotwar-malicious-npm-node-ipc-package-vulnerability/)
  * `ATK-008` cross-env Typosquatting: [BleepingComputer Coverage](https://www.bleepingcomputer.com/news/security/javascript-packages-caught-stealing-environment-variables/)
  * `ATK-009` Fallout / Roblib Dependency Confusion: [Alex Birsan Original Disclosure](https://medium.com/@alex.birsan/dependency-confusion-4a5d60fec610)
  * `ATK-010` Rust crates.io rustdecimal Typosquat: [Rust Security Advisory](https://blog.rust-lang.org/2022/05/10/malicious-crate-rustdecimal.html)
  * `ATK-012` Octopus Scanner: [GitHub Security Lab Investigation](https://securitylab.github.com/research/octopus-scanner-malware-open-source-supply-chain/)
  * `ATK-014` Autotools configure.ac Pre-Compilation Exploit: [Ally Petitt Security Research](https://medium.com/@allypetitt/stealthy-exploit-opens-door-for-pre-compilation-code-execution-17a57b9585cb)
  * `ATK-017` Rust build.rs Network Exfiltration: [StepSecurity Analysis](https://www.stepsecurity.io/blog/arrayref-rust-crate-supply-chain-attack)
  * `ATK-023` CCleaner (Piriform): [Cisco Talos Threat Intelligence](https://blog.talosintelligence.com/ccleaner-c2-concern/)
  * `ATK-024` PHP Git Source Tampering: [PHP Internals Mailing List](https://news-web.php.net/php.internals/113838)
  * `ATK-026` ShadowPad NetSarang: [Kaspersky Securelist](https://securelist.com/shadowpad-in-corporate-networks/81432/)
  * `ATK-030` Delphi Induc Virus: [Kaspersky Securelist Incident Report](https://securelist.com/induc-the-innovative-file-infector/30553/)
  * `ATK-034` CircleCI Security Incident: [CircleCI Official Post-Mortem](https://circleci.com/blog/jan-4-2023-incident-report/)
  * `ATK-036` GitHub Actions Mining via Fork PRs: [BleepingComputer Threat Report](https://www.bleepingcomputer.com/news/security/github-actions-being-actively-abused-to-mine-cryptocurrency-on-github-servers/)
  * `ATK-045` PyPI Release Wheel Malware: [DataDog Security Labs GuardDog Report](https://securitylabs.datadoghq.com/articles/guarddog-identify-malicious-pypi-packages/)
  * `ATK-046` Homebrew Cask Release Bot Hijack: [Homebrew Official Security Disclosure](https://brew.sh/2021/04/21/security-incident-disclosure/)
  * `ATK-047` Gentoo Linux GitHub Mirror Tampering: [Gentoo Linux Infrastructure Notice](https://infra-status.gentoo.org/notice/20180629-github)
  * `ATK-048` NVIDIA Stolen Code Signing Certificates: [BleepingComputer Breach Report](https://www.bleepingcomputer.com/news/security/malware-now-using-nvidias-stolen-code-signing-certificates/)
  * `ATK-049` PyPI W4SP Stealer Campaign: [Checkmarx Zero Supply Chain Research](https://zero.checkmarx.com/evolution-of-a-software-supply-chain-attacker-740cd33d1f29)
  * `ATK-050` Docker Hub Official Image Poisoning: [Sysdig Threat Research](https://www.sysdig.com/blog/analysis-of-supply-chain-attacks-through-public-docker-images)

---

## 3. Academic Foundations & Build System Specifications
* `ATK-025` Ken Thompson (1984): [Reflections on Trusting Trust](https://www.cs.cmu.edu/~rdriley/487/papers/Thompson_1984_ReflectionsonTrustingTrust.pdf), *Communications of the ACM*.
* `ATK-028` IEEE S&P Program Committee (2021): [Statement Regarding Hypocrite Commits in the Linux Kernel](https://www.ieee-security.org/TC/SP2021/downloads/2021_PC_Statement.pdf).
* `ATK-013` CMake Build System: [CMake find_package Command Specification](https://cmake.org/cmake/help/latest/command/find_package.html).
* `ATK-015` Meson Build System: [Meson Wrap Dependency System Manual](https://mesonbuild.com/Wrap-dependency-system-manual.html).
* `ATK-016` GNU Make: [GNU Make Environment Variables Manual](https://www.gnu.org/software/make/manual/html_node/Environment.html).
* `ATK-018` Ninja Build: [The Ninja Build System Manual](https://ninja-build.org/manual.html).
* `ATK-019` Python Packaging Authority: [Deprecating setup.py develop Security Discussion](https://discuss.python.org/t/deprecating-setup-py-develop-security/15823).
* `ATK-020` Gradle Build Tool: [Gradle Initialization Scripts Manual](https://docs.gradle.org/current/userguide/init_scripts.html).
* `ATK-029` GNU Binutils: [GNU ld Linker Options Reference (-Wl,--wrap)](https://sourceware.org/binutils/docs/ld/Options.html).
* `ATK-037` Pytest Framework: [Pytest Fixtures Reference](https://docs.pytest.org/en/7.1.x/how-to/fixtures.html).
* `ATK-039` GitLab CI: [GitLab Runner Docker Executor Security Documentation](https://docs.gitlab.com/runner/executors/docker.html#use-docker-in-docker-with-privileged-mode).
