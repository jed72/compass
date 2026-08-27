"""The public surface does not carry stale references or wrong claims.

Four items, each counted against HEAD before this file was written. Most of
what the comparison review listed under this heading was already paid by the
documentation slimming pass, which landed after the review was taken - the
delivery-approach record has the table.

What remained:

- `approaches/README.md` linked five files that do not exist.
- `CLAUDE.md` and `AGENTS.md` said the CLI's verbs and artifact filenames keep
  their v1 names "until their rename slice ships". Those slices shipped.
- `docs/routing-deep-dive.md` named the immovable gates as correctness,
  governance, regression and claims. The policy's are correctness, governance
  and traceability - regression is approach-scoped and claims is role-scoped.

Scenario ids: VOC-A1, VOC-B1, VOC-C1, VOC-C2 in
.compass/work/vocabulary-debt/acceptance-criteria.md
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
APPROACHES = ROOT / "approaches"
POLICY = ROOT / "governance" / "routing-policy.yml"
DEEP_DIVE = ROOT / "docs" / "routing-deep-dive.md"

LINK = re.compile(r"\[[^\]]+\]\(([^)]+\.md)\)")
BACKTICKED = re.compile(r"`([a-z0-9][a-z0-9-]*\.md)`")


def test_voc_a1_every_file_the_approaches_index_names_exists():
    """A reader following a link to a renamed delivery approach gets nothing.

    Five were dead: router.md, express.md, standard.md, expedition.md - four
    approaches that were renamed - and delivery-approach.md, which is the
    per-issue artifact and was never a file here at all.
    """
    index = APPROACHES / "README.md"
    assert index.is_file(), "approaches/README.md is gone"
    text = index.read_text(encoding="utf-8")

    named = sorted(set(LINK.findall(text)) | set(BACKTICKED.findall(text)))
    assert named, (
        "approaches/README.md names no other file at all, so this check is "
        "passing over nothing")

    dead = [n for n in named if not (index.parent / n).is_file()]
    assert not dead, (
        "approaches/README.md points a reader at files that do not exist: "
        + ", ".join(dead))


def test_voc_b1_no_document_says_a_shipped_rename_is_still_pending():
    """The claim was true when written and stopped being true when the slices
    landed. A reader believing it looks for v1 names that are gone."""
    stale = re.compile(r"until (?:their|its|the)[^.\n]*(?:rename )?slices? ships?",
                       re.I)
    offenders = []
    for rel in ("CLAUDE.md", "AGENTS.md", "README.md",
                "skills/compass-runtime/SKILL.md"):
        p = ROOT / rel
        if not p.is_file():
            continue
        for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if stale.search(line):
                offenders.append(f"{rel}:{n}")
    assert not offenders, (
        "these say a rename slice has not shipped yet, and it has: "
        + ", ".join(offenders))


def _policy_immovable_gates():
    doc = yaml.safe_load(POLICY.read_text(encoding="utf-8"))
    for key in ("policy", "routing", None):
        node = doc.get(key) if key else doc
        if isinstance(node, dict) and "immovable_gates" in node:
            return [g["gate"] for g in node["immovable_gates"]]
    # nested one level deeper in some shapes
    for v in doc.values():
        if isinstance(v, dict) and "immovable_gates" in v:
            return [g["gate"] for g in v["immovable_gates"]]
    raise AssertionError("routing-policy.yml has no immovable_gates block")


def _immovable_claim():
    """The gates routing-deep-dive.md CLAIMS are immovable.

    The parenthesised list immediately after the phrase, not the surrounding
    prose. Two anchors were wrong before this one:

    - the first "immovable gates" mention is a sentence about stapling that
      names no gate, so anchoring there passed over empty text;
    - a 400-character window around the right mention catches the sentences
      that explain which gates are NOT immovable, so correct prose failed.

    The claim is the list. That is what this reads.
    """
    text = DEEP_DIVE.read_text(encoding="utf-8")
    m = re.search(r"immovable gates?\b[^(]{0,40}\(([^)]*)\)", text, re.I | re.S)
    assert m, (
        "docs/routing-deep-dive.md no longer lists the immovable gates as a "
        "parenthesised set - this check would pass over nothing")
    return m.group(1)


def test_voc_c1_the_deep_dive_names_the_gates_the_policy_actually_staples():
    """The item that matters. The others mislead a reader; this one misstates
    what the framework enforces, in the document opened to learn how
    enforcement works.
    """
    gates = _policy_immovable_gates()
    assert gates, "the policy staples no immovable gates"

    claimed = _immovable_claim()

    missing = [g for g in gates if g not in claimed]
    assert not missing, (
        f"routing-deep-dive.md's immovable-gate list omits {', '.join(missing)}, "
        f"which the policy staples onto every delivery approach:\n{claimed}")


def test_voc_c2_the_deep_dive_does_not_claim_scoped_gates_are_immovable():
    """`verify.regression` is approach-scoped and `verify.claims` is
    role-scoped. The policy says so in as many words, and listing either as
    immovable tells a reader a quick fix runs a gate it does not."""
    gates = set(_policy_immovable_gates())
    claimed = _immovable_claim()

    wrongly_claimed = [g for g in ("verify.regression", "verify.claims")
                       if g in claimed and g not in gates]
    assert not wrongly_claimed, (
        "routing-deep-dive.md lists these as immovable when the policy scopes "
        f"them: {', '.join(wrongly_claimed)}. A reader is told a quick fix "
        "runs a gate it does not.")
