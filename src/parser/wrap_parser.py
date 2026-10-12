"""
src/parser/wrap_parser.py

Reads a single Meson .wrap file and extracts the fields the engine needs.
Called internally by meson_parser.parse_project(); not invoked directly.

Handles both wrap types:
  - [wrap-file] : downloads a source archive (source_url / source_hash)
  - [wrap-git]  : clones a git repository (url / revision)

For a uniform downstream interface, the "download location" of either type is
exposed as source_url (for [wrap-git] it is copied from the git url when an
explicit source_url is absent). The raw git url is also kept under "url".
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
            "file_path":   "subprojects/zlib.wrap",
            "type":        "wrap-file" | "wrap-git",
            "source_url":  str,          # download location (see module docstring)
            "url":         str | None,   # git url, only for [wrap-git]
            "source_hash": str | None,   # sha256, only meaningful for [wrap-file]
            "revision":    str | None,   # git revision, only for [wrap-git]
            "directory":   str | None,   # subproject folder name (may be absent)
        }

    Raises:
        FileNotFoundError: if the file does not exist
        ValueError: if the file has no recognized wrap section, or a required
                    field for the detected section is missing.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Wrap file not found: {file_path}")

    config = configparser.ConfigParser()
    config.read(path)

    # Detect the section type. Exactly one of these should be present.
    section = None
    for candidate in ("wrap-file", "wrap-git"):
        if config.has_section(candidate):
            section = candidate
            break

    if section is None:
        raise ValueError(
            f"No recognized wrap section ([wrap-file] or [wrap-git]) in {file_path}"
        )

    def get(key: str, required: bool = False) -> str | None:
        if config.has_option(section, key):
            return config.get(section, key).strip()
        if required:
            raise ValueError(f"Missing required field '{key}' in {file_path}")
        return None

    if section == "wrap-file":
        # [wrap-file] must point at a downloadable archive and name its folder.
        source_url = get("source_url", required=True)
        directory = get("directory", required=True)
        return {
            "file_path":   str(file_path),
            "type":        section,
            "source_url":  source_url,
            "url":         None,
            "source_hash": get("source_hash"),
            "revision":    None,
            "directory":   directory,
        }

    # [wrap-git] must supply a clone url; revision and directory are optional in
    # the wild, so we default directory from the url stem when absent.
    url = get("url", required=True)
    directory = get("directory")
    if directory is None:
        directory = Path(url).stem  # e.g. ".../mything.git" -> "mything"
    return {
        "file_path":   str(file_path),
        "type":        section,
        "source_url":  get("source_url") or url,
        "url":         url,
        "source_hash": get("source_hash"),
        "revision":    get("revision"),
        "directory":   directory,
    }
