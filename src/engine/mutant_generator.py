"""
src/engine/mutant_generator.py

Applies a filled operator to a target project, producing a concrete mutant:
a copy of the project with exactly one field changed.
"""

import shutil
from pathlib import Path


def generate_mutant(
    project_dir: str,
    filled_operator: dict,
    out_dir: str,
) -> dict:
    """
    Copy project_dir to out_dir and apply the single-field change described
    by filled_operator.

    Args:
        project_dir:     root of the original (unmodified) project
        filled_operator: dict returned by fill_template(), containing:
                           file_path, field, original_value, replacement_value,
                           operator_id, operator_name, scheme, difficulty
        out_dir:         destination directory for the mutant copy (created if
                         absent; must NOT already exist as a non-empty dir)

    Returns:
        A mutant record dict:
        {
            "mutant_dir":        str,   # absolute path of the generated mutant
            "operator_id":       str,
            "operator_name":     str,
            "file_path":         str,   # relative path of the changed file
            "field":             str,
            "original_value":    str,
            "replacement_value": str,
            "scheme":            str,
            "difficulty":        int,
            "applied":           bool,  # False if original_value not found
        }

    Raises:
        FileNotFoundError: if project_dir does not exist
        ValueError:        if the target file is not inside project_dir, or if
                           out_dir already exists and is non-empty
    """
    src_root = Path(project_dir).resolve()
    if not src_root.exists():
        raise FileNotFoundError(f"Project directory not found: {project_dir}")

    dst_root = Path(out_dir).resolve()
    if dst_root.exists() and any(dst_root.iterdir()):
        raise ValueError(f"Output directory already exists and is not empty: {out_dir}")

    # Copy the whole project tree
    shutil.copytree(str(src_root), str(dst_root), dirs_exist_ok=True)

    # Resolve target file (relative path from filled_operator)
    rel_file = filled_operator["file_path"]
    target_file = (dst_root / rel_file).resolve()

    # Safety: confirm the target stays inside the mutant tree
    try:
        target_file.relative_to(dst_root)
    except ValueError:
        raise ValueError(
            f"file_path '{rel_file}' resolves outside the mutant directory."
        )

    if not target_file.exists():
        return _mutant_record(filled_operator, str(dst_root), applied=False)

    original_value = filled_operator["original_value"]
    replacement_value = filled_operator["replacement_value"]
    mode = filled_operator.get("mode", "replace")

    text = target_file.read_text(encoding="utf-8", errors="replace")

    if original_value not in text:
        # The expected value wasn't found — record but mark as not applied
        return _mutant_record(filled_operator, str(dst_root), applied=False)

    new_text = _apply_change(text, mode, original_value, replacement_value)
    if new_text is None or new_text == text:
        # Mode could not produce a change (e.g. value only inside a longer
        # token for a line mode) — record but mark as not applied.
        return _mutant_record(filled_operator, str(dst_root), applied=False)

    target_file.write_text(new_text, encoding="utf-8")

    return _mutant_record(filled_operator, str(dst_root), applied=True)


def _apply_change(
    text: str, mode: str, original_value: str, replacement_value: str
) -> str | None:
    """
    Produce the mutated text for a given mode, changing exactly one location.

    Modes:
      replace      — swap the first occurrence of original_value for
                     replacement_value (used for URL/field substitution).
      delete_line  — remove the first line that contains original_value
                     (used for checksum/guard removal).
      insert_after — insert replacement_value as its own line immediately
                     after the first line containing original_value (used for
                     appending an extra command next to a legitimate one).

    Returns the new text, or None if the mode is unknown.
    """
    if mode == "replace":
        return text.replace(original_value, replacement_value, 1)

    # Line-oriented modes preserve the file's original newline style.
    newline = "\r\n" if "\r\n" in text else "\n"
    lines = text.split(newline)

    for idx, line in enumerate(lines):
        if original_value in line:
            if mode == "delete_line":
                del lines[idx]
            elif mode == "insert_after":
                # Match the indentation of the anchor line for a tidy insert.
                indent = line[: len(line) - len(line.lstrip())]
                lines.insert(idx + 1, indent + replacement_value)
            else:
                return None
            return newline.join(lines)

    return None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _mutant_record(filled_operator: dict, mutant_dir: str, *, applied: bool) -> dict:
    return {
        "mutant_dir":        mutant_dir,
        "operator_id":       filled_operator.get("operator_id", ""),
        "operator_name":     filled_operator.get("operator_name", ""),
        "file_path":         filled_operator.get("file_path", ""),
        "field":             filled_operator.get("field", ""),
        "original_value":    filled_operator.get("original_value", ""),
        "replacement_value": filled_operator.get("replacement_value", ""),
        "mode":              filled_operator.get("mode", "replace"),
        "scheme":            filled_operator.get("scheme", ""),
        "difficulty":        filled_operator.get("difficulty", 1),
        "applied":           applied,
    }
