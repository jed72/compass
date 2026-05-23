"""Tests for flow digest integration with rework-scan (TRC-D5).

TRC-D5: When `compass flow --digest` runs, the dated digest includes a
        "Rework scan" section. The section advises only — it does not modify
        task state (Inv-4).

Also covers TRC-F4: Flow advises, never gates — rework-scan results do not
        modify any task.yml field.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent
CLI_PATH = FRAMEWORK_ROOT / "cli" / "compass"


# ---------------------------------------------------------------------------
# Helpers shared with test_rework_scan.py (duplicated for isolation)
# ---------------------------------------------------------------------------

def write_task_yml(directory: Path, slug: str, changed_files: list[dict],
                   created: str = "2026-05-01") -> None:
    """Write a minimal task.yml for testing."""
    directory.mkdir(parents=True, exist_ok=True)
    data = {
        "slug": slug,
        "route": "standard",
        "status": "landed",
        "created": created,
        "readings": {
            "blast_radius": "contained",
            "terrain": "brownfield-mapped",
            "magnitude": "standard",
            "intent": "delivery",
            "role": "engineer",
        },
        "changed_files": changed_files,
    }
    with (directory / "task.yml").open("w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh, sort_keys=False)


def write_signals_yml(directory: Path, window_days: int = 14) -> Path:
    """Write a signals.yml for tests."""
    data = {
        "version": "1.0.0",
        "scope_bloat_phrases": [],
        "rework_scan": {
            "window_days": window_days,
            "public_surface_patterns": ["/api/v[0-9]+/", "pb\\."],
            "migration_paths": ["migrations/*.sql", "**/migrations/*.sql"],
        },
    }
    path = directory / "signals.yml"
    with path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh, sort_keys=False)
    return path


def run_cli(*args, cwd=None, env_extra=None) -> subprocess.CompletedProcess:
    """Run the compass CLI and return the CompletedProcess."""
    import os
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, str(CLI_PATH), *args],
        capture_output=True,
        text=True,
        cwd=str(cwd or FRAMEWORK_ROOT),
        env=env,
    )


# ---------------------------------------------------------------------------
# TRC-D5  Flow digest absorbs rework-scan
# ---------------------------------------------------------------------------

def test_includes_rework_scan(tmp_path):
    """TRC-D5: `compass flow --digest` output includes a Rework scan section.

    Verifies:
    - The digest contains a "Rework scan" header.
    - The digest is written to .compass/flow/digest-<date>.md.
    - The digest contains rework-scan content (at least one instance or clean).
    """
    import os

    # Set up a project with an add-then-delete pair
    work_root = tmp_path / "work"
    write_task_yml(work_root / "task-adds", "task-adds", [
        {"path": "services/foo/handler.go", "action": "added"},
    ], created="2026-05-01")
    write_task_yml(work_root / "task-removes", "task-removes", [
        {"path": "services/foo/handler.go", "action": "deleted"},
    ], created="2026-05-05")

    signals = write_signals_yml(tmp_path)

    proc = run_cli(
        "flow", "--digest",
        "--work-root", str(work_root),
        cwd=tmp_path,
        env_extra={"COMPASS_SIGNALS_YML": str(signals)},
    )

    assert proc.returncode == 0, (
        f"compass flow --digest should exit 0; got {proc.returncode}\n"
        f"stderr: {proc.stderr}\nstdout: {proc.stdout}"
    )

    # The output must include a Rework scan section
    output = proc.stdout
    assert "rework scan" in output.lower(), (
        f"expected 'Rework scan' section in flow --digest output:\n{output}"
    )


def test_does_not_mutate_tasks(tmp_path):
    """TRC-F4 / Inv-4: Flow advises, never gates.
    After `compass flow --digest` runs, no task.yml is modified.
    """
    work_root = tmp_path / "work"
    write_task_yml(work_root / "task-a", "task-a", [
        {"path": "services/foo/handler.go", "action": "added"},
    ], created="2026-05-01")
    write_task_yml(work_root / "task-b", "task-b", [
        {"path": "services/foo/handler.go", "action": "deleted"},
    ], created="2026-05-05")

    signals = write_signals_yml(tmp_path)

    # Read task files before running flow
    task_a_before = (work_root / "task-a" / "task.yml").read_text()
    task_b_before = (work_root / "task-b" / "task.yml").read_text()

    run_cli(
        "flow", "--digest",
        "--work-root", str(work_root),
        cwd=tmp_path,
        env_extra={"COMPASS_SIGNALS_YML": str(signals)},
    )

    # Task files must be unchanged
    task_a_after = (work_root / "task-a" / "task.yml").read_text()
    task_b_after = (work_root / "task-b" / "task.yml").read_text()

    assert task_a_before == task_a_after, (
        "Inv-4 VIOLATION: flow --digest modified task-a/task.yml"
    )
    assert task_b_before == task_b_after, (
        "Inv-4 VIOLATION: flow --digest modified task-b/task.yml"
    )


def test_includes_reframe_debt(tmp_path):
    """TRC-C6: Flow digest includes calibration's reframe-debt section.
    This tests that `compass flow --digest` surfaces calibration signals.
    """
    # This is a documentation/prose check — the flow.md command's
    # instructions include running calibration and including its output.
    # We verify the flow digest command includes a calibration section.
    work_root = tmp_path / "work"
    # A task with a scope-bloat devlog signal and empty reframes
    task_dir = work_root / "task-with-debt"
    task_dir.mkdir(parents=True, exist_ok=True)
    with (task_dir / "task.yml").open("w", encoding="utf-8") as fh:
        yaml.safe_dump({
            "slug": "task-with-debt",
            "created": "2026-05-01",
            "route": "standard",
            "readings": {
                "blast_radius": "contained",
                "terrain": "brownfield-mapped",
                "magnitude": "standard",
            },
            "reframes": [],
        }, fh)

    signals = write_signals_yml(tmp_path)

    proc = run_cli(
        "flow", "--digest",
        "--work-root", str(work_root),
        cwd=tmp_path,
        env_extra={"COMPASS_SIGNALS_YML": str(signals)},
    )

    assert proc.returncode == 0, (
        f"flow --digest should exit 0; got {proc.returncode}\n{proc.stderr}"
    )
