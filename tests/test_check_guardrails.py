"""`compass check` enforcing the default guardrails G1-G5: scenarios have
tests, suite is green, changed code traces to a scenario, gate evidence is
the right type, human approvals are present and structured, backfills are
paid.

Each test builds the smallest task.yml + evidence set that should pass or
fail a specific check, then asserts exit code and a (loose) message match.
"""
from __future__ import annotations

import json


# --- a baseline-correct task.yml the tests mutate one field at a time ------


def _correct_body(write_test_run=True):
    body = {
        "task": "baseline",
        "created": "2026-05-15",
        "readings": {
            "blast_radius": "contained",
            "terrain": "brownfield-mapped",
            "magnitude": "small",
            "intent": "delivery",
        },
        "route": "express",
        "scenarios": [
            {"id": "SCN-001", "intent": "INT-1",
             "tests": ["tests/test_x.py::test_y"]},
        ],
        "changed_files": [
            {"path": "src/x.py", "scenarios": ["SCN-001"]},
        ],
        "evidence": [],
        "gates": [
            {"id": "verify.correctness", "status": "pending"},
            {"id": "verify.governance", "status": "pending"},
            {"id": "verify.traceability", "status": "pending"},
        ],
        "backfills": [],
    }
    if write_test_run:
        body["evidence"].append({
            "id": "EV-T-SCN-001",
            "type": "test-run",
            "path": "evidence/green.json",
            "scenario": "SCN-001",
        })
    return body


def _make_green(task_dir, scenario="SCN-001"):
    """Write a fake evidence/green.json that the suite-passed check reads."""
    ev = task_dir / "evidence"
    ev.mkdir(parents=True, exist_ok=True)
    with (ev / "green.json").open("w") as fh:
        json.dump({"exit_code": 0, "passed": True, "scenario": scenario,
                   "command": "pytest", "timestamp": "2026-05-15T00:00:00+00:00"},
                  fh)


# --- G1 scenarios-have-tests + suite-passed --------------------------------


def test_check_fails_when_scenarios_have_no_tests(run_cli, make_task):
    body = _correct_body()
    body["scenarios"][0].pop("tests")
    task_dir = make_task("no-tests", body)
    _make_green(task_dir)
    r = run_cli("check", "--task", "no-tests")
    assert r.returncode != 0, r
    assert "scenarios-have-tests" in r.stdout, r


def test_check_fails_when_no_test_run_evidence(run_cli, make_task):
    body = _correct_body(write_test_run=False)
    make_task("no-green", body)
    r = run_cli("check", "--task", "no-green")
    assert r.returncode != 0, r
    assert "suite-passed" in r.stdout, r


def test_check_fails_when_test_run_path_does_not_resolve(run_cli, make_task):
    """A test-run entry pointing at a path that does not exist must fail."""
    body = _correct_body()
    # don't write the green.json file
    task_dir = make_task("dangling-path", body)
    r = run_cli("check", "--task", "dangling-path")
    assert r.returncode != 0, r
    assert "suite-passed" in r.stdout, r


def test_check_fails_when_test_run_records_failure(run_cli, make_task):
    body = _correct_body()
    task_dir = make_task("not-green", body)
    ev = task_dir / "evidence"
    ev.mkdir(parents=True, exist_ok=True)
    # exit_code != 0 means the recorded run was not green
    with (ev / "green.json").open("w") as fh:
        json.dump({"exit_code": 1, "passed": False}, fh)
    r = run_cli("check", "--task", "not-green")
    assert r.returncode != 0, r


def test_check_fails_when_test_run_bound_to_unknown_scenario(run_cli, make_task):
    """A test-run entry with `scenario: SCN-999` (not in task.yml) must
    fail — the binding has to resolve."""
    body = _correct_body()
    body["evidence"][0]["scenario"] = "SCN-999"   # not in scenarios
    task_dir = make_task("bad-binding", body)
    _make_green(task_dir, scenario="SCN-001")
    r = run_cli("check", "--task", "bad-binding")
    assert r.returncode != 0, r
    combined = r.stdout + r.stderr
    assert "SCN-999" in combined, r


