"""Run static 'outside baseline' defenses against mutant trees.

Each defense module under scripts/defenses/ exposes:
    learn(target_dir) -> manifest   (JSON-serialisable dict, from a CLEAN tree)
    check(target_dir, manifest) -> list[flag dicts]   (empty list => allowed)

A defense BLOCKS a mutant when check() returns at least one flag. These are
lightweight outside baselines (hash/URL pinning, lint rules) that need neither
Docker nor PipelineSave code, so they run whether or not --harness is set.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

_DEFENSE_DIR = Path(__file__).resolve().parent.parent.parent / "scripts" / "defenses"
_CACHE: dict[str, object] = {}


def available() -> list[str]:
    if not _DEFENSE_DIR.is_dir():
        return []
    return sorted(p.stem for p in _DEFENSE_DIR.glob("*.py")
                  if not p.stem.startswith("_"))


def _load(name: str):
    if name in _CACHE:
        return _CACHE[name]
    path = _DEFENSE_DIR / f"{name}.py"
    if not path.exists():
        raise ValueError(f"unknown defense '{name}'; available: "
                         + (", ".join(available()) or "none"))
    spec = importlib.util.spec_from_file_location(f"defenses.{name}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    for fn in ("learn", "check"):
        if not callable(getattr(mod, fn, None)):
            raise ValueError(f"defense '{name}' is missing a {fn}() function")
    _CACHE[name] = mod
    return mod


def learn_manifests(names, clean_target) -> dict:
    """Build each defense's trusted manifest from the clean target tree."""
    return {n: _load(n).learn(str(clean_target)) for n in names}


def run_defenses(names, mutant_dir, manifests) -> list[dict]:
    """Return [{name, blocked, flags}] for a single mutant tree."""
    out = []
    for n in names:
        flags = _load(n).check(str(mutant_dir), manifests[n])
        out.append({"name": n, "blocked": bool(flags), "flags": flags})
    return out
