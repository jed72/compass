#!/usr/bin/env python3
# =============================================================================
# compass - the two borrowed document shapes
# =============================================================================
# `threat-model.md` and `rollback-plan.md`, and the one check that reads them.
#
# Neither shape is ours. The threat model asks the Threat Modeling Manifesto's
# four questions (threatmodelingmanifesto.org) and answers each threat with a
# scenario id, which is the output form the ThoughtWorks Technology Radar names
# - "evil user stories" - and has had in Adopt since Nov 2015. The rollback plan
# records a REHEARSAL rather than a plan, because SWEBOK v4 §6.3.3 requires "a
# planned and rehearsed rollback" before a deploy and Dave Farley's answer to
# rollback is a mechanism you exercise rather than a document you write.
#
# It lives here rather than in checks.py because it reads those two templates
# and nothing else in checks.py touches them - the same reason the review
# page's currency check lives beside the page.
#
# DEPENDENCY: none. Python 3 standard library only - os and re. The YAML parser
# the rest of the package uses travels inside the plugin, so there is nothing
# to install either way.
# =============================================================================
"""Reading the threat model and the rollback plan for what each is for."""
from __future__ import annotations

import os
import re

from compass_pkg.check_results import NOTHING_TO_CHECK

# The shape the two borrowed templates write, and what "answered" means in
# each. A threat is answered by a scenario id or an explicit accepted risk; a
# rollback is answered by a rehearsal that happened.
_TRC_ID = re.compile(r"\bTRC-[A-Za-z0-9-]+\b")
_RISK_ACCEPTED = re.compile(r"risk\s+accepted", re.IGNORECASE)
_NOT_REHEARSED = re.compile(
    r"\b(not\s+yet|never|none|tbd|todo|n/?a|pending|planned)\b", re.IGNORECASE)


def _check_borrowed_documents_answered(task, task_dir):
    """The threat model and the rollback plan are answered, not just written.

    Both fail the same way - a section written and left unanswered - so one
    check reads whichever exists rather than two checks reading one each.

    A THREAT is answered by a `TRC-` scenario id, or by `risk accepted` with a
    reason. The Threat Modeling Manifesto names the failure this prevents:
    "Admiration for the Problem", a document that lists threats and mitigates
    none.

    A ROLLBACK is answered by a rehearsal that happened. SWEBOK v4 §6.3.3: "a
    planned and rehearsed rollback is done before a new version of the software
    is deployed in production." A rollback nobody has run is a guess, and a
    guess recorded as a plan is the assertion the evidence-not-assertion
    guardrail (`G4`) rejects.

    NEITHER FILE PRESENT RETURNS THE SENTINEL, NOT A PASS. Most issues earn
    neither document, and a guard reporting a clean result for work it never
    looked at is the failure this repository keeps finding.
    """
    threat = os.path.join(task_dir, "threat-model.md")
    rollback = os.path.join(task_dir, "rollback-plan.md")
    if not os.path.isfile(threat) and not os.path.isfile(rollback):
        return NOTHING_TO_CHECK, ("neither a threat model nor a rollback plan "
                                  "on this issue - the assessment earned "
                                  "neither, so there is nothing to read")

    findings, read = [], []

    if os.path.isfile(threat):
        read.append("threat-model.md")
        for row in _table_rows(threat):
            # A threat row is `| threat | answer |`. The answer column is the
            # one that has to carry a scenario id or an accepted risk.
            if len(row) < 2:
                continue
            name, answer = row[0], " ".join(row[1:])
            if not name or _is_table_furniture(name):
                continue
            if _TRC_ID.search(answer) or _RISK_ACCEPTED.search(answer):
                continue
            findings.append(
                "threat-model.md: %r names no scenario and no accepted risk"
                % _fit_threat(name))

    if os.path.isfile(rollback):
        read.append("rollback-plan.md")
        section = _section_after(rollback, "rehears")
        if section is None:
            findings.append(
                "rollback-plan.md: no section records when the rollback was "
                "rehearsed")
        elif not section.strip() or _NOT_REHEARSED.search(section):
            findings.append(
                "rollback-plan.md: the rehearsal section records no rehearsal "
                "- SWEBOK: a rollback is rehearsed before the deploy, and a "
                "plan nobody has run is a guess")

    if findings:
        return False, "; ".join(findings)
    return True, "%s answered" % " and ".join(read)


def _is_table_furniture(cell):
    """A header cell or a separator row, not a threat."""
    c = cell.strip().strip("*").lower()
    return (not c) or set(c) <= set("-: ") or c in {
        "threat", "what can go wrong", "what are we going to do about it",
        "scenario", "evidence"}


def _fit_threat(name, width=60):
    name = " ".join(name.split())
    return name if len(name) <= width else name[:width - 1] + "…"


def _table_rows(path):
    """Markdown table rows as lists of cells. Template placeholders are
    skipped: `{{...}}` is an unfilled example, not somebody's threat."""
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line.startswith("|") or "{{" in line:
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if cells:
                rows.append(cells)
    return rows


def _section_after(path, needle):
    """The body under the first heading containing `needle`, or None."""
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    body, found = [], False
    for line in text.splitlines():
        if line.startswith("#"):
            if found:
                break
            found = needle.lower() in line.lower()
            continue
        if found and not line.strip().startswith("<!--"):
            body.append(line)
    if not found:
        return None
    # Drop the instructional comment block, which is not somebody's answer.
    joined = "\n".join(body)
    return re.sub(r"<!--.*?-->", "", joined, flags=re.S)
