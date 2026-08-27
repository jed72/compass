"""R6 - gate-evidence type mismatches are reported in one enumerated pass, and
route evaluate seeds the gates block with each gate's accepted evidence types.
"""

# These tests read `compass check`'s PER-CHECK detail - a check's name,
# its PASS/FAIL and the reason it gave. That detail moved to --verbose on
# 2026-08-24 when the gate verdict came under the terminal output contract;
# the checks themselves are unchanged. The assertions are re-pointed rather
# than rewritten, because what they assert still holds - only where it is
# printed changed.
from __future__ import annotations

import yaml


def _body(gates, evidence):
    return {
        "task": "ge",
        "created": "2026-06-22",
        "assessment": {"risk": "contained", "familiarity": "brownfield-mapped",
                     "size": "small", "intent": "delivery"},
        "delivery_approach": "standard",
        "scenarios": [{"id": "SCN-1", "intent": "INT-1",
                       "tests": ["tests/test_x.py::test_y"]}],
        "evidence": evidence,
        "gates": gates,
        "changed_files": [],
    }


def _mk(task_dir, rel):
    p = task_dir / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("{}")


def test_mismatch_surfaces_at_check_baseline(run_cli, make_task):
    """TRC-R6-1 (baseline): a wrong-type gate-evidence is reported by check with
    the gate id, accepted types, and the actual type."""
    body = _body(
        [{"id": "verify.governance", "status": "pass", "evidence": ["EV-T"]}],
        [{"id": "EV-T", "type": "test-run", "path": "evidence/green.json"}],
    )
    task_dir = make_task("ge-base", body)
    _mk(task_dir, "evidence/green.json")
    r = run_cli("check", "--verbose", "--issue", "ge-base")
    assert r.returncode != 0, r
    combined = r.stdout + r.stderr
    assert "verify.governance" in combined and "test-run" in combined, r


def test_check_accumulates_both_gate_problems_baseline(run_cli, make_task):
    """TRC-R6-2 (baseline): two wrong-type gates → both appear (check does not
    stop at the first)."""
    body = _body(
        [{"id": "verify.governance", "status": "pass", "evidence": ["EV-T"]},
         {"id": "verify.claims", "status": "pass", "evidence": ["EV-MR"]}],
        [{"id": "EV-T", "type": "test-run", "path": "evidence/green.json"},
         {"id": "EV-MR", "type": "manual-review", "path": "evidence/rev.md"}],
    )
    task_dir = make_task("ge-both", body)
    _mk(task_dir, "evidence/green.json")
    _mk(task_dir, "evidence/rev.md")
    r = run_cli("check", "--verbose", "--issue", "ge-both")
    assert r.returncode != 0, r
    combined = r.stdout + r.stderr
    assert "verify.governance" in combined and "verify.claims" in combined, r


def test_two_bad_gates_show_two_enumerated_failures(run_cli, make_task):
    """TRC-R6-5: the two mismatches are enumerated one per line (not collapsed
    behind each other into one dense string)."""
    body = _body(
        [{"id": "verify.governance", "status": "pass", "evidence": ["EV-T"]},
         {"id": "verify.claims", "status": "pass", "evidence": ["EV-MR"]}],
        [{"id": "EV-T", "type": "test-run", "path": "evidence/green.json"},
         {"id": "EV-MR", "type": "manual-review", "path": "evidence/rev.md"}],
    )
    task_dir = make_task("ge-enum", body)
    _mk(task_dir, "evidence/green.json")
    _mk(task_dir, "evidence/rev.md")
    r = run_cli("check", "--verbose", "--issue", "ge-enum")
    assert r.returncode != 0, r
    combined = r.stdout + r.stderr
    gov_lines = [ln for ln in combined.splitlines() if "verify.governance" in ln]
    claims_lines = [ln for ln in combined.splitlines() if "verify.claims" in ln]
    # each offending gate is named on its own line, not concatenated into one
    assert gov_lines and claims_lines, r
    assert not any("verify.governance" in ln and "verify.claims" in ln
                   for ln in combined.splitlines()), r


def test_seeded_gates_carry_accepted_type_comments(run_cli, make_task):
    """TRC-R6-6: route evaluate --write annotates each gate with its accepted
    evidence types."""
    body = {
        "task": "ge-seed", "created": "2026-06-22",
        "assessment": {"risk": "contained", "familiarity": "brownfield-mapped",
                     "size": "small", "intent": "delivery"},
    }
    task_dir = make_task("ge-seed", body)
    r = run_cli("approach", "evaluate", "--issue", "ge-seed", "--write")
    assert r.returncode == 0, r
    text = (task_dir / "manifest.yml").read_text()
    assert "accepts:" in text, r
    # verify.regression accepts exactly [test-run]
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        if "verify.regression" in ln:
            ctx = "\n".join(lines[max(0, i - 2):i + 1])
            assert "test-run" in ctx, (ctx, r)
            break


def test_task_template_gates_document_accepted_types(framework_root):
    """TRC-R6-6 (doc half): templates/manifest.yml documents the accepted-types
    convention in its gates block."""
    text = (framework_root / "templates" / "manifest.yml").read_text()
    assert "accepts:" in text, "templates/manifest.yml gates block should document accepted evidence types"
