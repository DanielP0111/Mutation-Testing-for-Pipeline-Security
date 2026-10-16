"""
tests/test_validator.py

Unit tests for the attack-effect oracle (validator.classify_run / classify_runs),
harness_runner.load_run parsing, and the schema-v3 effect block in the loader.
No Docker needed: runs are plain dicts shaped like load_run() output.
"""

import copy
import json

import pytest

from src.engine import load_operator
from src.engine.harness_runner import load_run
from src.engine.validator import (
    CANARY_SECRET, check_effect, classify_run, classify_runs, newly_failing_tests,
)

BASE = {
    "status": {"fetch_rc": 0, "setup_rc": 0, "compile_rc": 0, "test_rc": 0},
    "hashes": {"build/git": "aaa", "build/libgit.a": "bbb"},
    "tests": {"t0000-basic": "OK", "t0001-init": "OK"},
    "markers": [],
    "requests": [],
}


def mutant(**changes):
    run = copy.deepcopy(BASE)
    for key, val in changes.items():
        if key == "status":
            run["status"].update(val)
        else:
            run[key] = val
    return run


# ===========================================================================
# Validity levels
# ===========================================================================

class TestLevels:
    def test_setup_failure(self):
        r = classify_run(mutant(status={"setup_rc": 1, "compile_rc": -1}), BASE)
        assert r["level"] == "setup_failed"

    def test_empty_run_is_setup_failed(self):
        # A run that died before writing status.json loads as {}.
        r = classify_run({"status": {}, "hashes": {}, "tests": {},
                          "markers": [], "requests": []}, BASE)
        assert r["level"] == "setup_failed"

    def test_compile_failure_is_setup_valid(self):
        r = classify_run(mutant(status={"compile_rc": 1}), BASE)
        assert r["level"] == "setup_valid"

    def test_identical_run_without_effect_is_build_valid(self):
        r = classify_run(mutant(), BASE)
        assert r["level"] == "build_valid"
        assert r["effect"] is None

    def test_identical_run_with_effect_not_observed(self):
        r = classify_run(mutant(), BASE, {"observable": "file_write"})
        assert r["level"] == "build_valid"
        assert r["effect"]["observed"] is False

    def test_new_test_failure_blocks_build_valid(self):
        tests = {"t0000-basic": "FAIL", "t0001-init": "OK"}
        r = classify_run(mutant(tests=tests, markers=["/src/PWNED_x"]), BASE,
                         {"observable": "file_write"})
        assert r["level"] == "setup_valid"
        assert r["newly_failing"] == ["t0000-basic"]

    def test_expected_test_failure_is_allowed(self):
        tests = {"t0000-basic": "FAIL", "t0001-init": "OK"}
        effect = {"observable": "file_write",
                  "check": {"tests_may_fail": ["t0000-basic"]}}
        r = classify_run(mutant(tests=tests, markers=["/src/PWNED_x"]), BASE, effect)
        assert r["level"] == "effective"

    def test_missing_test_counts_as_newly_failing(self):
        assert newly_failing_tests(mutant(tests={"t0000-basic": "OK"}), BASE) == ["t0001-init"]

    def test_bad_baseline_raises(self):
        with pytest.raises(ValueError, match="baseline"):
            classify_run(mutant(), mutant(status={"compile_rc": 1}))


# ===========================================================================
# Effect checks, one per evidence file
# ===========================================================================

class TestEffects:
    def test_file_write_marker(self):
        r = classify_run(mutant(markers=["/src/PWNED_op1"]), BASE,
                         {"observable": "file_write"})
        assert r["level"] == "effective"
        assert r["effect"]["evidence"] == ["/src/PWNED_op1"]

    def test_file_write_marker_filter(self):
        eff = {"observable": "file_write", "check": {"marker": "PWNED_op2"}}
        assert not check_effect(mutant(markers=["/src/PWNED_op1"]), BASE, eff)["observed"]

    def test_marker_already_in_baseline_does_not_count(self):
        base = mutant(markers=["/tmp/PWNED_stale"])
        r = classify_run(mutant(markers=["/tmp/PWNED_stale"]), base,
                         {"observable": "file_write"})
        assert r["level"] == "build_valid"

    def test_network_fetch(self):
        reqs = ["GET /evil.tar.gz ''"]
        eff = {"observable": "network_fetch", "check": {"request_path": "/evil"}}
        assert classify_run(mutant(requests=reqs), BASE, eff)["level"] == "effective"

    def test_network_fetch_wrong_path(self):
        eff = {"observable": "network_fetch", "check": {"request_path": "/other"}}
        assert classify_run(mutant(requests=["GET /evil ''"]), BASE, eff)["level"] == "build_valid"

    def test_env_exfil_needs_canary(self):
        eff = {"observable": "env_exfil"}
        no_secret = mutant(requests=["POST /x 'hello'"])
        with_secret = mutant(requests=[f"POST /x '{CANARY_SECRET}'"])
        assert classify_run(no_secret, BASE, eff)["level"] == "build_valid"
        assert classify_run(with_secret, BASE, eff)["level"] == "effective"

    def test_artifact_diff(self):
        hashes = {"build/git": "zzz", "build/libgit.a": "bbb"}
        r = classify_run(mutant(hashes=hashes), BASE, {"observable": "artifact_diff"})
        assert r["level"] == "effective"
        assert r["effect"]["evidence"] == ["build/git"]

    def test_artifact_diff_specific_artifact(self):
        hashes = {"build/git": "aaa", "build/libgit.a": "zzz"}
        eff = {"observable": "artifact_diff", "check": {"artifact": "build/git"}}
        assert classify_run(mutant(hashes=hashes), BASE, eff)["level"] == "build_valid"

    def test_artifact_diff_new_output(self):
        hashes = dict(BASE["hashes"], **{"build/evil.so": "eee"})
        r = classify_run(mutant(hashes=hashes), BASE, {"observable": "test_input_swap"})
        assert r["effect"]["evidence"] == ["build/evil.so"]

    def test_unknown_observable_raises(self):
        with pytest.raises(ValueError, match="unknown effect"):
            check_effect(mutant(), BASE, {"observable": "telepathy"})


