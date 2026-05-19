"""tdd-red / tdd-green: scenario binding, registry upsert, and the honesty
constraints (red is only recorded after a real failure; green only after a
real pass)."""
from __future__ import annotations

import sys

import yaml


def _baseline_body():
    return {
        "task": "tdd-task",
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
        "evidence": [],
    }


# --- scenario binding rejects bogus ids ------------------------------------


def test_tdd_red_rejects_unknown_scenario(run_cli, make_task):
    make_task("tdd-bind", _baseline_body())
    r = run_cli("tdd-red", "--task", "tdd-bind",
                "--scenario", "SCN-BOGUS",
                "--", "false")    # would have failed anyway
    assert r.returncode != 0, r
    combined = r.stdout + r.stderr
    assert "SCN-BOGUS" in combined, r


def test_tdd_green_rejects_unknown_scenario(run_cli, make_task):
    make_task("tdd-bind-g", _baseline_body())
    r = run_cli("tdd-green", "--task", "tdd-bind-g",
                "--scenario", "SCN-BOGUS",
                "--", sys.executable, "-c", "import sys; sys.exit(0)")
    assert r.returncode != 0, r
    combined = r.stdout + r.stderr
    assert "SCN-BOGUS" in combined, r


# --- tdd-red honesty: a passing command cannot be recorded as red ---------


def test_tdd_red_refuses_a_passing_command(run_cli, make_task):
    make_task("tdd-honest-red", _baseline_body())
    r = run_cli("tdd-red", "--task", "tdd-honest-red",
                "--scenario", "SCN-001",
                "--", sys.executable, "-c", "import sys; sys.exit(0)")
    assert r.returncode != 0, r
    combined = r.stdout + r.stderr
    assert "PASSED" in combined or "red-before-green" in combined.lower(), r


def test_tdd_red_records_red_on_real_failure(run_cli, make_task, project):
    task_dir = make_task("tdd-real-red", _baseline_body())
    r = run_cli("tdd-red", "--task", "tdd-real-red",
                "--scenario", "SCN-001",
                "--", sys.executable, "-c", "import sys; sys.exit(2)")
    assert r.returncode == 0, r
    # evidence/red.json + the .red marker on disk
    assert (task_dir / "evidence" / "red.json").is_file()
    assert (task_dir / ".red").is_file()


# --- tdd-green honesty: a failing command cannot be recorded as green -----


def test_tdd_green_refuses_a_failing_command(run_cli, make_task):
    make_task("tdd-honest-green", _baseline_body())
    r = run_cli("tdd-green", "--task", "tdd-honest-green",
                "--scenario", "SCN-001",
                "--", sys.executable, "-c", "import sys; sys.exit(1)")
    assert r.returncode != 0, r
    combined = r.stdout + r.stderr
    assert "FAILED" in combined or "not green" in combined.lower(), r


# --- tdd-green upserts a test-run entry in task.yml's evidence registry ----


def test_tdd_green_upserts_test_run_in_registry(run_cli, make_task, project):
    task_dir = make_task("tdd-upsert", _baseline_body())
    r = run_cli("tdd-green", "--task", "tdd-upsert",
                "--scenario", "SCN-001",
                "--", sys.executable, "-c", "import sys; sys.exit(0)")
    assert r.returncode == 0, r
    task = yaml.safe_load((task_dir / "task.yml").read_text())
    runs = [e for e in task["evidence"] if e["type"] == "test-run"]
    assert len(runs) == 1, f"expected one test-run entry, got {runs}"
    assert runs[0]["scenario"] == "SCN-001"
    assert runs[0]["path"].endswith(".json")


def test_tdd_green_upsert_is_idempotent_for_same_scenario(run_cli, make_task,
                                                          project):
    """Running tdd-green twice for the same scenario must UPDATE the
    existing entry, not append a new one."""
    task_dir = make_task("tdd-idem", _baseline_body())
    for _ in range(2):
        r = run_cli("tdd-green", "--task", "tdd-idem",
                    "--scenario", "SCN-001",
                    "--", sys.executable, "-c", "import sys; sys.exit(0)")
        assert r.returncode == 0, r
    task = yaml.safe_load((task_dir / "task.yml").read_text())
    runs = [e for e in task["evidence"] if e["type"] == "test-run"]
    assert len(runs) == 1, f"expected one test-run entry after two runs, got {runs}"


def test_tdd_green_clears_red_marker(run_cli, make_task, project):
    task_dir = make_task("tdd-clear", _baseline_body())
    # leave a stale .red on disk first
    (task_dir / ".red").write_text("")
    r = run_cli("tdd-green", "--task", "tdd-clear",
                "--scenario", "SCN-001",
                "--", sys.executable, "-c", "import sys; sys.exit(0)")
    assert r.returncode == 0, r
    assert not (task_dir / ".red").exists(), ".red marker should have been cleared"


# --- the check side: a bound test-run that does not resolve fails ---------


def test_check_suite_passed_fails_on_unresolvable_binding(run_cli, make_task):
    """A test-run entry whose `scenario` does not exist in scenarios must
    fail `_check_suite_passed`."""
    body = _baseline_body()
    body["evidence"].append({
        "id": "EV-T-X", "type": "test-run",
        "path": "evidence/green.json",
        "scenario": "SCN-NEVER",
    })
    body["scenarios"] = [{"id": "SCN-001", "intent": "INT-1",
                          "tests": ["tests/test_x.py::test_y"]}]
    body["changed_files"] = []
    body["gates"] = [{"id": "verify.correctness", "status": "pending"}]
    task_dir = make_task("bad-bind", body)
    ev = task_dir / "evidence"
    ev.mkdir(exist_ok=True)
    (ev / "green.json").write_text('{"exit_code": 0, "passed": true}')
    r = run_cli("check", "--task", "bad-bind")
    assert r.returncode != 0, r
    assert "SCN-NEVER" in (r.stdout + r.stderr), r
