"""
src/parser/meson_parser.py

Reads all Meson build files in a project directory and extracts the
structured data the placement step needs: wrap files, conditional blocks,
and dependency declarations.
"""

import re
from pathlib import Path
from .wrap_parser import parse_wrap_file


def parse_project(project_dir: str) -> dict:
    """
    Parse a Meson project directory and return structured data.

    Args:
        project_dir: Path to the root of the target project
                     (e.g., "data/targets/numpy")

    Returns:
        {
            "project_dir": str,
            "wrap_files": [
                {"file_path": str, "source_url": str,
                 "source_hash": str|None, "directory": str}
            ],
            "conditionals": [
                {"file_path": str, "line_start": int, "line_end": int|None,
                 "condition": str, "depth": int}
            ],
            "dependencies": [
                {"file_path": str, "line": int,
                 "name": str, "required": bool}
            ]
        }

    Raises:
        FileNotFoundError: if project_dir does not exist
    """
    root = Path(project_dir)
    if not root.exists():
        raise FileNotFoundError(f"Project directory not found: {project_dir}")

    return {
        "project_dir": str(project_dir),
        "wrap_files": _find_wrap_files(root),
        "conditionals": _find_conditionals(root),
        "dependencies": _find_dependencies(root),
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _find_wrap_files(root: Path) -> list[dict]:
    """Find and parse all .wrap files in the subprojects/ directory."""
    wrap_files = []
    subprojects = root / "subprojects"
    if not subprojects.exists():
        return wrap_files

    for wrap_path in sorted(subprojects.glob("*.wrap")):
        try:
            parsed = parse_wrap_file(str(wrap_path))
            # Store path relative to project root for portability
            parsed["file_path"] = str(wrap_path.relative_to(root))
            wrap_files.append(parsed)
        except (ValueError, FileNotFoundError):
            pass  # Skip malformed or unreadable .wrap files

    return wrap_files


def _find_conditionals(root: Path) -> list[dict]:
    """
    Find all if/elif blocks in every meson.build file under root.

    Returns one entry per if/elif block with file path, line numbers,
    condition string, and nesting depth (1 = top-level, 2 = nested, …).
    """
    conditionals = []
    if_re = re.compile(r"^(\s*)(if|elif)\s+(.+)$")

    for build_file in sorted(root.rglob("meson.build")):
        rel_path = str(build_file.relative_to(root))
        depth_stack: list[dict] = []

        try:
            lines = build_file.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue

        for lineno, line in enumerate(lines, start=1):
            m = if_re.match(line.rstrip())
            if m:
                keyword, condition = m.group(2), m.group(3)
                depth = len(depth_stack) + 1

                entry = {
                    "file_path": rel_path,
                    "line_start": lineno,
                    "line_end": None,
                    "condition": condition.strip(),
                    "depth": depth,
                }

                if keyword == "if":
                    depth_stack.append(entry)
                else:
                    # elif: close the current open block, open a new one
                    if depth_stack:
                        prev = depth_stack.pop()
                        prev["line_end"] = lineno - 1
                        conditionals.append(prev)
                    depth_stack.append(entry)

            elif re.match(r"^\s*endif\b", line.rstrip()):
                if depth_stack:
                    entry = depth_stack.pop()
                    entry["line_end"] = lineno
                    conditionals.append(entry)

        # Close any blocks that were never explicitly closed
        for entry in depth_stack:
            conditionals.append(entry)

    return conditionals


def _find_dependencies(root: Path) -> list[dict]:
    """
    Find all dependency() calls in every meson.build file under root.

    Returns one entry per call with file path, line number, dependency
    name, and whether it is required.
    """
    dependencies = []
    # Matches:  dependency('name', ...)  or  dependency("name", ...)
    dep_re = re.compile(
        r"""dependency\(\s*['"]([^'"]+)['"](.*?)\)""",
        re.DOTALL,
    )
    required_re = re.compile(r"required\s*:\s*(true|false|get_option\([^)]+\))")

    for build_file in sorted(root.rglob("meson.build")):
        rel_path = str(build_file.relative_to(root))
        try:
            text = build_file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        for m in dep_re.finditer(text):
            name = m.group(1)
            rest = m.group(2)
            line = text[: m.start()].count("\n") + 1

            # Meson default is required=true
            required = True
            rm = required_re.search(rest)
            if rm:
                val = rm.group(1)
                required = val == "true" or val.startswith("get_option")

            dependencies.append(
                {
                    "file_path": rel_path,
                    "line": line,
                    "name": name,
                    "required": required,
                }
            )

    return dependencies
