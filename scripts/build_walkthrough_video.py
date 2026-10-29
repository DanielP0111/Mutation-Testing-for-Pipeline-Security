#!/usr/bin/env python3
"""
scripts/build_walkthrough_video.py

Builds the pipeline walkthrough video from docs/video/SCRIPT.md.

For each "## Scene NN" in SCRIPT.md:
  1. records a terminal running `trace_mutant.py --stage NN` with VHS -> out/scene_NN.mp4
  2. takes the narration (the "> " lines) as audio:
       docs/video/voice/scene_NN.m4a if you recorded one, else macOS `say` (placeholder)
  3. holds the last frame until the narration ends, muxes audio + video
then concatenates all scenes into docs/video/out/walkthrough.mp4.

    python scripts/build_walkthrough_video.py                 # build everything
    python scripts/build_walkthrough_video.py --scenes 3 6    # rebuild some scenes, re-concat
    python scripts/build_walkthrough_video.py --record-voice  # record narration per scene (mic)
    python scripts/build_walkthrough_video.py --record-voice --scenes 6

Needs: vhs and ffmpeg (brew install vhs ffmpeg); `say` (macOS) only for the placeholder voice.
"""

import argparse
import json
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VIDEO = ROOT / "docs" / "video"
SCRIPT = VIDEO / "SCRIPT.md"
OUT = VIDEO / "out"
VOICE = VIDEO / "voice"

DEFAULTS = {
    "mutant": "git_configure_marker_injection_0002",
    "benchmark": "data/benchmark_video",
    "baseline": "data/evaluation/baseline_ff",
}


def parse_scenes():
    scenes, cur = [], None
    for line in SCRIPT.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^## Scene (\d+)\s*·\s*(.+)$", line)
        if m:
            cur = {"num": int(m.group(1)), "title": m.group(2).strip(), "lines": []}
            scenes.append(cur)
        elif cur and line.startswith(">"):
            cur["lines"].append(line[1:].strip())
    for s in scenes:
        s["text"] = "\n".join(s["lines"]).strip()
    return scenes


def need(tool, why):
    if not shutil.which(tool):
        sys.exit(f"'{tool}' not found ({why}). Install with: brew install {tool}")


def run(cmd, **kw):
    print(" $", " ".join(shlex.quote(str(c)) for c in cmd))
    return subprocess.run(cmd, check=True, **kw)


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "json", str(path)], capture_output=True, text=True, check=True)
    return float(json.loads(out.stdout)["format"]["duration"])


def record_terminal(args, scene):
    """Write a VHS tape for the scene and render it."""
    n = scene["num"]
    tape = OUT / f"scene_{n:02d}.tape"
    mp4 = OUT / f"scene_{n:02d}_raw.mp4"
    venv = ROOT / ".venv" / "bin" / "activate"
    # Paths go in env vars (read by trace_mutant.py) during the hidden setup, so the
    # command typed on camera stays short.
    setup = (f"cd {shlex.quote(str(ROOT))}"
             + (f" && source {shlex.quote(str(venv))}" if venv.exists() else "")
             + f" && export TRACE_MUTANT={args.mutant} TRACE_BENCHMARK={args.benchmark}"
               f" TRACE_BASELINE={args.baseline} TRACE_COLOR=always")
    tape.write_text("\n".join([
        f'Output "{mp4}"',
        'Set Shell "bash"',
        f"Set FontSize {args.font_size}",
        "Set Width 1920",
        "Set Height 1080",
        "Set Padding 36",
        f'Set Theme "{args.theme}"',
        "Set TypingSpeed 35ms",
        "Hide",
        f'Type "{setup} && clear"',
        "Enter",
        "Sleep 1s",
        "Show",
        f'Type "python scripts/trace_mutant.py --stage {n}"',
        "Sleep 600ms",
        "Enter",
        f"Sleep {args.hold}s",
        "",
    ]))
    run(["vhs", str(tape)])
    return mp4


def placeholder_voice(scene):
    need("say", "placeholder narration needs macOS `say`; or record with --record-voice")
    aiff = OUT / f"scene_{scene['num']:02d}_tts.aiff"
    txt = OUT / f"scene_{scene['num']:02d}.txt"
    txt.write_text(scene["text"].replace("\n", " "), encoding="utf-8")
    run(["say", "-r", "172", "-o", str(aiff), "-f", str(txt)])
    return aiff


