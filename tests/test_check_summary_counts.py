"""`compass check`'s summary does not overstate what was verified.

Three of the sixteen checks clear with nothing to check: no BDD runner wired,
no claims recorded, no project guardrails declared. Each is honestly labelled
on its own line - that is to the tool's credit. The summary was the problem:
`PASS - all 16 check(s) passed` flattens three vacuous clearances into the
same count as thirteen real ones, and the summary is the line a reader takes
away.

The signal is structured rather than matched from the detail prose. A check's
vacuity is a runtime property - "no BDD runner wired" depends on the project -
so a static list cannot express it, and matching the message would be a guard
that silently stops working the first time someone improves the wording.

Scenario ids: see .compass/work/identifiers-and-vocabulary-in-printed-output/
acceptance-criteria.md (group D).
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "cli"))

import compass_pkg                                              # noqa: F401,E402

# Imported inside each test rather than at module level. A module-level import
# of a symbol that does not exist yet is an ImportError, which makes the whole
# file uncollectable - and `compass tdd-red` correctly refuses to record that
# as a red, because no test ran. A red has to be a test that ran and failed.


def _summarise():
    from compass_pkg.check_cmd import summarise_counts
    return summarise_counts


# ---------------------------------------------------------------------------
# TRC-D1 - vacuous clearances are counted apart
# ---------------------------------------------------------------------------

def test_trc_d1_vacuous_counted_apart():
    """Sixteen ran, three had nothing to check."""
    line = _summarise()(ran=16, failures=0, vacuous=3)

    # The denominator was dropped after this test first shipped: "13 of 16
    # passed" reads as three failures at a glance, and the total is not a
    # constant - G5 only runs when the work touches auth, payments, personal
    # data or migrations. The count that matters is what passed.
    # tests/test_ceiling_and_honest_counts.py holds the current contract.
    assert "13 check(s) passed" in line, (
        f"the summary does not lead with how many checks verified something: "
        f"{line!r}")
    assert " of 16" not in line, (
        f"the summary prints a denominator again: {line!r}")
    assert re.search(r"3\b.*(nothing to check|vacuous)", line, re.I), (
        f"the three vacuous clearances are not reported as such: {line!r}")
    assert line.startswith("compass check: PASS"), (
        f"a run with no failures must still read as a pass: {line!r}")


# ---------------------------------------------------------------------------
# TRC-D2 - a real pass is not miscounted
# ---------------------------------------------------------------------------

def test_trc_d2_real_pass_not_miscounted():
    """The control.

    Without it, a change that labelled every check vacuous would satisfy
    TRC-D1 while reporting that Compass verified nothing.
    """
    line = _summarise()(ran=16, failures=0, vacuous=0)

    assert "16" in line, f"the total is no longer reported: {line!r}"
    assert not re.search(r"nothing to check|vacuous", line, re.I), (
        f"a run where every check had something to check still claims some "
        f"had nothing: {line!r}")
    assert line.startswith("compass check: PASS"), line


def test_trc_d2b_a_failure_still_reads_as_a_failure():
    """Vacuity must not soften a real failure - the count is a caveat on a
    pass, never a way to report fewer failures than there were."""
    line = _summarise()(ran=16, failures=2, vacuous=3)

    assert line.startswith("compass check: FAIL"), line
    assert "2" in line, f"the failure count is missing: {line!r}"


def test_trc_d2c_the_sentinel_is_truthy():
    """VACUOUS stands in for True at every existing call site.

    A falsy sentinel would silently convert three passing checks into three
    failures, which is the opposite of the defect being fixed.
    """
    from compass_pkg.checks import VACUOUS

    assert VACUOUS, "VACUOUS is falsy - every vacuous check would count as a failure"
    assert VACUOUS is not True, (
        "VACUOUS is literally True, so the summary cannot tell a vacuous "
        "clearance from a verified one")
