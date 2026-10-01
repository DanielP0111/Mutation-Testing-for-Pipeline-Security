"""
tests/test_parser.py

Unit tests for the parser layer:
  - wrap_parser.parse_wrap_file
  - meson_parser.parse_project  (via a temporary directory)
"""

import pytest
import tempfile
import shutil
from pathlib import Path

from src.parser.wrap_parser import parse_wrap_file
from src.parser.meson_parser import parse_project


# ===========================================================================
# parse_wrap_file
# ===========================================================================

class TestParseWrapFile:
    def test_valid_wrap_returns_expected_fields(self, example_wrap_path: str):
        result = parse_wrap_file(example_wrap_path)
        assert result["file_path"] == example_wrap_path
        assert result["source_url"].startswith("https://")
        assert result["directory"] == "zlib-1.3"
        assert result["source_hash"] is not None

    def test_missing_file_raises_file_not_found(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            parse_wrap_file(str(tmp_path / "nonexistent.wrap"))

    def test_no_valid_section_raises_value_error(self, tmp_path: Path):
        bad_wrap = tmp_path / "bad.wrap"
        bad_wrap.write_text("[unknown-section]\nkey = value\n")
        with pytest.raises(ValueError, match="No recognized wrap section"):
            parse_wrap_file(str(bad_wrap))

    def test_wrap_git_section_accepted(self, tmp_path: Path):
        git_wrap = tmp_path / "mything.wrap"
        git_wrap.write_text(
            "[wrap-git]\n"
            "directory = mything\n"
            "url = https://github.com/example/mything.git\n"
            "revision = main\n"
            "source_url = https://github.com/example/mything.git\n"
        )
        result = parse_wrap_file(str(git_wrap))
        assert result["directory"] == "mything"

    def test_missing_required_field_raises_value_error(self, tmp_path: Path):
        incomplete = tmp_path / "incomplete.wrap"
        # Missing 'directory'
        incomplete.write_text(
            "[wrap-file]\n"
            "source_url = https://example.com/thing.tar.gz\n"
        )
        with pytest.raises(ValueError, match="Missing required field"):
            parse_wrap_file(str(incomplete))


# ===========================================================================
# parse_project (integration-style, uses a temp dir)
# ===========================================================================

class TestParseProject:

    @pytest.fixture
    def project_with_wrap(self, tmp_path: Path, example_wrap_path: str) -> Path:
        """
        Build a minimal project tree:
          tmp/
            meson.build       (has one dependency() call)
            subprojects/
              zlib.wrap       (copy of the fixture)
        """
        subprojects = tmp_path / "subprojects"
        subprojects.mkdir()
        shutil.copy(example_wrap_path, subprojects / "zlib.wrap")
        (tmp_path / "meson.build").write_text(
            "project('demo', 'c')\n"
            "zlib_dep = dependency('zlib', required : true)\n"
        )
        return tmp_path

    @pytest.fixture
    def project_with_conditionals(
        self, tmp_path: Path, conditional_meson_path: str
    ) -> Path:
        """
        Build a project tree that contains the conditional fixture.
        """
        shutil.copy(conditional_meson_path, tmp_path / "meson.build")
        return tmp_path

    # -----------------------------------------------------------------------
    # Basic shape tests
    # -----------------------------------------------------------------------

    def test_returns_expected_keys(self, project_with_wrap: Path):
        result = parse_project(str(project_with_wrap))
        assert set(result.keys()) == {
            "project_dir", "wrap_files", "conditionals", "dependencies"
        }

    def test_project_dir_matches_input(self, project_with_wrap: Path):
        result = parse_project(str(project_with_wrap))
        assert result["project_dir"] == str(project_with_wrap)

    def test_nonexistent_dir_raises(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            parse_project(str(tmp_path / "does_not_exist"))

    # -----------------------------------------------------------------------
    # Wrap files
    # -----------------------------------------------------------------------

    def test_wrap_files_found(self, project_with_wrap: Path):
        result = parse_project(str(project_with_wrap))
        assert len(result["wrap_files"]) == 1
        wrap = result["wrap_files"][0]
        assert wrap["file_path"] == "subprojects/zlib.wrap"
        assert "source_url" in wrap

    def test_no_subprojects_dir_returns_empty_wraps(self, tmp_path: Path):
        (tmp_path / "meson.build").write_text("project('empty', 'c')\n")
        result = parse_project(str(tmp_path))
        assert result["wrap_files"] == []

    # -----------------------------------------------------------------------
    # Dependencies
    # -----------------------------------------------------------------------

    def test_dependencies_found(self, project_with_wrap: Path):
        result = parse_project(str(project_with_wrap))
        assert len(result["dependencies"]) >= 1
        dep = result["dependencies"][0]
        assert dep["name"] == "zlib"
        assert dep["required"] is True
        assert dep["file_path"] == "meson.build"

    def test_optional_dependency_required_false(self, tmp_path: Path):
        (tmp_path / "meson.build").write_text(
            "project('opt', 'c')\n"
            "opt = dependency('libfoo', required : false)\n"
        )
        result = parse_project(str(tmp_path))
        deps = [d for d in result["dependencies"] if d["name"] == "libfoo"]
        assert len(deps) == 1
        assert deps[0]["required"] is False

    # -----------------------------------------------------------------------
    # Conditionals
    # -----------------------------------------------------------------------

    def test_conditionals_found(self, project_with_conditionals: Path):
        result = parse_project(str(project_with_conditionals))
        # The fixture has two top-level if blocks and nested elif/endif
        assert len(result["conditionals"]) >= 2

    def test_conditional_has_expected_keys(self, project_with_conditionals: Path):
        result = parse_project(str(project_with_conditionals))
        cond = result["conditionals"][0]
        assert "file_path" in cond
        assert "line_start" in cond
        assert "condition" in cond
        assert "depth" in cond

    def test_nested_conditional_has_depth_gte_2(
        self, project_with_conditionals: Path
    ):
        result = parse_project(str(project_with_conditionals))
        deep = [c for c in result["conditionals"] if c["depth"] >= 2]
        assert len(deep) >= 1
