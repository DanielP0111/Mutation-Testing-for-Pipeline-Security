"""
src/engine/validator.py

Validates a generated mutant by running `meson setup` on it. A mutant is
"setup-valid" when Meson configures the project without error (exit code 0),
i.e. the injected change did not break the build definition syntactically.

This is the milestone-level validity check from the schedule: the mutant does
not need to fully compile — it only needs Meson to accept and configure it.
"""

import shutil
import subprocess
import tempfile
from pathlib import Path


def validate_mutant(mutant_dir: str, timeout: int = 300) -> dict:
    """
    Run `meson setup` on a mutant project and report the outcome.

    Args:
        mutant_dir: path to the mutant project root (must contain meson.build).
        timeout:    seconds before the setup is abandoned.

    Returns:
        {
            "setup_ok":   bool,        # True iff meson setup returned 0
            "returncode": int | None,  # None if meson missing or timed out
            "status":     str,         # "valid" | "invalid" | "error" | "skipped"
            "log_tail":   str,         # last lines of meson output (for triage)
        }
    """
    root = Path(mutant_dir)
    if not (root / "meson.build").exists():
        return {
            "setup_ok": False,
            "returncode": None,
            "status": "skipped",
            "log_tail": "no top-level meson.build found",
        }

    if shutil.which("meson") is None:
        return {
            "setup_ok": False,
            "returncode": None,
            "status": "error",
            "log_tail": "meson not found on PATH",
        }

    build_dir = tempfile.mkdtemp(prefix="meson_validate_")
    try:
        proc = subprocess.run(
            ["meson", "setup", build_dir, str(root), "--wipe"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        ok = proc.returncode == 0
        output = (proc.stdout or "") + (proc.stderr or "")
        return {
            "setup_ok": ok,
            "returncode": proc.returncode,
            "status": "valid" if ok else "invalid",
            "log_tail": "\n".join(output.strip().splitlines()[-25:]),
        }
    except subprocess.TimeoutExpired:
        return {
            "setup_ok": False,
            "returncode": None,
            "status": "error",
            "log_tail": f"meson setup timed out after {timeout}s",
        }
    finally:
        shutil.rmtree(build_dir, ignore_errors=True)
