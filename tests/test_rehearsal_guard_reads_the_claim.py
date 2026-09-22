"""The rollback rehearsal check reads the claim, not a word list.

Scenario RGN-1, in `rehearsal-guard-fails-on-a-neighbour/delivery-approach.md`.

The check reads the "When this was last rehearsed" section for a date, and
for an opening line that is not a denial. A denial word elsewhere in the
section, such as "Planned" in a table header, does not fail it.

A word-list match fails a real rehearsal on a neighbouring word, and the
author then rewords the section to get past the check.

The template asks for a date, a target, an outcome and a duration. So the
check reads for those: a date in the section, and an opening line that is not
a denial.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
COMPASS_CLI = ROOT / "cli" / "compass"

HEADING = "## When this was last rehearsed\n\n"

#: A completed rehearsal, written the way the template asks. The table header
#: is the one a word-list match fails on.
RECORDED = HEADING + """**Rehearsed on 2026-09-10**, against a copy taken that
morning.

| | Planned | Measured |
|---|---|---|
| Documents moved | 684 | 528 |
| Collisions | 0 | none |

Restored in 4m12s. Row counts matched on every table.
"""

#: The honest denial the template tells an author to write. Must still fail.
DENIED = HEADING + """**Not yet rehearsed.** The migration does not exist; this
plan is written at the design stage, before the code.
"""

#: A section with an outcome but no date - nothing says when it happened, so
#: there is no rehearsal on record.
UNDATED = HEADING + """Rehearsed against a copy. Restored cleanly, row counts
matched on every table.
"""


def _issue(tmp_path, rehearsal_section, slug="an-issue"):
    work = tmp_path / ".compass" / "work" / slug
    (work / "evidence").mkdir(parents=True)
    (tmp_path / ".compass" / "config.yml").write_text("version: 1.0.0\n",
                                                      encoding="utf-8")
    (work / "rollback-plan.md").write_text(
        "# Rollback plan\n\n## What this undoes\n\nThe move.\n\n"
        + rehearsal_section, encoding="utf-8")
    (work / "manifest.yml").write_text(yaml.safe_dump({
        "schema_version": "2.0", "issue": slug, "created": "2026-09-11",
        "status": "active",
        "assessment": {"risk": "critical", "familiarity": "brownfield-mapped",
                       "size": "small", "goal": "delivery", "role": "engineer",
                       "labels": ["migrations"]},
        "evidence": [], "gates": [], "scenarios": [], "changed_files": [],
        "claims": [], "follow_ups": [],
    }, sort_keys=False), encoding="utf-8")
    return work


def _check(project, slug="an-issue"):
    return subprocess.run(
        [sys.executable, str(COMPASS_CLI), "check", "--issue", slug,
         "--verbose"],
        capture_output=True, text=True, timeout=120, cwd=str(project))


def test_rgn_1_a_recorded_rehearsal_passes_beside_a_neighbouring_word(tmp_path):
    """A recorded rehearsal, with a table header a word-list match fails on:
    a table column headed `Planned`, and the word `none` as a collision
    count.

    Asserted against the WHOLE output. `compass check` prints the verdict on
    one line and the reason on the next, so a check that reads only the line
    naming the check passes while the reason beside it says it failed.
    """
    _issue(tmp_path, RECORDED)
    out = _check(tmp_path).stdout
    assert "records no rehearsal" not in out, (
        "a section recording a dated rehearsal was rejected, which is what "
        "teaches an author to reword around the guard:\n" + out[-1200:])


def test_rgn_1_a_denied_rehearsal_still_fails(tmp_path):
    """The control, in the template's own words. Reading the claim must not
    stop the check firing on a plan nobody has run."""
    r = _issue(tmp_path, DENIED) and _check(tmp_path)
    assert r.returncode != 0, (
        "a plan stating the rehearsal has not happened passed:\n"
        + r.stdout[-1200:])
    assert "records no rehearsal" in r.stdout, (
        "it failed for some other reason:\n" + r.stdout[-1200:])


def test_rgn_1_an_undated_rehearsal_fails(tmp_path):
    """"We rehearsed it" with no date is a claim, not a record.

    Without this, the check would accept any prose that avoids the denial
    words.
    """
    r = _issue(tmp_path, UNDATED) and _check(tmp_path)
    assert r.returncode != 0, (
        "a section claiming a rehearsal with no date passed:\n"
        + r.stdout[-1200:])


def test_rgn_1_a_missing_section_still_fails(tmp_path):
    """The third state, unchanged: no section at all."""
    r = _issue(tmp_path, "## Something else\n\nNot the section.\n") and _check(tmp_path)
    assert r.returncode != 0 and "no section records" in r.stdout, (
        "a rollback plan with no rehearsal section passed:\n"
        + r.stdout[-1200:])


def test_rgn_1_the_shipped_template_still_fails_unfilled(tmp_path):
    """The template ships with a placeholder. An author who writes nothing
    must be reported, or the check has stopped meaning anything for the case
    it is most likely to meet."""
    template = (ROOT / "templates" / "rollback-plan.md").read_text(
        encoding="utf-8")
    i = template.index("## When this was last rehearsed")
    r = _issue(tmp_path, template[i:]) and _check(tmp_path)
    assert r.returncode != 0, (
        "the unfilled template passes the rehearsal check:\n"
        + r.stdout[-1200:])
