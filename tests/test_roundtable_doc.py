"""Roundtable doc — Reframe trigger section.

TRC-C4: commands/roundtable.md contains a "Reframe trigger" section that
documents the requirement to run /compass:frame --reframe after boundary
or migration decisions.
"""
from __future__ import annotations

from pathlib import Path

FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent
ROUNDTABLE_DOC = FRAMEWORK_ROOT / "commands" / "roundtable.md"


def test_reframe_trigger_documented():
    """TRC-C4: roundtable.md has a Reframe trigger section with required content."""
    assert ROUNDTABLE_DOC.is_file(), f"commands/roundtable.md not found at {ROUNDTABLE_DOC}"
    text = ROUNDTABLE_DOC.read_text(encoding="utf-8")

    # Section must exist
    assert "Reframe trigger" in text, (
        "commands/roundtable.md is missing a 'Reframe trigger' section. "
        "Add a section with this heading as per TRC-C4."
    )

    # Must state that boundary or migration decisions trigger a reframe
    lower = text.lower()
    assert "boundary" in lower or "migration" in lower, (
        "The Reframe trigger section must mention 'boundary' or 'migration' decisions."
    )

    # Must show the concrete command
    assert "/compass:frame --reframe" in text, (
        "The Reframe trigger section must show the example invocation: "
        "/compass:frame --reframe --reason \"...\""
    )

    # Must include --reason flag in the example
    assert "--reason" in text, (
        "The example invocation must include the --reason flag."
    )
