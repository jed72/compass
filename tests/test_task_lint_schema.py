"""R3 - task lint's scenario schema agrees with the convention compass check
already accepts: `intent` may be a string OR a list of strings, and `group` +
`verifiable` are admitted optional fields. The widening is precise - a numeric
intent, or a list with a non-string element, still fails.
"""
from __future__ import annotations


def _body(scenario):
    return {
        "task": "lint", "created": "2026-06-22",
        "assessment": {"risk": "contained", "familiarity": "brownfield-mapped",
                     "size": "small", "intent": "delivery"},
        "scenarios": [scenario],
    }


def test_baseline_lint_check_disagree_on_corpus_shape(run_cli, make_task):
    """TRC-R3-1: the de-facto corpus shape (list intent + group + verifiable) is
    accepted by compass check's scenario-has-id-and-intent - the check side that
    the schema must be reconciled to."""
    make_task("r3-base", _body(
        {"id": "TRC-Z1", "intent": ["INT-1", "INT-2"], "group": "A",
         "verifiable": "narrative", "tests": []}))
    r = run_cli("check", "--task", "r3-base")
    line = next((l for l in (r.stdout + r.stderr).splitlines()
                 if "scenario-has-id-and-intent" in l), "")
    assert "PASS" in line, r


def test_corpus_shape_passes_after_fix(run_cli, make_task):
    """TRC-R3-2: the corpus shape that fails lint today passes after the schema
    is reconciled."""
    make_task("r3-corpus", _body(
        {"id": "TRC-Z1", "intent": ["INT-1", "INT-2"], "group": "A",
         "verifiable": "narrative", "tests": []}))
    r = run_cli("task", "lint", "--task", "r3-corpus")
    assert r.returncode == 0, r
    assert "PASS" in (r.stdout + r.stderr), r


def test_string_intent_still_passes(run_cli, make_task):
    """TRC-R3-3: a plain-string intent still lints clean (backward compat)."""
    make_task("r3-str", _body(
        {"id": "TRC-Z2", "intent": "INT-1", "tests": ["tests/test_x.py::test_y"]}))
    r = run_cli("task", "lint", "--task", "r3-str")
    assert r.returncode == 0, r


def test_numeric_intent_still_fails(run_cli, make_task):
    """TRC-R3-4: a numeric intent is still rejected - widened, not removed."""
    make_task("r3-num", _body({"id": "TRC-Z3", "intent": 7, "tests": []}))
    r = run_cli("task", "lint", "--task", "r3-num")
    assert r.returncode != 0, r
    assert "intent" in (r.stdout + r.stderr), r


def test_list_intent_non_string_element_fails(run_cli, make_task):
    """TRC-R3-5: a list intent with a non-string element is rejected."""
    make_task("r3-listbad", _body(
        {"id": "TRC-Z4", "intent": ["INT-1", 7], "tests": []}))
    r = run_cli("task", "lint", "--task", "r3-listbad")
    assert r.returncode != 0, r
    assert "intent" in (r.stdout + r.stderr), r
