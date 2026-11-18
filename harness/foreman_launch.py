#!/usr/bin/env python3
"""
Run the vendored Foreman (third_party/foreman/foreman.py, mounted read-only at
/work/foreman) inside the harness container, with compatibility shims and
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
# instead of crashing the whole analysis.
_orig = fm.is_file_in_any_paths


def _safe_is_file_in_any_paths(file, paths):
    try:
        return _orig(file, paths)
    except (FileNotFoundError, NotADirectoryError):
        f = file.absolute()
        return any(f == p.absolute() or p.absolute() in f.parents for p in paths)


# Shim 3 (speed only): the original walks every listed directory with rglob()
# for every touched file, which is O(touched x listed) and takes hours with a
# file-level policy on git. This equivalent check (same path or inside a listed
# directory, compared by path without resolving symlinks) gives the same
# answer in O(1).
# FOREMAN_EXACT=1 keeps the original.
_index: dict[int, tuple[set, list]] = {}


def _fast_is_file_in_any_paths(file, paths):
    key = id(paths)
    if key not in _index:
        exact, dirs = set(), []
        for p in paths:
            ap = os.path.abspath(str(p))
            exact.add(ap)
            if os.path.isdir(ap):
                dirs.append(ap.rstrip("/") + "/")
        _index[key] = (exact, dirs)
    exact, dirs = _index[key]
    f = os.path.abspath(str(file))
    return f in exact or any(f.startswith(d) for d in dirs)


# Shim 4: map_files_in_cwd_to_stats() calls Path.stat(), which follows
# symlinks and raises FileNotFoundError on a dangling one. GLib's build tree
# has these (e.g. build/girepository/libgirepository-2.0.so exists after setup,
# before the library it points to is linked), which crashed the whole run.
# Same walk, but a dangling link is recorded by its own lstat() instead; every
# other file gets exactly the stat() result it did before.
def _safe_map_files_in_cwd_to_stats():
    import pathlib
    result = {}
    for file in pathlib.Path.cwd().rglob("*"):
        try:
            result[file] = file.stat()
        except FileNotFoundError:
            try:
                result[file] = file.lstat()
            except FileNotFoundError:
                pass  # removed between the directory listing and the stat
    return result


fm.map_files_in_cwd_to_stats = _safe_map_files_in_cwd_to_stats

if os.environ.get("FOREMAN_EXACT"):
    fm.is_file_in_any_paths = _safe_is_file_in_any_paths
else:
    fm.is_file_in_any_paths = _fast_is_file_in_any_paths

sys.exit(fm.main())
