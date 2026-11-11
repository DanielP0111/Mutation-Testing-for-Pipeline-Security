"""Per-phase sandbox: policy learning, outcome scoring, docker commands (no Docker needed)."""
import json
import subprocess
from pathlib import Path
from unittest import mock

import pytest

from src.engine import sandbox as sbx
from src.engine.harness_runner import HarnessUnavailable

OP005 = {"observable": "file_write", "check": {"marker": "PWNED_netbeans"}}
EXFIL = {"observable": "env_exfil"}
TAMPER = {"observable": "artifact_diff", "check": {"artifact": "build/git"}}


def make_run(tmp, name, *, markers=(), phase_markers=None, phase_requests=None,
             hashes=None, changes=None, net="", status=None):
    d = Path(tmp) / name
    d.mkdir()
    (d / "status.json").write_text(json.dumps(status or {
        "fetch_rc": 0, "setup_rc": 0, "compile_rc": 0, "test_rc": 0}))
    (d / "markers.txt").write_text("\n".join(markers))
    (d / "hashes.txt").write_text("".join(f"{h} {p}\n" for p, h in (hashes or {"build/git": "aaa"}).items()))
    (d / "testlog.json").write_text('{"name": "t0000-basic", "result": "OK"}\n')
    (d / "sandbox_mode.txt").write_text(f"enforce\nnetwork_phases={net}\n")
    for p in sbx.PHASES:
        (d / f"sandbox_{p}_markers.txt").write_text("\n".join((phase_markers or {}).get(p, [])))
        (d / f"sandbox_{p}_requests.log").write_text("\n".join((phase_requests or {}).get(p, [])))
        (d / f"sandbox_{p}_changes.json").write_text(json.dumps((changes or {}).get(p, {})))
    return sbx.load_sandbox_run(str(d))


def test_op005_style_tmp_marker_is_confined(tmp_path):
    clean = make_run(tmp_path, "clean")
    mut = make_run(tmp_path, "mut", phase_markers={"compile": ["/tmp/PWNED_netbeans_1"]})
    o = sbx.sandbox_outcome(mut, clean, OP005)
    assert o["outcome"] == "confined" and o["blocked"]
    assert o["evidence"] == ["/tmp/PWNED_netbeans_1"]


def test_marker_left_in_src_is_not_blocked(tmp_path):
    clean = make_run(tmp_path, "clean")
    mut = make_run(tmp_path, "mut", markers=["/src/build/PWNED_netbeans_1"],
                   phase_markers={"compile": ["/src/build/PWNED_netbeans_1"]})
    o = sbx.sandbox_outcome(mut, clean, OP005)
    assert o["outcome"] == "not_blocked" and not o["blocked"]


def test_no_evidence_anywhere_is_prevented(tmp_path):
    clean = make_run(tmp_path, "clean")
    mut = make_run(tmp_path, "mut", status={"fetch_rc": 0, "setup_rc": 0, "compile_rc": 1, "test_rc": -1})
    o = sbx.sandbox_outcome(mut, clean, OP005)
    assert o["outcome"] == "prevented" and "compile_rc=1" in o["reason"]


def test_exfil_without_network_is_confined_with_network_escapes(tmp_path):
    req = {"setup": ["GET /x 'CANARY_SECRET_7f3a91'"]}
    clean = make_run(tmp_path, "clean")
    offline = make_run(tmp_path, "off", phase_requests=req)
    assert sbx.sandbox_outcome(offline, clean, EXFIL)["outcome"] == "confined"
    online = make_run(tmp_path, "on", phase_requests=req, net="setup")
    assert sbx.sandbox_outcome(online, clean, EXFIL)["outcome"] == "not_blocked"


def test_artifact_tamper_through_build_dir_is_not_blocked(tmp_path):
    # build/ is shared between phases by design: the documented gap.
    clean = make_run(tmp_path, "clean")
    mut = make_run(tmp_path, "mut", hashes={"build/git": "bbb"})
    assert sbx.sandbox_outcome(mut, clean, TAMPER)["outcome"] == "not_blocked"


def test_sandbox_errors_are_not_scored(tmp_path):
    clean = make_run(tmp_path, "clean")
    mut = make_run(tmp_path, "mut")
    (tmp_path / "mut" / "sandbox_errors.txt").write_text("compile: rc=1\n")
    mut = sbx.load_sandbox_run(str(tmp_path / "mut"))
    assert sbx.sandbox_outcome(mut, clean, OP005)["outcome"] == "error"


def test_learn_policy_from_changes(tmp_path):
    run = make_run(tmp_path, "learn", changes={
        "fetch": {"modified": [], "created": ["subprojects/zlib-1.3.1", "subprojects/curl-8.10.1"]},
        "setup": {"modified": ["version.txt"], "created": []}})
    pol = sbx.learn_policy(run)["phases"]
    assert pol["fetch"] == {"write_files": [], "create_in": ["subprojects"]}
    assert pol["setup"] == {"write_files": ["version.txt"], "create_in": []}
    assert pol["compile"] == {"write_files": [], "create_in": []}


def test_clean_check_flags_false_positives(tmp_path):
    learn = make_run(tmp_path, "learn")
    ok = make_run(tmp_path, "ok")
    assert sbx.clean_check(ok, learn) == []
    bad = make_run(tmp_path, "bad", status={"fetch_rc": 0, "setup_rc": 1, "compile_rc": -1, "test_rc": -1})
    assert any("setup_rc=1" in p for p in sbx.clean_check(bad, learn))


def test_phase_cmd_isolation_flags(tmp_path):
    kw = dict(volume="v", src=tmp_path, out=tmp_path, policy_path=tmp_path / "p.json",
              tests=("t0000-basic",), wrap_mode="forcefallback", image="img", name="n")
    c = sbx.phase_cmd("compile", network=False, **kw)
    assert ["--network", "none"] == c[c.index("--network"):c.index("--network") + 2]
    assert "--cap-drop" in c and "no-new-privileges" in c
    assert any(a.startswith("/tmp:") for a in c)
    assert f"{tmp_path / 'p.json'}:/work/policy.json:ro" in c
    assert not any(a.endswith(":/work/target:ro") for a in c)
    prep = sbx.phase_cmd("prepare", network=False, **kw)
    assert any(a.endswith(":/work/target:ro") for a in prep)
    assert not any("policy.json" in a for a in prep)
    assert "--network" not in sbx.phase_cmd("fetch", network=True, **kw)


def test_run_in_sandbox_aborts_when_docker_dies(tmp_path):
    def fake(cmd, **kw):
        rc = 125 if cmd[:2] == ["docker", "run"] else 0
        return subprocess.CompletedProcess(cmd, rc, "", "daemon gone")
    with mock.patch.object(sbx.subprocess, "run", side_effect=fake) as m:
        with pytest.raises(HarnessUnavailable, match="exited 125"):
            sbx.run_in_sandbox(str(tmp_path), str(tmp_path / "out"))
    # the volume is still removed
    assert any(c.args[0][:3] == ["docker", "volume", "rm"] for c in m.call_args_list)
    assert not (tmp_path / "out" / "status.json").exists()
