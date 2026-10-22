"""
src/placement/dependency_aware.py

Finds injection candidates in wrap files and dependency declarations.

Strategy: dependency-aware placements target the supply-chain surface —
.wrap file URLs and hashes, and dependency() calls — where an attacker
could swap a legitimate source for a malicious one without changing the
build logic.

Owned by David, please ask if u have any questions.
"""

# Maps a wrap field name to the placeholder key operators use to reference
# its current value (see data/operators/op_001_wrap_source_url_swap.json and
# op_002_wrap_hash_removal.json). Extend this as new wrap-field operators are
# added. Any field not listed here falls back to ORIGINAL_<FIELD> so a new
# operator still works without a code change — just keep the operator spec's
# placeholder name in sync with whatever this produces.
_FIELD_PLACEHOLDERS = {
    "source_url": "ORIGINAL_URL",
    "source_hash": "ORIGINAL_HASH",
}

# source_url / source_hash are only real, literal lines in a [wrap-file]
# entry's text. wrap_parser.py also *synthesizes* a source_url for
# [wrap-git] entries (copied from their `url` field) so downstream code has
# one uniform field to read — but that value never actually appears as a
# "source_url = ..." line in the wrap file, it's the git clone `url =` line.
# Treating it as a candidate would silently rewrite a git URL under the
# wrong field name, which doesn't match what op_001/op_002 describe
# ("project has at least one [wrap-file] subproject with a source_url"),
# and meson would then try to git-clone the attacker URL, which hangs
# rather than failing fast, so these two fields are restricted to actual
# [wrap-file] wraps.
_WRAP_FILE_ONLY_FIELDS = {"source_url", "source_hash"}


def find_dependency_candidates(parsed_project: dict, operator: dict) -> list[dict]:
    """
    Find candidates using the dependency-aware placement strategy.

    Looks at parsed_project["wrap_files"] for locations where this
    operator's attack can be applied. (parsed_project["dependencies"] is
    not used yet — name-based dependency() targeting is a later extension,
    noted in data/placement_rules.md.)

    Each returned candidate must include:
        scheme, file_path, field, current_value, placeholder_map
    (difficulty is assigned later by difficulty.py)

    Returns [] if no candidates apply.
    """
    # Only handle operators meant for this scheme.
    if operator.get("scheme") not in ("dependency_aware", "all"):
        return []

    field = operator.get("injection_location", {}).get("field")
    if not field:
        return []

    placeholder_key = _FIELD_PLACEHOLDERS.get(field, f"ORIGINAL_{field.upper()}")

    candidates = []
    for wrap in parsed_project.get("wrap_files", []):
        if field in _WRAP_FILE_ONLY_FIELDS and wrap.get("type") != "wrap-file":
            # Field only has meaning on a real [wrap-file] entry (see note
            # on _WRAP_FILE_ONLY_FIELDS above) — skip [wrap-git] entries.
            continue

        current_value = wrap.get(field)
        if not current_value:
            # This wrap doesn't have the field this operator targets
            # (e.g. a [wrap-file] entry with no source_hash set) — skip it.
            continue

        candidates.append(
            {
                "scheme": "dependency_aware",
                "file_path": wrap["file_path"],
                "field": field,
                "current_value": current_value,
                "placeholder_map": {
                    "WRAP_FILE": wrap["file_path"],
                    placeholder_key: current_value,
                },
            }
        )

    return candidates
