"""
src/engine/reference_placement.py

A small, self-contained dependency-aware placement used by the pipeline driver
so the engine can run end-to-end TODAY, before David's full placement package
(src/placement/) is implemented.

It implements only the dependency-aware case for wrap-file fields (source_url,
source_hash). It produces candidates in exactly the shape find_candidates()
promises, so once src/placement/dependency_aware.py is finished the driver can
switch to it with no other change. This is engine scaffolding, not a substitute
for the placement workstream.
"""


import glob as _glob
import os as _os


def reference_find_candidates(parsed_project: dict, operator: dict) -> list[dict]:
    """
    Find dependency-aware candidates for a wrap-field operator.

    Reads operator["injection_location"]["field"] and matches it against each
    parsed wrap file. Returns candidate dicts with:
        scheme, file_path, field, current_value, placeholder_map
    """
    scheme = operator.get("scheme")
    if scheme in ("config_aware", "all"):
        cfg = _config_aware_candidates(parsed_project, operator)
        if scheme == "config_aware":
            return cfg
    else:
        cfg = []

    if scheme not in ("dependency_aware", "all"):
        return cfg

    loc = operator.get("injection_location", {})
    field = loc.get("field")
    if not field:
        return []

    candidates = list(cfg)
    for wrap in parsed_project.get("wrap_files", []):
        current = wrap.get(field)
        if not current:
            continue  # operator's field absent in this wrap — not a candidate

        placeholder_map = {
            "WRAP_FILE": wrap["file_path"],
        }
        # Expose the current value under a field-specific placeholder name so
        # operators can reference it (ORIGINAL_URL / ORIGINAL_HASH / ...).
        placeholder_map[f"ORIGINAL_{field.upper().replace('SOURCE_', '')}"] = current
        placeholder_map[f"ORIGINAL_{field.upper()}"] = current

        candidates.append(
            {
                "scheme": "dependency_aware",
                "file_path": wrap["file_path"],
                "field": field,
                "current_value": current,
                "placeholder_map": placeholder_map,
            }
        )

    return candidates


def _config_aware_candidates(parsed_project: dict, operator: dict) -> list[dict]:
    """Find meson.build files to receive a configure-stage injection.

    Reference scaffolding for config_aware operators (append/insert_after on a
    build file). Globs operator.injection_location.file_glob under the project
    root; defaults to the top-level meson.build.
    """
    root = parsed_project.get("project_dir")
    if not root:
        return []
    loc = operator.get("injection_location", {})
    pattern = loc.get("file_glob", "meson.build")
    field = loc.get("field", "configure_hook")
    recursive = "**" in pattern
    matches = _glob.glob(_os.path.join(root, pattern), recursive=recursive)
    out = []
    for path in sorted(matches):
        if not _os.path.isfile(path):
            continue
        rel = _os.path.relpath(path, root)
        out.append({
            "scheme": "config_aware",
            "file_path": rel,
            "field": field,
            "current_value": "",   # append mode does not match an anchor
            "placeholder_map": {"MESON_BUILD": rel},
        })
    return out
