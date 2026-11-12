"""
src/placement/difficulty.py

Assigns a difficulty rating (1-4) to each candidate based on placement
context. Higher difficulty means the injection is harder for a security
tool (or human reviewer) to detect.

Rating scale:
  1 - Main code path, no guards, obvious field (e.g., top-level source_url)
  2 - Inside one conditional branch, or non-obvious field
  3 - Nested conditional (depth >= 2), or adversarial combination
  4 - Deeply nested, platform-specific, and in a rarely-executed branch

See docs/difficulty_levels.md for the full writeup with worked examples.

Owned by David.
"""

# Fields a dependency_aware candidate can target where the field itself is
# an obvious, literal, top-level value (see dependency_aware.py's
# _FIELD_PLACEHOLDERS) — these score at the bottom of the scale.
_OBVIOUS_DEPENDENCY_FIELDS = {"source_url", "source_hash"}


def assign_difficulty(candidate: dict, parsed_project: dict) -> dict:
    """
    Assign a difficulty rating to a candidate dict in place.

    Args:
        candidate: candidate dict (must have 'scheme'; 'field' for
            dependency_aware; optionally 'depth' and 'platform_guard' for
            config_aware / adversarial — see note below).
        parsed_project: full parsed project dict (for context lookups;
            currently unused directly, kept for interface stability and so
            a future heuristic can look up broader project context without
            changing every caller).

    Returns:
        The same candidate dict with 'difficulty' set.

    Note on config_aware / adversarial candidates:
        config_aware.find_config_candidates() does not currently produce
        any candidates (see docs/config_aware_status.md), so in the live
        pipeline this branch is exercised only by direct unit tests today.
        Once (if) that function is implemented, each candidate it returns
        should carry a 'depth' key (the nesting depth of the gating
        conditional, from analyze_branch_reachability()/parsed_project
        ["conditionals"]) and, when applicable, a 'platform_guard' key
        (e.g. "linux"), so this function can score it. Missing either key
        is scored at the conservative (lower-difficulty) default: depth 1,
        no platform guard.
    """
    scheme = candidate.get("scheme")

    if scheme == "dependency_aware":
        field = candidate.get("field")
        candidate["difficulty"] = 1 if field in _OBVIOUS_DEPENDENCY_FIELDS else 2
        return candidate

    if scheme in ("config_aware", "adversarial"):
        depth = candidate.get("depth", 1)
        platform_guard = candidate.get("platform_guard")

        if scheme == "adversarial":
            # Combining a dependency context with a conditional guard is at
            # least as hard to spot as a single nested conditional.
            base = 3
        else:
            base = 2 if depth <= 1 else 3

        if depth >= 2 and platform_guard:
            candidate["difficulty"] = 4
        else:
            candidate["difficulty"] = base
        return candidate

    # Unknown/unrecognized scheme - conservative default.
    candidate["difficulty"] = 1
    return candidate
