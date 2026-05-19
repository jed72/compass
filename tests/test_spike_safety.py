"""Spike mechanical safety — guarantee 4 of the safety contract.

On a Spike route, the delivery guardrails do not apply; instead the spike
guardrails do. The CLI must enforce:
  - a spike-conclusion evidence entry exists, with a recorded decision
  - if the decision is graduate-to-delivery, `next_task` links the new task
  - `changed_files` is empty (a Spike ships nothing)
"""
from __future__ import annotations


def _spike_body():
    return {
        "task": "spike-x",
        "created": "2026-05-15",
        "readings": {
            "blast_radius": "contained",
            "terrain": "brownfield-mapped",
            "magnitude": "small",
            "intent": "exploration",
        },
        "route": "spike",
        "evidence": [],
        "changed_files": [],
        "gates": [{"id": "spike.conclude", "status": "pending"}],
    }


def test_spike_without_conclusion_fails(run_cli, make_task):
    body = _spike_body()
    make_task("spike-no-conc", body)
    r = run_cli("check", "--task", "spike-no-conc")
    assert r.returncode != 0, r
    assert "spike-conclusion-present" in r.stdout, r


def test_spike_graduate_without_next_task_fails(run_cli, make_task):
    body = _spike_body()
    body["evidence"].append({
        "id": "EV-CONC", "type": "spike-conclusion",
        "decision": "graduate-to-delivery",
        # missing next_task
    })
    make_task("spike-no-next", body)
    r = run_cli("check", "--task", "spike-no-next")
    assert r.returncode != 0, r
    combined = r.stdout + r.stderr
    assert "next_task" in combined, r


def test_spike_with_production_changes_fails(run_cli, make_task):
    body = _spike_body()
    body["evidence"].append({
        "id": "EV-CONC", "type": "spike-conclusion",
        "decision": "discard",
    })
    body["changed_files"] = [{"path": "src/feature.py", "scenarios": []}]
    make_task("spike-with-changes", body)
    r = run_cli("check", "--task", "spike-with-changes")
    assert r.returncode != 0, r
    assert "spike-no-production-changes" in r.stdout, r


def test_spike_with_invalid_decision_fails(run_cli, make_task):
    body = _spike_body()
    body["evidence"].append({
        "id": "EV-CONC", "type": "spike-conclusion",
        "decision": "go-for-it",
    })
    make_task("spike-bad-decision", body)
    r = run_cli("check", "--task", "spike-bad-decision")
    assert r.returncode != 0, r
    combined = r.stdout + r.stderr
    assert "go-for-it" in combined or "decision" in combined, r


def test_spike_discard_decision_passes(run_cli, make_task):
    body = _spike_body()
    body["evidence"].append({
        "id": "EV-CONC", "type": "spike-conclusion",
        "decision": "discard",
    })
    make_task("spike-discard", body)
    r = run_cli("check", "--task", "spike-discard")
    assert r.returncode == 0, r
    assert "PASS" in r.stdout, r


def test_spike_graduate_with_next_task_passes(run_cli, make_task):
    body = _spike_body()
    body["evidence"].append({
        "id": "EV-CONC", "type": "spike-conclusion",
        "decision": "graduate-to-delivery",
        "next_task": ".compass/work/build-the-thing/",
    })
    make_task("spike-graduate", body)
    r = run_cli("check", "--task", "spike-graduate")
    assert r.returncode == 0, r
    assert "PASS" in r.stdout, r


def test_spike_check_does_not_run_delivery_guardrails(run_cli, make_task):
    """A Spike route shouldn't be hit by G1-G5 (no scenarios needed, no
    test-run evidence, etc.) — the check output is the spike guardrails."""
    body = _spike_body()
    body["evidence"].append({
        "id": "EV-CONC", "type": "spike-conclusion",
        "decision": "defer",
    })
    make_task("spike-only", body)
    r = run_cli("check", "--task", "spike-only")
    assert r.returncode == 0, r
    # the output should mention the spike route header
    assert "spike" in r.stdout.lower(), r
    # delivery checks should NOT appear in a Spike check output
    assert "scenarios-have-tests" not in r.stdout, r
    assert "suite-passed" not in r.stdout, r
