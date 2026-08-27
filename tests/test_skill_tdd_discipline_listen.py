"""TRC-C2 - tdd-discipline contains a "Listen to your tests" section.
TRC-C3 - tdd-discipline contains a "test behaviour, not implementation" anti-pattern.

Serves: INT-6
Spec:
  - skills/tdd-discipline/SKILL.md must have a section on "Listen to your tests"
  - that section says: a hard-to-write test is a design smell - change the design, not the test
  - must have an anti-pattern about testing behaviour not implementation
  - the anti-pattern includes "swap the implementation - does the test survive?"
"""
from __future__ import annotations
from pathlib import Path

SKILL_MD = Path(__file__).parent.parent / "skills" / "tdd-discipline" / "SKILL.md"

def _skill_text(skill_name):
    """Everything the skill says, across every file in its directory.

    A skill used to be one file. The long ones are now split - the parts load
    when they are needed instead of the whole thing loading to answer one
    question - so a guard that reads only SKILL.md reports content missing
    when it has merely moved next door.

    The strings each guard looks for are unchanged. Only where it looks has
    widened, and deleting the content still fails.
    """
    import pathlib as _p
    d = _p.Path(__file__).parent.parent / "skills" / skill_name
    return "\n".join(sorted(
        p.read_text(encoding="utf-8") for p in d.glob("*.md")))



def _read_skill() -> str:
    return _skill_text("tdd-discipline")


# --- TRC-C2 tests ---

def test_tdd_discipline_has_listen_to_tests_section():
    """Must have a section titled in the spirit of 'Listen to your tests'."""
    text = _read_skill()
    text_lower = text.lower()
    assert "listen to your tests" in text_lower, (
        "skills/tdd-discipline/SKILL.md must contain a 'Listen to your tests' section. "
        f"Section headings found: {[l for l in text.splitlines() if l.startswith('#')]}"
    )


def test_tdd_discipline_listen_section_has_design_smell_message():
    """The Listen section must say: a hard-to-write test is a design smell - change the design."""
    text = _read_skill()
    text_lower = text.lower()
    assert "hard-to-write" in text_lower or "hard to write" in text_lower, (
        "The 'Listen to your tests' section must say a hard-to-write test is a design smell."
    )
    assert "design smell" in text_lower or "design problem" in text_lower, (
        "The section must explicitly name the concept of a design smell."
    )
    # Must say change the design, not the test
    assert "change the design" in text_lower or "redesign" in text_lower or "the design" in text_lower, (
        "The section must advise: change the design, not the test."
    )


# --- TRC-C3 tests ---

def test_tdd_discipline_has_behaviour_not_implementation_antipattern():
    """Must have an anti-pattern about testing behaviour, not implementation."""
    text = _read_skill()
    text_lower = text.lower()
    assert "behaviour" in text_lower or "behavior" in text_lower, (
        "tdd-discipline must contain 'behaviour' (or 'behavior')."
    )
    assert "implementation" in text_lower, (
        "tdd-discipline must contain 'implementation'."
    )
    # Must have the concept together
    assert (
        "test behaviour" in text_lower
        or "behaviour, not implementation" in text_lower
        or "behavior, not implementation" in text_lower
        or "test behavior" in text_lower
    ), (
        "tdd-discipline must contain an anti-pattern about testing behaviour not implementation."
    )


def test_tdd_discipline_swap_implementation_check():
    """The anti-pattern must include the 'swap the implementation' check."""
    text = _read_skill()
    text_lower = text.lower()
    assert "swap" in text_lower, (
        "tdd-discipline must include the 'swap the implementation - does the test survive?' check."
    )
    assert "survive" in text_lower, (
        "The swap check must ask 'does the test survive?'"
    )
