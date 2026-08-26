#!/usr/bin/env python3
"""`landed_by` - an issue whose work was done through a different issue.

Its own module rather than more of `checks.py`, because the size cap in
`test_trc_a2` fired at 1289 lines against a limit of 1200. The cap exists to
keep modules grouped the way the code already is, and this block is cohesive:
one constant, one reader, one predicate and one check.

DEPENDENCY: none beyond the standard library and this package. It reads a spine
through `core.load_yaml`, which is where the bundled PyYAML is resolved; nothing
here imports yaml directly. Stated rather than omitted so the dependency scan
covers this file instead of listing it as unmarked.
"""
from __future__ import annotations

import os

from compass_pkg.check_results import NOTHING_TO_CHECK
from compass_pkg.core import CompassError, load_yaml, normalize_spine


# =============================================================================
# `landed_by` - an issue whose work was done through a different issue
# =============================================================================
# Six issues sat as `abandoned` with an empty record and had actually been
# delivered. `abandoned` was the only status that did not lie about the record,
# so it lied about the outcome instead - in the one place `compass retro` reads
# to judge whether triage is systematically over- or under-sizing.
#
# `landed_by:` MOVES the claim; it does not waive it. The named issue must
# exist, must be landed, must carry a record of its own, and must name this
# issue back in `delivered:`. Relaxing a guardrail check is the move a project
# talks itself into whenever a check is inconvenient, and the difference
# between doing it and getting away with it is whether every one of those four
# is checked.

#: The checks `landed_by` stands down, named rather than derived.
#:
#: Measured: these are exactly the three an empty-record landed issue fails.
#: A DERIVED set - "relax whatever fails" - would work today and rot the moment
#: a check is added, silently widening the relaxation. A named list fails
#: loudly when the set changes, which is the moment to think about it.
#:
#: What is NOT here is deliberate. `dashboard-current` still applies: the
#: review page must match the spine whatever the spine says. `dod-evidence-typed`
#: and `backfills-paid` still apply: an unchecked box or an owed follow-up is
#: this issue's own business regardless of who did the work.
LANDED_BY_RELAXES = (
    "scenarios-have-tests",
    "suite-passed",
    "scenario-has-id-and-intent",
    # Its complaint is "no gates in task.yml - has the route been evaluated?",
    # which is the same class as the three above: this issue never went through
    # verify, because a different one did.
    #
    # IT WAS MISSED THE FIRST TIME, and how is worth recording. The design says
    # this set was "measured rather than assumed" - and the measurement read
    # `compass check`'s DEFAULT view, which shows three failures and then
    # "... and 2 more". So it measured the truncation. Re-measured with
    # --verbose: four distinct checks, not three.
    "gate-evidence-present",
)


def _sibling_spine(task_dir, slug):
    """Another issue's spine, read from the same work root."""
    path = os.path.join(os.path.dirname(os.path.abspath(task_dir)),
                        slug, "task.yml")
    if not os.path.isfile(path):
        return None
    try:
        return normalize_spine(load_yaml(path) or {})
    except CompassError:
        return None


