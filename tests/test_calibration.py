"""Re-frame recording + `compass calibration`.

When `compass route evaluate --write` computes a route that differs from
the one already recorded in task.yml, the diff is logged under
`reframes:`. `compass calibration` aggregates these across every task and
classifies the trend as up (Needle under-sizing) or down (over-sizing).
"""
from __future__ import annotations

import yaml


def _readings_to_args(d):
    out = []
    for k, v in d.items():
        if isinstance(v, list):
            out.extend(["--reading", f"{k}=" + ",".join(v)])
        else:
            out.extend(["--reading", f"{k}={v}"])
    return out


# --- the recording behaviour ----------------------------------------------


def test_route_evaluate_write_logs_reframe(run_cli, make_task, project):
    """A task that ALREADY had a route (express) gets re-evaluated as
    expedition (after a touches: [auth] is added) — the diff must be
    appended to `reframes:`."""
    body = {
        "task": "rf-task",
        "created": "2026-05-15",
        "readings": {
            "blast_radius": "contained",
            "terrain": "brownfield-mapped",
            "magnitude": "small",
            "intent": "delivery",
            "touches": [],
        },
        "route": "express",   # the recorded route the next eval will diff against
    }
    task_dir = make_task("rf-task", body)
    # mutate the readings (touches=auth) so the next evaluate computes expedition
    body["readings"]["touches"] = ["auth"]
    (task_dir / "task.yml").write_text(yaml.safe_dump(body, sort_keys=False))

    r = run_cli("route", "evaluate", "--task", "rf-task", "--write",
                "--reason", "discovered the change touches auth")
    assert r.returncode == 0, r
    task = yaml.safe_load((task_dir / "task.yml").read_text())
    assert task["route"] == "expedition"
    assert task["reframes"], "expected a reframes entry"
    rf = task["reframes"][-1]
    assert rf["from_route"] == "express"
    assert rf["to_route"] == "expedition"
    assert "auth" in rf["reason"]


def test_route_evaluate_does_not_log_reframe_when_route_unchanged(run_cli,
                                                                  make_task,
                                                                  project):
    """Re-running --write with the same readings should NOT spuriously log
    a re-frame."""
    body = {
        "task": "no-rf",
        "created": "2026-05-15",
        "readings": {
            "blast_radius": "contained",
            "terrain": "brownfield-mapped",
            "magnitude": "small",
            "intent": "delivery",
        },
        "route": "express",
    }
    task_dir = make_task("no-rf", body)
    r = run_cli("route", "evaluate", "--task", "no-rf", "--write")
    assert r.returncode == 0, r
    task = yaml.safe_load((task_dir / "task.yml").read_text())
    assert task["route"] == "express"
    assert not task.get("reframes"), f"expected no reframes, got: {task.get('reframes')}"


def test_route_evaluate_warns_when_reframe_has_no_reason(run_cli, make_task,
                                                        project):
    """Re-frame with no --reason still records the entry, but warns — the
    reason is the calibration signal."""
    body = {
        "task": "rf-noreason",
        "created": "2026-05-15",
        "readings": {
            "blast_radius": "contained",
            "terrain": "brownfield-mapped",
            "magnitude": "small",
            "intent": "delivery",
            "touches": ["auth"],
        },
        "route": "express",
    }
    task_dir = make_task("rf-noreason", body)
    r = run_cli("route", "evaluate", "--task", "rf-noreason", "--write")
    assert r.returncode == 0, r
    combined = r.stdout + r.stderr
    # the CLI should mention the missing reason on stderr
    assert "reason" in combined.lower(), r


# --- the aggregator: calibration -------------------------------------------


def _task_with_reframes(slug, transitions, base_route="standard"):
    """transitions: list of (from_route, to_route) tuples."""
    return {
        "task": slug,
        "created": "2026-05-15",
        "readings": {
            "blast_radius": "contained",
            "terrain": "brownfield-mapped",
            "magnitude": "small",
            "intent": "delivery",
        },
        "route": base_route,
        "reframes": [
            {"from_route": fr, "to_route": to, "reason": "x",
             "date": "2026-05-15"}
            for fr, to in transitions
        ],
    }


