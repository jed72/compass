"""Consult doc - Reassessment trigger section.

`TRC-C4`: commands/consult.md contains a "Reassessment trigger" section that
says to run /compass:assess --reassess after boundary or migration
decisions.
"""

# These tests assert the current file names; files written under older
# names still load (ADR-006).
from __future__ import annotations

from pathlib import Path

FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent
CONSULT_DOC = FRAMEWORK_ROOT / "commands" / "consult.md"


def test_reframe_trigger_documented():
    """`TRC-C4`: consult.md has a Reassessment trigger section with required content."""
    assert CONSULT_DOC.is_file(), f"commands/consult.md not found at {CONSULT_DOC}"
    text = CONSULT_DOC.read_text(encoding="utf-8")

    # Section must exist
    assert "Reassessment trigger" in text, (
        "commands/consult.md is missing a 'Reassessment trigger' section. "
        "Add a section with this heading as per TRC-C4."
    )

    # Must state that boundary or migration decisions trigger a reassessment
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
