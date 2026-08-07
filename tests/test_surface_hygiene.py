"""Surface hygiene (task executable-bdd-and-richer-plans).

Two pieces of tidying that the Superpowers comparison surfaced:

  * `skills/constitution-check/` is a tombstone. Compass replaced the single
    "constitution" model with strategies and guardrails, and the skill has
    redirected to `governance-check` ever since. Nothing loads it. A dead skill
    in the plugin's skill list costs a reader attention every time they scan it.

  * Specify's inline self-review and the Clarify phase overlap, and neither
    file said so. A reader meeting both wonders which one is redundant. They
    are not: the self-review is four cheap scans the author owes Clarify, and
    Clarify does the work that needs a decision. Writing the split down in both
    places is the fix.

Spec: .compass/work/executable-bdd-and-richer-plans/spec.feature.md
      (TRC-D1..D4, TRC-F7).
"""
from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
BDD_SKILL = SKILLS / "bdd-specification" / "SKILL.md"
CLARIFY_CMD = ROOT / "commands" / "refine.md"

# The four scans the spec-author runs inline at the end of Specify.
FOUR_SCANS = ["placeholder", "orphan", "untestable", "ambiguous"]


# ---------------------------------------------------------------------------
# TRC-D1 - the superseded skill is gone
# ---------------------------------------------------------------------------

def test_trc_d1_constitution_check_skill_deleted():
    assert not (SKILLS / "constitution-check").exists(), (
        "skills/constitution-check/ still exists; it is a tombstone that "
        "redirects to governance-check and is loaded by nothing"
    )
    assert (SKILLS / "governance-check" / "SKILL.md").is_file(), (
        "governance-check must survive - it is what constitution-check "
        "redirected to"
    )


# ---------------------------------------------------------------------------
# TRC-D2 - nothing points at the deleted skill
# ---------------------------------------------------------------------------

SEARCHED_SUFFIXES = {".md", ".yml", ".yaml", ".json", ".py", ".sh"}
# .compass/, docs/proposals/ and docs/analysis/ are gitignored local working
# notes, not part of the shipped framework. They record what Compass looked
# like when they were written - including that this skill was still on disk -
# and rewriting history to match the present would destroy their value.
SKIPPED_DIRS = {".git", "__pycache__", ".compass", "dist", "node_modules",
                "proposals", "analysis"}


def _repo_files():
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix not in SEARCHED_SUFFIXES:
            continue
        if any(part in SKIPPED_DIRS for part in path.parts):
            continue
        yield path


def test_trc_d2_no_references_to_deleted_skill():
    """No file may point at constitution-check as a skill to load.

    Prose about the historic "constitution" model is fine and expected -
    governance/README.md explains what Compass replaced. What must not survive
    is a pointer to a skill that no longer exists.
    """
    offenders = []
    for path in _repo_files():
        # This file necessarily names the string it hunts for, the same way
        # `compass design lint` has to exempt the documents that explain it.
        if path.resolve() == pathlib.Path(__file__).resolve():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for i, line in enumerate(text.splitlines(), 1):
            if "constitution-check" not in line:
                continue
            offenders.append(f"{path.relative_to(ROOT)}:{i}: {line.strip()}")

    assert not offenders, (
        "these still reference the deleted constitution-check skill:\n  "
        + "\n  ".join(offenders)
    )


# ---------------------------------------------------------------------------
# TRC-D3 - the specification skill states what it leaves to Clarify
# ---------------------------------------------------------------------------

def test_trc_d3_bdd_skill_documents_the_split():
    text = BDD_SKILL.read_text(encoding="utf-8").lower()

    for scan in FOUR_SCANS:
        assert scan in text, (
            f"the bdd-specification skill does not name the {scan!r} scan"
        )

    # it must say what Clarify does that the self-review does not
    # "Clarify" became "the requirements review" with the skills-prose
    # slice; the required statement is the same, in the v2 words.
    assert re.search(
        r"(?:requirements )?review (?:still )?(?:does|runs|resolves|hunts)",
        text), (
        "the skill never says what work the requirements review does that "
        "the inline self-review does not"
    )
    # and which routes run each
    assert "express" in text and re.search(r"standard", text), (
        "the skill does not say which routes run the inline self-review and "
        "which run Clarify"
    )


# ---------------------------------------------------------------------------
# TRC-D4 - the clarify command states the same split from its side
# ---------------------------------------------------------------------------

def test_trc_d4_clarify_command_documents_the_split():
    text = CLARIFY_CMD.read_text(encoding="utf-8").lower()

    assert "self-review" in text or "self review" in text, (
        "commands/refine.md never mentions the inline self-review the "
        "spec-author has already run, so Clarify looks like it starts from "
        "nothing"
    )
    assert re.search(r"(does not repeat|not repeat|already (been )?run|already "
                     r"covered|no need to re-?run)", text), (
        "commands/refine.md does not say that Clarify does not repeat the "
        "inline scans"
    )
    # it names the same four scans the skill names
    for scan in FOUR_SCANS:
        assert scan in text, (
            f"commands/refine.md does not name the {scan!r} scan; the two "
            f"descriptions of the split must agree"
        )


# ---------------------------------------------------------------------------
# TRC-F7 - the skill count does not grow on net
# ---------------------------------------------------------------------------

def test_trc_f7_skill_count_unchanged_on_net():
    """One skill in, one out.

    Compass grows by adding artifacts and skills rather than guardrails or
    routing dimensions (architecture/decisions/ADR-002), and every new
    user-facing concept is meant to be scrutinised before it lands. This makes
    the arithmetic a checked fact rather than a claim.

    This is a cross-stream assertion: `plan-authoring` arrives with the richer
    plans work and `constitution-check` leaves with this one. It can only be
    true of the integrated result.
    """
    present = {p.name for p in SKILLS.iterdir()
               if p.is_dir() and (p / "SKILL.md").is_file()}

    assert "plan-authoring" in present, "plan-authoring was not added"
    assert "constitution-check" not in present, (
        "constitution-check was not removed")

    # A LIVING allowlist, in the same spirit as EXPECTED_PUBLIC_SUBCOMMANDS: no
    # skill appears or disappears without a deliberate edit here. It is not a
    # freeze on the count - a later task may add skills, and two did:
    # systematic-debugging and receiving-code-review, from
    # phase-2-skills-check-and-cli-split. What this task asserted, and what
    # still holds, is that IT added one and removed one.
    expected = {
        "adaptive-routing", "bdd-specification", "blueprint-distillation",
        "compass-runtime", "evidence-gates", "flow-management",
        "governance-check", "plan-authoring", "role-translation",
        "tdd-discipline", "traceability", "worktree-swarm",
        "receiving-code-review", "systematic-debugging",   # phase-2 task
    }
    assert present == expected, (
        "the skill set changed without this allowlist being updated.\n"
        f"  unexpected: {sorted(present - expected)}\n"
        f"  missing   : {sorted(expected - present)}"
    )
    assert len(present) == len(expected), (
        f"expected {len(expected)} skills, found {len(present)}")
