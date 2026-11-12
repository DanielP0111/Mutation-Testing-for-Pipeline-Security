"""
tests/test_placement.py

Unit tests for the placement layer (Phase 3):
  - config_aware.analyze_branch_reachability / load_build_options_from_introspect
  - config_aware.find_config_candidates (intentionally inert — see
    docs/config_aware_status.md)
  - difficulty.assign_difficulty
"""

import pytest

from src.parser.meson_parser import parse_project
from src.placement.config_aware import (
    analyze_branch_reachability,
    find_config_candidates,
    load_build_options_from_introspect,
)
from src.placement.difficulty import assign_difficulty


# ===========================================================================
# analyze_branch_reachability
# ===========================================================================

class TestAnalyzeBranchReachability:
    def test_finds_every_conditional_with_correct_depth(self, minimal_parsed_project: dict):
        report = analyze_branch_reachability(minimal_parsed_project)
        assert len(report) == 1
        assert report[0]["depth"] == 1
        assert report[0]["condition"] == "host_machine.system() == 'linux'"

    def test_extracts_platform_guard(self, minimal_parsed_project: dict):
        report = analyze_branch_reachability(minimal_parsed_project)
        assert report[0]["platform_guard"] == "linux"
        assert report[0]["gating_options"] == []

    def test_unresolved_without_build_options(self, minimal_parsed_project: dict):
        report = analyze_branch_reachability(minimal_parsed_project)
        # No host_system hint supplied -> can't resolve the platform guard.
        assert report[0]["reachable"] is None

    def test_resolves_platform_guard_when_matching_host_given(self, minimal_parsed_project: dict):
        report = analyze_branch_reachability(
            minimal_parsed_project, build_options={"host_system": "linux"}
        )
        assert report[0]["reachable"] is True

    def test_resolves_platform_guard_when_non_matching_host_given(self, minimal_parsed_project: dict):
        report = analyze_branch_reachability(
            minimal_parsed_project, build_options={"host_system": "windows"}
        )
        assert report[0]["reachable"] is False

    def test_real_fixture_nested_conditionals(self, conditional_meson_path: str, tmp_path):
        # conditional.meson.build lives directly under tests/fixtures/, not
        # under a subprojects/ layout; parse_project needs a project root,
        # so point it at the fixtures directory itself.
        import shutil
        from pathlib import Path

        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        shutil.copy(conditional_meson_path, project_dir / "meson.build")

        parsed = parse_project(str(project_dir))
        report = analyze_branch_reachability(parsed)

        # if-linux (1), if-feature-x (2), elif-feature-y, if-windows (1).
        # Note: meson_parser.py computes an elif's depth from the stack
        # depth *before* popping the branch it's replacing, so
        # elif-feature-y comes out at depth 3, not 2, here — a pre-existing
        # quirk in the parser (Daniel's module), not something fixed by
        # this placement work. Asserting the actual behavior rather than
        # the "should be" value so this test catches a real regression.
        depths = sorted(r["depth"] for r in report)
        assert depths == [1, 1, 2, 3]

        gating = {opt for r in report for opt in r["gating_options"]}
        assert gating == {"feature-x", "feature-y"}

        windows_block = [r for r in report if r["platform_guard"] == "windows"]
        assert len(windows_block) == 1
        assert windows_block[0]["depth"] == 1

    def test_option_gated_branch_unresolved_without_values(self, tmp_path):
        import shutil

        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        (project_dir / "meson.build").write_text(
            "if get_option('feature-x')\nendif\n"
        )
        parsed = parse_project(str(project_dir))
        report = analyze_branch_reachability(parsed)
        assert report[0]["reachable"] is None
        assert report[0]["gating_options"] == ["feature-x"]

    def test_option_gated_branch_resolved_true(self, tmp_path):
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        (project_dir / "meson.build").write_text(
            "if get_option('feature-x')\nendif\n"
        )
        parsed = parse_project(str(project_dir))
        report = analyze_branch_reachability(parsed, build_options={"feature-x": True})
        assert report[0]["reachable"] is True

    def test_option_gated_branch_resolved_false_for_disabled_string(self, tmp_path):
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        (project_dir / "meson.build").write_text(
            "if get_option('feature-x')\nendif\n"
        )
        parsed = parse_project(str(project_dir))
        report = analyze_branch_reachability(parsed, build_options={"feature-x": "disabled"})
        assert report[0]["reachable"] is False

    def test_unrecognized_gate_defaults_to_reachable(self, tmp_path):
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        (project_dir / "meson.build").write_text(
            "if some_local_var\nendif\n"
        )
        parsed = parse_project(str(project_dir))
        report = analyze_branch_reachability(parsed)
        assert report[0]["reachable"] is True
        assert "no recognized option/platform gate" in report[0]["reachability_basis"]

    def test_empty_project_returns_empty_report(self, tmp_path):
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        (project_dir / "meson.build").write_text("project('x', 'c')\n")
        parsed = parse_project(str(project_dir))
        assert analyze_branch_reachability(parsed) == []


