"""A backdated `created:` date does not exempt recorded work from red-first.

`suite-passed` needs a red record, or an acceptance record, on an issue that
declares scenarios and falls under the red-first rule. The rule first keyed on
the manifest's `created:` date alone, which anyone can edit. It now also
applies when any of the issue's evidence records is dated on or after the
cutoff. The CLI writes each record with the time of the run, so a backdated
`created:` escapes nothing once work is recorded.

Scenario ids: CDB-1 and CDB-2, in the delivery approach of issue
`created-date-can-be-backdated`.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "cli"))

from compass_pkg.checks import _check_suite_passed  # noqa: E402

BEFORE_DAY = "2026-01-01"
AFTER_STAMP = "2026-10-01T09:00:00+00:00"
BEFORE_STAMP = "2026-01-02T09:00:00+00:00"


def _issue(tmp_path, green_stamp):
    task_dir = tmp_path / ".compass" / "work" / "sample"
    (task_dir / "evidence").mkdir(parents=True)
    (task_dir / "evidence" / "green.json").write_text(json.dumps(
        {"exit_code": 0, "passed": True, "timestamp": green_stamp}))
    task = {"created": BEFORE_DAY, "scenarios": [{"id": "S-1"}],
            "evidence": [{"id": "EV-T", "type": "test-run",
                          "path": "evidence/green.json"}]}
    return task, str(task_dir)


def test_cdb_1_a_backdated_issue_with_later_evidence_gets_the_rule(tmp_path):
    task, task_dir = _issue(tmp_path, AFTER_STAMP)
    ok, why = _check_suite_passed(task, task_dir)
    assert ok is False, why
    assert "no red is on record" in why
    assert "evidence/green.json" in why and "2026-10-01" in why


def test_cdb_2_an_issue_created_and_worked_before_the_cutoff_keeps_its_result(
        tmp_path):
    task, task_dir = _issue(tmp_path, BEFORE_STAMP)
    ok, why = _check_suite_passed(task, task_dir)
    assert ok is True, why
