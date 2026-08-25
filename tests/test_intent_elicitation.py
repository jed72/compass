"""Reshaping an ingested brief into intent.md - the rules, made checkable.

The maintainer's instruction was "never take it verbatim, ask questions where
needed", so Compass rewrites someone else's document. That is the whole value
and the whole danger: an invented non-goal reads exactly like a decided one,
and a reader cannot tell them apart afterwards.

`requirements-review.md` Q2 turned that into a rule a test can hold - **every
statement in intent.md traces to the source or to a recorded answer, and there
is no third origin** - and this file is where it is held. The skill teaches the
discipline; the validator below is what makes the discipline checkable rather
than aspirational.

Scenario ids: ING-B1..B4 in
.compass/work/ingest-an-existing-brief/acceptance-criteria.md
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "cli"))

import compass_pkg  # noqa: E402,F401
from compass_pkg.core import CompassError  # noqa: E402

SKILL = REPO_ROOT / "skills" / "intent-elicitation" / "SKILL.md"


def _issue(tmp_path, sections, elicitation, intent_body, source="# src\n\nA.\n"):
    """An issue that has been ingested and reshaped, ready to validate."""
    work = tmp_path / ".compass" / "work" / "demo"
    work.mkdir(parents=True)
    (tmp_path / ".compass" / "config.yml").write_text("version: 1.0.0\n")
    (work / "intent-source.md").write_text(source, encoding="utf-8")
    (work / "intent.md").write_text(intent_body, encoding="utf-8")
    (work / "task.yml").write_text(yaml.safe_dump({
        "schema_version": "2.0", "task": "demo", "created": "2026-08-25",
        "status": "active",
        "intent_source": {
            "origin": "brief.md", "scheme": "file", "sha256": "0" * 64,
            "ingested_at": "2026-08-25T00:00:00+00:00",
            "snapshot": "intent-source.md",
            "sections": sections,
            "elicitation": elicitation,
        },
    }, sort_keys=False))
    return work


# ---------------------------------------------------------------------------
# ING-B3 - nothing is invented. The rule, held mechanically.
# ---------------------------------------------------------------------------

def test_ing_b3_a_section_with_no_recorded_origin_is_refused(tmp_path):
    """The rule's whole point: a statement nobody made must not pass.

    This is the failure the rule exists for - a plausible non-goal, written
    because it sounded right. It reads exactly like a decided one, so nothing
    but a recorded origin can tell them apart.
    """
    from compass_pkg.ingest import validate_intent_origins

    work = _issue(
        tmp_path,
        sections=[{"name": "problem", "from": "source"}],
        elicitation=[],
        intent_body="## Problem\n\nSearch is slow.\n\n"
                    "## Non-goals\n\nWe will not rebuild the index.\n")

    ok, detail = validate_intent_origins(str(work))
    assert not ok, "a section with no recorded origin was accepted"
    assert "non-goals" in detail.lower(), detail


def test_ing_b3b_an_answer_origin_must_name_an_answer_that_exists(tmp_path):
    """`from: answer` pointing at nothing is the same failure, dressed up.

    Without this, the origin record becomes a formality: write `from: answer`
    beside anything and the check clears. A citation is only as good as the
    thing it points at - the same rule the archive-citation guard holds.
    """
    from compass_pkg.ingest import validate_intent_origins

    work = _issue(
        tmp_path,
        sections=[{"name": "problem", "from": "source"},
                  {"name": "non-goals", "from": "answer", "answer_id": "Q9"}],
        elicitation=[{"id": "Q1", "question": "what is out?", "answer": "the index"}],
        intent_body="## Problem\n\nA.\n\n## Non-goals\n\nNot the index.\n")

    ok, detail = validate_intent_origins(str(work))
    assert not ok
    assert "Q9" in detail, detail


def test_ing_b3c_a_declined_question_may_not_be_cited_as_an_answer(tmp_path):
    """An unanswered question is not a source of material.

    The sharpest version of the rule. The question was asked, the person
    declined - and material appearing under that section anyway is invention
    with a paper trail, which is worse than invention without one because it
    looks audited.
    """
    from compass_pkg.ingest import validate_intent_origins

    work = _issue(
        tmp_path,
        sections=[{"name": "problem", "from": "source"},
                  {"name": "non-goals", "from": "answer", "answer_id": "Q1"}],
        elicitation=[{"id": "Q1", "question": "what is out?", "answer": None}],
        intent_body="## Problem\n\nA.\n\n## Non-goals\n\nNot the index.\n")

    ok, detail = validate_intent_origins(str(work))
    assert not ok
    assert "declin" in detail.lower() or "unanswered" in detail.lower(), detail


def test_ing_b3d_a_fully_traced_document_passes(tmp_path):
    """The control. Without it, a validator that refused everything would pass
    all three tests above while making the feature unusable."""
    from compass_pkg.ingest import validate_intent_origins

    work = _issue(
        tmp_path,
        sections=[{"name": "problem", "from": "source"},
                  {"name": "non-goals", "from": "answer", "answer_id": "Q1"}],
        elicitation=[{"id": "Q1", "question": "what is out?",
                      "answer": "rebuilding the index"}],
        intent_body="## Problem\n\nSearch is slow.\n\n"
                    "## Non-goals\n\nRebuilding the index.\n")

    ok, detail = validate_intent_origins(str(work))
    assert ok, detail


# ---------------------------------------------------------------------------
# ING-B4 - declining every question still produces a document
# ---------------------------------------------------------------------------

def test_ing_b4_a_declined_section_says_so_and_the_document_stands(tmp_path):
    """The loop must not become a wall.

    Someone in a hurry, or without the answers to hand, still needs to start.
    A section they declined is recorded as unanswered and says so in words -
    which is a finished document, not an unfinished one.
    """
    from compass_pkg.ingest import validate_intent_origins

    work = _issue(
        tmp_path,
        sections=[{"name": "problem", "from": "source"},
                  {"name": "non-goals", "from": "unanswered", "answer_id": "Q1"}],
        elicitation=[{"id": "Q1", "question": "what is out?", "answer": None}],
        intent_body="## Problem\n\nSearch is slow.\n\n## Non-goals\n\n"
                    "No non-goals were stated in the source, and none were "
                    "supplied when asked.\n")

    ok, detail = validate_intent_origins(str(work))
    assert ok, detail


def test_ing_b4b_an_unanswered_section_may_not_hide_behind_tbd(tmp_path):
    """`TBD` and "asked, declined" are different states.

    `TBD` reads as "someone will get to this", and `compass plan lint` scans
    for it as an unfinished placeholder. A section that was asked about and
    deliberately left open is finished - and only one of the two is true.
    """
    from compass_pkg.ingest import validate_intent_origins

    work = _issue(
        tmp_path,
        sections=[{"name": "problem", "from": "source"},
                  {"name": "non-goals", "from": "unanswered", "answer_id": "Q1"}],
        elicitation=[{"id": "Q1", "question": "what is out?", "answer": None}],
        intent_body="## Problem\n\nA.\n\n## Non-goals\n\nTBD\n")

    ok, detail = validate_intent_origins(str(work))
    assert not ok
    assert "tbd" in detail.lower(), detail


def test_ing_b1_the_document_is_reshaped_not_copied(tmp_path):
    """ING-B1: intent.md must not be the snapshot under another name.

    The cheapest way to satisfy every other rule here is to copy the source
    verbatim - every statement traces, trivially. That is exactly what the
    maintainer ruled out, so it is refused.
    """
    from compass_pkg.ingest import validate_intent_origins

    body = "## Problem\n\nSearch is slow.\n"
    work = _issue(
        tmp_path,
        sections=[{"name": "problem", "from": "source"}],
        elicitation=[],
        intent_body=body,
        source=body)

    ok, detail = validate_intent_origins(str(work))
    assert not ok, "intent.md is byte-identical to the source and was accepted"
    assert "identical" in detail.lower() or "verbatim" in detail.lower(), detail


def test_ing_b2_the_skill_requires_asking_rather_than_writing_tbd():
    """ING-B2: the discipline itself, which no validator can hold.

    A validator can refuse `TBD`. It cannot make anyone ASK - so that half
    lives in the skill, and this checks the skill says it. Weak evidence, and
    named as such: prose can satisfy a regex and still teach nothing.
    """
    assert SKILL.is_file(), "no intent-elicitation skill"
    text = SKILL.read_text(encoding="utf-8").lower()

    for needle, why in (
            ("one question at a time", "the questioning discipline P0-C specifies"),
            ("tbd", "the rule against writing TBD instead of asking"),
            ("decline", "the person's right to decline every question"),
            ("invent", "the rule that nothing is invented")):
        assert needle in text, (
            "the skill does not mention %s (%s)" % (needle, why))


def test_ing_b2b_the_skill_steps_aside_when_intake_already_exists():
    """P0-C's own open question, which this issue is the answer to.

    "Does the elicitation loop annoy experienced users who arrive with a
    finished PRD? It must step aside instantly when intake already exists."
    A loop that interrogates someone who already has a complete brief is the
    failure mode, not a thorough one.
    """
    text = SKILL.read_text(encoding="utf-8").lower()
    assert "step aside" in text or "steps aside" in text, (
        "the skill does not say it steps aside when the source already "
        "carries what the template asks for")
