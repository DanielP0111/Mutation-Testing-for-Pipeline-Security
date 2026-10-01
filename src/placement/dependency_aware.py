"""
src/placement/dependency_aware.py

Finds injection candidates in wrap files and dependency declarations.

Strategy: dependency-aware placements target the supply-chain surface —
.wrap file URLs and hashes, and dependency() calls — where an attacker
could swap a legitimate source for a malicious one without changing the
build logic.

Owned by David.
"""


def find_dependency_candidates(parsed_project: dict, operator: dict) -> list[dict]:
    """
    Find candidates using the dependency-aware placement strategy.

    Looks at parsed_project["wrap_files"] and parsed_project["dependencies"]
    for locations where this operator's attack can be applied.

    Each returned candidate must include:
        scheme, file_path, field, current_value, placeholder_map
    (difficulty is assigned later by difficulty.py)

    Returns [] if no candidates apply.
    """
    # TODO (David): implement dependency-aware candidate discovery.
    #
    # Example for a wrap-URL replacement operator:
    #   for wrap in parsed_project["wrap_files"]:
    #       if wrap["source_url"]:
    #           yield {
    #               "scheme": "dependency_aware",
    #               "file_path": wrap["file_path"],
    #               "field": "source_url",
    #               "current_value": wrap["source_url"],
    #               "placeholder_map": {
    #                   "WRAP_FILE": wrap["file_path"],
    #                   "ORIGINAL_URL": wrap["source_url"],
    #               },
    #           }
    return []
