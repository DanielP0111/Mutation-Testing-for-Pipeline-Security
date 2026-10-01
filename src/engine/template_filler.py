"""
src/engine/template_filler.py

Resolves {{PLACEHOLDER}} fields in an operator spec using the real values
from a chosen candidate location, producing a concrete change instruction.
"""

import re


def fill_template(operator: dict, candidate: dict) -> dict:
    """
    Resolve placeholders in an operator spec using a candidate's values.

    Args:
        operator:  operator spec dict (loaded from YAML in data/operators/)
        candidate: one candidate dict returned by find_candidates()

    Returns:
        A filled operator dict — no {{PLACEHOLDER}} fields remain:
        {
            "operator_id":       str,
            "operator_name":     str,
            "file_path":         str,   # resolved from placeholder
            "field":             str,
            "original_value":    str,
            "replacement_value": str,   # resolved from placeholder
            "scheme":            str,
            "difficulty":        int
        }

    Raises:
        ValueError: if any {{PLACEHOLDER}} cannot be resolved (i.e., the
                    operator's placeholders section and the candidate's
                    placeholder_map use mismatched keys).
    """
    placeholder_map = candidate.get("placeholder_map", {})

    def resolve(value: str) -> str:
        """Replace every {{KEY}} in value with the corresponding real value."""
        if not isinstance(value, str):
            return value
        for key, real_value in placeholder_map.items():
            value = value.replace(f"{{{{{key}}}}}", str(real_value))
        unresolved = re.findall(r"\{\{[^}]+\}\}", value)
        if unresolved:
            raise ValueError(
                f"Unresolved placeholders: {unresolved}. "
                f"Check that the operator's 'placeholders' section keys match "
                f"the candidate's placeholder_map keys."
            )
        return value

    template = operator.get("template", {})

    return {
        "operator_id":       operator.get("id", ""),
        "operator_name":     operator.get("name", ""),
        "file_path":         resolve(
            template.get("file_path", candidate.get("file_path", ""))
        ),
        "field":             candidate.get("field", ""),
        "original_value":    candidate.get("current_value", ""),
        "replacement_value": resolve(template.get("replacement_value", "")),
        "scheme":            candidate.get("scheme", ""),
        "difficulty":        candidate.get("difficulty", 1),
    }