# ===========================================================================
# load_build_options_from_introspect
# ===========================================================================

class TestLoadBuildOptionsFromIntrospect:
    def test_flattens_real_introspect_shape(self):
        introspect_json = [
            {"name": "feature-x", "value": True, "section": "user"},
            {"name": "buildtype", "value": "debug", "section": "core"},
        ]
        flat = load_build_options_from_introspect(introspect_json)
        assert flat == {"feature-x": True, "buildtype": "debug"}

    def test_non_list_input_returns_empty_dict(self):
        assert load_build_options_from_introspect({"not": "a list"}) == {}
        assert load_build_options_from_introspect(None) == {}

    def test_entries_without_name_are_skipped(self):
        introspect_json = [{"value": "orphan"}, {"name": "ok", "value": 1}]
        assert load_build_options_from_introspect(introspect_json) == {"ok": 1}


# ===========================================================================
# find_config_candidates (intentionally inert)
# ===========================================================================

class TestFindConfigCandidates:
    def test_returns_empty_for_config_aware_scheme(self, minimal_parsed_project: dict):
        operator = {"scheme": "config_aware"}
        assert find_config_candidates(minimal_parsed_project, operator) == []

    def test_returns_empty_for_all_scheme(self, minimal_parsed_project: dict):
        operator = {"scheme": "all"}
        assert find_config_candidates(minimal_parsed_project, operator) == []

    def test_returns_empty_for_unrelated_scheme(self, minimal_parsed_project: dict):
        operator = {"scheme": "dependency_aware"}
        assert find_config_candidates(minimal_parsed_project, operator) == []


# ===========================================================================
# assign_difficulty
# ===========================================================================

class TestAssignDifficulty:
    def test_dependency_aware_obvious_field_is_level_1(self, minimal_parsed_project: dict):
        candidate = {"scheme": "dependency_aware", "field": "source_url"}
        assign_difficulty(candidate, minimal_parsed_project)
        assert candidate["difficulty"] == 1

        candidate2 = {"scheme": "dependency_aware", "field": "source_hash"}
        assign_difficulty(candidate2, minimal_parsed_project)
        assert candidate2["difficulty"] == 1

    def test_dependency_aware_other_field_is_level_2(self, minimal_parsed_project: dict):
        candidate = {"scheme": "dependency_aware", "field": "directory"}
        assign_difficulty(candidate, minimal_parsed_project)
        assert candidate["difficulty"] == 2

    def test_config_aware_depth_1_is_level_2(self, minimal_parsed_project: dict):
        candidate = {"scheme": "config_aware", "depth": 1}
        assign_difficulty(candidate, minimal_parsed_project)
        assert candidate["difficulty"] == 2

    def test_config_aware_missing_depth_defaults_to_level_2(self, minimal_parsed_project: dict):
        candidate = {"scheme": "config_aware"}
        assign_difficulty(candidate, minimal_parsed_project)
        assert candidate["difficulty"] == 2

    def test_config_aware_depth_2_is_level_3(self, minimal_parsed_project: dict):
        candidate = {"scheme": "config_aware", "depth": 2}
        assign_difficulty(candidate, minimal_parsed_project)
        assert candidate["difficulty"] == 3

    def test_config_aware_depth_2_platform_guarded_is_level_4(self, minimal_parsed_project: dict):
        candidate = {"scheme": "config_aware", "depth": 2, "platform_guard": "windows"}
        assign_difficulty(candidate, minimal_parsed_project)
        assert candidate["difficulty"] == 4

    def test_config_aware_depth_1_platform_guarded_stays_level_2(self, minimal_parsed_project: dict):
        # Platform guard alone, without nesting, doesn't bump to level 4.
        candidate = {"scheme": "config_aware", "depth": 1, "platform_guard": "windows"}
        assign_difficulty(candidate, minimal_parsed_project)
        assert candidate["difficulty"] == 2

    def test_adversarial_defaults_to_level_3(self, minimal_parsed_project: dict):
        candidate = {"scheme": "adversarial", "depth": 1}
        assign_difficulty(candidate, minimal_parsed_project)
        assert candidate["difficulty"] == 3

    def test_adversarial_nested_and_platform_guarded_is_level_4(self, minimal_parsed_project: dict):
        candidate = {"scheme": "adversarial", "depth": 2, "platform_guard": "linux"}
        assign_difficulty(candidate, minimal_parsed_project)
        assert candidate["difficulty"] == 4

    def test_unknown_scheme_defaults_to_level_1(self, minimal_parsed_project: dict):
        candidate = {"scheme": "mystery"}
        assign_difficulty(candidate, minimal_parsed_project)
        assert candidate["difficulty"] == 1

    def test_mutates_and_returns_same_dict(self, minimal_parsed_project: dict):
        candidate = {"scheme": "dependency_aware", "field": "source_url"}
        result = assign_difficulty(candidate, minimal_parsed_project)
        assert result is candidate
