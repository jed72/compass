"""The docs stop implying that no project state is created.

`commands/init.md` opened with "**`/compass:init` is optional**" and
`CLAUDE.md` said "triage works with zero project setup". Both stay true in the
sense that matters - you never have to run init *before* your first real
command - but a reader who took them to mean no `.compass/` directory is
created was misled once the entry points began initialising for them.

Scenario ids: IOI-C1, IOI-C3 in
.compass/work/init-is-the-opt-in/acceptance-criteria.md
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _read(rel):
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


def test_ioi_c3_the_docs_say_the_project_is_initialised_for_you():
    """Both places that call init optional say what now happens instead."""
    missing = []
    for rel in ("commands/init.md", "CLAUDE.md"):
        text = _read(rel)
        if not re.search(r"compass init\b", text):
            missing.append(f"{rel}: never mentions the `compass init` verb")
            continue
        # The claim that matters: state IS created, by the command you ran.
        if not re.search(r"initialis(e|es|ed)[^.]{0,80}for you|creates? `?\.compass/",
                         text, re.I):
            missing.append(
                f"{rel}: does not say that a project is initialised for you")
    assert not missing, (
        "these documents still describe init as the step that creates project "
        "state, without saying it now happens on a user's first command:\n  "
        + "\n  ".join(missing))


def test_ioi_c3b_zero_project_setup_is_not_claimed_bare():
    """`CLAUDE.md`'s "zero project setup" needs its qualifier.

    Taken bare it says nothing is created, which is no longer true.

    Scoped to the paragraph the claim is IN. A character window either side
    reached `.compass/current-task` two paragraphs up and passed on text that
    had nothing to do with the claim - a check that could not fail, which is
    the pattern this repository keeps finding.
    """
    text = _read("CLAUDE.md")
    paragraphs = text.split("\n\n")
    claims = [p for p in paragraphs if re.search(r"zero project setup", p, re.I)]
    assert claims, "CLAUDE.md no longer makes the zero-project-setup claim at all"

    for para in claims:
        assert re.search(r"in the sense that matters|nothing for you to "
                         r"configure|initialis", para, re.I), (
            "CLAUDE.md claims zero project setup with nothing in the same "
            "paragraph to say that `.compass/` is created for the user on "
            "their first command:\n" + para)


def test_ioi_c1_the_slash_command_still_refuses_to_overwrite_governance():
    """The existing job keeps its guard. Only the framing moves."""
    text = _read("commands/init.md")
    assert re.search(r"do not overwrite|not overwrite", text, re.I), (
        "commands/init.md no longer refuses to overwrite live governance - "
        "that check is the reason the governance conversation is safe to "
        "re-run")
