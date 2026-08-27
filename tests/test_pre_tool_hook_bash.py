"""Red-before-green must apply to shell commands that write production files.

The hook enforced the TDD strategy for the Edit, Write, and MultiEdit tools.
A shell command that writes the same file - `sed -i`, a `>` redirect, an inline
`python3 -c` script - was never seen by it, so choosing a different tool
stepped around the enforcement entirely.

Detection is deliberately conservative and fails OPEN: only recognised write
shapes block, everything else is allowed, and the residual gap is stated in
docs/safety-contract.md. Blocking on suspicion would block `make`, `npm test`,
and every unrecognised command, and an enforcement people disable protects
nothing at all.

Scenarios: .compass/work/hook-bash-write-bypass/acceptance-criteria.md (SCN-A1..F2).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from conftest import write_red_record

FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent
HOOK_PATH = FRAMEWORK_ROOT / "hooks" / "pre-tool.sh"
HOOKS_JSON = FRAMEWORK_ROOT / "hooks" / "hooks.json"


def _fresh_project_dir() -> Path:
    """A temp dir whose path contains no 'test'/'spec' substring.

    The hook exempts those paths so the failing test can always be written; a
    fixture living under one would be exempt for the wrong reason and every
    assertion below would pass without checking anything.
    """
    return Path(tempfile.mkdtemp(prefix="compass-fix-"))


def _project(slug: str = "framed", *, route: bool = True, red: bool = False,
             spike: bool = False) -> tuple[Path, Path]:
    root = _fresh_project_dir()
    task_dir = root / ".compass" / "work" / slug
    task_dir.mkdir(parents=True)
    (root / ".compass" / "current-task").write_text(slug, encoding="utf-8")
    if route:
        (task_dir / "delivery-approach.md").write_text("# Route\n\nroute: standard\n", encoding="utf-8")
    if red:
        write_red_record(task_dir)
    if spike:
        (task_dir / ".spike").write_text("", encoding="utf-8")
    return root, task_dir


def _run(project: Path, payload: dict) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = str(project)
    return subprocess.run(
        ["bash", str(HOOK_PATH)],
        input=json.dumps(payload), capture_output=True, text=True, env=env,
    )


def _bash(command: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": command}}


# ---------------------------------------------------------------------------
# Group A - Bash writes that must be blocked (SCN-A1..A4)
# ---------------------------------------------------------------------------

BLOCKED_SHAPES = [
    pytest.param('echo "x = 1" > src/app.py', id="SCN-A1-redirect"),
    pytest.param('echo "x = 1" >> src/app.py', id="SCN-A1-append"),
    pytest.param("sed -i '' 's/a/b/' src/app.py", id="SCN-A2-sed-inplace"),
    pytest.param("perl -i -pe 's/a/b/' src/app.py", id="SCN-A2-perl-inplace"),
    pytest.param('python3 -c \'open("src/app.py","w").write("x")\'', id="SCN-A3-python-c"),
    pytest.param('echo x | tee src/app.py', id="SCN-A3-tee"),
    pytest.param('cp /tmp/thing.py src/app.py', id="SCN-A3-cp"),
    pytest.param('mv /tmp/thing.py src/app.py', id="SCN-A3-mv"),
    pytest.param('patch -p1 < /tmp/fix.diff', id="SCN-A3-patch"),
    pytest.param('git apply /tmp/fix.diff', id="SCN-A3-git-apply"),
]


@pytest.mark.parametrize("command", BLOCKED_SHAPES)
def test_write_shape_is_blocked_without_a_red(command):
    """SCN-A1..A3 - a recognised shell write of a source file needs a red first."""
    project, _ = _project(red=False)
    try:
        result = _run(project, _bash(command))
        assert result.returncode == 2, (
            f"expected a block for {command!r}, got exit {result.returncode}\n"
            f"stderr: {result.stderr}"
        )
    finally:
        shutil.rmtree(project, ignore_errors=True)


def test_block_message_names_the_command_and_the_tool():
    """A block a reader cannot act on is only half an enforcement."""
    project, _ = _project(red=False)
    try:
        result = _run(project, _bash("sed -i '' 's/a/b/' src/app.py"))
        assert result.returncode == 2
        assert "src/app.py" in result.stderr, result.stderr
        assert "Bash" in result.stderr, result.stderr
    finally:
        shutil.rmtree(project, ignore_errors=True)


def test_write_shape_is_allowed_once_a_red_is_on_record():
    """SCN-A4 - the marker means the same thing for Bash as for Edit."""
    project, _ = _project(red=True)
    try:
        result = _run(project, _bash("sed -i '' 's/a/b/' src/app.py"))
        assert result.returncode == 0, result.stderr
    finally:
        shutil.rmtree(project, ignore_errors=True)


# ---------------------------------------------------------------------------
# Group B - Bash that must not be blocked (SCN-B1..B4)
# ---------------------------------------------------------------------------

ALLOWED_COMMANDS = [
    pytest.param('grep -rn "TODO" src/', id="SCN-B1-read-only"),
    pytest.param('ls -la src/', id="SCN-B1-ls"),
    pytest.param('git commit -m "wip"', id="SCN-B1-git-commit"),
    pytest.param('make build', id="SCN-B1-make"),
    pytest.param("cat > tests/test_app.py <<'EOF'\nx\nEOF", id="SCN-B2-test-file"),
    pytest.param('echo "x" > docs/notes.md', id="SCN-B2-markdown"),
    pytest.param('python3 -m pytest -q > /tmp/out.txt', id="SCN-B3-non-code-dest"),
    pytest.param('echo hi > /dev/null', id="SCN-B3-dev-null"),
    pytest.param('git checkout -- src/app.py', id="SCN-B4-git-checkout"),
    pytest.param('git restore src/app.py', id="SCN-B4-git-restore"),
]


@pytest.mark.parametrize("command", ALLOWED_COMMANDS)
def test_ordinary_command_is_allowed(command):
    """SCN-B1..B4 - the hook does not obstruct work it has no business blocking."""
    project, _ = _project(red=False)
    try:
        result = _run(project, _bash(command))
        assert result.returncode == 0, (
            f"expected {command!r} to be allowed, got exit {result.returncode}\n"
            f"stderr: {result.stderr}"
        )
    finally:
        shutil.rmtree(project, ignore_errors=True)


# ---------------------------------------------------------------------------
# Group C - one classifier, one suspension (SCN-C1, SCN-C2)
# ---------------------------------------------------------------------------

SHARED_PATHS = ["src/app.py", "README.md", "tests/test_app.py", "src/notes.csv"]


@pytest.mark.parametrize("path", SHARED_PATHS)
def test_edit_and_bash_agree_on_the_same_path(path):
    """SCN-C1 - two classifiers would drift; there is only one."""
    project, _ = _project(red=False)
    try:
        as_edit = _run(project, {"tool_name": "Edit", "tool_input": {"file_path": path}})
        as_bash = _run(project, _bash(f'echo "x" > {path}'))
        assert as_edit.returncode == as_bash.returncode, (
            f"{path}: Edit exited {as_edit.returncode} but the equivalent Bash "
            f"redirect exited {as_bash.returncode} - the classifiers disagree."
        )
    finally:
        shutil.rmtree(project, ignore_errors=True)


def test_spike_route_suspends_the_check_for_bash_too():
    """SCN-C2 - on a Spike the TDD strategy is suspended, whichever tool is used."""
    project, _ = _project(red=False, spike=True)
    try:
        result = _run(project, _bash('echo "x" > src/probe.py'))
        assert result.returncode == 0, result.stderr
    finally:
        shutil.rmtree(project, ignore_errors=True)


# ---------------------------------------------------------------------------
# Failure modes (SCN-F1, SCN-F2)
# ---------------------------------------------------------------------------

def test_safety_contract_states_the_shell_detection_limit():
    """SCN-F1 - the gap that remains is written down, not left to be found."""
    contract = (FRAMEWORK_ROOT / "docs" / "safety-contract.md").read_text(encoding="utf-8")
    lowered = contract.lower()
    assert "best-effort" in lowered or "best effort" in lowered, (
        "docs/safety-contract.md must say that shell-command detection is "
        "best-effort - the contract currently promises more than the hook does."
    )
    assert "sed -i" in contract, (
        "the contract must name the shell write shapes that are detected, so a "
        "reader can tell which side of the line their command falls on."
    )


def test_read_only_command_does_not_consult_task_state():
    """SCN-F2 - the hook now runs on every Bash call; it must be cheap.

    A command with no write-shaped token is allowed without resolving the task,
    which is checked here by removing .compass entirely: the Edit path treats a
    missing .compass as "Frame has not run" and blocks, so if this command is
    allowed, the hook returned before looking.
    """
    project = _fresh_project_dir()
    try:
        result = _run(project, _bash('grep -rn "TODO" src/'))
        assert result.returncode == 0, (
            f"a read-only command consulted task state and blocked:\n{result.stderr}"
        )
    finally:
        shutil.rmtree(project, ignore_errors=True)


def test_hook_is_registered_for_bash():
    """The branch is unreachable unless hooks.json routes Bash to it."""
    registered = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))
    matchers = [
        entry.get("matcher", "")
        for entry in registered["hooks"]["PreToolUse"]
        if any("pre-tool.sh" in h.get("command", "") for h in entry.get("hooks", []))
    ]
    assert any("Bash" in m for m in matchers), (
        f"pre-tool.sh is not registered for Bash; PreToolUse matchers: {matchers}"
    )
