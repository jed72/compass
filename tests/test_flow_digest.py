"""Flow digest tests — TRC-F4, TRC-C6, TRC-D5.

Unified after integration of streams 3, 4, and 6:

- TRC-F4 (stream-6, canonical): Flow advises, never gates. Snapshot SHA256 of
  every task.yml before/after running advisory commands; assert byte-identity.
- TRC-D5 (stream-4): `compass flow --digest` includes a Rework scan section.
- TRC-C6 (stream-3): the digest surfaces calibration's reframe-debt section.
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict

import pytest
import yaml

FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent
CLI_PATH = FRAMEWORK_ROOT / "cli" / "compass"


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


def write_task_yml(directory: Path, slug: str, changed_files: list,
                   created: str = "2026-05-01") -> None:
    """Write a minimal task.yml for testing (stream-4 helper)."""
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
    """Write a signals.yml for tests (stream-4 helper)."""
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


def run_subprocess_cli(*args, cwd=None, env_extra=None) -> subprocess.CompletedProcess:
    """Run the compass CLI via subprocess in an isolated cwd (stream-4 helper)."""
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
# TRC-F4 (stream-6, canonical) — Advisory commands must not mutate task.yml
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
# TRC-D5 (stream-4) — Flow digest absorbs rework-scan
# ---------------------------------------------------------------------------

def test_includes_rework_scan(tmp_path):
    """TRC-D5: `compass flow --digest` output includes a Rework scan section."""
    work_root = tmp_path / "work"
    write_task_yml(work_root / "task-adds", "task-adds", [
        {"path": "services/foo/handler.go", "action": "added"},
    ], created="2026-05-01")
    write_task_yml(work_root / "task-removes", "task-removes", [
        {"path": "services/foo/handler.go", "action": "deleted"},
    ], created="2026-05-05")

    signals = write_signals_yml(tmp_path)

    proc = run_subprocess_cli(
        "flow", "--digest",
        "--work-root", str(work_root),
        cwd=tmp_path,
        env_extra={"COMPASS_SIGNALS_YML": str(signals)},
    )

    assert proc.returncode == 0, (
        f"compass flow --digest should exit 0; got {proc.returncode}\n"
        f"stderr: {proc.stderr}\nstdout: {proc.stdout}"
    )

    output = proc.stdout
    assert "rework scan" in output.lower(), (
        f"expected 'Rework scan' section in flow --digest output:\n{output}"
    )


# ---------------------------------------------------------------------------
# TRC-C6 (stream-3) — Flow digest includes calibration's reframe-debt section
# ---------------------------------------------------------------------------

def test_includes_reframe_debt(tmp_path):
    """TRC-C6: calibration output includes a 'reframe debt' section when at
    least one task has a devlog scope-bloat phrase and an empty reframes list.
    """
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

    slug = "bloat-no-reframe"
    task_dir = compass / "work" / slug
    task_dir.mkdir(parents=True, exist_ok=True)
    task_body = {
        "task": slug,
        "created": "2026-05-20",
        "readings": {
            "blast_radius": "contained",
            "terrain": "brownfield-mapped",
            "magnitude": "small",
        },
        "route": "standard",
        "reframes": [],
    }
    with (task_dir / "task.yml").open("w") as fh:
        yaml.safe_dump(task_body, fh, sort_keys=False)
    (compass / "current-task").write_text(slug)
    (task_dir / "devlog.md").write_text(
        "2026-05-20: more files than Plan estimated\n"
    )

    env = dict(os.environ)
    result = subprocess.run(
        [sys.executable, str(CLI_PATH), "calibration"],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )
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
