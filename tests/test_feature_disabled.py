"""feature_disabled effect: a silent downgrade (op_002 on openssl) counts as effective."""
import pytest

from src.engine.harness_runner import parse_subprojects
from src.engine.template_filler import resolve_effect
from src.engine.validator import check_effect, classify_run

SUMMARY_OK = """\
git 2.48.0

  Subprojects
    curl     : YES
    openssl  : YES (from curl)
    zlib     : YES

  User defined options
    wrap_mode: forcefallback
"""
SUMMARY_DOWN = SUMMARY_OK.replace("openssl  : YES (from curl)",
                                  "openssl  : NO Missing key 'source_hash' in openssl.wrap")
STATUS = {"fetch_rc": 0, "setup_rc": 0, "compile_rc": 0, "test_rc": 0}
OP002 = {"observable": "feature_disabled", "check": {"wrap_file": "subprojects/openssl.wrap"}}


def run(summary, hashes):
    return {"status": STATUS, "tests": {"t0000-basic": "OK"}, "markers": [], "requests": [],
            "hashes": hashes, "subprojects": parse_subprojects(summary)}


BASE_H = {"build/git": "a", "build/subprojects/openssl-3.0.8/libssl.so": "b",
          "build/subprojects/openssl-3.0.8/libcrypto.so": "c"}


def test_parse_subprojects_reads_summary_block():
    assert parse_subprojects(SUMMARY_OK) == {"curl": "YES", "openssl": "YES (from curl)", "zlib": "YES"}
    assert parse_subprojects("no summary here") == {}


def test_parse_subprojects_last_block_wins():
    nested = "  Subprojects\n    inner : YES\n\n" + SUMMARY_OK
    assert "inner" not in parse_subprojects(nested)


def test_openssl_downgrade_is_effective_with_evidence():
    base = run(SUMMARY_OK, BASE_H)
    mut = run(SUMMARY_DOWN, {"build/git": "a"})
    r = classify_run(mut, base, OP002)
    assert r["level"] == "effective"
    ev = r["effect"]["evidence"]
    assert ev[0].startswith("subproject openssl:")
    assert "missing output build/subprojects/openssl-3.0.8/libssl.so" in ev


def test_only_the_targeted_feature_counts():
    # zlib disappearing is not op_002-on-openssl's effect.
    base = run(SUMMARY_OK, BASE_H)
    mut = run(SUMMARY_OK.replace("zlib     : YES", "zlib     : NO"), BASE_H)
    assert not check_effect(mut, base, OP002)["observed"]


def test_feature_absent_in_baseline_cannot_be_disabled():
    base = run(SUMMARY_DOWN, {})
    mut = run(SUMMARY_DOWN, {})
    assert not check_effect(mut, base, OP002)["observed"]


def test_needs_a_named_feature():
    with pytest.raises(ValueError, match="subproject or check.wrap_file"):
        check_effect(run(SUMMARY_OK, {}), run(SUMMARY_OK, {}), {"observable": "feature_disabled"})


def test_resolve_effect_fills_wrap_file():
    op = {"effect": {"observable": "feature_disabled", "check": {"wrap_file": "{{WRAP_FILE}}"}}}
    eff = resolve_effect(op, {"placeholder_map": {"WRAP_FILE": "subprojects/openssl.wrap"}})
    assert eff["check"] == {"wrap_file": "subprojects/openssl.wrap"}
    with pytest.raises(ValueError, match="Unresolved"):
        resolve_effect(op, {"placeholder_map": {}})
    assert resolve_effect({}, {}) is None
