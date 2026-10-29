# Pipeline walkthrough video: script and shot list

This is a mechanistic walkthrough of the mutation-testing pipeline. It traces **one real mutant** from the attack it models to the defense verdict, showing the real artifacts at every stage.

- **Mutant shown:** op_013, `configure_marker_injection`, which models Octopus Scanner and the XZ configure hook. It is the one mutant that reached **effective**, so every stage has real output to show.
- **Length:** about 9–11 minutes, in 10 scenes.
- **How it's made:** `scripts/build_walkthrough_video.py` turns this file into the video. Each scene runs `scripts/trace_mutant.py --stage N` in a recorded terminal (VHS), then lays the narration below over it. Lines starting with `>` are the narration; everything else is notes for you.

## Before recording (one time)

1. **Rebuild the baseline with the same wrap mode as the mutants.** The current `data/evaluation/baseline` was built without `--wrap-mode=forcefallback`, so its output hashes don't match the mutants'. `trace_mutant.py` stage 6 flags this. Also re-run op_013 and the fixed op_005 against the new baseline (this takes roughly 30–40 minutes):
   ```bash
   source .venv/bin/activate
   mkdir -p /tmp/video_ops && cp data/operators/op_005_*.json data/operators/op_013_*.json /tmp/video_ops/
   python scripts/run_pipeline.py --target data/targets/git --operators /tmp/video_ops \
     --out data/benchmark_video --reference-placement --harness \
     --baseline data/evaluation/baseline_ff --wrap-mode forcefallback --runs 3 \
     --defense wrap_integrity_check
   ```
   This creates `data/benchmark_video/git_configure_marker_injection_0002`, which is the build script's default mutant. If op_005 also comes back effective, you can swap it in with `--mutant git_netbeans_build_script_tampering_0001` to show a compile-phase example.
2. **Install the recording tools:** `brew install vhs ffmpeg`.
3. **Preview every stage once:**
   ```bash
   python scripts/trace_mutant.py --benchmark data/benchmark_video \
     --baseline data/evaluation/baseline_ff --mutant git_configure_marker_injection_0002 --pause
   ```
   Stage 6 should show **no red warning**, and "output hashes changed" should read **none**. If it doesn't, note it in scene 6's narration rather than hiding it.

## Building the video

```bash
# 1. record your voice, one scene at a time: prints the narration, Enter to start, q to stop
python scripts/build_walkthrough_video.py --record-voice
# 2. render: terminal recordings + your voice -> docs/video/out/walkthrough.mp4
python scripts/build_walkthrough_video.py
```

If you skip step 1, the build uses macOS `say` as a placeholder voice, which is good enough for checking timing. To redo one scene, use `--scenes 6` for either command. Recordings are saved as `docs/video/voice/scene_NN.m4a`, and a recording always wins over the placeholder voice.

---

## Scene 00 · Overview

**Command:** `trace_mutant.py --stage 0`
**On screen:** the mutant name, its operator, the target, the final verdict, and the 7-step chain.

> This is a mechanistic walkthrough of our pipeline for adversarial mutation testing of build-pipeline defenses. Instead of describing each component in the abstract, I'm going to follow one real mutant all the way through, from the real-world attack it models to the verdict a defense gives it. Everything on screen is the actual output our pipeline produced. Nothing is mocked up.
> The mutant we'll follow comes from operator thirteen, a configure-stage build-script injection, applied to git, which is our target project. It ended up classified as effective, the strongest level, so we can see every stage do real work. The chain is: taxonomy, operator, placement, mutant, harness, oracle, and defense.

## Scene 01 · Taxonomy

**Command:** `trace_mutant.py --stage 1`
**On screen:** ATK-005 Octopus Scanner, ATK-001 XZ Utils, their phase and pattern labels, and the kappa line.

> Everything starts from the taxonomy: a catalogue of documented supply-chain incidents. Each one gets an ID, the build phase it hit, how the attack got in, and a dataflow pattern.
> Our operator models two of them. Octopus Scanner, ATK-005, was malware that modified project build descriptors so every build ran attacker code. XZ Utils, ATK-001, hid its backdoor in the configure step. Both were labeled with the configure phase.
> Because these phase labels drive the whole evaluation, they're double-coded. Rejoice labeled all fifteen incidents, and a second coder relabeled them without seeing hers. They agreed on fifteen out of fifteen, which gives a Cohen's kappa of one. Kappa measures agreement after subtracting what you'd expect by chance, so one means perfect agreement.

## Scene 02 · Operator

**Command:** `trace_mutant.py --stage 2`
**On screen:** each field of the op_013 JSON.

> Next, the attack's mechanism is abstracted into an operator: a JSON rule for injecting that kind of attack into any Meson project.
> Reading the fields: the target build phase is configure. The scheme is config-aware, meaning it edits build scripts rather than dependency files. The injection location is the top-level meson dot build, and the mode is append, so it adds a line at the end of the file.
> The template is the payload: a run-command call that Meson executes during setup. It shells out and writes a marker file named PWNED underscore configtime into slash tmp. It's a harmless stand-in for "attacker code ran during the build," and the placeholder in double braces gets filled in later.
> The most important field is the effect block. It declares what proves the attack worked: an observable of file write, checked by looking for that specific marker. Without an effect block, a mutant can never be classified as effective.

