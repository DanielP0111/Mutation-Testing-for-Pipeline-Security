# Defenses Under Evaluation

This document enumerates the defenses the benchmark scores mutants against,
organized by the isolation/monitoring dimension each one covers. It expands
Section 2.7 of the methodology into a concrete evaluation plan and integration
backlog. The tool set follows advisor guidance (P. Gazzillo, Slack, 2026-10-27):
one representative mechanism per dimension.

Every defense is run through the pluggable interface
(`run_pipeline.py --defense NAME`), which records, per mutant,
`{name, blocked, flags}` in `metadata.json`. Only **effective** mutants
(§2.5 of the methodology) are scored, so a "block" always means a real attack
was stopped. Each defense is characterized as **blocking** (prevents the attack
effect) or **detecting** (flags it after the fact) — the distinction RQ3 turns
on.

## Defense of record: PipelineSave

PipelineSave contributes the two primary defenses, and the advisor's tool list
maps directly onto them:

| Capability | Mechanism | Mode | Effects it addresses |
| --- | --- | --- | --- |
| Cap II — per-phase sandbox | `systemd-nspawn` process/namespace isolation (XZ demo) | block | `network_fetch`, `env_exfil`, cross-phase `file_write` |
| Cap I — phase-isolation checker (Foreman) | per-phase JSON spec of command + permitted files; compares file access times before/after each phase (177-line Python prototype, Pappas & Gazzillo, ICSE-NIER '26) | detect | unexpected file reads/writes (`file_write`, `source_swap`); not network or env |

Status: Foreman is public (Zenodo 10.5281/zenodo.18233614; code Apache-2.0), vendored in `third_party/foreman/` and wired into the harness (`run_pipeline.py --foreman`). The `systemd-nspawn` sandbox is still planned work in the paper; waiting on that code from Kevin
(reminder sent). Until then, only the outside baselines below are runnable.

## Outside baselines (no PipelineSave code required)

These are independent, tool-agnostic defenses used to contextualize
PipelineSave's numbers. Three are low-effort because the harness already
produces the evidence they need.

| Dimension | Tool / mechanism | Mode | Effects covered | Attacks hit | Integration effort | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Artifact integrity | in-toto provenance / hash pinning | detect (block if gating) | `artifact_diff`, `tarball_injection`, `binary_tampering`, `library_substitution` | SolarWinds, 3CX, Webmin, ASUS | medium | `wrap_integrity_check` is a first slice (wrap URL/hash pinning); extend to output-hash provenance |
| Network isolation | eBPF egress filter (confirmed: advisor's "ebnf" = eBPF) | block | `network_fetch`, `env_exfil` | Codecov, Travis, CIDER, xssfox, HackerBot | low | harness already runs `--network none` + logs the mock server; a "no unexpected egress" check over `mock_server.log` is nearly free |
| File-access monitoring | `strace`-style write/read monitor | detect | `file_write`, `source_swap` | XZ, SolarWinds, Octopus | low | local run flagging writes outside the build tree; maps to op_013's marker |
| CI/CD hardening | COSSETER (Tystahl et al., IEEE S&P 2026) — static `GITHUB_TOKEN` least-privilege inference per job; code: github.com/s3c2/cosseter | mitigate (limits blast radius; neither blocks nor detects the injection) | `script_injection`, `credential_exfiltration` via `GITHUB_TOKEN` | GH Actions injection, PPE set | medium | scored statically on workflow mutants (op_010): run COSSETER on the mutant workflow, record whether the injected step's token use exceeds the inferred MINPERMS. Not a runtime check — the harness does not execute GitHub workflows |
| Phase isolation | Bazel hermetic build | block | ambient-state configure/compile injection | XZ, Octopus | high | heavy to retrofit onto Meson/git; lower priority |
| Sandboxing | Docker | block | coarse phase isolation | broad | n/a | already the harness substrate; not a standalone defense |

## Build order (quick wins first)

1. **Network-egress baseline** — flag any request in `mock_server.log` the clean
   baseline did not make. Reuses existing harness output; covers the
   credential-exfil attacks (the largest cluster).
2. **File-access detector** — flag writes outside the build tree / unexpected
   reads; pairs with op_013 (`file_write`) and future `source_swap` operators.
3. **Integrity/provenance** — extend `wrap_integrity_check` from wrap pinning to
   build-output-hash provenance (in-toto-style).
4. **COSSETER and Bazel** — after the above. COSSETER is static and only
   applies to workflow-file mutants (op_010), so it is scored separately from
   the harness-run defenses.

## Resolved advisor questions

- "cosseter for GitHub Actions" = COSSETER: *GitHub Actions Permission
  Reduction Using Demand-Driven Static Analysis* (Tystahl, Ghebremichael,
  Kapravelos, Enck, Muralee, Cherupattamoolayil, Bianchi, Machiry; IEEE S&P
  2026). Purely static; no eBPF or runtime monitoring. It reduces what a
  hijacked `GITHUB_TOKEN` can do, so we report it as a *mitigation*, separate
  from block/detect rates.
- "ebnf for network isolation" = eBPF (confirmed).

## Reporting

For each defense, over the effective-mutant set: block rate, detection rate,
false-positive rate on the benign-change corpus, and per-phase / per-difficulty
coverage (see methodology §2.7). PipelineSave is reported against the outside
baselines on the same mutants so coverage gaps are directly comparable.
