"""
src/engine/operator_loader.py

Loads mutation-operator specs from data/operators/. Each operator is one file,
either JSON (Debora's schema) or YAML — both are accepted so the operator
authors and the engine never block on a format choice.

A loaded operator is a plain dict. The loader does light validation only:
it checks that the fields the rest of the engine reads are present, so a
malformed spec fails here with a clear message instead of deep inside
template filling or mutant generation.
"""

import json
import sys
from pathlib import Path

import yaml

# Fields the engine itself consumes. Kept small on purpose: schema-level
# fields that are only for the paper/taxonomy (e.g. description, source_attacks)
# are not required here.
_REQUIRED_TOP = ("id", "scheme", "template")
_VALID_SCHEMES = ("dependency_aware", "config_aware", "adversarial", "all")
_VALID_MODES = ("replace", "delete_line", "insert_after", "append")
_VALID_OBSERVABLES = ("file_write", "network_fetch", "env_exfil",
                      "artifact_diff", "test_input_swap")
_VALID_CHECK_KEYS = ("marker", "request_path", "contains", "artifact",
                     "tests_may_fail")


def load_operator(file_path: str) -> dict:
    """
    Load and validate a single operator spec (JSON or YAML).

    Args:
        file_path: path to a .json / .yaml / .yml operator file.

    Returns:
        The operator dict, with a guaranteed "mode" key (defaults to "replace")
        and a guaranteed "attacker_values" dict (defaults to {}). If the
        operator has a schema-v3 "effect" block, it is validated and given
        default "check" ({}) and "requires" ([]) keys.

    Raises:
        FileNotFoundError: if the file does not exist.
        ValueError: if the file cannot be parsed, is not a mapping, is missing
                    a required field, or uses an unknown scheme/mode.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Operator spec not found: {file_path}")

    text = path.read_text(encoding="utf-8")
    try:
        if path.suffix.lower() == ".json":
            operator = json.loads(text)
        else:
            operator = yaml.safe_load(text)
    except (json.JSONDecodeError, yaml.YAMLError) as exc:
        raise ValueError(f"Could not parse operator spec {file_path}: {exc}")

    if not isinstance(operator, dict):
        raise ValueError(f"Operator spec {file_path} must be a mapping/object.")

    for field in _REQUIRED_TOP:
        if field not in operator:
            raise ValueError(f"Operator {file_path} missing required field '{field}'.")

    scheme = operator["scheme"]
    if scheme not in _VALID_SCHEMES:
        raise ValueError(
            f"Operator {file_path} has unknown scheme '{scheme}'. "
            f"Expected one of {_VALID_SCHEMES}."
        )

    mode = operator.setdefault("mode", "replace")
    if mode not in _VALID_MODES:
        raise ValueError(
            f"Operator {file_path} has unknown mode '{mode}'. "
            f"Expected one of {_VALID_MODES}."
        )

    operator.setdefault("attacker_values", {})
    if not isinstance(operator["attacker_values"], dict):
        raise ValueError(f"Operator {file_path} 'attacker_values' must be a mapping.")

    if "effect" in operator:
        _validate_effect(operator["effect"], file_path)

    return operator


def _validate_effect(effect, file_path: str) -> None:
    """Check the optional schema-v3 'effect' block; fill in defaults in place."""
    if not isinstance(effect, dict):
        raise ValueError(f"Operator {file_path} 'effect' must be a mapping.")
    obs = effect.get("observable")
    if obs not in _VALID_OBSERVABLES:
        raise ValueError(
            f"Operator {file_path} has unknown effect observable '{obs}'. "
            f"Expected one of {_VALID_OBSERVABLES}."
        )
    check = effect.setdefault("check", {})
    if not isinstance(check, dict):
        raise ValueError(f"Operator {file_path} 'effect.check' must be a mapping.")
    unknown = set(check) - set(_VALID_CHECK_KEYS)
    if unknown:
        raise ValueError(
            f"Operator {file_path} 'effect.check' has unknown key(s) {sorted(unknown)}. "
            f"Expected any of {_VALID_CHECK_KEYS}."
        )
    requires = effect.setdefault("requires", [])
    if not (isinstance(requires, list) and all(isinstance(r, str) for r in requires)):
        raise ValueError(f"Operator {file_path} 'effect.requires' must be a list of operator ids.")


def load_operators(operators_dir: str, strict: bool = False) -> list[dict]:
    """
    Load every operator spec in a directory (JSON and YAML), sorted by filename.

    Args:
        operators_dir: directory containing operator spec files
                       (e.g., "data/operators").

    Returns:
        A list of validated operator dicts.

    Raises:
        FileNotFoundError: if operators_dir does not exist.
    """
    root = Path(operators_dir)
    if not root.exists():
        raise FileNotFoundError(f"Operators directory not found: {operators_dir}")

    operators = []
    skipped = []
    for spec in sorted(root.iterdir()):
        if spec.suffix.lower() not in (".json", ".yaml", ".yml"):
            continue
        if strict:
            operators.append(load_operator(str(spec)))
            continue
        try:
            operators.append(load_operator(str(spec)))
        except (ValueError, FileNotFoundError) as exc:
            skipped.append(spec.name)
            print(f"WARNING: skipping malformed operator {spec.name}: {exc}",
                  file=sys.stderr)
    if skipped:
        print(f"WARNING: {len(skipped)} operator(s) skipped: "
              + ", ".join(skipped), file=sys.stderr)
    return operators
