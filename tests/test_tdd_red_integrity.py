"""`compass tdd-red` must only record a red for a genuine test failure.

The `.red` marker is what `hooks/pre-tool.sh` reads to permit a code edit, and
the hook documents it as meaning "a real, observed failure is on record, not
someone touched a file". A `tdd-red` that accepts any non-zero exit cannot keep
that promise: a test runner exits non-zero for reasons that are not failures.

pytest's exit codes:
    0  all tests passed
    1  tests were collected and run, and some FAILED   <- the only real red
    2  interrupted
    3  internal error
    4  usage error (a bad argument)                    <- no test ran
    5  no tests were collected                         <- no test ran

Exits 4 and 5 are what a *misconfigured command* produces, which is precisely
when a false red is most likely and most damaging. This was found in the field:
`_neutralise_coverage` appends `--cov-fail-under=0` to any recognised pytest
command so a project coverage floor cannot refuse a passing targeted test, but
that flag only exists when pytest-cov is loaded. On a project that disables
pytest plugin autoload - as this repository does everywhere by design - pytest
rejected the argument, exited 4, and `tdd-red` recorded it as a failing test.

Spec: .compass/work/executable-bdd-and-richer-plans/acceptance-criteria.md (TRC-G1..G3).
"""
from __future__ import annotations

import json


TASK_BODY = {
    "assessment": {"risk": "contained", "familiarity": "greenfield",
                 "size": "small", "intent": "delivery",
                 "role": "engineer", "labels": []},
    "scenarios": [],
}


def _markers(task_dir):
    return (task_dir / ".red").exists(), (task_dir / "evidence" / "red.json").exists()


# ---------------------------------------------------------------------------
# TRC-G1 - a command that fails to RUN is not a red
# ---------------------------------------------------------------------------

def test_trc_g1_usage_error_is_not_a_red(make_task, run_cli, project):
    task_dir = make_task("g1", TASK_BODY)
    (project / "tests_demo").mkdir()
    (project / "tests_demo" / "test_ok.py").write_text(
        "def test_ok():\n    assert True\n", encoding="utf-8")

    # --definitely-not-a-pytest-flag makes pytest exit 4 (usage error).
    result = run_cli(
        "tdd-red", "--issue", "g1", "--",
        "python3", "-m", "pytest", "tests_demo", "-q",
        "--definitely-not-a-pytest-flag",
        timeout=60,
    )

    assert result.returncode != 0, (
        "tdd-red accepted a command that never ran a test:\n%r" % result)
    combined = result.combined.lower()
    assert "did not run" in combined or "could not run" in combined, (
        "the message must distinguish 'the command did not run' from 'the test "
        "failed':\n%r" % result)

    marker, evidence = _markers(task_dir)
    assert not marker, "a .red marker was written for a command that never ran"
    assert not evidence, "red.json was written for a command that never ran"


# ---------------------------------------------------------------------------
# TRC-G2 - a run that collects no tests is not a red
# ---------------------------------------------------------------------------

def test_trc_g2_no_tests_collected_is_not_a_red(make_task, run_cli, project):
    task_dir = make_task("g2", TASK_BODY)
    (project / "tests_empty").mkdir()          # no test files at all

    result = run_cli(
        "tdd-red", "--issue", "g2", "--",
        "python3", "-m", "pytest", "tests_empty", "-q",
        timeout=60,
    )

    assert result.returncode != 0, (
        "tdd-red accepted a run that collected no tests:\n%r" % result)
    assert "collect" in result.combined.lower(), (
        "the message must say no test was collected:\n%r" % result)

    marker, evidence = _markers(task_dir)
    assert not marker, "a .red marker was written when no test was collected"
    assert not evidence, "red.json was written when no test was collected"


# ---------------------------------------------------------------------------
# TRC-G3 - a genuinely failing test IS still a red
# ---------------------------------------------------------------------------

def test_trc_g3_real_failure_is_still_a_red(make_task, run_cli, project):
    task_dir = make_task("g3", TASK_BODY)
    (project / "tests_fail").mkdir()
    (project / "tests_fail" / "test_bad.py").write_text(
        "def test_bad():\n    assert 1 == 2\n", encoding="utf-8")

    # Autoload disabled: pytest-cov is not loadable here, which is the exact
    # condition that produced the false red in the field.
    result = run_cli(
        "tdd-red", "--issue", "g3", "--",
        "python3", "-m", "pytest", "tests_fail", "-q",
        extra_env={"PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"},
        timeout=60,
    )

    assert result.returncode == 0, (
        "a genuinely failing test was not recorded as a red:\n%r" % result)

    marker, evidence = _markers(task_dir)
    assert marker, "no .red marker for a real failure"
    assert evidence, "no red.json for a real failure"

    record = json.loads((task_dir / "evidence" / "red.json").read_text())
    assert record["exit_code"] == 1, (
        "the recorded exit should be pytest's 'tests failed' code, got %r"
        % record["exit_code"])

    # and the command recorded must be one the runner would actually accept -
    # no injected flag that only exists when an unloaded plugin is present
    recorded = " ".join(record["command"]) if isinstance(
        record["command"], list) else str(record["command"])
    assert "--cov-fail-under" not in recorded, (
        "tdd-red injected a coverage flag into a project where pytest-cov is "
        "not loadable; the runner would reject it: %s" % recorded)