# --- G3 traceability (changed_files -> scenario) ---------------------------


def test_check_fails_on_changed_file_without_scenario(run_cli, make_task):
    body = _correct_body()
    body["changed_files"] = [{"path": "src/x.py", "scenarios": []}]
    task_dir = make_task("untraced", body)
    _make_green(task_dir)
    r = run_cli("check", "--task", "untraced")
    assert r.returncode != 0, r
    assert "changed-code-traces" in r.stdout, r


def test_check_fails_on_changed_file_pointing_at_unknown_scenario(run_cli,
                                                                  make_task):
    body = _correct_body()
    body["changed_files"] = [{"path": "src/x.py",
                               "scenarios": ["SCN-DOES-NOT-EXIST"]}]
    task_dir = make_task("dangling-scn", body)
    _make_green(task_dir)
    r = run_cli("check", "--task", "dangling-scn")
    assert r.returncode != 0, r
    assert "changed-code-traces" in r.stdout, r
    assert "SCN-DOES-NOT-EXIST" in (r.stdout + r.stderr), r


def test_check_passes_when_changed_file_traces_to_real_scenario(run_cli, make_task):
    body = _correct_body()
    task_dir = make_task("traced", body)
    _make_green(task_dir)
    r = run_cli("check", "--task", "traced")
    assert r.returncode == 0, r
    assert "PASS" in r.stdout, r


# --- G3 claim traceability -------------------------------------------------


def test_check_fails_when_claim_references_unknown_scenario(run_cli, make_task):
    body = _correct_body()
    body["claims"] = [{"id": "CLM-1", "text": "fast", "scenario": "SCN-???"}]
    task_dir = make_task("bad-claim", body)
    _make_green(task_dir)
    r = run_cli("check", "--task", "bad-claim")
    assert r.returncode != 0, r
    assert "claim-traces-to-scenario" in r.stdout, r


# --- G4 gate evidence types ------------------------------------------------


def test_check_fails_on_wrong_evidence_type_for_gate(run_cli, make_task):
    """`verify.correctness` accepts only `test-run`. Clearing it with an
    `artifact` evidence id must fail."""
    body = _correct_body()
    # add an artifact-type evidence and point verify.correctness at it
    body["evidence"].append({
        "id": "EV-ART", "type": "artifact", "path": "notes.md",
    })
    body["gates"][0] = {
        "id": "verify.correctness", "status": "pass",
        "evidence": ["EV-ART"],
    }
    task_dir = make_task("wrong-type", body)
    _make_green(task_dir)
    # also create the file so path-resolution doesn't trip first
    (task_dir / "notes.md").write_text("placeholder")
    r = run_cli("check", "--task", "wrong-type")
    assert r.returncode != 0, r
    assert "gate-evidence-present" in r.stdout, r


def test_check_passes_with_correct_evidence_type(run_cli, make_task):
    body = _correct_body()
    body["gates"][0] = {
        "id": "verify.correctness", "status": "pass",
        "evidence": ["EV-T-SCN-001"],
    }
    task_dir = make_task("right-type", body)
    _make_green(task_dir)
    r = run_cli("check", "--task", "right-type")
    assert r.returncode == 0, r


def test_check_fails_on_old_inline_dict_evidence_shape(run_cli, make_task):
    """The pre-registry inline `{type, path}` shape is explicitly rejected:
    the registry is now the model."""
    body = _correct_body()
    body["gates"][0] = {
        "id": "verify.correctness", "status": "pass",
        "evidence": {"type": "test-run", "path": "evidence/green.json"},
    }
    task_dir = make_task("old-shape", body)
    _make_green(task_dir)
    r = run_cli("check", "--task", "old-shape")
    assert r.returncode != 0, r
    combined = r.stdout + r.stderr
    assert "old inline-evidence" in combined or "inline-evidence" in combined, r