def test_calibration_no_tasks(run_cli):
    r = run_cli("calibration")
    assert r.returncode == 0, r
    assert "no tasks" in r.stdout.lower(), r


def test_calibration_aggregates_up_reframes(run_cli, make_task):
    """Three up-reframes (express -> expedition, standard -> expedition,
    express -> standard) should report 'UNDER-sizing'."""
    make_task("t1", _task_with_reframes(
        "t1", [("express", "expedition")], base_route="expedition"))
    make_task("t2", _task_with_reframes(
        "t2", [("standard", "expedition")], base_route="expedition"))
    make_task("t3", _task_with_reframes(
        "t3", [("express", "standard")], base_route="standard"))
    r = run_cli("calibration")
    assert r.returncode == 0, r
    assert "UNDER-sizing" in r.stdout, r


def test_calibration_aggregates_down_reframes(run_cli, make_task):
    """Three down-reframes report 'OVER-sizing'."""
    make_task("t1", _task_with_reframes(
        "t1", [("expedition", "express")], base_route="express"))
    make_task("t2", _task_with_reframes(
        "t2", [("expedition", "standard")], base_route="standard"))
    make_task("t3", _task_with_reframes(
        "t3", [("standard", "express")], base_route="express"))
    r = run_cli("calibration")
    assert r.returncode == 0, r
    assert "OVER-sizing" in r.stdout, r


def test_calibration_balanced(run_cli, make_task):
    """One up, one down — balanced; neither over nor under."""
    make_task("t1", _task_with_reframes(
        "t1", [("express", "standard")], base_route="standard"))
    make_task("t2", _task_with_reframes(
        "t2", [("expedition", "standard")], base_route="standard"))
    r = run_cli("calibration")
    assert r.returncode == 0, r
    out = r.stdout
    # neither verdict should be selected when ups == downs == 1
    assert "UNDER-sizing" not in out, r
    assert "OVER-sizing" not in out, r
    # and the route distribution must be reported
    assert "Route distribution" in out, r


# --- TRC-C5: reframe-debt section in calibration output ---------------------


def test_reframe_debt_section(run_cli, make_task, project):
    """TRC-C5: compass calibration surfaces absorbed mis-frames.

    A task with scope-bloat devlog phrases and an empty reframes list is
    reported in a 'reframe debt' section, with the matched devlog signal
    and explicit mention that the signal was absorbed/lost.

    B-Risk 6: the devlog patterns come from signals.yml, not hardcoded in
    the CLI.
    """
    import pathlib
    import shutil

    # Ensure signals.yml is in the project's governance/ so the CLI can find it
    gov_dir = project / "governance"
    signals_src = pathlib.Path(__file__).resolve().parent.parent / "governance" / "signals.yml"
    if signals_src.is_file() and not (gov_dir / "signals.yml").is_file():
        shutil.copy(signals_src, gov_dir / "signals.yml")

    # Task with a scope-bloat devlog phrase and no reframes
    task_dir = make_task("reframe-debt-task", {
        "task": "reframe-debt-task",
        "created": "2026-05-20",
        "readings": {
            "blast_radius": "contained",
            "terrain": "brownfield-mapped",
            "magnitude": "small",
        },
        "route": "standard",
        "reframes": [],
    })
    (task_dir / "devlog.md").write_text(
        "2026-05-20: more files than Plan estimated — had to extend the scope\n"
    )

    r = run_cli("calibration")
    assert r.returncode == 0, r

    out = r.stdout.lower()
    assert "reframe debt" in out, (
        "Expected a 'reframe debt' section in calibration output.\n"
        f"Got:\n{r.stdout}"
    )
    # Must name the task
    assert "reframe-debt-task" in r.stdout.lower(), (
        "Reframe-debt section must name the affected task.\n"
        f"Got:\n{r.stdout}"
    )
    # Must explain the consequence
    assert "absorbed" in out or "signal lost" in out, (
        "Reframe-debt section must state 'absorbed mis-frame, signal lost'.\n"
        f"Got:\n{r.stdout}"
    )


