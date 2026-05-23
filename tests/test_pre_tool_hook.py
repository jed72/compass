"""TRC-F1 — Frame remains mandatory, unchanged.

pre-tool.sh blocks an Edit on a production file when the current task has no
route.md (i.e. Frame did not complete).

The hook reads the hook context from stdin as JSON (Claude Code PreToolUse
format) and inspects the .compass/current-task pointer to find the task
directory. If the task directory lacks route.md, it exits 2 and writes a
message to stderr naming the missing route.md.

This test creates a synthetic Compass project in a tmp directory, sets up
.compass/current-task pointing at a task without route.md, then invokes
hooks/pre-tool.sh with the synthetic tool call JSON.

IMPORTANT NOTE on path design:
  hooks/pre-tool.sh exempts any target file whose path matches *test* or
  *Test* (so you can always write the failing test before any red is on record).
  This means the project directory and target file path must not contain the
  word "test" as a substring. We use tempfile.mkdtemp with a "compass-fixture-"
  prefix and place the target at "src/app.py" to avoid this exemption.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path



FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent
HOOK_PATH = FRAMEWORK_ROOT / "hooks" / "pre-tool.sh"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_compass_project(root: Path, slug: str, *, with_route_md: bool) -> Path:
    """Scaffold a minimal Compass project under root.

    Returns the task directory path.
    """
    compass_dir = root / ".compass"
    work_dir = compass_dir / "work"
    task_dir = work_dir / slug
    task_dir.mkdir(parents=True, exist_ok=True)

    # .compass/current-task points at our slug
    (compass_dir / "current-task").write_text(slug, encoding="utf-8")

    # Optionally create route.md
    if with_route_md:
        (task_dir / "route.md").write_text(
            "# Route\n\nroute: express\n", encoding="utf-8"
        )

    return task_dir


def _hook_env(project_dir: Path) -> dict:
    """Environment for the hook subprocess."""
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    return env


def _tool_call_json(file_path: str, tool_name: str = "Edit") -> str:
    """Build a Claude Code PreToolUse JSON payload."""
    return json.dumps({
        "tool_name": tool_name,
        "tool_input": {
            "file_path": file_path,
        },
    })


def _fresh_project_dir() -> Path:
    """Return a new temp directory whose absolute path contains no 'test' substring.

    hooks/pre-tool.sh exempts any path matching *test* or *Test* (that is the
    escape hatch so engineers can always write the failing test). pytest's
    tmp_path fixture always includes the test function name in the path (e.g.
    ".../pytest-0/test_blocks_without_frame0/"), which contains "test". We
    therefore create our own directory whose path is clean.
    """
    d = tempfile.mkdtemp(prefix="compass-fix-")
    return Path(d)


# ---------------------------------------------------------------------------
# TRC-F1: hook blocks when route.md is absent
# ---------------------------------------------------------------------------

def test_blocks_without_frame():
    """Frame is still required — hook exits 2 and names missing route.md.

    Given a fresh task with no route.md
    When any tool attempts to Edit a file under the project source (a .py file)
    Then hooks/pre-tool.sh blocks the edit (exit code 2)
    And the block message names the missing route.md
    """
    assert HOOK_PATH.is_file(), f"pre-tool.sh not found at {HOOK_PATH}"

    project = _fresh_project_dir()
    try:
        slug = "no-frame-slug"
        _make_compass_project(project, slug, with_route_md=False)

        # Target a recognised production file (.py extension).
        # "src/app.py" — no "test" component anywhere in the path.
        target = str(project / "src" / "app.py")
        assert "test" not in target.lower(), (
            f"Target path must not contain 'test': {target}"
        )
        payload = _tool_call_json(target, tool_name="Edit")

        result = subprocess.run(
            ["bash", str(HOOK_PATH)],
            input=payload,
            capture_output=True,
            text=True,
            env=_hook_env(project),
        )

        # Hook must block
        assert result.returncode == 2, (
            f"Expected exit 2 (block), got {result.returncode}.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
        # Block message must name route.md
        assert "route.md" in result.stderr, (
            f"Expected 'route.md' in stderr.\nstderr: {result.stderr}"
        )
    finally:
        shutil.rmtree(str(project), ignore_errors=True)


def test_allows_when_route_md_present_and_red_marker():
    """Hook allows the edit when route.md exists and the .red marker is set.

    This is the complementary positive case — confirms the hook's basic
    allow-path still works after the F1 regression check.
    """
    assert HOOK_PATH.is_file(), f"pre-tool.sh not found at {HOOK_PATH}"

    project = _fresh_project_dir()
    try:
        slug = "framed-slug"
        task_dir = _make_compass_project(project, slug, with_route_md=True)

        # Drop the .red marker so the hook's green path is satisfied
        (task_dir / ".red").write_text("", encoding="utf-8")

        target = str(project / "src" / "app.py")
        payload = _tool_call_json(target, tool_name="Edit")

        result = subprocess.run(
            ["bash", str(HOOK_PATH)],
            input=payload,
            capture_output=True,
            text=True,
            env=_hook_env(project),
        )

        assert result.returncode == 0, (
            f"Expected exit 0 (allow), got {result.returncode}.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
    finally:
        shutil.rmtree(str(project), ignore_errors=True)


def test_hook_exits_zero_for_non_code_file():
    """Hook exempts non-production files (e.g. .md docs) from the check."""
    assert HOOK_PATH.is_file(), f"pre-tool.sh not found at {HOOK_PATH}"

    project = _fresh_project_dir()
    try:
        slug = "no-frame-slug"
        _make_compass_project(project, slug, with_route_md=False)

        # Markdown files are always exempt regardless of task state
        target = str(project / "README.md")
        payload = _tool_call_json(target, tool_name="Edit")

        result = subprocess.run(
            ["bash", str(HOOK_PATH)],
            input=payload,
            capture_output=True,
            text=True,
            env=_hook_env(project),
        )

        assert result.returncode == 0, (
            f"Expected exit 0 (exempt), got {result.returncode}.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
    finally:
        shutil.rmtree(str(project), ignore_errors=True)