def test_check_fails_on_evidence_id_not_in_registry(run_cli, make_task):
    """A gate referencing an evidence id that the registry does not contain."""
    body = _correct_body()
    body["gates"][0] = {
        "id": "verify.correctness", "status": "pass",
        "evidence": ["EV-NOPE"],
    }
    task_dir = make_task("dangling-ev", body)
    _make_green(task_dir)
    r = run_cli("check", "--task", "dangling-ev")
    assert r.returncode != 0, r
    combined = r.stdout + r.stderr
    assert "EV-NOPE" in combined, r


# --- G5 human approvals ----------------------------------------------------


def test_check_fails_on_g5_touched_task_with_no_approval(run_cli, make_task):
    """Touching auth without a human-approval evidence entry => check fails
    on the G5 check."""
    body = _correct_body()
    body["readings"]["touches"] = ["auth"]
    body["route"] = "expedition"
    task_dir = make_task("g5-no-approval", body)
    _make_green(task_dir)
    r = run_cli("check", "--task", "g5-no-approval")
    assert r.returncode != 0, r
    assert "human-approval-present" in r.stdout, r


def test_check_fails_on_g5_approval_missing_fields(run_cli, make_task):
    """A human-approval entry without the required structured fields must
    fail — partial approvals are worse than missing ones."""
    body = _correct_body()
    body["readings"]["touches"] = ["auth"]
    body["route"] = "expedition"
    body["evidence"].append({
        "id": "EV-APP", "type": "human-approval",
        "decision": "approved",
        # missing approver, role, scope, timestamp
    })
    task_dir = make_task("g5-partial-approval", body)
    _make_green(task_dir)
    r = run_cli("check", "--task", "g5-partial-approval")
    assert r.returncode != 0, r
    combined = r.stdout + r.stderr
    assert "missing required" in combined or "approver" in combined, r


def test_check_passes_on_complete_g5_approval(run_cli, make_task):
    body = _correct_body()
    body["readings"]["touches"] = ["auth"]
    body["route"] = "expedition"
    body["evidence"].append({
        "id": "EV-APP", "type": "human-approval",
        "approver": "ada@example.com",
        "role": "engineering-lead",
        "scope": "auth-related migration",
        "decision": "approved",
        "timestamp": "2026-05-15T10:00:00Z",
    })
    task_dir = make_task("g5-ok", body)
    _make_green(task_dir)
    r = run_cli("check", "--task", "g5-ok")
    # the approval check should pass — overall result depends on the other
    # checks all passing (they do, in this baseline task), so we just check
    # the approval check passes its own line.
    assert "PASS human-approval-present" in r.stdout, r


# --- backfills (cross-cutting) ---------------------------------------------


def test_check_fails_on_unpaid_backfill(run_cli, make_task):
    body = _correct_body()
    body["backfills"] = [{"id": "BF-1", "description": "promote repro test",
                           "status": "owed"}]
    task_dir = make_task("owed-bf", body)
    _make_green(task_dir)
    r = run_cli("check", "--task", "owed-bf")
    assert r.returncode != 0, r
    assert "backfills-paid" in r.stdout, r
    assert "BF-1" in (r.stdout + r.stderr), r


def test_check_passes_with_paid_backfill(run_cli, make_task):
    body = _correct_body()
    body["backfills"] = [{"id": "BF-1", "description": "promote repro test",
                           "status": "paid"}]
    task_dir = make_task("paid-bf", body)
    _make_green(task_dir)
    r = run_cli("check", "--task", "paid-bf")
    assert r.returncode == 0, r


# --- scenario-has-id-and-intent --------------------------------------------


def test_check_fails_when_scenario_has_no_intent(run_cli, make_task):
    body = _correct_body()
    body["scenarios"][0].pop("intent")
    task_dir = make_task("no-intent", body)
    _make_green(task_dir)
    r = run_cli("check", "--task", "no-intent")
    assert r.returncode != 0, r
    assert "scenario-has-id-and-intent" in r.stdout, r
