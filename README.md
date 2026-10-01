# Adversarial Mutation Testing of Build-Pipeline Security Defenses

> CIS 6614 — Group 14 · University of Central Florida · Fall 2026

Build pipelines are the automated systems that turn source code into a finished program. Attackers have learned to target the pipeline itself by injecting malicious code during the build, instead of hacking the app. High-profile real examples include the **XZ Utils backdoor** (2024), **SolarWinds** (2020), **Codecov** (2021), and the **event-stream npm** compromise (2018).

This project asks how well does an existing defense tool (**PipelineSave**) actually catch these kinds of attacks? We answer that by building a systematic benchmark of artificially created pipeline attacks and running PipelineSave against each one to see whether it blocks, detects, or misses it.

---

## What We're Building

1. **A taxonomy of real attacks.** A structured database of 50+ documented pipeline attacks, each classified by where in the build it strikes and how it works.
2. **A library of mutation operators.** Abstract templates describing categories of attack that can be applied to any compatible build file.
3. **A placement engine.** Python code that reads a real Meson build file and decides where and how to inject each operator, at four difficulty levels.
4. **A benchmark of 500+ mutants.** Auto-generated modified build files across three real open-source projects, each labeled with its attack type and difficulty.
5. **An evaluation.** Running PipelineSave against every mutant and recording BLOCKED, DETECTED, or MISSED.

---

## Repository Layout

| Folder     | What it contains                                                                           |
| ---------- | ------------------------------------------------------------------------------------------ |
| `src/`     | All Python source code — the Meson parser, mutation engine, and placement algorithms       |
| `data/`    | All data files — attack records, operator specs, generated mutants, and evaluation results |
| `tests/`   | Automated tests for the code in `src/`                                                     |
| `scripts/` | Helper scripts for setup, benchmark generation, and running evaluations                    |
| `docs/`    | Write-ups, diagrams, and the ACM report drafts                                             |
| `.github/` | CI workflow                                                                                |

---

## Team

| Name        | Role                                                                     |
| ----------- | ------------------------------------------------------------------------ |
| **Rejoice** | Attack taxonomy — collecting and classifying real-world pipeline attacks |
| **Debora**  | Mutation operators — designing abstract attack templates                 |
| **David**   | Placement strategies — algorithms for finding attack injection sites     |
| **Daniel**  | Engine — Meson parser, mutant generator, repo infrastructure             |

## Getting Started

```bash
git clone <repo-url>
cd <repo-name>

# Install Python dependencies (once src/ is set up)
pip install -r src/requirements.txt

# Set up the three target Meson projects
bash scripts/setup_targets.sh
```
