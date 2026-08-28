"""The instructions that govern what a session says to a person.

The plain-language rule names three surfaces: what the tool prints, what it
writes into documents, and what the assistant says. The first two have checks.
The third cannot have one - nothing mechanical reads a conversation - so what is
checked here is the *instruction*, not the reply.

BE CLEAR ABOUT WHAT THAT BUYS. A session can carry all four headings and write
jargon underneath every one of them, and nothing in this file would notice. What
these tests establish is that the rule exists where the speaker reads it, and
that two shipped instructions do not tell a session opposite things.

Scenario ids trace to .compass/work/agent-speech-is-unchecked/
acceptance-criteria.md.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ALWAYS_LOADED = REPO_ROOT / "CLAUDE.md"
VOICE_SKILL = REPO_ROOT / "skills" / "compass-runtime" / "writing-voice.md"
AGENTS = REPO_ROOT / "AGENTS.md"


def _prose(path: Path) -> str:
    """File text with whitespace collapsed.

    The prose here is hard-wrapped, so a phrase that is genuinely present
    routinely straddles a line break and fails a plain substring test. This
    normalises the wrapping, not the phrase: every word still has to be there,
    in order.
    """
    return " ".join(path.read_text(encoding="utf-8").split())


# The six terms a cold reader could not read, quoted from the bug report. Each
# entry is (the shorthand, a word that must appear in its plain form) - the
# second is what stops an entry being the term listed against itself.
REPORTED_TERMS = [
    ("papercuts", "irritation"),
    ("work the issue owes", "outstanding"),
    ("stale green", "record"),
    ("keys only on", "who"),
    ("full weight", "properly"),
    ("borrowed process weight", "skipped"),
]



def _tell_seven(prose: str) -> str:
    """Just tell #7's own entry, not its neighbours.

    An earlier version read a fixed 700-character window from the start of the
    tell, which ran into tell #8 - "restating the request before *answering*
    it". So a check for the word "answer" passed on a neighbouring entry while
    tell #7 itself was untouched. The window now ends where the next numbered
    tell begins.
    """
    idx = prose.index("headings inside conversation")
    rest = prose[idx:]
    end = re.search(r"\s\d+\.\s+\*\*", rest)
    return rest[:end.start()] if end else rest


# ---------------------------------------------------------------------------
# Group A - the reply shape, where a session reads it
# ---------------------------------------------------------------------------

def test_a1_reply_shape_is_in_the_always_loaded_instructions():
    """TRC-A1: the always-loaded instructions state the four-part reply shape.

    Not only the skill. A rule about speaking applies to every reply, including
    those in a session that never loads the skill - and this ruling spent eight
    days recorded in a place no session reads, which is the defect being fixed.
    """
    # Read the bullet list itself, not the whole file. Mutation MP-1 renamed a
    # bullet and this passed anyway, because the same phrase appears in the
    # sentence explaining why the shape works - so the test was confirming that
    # the words exist somewhere, not that they are the shape.
    text = ALWAYS_LOADED.read_text(encoding="utf-8")
    bullets = " ".join(
        l.strip() for l in text.splitlines() if l.lstrip().startswith("- **"))
    for part in ("what I did", "outstanding questions",
                 "what I need from you", "what I intend to do next"):
        assert part.lower() in bullets.lower(), (
            f"{ALWAYS_LOADED.name} does not list the reply-shape part "
            f"{part!r} as one of the four, so a session that never loads the "
            f"voice skill is told nothing about how to report")


def test_a2_the_three_rules_are_stated():
    """TRC-A2: the shape carries its three rules.

    The shape without them is four headings over the same buried prose.
    """
    prose = _prose(ALWAYS_LOADED).lower()
    assert "short" in prose, "the instruction does not say to keep sections short"
    assert "snippet" in prose, (
        "the instruction does not say to put a snippet under the point it "
        "belongs to")
    assert "number" in prose, (
        "the instruction does not say to number the questions")


def test_a3_length_tension_is_resolved():
    """TRC-A3: the length tension is resolved rather than left open.

    "Keep each section short" collides with a change that genuinely has a lot in
    it. If the instruction does not say what to cut, the next reader cuts
    substance.
    """
    prose = _prose(ALWAYS_LOADED).lower()
    assert "never the substance" in prose or "not the substance" in prose, (
        "the instruction says to keep sections short and never says what to cut "
        "when a change is genuinely large - so the reader will cut findings")


# ---------------------------------------------------------------------------
# Group B - the terms that leak
# ---------------------------------------------------------------------------

def test_b1_leaky_terms_have_plain_forms():
    """TRC-B1: the list gives each term a plain-English form beside it."""
    prose = _prose(VOICE_SKILL)
    assert re.search(r"plain", prose, re.IGNORECASE), (
        "the voice skill carries no list of terms with plain forms")
    for term, plain_word in REPORTED_TERMS:
        assert term.lower() in prose.lower(), (
            f"the list does not carry the term {term!r}")


def test_b2_list_covers_the_six_reported_terms():
    """TRC-B2: every term the cold reader named has a plain form, and the plain
    form is not the term restated.

    A list that names a term and then explains it in the same vocabulary has
    added nothing - that is the failure mode of a glossary written by someone
    fluent in the jargon.
    """
    # Each term's plain form has to be on that term's own row. Searching the
    # whole file passed a mutation that replaced one row's plain form with more
    # jargon, because the word it looked for occurred in an unrelated sentence.
    rows = [l for l in VOICE_SKILL.read_text(encoding="utf-8").splitlines()
            if l.lstrip().startswith("|")]
    missing = []
    for term, plain_word in REPORTED_TERMS:
        row = next((r for r in rows if term.lower() in r.lower()), None)
        if row is None or plain_word.lower() not in row.lower():
            missing.append(term)
    assert not missing, (
        "these terms have no plain-English form on their own row, so the entry "
        "restates the jargon rather than translating it: "
        + ", ".join(repr(t) for t in missing))


# ---------------------------------------------------------------------------
# Group C - the moment
# ---------------------------------------------------------------------------

def test_c1_rule_is_attached_to_a_moment():
    """TRC-C1: the rule names when to apply it.

    This project has learned that a rule with no moment attached is advice, and
    that a judgement has not landed until it reaches the actor at the moment of
    acting. This issue exists because a ruling was recorded and reached none.
    """
    prose = _prose(ALWAYS_LOADED).lower()
    assert "before you report" in prose, (
        "the instruction does not name the moment to apply it, so it is advice "
        "rather than a rule attached to a point in the work")
    before = prose.index("before you report")
    after = prose.find("afterwards", before)
    assert after != -1 and after - before < 300, (
        "the instruction names a moment but does not distinguish it from doing "
        "the check after the reply is written")


# ---------------------------------------------------------------------------
# Group D - the two instructions stop disagreeing
# ---------------------------------------------------------------------------

def test_d1_tell_seven_distinguishes_label_from_answer():
    """TRC-D1: the headings tell separates a label from an answer.

    Tell #7 is real and is not being deleted - "## Summary" over a summary is
    still worth catching. What it lacked is the line separating that from a
    heading that answers a question the reader already has.
    """
    prose = _prose(VOICE_SKILL)
    assert "headings inside conversation" in prose, (
        "tell #7 is gone - narrowing it was the decision, not deleting it")
    entry = _tell_seven(prose).lower()
    assert "label" in entry, (
        "the tell does not name the kind of heading it is against - one "
        "labelling the prose beneath it")
    assert "answers a question the reader" in entry, (
        "the tell does not say that a heading answering a question the reader "
        "has is not the tell, so it still forbids the reply shape")


def test_d2_instructions_do_not_contradict_each_other():
    """TRC-D2: a session following every instruction can satisfy them all.

    This asserts an absence, which is the easiest thing to satisfy without
    checking anything - so it asserts a positive fact instead: the file that
    forbids headings must also carry the exemption. Tell #7 present without its
    narrowing IS the contradiction.
    """
    voice = _prose(VOICE_SKILL)
    if "headings inside conversation" in voice:
        entry = _tell_seven(voice).lower()
        assert "answers a question the reader" in entry, (
            "the voice skill forbids headings in conversation while the "
            "always-loaded instructions require a four-heading reply shape - a "
            "session cannot follow both")

    # And nothing else may forbid them outright.
    for path in (ALWAYS_LOADED, AGENTS):
        if not path.is_file():
            continue
        prose = _prose(path).lower()
        for banned in ("never use headings", "do not use headings",
                       "avoid headings in"):
            assert banned not in prose, (
                f"{path.name} says {banned!r}, which contradicts the reply "
                f"shape the same instructions require")


def test_a4_portable_instructions_carry_the_shape():
    """TRC-A4: the runtime-neutral instructions carry the shape too.

    `AGENTS.md` is the portable expression of Compass for any other agent
    runtime, and its voice section already covers "replies to the person driving
    it". A rule about reporting that lands only in the Claude adapter tells every
    other runtime nothing - which is the same defect this issue exists to fix.
    """
    prose = _prose(AGENTS)
    for part in ("what I did", "outstanding questions",
                 "what I need from you", "what I intend to do next"):
        assert part.lower() in prose.lower(), (
            f"AGENTS.md does not name the reply-shape part {part!r}, so a "
            f"non-Claude runtime is told nothing about how to report")
