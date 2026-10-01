"""
src/placement/adversarial.py

Finds injection candidates that combine dependency and configuration
awareness to create harder-to-detect attack locations.

Strategy: adversarial placements target locations that are both dependency-
relevant AND conditionally guarded, making the injection stealthy — it only
activates under specific build conditions (e.g., platform == 'linux' AND
the optional feature is enabled).

Owned by David.
"""


def find_adversarial_candidates(parsed_project: dict, operator: dict) -> list[dict]:
    """
    Find candidates using the adversarial placement strategy.

    Combines dependency and configuration context to find stealthy locations
    that require both conditions to trigger.

    Each returned candidate must include:
        scheme, file_path, field, current_value, placeholder_map
    (difficulty is assigned later by difficulty.py)

    Returns [] if no candidates apply.
    """
    # TODO (David): implement adversarial candidate discovery.
    return []
