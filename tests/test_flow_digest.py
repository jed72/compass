"""Flow digest — reframe-debt and no-mutation invariants.

TRC-C6 — Flow digest includes calibration's reframe-debt section
TRC-D5 — Flow digest absorbs rework-scan (stub; full coverage in test_rework_scan)
TRC-F4 — Flow still advises, never gates (calibration/rework-scan do not mutate task.yml)

The flow digest is the markdown file written by /compass:flow --digest.
For this task's scope: we assert that the flow command's digest output
contains the reframe-debt section produced by calibration, and that
running calibration leaves all task.yml files unmodified (B-Risk 5 /
Inv-4).
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent
CLI_PATH = FRAMEWORK_ROOT / "cli" / "compass"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _make_project(tmp_path: Path) -> Path:
    import shutil
    compass = tmp_path / ".compass"
    (compass / "work").mkdir(parents=True, exist_ok=True)
    (compass / "config.yml").write_text("version: 1.0.0\nmode: enforced\n")
    gov_src = FRAMEWORK_ROOT / "governance"
    gov_dst = tmp_path / "governance"
    gov_dst.mkdir(parents=True, exist_ok=True)
    for f in gov_src.iterdir():
        if f.is_file():
            shutil.copy(f, gov_dst / f.name)
    return tmp_path


def _make_task(project: Path, slug: str, body: dict) -> Path:
    task_dir = project / ".compass" / "work" / slug
    task_dir.mkdir(parents=True, exist_ok=True)
    with (task_dir / "task.yml").open("w") as fh:
        yaml.safe_dump(body, fh, sort_keys=False)
    (project / ".compass" / "current-task").write_text(slug)
    return task_dir


def _run_cli(project: Path, *args: str) -> subprocess.CompletedProcess:
    import os
    env = dict(os.environ)
    return subprocess.run(
        [sys.executable, str(CLI_PATH), *args],
        cwd=str(project),
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )


# ---------------------------------------------------------------------------
# TRC-C6 — Flow digest includes the reframe-debt section
# ---------------------------------------------------------------------------

def test_includes_reframe_debt(tmp_path):
    """TRC-C6: calibration --reframe-debt section appears in the output when
    tasks have scope-bloat phrases and no reframes.

    The test verifies that `compass calibration` output includes a
    'reframe debt' section when at least one task has a devlog scope-bloat
    phrase and an empty reframes list.
    """
    project = _make_project(tmp_path)

    # Task with a scope-bloat devlog phrase and no reframes
    task_body = {
        "task": "bloat-no-reframe",
        "created": "2026-05-20",
        "readings": {
            "blast_radius": "contained",
            "terrain": "brownfield-mapped",
            "magnitude": "small",
        },
        "route": "standard",
        "reframes": [],
    }
    task_dir = _make_task(project, "bloat-no-reframe", task_body)
    # Write devlog with a scope-bloat phrase
    (task_dir / "devlog.md").write_text(
        "2026-05-20: more files than Plan estimated\n"
    )

    result = _run_cli(project, "calibration")
    assert result.returncode == 0, result.stderr

    output = result.stdout.lower()
    assert "reframe debt" in output, (
        "Expected a 'reframe debt' section in calibration output when "
        "a task has scope-bloat devlog phrases and empty reframes.\n"
        f"Got:\n{result.stdout}"
    )
    assert "absorbed" in output or "signal lost" in output, (
        "The reframe-debt section should explain 'absorbed mis-frame, signal lost'.\n"
        f"Got:\n{result.stdout}"
    )


# ---------------------------------------------------------------------------
# TRC-D5 — Flow digest includes rework-scan (minimal structural assertion)
# ---------------------------------------------------------------------------

def test_includes_rework_scan(tmp_path):
    """TRC-D5: calibration output exists (rework-scan section integration
    is tested in full in test_rework_scan.py; this is the minimal structural
    assertion that the digest pathway doesn't crash on a clean project)."""
    project = _make_project(tmp_path)
    task_body = {
        "task": "clean-task",
        "created": "2026-05-20",
        "readings": {
            "blast_radius": "contained",
            "terrain": "brownfield-mapped",
            "magnitude": "small",
        },
        "route": "standard",
        "reframes": [],
        "changed_files": [],
    }
    _make_task(project, "clean-task", task_body)

    result = _run_cli(project, "calibration")
    assert result.returncode == 0, (
        f"calibration should not crash on a clean project\n{result.stderr}"
    )


# ---------------------------------------------------------------------------
# TRC-F4 — Calibration and rework-scan must not mutate any task.yml (B-Risk 5 / Inv-4)
# ---------------------------------------------------------------------------

def test_does_not_mutate_tasks(tmp_path):
    """TRC-F4 / B-Risk 5: compass calibration is strictly read-only over task.yml.

    Capture SHA256 of every task.yml before and after running calibration;
    assert they are identical.
    """
    project = _make_project(tmp_path)

    tasks_bodies = [
        {
            "task": f"task-{i}",
            "created": "2026-05-20",
            "readings": {
                "blast_radius": "contained",
                "terrain": "brownfield-mapped",
                "magnitude": "small",
            },
            "route": "standard",
            "reframes": [],
        }
        for i in range(3)
    ]
    task_dirs = []
    for body in tasks_bodies:
        slug = body["task"]
        td = _make_task(project, slug, body)
        # some with devlog scope-bloat phrases to trigger the reframe-debt path
        (td / "devlog.md").write_text("more files than Plan estimated\n")
        task_dirs.append(td)

    # Capture SHAs before
    before = {td / "task.yml": _sha256(td / "task.yml") for td in task_dirs}

    result = _run_cli(project, "calibration")
    assert result.returncode == 0, result.stderr

    # Verify SHAs after
    for path, sha_before in before.items():
        sha_after = _sha256(path)
        assert sha_before == sha_after, (
            f"B-Risk 5 violated: calibration mutated {path}\n"
            f"Before SHA: {sha_before}\nAfter SHA:  {sha_after}"
        )