def _git_commit_subject(sha, cwd):
    """The subject line of `sha`, or None when it cannot be resolved.

    None means "could not look" as well as "not there" - the caller
    distinguishes them by asking git whether it is usable at all, because a
    check that clears because it could not look is the failure this repository
    found four of in one release.
    """
    import subprocess

    try:
        r = subprocess.run(["git", "log", "-1", "--format=%s", sha],
                           cwd=cwd, capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def _git_is_usable(cwd):
    import subprocess

    try:
        r = subprocess.run(["git", "rev-parse", "--git-dir"], cwd=cwd,
                           capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return False
    return r.returncode == 0


def _entries(value):
    """`landed_by` as a list of dicts, whatever shape it was written in.

    A bare string is read as one issue entry. That is not politeness - the
    field shipped as a single slug and an adopter may have written one.
    """
    if not value:
        return []
    if isinstance(value, str):
        return [{"issue": value.strip()}] if value.strip() else []
    if isinstance(value, dict):
        return [value]
    out = []
    for item in value:
        if isinstance(item, str) and item.strip():
            out.append({"issue": item.strip()})
        elif isinstance(item, dict):
            out.append(item)
    return out


def _issue_entry_holds(entry, task_dir, mine):
    slug = str(entry.get("issue") or "").strip()
    other = _sibling_spine(task_dir, slug)
    if other is None:
        return "`landed_by` names issue %r, and there is no such issue in " \
               "this work root" % slug
    if (other.get("status") or "") != "landed":
        return ("`landed_by` names issue %r, which has not landed (it is %r). "
                "A pointer at an unfinished issue is a promise, not a record."
                % (slug, other.get("status") or "unset"))
    if not (other.get("scenarios") or []):
        return ("`landed_by` names issue %r, which carries no record of its "
                "own - so neither issue has one, and the claim points at "
                "nothing" % slug)
    delivered = [str(x).strip() for x in (other.get("delivered") or [])]
    if mine not in delivered:
        return ("`landed_by` names issue %r, and that issue does not name this "
                "one in its `delivered:` list - so the link is one-way and "
                "anything could claim it" % slug)
    return None


def _commit_entry_holds(entry, project_root, git_reader):
    sha = str(entry.get("commit") or "").strip()
    what = str(entry.get("what") or "").strip()
    if len(what.split()) < 3:
        return ("`landed_by` names commit %s and does not say what it did. A "
                "bare sha is a reference nobody can act on - add `what:` "
                "saying what changed." % (sha[:12] or "(none)"))
    if git_reader(sha, project_root) is not None:
        return None
    if not _git_is_usable(project_root):
        # Declines rather than fails: unreachable is not the same as wrong.
        return ("could not reach git to resolve commit %s, so this claim is "
                "unverified here" % sha[:12])
    return ("`landed_by` names commit %s, and git could not find it in this "
            "repository" % sha[:12])


def landed_by_holds(task, task_dir, git_reader=None):
    """Does this issue's `landed_by` resolve? Returns (ok, detail).

    (False, None) means there is nothing to judge - distinct from a claim that
    fails, so a caller can tell "not claimed" from "claimed and wrong".

    `landed_by` is a LIST, and an entry names either another issue or a commit.
    The single-slug form the field shipped with is read as one issue entry.

    THE LIST IS WHY THIS WAS WIDENED. The first design assumed every already-done
    issue had been delivered by another issue - which fits one of the six
    records that motivated it. Three were fixed by an ordinary commit with no
    issue opened, and one had three parents.

    `git_reader` is injected so the commit form is testable without depending
    on this repository's history.
    """
    entries = _entries(task.get("landed_by"))
    if not entries:
        return False, None

    if (task.get("status") or "active") != "landed":
        return False, (
            "`landed_by` has no effect at status %r - it only applies to a "
            "landed issue, and nothing is relaxed here"
            % (task.get("status") or "active"))

    mine = str(task.get("task") or os.path.basename(os.path.abspath(task_dir)))
    project_root = os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(task_dir))))
    reader = git_reader or _git_commit_subject

    problems, described = [], []
    for entry in entries:
        if entry.get("issue"):
            problem = _issue_entry_holds(entry, task_dir, mine)
            described.append("issue %r" % entry["issue"])
        elif entry.get("commit"):
            problem = _commit_entry_holds(entry, project_root, reader)
            described.append("commit %s" % str(entry["commit"])[:12])
        else:
            problem = ("a `landed_by` entry names neither an issue nor a "
                       "commit: %r" % (entry,))
        if problem:
            problems.append(problem)

    if problems:
        return False, "; ".join(problems)
    return True, "the work was delivered by %s" % ", ".join(described)


def _check_landed_by_resolves(task, task_dir):
    """The pointer is a claim, so it is checked like one."""
    if not str(task.get("landed_by") or "").strip():
        return NOTHING_TO_CHECK, "no `landed_by` pointer on this issue"
    ok, detail = landed_by_holds(task, task_dir)
    if ok:
        return True, detail
    if detail is None:                       # unreachable; kept explicit
        return NOTHING_TO_CHECK, "no `landed_by` pointer on this issue"
    if (task.get("status") or "active") != "landed":
        # Inert rather than wrong: say so and pass, so nobody assumes the
        # field is doing something it is not.
        return NOTHING_TO_CHECK, detail
    return False, detail
