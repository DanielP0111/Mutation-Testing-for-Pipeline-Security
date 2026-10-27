# Methodology

This section describes the adversarial mutation-testing framework end to end:
how real build-pipeline attacks are collected and abstracted into mutation
operators, how mutants are placed in a target Meson project, how each mutant is
*validated to achieve its intended attack effect*, and how defenses are then
scored against only the mutants that are known to work. The framework is
implemented as a Python engine (`src/`) driven by a single pipeline script
(`scripts/run_pipeline.py`) and a containerized build harness (`harness/`).

## 2.1 Overview and Research Questions

We evaluate build-pipeline defenses by injecting *validated* synthetic attacks
into a real project's build and measuring whether a defense blocks or merely
detects each one. The study is organized around four research questions:

- **RQ1 (Attack surface).** Across which build phases and dataflow patterns do
  real pipeline attacks concentrate?
- **RQ2 (Operator fidelity).** Can real attacks be abstracted into reusable,
  target-agnostic mutation operators that produce *effective* mutants in a
  previously unseen project?
- **RQ3 (Defense effectiveness).** For each defense, what fraction of effective
  mutants are blocked (prevented) versus detected (flagged after compromise),
  broken down by build phase?
- **RQ4 (Difficulty and generalization).** How does defense effectiveness vary
  with adversarial obfuscation difficulty, and do operators generalize to a
  held-out set of attacks they were not designed from?

The design mirrors the four workstreams of the proposal — taxonomy (§2.2),
operators (§2.3), placement (§2.4), and benchmark/evaluation (§2.5–§2.7) — with
a mutant-validity oracle (§2.5) added as the pivot between mutant generation and
defense scoring.

## 2.2 Attack Taxonomy Construction

Attacks were collected following a pre-registered protocol
(`data/taxonomy/protocol.md`) drawing on the NVD, the CISA KEV catalog and
alerts, the GitHub Security Advisory database, and vendor post-mortems. A
documented selection funnel (48 candidate incidents screened to 15 confirmed
build-pipeline attacks) records inclusion and exclusion criteria so the corpus
is reproducible. Each incident is encoded in `data/taxonomy/attacks.json` with a
build phase, a dataflow pattern, a stealth rating, and a primary source.

Every record is classified using closed controlled vocabularies: five build
phases (`dependency_fetch`, `configure`, `compile`, `test`, `package_release`)
and thirteen dataflow patterns. To establish that these labels are objective
rather than author-dependent, a second coder independently classified all 15
incidents from the controlled vocabulary alone; agreement is reported as
Cohen's $\kappa$ (`docs/inter_rater_reliability.md`). The closed codebook is a
precondition for a meaningful $\kappa$: free-text labels cannot be reproduced by
a second rater.

Four incidents (ATK-009 PHP Git source tampering, ATK-011 Travis CI secret
leakage, ATK-014 3CX DesktopApp, ATK-015 Webmin) are **held out** of operator
design and reserved for the generalization test in §2.7. No operator's
`source_attacks` references a held-out incident, so held-out attacks remain
genuinely unseen by the operator set.

## 2.3 Mutation Operators

A mutation operator is a target-agnostic specification of one attack primitive,
validated against a machine-readable schema (`data/schemas/operator_schema.json`,
v3). Operators are abstracted from the training incidents by replacing concrete
package names, URLs, file paths, and identifiers with placeholders per the
abstraction and locator rules in `data/schemas/abstraction_rules.md`. Each
operator declares the build phase it targets, a placement `scheme` (§2.4), an
edit `mode` (`replace`, `delete_line`, `insert_after`, `append`), an
`injection_location`, a `template`, preconditions, and the training incidents it
generalizes.

Crucially, each operator also declares an **effect block** — the observable
signal its attack produces when it succeeds (e.g., a marker file written during
configure, a request to an attacker-controlled host, or a divergence in a build
output hash). The effect block is what makes a mutant *checkable* rather than
merely syntactically applied, and is consumed by the oracle in §2.5. For
example, a configure-stage operator that appends a `run_command` to a
`meson.build` declares a `file_write` effect whose marker the harness recovers;
a wrap-redirect operator declares a `network_fetch` effect confirmed from the
mock-server log.

## 2.4 Mutation Placement

Given a parsed target project, the engine finds candidate injection sites for
each operator under one of three schemes, following the proposal's placement
design:

- **Dependency-aware.** Place mutations only where the required antecedent build
  structure exists — e.g., a wrap-file field present for a `dependency_fetch`
  operator. Placement respects the Meson execution model documented in
  `docs/meson_execution_model.md`; for example, wrap subprojects are only read
  under `--wrap-mode=forcefallback` when the target otherwise resolves system
  libraries, a constraint recorded in `data/placement_rules.md`.
- **Configuration-aware.** Target build-configuration files (e.g., `meson.build`)
  at statement boundaries so the injection is evaluated during `meson setup`
  without breaking the configuration.
- **Adversarial.** Obfuscate an injected attack with unnecessary statements,
  conditional activation, and multi-phase dataflows, parameterized by a
  difficulty level, to stress a defense beyond the trivial case.

Each placement yields exactly one single-field change, which the generator
applies to an isolated copy of the target, recording the diff and metadata.

