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
| Cap I — build tracer (Foreman) | `strace` syscall/file-access tracing | detect | `file_write`, `source_swap`, unexpected file reads |

Status: blocked on receiving the Foreman + `systemd-nspawn` code from Kevin
(reminder sent). Until then, only the outside baselines below are runnable.

## Outside baselines (no PipelineSave code required)

These are independent, tool-agnostic defenses used to contextualize
PipelineSave's numbers. Three are low-effort because the harness already
produces the evidence they need.

| Dimension | Tool / mechanism | Mode | Effects covered | Attacks hit | Integration effort | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Artifact integrity | in-toto provenance / hash pinning | detect (block if gating) | `artifact_diff`, `tarball_injection`, `binary_tampering`, `library_substitution` | SolarWinds, 3CX, Webmin, ASUS | medium | `wrap_integrity_check` is a first slice (wrap URL/hash pinning); extend to output-hash provenance |
| Network isolation | eBPF egress filter (advisor's "ebnf" — confirm) | block | `network_fetch`, `env_exfil` | Codecov, Travis, CIDER, xssfox, HackerBot | low | harness already runs `--network none` + logs the mock server; a "no unexpected egress" check over `mock_server.log` is nearly free |
| File-access monitoring | `strace`-style write/read monitor | detect | `file_write`, `source_swap` | XZ, SolarWinds, Octopus | low | local run flagging writes outside the build tree; maps to op_013's marker |
| CI/CD hardening | GitHub Actions hardener — "cosseter" unresolved; likely StepSecurity Harden-Runner (runtime egress) or zizmor (static) | block or detect | `script_injection`, `credential_exfiltration` | GH Actions injection, PPE set | medium | pending name confirmation |
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
4. **CI/CD hardener and Bazel** — after the above, and after the tool-name
   questions are resolved.

## Open questions for the advisor

- "cosseter for GitHub Actions" — which tool? (StepSecurity Harden-Runner for
  runtime egress, or zizmor for static analysis?)
- "ebnf for network isolation" — confirm this is eBPF.

## Reporting

For each defense, over the effective-mutant set: block rate, detection rate,
false-positive rate on the benign-change corpus, and per-phase / per-difficulty
coverage (see methodology §2.7). PipelineSave is reported against the outside
baselines on the same mutants so coverage gaps are directly comparable.
