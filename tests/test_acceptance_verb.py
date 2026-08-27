"""Config, docs and refactor work needs an honest acceptance (field report R13).

The highest-frequency item in the batch - roughly 40% of the reporter's tasks.
A compose `mem_limit`, a CI `exit-code`, a Prometheus rule, a Terraform runbook,
a dead-code removal: none has a natural behavioural red, because the whole point
of a refactor is that behaviour does not change.

To satisfy the hook they recorded reds like

    compass tdd-red --verified-by regression -- '! grep -q "_ = is_unique" solver.py'

which asserts the presence of a string in a file - exactly the "test the
implementation, not the behaviour" smell `tdd-discipline` warns against. R8's
sanction made that *allowed*; it did not make it *right*. The framework had no
honest path for a legitimate change, so authors invented a dishonest one.

The acceptance verb gives those changes a real signal: a validator that must
pass, or a green baseline that must stay green across a demonstrably changed
tree. It writes its own marker - `.red` keeps meaning only "a real failure was
observed here".

Scenarios: .compass/work/honest-acceptance-for-config-and-refactor/acceptance-criteria.md
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
CLI = ROOT / "cli" / "compass"
HOOK = ROOT / "hooks" / "pre-tool.sh"

PASS_CMD = [sys.executable, "-c", "print('validator ok')"]
FAIL_CMD = [sys.executable, "-c", "import sys; print('nope'); sys.exit(1)"]


def _project(slug="t"):
    """A framed project whose path contains no 'test'/'spec' substring."""
    root = Path(tempfile.mkdtemp(prefix="compass-fix-"))
    (root / "src").mkdir()
    (root / "src" / "app.py").write_text("x = 1\n")
    shutil.copytree(ROOT / "governance", root / "governance")
    (root / ".compass").mkdir()
    (root / ".compass" / "config.yml").write_text("version: 1.0.0\nmode: enforced\n")
    (root / ".compass" / "current-task").write_text(slug + "\n")
    task_dir = root / ".compass" / "work" / slug
    task_dir.mkdir(parents=True)
    (task_dir / "delivery-approach.md").write_text("# Route\n")
    (task_dir / "task.yml").write_text(yaml.safe_dump({
        "schema_version": "1.1", "task": slug, "created": "2026-08-06",
        "assessment": {"risk": "contained", "familiarity": "greenfield",
                     "size": "small", "intent": "delivery"},
        "delivery_approach": "standard", "stages": {"specify": "light"},
        "evidence": [], "gates": [], "scenarios": [], "changed_files": [],
    }, sort_keys=False))
    return root, task_dir


def _run(root, *args):
    return subprocess.run([sys.executable, str(CLI), *args], cwd=str(root),
                          capture_output=True, text=True, timeout=60)


def _hook(root, target="src/app.py"):
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = str(root)
    payload = {"tool_name": "Edit", "tool_input": {"file_path": str(root / target)}}
    return subprocess.run(["bash", str(HOOK)], input=json.dumps(payload),
                          capture_output=True, text=True, env=env, timeout=30)


# ---------------------------------------------------------------------------
# Group A - declaring an acceptance
# ---------------------------------------------------------------------------

def test_scn_a1_validation_start_permits_the_edit():
    root, task_dir = _project()
    try:
        r = _run(root, "acceptance", "start", "--kind", "validation",
                 "--", *PASS_CMD)
        assert r.returncode == 0, f"{r.stdout}{r.stderr}"
        assert (task_dir / ".acceptance").is_file(), "no .acceptance marker written"
        assert not (task_dir / ".red").exists(), (
            ".red must keep meaning that a real failure was observed")
        assert _hook(root).returncode == 0, "the hook did not honour the marker"
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_scn_a2_refactor_requires_a_green_baseline():
    """A refactor's contract is that a passing suite stays passing. Without a
    passing suite to begin with there is nothing to preserve."""
    root, task_dir = _project()
    try:
        r = _run(root, "acceptance", "start", "--kind", "refactor", "--", *FAIL_CMD)
        assert r.returncode != 0, f"a red baseline was accepted:\n{r.stdout}"
        assert not (task_dir / ".acceptance").exists()
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_scn_a3_unknown_kind_refused():
    root, task_dir = _project()
    try:
        r = _run(root, "acceptance", "start", "--kind", "whatever", "--", *PASS_CMD)
        assert r.returncode != 0
        assert "validation" in (r.stdout + r.stderr)
        assert not (task_dir / ".acceptance").exists()
    finally:
        shutil.rmtree(root, ignore_errors=True)


# ---------------------------------------------------------------------------
# Group B - closing an acceptance
# ---------------------------------------------------------------------------

def test_scn_b1_validation_records_the_output():
    root, task_dir = _project()
    try:
        _run(root, "acceptance", "start", "--kind", "validation", "--", *PASS_CMD)
        r = _run(root, "acceptance", "record", "--", *PASS_CMD)
        assert r.returncode == 0, f"{r.stdout}{r.stderr}"
        rec = json.loads((task_dir / "evidence" / "acceptance.json").read_text())
        assert rec["kind"] == "validation", rec
        assert rec["passed"] is True, rec
        assert "validator ok" in rec.get("log_excerpt", ""), rec
        assert not (task_dir / ".acceptance").exists(), "marker not cleared"
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_scn_b2_failing_validator_does_not_close():
    root, task_dir = _project()
    try:
        _run(root, "acceptance", "start", "--kind", "validation", "--", *PASS_CMD)
        r = _run(root, "acceptance", "record", "--", *FAIL_CMD)
        assert r.returncode != 0, "a failing validator closed the acceptance"
        assert (task_dir / ".acceptance").is_file(), "marker was cleared on failure"
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_scn_b3_refactor_requires_the_same_command():
    root, task_dir = _project()
    try:
        _run(root, "acceptance", "start", "--kind", "refactor", "--", *PASS_CMD)
        (root / "src" / "app.py").write_text("x = 2\n")
        other = [sys.executable, "-c", "print('a different command')"]
        r = _run(root, "acceptance", "record", "--", *other)
        assert r.returncode != 0, (
            f"a different command closed a refactor acceptance:\n{r.stdout}")
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_scn_b4_refactor_requires_a_changed_tree():
    """Green then green with nothing changed in between is two runs, not a
    refactor."""
    root, task_dir = _project()
    try:
        _run(root, "acceptance", "start", "--kind", "refactor", "--", *PASS_CMD)
        r = _run(root, "acceptance", "record", "--", *PASS_CMD)
        assert r.returncode != 0, (
            f"an unchanged tree was accepted as a refactor:\n{r.stdout}")
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_scn_b5_refactor_records_both_runs():
    root, task_dir = _project()
    try:
        _run(root, "acceptance", "start", "--kind", "refactor", "--", *PASS_CMD)
        (root / "src" / "app.py").write_text("x = 2  # refactored\n")
        r = _run(root, "acceptance", "record", "--", *PASS_CMD)
        assert r.returncode == 0, f"{r.stdout}{r.stderr}"
        rec = json.loads((task_dir / "evidence" / "acceptance.json").read_text())
        assert rec["kind"] == "refactor", rec
        assert rec.get("baseline", {}).get("passed") is True, rec
        assert rec["passed"] is True, rec
    finally:
        shutil.rmtree(root, ignore_errors=True)


# ---------------------------------------------------------------------------
# Group C - the boundary with red-before-green
# ---------------------------------------------------------------------------

def test_scn_c1_hook_honours_the_acceptance_marker():
    root, task_dir = _project()
    try:
        _run(root, "acceptance", "start", "--kind", "validation", "--", *PASS_CMD)
        assert _hook(root).returncode == 0
        # ... and once the acceptance closes, the permission goes with it.
        _run(root, "acceptance", "record", "--", *PASS_CMD)
        assert _hook(root).returncode == 2, (
            "the marker outlived the acceptance it recorded")
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_scn_c2_marker_is_per_task():
    root, task_dir = _project(slug="one")
    try:
        _run(root, "acceptance", "start", "--kind", "validation", "--", *PASS_CMD)
        other = root / ".compass" / "work" / "two"
        other.mkdir(parents=True)
        (other / "delivery-approach.md").write_text("# Route\n")
        (root / ".compass" / "current-task").write_text("two\n")
        assert _hook(root).returncode == 2, (
            "one task's acceptance permitted an edit under another task")
    finally:
        shutil.rmtree(root, ignore_errors=True)


# ---------------------------------------------------------------------------
# Failure modes
# ---------------------------------------------------------------------------

def test_scn_f1_evidence_is_accepted_by_check():
    """The acceptance has to be usable as the task's recorded run, or authors
    are back to faking a red to satisfy G1."""
    root, task_dir = _project()
    try:
        _run(root, "acceptance", "start", "--kind", "validation", "--", *PASS_CMD)
        _run(root, "acceptance", "record", "--", *PASS_CMD)
        task = yaml.safe_load((task_dir / "task.yml").read_text())
        entries = [e for e in (task.get("evidence") or [])
                   if e.get("path", "").endswith("acceptance.json")]
        assert entries, f"nothing registered in the evidence registry: {task}"
        assert entries[0]["type"] == "test-run", entries
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_scn_f2_tdd_discipline_names_the_verb():
    """An author meets this problem inside the TDD skill, so that is where the
    honest path has to be named - otherwise --verified-by stays the only option
    they can see."""
    text = "\n".join(sorted(q.read_text(encoding="utf-8") for q in (ROOT / "skills" / "tdd-discipline" / "SKILL.md").parent.glob("*.md")))
    assert "compass acceptance" in text, (
        "tdd-discipline does not mention the acceptance verb, so an author with "
        "a config or refactor change will still reach for a grep-shaped red")


# ---------------------------------------------------------------------------
# Group G - two scenarios' acceptance records must not collide
#
# Found while recording TRC-F4 and TRC-F5's characterisation acceptances for
# zero-friction-install: `compass acceptance record --scenario ...` always
# wrote the SAME fixed file, evidence/acceptance.json, regardless of
# --scenario. A second scenario's record silently overwrote the first's real
# evidence, even though task.yml's registry still listed both scenarios as
# bound to that one (now wrong-for-one-of-them) file. `compass tdd-green`
# already avoids exactly this by writing a scenario-specific copy alongside
# the generic one; `compass acceptance record` did not.
# ---------------------------------------------------------------------------

def test_scn_g1_two_scenarios_recorded_in_sequence_do_not_overwrite_each_other():
    root, task_dir = _project()
    try:
        _run(root, "acceptance", "start", "--kind", "refactor", "--", *PASS_CMD)
        (root / "src" / "app.py").write_text("x = 2  # first change\n")
        r1 = _run(root, "acceptance", "record", "--scenario", "TRC-ONE", "--", *PASS_CMD)
        assert r1.returncode == 0, r1.stdout + r1.stderr

        _run(root, "acceptance", "start", "--kind", "refactor", "--", *PASS_CMD)
        (root / "src" / "app.py").write_text("x = 3  # second change\n")
        r2 = _run(root, "acceptance", "record", "--scenario", "TRC-TWO", "--", *PASS_CMD)
        assert r2.returncode == 0, r2.stdout + r2.stderr

        task = yaml.safe_load((task_dir / "task.yml").read_text())
        by_scenario = {e.get("scenario"): e.get("path")
                       for e in (task.get("evidence") or [])
                       if e.get("type") == "test-run"}
        assert by_scenario.get("TRC-ONE") and by_scenario.get("TRC-TWO"), by_scenario
        assert by_scenario["TRC-ONE"] != by_scenario["TRC-TWO"], (
            "both scenarios are registered against the same evidence file - "
            "the second record overwrote the first's real evidence")

        one = json.loads((task_dir / by_scenario["TRC-ONE"]).read_text())
        two = json.loads((task_dir / by_scenario["TRC-TWO"]).read_text())
        assert one["scenario"] == "TRC-ONE", one
        assert two["scenario"] == "TRC-TWO", two
    finally:
        shutil.rmtree(root, ignore_errors=True)
