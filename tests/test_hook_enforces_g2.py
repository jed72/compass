"""The hook must enforce G2, not only the strategy that serves G1 (report R23).

`hooks/pre-tool.sh` blocks a code edit until a failing test is on record -
strategy S2, in service of guardrail G1. Nothing blocked a code edit when the
route said `specify: full` and no spec existed, so guardrail G2 - acceptance
defined before it is built - had no enforcement at the point where it could
still be true.

The asymmetry is the point: S2, a *strategy*, got a real-time blocking hook. G2,
a *guardrail*, which by the framework's own conflict rule beats a strategy, got
a post-hoc report. `compass check` does catch it, at Verify, after the code
exists - which is the ordering G2 exists to prevent.

Only `specify: full` triggers this, and routing-policy.yml gives that to
standard and expedition only. A Hotfix (reproduce-first) and a Spike (collapsed)
are exempt by construction rather than by special case.

Scenarios: .compass/work/hook-enforces-g2/spec.feature.md (SCN-A1..F2).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / "hooks" / "pre-tool.sh"


def _project(*, specify="full", scenarios=0, red=True, spike=False,
             task_yml=True, broken_yml=False):
    root = Path(tempfile.mkdtemp(prefix="compass-fix-"))
    task_dir = root / ".compass" / "work" / "t"
    task_dir.mkdir(parents=True)
    (root / ".compass" / "current-task").write_text("t\n")
    (task_dir / "delivery-approach.md").write_text("# Route\n")
    if red:
        (task_dir / ".red").write_text("")
    if spike:
        (task_dir / ".spike").write_text("")
    if broken_yml:
        (task_dir / "task.yml").write_text("phases: [this is not\n  valid: yaml\n")
    elif task_yml:
        (task_dir / "task.yml").write_text(yaml.safe_dump({
            "schema_version": "1.1", "task": "t", "created": "2026-08-06",
            "assessment": {"risk": "contained", "familiarity": "greenfield",
                         "size": "small", "intent": "delivery"},
            "delivery_approach": "standard",
            "stages": {"specify": specify},
            "scenarios": [{"id": f"SCN-{i}", "title": "s", "intent": "INT-1",
                           "tests": ["tests/test_x.py"]}
                          for i in range(1, scenarios + 1)],
        }, sort_keys=False))
    return root


def _run(project, target="src/app.py", tool="Edit"):
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = str(project)
    payload = {"tool_name": tool, "tool_input": {"file_path": str(project / target)}}
    return subprocess.run(["bash", str(HOOK)], input=json.dumps(payload),
                          capture_output=True, text=True, env=env, timeout=30)


# ---------------------------------------------------------------------------
# Group A - G2 is enforced where it can still be true
# ---------------------------------------------------------------------------

def test_scn_a1_full_specify_with_no_scenarios_blocks_a_code_edit():
    """The reporter's case: a red was on record, so S2 was satisfied and every
    edit was allowed - while the route asked for a full Specify that never
    happened."""
    project = _project(specify="full", scenarios=0, red=True)
    try:
        result = _run(project)
        assert result.returncode == 2, (
            f"code was edited on a full-Specify route with no scenarios:\n"
            f"{result.stdout}{result.stderr}")
        assert "G2" in result.stderr, result.stderr
    finally:
        shutil.rmtree(project, ignore_errors=True)


def test_scn_a2_scenarios_present_allows_the_edit():
    project = _project(specify="full", scenarios=3, red=True)
    try:
        result = _run(project)
        assert result.returncode == 0, result.stderr
    finally:
        shutil.rmtree(project, ignore_errors=True)


@pytest.mark.parametrize("specify", ["light", "collapsed", "reproduce-first"])
def test_scn_a3_routes_without_a_full_specify_are_unaffected(specify):
    """Express (light), Spike (collapsed) and Hotfix (reproduce-first) are
    exempt by construction - a Hotfix writes its reproduction before any spec."""
    project = _project(specify=specify, scenarios=0, red=True)
    try:
        result = _run(project)
        assert result.returncode == 0, (
            f"specify={specify} was blocked by the G2 check:\n{result.stderr}")
    finally:
        shutil.rmtree(project, ignore_errors=True)


def test_scn_a4_a_spike_suspends_the_g2_check_too():
    project = _project(specify="full", scenarios=0, red=False, spike=True)
    try:
        result = _run(project)
        assert result.returncode == 0, result.stderr
    finally:
        shutil.rmtree(project, ignore_errors=True)


# ---------------------------------------------------------------------------
# Group B - the block has to be actionable
# ---------------------------------------------------------------------------

def test_scn_b1_the_message_names_the_guardrail_and_the_remedy():
    project = _project(specify="full", scenarios=0, red=True)
    try:
        err = _run(project).stderr
        assert "G2" in err and "acceptance-criteria.md" in err, err
        assert "scenarios" in err, err
        assert "frame" in err.lower(), (
            "a genuinely exploratory task should be told to re-frame - a Spike "
            "suspends G2:\n" + err)
    finally:
        shutil.rmtree(project, ignore_errors=True)


def test_scn_b2_a_test_file_is_still_editable():
    """G2 must not stop you writing the spec's tests, any more than S2 does."""
    project = _project(specify="full", scenarios=0, red=False)
    try:
        result = _run(project, target="tests/test_app.py")
        assert result.returncode == 0, result.stderr
    finally:
        shutil.rmtree(project, ignore_errors=True)


# ---------------------------------------------------------------------------
# Failure modes - an unreadable spine must not block work
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("kwargs,label", [
    ({"task_yml": False}, "no task.yml at all"),
    ({"broken_yml": True}, "unparseable task.yml"),
])
def test_scn_f1_an_unreadable_spine_does_not_block(kwargs, label):
    """This check reads a file the hook did not previously need. If it cannot be
    read the hook must fall back to its prior behaviour, not invent a block -
    a false block on unreadable state trains people to bypass the hook."""
    project = _project(specify="full", scenarios=0, red=True, **kwargs)
    try:
        result = _run(project)
        assert result.returncode == 0, (
            f"blocked because of {label}:\n{result.stdout}{result.stderr}")
    finally:
        shutil.rmtree(project, ignore_errors=True)


def test_scn_f2_g2_is_checked_before_the_red():
    """With neither a spec nor a red, the G2 message is the useful one: you
    cannot write a red for a scenario that does not exist yet."""
    project = _project(specify="full", scenarios=0, red=False)
    try:
        err = _run(project).stderr
        assert "G2" in err, (
            f"the red message won over the acceptance one:\n{err}")
    finally:
        shutil.rmtree(project, ignore_errors=True)
