1. Dependency source or package-download manipulation
If: The attack introduces or changes a dependency, package source, download location, registry entry, or dependency version.

Abstraction rule: Replace a specific package or dependency name with {{PACKAGE_NAME}}; a version with {{PACKAGE_VERSION}}; a malicious or attacker-controlled download address with {{MALICIOUS_URL}}; and a registry or repository host with {{PACKAGE_SOURCE}}. Preserve the operation being performed, such as changing a source URL, adding a dependency, or changing a version constraint.

Locator rule: First locate the dependency declaration actually changed. For Meson subprojects, check subprojects/{{PACKAGE_NAME}}.wrap and its url= or source_url= field when present. Otherwise check the relevant package manifest, lockfile, registry metadata, vendored dependency configuration, or fetch script. Do not assume the Meson .wrap path for npm, PyPI, or other ecosystems.

2. Install-time hooks and build/configuration script injection
If: Malicious behavior is introduced through an install hook, lifecycle script, configure macro, build descriptor, or CI workflow command.

Abstraction rule: Replace package names with {{PACKAGE_NAME}}, filenames with {{BUILD_FILE}}, hook or macro names with {{HOOK_NAME}}, injected commands with {{INJECTED_COMMAND}}, and environment-specific activation checks with {{ACTIVATION_CONDITION}}. Keep whether execution happens during fetch/install, configure, test, or release build.

Locator rule: Locate the exact execution entry point evidenced by the record. Check package lifecycle fields and referenced scripts (for example, package.json scripts such as preinstall), Autoconf input such as configure.ac or m4/ macros, project build descriptors, and CI workflow files. For GitHub Actions, inspect the workflow step and the expression-to-shell boundary. Do not name a specific file unless the incident evidence supports it.

3. Source-code or build-input tampering
If: Source files are changed without an authorized source-control change, or the files compiled differ from the reviewed revision.

Abstraction rule: Replace repository names with {{REPOSITORY}}, source filenames with {{SOURCE_FILE}}, function or code locations with {{CODE_LOCATION}}, commit IDs with {{APPROVED_REVISION}} and {{OBSERVED_REVISION}}, and inserted code with {{UNAUTHORIZED_CODE}}. Preserve the key relationship: approved source versus actual build input.

Locator rule: Compare the affected file and its content hash against the reviewed commit, then locate the source-control event, workspace write, build-worker event, or compiler input manifest that explains the difference. Candidate locations include the named source file, repository history, working tree, generated-source directory, and build logs. If files were swapped only briefly during compilation, use host/process telemetry and recorded compiler inputs rather than relying only on the final repository state.

4. Compiler, toolchain, or build-worker compromise
If: A compiler, linker, compiler runtime, build tool, or worker process is suspected of altering outputs or injecting code.

Abstraction rule: Replace tool names with {{TOOLCHAIN_COMPONENT}}, versions with {{TOOLCHAIN_VERSION}}, worker names with {{BUILD_WORKER}}, target binaries with {{OUTPUT_ARTIFACT}}, and injected behavior with {{INJECTED_BEHAVIOR}}. Generalize any named compiler or vendor while preserving whether the compromise affects tool execution, source inputs, or output generation.

Locator rule: Start with the executable or runtime actually used by the build and its identity/hash, then inspect the worker process tree, compiler invocation records, toolchain installation source, and output provenance. Compare a controlled rebuild in an independently trusted environment. Do not assume the compiler itself is the locator if evidence instead points to a compromised worker or runtime routine.

5. Credential and environment-data collection or exfiltration
If: A build script, dependency, test process, or shared runner reads secrets, environment variables, process memory, or credentials and exposes them to an unauthorized recipient.

Abstraction rule: Replace secret names and values with {{SECRET_NAME}} and {{SECRET_VALUE}}; environment variable names with {{ENV_VAR_NAME}}; external destinations with {{EXFILTRATION_URL}}; and process or runner identifiers with {{BUILD_PROCESS}} and {{CI_RUNNER}}. Never copy actual secret values into an abstract operator or report.

