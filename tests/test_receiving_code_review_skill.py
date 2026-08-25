"""The receiving-code-review skill (task phase-2-skills-check-and-cli-split).

Small and focused: how to answer a reviewer without either capitulating to a
wrong suggestion or digging in against a right one. Compass already has a
`reviewer` agent and a `verifier`; nothing described the other side of that
conversation.

Spec: .compass/work/phase-2-skills-check-and-cli-split/acceptance-criteria.md (TRC-B1..B3).
"""
from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "receiving-code-review" / "SKILL.md"


def _body(path):
    parts = path.read_text(encoding="utf-8").split("---", 2)
    return parts[2] if len(parts) >= 3 else parts[0]


def test_trc_b1_a_suggestion_should_be_checked_against_the_code_before_it_is_acted_on():
    assert SKILL.is_file(), "skills/receiving-code-review/SKILL.md does not exist"
    body = _body(SKILL)

    assert re.search(r"verify|check|confirm", body, re.I), (
        "the skill never tells the engineer to verify a suggestion")
    m = re.search(r"(verify|check|confirm)[^.]{0,120}(against|in) the code",
                  body, re.I)
    assert m, ("the skill does not require checking the suggestion against the "
               "code before implementing it")

    # it must name the failure it prevents, or it reads as generic advice
    assert re.search(r"(without checking|agree|sycophan|you'?re absolutely right)",
                     body, re.I), (
        "the skill does not name agreeing-without-checking as the failure mode "
        "it exists to prevent")


def test_trc_b2_the_skill_should_shape_disagreement_rather_than_forbid_it():
    body = _body(SKILL)

    assert re.search(r"push back|disagree|challenge", body, re.I), (
        "the skill never permits disagreement, so it teaches capitulation")
    m = re.search(r"(push back|disagree|challenge)[^.]{0,160}", body, re.I)
    assert re.search(r"reason|evidence|technical|because|why", m.group(0), re.I), (
        f"disagreement is permitted but unshaped - it must be grounded in "
        f"technical reasoning, not preference: {m.group(0)!r}")

    assert not re.search(r"defer to (the )?(reviewer|senior)", body, re.I), (
        "the skill tells the engineer to defer on authority, which is the "
        "behaviour it is meant to replace")


def test_trc_b3_the_skill_should_be_short_enough_to_be_read_at_the_moment_of_use():
    body = _body(SKILL)
    words = len(body.split())
    assert words < 500, (
        f"the skill is {words} words. A method nobody reads while a review is "
        f"open is not a method; the improvement plan asked for 200-300 words.")
    assert words > 80, (
        f"the skill is {words} words - too thin to say anything actionable")
