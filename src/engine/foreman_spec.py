"""
src/engine/foreman_spec.py

Foreman phase specifications for the harness.

The harness runs four phases, each one step of harness/step.sh:
    fetch -> setup -> compile -> test

A *spec* file (JSON) holds per-phase Foreman permissions:

    {"phases": {"compile": {"file": {"restricted": ["/src/t/"]}}, ...},
     "learn": false}

`to_build_phases()` turns it into Foreman's own build_phases.json format.
`learn_from_info()` derives a spec from a CLEAN run's Foreman info log: each
phase is restricted from every top-level entry of the source tree it did not
touch in the clean build (deny-what-wasn't-needed, at directory granularity).
"""
from __future__ import annotations

import json
from pathlib import Path

PHASES = ("fetch", "setup", "compile", "test")
SRC = "/src"
# Entries never restricted: the build output dir and Foreman's own spec file.
NEVER_RESTRICT = {"build", "build_phases.json"}


def load_spec(path: str | Path) -> dict:
    spec = json.loads(Path(path).read_text(encoding="utf-8"))
    spec.setdefault("phases", {})
    return spec


def needs_learning(spec: dict) -> bool:
    return bool(spec.get("learn")) or not any(spec.get("phases", {}).values())


def learn_granularity(spec: dict) -> str:
    return spec.get("learn") if spec.get("learn") in ("dirs", "files") else "dirs"


def to_build_phases(spec: dict) -> list[dict]:
    out = []
    for name in PHASES:
        phase = {"name": name, "commands": [["bash", "/work/harness/step.sh", name]]}
        perms = spec.get("phases", {}).get(name)
        if perms:
            phase["permissions"] = perms
        out.append(phase)
    return out


def parse_info_line(line: str) -> tuple[str, str] | None:
    """'compile accessed and modified /src/x/y.c' -> ('compile', '/src/x/y.c')."""
    parts = line.strip().split()
    if len(parts) < 3 or parts[0] not in PHASES:
        return None
    return parts[0], parts[-1]


def learn_from_info(info_path: str | Path, target_dir: str | Path,
                    granularity: str = "dirs") -> dict:
    """granularity="dirs": restrict top-level entries a phase never touched.
    granularity="files": permit exactly the files a phase touched (plus build/);
    any other file the phase touches is a violation."""
    if granularity == "files":
        return _learn_files(info_path, target_dir)
    touched: dict[str, set[str]] = {p: set() for p in PHASES}
    for line in Path(info_path).read_text(encoding="utf-8", errors="replace").splitlines():
        parsed = parse_info_line(line)
        if not parsed:
            continue
        phase, path = parsed
        if not path.startswith(SRC + "/"):
            continue
        rel = path[len(SRC) + 1:]
        # Skip directories: Foreman's own between-phase scan lists every
        # directory, which bumps their access times, so a directory showing up
        # as "accessed" says nothing about the build. Only files count.
        if (Path(target_dir) / rel).is_dir():
            continue
        top = rel.split("/", 1)[0]
        touched[phase].add(top)

    entries = sorted(p.name for p in Path(target_dir).iterdir()
                     if p.name not in NEVER_RESTRICT and not p.name.startswith(".git"))
    phases = {}
    for phase in PHASES:
        restricted = [f"{SRC}/{e}" + ("/" if (Path(target_dir) / e).is_dir() else "")
                      for e in entries if e not in touched[phase]]
        if restricted:
            phases[phase] = {"file": {"restricted": restricted}}
    return {"learn": False,
            "learned_from": str(info_path),
            "policy": "restrict each phase from top-level entries it did not touch in the clean build",
            "phases": phases}


def read_warnings(run_dir: str | Path) -> list[str]:
    p = Path(run_dir) / "foreman_warnings.txt"
    if not p.exists():
        return []
    return [l.strip() for l in p.read_text(encoding="utf-8", errors="replace").splitlines() if l.strip()]


def _learn_files(info_path: str | Path, target_dir: str | Path) -> dict:
    touched: dict[str, set[str]] = {p: set() for p in PHASES}
    for line in Path(info_path).read_text(encoding="utf-8", errors="replace").splitlines():
        parsed = parse_info_line(line)
        if not parsed:
            continue
        phase, path = parsed
        if not path.startswith(SRC + "/"):
            continue
        rel = path[len(SRC) + 1:]
        if rel.split("/", 1)[0] in NEVER_RESTRICT:
            continue  # build outputs differ run to run; build/ is permitted wholesale
        if (Path(target_dir) / rel).is_dir():
            continue  # directory atime noise from Foreman's own scan
        touched[phase].add(path)
    phases = {}
    for phase in PHASES:
        permitted = sorted(touched[phase]) + [f"{SRC}/build/", f"{SRC}/build_phases.json"]
        phases[phase] = {"file": {"permitted": permitted}}
    return {"learn": False,
            "learned_from": str(info_path),
            "policy": "permit each phase exactly the source files it touched in the clean build (+ build/)",
            "phases": phases}
