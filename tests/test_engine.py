"""
tests/test_engine.py

Unit tests for the engine layer:
  - operator_loader.load_operator / load_operators
  - template_filler.fill_template  (incl. attacker_values merge)
  - mutant_generator.generate_mutant  (replace / delete_line / insert_after)
"""

import json

import pytest

from src.engine import load_operator, load_operators, fill_template, generate_mutant


# ===========================================================================
# operator_loader
# ===========================================================================

class TestOperatorLoader:
    def _write(self, path, obj):
        path.write_text(json.dumps(obj), encoding="utf-8")

    def _valid(self):
        return {
            "id": "wrap_source_url_swap",
            "scheme": "dependency_aware",
            "mode": "replace",
            "template": {"file_path": "{{WRAP_FILE}}",
                         "replacement_value": "{{SUBSTITUTE_URL}}"},
        }

    def test_loads_json_and_defaults(self, tmp_path):
        p = tmp_path / "op.json"
        self._write(p, self._valid())
        op = load_operator(str(p))
        assert op["id"] == "wrap_source_url_swap"
        assert op["mode"] == "replace"
        assert op["attacker_values"] == {}

    def test_mode_defaults_to_replace(self, tmp_path):
        spec = self._valid()
        del spec["mode"]
        p = tmp_path / "op.json"
        self._write(p, spec)
        assert load_operator(str(p))["mode"] == "replace"

    def test_missing_required_field_raises(self, tmp_path):
        spec = self._valid()
        del spec["template"]
        p = tmp_path / "op.json"
        self._write(p, spec)
        with pytest.raises(ValueError, match="missing required field"):
            load_operator(str(p))

    def test_unknown_scheme_raises(self, tmp_path):
        spec = self._valid()
        spec["scheme"] = "wishful_thinking"
        p = tmp_path / "op.json"
        self._write(p, spec)
        with pytest.raises(ValueError, match="unknown scheme"):
            load_operator(str(p))

    def test_yaml_is_accepted(self, tmp_path):
        p = tmp_path / "op.yaml"
        p.write_text(
            "id: y\nscheme: dependency_aware\n"
            "template:\n  file_path: '{{WRAP_FILE}}'\n  replacement_value: x\n",
            encoding="utf-8",
        )
        assert load_operator(str(p))["id"] == "y"

    def test_load_operators_sorted(self, tmp_path):
        self._write(tmp_path / "b.json", {**self._valid(), "id": "b"})
        self._write(tmp_path / "a.json", {**self._valid(), "id": "a"})
        ops = load_operators(str(tmp_path))
        assert [o["id"] for o in ops] == ["a", "b"]


# ===========================================================================
# template_filler
# ===========================================================================

class TestFillTemplate:
    def test_attacker_value_resolved(self):
        operator = {
            "id": "op", "scheme": "dependency_aware", "mode": "replace",
            "attacker_values": {"SUBSTITUTE_URL": "https://sub.invalid/x.tgz"},
            "template": {"file_path": "{{WRAP_FILE}}",
                         "replacement_value": "{{SUBSTITUTE_URL}}"},
        }
        candidate = {
            "scheme": "dependency_aware",
            "file_path": "subprojects/z.wrap",
            "field": "source_url",
            "current_value": "https://orig.example/z.tgz",
            "placeholder_map": {"WRAP_FILE": "subprojects/z.wrap"},
        }
        filled = fill_template(operator, candidate)
        assert filled["file_path"] == "subprojects/z.wrap"
        assert filled["replacement_value"] == "https://sub.invalid/x.tgz"
        assert filled["original_value"] == "https://orig.example/z.tgz"
        assert filled["mode"] == "replace"

    def test_unresolved_placeholder_raises(self):
        operator = {
            "id": "op", "scheme": "dependency_aware", "mode": "replace",
            "attacker_values": {},
            "template": {"file_path": "{{WRAP_FILE}}",
                         "replacement_value": "{{MISSING}}"},
        }
        candidate = {"placeholder_map": {"WRAP_FILE": "w"}}
        with pytest.raises(ValueError, match="Unresolved placeholders"):
            fill_template(operator, candidate)


# ===========================================================================
# mutant_generator — modes
# ===========================================================================

class TestGenerateMutant:
    def _project(self, tmp_path):
        proj = tmp_path / "proj"
        (proj / "subprojects").mkdir(parents=True)
        (proj / "meson.build").write_text("project('p')\n", encoding="utf-8")
        wrap = proj / "subprojects" / "z.wrap"
        wrap.write_text(
            "[wrap-file]\n"
            "directory = z\n"
            "source_url = https://orig.example/z.tgz\n"
            "source_hash = deadbeef\n",
            encoding="utf-8",
        )
        return proj

    def test_replace_mode(self, tmp_path):
        proj = self._project(tmp_path)
        filled = {
            "operator_id": "swap", "file_path": "subprojects/z.wrap",
            "field": "source_url", "mode": "replace",
            "original_value": "https://orig.example/z.tgz",
            "replacement_value": "https://sub.invalid/z.tgz",
        }
        rec = generate_mutant(str(proj), filled, str(tmp_path / "m1"))
        assert rec["applied"] is True
        txt = (tmp_path / "m1" / "subprojects" / "z.wrap").read_text()
        assert "sub.invalid" in txt and "orig.example" not in txt

    def test_delete_line_mode(self, tmp_path):
        proj = self._project(tmp_path)
        filled = {
            "operator_id": "hash_rm", "file_path": "subprojects/z.wrap",
            "field": "source_hash", "mode": "delete_line",
            "original_value": "deadbeef", "replacement_value": "",
        }
        rec = generate_mutant(str(proj), filled, str(tmp_path / "m2"))
        assert rec["applied"] is True
        txt = (tmp_path / "m2" / "subprojects" / "z.wrap").read_text()
        assert "source_hash" not in txt
        assert "source_url" in txt  # only the hash line removed

    def test_insert_after_mode(self, tmp_path):
        proj = self._project(tmp_path)
        filled = {
            "operator_id": "ins", "file_path": "subprojects/z.wrap",
            "field": "source_url", "mode": "insert_after",
            "original_value": "directory = z",
            "replacement_value": "patch_directory = overlay",
        }
        rec = generate_mutant(str(proj), filled, str(tmp_path / "m3"))
        assert rec["applied"] is True
        lines = (tmp_path / "m3" / "subprojects" / "z.wrap").read_text().splitlines()
        i = lines.index("directory = z")
        assert lines[i + 1] == "patch_directory = overlay"

    def test_value_absent_marks_not_applied(self, tmp_path):
        proj = self._project(tmp_path)
        filled = {
            "operator_id": "swap", "file_path": "subprojects/z.wrap",
            "field": "source_url", "mode": "replace",
            "original_value": "NOT_PRESENT", "replacement_value": "x",
        }
        rec = generate_mutant(str(proj), filled, str(tmp_path / "m4"))
        assert rec["applied"] is False

    def test_original_project_untouched(self, tmp_path):
        proj = self._project(tmp_path)
        before = (proj / "subprojects" / "z.wrap").read_text()
        filled = {
            "operator_id": "swap", "file_path": "subprojects/z.wrap",
            "field": "source_url", "mode": "replace",
            "original_value": "https://orig.example/z.tgz",
            "replacement_value": "https://sub.invalid/z.tgz",
        }
        generate_mutant(str(proj), filled, str(tmp_path / "m5"))
        assert (proj / "subprojects" / "z.wrap").read_text() == before
