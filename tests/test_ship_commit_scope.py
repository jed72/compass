"""Shipping does not refuse the framework's own bookkeeping.

`compass ship-commit` refuses to commit paths outside the issue's declared
scope - its `changed_files` plus its artifact directory. That check earns its
place: a repo-wide auto-formatter plus a whole-tree re-stage once took a real
index from 23 files to 1,574, including a concurrent agent's uncommitted work.

But `.compass/current-task` sits beside `.compass/work/`, not inside the
issue's directory, and triage writes it. So Compass refused to commit a file
Compass had just written, and shipping stalled on the framework's own output
with a message telling the author to record it as a changed file - which it
is not.

The fix widens the allowance by a named list, never by a prefix: anything
under `.compass/` would re-admit a sibling issue's artifacts into this
issue's commit, which is exactly what the check exists to stop.

Scenario ids: see docs/system-spec.md (group D).
"""

# The vocabulary rename landed on 2026-08-25: the assess and plan stages took
# the names their machine keys, skills and agents already used; `design` went
# back to the designer; design.md became technical-design.md and prd.md became
# intent.md. Spines and documents written before still load and resolve
# (ADR-006), so what moved is the CANONICAL spelling these tests assert - not
# what the framework computes. Re-pointed, not relaxed.
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "cli"))

from compass_pkg import task_spine                              # noqa: E402

TASK = {
    "task": "demo",
    "changed_files": [{"path": "src/app.py", "scenarios": ["SCN-1"]}],
}


def _scope():
    return task_spine._land_scope(TASK, "demo")


def test_rcd_d1_current_task_pointer_in_scope():
    """The pointer triage writes must not be refused by the commit that ships it."""
    owned, artifact_dir = _scope()
    stray = task_spine._out_of_scope(
        ["src/app.py", ".compass/current-task"], owned, artifact_dir)

    assert ".compass/current-task" not in stray, (
        "shipping refused .compass/current-task as outside the issue's "
        "declared scope. Compass writes that file itself at triage, so this "
        "blocks the commit on the framework's own output."
    )


def test_rcd_d1b_the_issues_own_artifacts_stay_in_scope():
    """The existing allowance must survive the widening."""
    owned, artifact_dir = _scope()
    stray = task_spine._out_of_scope(
        ["src/app.py", ".compass/work/demo/technical-design.md"], owned, artifact_dir)

    assert stray == [], (
        f"the issue's own declared file or artifact directory was refused: "
        f"{stray}"
    )


def test_rcd_d2_unrelated_file_still_refused():
    """The control, and the reason the check exists at all.

    Without this, D1 passes against a change that allowed everything - which
    would re-open the case where a formatter's output rides into the commit.
    """
    owned, artifact_dir = _scope()
    stray = task_spine._out_of_scope(
        ["src/app.py", "src/unrelated.py", "vendor/generated.js"],
        owned, artifact_dir)

    assert "src/unrelated.py" in stray and "vendor/generated.js" in stray, (
        f"an undeclared source file was accepted into the issue's commit. "
        f"Refused: {stray}"
    )


def test_rcd_d2b_a_sibling_issues_artifacts_are_still_refused():
    """The widening must be a named list, not a `.compass/` prefix.

    A prefix would let another issue's artifacts - or another agent's
    in-progress work in the same tree - ride into this commit, which is the
    collision the scope check was built for.
    """
    owned, artifact_dir = _scope()
    # `demo-2` EXTENDS `demo`. A slug sharing no prefix passes whether or not
    # the artifact directory carries its trailing slash, so the earlier
    # fixture left that boundary untested - and slugs that extend one another
    # are ordinary here (rehearsal-recordings beside rehearsal-cli-defects).
    stray = task_spine._out_of_scope(
        [".compass/work/demo-2/task.yml",
         ".compass/work/some-other-issue/task.yml"], owned, artifact_dir)

    assert stray == [".compass/work/demo-2/task.yml",
                     ".compass/work/some-other-issue/task.yml"], (
        "a sibling issue's artifacts were accepted into this issue's commit - "
        "the allowance widened to a prefix instead of a named set"
    )