Locator rule: Locate the code or process that reads the sensitive data and the outbound sink or unauthorized reader. Check the implicated test/build script, dependency install code, CI step, runner environment, process-access telemetry, and network egress logs. For a secret-to-network pattern, record both source and sink; a secret read alone does not prove exfiltration.

6. Release artifact, archive, or bundled-library substitution
If: A binary, library, archive, installer, or package is modified or replaced after the trusted build output or approved component has been established.

Abstraction rule: Replace product names with {{PRODUCT_NAME}}, artifact filenames with {{ARTIFACT_NAME}}, component filenames with {{COMPONENT_NAME}}, hashes with {{EXPECTED_HASH}} and {{OBSERVED_HASH}}, and signing identities with {{SIGNING_IDENTITY}}. Preserve whether the operation is insertion, replacement, repackaging, or modification before signing.

Locator rule: Compare the published or signed artifact with the approved build output and component manifest. Inspect the packaging/installer assembly step, archive contents, staging directory, bundled-library path, signing input, and release-upload record. A valid signature identifies a signing event or identity; it does not by itself prove that the contents are trustworthy. Use a specific path only when the record identifies it.

7. Conditional or dormant payload activation
If: Malicious behavior is activated only in a particular environment, release process, target application, or build context.

Abstraction rule: Replace concrete environment values with {{ENVIRONMENT_CONDITION}}, release or application names with {{TARGET_CONTEXT}}, and the payload with {{PAYLOAD_BEHAVIOR}}. Preserve the condition that distinguishes the triggering build from an ordinary build.

Locator rule: Locate the conditional branch, build profile, lifecycle hook, release-only step, or target-specific bundling stage that gates execution. Compare logs and behavior across controlled contexts, such as ordinary versus release builds, without assuming that conditional behavior is malicious by itself. If the record says only that activation is context-dependent, report the locator as a hypothesis until the exact gate is found.

8. Trust-boundary crossing and multi-stage attack chain
If: An untrusted dependency, pull request, developer workstation, build worker, or upstream service influences a more trusted build, signing, secret, or release operation.

Abstraction rule: Replace actor identities with {{ACTOR}}, trust zones with {{SOURCE_TRUST_ZONE}} and {{DESTINATION_TRUST_ZONE}}, the affected workflow with {{BUILD_WORKFLOW}}, and the resulting action with {{PRIVILEGED_ACTION}}. Represent the chain as input → execution or modification → sensitive effect, using the specific stages supported by evidence.

Locator rule: Trace the path across the relevant boundary: source or dependency acquisition, configuration, compilation, testing, packaging, signing, and publication. Identify the first untrusted input, the process or file that carries its influence, and the privileged sink. Correlate using build/job IDs, timestamps, source revisions, process ancestry, and artifact hashes. Do not claim a causal chain from timing alone.

Decision tree for selecting a rule
1. Did a dependency declaration, package source, or downloaded component change? Use Rule 1.
2. Did a hook, macro, build descriptor, or CI command introduce execution? Use Rule 2.
3. Did actual compiled source differ from approved source? Use Rule 3.
4. Is the compiler, toolchain, runtime, or build worker the suspected source of altered output? Use Rule 4.
5. Was sensitive environment data accessed or sent to an unauthorized destination? Use Rule 5.
6. Was a built, bundled, signed, archived, or published artifact modified or substituted? Use Rule 6.
7. Does the behavior depend on a specific build/release context or activation condition? Add Rule 7.
8. Does the attack cross a trust boundary or connect multiple stages? Add Rule 8.
Apply more than one rule when the evidence supports multiple behaviors. Select the primary rule based on the earliest evidenced malicious change; use secondary rules for downstream effects. Keep uncertain locators explicitly marked as candidates rather than presenting them as guaranteed paths.
