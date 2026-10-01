"""
tests/conftest.py

Shared pytest fixtures for the mutation-testing engine test suite.
"""

import pytest
from pathlib import Path

# ---------------------------------------------------------------------------
# Fixture directory
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    """Absolute path to the tests/fixtures/ directory."""
    return FIXTURES_DIR


# ---------------------------------------------------------------------------
# Wrap file fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def example_wrap_path(fixtures_dir: Path) -> str:
    """Path to a minimal, valid .wrap fixture file."""
    return str(fixtures_dir / "example.wrap")


# ---------------------------------------------------------------------------
# Meson build file fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def simple_meson_path(fixtures_dir: Path) -> str:
    """Path to a meson.build fixture with no conditionals."""
    return str(fixtures_dir / "simple.meson.build")


@pytest.fixture
def conditional_meson_path(fixtures_dir: Path) -> str:
    """Path to a meson.build fixture with nested if/elif/endif blocks."""
    return str(fixtures_dir / "conditional.meson.build")


# ---------------------------------------------------------------------------
# Minimal parsed-project fixture (no real files needed)
# ---------------------------------------------------------------------------

@pytest.fixture
def minimal_parsed_project() -> dict:
    """
    A minimal parsed project dict with one wrap file, one conditional,
    and one dependency — enough to exercise the placement stubs.
    """
    return {
        "project_dir": "/fake/project",
        "wrap_files": [
            {
                "file_path": "subprojects/zlib.wrap",
                "source_url": "https://zlib.net/zlib-1.3.tar.gz",
                "source_hash": "abc123",
                "directory": "zlib-1.3",
            }
        ],
        "conditionals": [
            {
                "file_path": "meson.build",
                "line_start": 10,
                "line_end": 14,
                "condition": "host_machine.system() == 'linux'",
                "depth": 1,
            }
        ],
        "dependencies": [
            {
                "file_path": "meson.build",
                "line": 5,
                "name": "zlib",
                "required": True,
            }
        ],
    }


# ---------------------------------------------------------------------------
# Minimal operator fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def url_swap_operator() -> dict:
    """
    A minimal dependency-aware operator that swaps a wrap file's source_url.
    Mirrors the structure of data/operators/*.yaml.
    """
    return {
        "id": "op-url-swap",
        "name": "Wrap URL Swap",
        "scheme": "dependency_aware",
        "placeholders": {
            "WRAP_FILE": "path to the .wrap file",
            "ORIGINAL_URL": "the legitimate source_url value",
        },
        "template": {
            "file_path": "{{WRAP_FILE}}",
            "replacement_value": "https://evil.example.com/malicious.tar.gz",
        },
    }
