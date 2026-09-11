"""CLAUDE.md tells a session to write plain English, with no idiom or metaphor.

Nothing mechanical reads a conversation, so what is checked here is the
instruction, not the writing. A session can have this rule in front of it and
still write "low-hanging fruit". These tests establish only that the rule is
where every session in this repository reads it.

Each test reads the "Plain English" section alone, up to the next heading. A
word such as "idiom" appearing somewhere else in the file must not satisfy it.

Scenario id PE-1, in
docs/compass/2026-09-11-claude-md-plain-english/delivery-approach.md.
"""
from __future__ import annotations

import re
from pathlib import Path

CLAUDE_MD = Path(__file__).resolve().parent.parent / "CLAUDE.md"
HEADING = "### Plain English"


def _section() -> str:
    """The section's text with whitespace collapsed, or "" when it is absent.

    The prose is hard-wrapped, so a phrase often straddles a line break.
    Collapsing whitespace keeps every word and its order.
    """
    text = CLAUDE_MD.read_text(encoding="utf-8")
    start = text.find("\n" + HEADING + "\n")
    if start == -1:
        return ""
    body = text[start + len(HEADING) + 2:]
    end = re.search(r"^#{1,6} ", body, re.M)
    return " ".join((body[: end.start()] if end else body).split())


def test_pe_1_claude_md_has_a_plain_english_section():
    assert _section(), f"CLAUDE.md has no '{HEADING}' section with text under it"


def test_pe_1_the_section_bans_idiom_and_metaphor():
    section = _section().lower()
    missing = [w for w in ("idiom", "metaphor", "say what happens") if w not in section]
    assert not missing, (
        f"the '{HEADING}' section does not say: {', '.join(missing)}. It must ban "
        "idiom and metaphor and tell the writer to state what happens instead.")


def test_pe_1_the_section_says_lead_with_the_point():
    section = _section().lower()
    missing = [w for w in ("lead with the point", "active voice") if w not in section]
    assert not missing, f"the '{HEADING}' section does not say: {', '.join(missing)}"
