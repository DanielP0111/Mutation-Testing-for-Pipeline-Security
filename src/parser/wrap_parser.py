"""
src/parser/wrap_parser.py

Reads a single Meson .wrap file and extracts the fields the engine needs.
Called internally by meson_parser.parse_project(); not invoked directly.
"""

import configparser
from pathlib import Path


def parse_wrap_file(file_path: str) -> dict:
    """
    Parse a Meson .wrap file and return its key fields.

    Args:
        file_path: Path to the .wrap file (e.g., "subprojects/zlib.wrap")

    Returns:
        {
            "file_path": "subprojects/zlib.wrap",
            "source_url": "https://zlib.net/zlib-1.3.tar.gz",
            "source_hash": "abcdef1234...",
            "directory": "zlib-1.3"
        }

    Raises:
        FileNotFoundError: if the file does not exist
        ValueError: if the file has no recognized wrap section
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Wrap file not found: {file_path}")

    config = configparser.ConfigParser()
    config.read(path)

    # .wrap files use [wrap-file] or [wrap-git] as the section header
    section = None
    for candidate in ("wrap-file", "wrap-git"):
        if config.has_section(candidate):
            section = candidate
            break

    if section is None:
        raise ValueError(
            f"No recognized wrap section ([wrap-file] or [wrap-git]) in {file_path}"
        )

    def get(key: str, required: bool = True) -> str | None:
        if config.has_option(section, key):
            return config.get(section, key).strip()
        if required:
            raise ValueError(f"Missing required field '{key}' in {file_path}")
        return None

    return {
        "file_path": str(file_path),
        "source_url": get("source_url"),
        "source_hash": get("source_hash", required=False),
        "directory": get("directory"),
    }
