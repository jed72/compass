"""`compass land-commit` must commit only what the task owns (field report R11).

`land-commit` survives auto-fixing pre-commit hooks by re-staging what the hook
rewrote and retrying. The re-stage was `git add -A`, which stages the whole
tree - so anything the task does not own goes into the commit: a second agent's
uncommitted edits, untracked scratch, or the N unrelated files a repo-wide
formatter just touched.

Reported from the field: a repo-wide `ruff format` hook touched 94 files and
the index went from ~23 task files to 1,574, including a concurrent agent's
work. Only a manual inspection caught it before it committed. This is R5's cure
over-applied - the fix for a real problem, scoped too broadly.

Scenarios: .compass/work/hotfix-1-8-1-false-blocks-and-land-scope/spec.feature.md
(SCN-B1..B3).
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
CLI = ROOT / "cli" / "compass"
SLUG = "land-scope"


def _git(repo, *args, check=True):
    return subprocess.run(["git", "-C", str(repo), *args],
                          capture_output=True, text=True, check=check)


@pytest.fixture
def repo(tmp_path):
    """A git repo with one Compass task declaring exactly one owned file."""
    r = tmp_path / "proj"
    (r / "src").mkdir(parents=True)
    _git(r.parent, "init", "-q", "-b", "main", str(r))
    _git(r, "config", "user.email", "t@example.com")
    _git(r, "config", "user.name", "T")

    task_dir = r / ".compass" / "work" / SLUG
    task_dir.mkdir(parents=True)
    (r / ".compass" / "current-task").write_text(SLUG + "\n")
    (task_dir / "delivery-approach.md").write_text("# Route\n")
    (task_dir / "task.yml").write_text(yaml.safe_dump({
        "schema_version": "1.1", "task": SLUG, "created": "2026-08-04",
        "status": "active",
        "assessment": {"risk": "contained", "familiarity": "greenfield",
                     "size": "small", "intent": "delivery",
                     "urgency": "none", "role": "engineer", "labels": []},
        "delivery_approach": "standard", "topology": "solo", "policy_rules_fired": [],
        "stages": {}, "evidence": [], "gates": [], "scenarios": [],
        "changed_files": [{"path": "src/owned.py", "scenarios": ["SCN-1"]}],
        "claims": [], "follow_ups": [], "reassessments": [], "friction": [],
    }, sort_keys=False))

    (r / "src" / "owned.py").write_text("x = 1\n")
    (r / "src" / "other.py").write_text("y = 1\n")
    (r / "README.md").write_text("# demo\n")
    _git(r, "add", "-A")
    _git(r, "commit", "-q", "-m", "init")
    return r


def _install_autofixing_hook(repo):
    """A git pre-commit hook that behaves like `ruff format` under pre-commit:
    it rewrites a staged file and aborts the commit the first time, then passes.

    This is what triggers land-commit's retry path - the one that re-staged the
    whole tree. Without it the retry never runs and the scope assertions below
    would pass vacuously.
    """
    hook = repo / ".git" / "hooks" / "pre-commit"
    hook.write_text(
        "#!/bin/sh\n"
        "if [ ! -f .git/formatted-once ]; then\n"
        "  touch .git/formatted-once\n"
        "  printf 'x = 1  # reformatted\\n' > src/owned.py\n"
        "  exit 1\n"
        "fi\n"
        "exit 0\n"
    )
    os.chmod(hook, 0o755)


def _land(repo, *extra):
    return subprocess.run(
        [sys.executable, str(CLI), "land-commit", "-m", "land it",
         "--task", SLUG, *extra],
        cwd=str(repo), capture_output=True, text=True, timeout=60,
    )


def _committed_files(repo):
    out = _git(repo, "show", "--name-only", "--pretty=format:", "HEAD").stdout
    return {line.strip() for line in out.splitlines() if line.strip()}


def test_scn_b1_unrelated_dirty_file_is_not_swept_into_the_land_commit(repo):
    """The concurrent-agent case: another file is modified but not staged."""
    _install_autofixing_hook(repo)
    (repo / "src" / "owned.py").write_text("x = 2\n")
    (repo / "src" / "other.py").write_text("y = 999  # another agent's work\n")
    _git(repo, "add", "--", "src/owned.py")

    result = _land(repo)
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"

    committed = _committed_files(repo)
    assert "src/owned.py" in committed, committed
    assert "src/other.py" not in committed, (
        f"land-commit swept an unrelated modified file into the commit: {committed}"
    )


def test_scn_b1_untracked_scratch_is_not_swept_in(repo):
    """`git add -A` also picks up untracked files - scratch dirs, other agents'
    working notes. Those must not land either."""
    _install_autofixing_hook(repo)
    (repo / "src" / "owned.py").write_text("x = 3\n")
    (repo / "scratch").mkdir()
    (repo / "scratch" / "notes.txt").write_text("someone else's work\n")
    _git(repo, "add", "--", "src/owned.py")

    result = _land(repo)
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"

    committed = _committed_files(repo)
    assert not any(f.startswith("scratch/") for f in committed), (
        f"untracked scratch was committed: {committed}"
    )


def test_scn_b2_out_of_scope_staged_path_aborts_the_commit(repo):
    """If something else staged a path the task does not declare, refuse rather
    than commit it under this task's message."""
    (repo / "src" / "owned.py").write_text("x = 4\n")
    (repo / "src" / "other.py").write_text("y = 4\n")
    _git(repo, "add", "--", "src/owned.py", "src/other.py")

    head_before = _git(repo, "rev-parse", "HEAD").stdout.strip()
    result = _land(repo)
    head_after = _git(repo, "rev-parse", "HEAD").stdout.strip()

    assert result.returncode != 0, (
        f"committed an out-of-scope staged path:\n{result.stdout}"
    )
    assert head_after == head_before, "HEAD moved despite the out-of-scope path"
    combined = result.stdout + result.stderr
    assert "src/other.py" in combined, (
        f"the refusal must name the out-of-scope path:\n{combined}"
    )


def test_the_tasks_own_artifact_directory_is_always_in_scope(repo):
    """A Land commits the task's artifacts alongside its code; they are owned by
    definition and must not trip the scope check."""
    (repo / "src" / "owned.py").write_text("x = 5\n")
    (repo / ".compass" / "work" / SLUG / "devlog.md").write_text("# Devlog\n")
    _git(repo, "add", "--", "src/owned.py",
         f".compass/work/{SLUG}/devlog.md")

    result = _land(repo)
    assert result.returncode == 0, (
        f"the task's own artifact directory was treated as out of scope:\n"
        f"{result.stdout}\n{result.stderr}"
    )
