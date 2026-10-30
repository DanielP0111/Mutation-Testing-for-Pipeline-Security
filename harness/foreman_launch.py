#!/usr/bin/env python3
"""
Run the vendored Foreman (third_party/foreman/foreman.py, mounted read-only at
/work/foreman) inside the harness container, with two compatibility shims and
no change to Foreman's analysis. See third_party/foreman/NOTICE.md.

Usage (same flags as foreman.py):
    python3 foreman_launch.py -C /src -oi info.txt -ow warnings.txt
"""
import importlib.util
import os
import sys

FOREMAN = os.environ.get("FOREMAN_PY", "/work/foreman/foreman.py")

# Shim 1: os.reload_environ is new in Python 3.14 (image has 3.11). Foreman uses
# it to re-read its *own* environment between phases; child processes cannot
# change that environment, so the result is the same either way.
if not hasattr(os, "reload_environ"):
    os.reload_environ = lambda: None  # type: ignore[attr-defined]

spec = importlib.util.spec_from_file_location("foreman", FOREMAN)
fm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fm)  # type: ignore[union-attr]

# Shim 2: is_file_in_any_paths() calls samefile(), which raises for a file that
# was deleted during the phase. Fall back to the equivalent path-prefix test
# (no symlinks in the build tree) instead of crashing the whole analysis.
_orig = fm.is_file_in_any_paths


def _safe_is_file_in_any_paths(file, paths):
    try:
        return _orig(file, paths)
    except (FileNotFoundError, NotADirectoryError):
        f = file.absolute()
        return any(f == p.absolute() or p.absolute() in f.parents for p in paths)


fm.is_file_in_any_paths = _safe_is_file_in_any_paths

sys.exit(fm.main())