# ===========================================================================
# Repeated runs
# ===========================================================================

class TestRepeatedRuns:
    def test_consistent_runs(self):
        run = mutant(markers=["/src/PWNED_x"])
        r = classify_runs([run, run, run], BASE, {"observable": "file_write"})
        assert r["level"] == "effective" and r["flaky"] is False

    def test_lowest_level_wins_and_flags_flaky(self):
        good = mutant(markers=["/src/PWNED_x"])
        bad = mutant(status={"compile_rc": 1})
        r = classify_runs([good, bad, good], BASE, {"observable": "file_write"})
        assert r["level"] == "setup_valid" and r["flaky"] is True

    def test_no_runs_raises(self):
        with pytest.raises(ValueError):
            classify_runs([], BASE)


# ===========================================================================
# load_run parsing (harness output folder -> dict)
# ===========================================================================

class TestLoadRun:
    def test_parses_all_files(self, tmp_path):
        (tmp_path / "status.json").write_text(json.dumps(BASE["status"]))
        (tmp_path / "hashes.txt").write_text("aaa  build/git\nbbb  build/libgit.a\n")
        (tmp_path / "testlog.json").write_text(
            json.dumps({"name": "t0000-basic", "result": "OK"}) + "\n" +
            json.dumps({"name": "t0001-init", "result": "FAIL"}) + "\nnot json\n")
        (tmp_path / "markers.txt").write_text("/src/PWNED_a\n\n")
        (tmp_path / "mock_server.log").write_text("GET /x ''\n")
        run = load_run(str(tmp_path))
        assert run["hashes"] == {"build/git": "aaa", "build/libgit.a": "bbb"}
        assert run["tests"] == {"t0000-basic": "OK", "t0001-init": "FAIL"}
        assert run["markers"] == ["/src/PWNED_a"]
        assert run["requests"] == ["GET /x ''"]

    def test_empty_dir_loads_as_empty(self, tmp_path):
        run = load_run(str(tmp_path))
        assert run == {"status": {}, "hashes": {}, "tests": {},
                       "markers": [], "requests": []}


# ===========================================================================
# Schema v3 effect block in the loader
# ===========================================================================

class TestEffectBlockLoader:
    def _op(self, tmp_path, effect):
        spec = {"id": "x", "scheme": "adversarial",
                "template": {"file_path": "meson.build", "replacement_value": "y"},
                "effect": effect}
        p = tmp_path / "op.json"
        p.write_text(json.dumps(spec))
        return str(p)

    def test_valid_effect_gets_defaults(self, tmp_path):
        op = load_operator(self._op(tmp_path, {"observable": "file_write"}))
        assert op["effect"] == {"observable": "file_write", "check": {}, "requires": []}

    def test_operator_without_effect_still_loads(self, tmp_path):
        p = tmp_path / "op.json"
        p.write_text(json.dumps({"id": "x", "scheme": "adversarial",
                                 "template": {"file_path": "a", "replacement_value": "b"}}))
        assert "effect" not in load_operator(str(p))

    def test_unknown_observable(self, tmp_path):
        with pytest.raises(ValueError, match="unknown effect observable"):
            load_operator(self._op(tmp_path, {"observable": "magic"}))

    def test_unknown_check_key(self, tmp_path):
        with pytest.raises(ValueError, match="unknown key"):
            load_operator(self._op(tmp_path, {"observable": "file_write",
                                              "check": {"markr": "x"}}))

    def test_requires_must_be_list(self, tmp_path):
        with pytest.raises(ValueError, match="requires"):
            load_operator(self._op(tmp_path, {"observable": "file_write",
                                              "requires": "wrap_hash_removal"}))
