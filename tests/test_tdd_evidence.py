"""tdd-red / tdd-green: scenario binding, registry upsert, and the honesty
constraints (red is only recorded after a real failure; green only after a
real pass)."""
from __future__ import annotations

import json
import shutil
import sys

import pytest
import yaml

_BASH = shutil.which("bash")


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


# ===========================================================================
# R2 — exit-code masking in piped test commands (TRC-R2-1 … TRC-R2-5)
# The masking path is caller-introduced: `bash -c '... | tail'` makes the
# shell return the final stage's exit code (tail = 0), masking an inner
# failure. The fix injects `set -o pipefail` into bash/zsh wrappers, warns on
# a pager/filter final stage, and cross-checks output for a fail-token.
# ===========================================================================


def _r2_body():
    body = _baseline_body()
    body["scenarios"] = [{"id": "SCN-001", "intent": "INT-1",
                          "tests": ["tests/test_x.py::test_y"]}]
    return body


def test_pipe_masking_records_false_green_baseline(run_cli, make_task):
    """TRC-R2-1 (distillation→regression guard): a failing test piped to `tail`
    must NOT be recordable as a green. The masked inner failure is caught."""
    if not _BASH:
        pytest.skip("bash not available")
    task_dir = make_task("r2-mask", _r2_body())
    (task_dir / ".red").write_text("")
    r = run_cli("tdd-green", "--task", "r2-mask", "--scenario", "SCN-001",
                "--", "bash", "-c", "exit 1 | tail -1")
    assert r.returncode != 0, r              # refused — not a false green
    assert (task_dir / ".red").exists(), r   # marker NOT cleared


def test_pipefail_propagates_masked_failure(run_cli, make_task):
    """TRC-R2-2: with pipefail injected into the shell wrapper, the mid-pipeline
    failure propagates so tdd-green refuses and records no passing green."""
    if not _BASH:
        pytest.skip("bash not available")
    task_dir = make_task("r2-pf", _r2_body())
    (task_dir / ".red").write_text("")
    r = run_cli("tdd-green", "--task", "r2-pf", "--scenario", "SCN-001",
                "--", "bash", "-c", "exit 1 | tail -1")
    assert r.returncode != 0, r
    assert "FAILED" in (r.stdout + r.stderr), r
    green = task_dir / "evidence" / "green.json"
    if green.exists():
        assert json.loads(green.read_text()).get("passed") is not True, r


def test_direct_argv_green_unchanged(run_cli, make_task):
    """TRC-R2-3: an ordinary direct-argv passing command still records green
    (the hardening must not touch the default shell=False path)."""
    task_dir = make_task("r2-direct", _r2_body())
    (task_dir / ".red").write_text("")
    r = run_cli("tdd-green", "--task", "r2-direct", "--scenario", "SCN-001",
                "--", sys.executable, "-c", "import sys; sys.exit(0)")
    assert r.returncode == 0, r
    green = json.loads((task_dir / "evidence" / "green.json").read_text())
    assert green["passed"] is True, r
    assert not (task_dir / ".red").exists(), r


def test_pipe_filter_final_stage_warns(run_cli, make_task):
    """TRC-R2-4: a top-level pipe ending in a pager/filter (tail) is flagged,
    even when the command happens to pass."""
    if not _BASH:
        pytest.skip("bash not available")
    task_dir = make_task("r2-warn", _r2_body())
    (task_dir / ".red").write_text("")
    r = run_cli("tdd-green", "--task", "r2-warn", "--scenario", "SCN-001",
                "--", "bash", "-c", "echo hi | tail")
    combined = (r.stdout + r.stderr).lower()
    assert "pipe" in combined and "tail" in combined, r


def test_output_token_crosscheck_on_known_runner(run_cli, make_task):
    """TRC-R2-5: a zero exit whose output carries a runner fail-token does not
    silently record a clean green."""
    if not _BASH:
        pytest.skip("bash not available")
    task_dir = make_task("r2-token", _r2_body())
    (task_dir / ".red").write_text("")
    r = run_cli("tdd-green", "--task", "r2-token", "--scenario", "SCN-001",
                "--", "bash", "-c", "echo '1 failed in 0.10s'; exit 0")
    assert r.returncode != 0, r              # not a silent clean green
    assert "fail" in (r.stdout + r.stderr).lower(), r
