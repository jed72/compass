#!/usr/bin/env python3
# =============================================================================
# compass - a failure observed first
# =============================================================================
# A green record shows the suite passes; it does not show that a test ever
# failed. `suite-passed`, the check behind "tested before it lands"
# (guardrail `G1`), accepted any green, and an unbound green needs no red. So
# an issue could pass it having never seen a failure: 9 of 110 archived
# issues did, as the issue `unbound-green-needs-no-red` measured. This module
# holds the one extra condition `suite-passed` now applies.
#
# Kept apart from checks.py, which is near its line cap.
#
# DEPENDENCY: standard library only (datetime, json, os, stat). tdd.py
# imports from here, so this module must not import tdd.py.
# =============================================================================
"""Does an issue that declares scenarios show a failure observed first?"""
from __future__ import annotations

import datetime
import json
import os
import stat

#: Issues created on or after this date must show a failure first. Issues
#: created before it keep the result they had: their records say what was
#: required when they were written, and failing them now would rewrite that.
#: A manifest with no `created:` predates the field and counts as before.
RED_REQUIRED_FROM = datetime.date(2026, 9, 24)

#: The kinds `compass acceptance start` accepts, for work with no natural red.
#: Defined here, not in tdd.py, so the check and the verb read one list.
ACCEPTANCE_KINDS = ("validation", "refactor")


def _load(path):
    """A record's payload, or {} for anything that is not a JSON object in a
    regular file. A FIFO would block the read, and a symlink could stand
    another issue's record in for this one's."""
    try:
        mode = os.lstat(path).st_mode
    except OSError:
        return {}
    if not stat.S_ISREG(mode):
        return {}
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _is_failed_run(record):
    """True only for what `compass tdd-red` writes: `passed` false and an
    integer exit code that is not 0. Either field alone is not enough - a
    green record with `passed` flipped still says exit code 0."""
    code = record.get("exit_code")
    return (record.get("passed") is False and isinstance(code, int)
            and not isinstance(code, bool) and code != 0)


def has_red(task_dir):
    """Is a failed run on record? `compass tdd-red` writes `evidence/red.json`
    unbound and `evidence/red-<scenario>.json` bound. A red record is not
    registered in `evidence:`, so this reads the directory."""
    evidence = os.path.join(task_dir, "evidence")
    if os.path.islink(evidence):
        return False
    try:
        names = os.listdir(evidence)
    except OSError:
        return False
    return any(
        (name == "red.json" or (name.startswith("red-") and name.endswith(".json")))
        and _is_failed_run(_load(os.path.join(evidence, name)))
        for name in names)


def _has_acceptance(task, task_dir):
    """Is an acceptance record among the issue's test-run evidence? Only a
    path inside the issue directory counts."""
    root = os.path.realpath(task_dir)
    for entry in task.get("evidence") or []:
        if not isinstance(entry, dict) or entry.get("type") != "test-run":
            continue
        full = os.path.realpath(os.path.join(task_dir, entry.get("path") or ""))
        if os.path.commonpath([root, full]) != root:
            continue
        if _load(full).get("kind") in ACCEPTANCE_KINDS:
            return True
    return False


def _rule_applies(created):
    """Was the issue created on or after the cutoff? A missing or blank
    `created:` is the one exemption. A value that is present but not an ISO
    date is not trusted to mean "old", so the rule applies to it."""
    if isinstance(created, datetime.datetime):
        created = created.date()
    if isinstance(created, datetime.date):
        return created >= RED_REQUIRED_FROM
    text = "" if created is None else str(created).strip()
    if not text:
        return False
    try:
        return datetime.date.fromisoformat(text[:10]) >= RED_REQUIRED_FROM
    except ValueError:
        return True


def missing_first_failure(task, task_dir):
    """The failure message when the rule applies and is not met, else None."""
    if not task.get("scenarios") or not _rule_applies(task.get("created")):
        return None
    if has_red(task_dir) or _has_acceptance(task, task_dir):
        return None
    return ("the greens on record show the suite passes, but no red is on "
            "record for this issue, so nothing shows a test failed first. Run "
            "`compass tdd-red -- <test command>` on a failing test. For work "
            "with no natural red - config, docs, a behaviour-preserving "
            "refactor - declare it before the change with `compass "
            "acceptance start --kind validation|refactor -- <command>` and "
            "finish with `compass acceptance record`")
