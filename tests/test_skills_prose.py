"""Slice 6 of the v2 rename: the skills and agents speak the v2 register.

The twelve pending skills and the ten agent definitions are rewritten in
the frozen v2 vocabulary; `skills/` leaves both pending lists and
`agents/` enters `scan.surfaces` as an enforced, never-pending surface -
the same shape as the root instruction files. The worktree-swarm skill
gains the queued "never stash across a worktree hop" rule, and the lens
ban pattern is tuned so agent identifiers (machine names like
`product-lens`, which keep their spelling until an agent-rename decision)
no longer collide with the banned role-perspective concept word.
"""
from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).parent.parent


def _scan_cfg() -> dict:
    return yaml.safe_load(
        (REPO_ROOT / "governance" / "terminology.yml").read_text(
            encoding="utf-8"))["scan"]


def test_skills_surface_is_enforced():
    """TRC-1: skills/ has left pending_surfaces and the committed
    baseline - its banned terms are build failures from here on."""
    from test_terminology import PENDING_BASELINE
    scan = _scan_cfg()
    assert "skills/" not in scan["pending_surfaces"], (
        "skills/ is still pending in terminology.yml - slice 6's "
        "definition of done includes de-pending it")
    assert "skills/" not in PENDING_BASELINE, (
        "skills/ is still in the committed baseline - the ratchet shrinks "
        "in the same diff that cleans the surface")


def test_agents_surface_is_enforced_never_pending():
    """TRC-2: agents/ is scanned and enforced from the day it was
    rewritten - present in surfaces, absent from both pending lists."""
    from test_terminology import PENDING_BASELINE
    scan = _scan_cfg()
    assert "agents/" in scan["surfaces"], (
        "agents/ is not a scanned surface - ten agent definitions teach "
        "every session unscanned")
    assert "agents/" not in scan["pending_surfaces"], (
        "agents/ must arrive clean, never pending")
    assert "agents/" not in PENDING_BASELINE, (
        "agents/ must never enter the pending baseline")


def test_worktree_swarm_carries_the_stash_rule():
    """TRC-3: the lesson moved from the slice-3a issue's devlog into the
    skill where future sessions will read it."""
    text = (REPO_ROOT / "skills" / "worktree-swarm" / "SKILL.md").read_text(
        encoding="utf-8").lower()
    assert "never stash across a worktree hop" in text, (
        "the worktree-swarm skill does not state the stash rule")
    assert "destroys the stashed work" in text, (
        "the stash rule is stated without its reason - a rule with no why "
        "gets deleted by the first person it inconveniences")


def test_lens_ban_catches_concept_not_identifiers():
    """TRC-4: the ban still catches 'lens' as the role-perspective
    concept, but a hyphenated agent identifier is machine vocabulary and
    passes - the fixture pair proves both sides."""
    from test_terminology import BAN_PATTERNS
    patterns = BAN_PATTERNS["lens"]
    concept = "read the spec through the marketing lens before shipping"
    assert any(p.search(concept) for p in patterns), (
        "the lens ban no longer catches the role-perspective concept")
    identifier = "invoke the product-lens agent when a PRD exists"
    assert not any(p.search(identifier) for p in patterns), (
        "a hyphenated agent identifier is flagged - those names are "
        "machine vocabulary until an agent-rename decision retires them")