def voice_for(scene):
    rec = VOICE / f"scene_{scene['num']:02d}.m4a"
    if rec.exists():
        print(f"   using your recording: {rec.relative_to(ROOT)}")
        return rec
    print("   no recording found, using placeholder `say` voice")
    return placeholder_voice(scene)


def mux(scene, video, audio):
    n = scene["num"]
    out = OUT / f"scene_{n:02d}.mp4"
    vd, ad = duration(video), duration(audio)
    target = max(vd, ad + 1.0)
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-i", str(audio),
         "-filter_complex",
         f"[0:v]tpad=stop_mode=clone:stop_duration={target - vd + 0.5:.2f},fps=30[v];"
         f"[1:a]aresample=48000,apad[a]",
         "-map", "[v]", "-map", "[a]", "-t", f"{target:.2f}",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium", "-crf", "20",
         "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2", str(out)])
    return out


def concat(scenes):
    parts = [OUT / f"scene_{s['num']:02d}.mp4" for s in scenes]
    missing = [p.name for p in parts if not p.exists()]
    if missing:
        print(f"skipping final concat; missing: {', '.join(missing)}")
        return
    lst = OUT / "concat.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in parts))
    final = OUT / "walkthrough.mp4"
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
         "-i", str(lst), "-c", "copy", str(final)])
    print(f"\nDone: {final.relative_to(ROOT)}  ({duration(final) / 60:.1f} min)")


def record_voice(scenes, mic):
    need("ffmpeg", "used to record from the microphone")
    VOICE.mkdir(parents=True, exist_ok=True)
    for s in scenes:
        dest = VOICE / f"scene_{s['num']:02d}.m4a"
        print("\n" + "=" * 72)
        print(f"Scene {s['num']:02d} · {s['title']}" + ("   (re-recording)" if dest.exists() else ""))
        print("=" * 72)
        print(s["text"])
        print("=" * 72)
        ans = input("[Enter] start recording · s = skip · x = quit: ").strip().lower()
        if ans == "x":
            return
        if ans == "s":
            continue
        print("Recording… press q to stop.")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "avfoundation",
                        "-i", f":{mic}", "-ac", "1", "-c:a", "aac", "-b:a", "160k", str(dest)])
        print(f"saved {dest.relative_to(ROOT)} ({duration(dest):.0f}s)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scenes", type=int, nargs="*", help="only these scene numbers")
    ap.add_argument("--record-voice", action="store_true", help="record narration from the mic")
    ap.add_argument("--mic", default="0", help="avfoundation audio device index (default 0)")
    ap.add_argument("--mutant", default=DEFAULTS["mutant"])
    ap.add_argument("--benchmark", default=DEFAULTS["benchmark"])
    ap.add_argument("--baseline", default=DEFAULTS["baseline"])
    ap.add_argument("--theme", default="Catppuccin Mocha")
    ap.add_argument("--font-size", type=int, default=20)
    ap.add_argument("--hold", type=float, default=4.0,
                    help="seconds the terminal is recorded after output (frame then held for narration)")
    args = ap.parse_args()

    scenes = parse_scenes()
    if not scenes:
        sys.exit(f"no '## Scene NN' sections found in {SCRIPT}")
    chosen = [s for s in scenes if not args.scenes or s["num"] in args.scenes]

    if args.record_voice:
        record_voice(chosen, args.mic)
        return

    need("vhs", "records the terminal")
    need("ffmpeg", "muxes audio and video")
    if not (ROOT / args.benchmark / args.mutant / "metadata.json").exists():
        sys.exit(f"mutant not found: {args.benchmark}/{args.mutant}\n"
                 f"run the 'Before recording' step in docs/video/SCRIPT.md, or pass "
                 f"--benchmark/--baseline/--mutant for an existing run")
    OUT.mkdir(parents=True, exist_ok=True)
    for s in chosen:
        print(f"\n== Scene {s['num']:02d} · {s['title']}")
        mux(s, record_terminal(args, s), voice_for(s))
    concat(scenes)


if __name__ == "__main__":
    main()
