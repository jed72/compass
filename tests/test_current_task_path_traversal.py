"""The current-task pointer names an issue inside the work directory.

The pre-tool hook and the CLI read `.compass/current-task` and join it onto
`.compass/work/`. A pointer such as `../../side` resolved to a directory
outside the work directory, and the hook then read that directory's `.red`
marker and red record to decide whether an edit could go ahead. A slug is one
path segment; anything else is refused, naming where it came from.

Scenario ids: CTP-1 to CTP-3, in the delivery approach of issue
`pointer-path-traversal`.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
CLI = ROOT / "cli" / "compass"
BAD = ["../side", "../../side", "a/b", "..", "."]


@pytest.fixture
def project():
    """A project whose work directory holds a real issue, and a sibling
    directory outside it that holds a red record and marker. The path holds
    no "test", so the hook's test-file exemption does not fire."""
    root = Path(tempfile.mkdtemp(prefix="compass-ctp-"))
    work = root / ".compass" / "work"
    real = work / "real"
    real.mkdir(parents=True)
    (real / "manifest.yml").write_text(
        "schema_version: '2.0'\nissue: real\ncreated: '2026-09-25'\n"
        "status: active\n")
    side = root / ".compass" / "side"
    (side / "evidence").mkdir(parents=True)
    (side / "delivery-approach.md").write_text("# Approach\n")
    (side / ".red").write_text("")
    (side / "evidence" / "red.json").write_text(json.dumps(
        {"passed": False, "exit_code": 1, "timestamp": "2026-01-01T00:00:00"}))
    yield root
    shutil.rmtree(root, ignore_errors=True)


def _point(root, slug):
    (root / ".compass" / "current-task").write_text(slug + "\n")


def _hook(root):
    event = json.dumps({"tool_name": "Edit",
                        "tool_input": {"file_path": str(root / "src" / "app.py")}})
    return subprocess.run(["bash", str(ROOT / "hooks" / "pre-tool.sh")],
                          input=event, capture_output=True, text=True,
                          timeout=120,
                          env={**os.environ, "CLAUDE_PROJECT_DIR": str(root)})


def _cli(root, *args):
    return subprocess.run([sys.executable, str(CLI), *args], cwd=root,
                          capture_output=True, text=True,
                          env={**os.environ, "CLAUDE_PROJECT_DIR": str(root)})


@pytest.mark.parametrize("slug", ["../side"])
def test_ctp_1_a_pointer_holding_a_path_makes_the_hook_refuse(project, slug):
    _point(project, slug)
    result = _hook(project)
    assert result.returncode == 2, (result.returncode, result.stderr)
    assert ".compass/current-task" in result.stderr


@pytest.mark.parametrize("slug", BAD)
def test_ctp_2_the_cli_refuses_a_pointer_holding_a_path(project, slug):
    _point(project, slug)
    result = _cli(project, "check")
    assert result.returncode != 0
    text = " ".join((result.stdout + result.stderr).split())
    assert ".compass/current-task" in text and "one path segment" in text, text


@pytest.mark.parametrize("slug", BAD)
def test_ctp_2_the_cli_refuses_an_issue_flag_holding_a_path(project, slug):
    result = _cli(project, "check", "--issue", slug)
    assert result.returncode != 0
    text = " ".join((result.stdout + result.stderr).split())
    assert "--issue" in text and "one path segment" in text, text


def test_ctp_3_an_ordinary_slug_behaves_as_today(project):
    _point(project, "real")
    result = _cli(project, "next")
    assert "one path segment" not in result.stdout + result.stderr
