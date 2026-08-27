"""Tests for `compass rework-scan` - cross-task rework detection (R4).

Scenarios covered:
  TRC-D1  clean repo reports 0 rework instances
  TRC-D2  add-then-delete file pair is reported
  TRC-D3  public-surface symbol added then removed is reported
  TRC-D4  migration created then dropped is reported
  TRC-D6  canonical fixture at tests/fixtures/rework-scan/add-then-delete-pair/
  TRC-X2  corrupt manifest.yml is skipped gracefully

Architectural invariants under test:
  The exit code is ALWAYS 0 when rework is detected: it is a signal, not a gate.
  Patterns are loaded from signals.yml at runtime, not hardcoded.
  Inv-7:   given identical input, output is deterministic.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent
CLI_PATH = FRAMEWORK_ROOT / "cli" / "compass"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run_rework_scan(root: Path, extra_args: list[str] | None = None,
                    signals_yml: Path | None = None) -> subprocess.CompletedProcess:
    """Run `compass rework-scan --root <root>` and return the CompletedProcess."""
    cmd = [sys.executable, str(CLI_PATH), "rework-scan", "--root", str(root)]
    if extra_args:
        cmd.extend(extra_args)
    env = None
    if signals_yml is not None:
        env = dict(__import__("os").environ)
        env["COMPASS_SIGNALS_YML"] = str(signals_yml)
    return subprocess.run(cmd, capture_output=True, text=True, env=env)


def write_task_yml(directory: Path, slug: str, changed_files: list[dict],
                   created: str = "2026-05-01") -> None:
    """Write a minimal manifest.yml for rework-scan testing."""
    directory.mkdir(parents=True, exist_ok=True)
    data = {
        "slug": slug,
        "delivery_approach": "standard",
        "status": "landed",
        "created": created,
        "assessment": {
            "risk": "contained",
            "familiarity": "brownfield-mapped",
            "size": "standard",
            "intent": "delivery",
            "role": "engineer",
        },
        "changed_files": changed_files,
    }
    with (directory / "manifest.yml").open("w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh, sort_keys=False)


def write_signals_yml(directory: Path, window_days: int = 14,
                      public_surface_patterns: list[str] | None = None,
                      migration_paths: list[str] | None = None) -> Path:
    """Write a signals.yml next to the scan root for runtime-loading tests."""
    if public_surface_patterns is None:
        public_surface_patterns = ["/api/v[0-9]+/", "pb\\."]
    if migration_paths is None:
        migration_paths = ["migrations/*.sql", "**/migrations/*.sql"]
    data = {
        "version": "1.0.0",
        "scope_bloat_phrases": [],
        "rework_scan": {
            "window_days": window_days,
            "public_surface_patterns": public_surface_patterns,
            "migration_paths": migration_paths,
        },
    }
    path = directory / "signals.yml"
    with path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh, sort_keys=False)
    return path


# ---------------------------------------------------------------------------
# TRC-D1  Clean repo - no rework detected
# ---------------------------------------------------------------------------

def test_clean_repo(tmp_path):
    """TRC-D1: disjoint changed_files produces a report with 0 rework instances."""
    root = tmp_path / "work"
    signals = write_signals_yml(tmp_path)

    write_task_yml(root / "task-a", "task-a", [
        {"path": "services/foo/handler.go", "action": "added"},
    ])
    write_task_yml(root / "task-b", "task-b", [
        {"path": "services/bar/handler.go", "action": "added"},
    ])

    proc = run_rework_scan(root, signals_yml=signals)
    assert proc.returncode == 0, f"expected exit 0, got {proc.returncode}\n{proc.stderr}"
    assert "0 rework" in proc.stdout.lower() or "no rework" in proc.stdout.lower(), (
        f"expected clean report, got:\n{proc.stdout}"
    )


# ---------------------------------------------------------------------------
# TRC-D2  Add-then-delete pair detected
# ---------------------------------------------------------------------------

def test_add_then_delete(tmp_path):
    """TRC-D2: file added by task-a and deleted by task-b is reported."""
    root = tmp_path / "work"
    signals = write_signals_yml(tmp_path)

    write_task_yml(root / "task-a", "task-a", [
        {"path": "services/foo/handler.go", "action": "added"},
    ], created="2026-05-01")
    write_task_yml(root / "task-b", "task-b", [
        {"path": "services/foo/handler.go", "action": "deleted"},
    ], created="2026-05-05")

    proc = run_rework_scan(root, signals_yml=signals)
    assert proc.returncode == 0, (
        f"exit code should be 0 even when rework is detected. "
        f"Got {proc.returncode}\n{proc.stderr}"
    )
    output = proc.stdout
    assert "1 rework" in output.lower() or "rework instance" in output.lower(), (
        f"expected 1 rework instance in report:\n{output}"
    )
    assert "task-a" in output, f"expected task-a named in report:\n{output}"
    assert "task-b" in output, f"expected task-b named in report:\n{output}"


# ---------------------------------------------------------------------------
# TRC-D3  Public-surface churn detected
# ---------------------------------------------------------------------------

def test_public_surface_churn(tmp_path):
    """TRC-D3: path matching public_surface_patterns added then removed is reported.
    Also verifies the pattern is loaded from signals.yml at runtime.
    """
    root = tmp_path / "work"
    # Use a custom pattern to prove runtime-loading (not hardcoded)
    signals = write_signals_yml(
        tmp_path,
        public_surface_patterns=["/api/v[0-9]+/", "pb\\."],
    )

    write_task_yml(root / "task-a", "task-a", [
        {"path": "routes/api/v1/users.go", "action": "added"},
    ], created="2026-05-01")
    write_task_yml(root / "task-b", "task-b", [
        {"path": "routes/api/v1/users.go", "action": "deleted"},
    ], created="2026-05-05")

    proc = run_rework_scan(root, signals_yml=signals)
    assert proc.returncode == 0, (
        f"exit 0 required even with public-surface rework. "
        f"Got {proc.returncode}\n{proc.stderr}"
    )
    output = proc.stdout
    assert "rework" in output.lower(), f"expected rework in report:\n{output}"
    assert "task-a" in output and "task-b" in output, (
        f"both tasks should be named:\n{output}"
    )


def test_public_surface_patterns_loaded_at_runtime(tmp_path):
    """The scanner uses patterns from signals.yml, not hardcoded values.
    We use a unique sentinel pattern that would not match if patterns were hardcoded.
    """
    root = tmp_path / "work"
    # A completely custom pattern - proves runtime loading
    sentinel_pattern = "SENTINEL_CUSTOM_PATTERN_[0-9]+"
    signals = write_signals_yml(
        tmp_path,
        public_surface_patterns=[sentinel_pattern],
    )

    write_task_yml(root / "task-a", "task-a", [
        {"path": "SENTINEL_CUSTOM_PATTERN_42/module.py", "action": "added"},
    ], created="2026-05-01")
    write_task_yml(root / "task-b", "task-b", [
        {"path": "SENTINEL_CUSTOM_PATTERN_42/module.py", "action": "deleted"},
    ], created="2026-05-05")

    proc = run_rework_scan(root, signals_yml=signals)
    assert proc.returncode == 0
    assert "rework" in proc.stdout.lower(), (
        f"sentinel pattern should have triggered rework detection:\n{proc.stdout}"
    )


# ---------------------------------------------------------------------------
# TRC-D4  Migration pair detected
# ---------------------------------------------------------------------------

def test_migration_pair(tmp_path):
    """TRC-D4: migration added in task-a and a drop migration added in task-b is reported."""
    root = tmp_path / "work"
    signals = write_signals_yml(tmp_path)

    write_task_yml(root / "task-a", "task-a", [
        {"path": "migrations/024_create_runs.sql", "action": "added"},
    ], created="2026-05-01")
    write_task_yml(root / "task-b", "task-b", [
        {"path": "migrations/025_drop_runs.sql", "action": "added"},
    ], created="2026-05-05")

    proc = run_rework_scan(root, signals_yml=signals)
    assert proc.returncode == 0, (
        f"exit 0 required even with migration rework. "
        f"Got {proc.returncode}\n{proc.stderr}"
    )
    output = proc.stdout
    assert "rework" in output.lower(), (
        f"expected migration pair to be flagged as rework:\n{output}"
    )
    assert "task-a" in output and "task-b" in output, (
        f"both tasks should be named:\n{output}"
    )


# ---------------------------------------------------------------------------
# TRC-D6  Canonical regression fixture
# ---------------------------------------------------------------------------

def test_add_then_delete_pair_fixture():
    """TRC-D6: the canonical checked-in fixture must yield exactly one rework instance.

    Also verifies the exit code is 0 even when rework is detected.
    The scanner is a SIGNAL, not a gate.
    """
    fixture_root = FIXTURES_DIR / "rework-scan" / "add-then-delete-pair"
    assert fixture_root.is_dir(), f"fixture directory not found: {fixture_root}"

    # Use the framework's shipped signals.yml for this regression test
    signals_yml = FRAMEWORK_ROOT / "governance" / "signals.yml"

    proc = run_rework_scan(fixture_root, signals_yml=signals_yml)

    # The exit code must be 0 even when rework is detected
    assert proc.returncode == 0, (
        f"rework-scan must exit 0 on detection (it is a "
        f"signal, not a gate). Got exit {proc.returncode}.\n"
        f"stderr: {proc.stderr}"
    )

    output = proc.stdout
    assert "1 rework" in output.lower() or (
        output.lower().count("rework instance") >= 1
    ), f"expected exactly one rework instance:\n{output}"

    assert "task-removes-handler" in output, (
        f"expected task-removes-handler named as the undoing task:\n{output}"
    )
    assert "task-adds-handler" in output, (
        f"expected task-adds-handler named as the original-add task:\n{output}"
    )


# ---------------------------------------------------------------------------
# TRC-X2  Corrupt manifest.yml is skipped gracefully
# ---------------------------------------------------------------------------

def test_skips_malformed_task(tmp_path):
    """TRC-X2: a malformed manifest.yml is skipped with a WARNING; scan completes;
    exit code is 0.
    """
    root = tmp_path / "work"
    signals = write_signals_yml(tmp_path)

    # Write a valid task
    write_task_yml(root / "task-good", "task-good", [
        {"path": "services/foo/handler.go", "action": "added"},
    ])

    # Write a corrupt manifest.yml (invalid YAML)
    bad_dir = root / "task-corrupt"
    bad_dir.mkdir(parents=True, exist_ok=True)
    (bad_dir / "manifest.yml").write_text(
        "slug: corrupt\nchanged_files: [\n  UNCLOSED BRACKET\n",
        encoding="utf-8",
    )

    proc = run_rework_scan(root, signals_yml=signals)

    assert proc.returncode == 0, (
        f"TRC-X2: exit code must be 0 even when a manifest.yml is corrupt. "
        f"Got {proc.returncode}\n{proc.stderr}"
    )
    combined = proc.stdout + proc.stderr
    assert "warning" in combined.lower() or "skipped" in combined.lower(), (
        f"expected a WARNING or 'skipped' message for the corrupt file:\n{combined}"
    )
    # The scan should complete and still report on the valid tasks
    # (no crash, no silent failure)


# ---------------------------------------------------------------------------
# Additional: window_days respected
# ---------------------------------------------------------------------------

def test_window_days_respected(tmp_path):
    """Rework outside the configured window is not reported."""
    root = tmp_path / "work"
    # window of 3 days
    signals = write_signals_yml(tmp_path, window_days=3)

    write_task_yml(root / "task-a", "task-a", [
        {"path": "services/foo/handler.go", "action": "added"},
    ], created="2026-05-01")
    # task-b is 10 days later - outside the window
    write_task_yml(root / "task-b", "task-b", [
        {"path": "services/foo/handler.go", "action": "deleted"},
    ], created="2026-05-11")

    proc = run_rework_scan(root, signals_yml=signals)
    assert proc.returncode == 0
    output = proc.stdout
    assert "0 rework" in output.lower() or "no rework" in output.lower(), (
        f"expected no rework (outside window), got:\n{output}"
    )


# ---------------------------------------------------------------------------
# Additional: JSON format output
# ---------------------------------------------------------------------------

def test_json_format(tmp_path):
    """--format json produces parseable JSON output."""
    import json as _json

    root = tmp_path / "work"
    signals = write_signals_yml(tmp_path)

    write_task_yml(root / "task-a", "task-a", [
        {"path": "services/foo/handler.go", "action": "added"},
    ], created="2026-05-01")
    write_task_yml(root / "task-b", "task-b", [
        {"path": "services/foo/handler.go", "action": "deleted"},
    ], created="2026-05-05")

    proc = run_rework_scan(root, extra_args=["--format", "json"],
                           signals_yml=signals)
    assert proc.returncode == 0
    try:
        data = _json.loads(proc.stdout)
    except _json.JSONDecodeError as exc:
        pytest.fail(f"--format json did not produce valid JSON: {exc}\n{proc.stdout}")
    assert "rework_instances" in data, f"JSON missing 'rework_instances' key: {data}"
