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


def reference_find_candidates(parsed_project: dict, operator: dict) -> list[dict]:
    """
    Find dependency-aware candidates for a wrap-field operator.

    Reads operator["injection_location"]["field"] and matches it against each
    parsed wrap file. Returns candidate dicts with:
        scheme, file_path, field, current_value, placeholder_map
    """
    if operator.get("scheme") not in ("dependency_aware", "all"):
        return []

    loc = operator.get("injection_location", {})
    field = loc.get("field")
    if not field:
        return []

    candidates = []
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
