"""TRC-D1 - bdd-specification teaches the example-first refinement chain.
TRC-D2 - user stories remain refused as a per-role spec format.

Serves: INT-8 (D1), INT-8+INT-11 (D2)
Spec:
  - skills/bdd-specification/SKILL.md must have a refinement-chain section
  - the chain: vague idea → concrete examples → acceptance criteria → at least one executable specification each
  - recommends specs that start with "should" and a ubiquitous language
  - must refuse user stories as a per-role spec format (TRC-D2)
  - ADR-004 reference: the shared artifact stays as BDD scenario in spec.feature.md
"""
from __future__ import annotations
from pathlib import Path

SKILL_MD = Path(__file__).parent.parent / "skills" / "bdd-specification" / "SKILL.md"


def _read_skill() -> str:
    return SKILL_MD.read_text(encoding="utf-8")


# --- TRC-D1 tests ---

def test_bdd_spec_has_refinement_chain_section():
    """Must have a refinement-chain section (example-first)."""
    text = _read_skill()
    text_lower = text.lower()
    assert "refinement" in text_lower or "example-first" in text_lower or "refine" in text_lower, (
        "skills/bdd-specification/SKILL.md must contain an example-first refinement chain section. "
        f"Headings: {[l for l in text.splitlines() if l.startswith('#')]}"
    )


def test_refinement_chain_covers_vague_to_concrete():
    """The chain must go from vague idea → concrete examples."""
    text = _read_skill()
    text_lower = text.lower()
    assert "vague" in text_lower or "concrete examples" in text_lower, (
        "The refinement chain must describe moving from a vague idea to concrete examples."
    )


def test_refinement_chain_covers_examples_to_acceptance_criteria():
    """The chain must include acceptance criteria step."""
    text = _read_skill()
    text_lower = text.lower()
    assert "acceptance criteria" in text_lower or "acceptance criterion" in text_lower, (
        "The refinement chain must include an acceptance criteria step."
    )


def test_refinement_chain_covers_executable_spec():
    """The chain must lead to at least one executable specification."""
    text = _read_skill()
    text_lower = text.lower()
    assert "executable" in text_lower or "runnable" in text_lower, (
        "The refinement chain must mention executable specifications."
    )


def test_bdd_spec_recommends_should_prefix():
    """The section should recommend specs starting with 'should'."""
    text = _read_skill()
    text_lower = text.lower()
    assert '"should"' in text_lower or "'should'" in text_lower or "start with" in text_lower or "prefix" in text_lower, (
        "The bdd-specification skill should recommend using 'should' as a scenario prefix/convention. "
        "Look for mentions of 'should' as a naming convention."
    )


def test_bdd_spec_mentions_ubiquitous_language():
    """The section should recommend a ubiquitous language used consistently."""
    text = _read_skill()
    text_lower = text.lower()
    assert "ubiquitous" in text_lower or "ubiquitous language" in text_lower, (
        "The bdd-specification skill should mention ubiquitous language as a discipline."
    )


# --- TRC-D2 tests ---

def test_bdd_spec_refuses_user_stories_as_spec_format():
    """User stories must be refused as a per-role spec format."""
    text = _read_skill()
    text_lower = text.lower()
    assert "user stor" in text_lower, (
        "bdd-specification/SKILL.md must mention user stories (to refuse them as a per-role spec format). "
        "The refusal should be explicit."
    )
    # The skill must contain a refusal - words like "refused", "not", "reject"
    # near "user stories"
    lines = text.splitlines()
    user_story_context = []
    for i, line in enumerate(lines):
        if "user stor" in line.lower():
            start = max(0, i - 2)
            end = min(len(lines), i + 3)
            user_story_context.extend(lines[start:end])

    context_lower = " ".join(user_story_context).lower()
    assert any(word in context_lower for word in ["refus", "not a", "stays", "remain", "adr-004", "reject"]), (
        "The mention of user stories in bdd-specification must be in the context of refusing them. "
        f"Context found: {user_story_context}"
    )


def test_bdd_spec_shared_artifact_stays_bdd():
    """The spec.feature.md artifact must remain the shared BDD artifact."""
    text = _read_skill()
    text_lower = text.lower()
    assert "spec.feature.md" in text_lower, (
        "bdd-specification must confirm spec.feature.md stays as the shared BDD artifact."
    )
