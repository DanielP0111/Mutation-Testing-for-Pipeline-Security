"""check_docker() must stop the run before any mutant when the harness can't work."""

import subprocess
from unittest import mock

import pytest

from src.engine import harness_runner
from src.engine.harness_runner import check_docker


def _proc(rc, out="", err=""):
    return subprocess.CompletedProcess(args=[], returncode=rc, stdout=out, stderr=err)


def test_passes_when_daemon_and_image_present():
    with mock.patch.object(harness_runner.subprocess, "run",
                           side_effect=[_proc(0, "27.0.3"), _proc(0, "[]")]):
        check_docker()  # no SystemExit


def test_exits_when_docker_cli_missing():
    with mock.patch.object(harness_runner.subprocess, "run", side_effect=FileNotFoundError):
        with pytest.raises(SystemExit, match="not found on PATH"):
            check_docker()


def test_exits_when_daemon_unreachable():
    err = "Cannot connect to the Docker daemon at unix:///var/run/docker.sock."
    with mock.patch.object(harness_runner.subprocess, "run", return_value=_proc(1, err=err)):
        with pytest.raises(SystemExit, match="Docker is not reachable") as e:
            check_docker()
    assert "Cannot connect" in str(e.value)


def test_exits_when_docker_info_hangs():
    with mock.patch.object(harness_runner.subprocess, "run",
                           side_effect=subprocess.TimeoutExpired("docker", 15)):
        with pytest.raises(SystemExit, match="did not answer"):
            check_docker()


def test_exits_when_image_missing():
    with mock.patch.object(harness_runner.subprocess, "run",
                           side_effect=[_proc(0, "27.0.3"), _proc(1, err="No such image")]):
        with pytest.raises(SystemExit, match="docker build -t pipeline-harness harness/"):
            check_docker()


# --- mid-run guard: Docker dies after the preflight passed ------------------

@pytest.mark.parametrize("rc", [125, 126, 127])
def test_run_in_harness_raises_when_container_never_ran(tmp_path, rc):
    err = "docker: Error response from daemon: connection refused."
    with mock.patch.object(harness_runner.subprocess, "run", return_value=_proc(rc, err=err)):
        with pytest.raises(harness_runner.HarnessUnavailable, match=f"exited {rc}"):
            harness_runner.run_in_harness(str(tmp_path), str(tmp_path / "out"))
    # Nothing a later rerun would mistake for a finished result.
    assert not (tmp_path / "out" / "status.json").exists()


def test_run_in_harness_records_build_failures_normally(tmp_path):
    # rc 1 = run_build.sh ran and something failed: that IS a result.
    out = tmp_path / "out"
    out.mkdir()
    (out / "status.json").write_text('{"fetch_rc": 0, "setup_rc": 1, "compile_rc": -1, "test_rc": -1}')
    with mock.patch.object(harness_runner.subprocess, "run", return_value=_proc(1)):
        run = harness_runner.run_in_harness(str(tmp_path), str(out))
    assert run["status"]["setup_rc"] == 1
