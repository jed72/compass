#!/usr/bin/env python3
# =============================================================================
# compass - evidence identity
# =============================================================================
# Does a registry entry still name the record it was created from?
#
# Split out of checks.py, which is the check registry and had grown past this
# project's 1200-line guard. The split follows a real boundary: everything here
# is about the relationship between a citation and the file it cites, which is
# a different concern from the guardrail checks that consume it.
#
# The write side lives in compass_pkg.tdd (`_stamp_identity`). The two halves
# have to agree on the field names and nothing else, which is why they can sit
# in different modules.
#
# DEPENDENCY: PyYAML, bundled at cli/vendor/yaml/ and pinned in
# THIRD-PARTY-NOTICES.md. It is resolved by compass_pkg/__init__.py and is
# the only third-party code Compass ships; everything else is the Python 3
# standard library. This module uses none of it - json and os only.
# =============================================================================
"""Verifying that a cited evidence record is the one that was recorded."""
from __future__ import annotations

import json
import os

from compass_pkg.check_results import NOTHING_TO_CHECK


def _check_evidence_identity_matches(task, task_dir):
    """Is each registry entry still naming the record it was created from?

    THE QUESTION THIS ASKS THAT NOTHING ASKED BEFORE. A registry entry is a
    path, and `gate-evidence-present` confirms the path resolves. Neither
    established that the file at that path is the run the entry was made for.
    So a record replaced after it was cited left every check green: three gates
    on `zero-friction-install` rested on an eleven-test run of one file, and two
    landed issues are still in that state.

    Two stamps, two different failures:
      record_id      - unique per write. A different one means the file is a
                       different record under the same name.
      content_digest - over the payload. A matching record_id with a different
                       digest means this record was edited in place.

    A record written before stamping existed carries neither. That is
    UNVERIFIABLE, not a pass and not a failure: an unstamped record cannot be
    checked against its citation, and calling it verified would be a check that
    cannot fail. Where nothing in the issue is stamped, the whole check returns
    NOTHING_TO_CHECK so it is counted apart from the passes rather than
    inflating them.
    """
    registry = [e for e in (task.get("evidence") or []) if isinstance(e, dict)]
    if not registry:
        return NOTHING_TO_CHECK, "no evidence recorded yet - nothing to verify"

    problems, verified, unverifiable = [], 0, 0
    for entry in registry:
        ev_id = entry.get("id", "?")
        claimed = entry.get("record_id")
        if not claimed:
            unverifiable += 1
            continue
        path = entry.get("path")
        if not path:
            problems.append(f"{ev_id}: carries a record_id but no path")
            continue
        full = path if os.path.isabs(path) else os.path.join(task_dir, path)
        if not os.path.isfile(full):
            # gate-evidence-present owns the resolves-or-not question; not
            # repeating its failure here would leave this one silent on it.
            unverifiable += 1
            continue
        try:
            record = json.load(open(full, encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            problems.append(f"{ev_id}: {path} could not be read ({exc})")
            continue
        actual = record.get("record_id")
        if actual != claimed:
            problems.append(
                f"{ev_id} was created from record {claimed} but {path} now "
                f"holds record {actual or '(unstamped)'} - the file was "
                f"replaced after it was cited"
            )
            continue
        claimed_digest = entry.get("content_digest")
        actual_digest = record.get("content_digest")
        if claimed_digest and actual_digest != claimed_digest:
            problems.append(
                f"{ev_id}: {path} is the right record but its contents changed "
                f"after it was cited - it was edited in place"
            )
            continue
        verified += 1

    if problems:
        return False, "; ".join(problems)
    if not verified:
        return NOTHING_TO_CHECK, (
            f"{unverifiable} evidence record(s) carry no identity - they were "
            f"written before records were stamped, so their citations cannot "
            f"be verified. This checked nothing"
        )
    note = (f", {unverifiable} unverifiable (written before records were "
            f"stamped)") if unverifiable else ""
    return True, f"{verified} citation(s) match the record they name{note}"
