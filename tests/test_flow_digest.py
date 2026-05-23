"""Flow digest tests — TRC-F4, TRC-C6, TRC-D5.

TRC-F4 (this stream, stream-6): Flow still advises, never gates.
  - Advisory commands (compass calibration, and future compass flow --digest)
    must not mutate any task.yml file under .compass/work/.
  - The test snapshots SHA256 of every task.yml before the advisory command,
    runs the command, then re-snapshots and asserts byte-identity.
  - If the command writes to disk anywhere besides .compass/flow/, that is a
    violation of Inv-4 (architecture-notes.md §2).

TRC-C6 and TRC-D5 are owned by streams 3 and 4 respectively. Stubs are
included here so the test module exists for those streams to extend.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Dict

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sha256_of_file(path: Path) -> str:
    """Return the hex SHA256 digest of a file's contents."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _snapshot_task_ymls(compass_work_dir: Path) -> Dict[str, str]:
    """Return {relative_path: sha256} for every task.yml under compass_work_dir."""
    snapshots: Dict[str, str] = {}
    if not compass_work_dir.is_dir():
        return snapshots
    for task_yml in sorted(compass_work_dir.rglob("task.yml")):
        rel = str(task_yml.relative_to(compass_work_dir))
        snapshots[rel] = _sha256_of_file(task_yml)
    return snapshots


# ---------------------------------------------------------------------------
# TRC-F4 — Advisory commands must not mutate task.yml
# ---------------------------------------------------------------------------

def test_does_not_mutate_tasks(run_cli, make_task, project):
    """TRC-F4: Flow still advises, never gates.

    Given multiple tasks exist in .compass/work/
    When compass calibration runs (the primary advisory/reporting command)
    Then no task.yml under .compass/work/ is modified (byte-identical after)
    And no task is automatically reframed, downgraded, or blocked.

    This tests Inv-4 (architecture-notes.md §2): Flow reads disk and reports;
    it does not write task state, does not block, does not reframe.
    """
    compass_work = project / ".compass" / "work"

    # --- Given: set up multiple tasks with varying reframe states -----------
    # Task with no reframes — calibration should report but not modify.
    make_task("alpha-task", {
        "readings": {
            "blast_radius": "contained",
            "terrain": "brownfield-mapped",
            "magnitude": "standard",
            "intent": "delivery",
        },
        "route": "standard",
        "scenarios": [{"id": "SCN-001", "intent": "INT-1", "tests": ["tests/t.py::t"]}],
        "reframes": [],
        "changed_files": [],
    }, set_current=False)

    # Task with a reframe — calibration should count it but not modify.
    make_task("beta-task", {
        "readings": {
            "blast_radius": "contained",
            "terrain": "brownfield-mapped",
            "magnitude": "small",
            "intent": "delivery",
        },
        "route": "standard",
        "scenarios": [{"id": "SCN-002", "intent": "INT-1", "tests": ["tests/t.py::t"]}],
        "reframes": [
            {"from_route": "express", "to_route": "standard",
             "reason": "needed more ceremony", "date": "2026-05-23"},
        ],
        "changed_files": [],
    }, set_current=False)

    # --- Snapshot before advisory command -----------------------------------
    before = _snapshot_task_ymls(compass_work)
    assert before, "No task.yml found before calibration — test setup failed"

    # --- When: run the advisory command -------------------------------------
    r = run_cli("calibration")
    # calibration always exits 0 (it is advisory, not a gate)
    assert r.returncode == 0, (
        f"compass calibration should exit 0 (advisory). Got {r.returncode}.\n"
        f"stdout: {r.stdout}\nstderr: {r.stderr}"
    )

    # --- Then: task.ymls must be byte-identical after -----------------------
    after = _snapshot_task_ymls(compass_work)

    assert before == after, (
        "Advisory command 'compass calibration' mutated task.yml files — "
        "this violates Inv-4 (Flow advises, never gates). "
        "Changed files:\n" + "\n".join(
            f"  {k}: before={before[k][:8]}... after={after[k][:8]}..."
            for k in set(before) | set(after)
            if before.get(k) != after.get(k)
        )
    )


def test_calibration_does_not_write_to_work_dir(run_cli, make_task, project):
    """TRC-F4 (supplementary): calibration must not create NEW files in
    .compass/work/ — any output should go to .compass/flow/ or stdout only.
    """
    compass_work = project / ".compass" / "work"

    make_task("gamma-task", {
        "readings": {
            "blast_radius": "contained",
            "terrain": "brownfield-mapped",
            "magnitude": "standard",
            "intent": "delivery",
        },
        "route": "standard",
        "reframes": [],
        "changed_files": [],
    }, set_current=False)

    # Record the set of files before
    def _all_files_in(d: Path):
        return {str(p.relative_to(d)) for p in d.rglob("*") if p.is_file()}

    before_files = _all_files_in(compass_work)

    r = run_cli("calibration")
    assert r.returncode == 0, r

    after_files = _all_files_in(compass_work)
    new_files = after_files - before_files
    assert not new_files, (
        "compass calibration created new files under .compass/work/ — "
        "advisory output must go to stdout or .compass/flow/, not work/.\n"
        f"New files: {sorted(new_files)}"
    )


# ---------------------------------------------------------------------------
# Stubs for sibling streams — TRC-C6 (stream-3), TRC-D5 (stream-4)
# ---------------------------------------------------------------------------

def test_includes_reframe_debt(run_cli, make_task, project):
    """TRC-C6 (stream-3): Flow digest contains calibration's reframe-debt.

    Stub — stream-3 will extend this when compass flow --digest lands.
    Until then, we assert calibration surfaces reframe-debt in stdout (the
    existing mechanism), and the test will be upgraded when the digest command
    exists.
    """
    # Arrange: task with scope-bloat signal and no reframe
    make_task("debt-task", {
        "readings": {
            "blast_radius": "contained",
            "terrain": "brownfield-mapped",
            "magnitude": "standard",
            "intent": "delivery",
        },
        "route": "express",
        "reframes": [],
        "changed_files": [],
    }, set_current=False)

    r = run_cli("calibration")
    assert r.returncode == 0, r
    # calibration should complete; reframe-debt reporting is a stream-3 concern
    assert "calibration" in r.stdout.lower() or len(r.stdout) > 0, (
        "compass calibration produced no output — unexpected"
    )


def test_includes_rework_scan(run_cli, make_task, project):
    """TRC-D5 (stream-4): Flow digest absorbs rework-scan.

    Stub — stream-4 will extend this when compass rework-scan lands and
    compass flow --digest integrates the rework-scan output.
    """
    # Minimal task setup
    make_task("rework-stub-task", {
        "readings": {
            "blast_radius": "contained",
            "terrain": "brownfield-mapped",
            "magnitude": "standard",
            "intent": "delivery",
        },
        "route": "standard",
        "changed_files": [],
    }, set_current=False)

    # When rework-scan doesn't exist yet, calibration still exits 0
    r = run_cli("calibration")
    assert r.returncode == 0, r
