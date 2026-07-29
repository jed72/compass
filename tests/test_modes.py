"""Adoption modes: enforced blocks on failures (exit 1), advisory reports
the same failures but exits 0. The banner makes the mode visible so a run
is never mistaken."""
from __future__ import annotations

import json


def _failing_task_body():
    """A task with a missing test-run binding - fails the suite-passed check."""
    return {
        "task": "fail-me",
        "created": "2026-05-15",
        "readings": {
            "blast_radius": "contained",
            "terrain": "brownfield-mapped",
            "magnitude": "small",
            "intent": "delivery",
        },
        "route": "express",
        "scenarios": [{"id": "SCN-001", "intent": "INT-1",
                       "tests": ["tests/test_x.py::test_y"]}],
        "changed_files": [{"path": "src/x.py", "scenarios": ["SCN-001"]}],
        "evidence": [],   # no test-run => suite-passed fails
        "gates": [{"id": "verify.correctness", "status": "pending"}],
    }


def _set_mode(project, mode):
    path = project / ".compass" / "config.yml"
    path.write_text(f"version: 1.0.0\nmode: {mode}\n")


def test_enforced_mode_returns_nonzero_on_failure(run_cli, project, make_task):
    _set_mode(project, "enforced")
    make_task("fail-1", _failing_task_body())
    r = run_cli("check", "--task", "fail-1")
    assert r.returncode != 0, r
    assert "[mode: enforced]" in r.stdout, r
    assert "FAIL" in r.stdout, r


def test_advisory_mode_returns_zero_on_failure(run_cli, project, make_task):
    _set_mode(project, "advisory")
    make_task("fail-1", _failing_task_body())
    r = run_cli("check", "--task", "fail-1")
    assert r.returncode == 0, f"advisory mode must exit 0 even on failure:\n{r}"
    # the failure is still reported
    assert "FAIL" in r.stdout, r
    assert "[mode: advisory]" in r.stdout, r


def test_advisory_banner_is_visible(run_cli, project, make_task):
    """Even on a PASS, the advisory banner must be printed so nobody mistakes
    an advisory run for enforced."""
    _set_mode(project, "advisory")
    body = _failing_task_body()
    body["evidence"] = [{"id": "EV-T", "type": "test-run",
                         "path": "evidence/green.json", "scenario": "SCN-001"}]
    task_dir = make_task("ok", body)
    (task_dir / "evidence").mkdir(exist_ok=True)
    (task_dir / "evidence" / "green.json").write_text(
        json.dumps({"exit_code": 0, "passed": True}))
    r = run_cli("check", "--task", "ok")
    assert "[mode: advisory]" in r.stdout, r


def test_ci_respects_advisory_mode(run_cli, project, make_task):
    """compass ci should also exit 0 in advisory mode even when checks fail."""
    _set_mode(project, "advisory")
    make_task("fail-1", _failing_task_body())
    r = run_cli("ci")
    assert r.returncode == 0, r
    assert "[mode: advisory]" in r.stdout, r


def test_same_task_different_exit_under_two_modes(run_cli, project, make_task):
    """Same failing task, same machine, different exit code per mode - that
    is the entire point of adoption-mode."""
    make_task("twin", _failing_task_body())

    _set_mode(project, "enforced")
    r1 = run_cli("check", "--task", "twin")

    _set_mode(project, "advisory")
    r2 = run_cli("check", "--task", "twin")

    assert r1.returncode != 0, r1
    assert r2.returncode == 0, r2
    # both produce a FAIL message - the difference is the exit code
    assert "FAIL" in r1.stdout
    assert "FAIL" in r2.stdout