## Scene 03 · Placement

**Command:** `trace_mutant.py --stage 3`
**On screen:** the parsed target, 1 candidate, and the filled template.

> Placement answers: where in this specific project can this operator go? This stage runs live. A parser reads git's build files, including its five dependency wrap files and the top-level meson dot build. Then the config-aware placement looks for files matching the operator's glob.
> For this operator, there's exactly one candidate: meson dot build at the project root. The template's placeholders are then filled with that candidate's real values: the file path, and the marker ID git zero zero one. What comes out is a concrete instruction: append this exact line to this exact file.
> Operators that target wrap files instead find one candidate per dependency, which is why the wrap operators produce five mutants each on git.

## Scene 04 · Mutant

**Command:** `trace_mutant.py --stage 4`
**On screen:** mutant metadata and the colored `change.diff`.

> The generator copies the entire git project and applies exactly one change. That copy is the mutant.
> Here's the diff against the original: one added line at the very end of meson dot build. Nothing else in the project is touched. Next to the mutant we save metadata dot json, which records the operator, the file, the mode, and the before and after values, and this change dot diff.
> One change per mutant is deliberate. When a defense blocks or misses this mutant, we know exactly which single attack step it was responding to.

## Scene 05 · Harness

**Command:** `trace_mutant.py --stage 5`
**On screen:** the docker command, the in-container steps, and run1's evidence.
**Optional:** cut in a short clip of a live `docker run` scrolling, sped up.

> Now the mutant gets built for real. The harness runs it in a Docker container with networking turned off. Inside, a mock attacker server listens on localhost and logs every request, so we can see network attacks without letting anything out.
> The container runs the same steps for every build: download subprojects, meson setup, meson compile, hash the build outputs, run the test suite, and finally scan the filesystem for any file whose name starts with PWNED.
> For this mutant, every step exited with zero, all four git tests passed, the mock server got no requests, and one marker file appeared: slash tmp slash PWNED underscore configtime underscore git zero zero one. The whole thing runs three times, to catch flaky builds.

## Scene 06 · Oracle

**Command:** `trace_mutant.py --stage 6`
**On screen:** the baseline-vs-mutant table, the ladder, and the 3 runs.

> Seeing a marker isn't enough on its own. The oracle compares the mutant's evidence against a clean baseline: unmodified git, built in the same harness with the same settings.
> Row by row: setup and compile succeeded in both. All four tests pass in both, so nothing newly fails. The baseline produced no markers, and the mutant produced one new one. No new network requests, and no build outputs changed.
> That places it on our validity ladder. Setup failed means the mutation broke configuration. Setup valid means it configured, but the compile or a previously passing test broke, which a real attacker would avoid because broken builds get noticed. Build valid means the build looks completely normal. Effective means build valid and the declared effect was observed.
> All three runs reached effective with the same evidence, and since the final level is the lowest across runs, the verdict is effective. Only effective mutants get scored against defenses, so every block we report is a real, working, stealthy attack being stopped.

## Scene 07 · Defense

**Command:** `trace_mutant.py --stage 7`
**On screen:** the recorded verdict, then a live re-run of the wrap integrity check.

> Last, the defenses. Each defense is a plug-in with the same contract: given a mutant, return whether it blocked it, plus flags explaining why. The pipeline stores that in the mutant's metadata.
> Here it's the wrap integrity check, our first outside baseline. It works in two steps, shown live. First, learn: read clean git's wrap files and record every trusted download host and hash. Second, check: compare the mutant's wrap files to that manifest.
> Its verdict is allowed, and that's the correct answer. This attack lives in meson dot build, not in a dependency, so an integrity check on dependencies has nothing to catch. That's exactly the kind of coverage gap the benchmark exists to expose. A defense focused on build scripts or file writes, like PipelineSave's tracer, is what should catch this one, and it plugs in the same way once we have its code.

## Scene 08 · Caveat: wrap no-ops

**Command:** `trace_mutant.py --stage 8`
**On screen:** the unpacked dependency folders and "Already downloaded" in the fetch log.

> One finding from our first full run, because it affects the numbers. Our fifteen wrap-file mutants, which attack the dependency download step, all came back build valid and never effective.
> The reason is right here. git's subprojects folder already contains every dependency unpacked: curl, expat, openssl, pcre2, zlib. So Meson prints "Already downloaded" and never reads the wrap file again. Our edits to the download URL or hash changed a file the build doesn't use. Those mutants were no-ops.
> The fix is to build every mutant and the baseline from a copy without those unpacked folders, so Meson really processes the wraps. For the redirect attack, it also means updating the filename and hash together, the way an attacker controlling the download mirror would.

## Scene 09 · Summary

**Command:** `trace_mutant.py --stage 9`
**On screen:** the one-screen chain from incident to verdict.

> To recap the whole mechanism in one line: two real incidents, Octopus Scanner and XZ, became one operator. Placement found one spot in git. The generator made one change. The harness built and tested it three times in isolation. The oracle confirmed against a clean baseline that the attack ran while the build stayed normal. And the defense gave its verdict, which counts toward its score because the attack was effective.
> Every other mutant goes through exactly the same path. The benchmark's results are this trace, repeated across every operator, every placement, and every defense.
