"""An acceptance declared after the work does not stand in for a red.

`suite-passed` accepts an acceptance record in place of a red, for work with no
natural failing test. `compass acceptance start` exists to declare that before
the change. Nothing checked the order, so declaring and recording an acceptance
after the work was done cleared the rule. The record now carries the time it
was declared, and `suite-passed` counts it only when that time is earlier than
the issue's first green.

Scenario ids: ADW-1 to ADW-4, in the delivery approach of issue
`acceptance-declared-after-the-work`.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLI = ROOT / "cli" / "compass"
sys.path.insert(0, str(ROOT / "cli"))

from compass_pkg.checks import _check_suite_passed  # noqa: E402

EARLY = "2026-10-01T09:00:00+00:00"
LATE = "2026-10-01T10:00:00+00:00"


def _issue(tmp_path, *, green_at, declared_at):
    task_dir = tmp_path / ".compass" / "work" / "sample"
    ev = task_dir / "evidence"
    ev.mkdir(parents=True)
    (ev / "green.json").write_text(json.dumps(
        {"exit_code": 0, "passed": True, "timestamp": green_at}))
    record = {"kind": "validation", "exit_code": 0, "passed": True,
              "timestamp": LATE}
    if declared_at is not None:
        record["declared_at"] = declared_at
    (ev / "acceptance.json").write_text(json.dumps(record))
    task = {"created": "2026-10-01", "scenarios": [{"id": "S-1"}],
            "evidence": [
                {"id": "EV-T", "type": "test-run", "path": "evidence/green.json"},
                {"id": "EV-A", "type": "test-run",
                 "path": "evidence/acceptance.json"}]}
    return task, str(task_dir)


def test_adw_1_an_acceptance_declared_after_the_first_green_does_not_count(
        tmp_path):
    task, task_dir = _issue(tmp_path, green_at=EARLY, declared_at=LATE)
    ok, why = _check_suite_passed(task, task_dir)
    assert ok is False, why
    assert "declared" in why and "after the first green" in why


def test_adw_2_an_acceptance_declared_before_any_green_counts(tmp_path):
    task, task_dir = _issue(tmp_path, green_at=LATE, declared_at=EARLY)
    ok, why = _check_suite_passed(task, task_dir)
    assert ok is True, why


def test_adw_3_an_acceptance_record_with_no_declared_at_counts(tmp_path):
    task, task_dir = _issue(tmp_path, green_at=EARLY, declared_at=None)
    ok, why = _check_suite_passed(task, task_dir)
    assert ok is True, why


def test_adw_4_acceptance_record_carries_declared_at(tmp_path):
    task_dir = tmp_path / ".compass" / "work" / "sample"
    task_dir.mkdir(parents=True)
    (task_dir / "manifest.yml").write_text(
        "schema_version: '2.0'\nissue: sample\ncreated: '2026-10-01'\n"
        "status: active\nevidence: []\n")
    run = lambda *a: subprocess.run(  # noqa: E731
        [sys.executable, str(CLI), *a], cwd=tmp_path,
        capture_output=True, text=True,
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(tmp_path)})
    start = run("acceptance", "start", "--issue", "sample",
                "--kind", "validation", "--",
                sys.executable, "-c", "pass")
    assert start.returncode == 0, start.stderr
    record = run("acceptance", "record", "--issue", "sample", "--",
                 sys.executable, "-c", "pass")
    assert record.returncode == 0, record.stderr
    baseline = json.loads((task_dir / "evidence" / "acceptance-baseline.json")
                          .read_text())
    written = json.loads((task_dir / "evidence" / "acceptance.json").read_text())
    assert written.get("declared_at") == baseline["declared_at"]
