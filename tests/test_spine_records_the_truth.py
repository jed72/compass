"""The spine must record what actually happened (reports R18, R15, R19).

R18 - `route evaluate --write --reason "..."` logged a re-frame only when the
route NAME changed. Two re-frames on one task, days apart, both with an explicit
reason, left `reframes: []`: one adopted a newer governance policy and took the
task from 7 gates to 9; the other split scope, moving magnitude large ->
standard. The second is a textbook re-frame - the readings themselves changed -
and it was invisible. `compass retro` aggregates `reframes:` to detect the
Needle systematically mis-sizing routes, so the signal was under-counted.

R15 - `evidence add --type test-run --path run.txt` was accepted, and `check`
failed later with "test-run evidence unreadable", because `test-run` means a
JSON run record and not a raw log. Nothing said so at write time.

R19 - `blueprint-distillation` names silent supersession as an anti-pattern and
asks for the link to be recorded. The schema rejected `superseded_by`, so a
skill instructed authors to record something the validator forbade.

Scenarios: .compass/work/spine-records-the-truth/spec.feature.md (SCN-A1..F1).
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
CLI = ROOT / "cli" / "compass"


def _project(tmp_path, task=None, slug="t"):
    root = tmp_path / "proj"
    if not root.exists():
        shutil.copytree(ROOT / "governance", root / "governance")
        (root / ".compass").mkdir(parents=True)
        (root / ".compass" / "config.yml").write_text("version: 1.0.0\nmode: enforced\n")
    d = root / ".compass" / "work" / slug
    d.mkdir(parents=True, exist_ok=True)
    (d / "delivery-approach.md").write_text("# Route\n")
    (d / "evidence").mkdir(exist_ok=True)
    (d / "task.yml").write_text(yaml.safe_dump(task or _base(), sort_keys=False))
    (root / ".compass" / "current-task").write_text(slug + "\n")
    return root


def _base(**over):
    t = {
        "schema_version": "1.1", "task": "t", "created": "2026-08-06",
        "assessment": {"risk": "contained", "familiarity": "greenfield",
                     "size": "small", "intent": "delivery",
                     "urgency": "none", "role": "engineer", "labels": []},
        "evidence": [], "gates": [], "scenarios": [], "changed_files": [],
        "claims": [], "follow_ups": [], "reassessments": [], "friction": [],
    }
    t.update(over)
    return t


def _run(root, *args):
    return subprocess.run([sys.executable, str(CLI), *args], cwd=str(root),
                          capture_output=True, text=True, timeout=60)


def _task(root, slug="t"):
    return yaml.safe_load((root / ".compass" / "work" / slug / "task.yml").read_text())


# ---------------------------------------------------------------------------
# Group A - re-frame detection (R18)
# ---------------------------------------------------------------------------

def _seeded(tmp_path, **readings):
    """A task whose route has already been computed once."""
    root = _project(tmp_path, _base(readings={
        "risk": "contained", "familiarity": "greenfield",
        "size": "small", "intent": "delivery", "urgency": "none",
        "role": "engineer", "labels": [], **readings}))
    _run(root, "approach", "evaluate", "--issue", "t", "--write")
    return root


def test_scn_a1_content_change_is_logged(tmp_path):
    """Same route name, materially different route."""
    root = _seeded(tmp_path)
    before = _task(root)
    assert before["delivery_approach"] == "feature", before["delivery_approach"]

    # cross-cutting keeps the route name `standard` and takes the gate set from
    # 6 to 7 (RP-REQUIRE-003 adds verify.fitness) - R18's exact case. `critical`
    # would also change the route NAME, which the old code already logged, so it
    # would prove nothing.
    before["assessment"]["risk"] = "cross-cutting"
    (root / ".compass" / "work" / "t" / "task.yml").write_text(
        yaml.safe_dump(before, sort_keys=False))
    r = _run(root, "approach", "evaluate", "--issue", "t", "--write",
             "--reason", "risk re-read after discovery")
    after = _task(root)
    assert after["reassessments"], (
        f"a re-frame that changed the gate set was not logged:\n{r.stdout}")


def test_scn_a2_no_material_change_is_not_logged(tmp_path):
    root = _seeded(tmp_path)
    r = _run(root, "approach", "evaluate", "--issue", "t", "--write",
             "--reason", "no change expected")
    after = _task(root)
    assert after["reassessments"] == [], (
        f"an unchanged re-evaluation was logged as a re-frame:\n{after['reframes']}")
    assert "not recorded" in (r.stdout + r.stderr).lower(), (
        f"a --reason that went nowhere must be said out loud:\n{r.stdout}{r.stderr}")


def test_scn_a3_entry_records_what_changed(tmp_path):
    root = _seeded(tmp_path)
    t = _task(root)
    t["assessment"]["risk"] = "cross-cutting"
    (root / ".compass" / "work" / "t" / "task.yml").write_text(
        yaml.safe_dump(t, sort_keys=False))
    _run(root, "approach", "evaluate", "--issue", "t", "--write", "--reason", "why")
    entry = _task(root)["reassessments"][-1]
    assert "changed" in entry, entry
    assert "gates" in entry["changed"], entry
    assert entry["changed"]["gates"]["from"] != entry["changed"]["gates"]["to"], entry


def test_scn_a4_entry_carries_a_kind(tmp_path):
    root = _seeded(tmp_path)
    t = _task(root)
    t["assessment"]["risk"] = "cross-cutting"
    (root / ".compass" / "work" / "t" / "task.yml").write_text(
        yaml.safe_dump(t, sort_keys=False))
    _run(root, "approach", "evaluate", "--issue", "t", "--write",
         "--reason", "policy moved", "--kind", "policy-correction")
    entry = _task(root)["reassessments"][-1]
    assert entry.get("kind") == "policy-correction", entry

    # and the default, when nobody says
    t2 = _task(root)
    t2["assessment"]["size"] = "large"
    (root / ".compass" / "work" / "t" / "task.yml").write_text(
        yaml.safe_dump(t2, sort_keys=False))
    _run(root, "approach", "evaluate", "--issue", "t", "--write", "--reason", "bigger")
    assert _task(root)["reassessments"][-1].get("kind") == "judgement", _task(root)["reassessments"]


def test_scn_a5_calibration_counts_only_judgement(tmp_path):
    """A policy-correction re-frame would otherwise read as the Needle
    under-sizing, which pollutes the signal calibration exists to produce."""
    reframes = [
        {"from_route": "standard", "to_route": "expedition", "kind": "judgement",
         "reason": "magnitude under-read", "date": "2026-08-01"},
        {"from_route": "expedition", "to_route": "expedition",
         "kind": "policy-correction", "reason": "adopted newer policy",
         "date": "2026-08-02"},
    ]
    root = _project(tmp_path, _base(route="expedition", reframes=reframes))
    r = _run(root, "retro")
    out = r.stdout + r.stderr
    assert "policy-correction" in out or "1" in out, out
    assert "2 re-frame" not in out, (
        f"a policy-correction was counted in the re-sizing signal:\n{out}")


# ---------------------------------------------------------------------------
# Group B - evidence shape (R15)
# ---------------------------------------------------------------------------

def test_scn_b1_raw_log_as_test_run_refused(tmp_path):
    root = _project(tmp_path)
    (root / ".compass" / "work" / "t" / "evidence" / "run.txt").write_text(
        "===== 12 passed in 0.4s =====\n")
    r = _run(root, "evidence", "add", "EV-R", "--type", "test-run",
             "--path", "evidence/run.txt")
    out = r.stdout + r.stderr
    assert r.returncode != 0, f"a raw log was registered as a test-run:\n{out}"
    assert "command-output" in out, (
        f"the failure must name the type a raw log should use:\n{out}")


def test_scn_b2_real_run_record_accepted(tmp_path):
    root = _project(tmp_path)
    (root / ".compass" / "work" / "t" / "evidence" / "green.json").write_text(
        json.dumps({"command": "pytest -q", "exit_code": 0, "passed": True}))
    r = _run(root, "evidence", "add", "EV-G", "--type", "test-run",
             "--path", "evidence/green.json")
    assert r.returncode == 0, f"{r.stdout}{r.stderr}"


def test_scn_b3_missing_file_refused(tmp_path):
    root = _project(tmp_path)
    r = _run(root, "evidence", "add", "EV-X", "--type", "command-output",
             "--path", "evidence/nope.txt")
    assert r.returncode != 0, "evidence was registered against a missing file"


@pytest.mark.parametrize("etype", ["manual-review", "artifact"])
def test_scn_b4_types_without_shape_contract_unaffected(tmp_path, etype):
    root = _project(tmp_path)
    (root / ".compass" / "work" / "t" / "notes.md").write_text("# Review\n")
    r = _run(root, "evidence", "add", f"EV-{etype[:3].upper()}", "--type", etype,
             "--path", "notes.md")
    assert r.returncode == 0, f"{etype} was rejected:\n{r.stdout}{r.stderr}"


# ---------------------------------------------------------------------------
# Group C - supersession (R19)
# ---------------------------------------------------------------------------

def test_scn_c1_superseded_by_validates(tmp_path):
    scenarios = [
        {"id": "TRC-A1", "title": "baseline", "intent": "INT-1",
         "tests": ["tests/test_x.py"], "superseded_by": ["TRC-D1"]},
        {"id": "TRC-D1", "title": "target", "intent": "INT-1",
         "tests": ["tests/test_x.py"]},
    ]
    root = _project(tmp_path, _base(scenarios=scenarios))
    r = _run(root, "issue", "lint", "--issue", "t")
    assert r.returncode == 0, (
        f"the schema still forbids what blueprint-distillation requires:\n"
        f"{r.stdout}{r.stderr}")


def test_scn_c2_dangling_supersession_fails(tmp_path):
    scenarios = [
        {"id": "TRC-A1", "title": "baseline", "intent": "INT-1",
         "tests": ["tests/test_x.py"], "superseded_by": ["TRC-NOPE"]},
    ]
    root = _project(tmp_path, _base(scenarios=scenarios, route="express",
                                    gates=[]))
    r = _run(root, "check", "--issue", "t")
    out = r.stdout + r.stderr
    assert "TRC-NOPE" in out, (
        f"a supersession pointing at nothing was not reported:\n{out}")


# ---------------------------------------------------------------------------
# Failure modes
# ---------------------------------------------------------------------------

def test_scn_f1_existing_task_files_unchanged(tmp_path):
    """Every task.yml on disk predates all three changes: reframes entries with
    no `kind`, scenarios with no `superseded_by`."""
    old = _base(route="standard", reframes=[
        {"from_route": "express", "to_route": "standard",
         "reason": "magnitude under-read", "date": "2026-07-01"}])
    root = _project(tmp_path, old)
    assert _run(root, "issue", "lint", "--issue", "t").returncode == 0
    assert _run(root, "retro").returncode == 0
