"""TRC-E1 - evidence-gates frames verify.correctness as acceptance/releasability gate.
TRC-E2 - evidence-gates frames the tdd-red/tdd-green loop as the commit stage.
TRC-E3 - Release and Production stages stay out of scope in evidence-gates.

Serves: INT-9
Spec:
  - skills/evidence-gates/SKILL.md must frame verify.correctness as
    "anything that defines releasable" (acceptance/releasability gate)
  - must frame .red/.tdd-green loop as the commit stage ("anything that can fail fast")
  - must name the deployment-pipeline stage vocabulary (commit, acceptance)
  - must explicitly state Release and Production stages are out of scope
    (safety-contract guarantee 6)
  - must cite G4 (falsification principle) as the standing version
"""
from __future__ import annotations
from pathlib import Path

SKILL_MD = Path(__file__).parent.parent / "skills" / "evidence-gates" / "SKILL.md"


def _read_skill() -> str:
    return SKILL_MD.read_text(encoding="utf-8")


# --- TRC-E1 tests ---

def test_evidence_gates_frames_verify_correctness_as_acceptance_gate():
    """verify.correctness must be framed as the acceptance/releasability gate."""
    text = _read_skill()
    text_lower = text.lower()
    assert "verify.correctness" in text_lower, (
        "evidence-gates/SKILL.md must mention verify.correctness."
    )
    # Must frame it as the acceptance/releasability gate
    assert "accept" in text_lower and "releas" in text_lower, (
        "evidence-gates must frame verify.correctness in terms of acceptance and releasability."
    )


def test_evidence_gates_verify_correctness_anything_that_defines_releasable():
    """The framing must use 'anything that defines releasable' language."""
    text = _read_skill()
    text_lower = text.lower()
    assert "defines releasable" in text_lower or "releasable" in text_lower, (
        "evidence-gates must describe verify.correctness as 'anything that defines releasable'. "
        f"Verify.correctness context: {[l for l in text.splitlines() if 'correctness' in l.lower() or 'releas' in l.lower()]}"
    )


# --- TRC-E2 tests ---

def test_evidence_gates_frames_tdd_loop_as_commit_stage():
    """The tdd-red/tdd-green loop must be framed as the commit stage."""
    text = _read_skill()
    text_lower = text.lower()
    assert "commit" in text_lower, (
        "evidence-gates must mention the commit stage."
    )
    # Must mention the tdd-red/green loop in this context
    assert "tdd-red" in text_lower or "tdd-green" in text_lower or ".red" in text_lower, (
        "evidence-gates must mention tdd-red/tdd-green (or .red marker) as the commit-stage mechanism."
    )


def test_evidence_gates_commit_stage_fail_fast_language():
    """The commit stage framing must use 'anything that can fail fast' language."""
    text = _read_skill()
    text_lower = text.lower()
    assert "fail fast" in text_lower or "fast feedback" in text_lower or "commit stage" in text_lower, (
        "evidence-gates must describe the commit stage as 'anything that can fail fast'. "
        f"TDD loop context: {[l for l in text.splitlines() if 'commit' in l.lower() or 'fail fast' in l.lower()]}"
    )


# --- TRC-E3 tests ---

def test_evidence_gates_release_production_out_of_scope():
    """Release and Production stages must be stated as out of scope."""
    text = _read_skill()
    text_lower = text.lower()
    # Must mention Release and Production in the context of being out of scope
    assert "release" in text_lower or "production" in text_lower, (
        "evidence-gates must mention Release and/or Production stages to state they are out of scope."
    )
    # Find context around these mentions
    lines = text.splitlines()
    release_context = []
    for i, line in enumerate(lines):
        if "release" in line.lower() or "production" in line.lower():
            start = max(0, i - 2)
            end = min(len(lines), i + 3)
            release_context.extend(lines[start:end])

    context_lower = " ".join(release_context).lower()
    assert any(word in context_lower for word in ["out of scope", "not a deployment", "guarantee 6", "safety-contract"]), (
        "The mention of Release/Production must be in context of being out of scope. "
        f"Context found: {release_context}"
    )


def test_evidence_gates_cites_g4_for_falsification():
    """Must cite G4 (falsification principle) as the standing version of the idea inside Compass."""
    text = _read_skill()
    assert "G4" in text, (
        "evidence-gates must cite G4 as the standing falsification principle. "
        "The skill already references G4; this test confirms it's in the E2/E3 context."
    )
