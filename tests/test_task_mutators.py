"""R6 + R9 — schema-owning task.yml mutators and the write-time gate-evidence
type guard. `compass gate pass` is the shared command: it is R9's gate mutator
whose write-time validation against gate_evidence_requirements IS the R6 fix.
"""
from __future__ import annotations

import yaml


def _body_with_gates():
    return {
        "task": "mut",
        "created": "2026-06-22",
        "readings": {"blast_radius": "contained", "terrain": "brownfield-mapped",
                     "magnitude": "small", "intent": "delivery"},
        "route": "standard",
        "scenarios": [{"id": "SCN-1", "intent": "INT-1",
                       "tests": ["tests/test_x.py::test_y"]}],
        "evidence": [
            {"id": "EV-T", "type": "test-run", "path": "evidence/green.json"},
            {"id": "EV-CO", "type": "command-output", "path": "evidence/scan.txt"},
        ],
        "gates": [
            {"id": "verify.correctness", "status": "pending", "evidence": []},
            {"id": "verify.governance", "status": "pending", "evidence": []},
        ],
        "changed_files": [],
    }


def _mk_evfile(task_dir, rel):
    p = task_dir / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("{}")


# --- R9-1 (baseline → guard): the mutators now exist -----------------------

def test_no_mutator_exists_today_baseline(run_cli, make_task):
    """TRC-R9-1: the gap is closed — schema-owning mutators are registered
    verbs (no longer hand-edited YAML)."""
    make_task("mut-help", _body_with_gates())
    for verb in (("scenario", "add"), ("changed-file", "add"),
                 ("evidence", "add"), ("gate", "pass")):
        r = run_cli(*verb, "--help")
        assert r.returncode == 0, (verb, r)


# --- R6-3/4 + R9-7: gate pass ----------------------------------------------

def test_gate_pass_rejects_wrong_type_with_accepted_list(run_cli, make_task):
    """TRC-R6-3: a wrong-type evidence is refused at write time, with the
    accepted-type list, and the gate stays pending (no partial write)."""
    task_dir = make_task("gp-wrong", _body_with_gates())
    _mk_evfile(task_dir, "evidence/green.json")
    r = run_cli("gate", "pass", "verify.governance", "--evidence", "EV-T")
    assert r.returncode != 0, r
    combined = r.stdout + r.stderr
    assert "verify.governance" in combined and "test-run" in combined, r
    assert "command-output" in combined, r          # the accepted list
    task = yaml.safe_load((task_dir / "task.yml").read_text())
    g = next(x for x in task["gates"] if x["id"] == "verify.governance")
    assert g["status"] == "pending", r              # no partial write


def test_gate_pass_accepts_correct_type_and_flips_pass(run_cli, make_task):
    """TRC-R6-4: a correct-type evidence flips the gate to pass and check accepts it."""
    task_dir = make_task("gp-ok", _body_with_gates())
    _mk_evfile(task_dir, "evidence/scan.txt")
    r = run_cli("gate", "pass", "verify.governance", "--evidence", "EV-CO")
    assert r.returncode == 0, r
    task = yaml.safe_load((task_dir / "task.yml").read_text())
    g = next(x for x in task["gates"] if x["id"] == "verify.governance")
    assert g["status"] == "pass" and g["evidence"] == ["EV-CO"], r


def test_gate_pass_mutation_lints_clean(run_cli, make_task):
    """TRC-R9-7: gate pass mutates through the schema-owning writer; task lint passes."""
    task_dir = make_task("gp-lint", _body_with_gates())
    _mk_evfile(task_dir, "evidence/green.json")
    r = run_cli("gate", "pass", "verify.correctness", "--evidence", "EV-T")
    assert r.returncode == 0, r
    lint = run_cli("task", "lint", "--task", "gp-lint")
    assert lint.returncode == 0, lint


def test_gate_pass_unknown_gate_errors(run_cli, make_task):
    make_task("gp-unknown", _body_with_gates())
    r = run_cli("gate", "pass", "verify.nope", "--evidence", "EV-T")
    assert r.returncode != 0, r
    assert "verify.nope" in (r.stdout + r.stderr), r


# --- R9-2/3/4: the add mutators --------------------------------------------

def test_scenario_add_appends_lint_clean_entry(run_cli, make_task):
    task_dir = make_task("sc-add", _body_with_gates())
    r = run_cli("scenario", "add", "SCN-2", "--title", "Export ledger",
                "--intent", "INT-1", "--test", "tests/test_x.py::test_z")
    assert r.returncode == 0, r
    task = yaml.safe_load((task_dir / "task.yml").read_text())
    scn = next(s for s in task["scenarios"] if s["id"] == "SCN-2")
    assert scn["title"] == "Export ledger" and scn["intent"] == "INT-1"
    assert scn["tests"] == ["tests/test_x.py::test_z"], r
    lint = run_cli("task", "lint", "--task", "sc-add")
    assert lint.returncode == 0, lint


def test_changed_file_add_traces_to_scenario(run_cli, make_task):
    task_dir = make_task("cf-add", _body_with_gates())
    r = run_cli("changed-file", "add", "cli/compass", "--scenario", "SCN-1")
    assert r.returncode == 0, r
    task = yaml.safe_load((task_dir / "task.yml").read_text())
    cf = next(c for c in task["changed_files"] if c["path"] == "cli/compass")
    assert "SCN-1" in cf["scenarios"], r


def test_evidence_add_appends_typed_entry(run_cli, make_task):
    task_dir = make_task("ev-add", _body_with_gates())
    r = run_cli("evidence", "add", "EV-5", "--type", "command-output",
                "--path", "evidence/scan.txt")
    assert r.returncode == 0, r
    task = yaml.safe_load((task_dir / "task.yml").read_text())
    e = next(x for x in task["evidence"] if x["id"] == "EV-5")
    assert e["type"] == "command-output" and e["path"] == "evidence/scan.txt", r


# --- R9-5/6: rejections -----------------------------------------------------

def test_scenario_add_rejects_duplicate_id(run_cli, make_task):
    task_dir = make_task("sc-dup", _body_with_gates())
    r = run_cli("scenario", "add", "SCN-1", "--title", "Other",
                "--intent", "INT-2", "--test", "tests/test_z.py::t")
    assert r.returncode != 0, r
    assert "SCN-1" in (r.stdout + r.stderr), r
    task = yaml.safe_load((task_dir / "task.yml").read_text())
    scn = next(s for s in task["scenarios"] if s["id"] == "SCN-1")
    assert scn["intent"] == "INT-1", r              # unchanged, no clobber


def test_evidence_add_rejects_unknown_type(run_cli, make_task):
    task_dir = make_task("ev-bad", _body_with_gates())
    r = run_cli("evidence", "add", "EV-9", "--type", "bogus-type",
                "--path", "evidence/x.txt")
    assert r.returncode != 0, r
    assert "bogus-type" in (r.stdout + r.stderr), r
    task = yaml.safe_load((task_dir / "task.yml").read_text())
    assert not any(e["id"] == "EV-9" for e in task["evidence"]), r
