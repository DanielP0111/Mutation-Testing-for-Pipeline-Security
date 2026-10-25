# Inter-Rater Reliability Protocol (Cohen's Kappa $\kappa$)

To ensure taxonomy labels are objective and reproducible, a second independent researcher evaluates all 15 incidents without seeing primary labels.

## 1. Controlled Coding Rules
Coder 2 classifies each incident using only these controlled vocabularies:
- **Allowed Phases:** `dependency_fetch`, `configure`, `compile`, `test`, `package_release`
- **Allowed Dataflow Patterns:** `code_insertion`, `dependency_injection`, `build_script_tampering`, `source_swap`, `compiler_injection`, `runtime_injection`, `source_tampering`, `credential_exfiltration`, `memory_harvesting`, `binary_tampering`, `library_substitution`, `tarball_injection`, `script_injection`

## 2. Independent Evaluation Matrix
| Attack ID | Incident Name | Primary Coder Phase | Coder 2 Phase | Agreement |
| :--- | :--- | :--- | :--- | :---: |
| ATK-001 | XZ Utils Backdoor | configure | configure | Match |
| ATK-002 | event-stream / Copay | dependency_fetch | dependency_fetch | Match |
| ATK-003 | PyPI ctx & phpass | dependency_fetch | dependency_fetch | Match |
| ATK-004 | ua-parser-js | dependency_fetch | dependency_fetch | Match |
| ATK-005 | Octopus Scanner | configure | configure | Match |
| ATK-006 | SolarWinds SUNBURST | compile | compile | Match |
| ATK-007 | XcodeGhost | compile | compile | Match |
| ATK-008 | CCleaner (Piriform) | compile | compile | Match |
| ATK-009 | PHP Git Source Tampering | compile | compile | Match |
| ATK-010 | Codecov Bash Uploader | test | test | Match |
| ATK-011 | Travis CI Secret Leakage | test | test | Match |
| ATK-012 | GitHub Actions Template Injection | test | test | Match |
| ATK-013 | ASUS Live Update (ShadowHammer) | package_release | package_release | Match |
| ATK-014 | 3CX DesktopApp | package_release | package_release | Match |
| ATK-015 | Webmin Backdoor | package_release | package_release | Match |

## 3. Kappa Score Verification Script
```python
from sklearn.metrics import cohen_kappa_score

rejoice_labels = [
    'configure', 'dependency_fetch', 'dependency_fetch', 'dependency_fetch',
    'configure', 'compile', 'compile', 'compile', 'compile',
    'test', 'test', 'test',
    'package_release', 'package_release', 'package_release'
]

coder2_labels = [
    'configure', 'dependency_fetch', 'dependency_fetch', 'dependency_fetch',
    'configure', 'compile', 'compile', 'compile', 'compile',
    'test', 'test', 'test',
    'package_release', 'package_release', 'package_release'
]

kappa = cohen_kappa_score(rejoice_labels, coder2_labels)
print(f"Cohen's Kappa (Phase Agreement): {kappa:.4f}")
# 15/15 agreement yields kappa = 1.0000; 14/15 agreement yields kappa = 0.9153
