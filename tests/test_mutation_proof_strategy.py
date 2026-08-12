"""Mutation proof is standing practice, not this cycle's habit.

The 2.1.0 release found five guards that reported success while checking
nothing, and four of them had passing tests the whole time. A passing test
proves the guard runs. It does not prove the guard is connected to the thing
it names.

The case that settles it: `test_version_guard_covers_every_location.py` was
written specifically to close that class, passed its own tests, and performed
zero comparisons on the single location it existed for. Setting both version
banners to `9.9.9` left it green. Nothing but breaking the subject would have
shown that.

Spec: .compass/work/mutation-proof-standing/acceptance-criteria.md.
"""
from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
STRATEGIES = ROOT / "governance" / "strategies.md"
VERIFY_COMMAND = ROOT / "commands" / "verify.md"
EVIDENCE_GATES = ROOT / "skills" / "evidence-gates" / "SKILL.md"


def _flat(text: str) -> str:
    """Whitespace-collapsed, so an assertion about what the prose says does
    not break when a paragraph is re-wrapped. Three assertions in this
    repository have broken that way already."""
    return " ".join(text.split())


def _strategy_entry() -> str:
    """The mutation-proof strategy's own section.

    Found by its heading rather than by body text, so a coincidental match
    elsewhere in the file cannot grab the wrong section.
    """
    text = STRATEGIES.read_text(encoding="utf-8")
    for section in re.split(r"(?m)^### ", text)[1:]:
        heading = section.split("\n", 1)[0]
        if "mutation" in heading.lower():
            return "### " + section
    return ""


def test_trc_1_the_strategy_states_the_method_and_the_reason():
    entry = _strategy_entry()
    assert entry, (
        "no strategy in governance/strategies.md states the mutation-proof "
        "practice"
    )
    flat = _flat(entry).lower()

    assert re.search(r"\bS\d+\b", entry.split("\n", 1)[0]), (
        "the heading must carry an S-number, matching the file's convention"
    )

    # The four steps, and they must be one method rather than four words
    # scattered through the section. The first version of this assertion
    # checked each word independently and survived deleting the method
    # sentence entirely - "failure", "passing test" and "recorded" all occur
    # elsewhere in the entry. Caught by applying S10 to S10's own test.
    method = re.search(
        r"break[^.]*?\bred\b[^.]*?restore[^.]*?\bgreen\b[^.]*?record",
        flat,
    )
    assert method, (
        "the strategy does not state the method as one instruction - break "
        "the subject, watch it go red, restore, watch it go green, record "
        "the result. Scattered mentions of those words are not the method."
    )

    # The reason, which is the part that makes the rule stick.
    assert "passing test" in flat, (
        "the strategy must say what a passing test does and does not prove"
    )
    assert "record" in flat, (
        "the strategy must require the result to be recorded, not just done"
    )

    assert "*Why a strategy and not a guardrail:*" in entry, (
        "the entry must carry the file's own convention"
    )


def test_trc_2_the_verify_guidance_points_at_the_strategy():
    entry = _strategy_entry()
    match = re.search(r"`(S\d+)`", entry.split("\n", 1)[0])
    assert match, "TRC-1 must land before this scenario can"
    s_number = match.group(1)

    for name, path in (("commands/verify.md", VERIFY_COMMAND),
                       ("skills/evidence-gates/SKILL.md", EVIDENCE_GATES)):
        text = _flat(path.read_text(encoding="utf-8"))
        assert s_number in text, (
            f"{name} does not name {s_number}, so a reviewer at the verify "
            f"stage has no pointer to the practice"
        )
