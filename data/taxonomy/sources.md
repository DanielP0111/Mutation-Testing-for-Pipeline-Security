# Bibliography of Build Pipeline Attack Sources

This bibliography documents authoritative research, post-mortems, advisories, and CVE definitions used to construct the build-pipeline attack taxonomy.

### Authoritative Repositories & Catalogs
1. **NIST National Vulnerability Database (NVD)**: CVE-2024-3094 (XZ Utils), CVE-2019-15107 (Webmin), CVE-2023-42793 (TeamCity), CVE-2023-29059 (3CX DesktopApp), CVE-2021-41077 (Travis CI). Note: SolarWinds SUNBURST has no assigned CVE; CVE-2020-10148 is the related Orion API authentication-bypass (SUPERNOVA), not SUNBURST.
2. **CISA Known Exploited Vulnerabilities (KEV) Catalog & Alerts**:
   - Alert AA20-352A (SolarWinds Orion Supply Chain Compromise)
   - Alert TA15-266A (Compromised Xcode Compiler)
   - Alert (3CX DesktopApp Supply Chain Compromise)
   - CISA KEV Catalog entries for ASUS ShadowHammer and JetBrains TeamCity.
3. **GitHub Security Advisory Database**:
   - `GHSA-mh6f-8j2x-4483` (event-stream / flatmap-stream)
   - `GHSA-pjwm-rvh2-c87w` (ua-parser-js credential harvester)
   - `GHSA-m259-7558-8p8w` (Codecov bash uploader modification)
4. **Trail of Bits Research**:
   - *Supply chain attacks are exploiting our assumptions* (CI/CD and GitHub Actions template injection analysis).
5. **Vendor Post-Mortems & Threat Research**:
   - Gazzillo, P. (2026). *Defining Software Development Pipeline Code Attacks.* University of Central Florida. (Source for ATK-016 CIDER, ATK-017 HackerBot-Claw, ATK-018 xssfox; formalizes Poisoned Pipeline Execution, D-PPE/I-PPE.)
   - Mandiant / CrowdStrike SolarWinds SUNBURST & Sunspot Technical Breakdown.
   - Cisco Talos CCleaner C2 Survey and Technical Analysis.
   - Orca Security Python Supply Chain Attack Analysis (PyPI ctx & phpass).
   - GitHub Security Lab Research on Octopus Scanner.
