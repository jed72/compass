"""compass ship-commit (R5): the Land commit step must survive auto-fixing
pre-commit hooks and never silently believe a land that didn't move HEAD.

The defect: an auto-fixing pre-commit hook (ruff format/--fix) rewrites a
staged file and aborts the commit; HEAD does not move, but nothing notices.
land-commit detects the no-op, re-stages the hook's fixes, retries once, and
always verifies HEAD advanced - erroring loudly if not.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
import yaml


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(cwd),
                          capture_output=True, text=True)


def _init_repo(d: Path) -> None:
    _git(d, "init", "-q")
    _git(d, "config", "user.email", "t@example.com")
    _git(d, "config", "user.name", "Test")
    _git(d, "config", "commit.gpgsign", "false")
    (d / "file.txt").write_text("hello\n")
    _git(d, "add", "-A")
    _git(d, "commit", "-q", "-m", "init")


def _install_autofix_hook(d: Path, *, persistent: bool = False) -> None:
    """A pre-commit hook that rewrites a staged file and aborts (exit 1).

    persistent=False: rewrites only while NEEDS_FIX is present, so a re-stage +
    retry succeeds (the real ruff-fix case). persistent=True: rewrites and
    aborts every time, so no retry can ever succeed.
    """
    hook = d / ".git" / "hooks" / "pre-commit"
    hook.parent.mkdir(parents=True, exist_ok=True)
    if persistent:
        body = '#!/bin/sh\nprintf "churn\\n" >> file.txt\nexit 1\n'
    else:
        body = ('#!/bin/sh\n'
                'if grep -q NEEDS_FIX file.txt; then\n'
                '  sed -i.bak "s/NEEDS_FIX/FIXED/" file.txt && rm -f file.txt.bak\n'
                '  exit 1\n'
                'fi\n'
                'exit 0\n')
    hook.write_text(body)
    os.chmod(hook, 0o755)


def _head(d: Path) -> str:
    return _git(d, "rev-parse", "HEAD").stdout.strip()


def test_single_commit_noops_under_autofix_hook(run_cli, tmp_path):
    """TRC-R5-1 (distillation): a bare `git commit` no-ops under an auto-fixing
    hook - HEAD does not move. This is the trap land-commit must defeat."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    _install_autofix_hook(repo)
    (repo / "file.txt").write_text("NEEDS_FIX\n")
    _git(repo, "add", "-A")
    h0 = _head(repo)
    _git(repo, "commit", "-m", "try")     # hook rewrites + aborts
    assert _head(repo) == h0               # HEAD did NOT move - the silent no-op


def test_clean_then_commit_advances_head(run_cli, tmp_path):
    """TRC-R5-2: land-commit lands the staged change despite the auto-fix hook."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    _install_autofix_hook(repo)
    (repo / "file.txt").write_text("NEEDS_FIX\n")
    _git(repo, "add", "-A")
    h0 = _head(repo)
    r = run_cli("ship-commit", "-m", "land it", cwd=repo)
    assert r.returncode == 0, r
    assert _head(repo) != h0, r


def test_noop_detected_retry_advances_head(run_cli, tmp_path):
    """TRC-R5-3: the no-op is detected, fixes re-staged, retry advances HEAD,
    and the retry is reported (not silent)."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    _install_autofix_hook(repo)
    (repo / "file.txt").write_text("NEEDS_FIX\n")
    _git(repo, "add", "-A")
    h0 = _head(repo)
    r = run_cli("ship-commit", "-m", "land it", cwd=repo)
    assert r.returncode == 0, r
    assert _head(repo) != h0, r
    assert "retry" in (r.stdout + r.stderr).lower(), r
    assert "FIXED" in (repo / "file.txt").read_text(), r   # the hook's fix landed


def test_head_advance_always_verified(run_cli, tmp_path):
    """TRC-R5-4: a successful land prints the advanced HEAD as evidence."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    (repo / "file.txt").write_text("clean change\n")
    _git(repo, "add", "-A")
    h0 = _head(repo)
    r = run_cli("ship-commit", "-m", "clean land", cwd=repo)
    assert r.returncode == 0, r
    h1 = _head(repo)
    assert h1 != h0, r
    assert h1[:8] in (r.stdout + r.stderr), r


def test_persistent_noop_errors_loudly(run_cli, tmp_path):
    """TRC-R5-F1: a hook that keeps aborting → land-commit errors, HEAD unmoved,
    and any --issue status stays active (never a silent false land)."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    # a task to prove status is not flipped to landed
    task_dir = repo / ".compass" / "work" / "slug"
    task_dir.mkdir(parents=True)
    (task_dir / "manifest.yml").write_text(
        yaml.safe_dump({"task": "slug", "status": "active"}, sort_keys=False))
    _install_autofix_hook(repo, persistent=True)
    (repo / "file.txt").write_text("NEEDS_FIX\n")
    _git(repo, "add", "-A")
    h0 = _head(repo)
    r = run_cli("ship-commit", "-m", "land it", "--issue", "slug", cwd=repo)
    assert r.returncode != 0, r
    assert _head(repo) == h0, r
    combined = (r.stdout + r.stderr).lower()
    assert "head" in combined and ("did not advance" in combined or "not happen" in combined), r
    status = yaml.safe_load((task_dir / "manifest.yml").read_text())["status"]
    assert status == "active", r


def test_empty_staging_is_explicit_error(run_cli, tmp_path):
    """TRC-R5-F2: nothing staged → an explicit error, not a retry loop."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    h0 = _head(repo)
    r = run_cli("ship-commit", "-m", "nothing", cwd=repo)
    assert r.returncode != 0, r
    assert "nothing staged" in (r.stdout + r.stderr).lower(), r
    assert _head(repo) == h0, r
