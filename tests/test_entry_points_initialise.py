"""The five entry-point commands initialise the project, and nothing else does.

A user's first Compass command should work in a repository that has never used
Compass. Four of the five role entry points wrote into `.compass/work/<slug>/`
while assuming somebody else had created it - `commands/intent.md` and
`commands/position.md` named the path, `wireframe.md` and `consult.md` did
not mention it at all.

These are checks on the COMMAND PROSE, because the commands are instructions to
an agent rather than code with a call site to assert on. What they check is
that each entry point tells the agent to initialise, and that the commands
which only read state do not.

Scenario ids: IOI-B1, IOI-C2, IOI-D2 in
.compass/work/init-is-the-opt-in/acceptance-criteria.md
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
COMMANDS = REPO_ROOT / "commands"

# Settled in requirements-review.md AMB-1: the five ways a user can arrive
# first. Every other command needs an issue a previous command created.
#
# `design` rather than `wireframe`: commands/design.md is the designer entry
# point that produces the UI contract, and commands/wireframe.md is the
# retired redirect stub that points at it. A stub does no work, so it has
# nothing to initialise for - it is in MUST_NOT_INITIALISE below.
ENTRY_POINTS = ["assess", "intent", "design", "position", "consult"]

# Commands that report on existing state, and the retired stubs that only
# forward a caller to the current name. Creating a directory because someone
# ran a read - or typed an old command name - is the silent-creation failure
# by another route.
MUST_NOT_INITIALISE = ["status", "flow", "wireframe"]

INIT_CALL = re.compile(r"compass init\b")


def _read(name):
    return (COMMANDS / f"{name}.md").read_text(encoding="utf-8")


def test_ioi_b1_every_entry_point_initialises_the_project():
    missing = [name for name in ENTRY_POINTS if not INIT_CALL.search(_read(name))]
    assert not missing, (
        "these entry-point commands never run `compass init`, so a user whose "
        "first Compass command is one of them lands in a project that was "
        f"never initialised: {', '.join(missing)}")


def test_ioi_b1b_every_entry_point_reports_that_it_initialised():
    """Silent creation is the failure mode, not missing creation.

    A .compass/ directory appearing with no word said is how someone deletes
    it by hand, or commits it without meaning to.
    """
    silent = []
    for name in ENTRY_POINTS:
        text = _read(name)
        m = INIT_CALL.search(text)
        if not m:
            continue
        # The instruction to say so should sit with the instruction to run it,
        # not three sections away where an agent will not connect them.
        window = text[max(0, m.start() - 400):m.end() + 400].lower()
        if not any(w in window for w in ("report", "say", "tell")):
            silent.append(name)
    assert not silent, (
        "these commands initialise the project without being told to say so: "
        f"{', '.join(silent)}")


def test_ioi_d2_reading_commands_do_not_initialise():
    """The boundary, and the one at risk of passing without proving anything.

    Commands that do not initialise today already do not, so this passes
    against HEAD before anything is built. Its red has to be demonstrated
    against a build that over-initialises - see technical-design.md DD-5.
    """
    offenders = [name for name in MUST_NOT_INITIALISE
                 if INIT_CALL.search(_read(name))]
    assert not offenders, (
        "these commands only report on existing state or forward to another "
        f"command, but tell the agent to initialise a project: "
        f"{', '.join(offenders)}. Creating a directory because someone ran a "
        "read, or typed a retired command name, is silent creation by another "
        "route.")


def test_ioi_c2_entry_points_do_not_run_the_governance_conversation():
    """Being initialised for you is small and reversible. Having governance/
    copied into your repository because you ran /compass:intent is not.

    Checked as an INSTRUCTION, not a mention: an entry point saying "adopting
    your own governance is what /compass:init offers separately" is telling the
    user where that lives, which is the opposite of doing it for them. What
    must not appear is an instruction to copy governance in.
    """
    adopt = re.compile(r"(copy|adopt).{0,40}governance/", re.I | re.S)
    offenders = [name for name in ENTRY_POINTS if adopt.search(_read(name))]
    assert not offenders, (
        f"these entry-point commands tell the agent to copy governance/ into "
        f"the project as part of starting work: {', '.join(offenders)}. "
        "Auto-initialisation creates project state only.")
