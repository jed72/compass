"""The hook must block writes, never reads or prose (field report R12-followup).

1.8.0 taught the pre-tool hook to see shell commands that write production
files. Its inline-interpreter rule was too greedy in two ways, and both were
reported from the field within hours:

- `open(` was treated as a write regardless of mode, so a read-only
  `yaml.safe_load(open('.github/workflows/ci.yml'))` used to verify a change was
  blocked - the hook stopping an author from checking their own work.
- When that rule fired it lifted *every* path-like token out of the whole
  command, heredoc bodies included, so writing a document that merely names a
  `.sql` migration demanded a failing test for the migration. The reporter's
  third occurrence was this file's own bug report being blocked by the path
  quoted inside it.

Both push authors toward bypassing the hook, which costs more than the misses
the extra strictness prevented.

Scenarios: .compass/work/hotfix-1-8-1-false-blocks-and-land-scope/acceptance-criteria.md
(SCN-A1..A4).
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

ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / "hooks" / "pre-tool.sh"


def _project(*, red: bool = False) -> Path:
    """A framed project whose path contains no 'test'/'spec' substring."""
    root = Path(tempfile.mkdtemp(prefix="compass-fix-"))
    task_dir = root / ".compass" / "work" / "t"
    task_dir.mkdir(parents=True)
    (root / ".compass" / "current-task").write_text("t\n", encoding="utf-8")
    (task_dir / "delivery-approach.md").write_text("# Route\n", encoding="utf-8")
    if red:
        write_red_record(task_dir)
    return root


def _run(project: Path, command: str) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = str(project)
    return subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps({"tool_name": "Bash", "tool_input": {"command": command}}),
        capture_output=True, text=True, env=env, timeout=30,
    )


# ---------------------------------------------------------------------------
# SCN-A1, SCN-A2 - what must no longer be blocked
# ---------------------------------------------------------------------------

MUST_ALLOW = [
    pytest.param(
        'python3 -c "import yaml; d=yaml.safe_load(open(\'.github/workflows/ci.yml\')); print(len(d))"',
        id="SCN-A1-read-only-open",
    ),
    pytest.param(
        'python3 -c "print(open(\'src/app.py\').read())"',
        id="SCN-A1-read-then-print",
    ),
    pytest.param(
        'python3 -c "import json; json.load(open(\'package.json\'))"',
        id="SCN-A1-read-json",
    ),
    pytest.param(
        'python3 - <<\'PY\'\n'
        'import pathlib\n'
        'pathlib.Path("docs/notes.md").write_text("""\n'
        'The change drops two tables in 024_runs_and_attempts.sql\n'
        '""")\n'
        'PY',
        id="SCN-A2-path-named-in-written-prose",
    ),
    pytest.param(
        'python3 - <<\'PY\'\n'
        'import pathlib\n'
        'pathlib.Path("feedback.md").write_text("  Edit target: .github/workflows/ci.yml")\n'
        'PY',
        id="SCN-A2-report-quoting-a-blocked-path",
    ),
]


@pytest.mark.parametrize("command", MUST_ALLOW)
def test_command_that_writes_no_production_file_is_allowed(command):
    project = _project(red=False)
    try:
        result = _run(project, command)
        assert result.returncode == 0, (
            f"the hook blocked a command that writes no production file:\n"
            f"  command: {command}\n{result.stderr}"
        )
    finally:
        shutil.rmtree(project, ignore_errors=True)


# ---------------------------------------------------------------------------
# SCN-A3, SCN-A4 - what must still be blocked (the narrowing must not go too far)
# ---------------------------------------------------------------------------

MUST_BLOCK = [
    pytest.param('python3 -c \'open("src/app.py","w").write("x")\'', id="SCN-A3-open-w"),
    pytest.param('python3 -c \'open("src/app.py", "a").write("x")\'', id="SCN-A3-open-a"),
    pytest.param('python3 -c \'open("src/app.py","wb").write(b"x")\'', id="SCN-A3-open-wb"),
    pytest.param(
        'python3 - <<\'PY\'\nimport pathlib\npathlib.Path("src/app.py").write_text("x")\nPY',
        id="SCN-A4-heredoc-write-text",
    ),
    # The two-step form is the commonest heredoc idiom - and the one used to
    # edit this repository's own source all session - so the narrowing must not
    # lose it. Here the write is on a variable, not chained to Path(...).
    pytest.param(
        'python3 - <<\'PY\'\nimport pathlib\np = pathlib.Path("src/app.py")\np.write_text("x")\nPY',
        id="SCN-A4-heredoc-write-via-variable",
    ),
    pytest.param(
        'python3 -c \'f = open("src/app.py", "w"); f.write("x")\'',
        id="SCN-A3-open-via-variable",
    ),
]


# ---------------------------------------------------------------------------
# The read-then-generate case: reading one file and writing another must be
# judged on what it writes, not on what it reads.
# ---------------------------------------------------------------------------

def test_reading_a_source_file_while_writing_a_doc_is_allowed():
    project = _project(red=False)
    try:
        result = _run(project, (
            'python3 - <<\'PY\'\nimport pathlib\n'
            'src = pathlib.Path("src/app.py").read_text()\n'
            'pathlib.Path("docs/api.md").write_text(src[:100])\n'
            'PY'
        ))
        assert result.returncode == 0, (
            f"blocked on the file it READ while writing a doc:\n{result.stderr}"
        )
    finally:
        shutil.rmtree(project, ignore_errors=True)


@pytest.mark.parametrize("command", MUST_BLOCK)
def test_inline_script_writing_a_production_file_is_still_blocked(command):
    project = _project(red=False)
    try:
        result = _run(project, command)
        assert result.returncode == 2, (
            f"a real write to production code was allowed:\n"
            f"  command: {command}\n{result.stdout}{result.stderr}"
        )
    finally:
        shutil.rmtree(project, ignore_errors=True)
