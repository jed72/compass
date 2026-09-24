"""The 5.0.0 upgrade notes name what a 4.x caller must change (issue release-5-0-0).

5.0.0 is a major release because two skills were removed: `traceability`
merged into `evidence-gates`, and `role-translation` merged into
`intent-interview`. A session or an agent file that loads a removed skill by
name stops finding it. `docs/releasing.md` is where someone upgrading looks,
so each removed name must sit in a table row beside the name that replaced
it - a loose mention elsewhere in the file does not help a reader match the
name that failed to the one that works.

The same release moved issue documents to `docs/compass/<created>-<slug>/`.
Old manifests still resolve by a fallback, and `compass migrate` moves them,
so the notes must name that command.

Scenario id: `REL-3` in release-5-0-0's delivery-approach.md.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS = REPO_ROOT / "skills"
RELEASING = REPO_ROOT / "docs" / "releasing.md"

REMOVED_SKILLS = {
    "traceability": "evidence-gates",
    "role-translation": "intent-interview",
}


def _section_5_0_0() -> str:
    body = RELEASING.read_text(encoding="utf-8")
    match = re.search(r"^### What changed at 5\.0\.0\n(.*?)(?=^#{1,3} )",
                      body, re.M | re.S)
    assert match, "docs/releasing.md has no '### What changed at 5.0.0' section"
    return match.group(1)


def test_rel_3_each_removed_skill_has_an_upgrade_row():
    section = _section_5_0_0()
    for removed, replacement in sorted(REMOVED_SKILLS.items()):
        # The table is only true while the removal holds on disk. If a removed
        # skill comes back, or its replacement goes, the row is wrong.
        assert not (SKILLS / removed / "SKILL.md").exists(), (
            f"skills/{removed}/SKILL.md exists, so the 5.0.0 notes wrongly "
            f"say it was removed")
        assert (SKILLS / replacement / "SKILL.md").is_file(), (
            f"skills/{replacement}/SKILL.md is missing, so the 5.0.0 notes "
            f"point a reader at a skill that does not exist")
        row = re.compile(r"^\|\s*`%s`[^|]*\|\s*`%s`[^|]*\|"
                         % (re.escape(removed), re.escape(replacement)), re.M)
        assert row.search(section), (
            f"The 5.0.0 notes have no table row pairing `{removed}` with "
            f"`{replacement}`")


def test_rel_3_the_notes_say_how_to_move_issue_documents():
    section = _section_5_0_0()
    assert "compass migrate" in section, (
        "The 5.0.0 notes do not name `compass migrate`, which moves issue "
        "documents to docs/compass/")
