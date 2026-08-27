"""TRC-C5 - the coverage-floor example carries the floor-never-target caveat.

Serves: INT-7
Spec:
  - governance/guardrails.yml coverage-floor example must carry a caveat
  - caveat: a floor, never a target - coverage is a side effect of test discipline, not a goal
  - skills/evidence-gates/SKILL.md must also carry the coverage caveat paragraph
"""
from __future__ import annotations
from pathlib import Path

GUARDRAILS_YML = Path(__file__).parent.parent / "governance" / "guardrails.yml"
EVIDENCE_GATES = Path(__file__).parent.parent / "skills" / "evidence-gates" / "SKILL.md"

def _evidence_gates_text():
    """Everything the evidence-gates skill says, across its whole directory.

    The skill was split so its parts load when needed - the review-dimension
    checklists, the evidence vocabulary, the fitness-function detail and the
    coverage notes are siblings of SKILL.md now. A guard reading only SKILL.md
    reports content missing when it has moved next door.

    The strings below are unchanged; only where they are looked for widened.
    """
    import pathlib as _p
    d = _p.Path(__file__).resolve().parent.parent / "skills" / "evidence-gates"
    return "\n".join(sorted(p.read_text(encoding="utf-8") for p in d.glob("*.md")))



def test_guardrails_coverage_floor_has_caveat():
    """governance/guardrails.yml coverage-floor example must carry the floor-never-target caveat."""
    text = GUARDRAILS_YML.read_text(encoding="utf-8")
    text_lower = text.lower()
    # Must have the key phrase
    assert "floor" in text_lower and "target" in text_lower, (
        "guardrails.yml must mention both 'floor' and 'target' near the coverage example."
    )
    assert "never a target" in text_lower or "not its goal" in text_lower or "side effect" in text_lower, (
        "guardrails.yml coverage-floor example must carry the caveat: "
        "'a floor, never a target' or 'side effect of test discipline'. "
        f"Coverage-related content: {[l for l in text.splitlines() if 'coverage' in l.lower()]}"
    )


def test_evidence_gates_has_coverage_caveat():
    """skills/evidence-gates/SKILL.md must also carry the coverage caveat paragraph."""
    text = _evidence_gates_text()
    text_lower = text.lower()
    assert "coverage" in text_lower, (
        "evidence-gates/SKILL.md must mention coverage."
    )
    assert "floor" in text_lower, (
        "evidence-gates/SKILL.md must mention the coverage 'floor' concept."
    )
    assert "target" in text_lower or "goal" in text_lower, (
        "evidence-gates/SKILL.md must say coverage is not a target/goal."
    )
    assert "side effect" in text_lower or "never a target" in text_lower or "not a target" in text_lower, (
        "evidence-gates/SKILL.md must say coverage is a side effect (floor, never a target). "
        f"Coverage lines: {[l for l in text.splitlines() if 'coverage' in l.lower()]}"
    )