def test_reframe_debt_empty_when_no_bloat(run_cli, make_task, project):
    """TRC-C5 negative case: tasks with no scope-bloat phrases get no reframe-debt section."""
    import pathlib
    import shutil

    gov_dir = project / "governance"
    signals_src = pathlib.Path(__file__).resolve().parent.parent / "governance" / "signals.yml"
    if signals_src.is_file() and not (gov_dir / "signals.yml").is_file():
        shutil.copy(signals_src, gov_dir / "signals.yml")

    make_task("clean-no-bloat", {
        "task": "clean-no-bloat",
        "created": "2026-05-20",
        "readings": {
            "blast_radius": "contained",
            "terrain": "brownfield-mapped",
            "magnitude": "small",
        },
        "route": "standard",
        "reframes": [],
    })

    r = run_cli("calibration")
    assert r.returncode == 0, r
    # No reframe-debt section when devlog has no scope-bloat phrases
    assert "reframe debt" not in r.stdout.lower(), (
        "Unexpected reframe-debt section when no scope-bloat phrases in devlog.\n"
        f"Got:\n{r.stdout}"
    )


def test_reframe_debt_suppressed_when_reframe_filed(run_cli, make_task, project):
    """TRC-C5 suppression case: a filed reframe removes the debt for that task."""
    import pathlib
    import shutil

    gov_dir = project / "governance"
    signals_src = pathlib.Path(__file__).resolve().parent.parent / "governance" / "signals.yml"
    if signals_src.is_file() and not (gov_dir / "signals.yml").is_file():
        shutil.copy(signals_src, gov_dir / "signals.yml")

    task_dir = make_task("reframed-ok", {
        "task": "reframed-ok",
        "created": "2026-05-19",
        "readings": {
            "blast_radius": "contained",
            "terrain": "brownfield-mapped",
            "magnitude": "small",
        },
        "route": "expedition",
        "reframes": [
            {
                "from_route": "standard",
                "to_route": "expedition",
                "reason": "scope grew",
                "date": "2026-05-20",
            }
        ],
    })
    (task_dir / "devlog.md").write_text(
        "2026-05-19: more files than Plan estimated\n"
    )

    r = run_cli("calibration")
    assert r.returncode == 0, r
    # The task had a bloat phrase BUT a reframe was filed after — no debt
    # (If the section is absent entirely, or the task is not in it, pass.)
    out = r.stdout.lower()
    if "reframe debt" in out:
        assert "reframed-ok" not in out, (
            "Task 'reframed-ok' should not appear in reframe-debt when a "
            "reframe was already filed.\n"
            f"Got:\n{r.stdout}"
        )


def test_calibration_does_not_mutate_task_yml(run_cli, make_task, project):
    """B-Risk 5: calibration is read-only — task.yml must be unchanged after running."""
    import pathlib
    import hashlib
    import shutil

    gov_dir = project / "governance"
    signals_src = pathlib.Path(__file__).resolve().parent.parent / "governance" / "signals.yml"
    if signals_src.is_file() and not (gov_dir / "signals.yml").is_file():
        shutil.copy(signals_src, gov_dir / "signals.yml")

    task_dir = make_task("immutable-task", {
        "task": "immutable-task",
        "created": "2026-05-20",
        "readings": {
            "blast_radius": "contained",
            "terrain": "brownfield-mapped",
            "magnitude": "small",
        },
        "route": "standard",
        "reframes": [],
    })
    (task_dir / "devlog.md").write_text(
        "more files than Plan estimated\n"
    )

    task_yml = task_dir / "task.yml"
    sha_before = hashlib.sha256(task_yml.read_bytes()).hexdigest()

    r = run_cli("calibration")
    assert r.returncode == 0, r

    sha_after = hashlib.sha256(task_yml.read_bytes()).hexdigest()
    assert sha_before == sha_after, (
        f"B-Risk 5 violated: calibration mutated task.yml\n"
        f"Before SHA: {sha_before}\nAfter SHA:  {sha_after}"
    )
