"""
src/placement/difficulty.py

Assigns a difficulty rating (1–4) to each candidate based on placement
context. Higher difficulty means the injection is harder for a security
tool (or human reviewer) to detect.

Rating scale:
  1 — Main code path, no guards, obvious field (e.g., top-level source_url)
  2 — Inside one conditional branch, or non-obvious field
  3 — Nested conditional (depth ≥ 2), or adversarial combination
  4 — Deeply nested, platform-specific, and in a rarely-executed branch

Owned by David.
"""


def assign_difficulty(candidate: dict, parsed_project: dict) -> dict:
    """
    Assign a difficulty rating to a candidate dict in place.

    Args:
        candidate: candidate dict (must have 'scheme' and 'file_path')
        parsed_project: full parsed project dict (for context lookups)

    Returns:
        The same candidate dict with 'difficulty' set.
    """
    # TODO (David): implement real difficulty scoring.
    #
    # Suggested heuristics:
    #   - dependency_aware + no surrounding conditional → difficulty 1 or 2
    #   - config_aware + depth == 1 → difficulty 2
    #   - config_aware + depth >= 2 → difficulty 3
    #   - adversarial → difficulty 3 or 4
    #
    candidate["difficulty"] = 1  # placeholder — replace with real logic
    return candidate