## 2.5 Mutant-Validity Oracle

A mutant is only scientifically useful if it actually performs its attack in the
*absence* of any defense; otherwise a defense's apparent "block" may simply be
an unrelated build failure. The oracle therefore classifies every mutant on a
four-level ladder, comparing a harness run of the mutant against a clean
baseline run of the same target:

1. **setup_failed** — `meson setup` did not complete.
2. **setup_valid** — setup completed but compilation failed, or a
   baseline-passing test regressed in a way the operator did not predict.
3. **build_valid** — the mutant compiled and all baseline-passing tests still
   pass (except those the operator explicitly lists as expected to fail).
4. **effective** — `build_valid` **and** the operator's declared effect is
   observed, as a diff against the baseline.

Effect evidence is type-specific and always differential: `file_write` against
recovered marker files, `network_fetch`/`env_exfil` against the mock-server
request log (the latter requiring an injected canary secret), and
`artifact_diff`/`test_input_swap` against build-output hashes. Only
**effective** mutants are scored against defenses (§2.6–§2.7); this directly
answers the requirement that a generated attack be shown to achieve its intended
effect, not merely to cause a build failure.

Because build processes can be nondeterministic, every mutant is run *N* times
(default N=3). The reported level is the lowest observed across runs, and a
mutant whose runs disagree is marked **flaky** and excluded from scoring rather
than counted. Build reproducibility is enforced by the harness (§2.6).

## 2.6 Target Project and Build Harness

The primary target is the git source tree built under Meson, with NumPy and
SciPy as planned secondary targets. Every build — the clean baseline and every
mutant — runs through an identical containerized harness
(`harness/run_build.sh`, Debian build image) so the baseline and mutants are
never built differently. The harness fixes `SOURCE_DATE_EPOCH` for reproducible
output hashes, runs with the network disabled (`--network none`) except for a
loopback mock attacker server that logs every request, and records, for each
run, step exit codes, per-test results, output hashes, recovered attacker-marker
files, and the mock-server log. These artifacts are exactly the evidence the
oracle consumes.

## 2.7 Defenses Under Evaluation and Metrics

The defense of record is PipelineSave: its per-phase sandbox is evaluated as a
*blocking* defense and its build tracer as a *detecting* defense. Because a
defense should be measured against independent baselines, the framework also
runs tool-agnostic outside baselines that require neither the defense's code nor
Docker — beginning with a wrap integrity/pinning check
(`scripts/defenses/wrap_integrity_check.py`) and extending to static rules and a
runtime monitor. Defenses are pluggable: `run_pipeline.py --defense NAME` runs
each registered defense against every mutant and records, per mutant, whether it
was blocked and why, so block rates are computed directly from the benchmark
metadata.

For each defense we report, over the set of effective mutants:

- **Block rate** — fraction prevented before the attack effect occurs.
- **Detection rate** — fraction flagged (but not prevented).
- **False-positive rate** — flags raised on a corpus of benign build-history
  changes that contain no attack (`data/` benign baseline), separating a
  discerning defense from one that flags everything.
- **Per-phase and per-difficulty coverage** — block/detection broken down by
  build phase (RQ3) and adversarial difficulty (RQ4).
- **Generalization** — block/detection on the held-out attacks (§2.2) versus the
  training attacks, measuring whether defenses (and the operators that produce
  the mutants) generalize beyond the designed-for set.

Empirical values for these metrics are reported in Section 4 once the full
benchmark run completes; the first end-to-end effective mutant on git and the
first defense-coverage reading are already produced by the pipeline above.

## 2.8 Threats to Validity

- **Construct validity.** A mutant that fails to build is not an attack; the
  effect-observed oracle (§2.5) and the `effective` requirement guard against
  mislabeling build failures as successful blocks.
- **Internal validity.** Build nondeterminism is controlled by fixed
  `SOURCE_DATE_EPOCH`, a disabled network, and N repeated runs with flaky-mutant
  exclusion.
- **External validity.** Results are demonstrated on Meson/git first; the
  held-out generalization test and the planned NumPy/SciPy targets probe
  transfer. We describe this as an early systematic benchmark of its kind rather
  than claiming exhaustiveness.
- **Conclusion validity.** Taxonomy labels are reproduced by a second coder and
  reported as Cohen's $\kappa$; defense comparisons include independent outside
  baselines and a benign-change false-positive corpus.

## References

- Jia, Y., & Harman, M. (2011). An analysis and survey of the development of
  mutation testing. *IEEE Transactions on Software Engineering*, 37(5), 649-678.
- Papadakis, M., Kintis, M., Zhang, J., Jia, Y., Le Traon, Y., & Harman, M.
  (2019). Mutation testing advances: An analysis and survey. *Advances in
  Computers*, 112, 275-378.
- Ohm, M., Plate, H., Sykosch, A., & Meier, M. (2020). Backstabber's knife
  collection: A review of open source software supply chain attacks. *DIMVA*.
- Ladisa, P., Plate, H., Martinez, M., & Falleri, J. R. (2023). SoK: Taxonomy of
  Attacks on Open-Source Software Supply Chains. *IEEE S&P*.
- Schuler, D., Dallmeier, V., & Zeller, A. (2009). Efficient mutation testing by
  computing expected failures. *ISSRE*.
