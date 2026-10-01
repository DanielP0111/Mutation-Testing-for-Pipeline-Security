"""
src/placement/placer_api.py

Top-level placement API: finds all candidate injection locations for a given
operator in a parsed project, across all three placement strategies.

Owned by David.
"""

from .dependency_aware import find_dependency_candidates
from .config_aware import find_config_candidates
from .adversarial import find_adversarial_candidates
from .difficulty import assign_difficulty


def find_candidates(parsed_project: dict, operator: dict) -> list[dict]:
    """
    Find all candidate injection locations for the given operator.

    Args:
        parsed_project: dict returned by parse_project()
        operator: operator spec dict (loaded from YAML in data/operators/)

    Returns:
        List of candidate dicts. Each dict must contain:
            scheme         (str)  — which strategy found this candidate
            difficulty     (int)  — 1–4 rating assigned by difficulty.py
            file_path      (str)  — relative path to the file to modify
            field          (str)  — which field to change
            current_value  (str)  — current value of that field
            placeholder_map (dict) — maps {{PLACEHOLDER}} names to real values

        Returns [] if no valid candidates exist for this operator+project
        combination — do NOT raise an exception.
    """
    scheme = operator.get("scheme", "dependency_aware")
    raw_candidates: list[dict] = []

    if scheme in ("dependency_aware", "all"):
        raw_candidates.extend(find_dependency_candidates(parsed_project, operator))

    if scheme in ("config_aware", "all"):
        raw_candidates.extend(find_config_candidates(parsed_project, operator))

    if scheme in ("adversarial", "all"):
        raw_candidates.extend(find_adversarial_candidates(parsed_project, operator))

    # Assign difficulty ratings to every candidate
    candidates = [assign_difficulty(c, parsed_project) for c in raw_candidates]

    return candidates
