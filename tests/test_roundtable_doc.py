"""Roundtable doc - Reassessment trigger section.

TRC-C4: commands/consult.md contains a "Reassessment trigger" section that
documents the requirement to run /compass:assess --reassess after boundary
or migration decisions.
"""

# The vocabulary rename landed on 2026-08-25: the assess and plan stages took
# the names their machine keys, skills and agents already used; `design` went
# back to the designer; design.md became technical-design.md and prd.md became
# intent.md. Spines and documents written before still load and resolve
# (ADR-006), so what moved is the CANONICAL spelling these tests assert - not
# what the framework computes. Re-pointed, not relaxed.
from __future__ import annotations

from pathlib import Path

FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent
ROUNDTABLE_DOC = FRAMEWORK_ROOT / "commands" / "consult.md"


def test_reframe_trigger_documented():
    """TRC-C4: consult.md has a Reassessment trigger section with required content."""
    assert ROUNDTABLE_DOC.is_file(), f"commands/consult.md not found at {ROUNDTABLE_DOC}"
    text = ROUNDTABLE_DOC.read_text(encoding="utf-8")

    # Section must exist
    assert "Reassessment trigger" in text, (
        "commands/consult.md is missing a 'Reassessment trigger' section. "
        "Add a section with this heading as per TRC-C4."
    )

    # Must state that boundary or migration decisions trigger a reframe
    lower = text.lower()
    assert "boundary" in lower or "migration" in lower, (
        "The Reassessment trigger section must mention 'boundary' or 'migration' decisions."
    )

    # Must show the concrete command
    assert "/compass:assess --reassess" in text, (
        "The Reassessment trigger section must show the example invocation: "
        "/compass:assess --reassess --reason \"...\""
    )

    # Must include --reason flag in the example
    assert "--reason" in text, (
        "The example invocation must include the --reason flag."
    )
