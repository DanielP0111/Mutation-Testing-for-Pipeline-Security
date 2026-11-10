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
