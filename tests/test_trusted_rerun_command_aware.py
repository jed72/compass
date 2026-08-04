"""A different test command is a different assertion, not a rerun-to-green.

`compass tdd-green` flags `rerun_without_change` when the source tree hash is
unchanged since the previous green. The flag exists to catch running the same
failing test again until it happens to pass - flaky-test laundering, which
`compass check`'s no-trusted-rerun check then refuses.

It hashed only the source, not the command, so the ordinary Verify sequence -
run the unit tests, then run the full suite, with no code change in between -
was recorded as a rerun-to-green and failed the check. That punishes the exact
behaviour Verify asks for.

Scenario: .compass/work/release-blockers-2026-08/spec.feature.md (SCN-17).
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
CLI = ROOT / "cli" / "compass"

TASK_YML = yaml.safe_dump({
    "schema_version": "1.1", "task": "t", "created": "2026-08-04",
    "status": "active",
    "readings": {"blast_radius": "contained", "terrain": "greenfield",
                 "magnitude": "small", "intent": "delivery", "urgency": "none",
                 "role": "engineer", "touches": []},
    "route": "standard", "topology": "solo", "fired_guardrails": [],
    "phases": {}, "evidence": [], "gates": [], "scenarios": [],
    "changed_files": [], "claims": [], "backfills": [], "reframes": [],
    "friction": [],
}, sort_keys=False)


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "proj"
    task_dir = root / ".compass" / "work" / "t"
    task_dir.mkdir(parents=True)
    (root / ".compass" / "config.yml").write_text("version: 1.0.0\nmode: enforced\n")
    (root / ".compass" / "current-task").write_text("t\n")
    (task_dir / "task.yml").write_text(TASK_YML)
    (task_dir / "route.md").write_text("# Route\n")
    return root, task_dir


def _green(root: pathlib.Path, *cmd) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CLI), "tdd-green", "--", *cmd],
        cwd=str(root), capture_output=True, text=True, timeout=60,
    )


def _record(task_dir: pathlib.Path) -> dict:
    return json.loads((task_dir / "evidence" / "green.json").read_text())


def test_a_different_command_is_not_a_rerun_without_change(project):
    """The Verify sequence - narrow suite, then full suite - must stay clean."""
    root, task_dir = project
    _green(root, sys.executable, "-c", "print('unit tests')")
    _green(root, sys.executable, "-c", "print('the full suite')")

    record = _record(task_dir)
    assert record.get("rerun_without_change") is not True, (
        "running a different test command with no source change was recorded as "
        f"a rerun-to-green:\n{record}"
    )


def test_the_same_command_again_is_still_a_rerun_without_change(project):
    """The flag must keep catching what it exists for: the same assertion run
    again, unchanged, until it goes green."""
    root, task_dir = project
    _green(root, sys.executable, "-c", "print('same')")
    _green(root, sys.executable, "-c", "print('same')")

    record = _record(task_dir)
    assert record.get("rerun_without_change") is True, (
        f"re-running the identical command was not flagged:\n{record}"
    )
    assert record.get("attempts", 0) > 1, record
