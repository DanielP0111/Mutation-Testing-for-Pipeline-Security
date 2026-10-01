"""
src/placement/config_aware.py

Finds injection candidates inside conditional blocks in meson.build files.

Strategy: configuration-aware placements target the conditional logic of
the build — if/elif blocks that gate platform-specific behavior, optional
features, or fallback dependencies.

Owned by David.
"""


def find_config_candidates(parsed_project: dict, operator: dict) -> list[dict]:
    """
    Find candidates using the configuration-aware placement strategy.

    Looks at parsed_project["conditionals"] for if/elif blocks where this
    operator's attack can be injected inside a guarded branch.

    Each returned candidate must include:
        scheme, file_path, field, current_value, placeholder_map
    (difficulty is assigned later by difficulty.py)

    Returns [] if no candidates apply.
    """
    # TODO (David): implement configuration-aware candidate discovery.
    return []
