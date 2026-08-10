"""TRC-F4 - an issue already in flight survives the zero-friction-install
upgrade unchanged.

`compass check` is read-only over an issue directory: nothing in
`cli/compass_pkg/check_cmd.py` opens a file for writing. That single fact is
what makes "nothing changes for anyone mid-issue" checkable rather than an
instruction to remember - a half-finished issue's `.red` marker, its recorded
evidence, and `compass check`'s gate-by-gate verdict on it are exactly what
they were, because the command that reads them never touches the disk.

This is a characterisation test: there is no natural failing state to drive
it red, so it goes through `compass acceptance start --kind refactor` rather
than a manufactured one (see devlog, U0). It is declared before the bundled
copy and its resolver land, and recorded after - across a tree that genuinely
changed - so the "before" and "after" are two different points in this
issue's history, not one run compared with itself.
"""
from __future__ import annotations

import hashlib
import json


def _tree_fingerprint(task_dir):
    """A stable fingerprint of every file's path + bytes under `task_dir`."""
    h = hashlib.sha256()
    for path in sorted(task_dir.rglob("*")):
        if path.is_file():
            h.update(str(path.relative_to(task_dir)).encode("utf-8"))
            h.update(path.read_bytes())
    return h.hexdigest()


def _in_flight_body():
    return {
        "task": "in-flight-issue",
        "created": "2026-05-15",
        "assessment": {
            "risk": "contained",
            "familiarity": "brownfield-mapped",
            "size": "small",
            "goal": "delivery",
        },
        "delivery_approach": "express",
        "scenarios": [
            {"id": "SCN-001", "intent": "INT-1",
             "tests": ["tests/test_x.py::test_y"]},
        ],
        "changed_files": [
            {"path": "src/x.py", "scenarios": ["SCN-001"]},
        ],
        "evidence": [
            {"id": "EV-T-SCN-001", "type": "test-run",
             "path": "evidence/red.json", "scenario": "SCN-001"},
        ],
        "gates": [
            {"id": "verify.correctness", "status": "pending"},
            {"id": "verify.governance", "status": "pending"},
            {"id": "verify.traceability", "status": "pending"},
        ],
        "follow_ups": [],
    }


def test_an_issue_in_flight_survives_the_upgrade_unchanged(make_task, run_cli):
    """A mid-flight issue - `.red` set, one red recorded, three gates
    pending - gets the same `compass check` verdict, gate by gate, and not
    one byte in its directory moves, whether the CLI underneath it is
    yesterday's or this issue's."""
    task_dir = make_task("in-flight-issue", _in_flight_body())

    # A real red on record: the marker plus the evidence it names.
    (task_dir / ".red").write_text("red\n", encoding="utf-8")
    ev_dir = task_dir / "evidence"
    ev_dir.mkdir(exist_ok=True)
    with (ev_dir / "red.json").open("w", encoding="utf-8") as fh:
        json.dump({
            "command": "pytest tests/test_x.py::test_y",
            "scenario": "SCN-001",
            "exit_code": 1,
            "passed": False,
            "timestamp": "2026-05-15T00:00:00+00:00",
        }, fh)

    before_fingerprint = _tree_fingerprint(task_dir)
    before_red = (task_dir / ".red").read_bytes()

    result = run_cli("check", "--issue", "in-flight-issue")

    after_fingerprint = _tree_fingerprint(task_dir)
    after_red = (task_dir / ".red").read_bytes()

    # No migration step, none prompted for: `compass check` needs no `--apply`,
    # no flag naming a schema version, nothing beyond the verb itself.
    # The recorded red is not a green, so G1 (tested before it lands) is not
    # clear yet - the issue is genuinely mid-flight, and the verdict says so.
    assert result.returncode != 0, result
    assert "G1" in result.stdout, result
    assert "suite-passed" in result.stdout, result
    assert "compass check: FAIL" in result.stdout, result

    # `.red` keeps its meaning - untouched, byte for byte.
    assert after_red == before_red == b"red\n"

    # No file in the issue directory was rewritten - not even a byte moved
    # anywhere under it, which is what "compass check is read-only" means in
    # a form a test can hold the build to.
    assert after_fingerprint == before_fingerprint
