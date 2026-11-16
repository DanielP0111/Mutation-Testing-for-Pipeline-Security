# Attack Decomposition Template

Use this reusable fill-in-the-blank specification to record, decompose, and integrate any new build pipeline attack into the benchmark taxonomy. Every field is required to ensure reproducibility and automated schema ingestion.

---

## Attack Metadata Form

### 1. Primary Identification
* **Incident Name:** `[Common incident name, e.g., SolarWinds SUNBURST]`
* **Incident ID:** `[Next sequential ID, e.g., ATK-051]`
* **Year of Occurrence:** `[YYYY]`
* **CVE Identifier:** `[CVE-YYYY-XXXXX or "None"]`
* **Primary Reference URL:** `[Authoritative NVD, CISA, vendor post-mortem, or advisory URL]`

---

### 2. Taxonomy Classification
* **Build Phase:** `[Select exactly ONE: dependency_fetch | configure | compile | test | package_release]`
  * *Phase Selection Rationale:* `[Explain why the initial malicious execution or tampering belongs in this phase]`
* **Dataflow Pattern:** `[Select exactly ONE from the 13 standardized patterns: dependency_injection | code_insertion | build_script_tampering | source_swap | compiler_injection | runtime_injection | source_tampering | credential_exfiltration | memory_harvesting | binary_tampering | library_substitution | tarball_injection | script_injection]`
* **Detection Difficulty (1–4):** `[1 = Obvious, 2 = Moderate, 3 = Stealthy, 4 = Advanced Persistent/Toolchain Level]`

---

### 3. Pipeline Mechanics & Propagation
* **Targeted File / Pipeline Entity:** `[e.g., m4/build-to-host.m4, package.json, build.ninja, CI runner memory]`
* **Adversarial Vector:** `[Concise technical description of how the adversary gained write access or code execution]`
* **Attacker Gain:** `[What the attacker achieved: e.g., remote code execution in client environments, token theft]`
* **Observable Artifact / System Effect:** `[Concrete filesystem, process, network, or symbol change that a defense system can observe]`

---

### 4. Meson Build System Expressibility
* **Meson Expressible:** `[Select ONE: yes | partial | no]`
* **Meson Placement Scheme:** `[Select ONE: build_file_manipulation | subproject_wrap_injection | test_target_modification | N/A]`
* **Simulation Construct:** `[Describe how this can be simulated in a Meson project: e.g., custom_target(), run_command(), wrap-git patch, meson.add_postconf_script()]`

---

### 5. Preconditions & Execution Environment
* **Precondition 1:** `[Requirement 1, e.g., Build system evaluates unpinned third-party wrap dependencies]`
* **Precondition 2:** `[Requirement 2, e.g., CI runner environment grants outbound internet egress during test jobs]`
* **Precondition 3:** `[Requirement 3, e.g., Code signing authority signs packaged staging directories without hash verification]`

---

### 6. Raw Ingestion Schema (JSON Snippet)
```json
{
  "id": "ATK-XXX",
  "name": "[Incident Name]",
  "year": 202X,
  "cve": "[CVE or None]",
  "source_url": "[URL]",
  "build_phase": "[dependency_fetch|configure|compile|test|package_release]",
  "attack_vector": "[Technical vector summary]",
  "dataflow_pattern": "[Standardized pattern]",
  "detection_difficulty": 3,
  "notes": "[Key technical takeaway]"
}
