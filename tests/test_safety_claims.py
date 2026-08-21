"""What Compass promises about itself matches what it can demonstrate.

Issue: claims-match-what-is-proved. Scenarios TRC-B1 to TRC-B4, TRC-D1, TRC-D2
and TRC-F2.

The finding these cover, from an outside engineering review of 3.2.0: the
tested-before-ship promise reads as "the declared test ran", and what Compass
establishes is that the code declares a scenario, the scenario declares a test,
and some command exited zero. `_check_suite_passed` says so in its own comment.

Two separate jobs here. Narrow the wording so it stops overclaiming (group B),
and hold the safety contract to naming a real mechanism behind every guarantee
so it cannot drift back (group D).
"""

import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "cli"))

GUARDRAILS_YML = REPO_ROOT / "governance" / "guardrails.yml"
GUARDRAILS_MD = REPO_ROOT / "governance" / "guardrails.md"
METHODOLOGY = REPO_ROOT / "docs" / "methodology.md"
CONTRACT = REPO_ROOT / "docs" / "safety-contract.md"

#: The sentence this issue removes. It appeared in three files, worded
#: identically, and it is the overclaim itself - kept here so the test can say
#: "not this" rather than only "something like that".
OVERCLAIM = "No code reaches main without a passing automated test it traces to"


def _g1_statement() -> str:
    """G1's statement, read from the machine-readable file that owns it."""
    import yaml
    data = yaml.safe_load(GUARDRAILS_YML.read_text(encoding="utf-8"))
    for g in (data.get("defaults") or []):
        if g.get("id") == "G1":
            return " ".join(str(g.get("statement", "")).split())
    raise AssertionError("G1 is not in governance/guardrails.yml")


def _normalise(text: str) -> str:
    """Collapse whitespace and markdown emphasis so wording can be compared.

    The same sentence is a YAML block scalar in one file, a prose paragraph in
    another, and a numbered list item with backticks in the third. Comparing
    them raw would fail on formatting, which is not what any of these test.
    """
    text = text.replace("`", "").replace("**", "").replace("*", "")
    return " ".join(text.split())


# --- TRC-B1 -----------------------------------------------------------------

def test_b1_tested_before_ship_promise_is_narrowed():
    """TRC-B1 - the promise says what a green record establishes.

    A test-run record holds one exit code for one command. It does not
    enumerate the tests the command collected, so "a passing automated test it
    traces to" claims an execution relationship Compass never observes.
    """
    statement = _normalise(_g1_statement())

    assert OVERCLAIM.lower() not in statement.lower(), (
        "G1 still carries the sentence this issue exists to remove:\n"
        f"  {statement}")

    low = statement.lower()
    # It must still promise the traceable relationship, which is real...
    assert "trace" in low, (
        "the narrowed statement dropped the traceability half, which Compass "
        "does establish - this narrows the promise past what is true")
    # ...and it must say what is NOT observed, in words a reader meets here
    # rather than having to find in the source.
    assert "observe" in low or "does not establish" in low or "not verify" in low, (
        "the narrowed statement does not say what is left unproved. A promise "
        "that quietly omits its limit reads exactly like the old one")


def test_b1b_the_statement_points_at_where_the_stronger_guarantee_is_built():
    """TRC-B1 - a limit with no route out reads as a permanent one."""
    statement = _g1_statement().lower()
    assert "safety-contract" in statement or "safety contract" in statement, (
        "the statement does not point the reader at the contract that "
        "explains the limit in full")


# --- TRC-B2 -----------------------------------------------------------------

def test_b2_promise_reads_the_same_in_all_three_files():
    """TRC-B2 - correct every place at once, or a reader finds a contradiction.

    The canonical wording lives in G1's `statement:`. The two prose files must
    carry it. Reading it from the YAML rather than hardcoding it here keeps the
    sentence in one place instead of four.
    """
    canonical = _normalise(_g1_statement())
    # The first sentence is the promise; the rest of the statement may add the
    # pointer and the limit in whatever shape each file's prose wants.
    promise = canonical.split(".")[0].strip()
    assert len(promise) > 20, f"G1's statement is too short to be a promise: {promise!r}"

    for path in (GUARDRAILS_MD, METHODOLOGY):
        body = _normalise(path.read_text(encoding="utf-8"))
        assert promise.lower() in body.lower(), (
            f"{path.relative_to(REPO_ROOT)} does not carry the narrowed "
            f"promise from governance/guardrails.yml.\n"
            f"  expected to find: {promise}\n"
            f"Correct every place at once - a reader who finds the old wording "
            f"has no way to know which is current.")


def test_b2b_the_old_overclaim_is_gone_from_every_file():
    """TRC-B2 - the removal is checked, not assumed."""
    for path in (GUARDRAILS_YML, GUARDRAILS_MD, METHODOLOGY, CONTRACT):
        body = _normalise(path.read_text(encoding="utf-8"))
        assert OVERCLAIM.lower() not in body.lower(), (
            f"{path.relative_to(REPO_ROOT)} still carries the overclaim")


# --- TRC-F2 -----------------------------------------------------------------

def test_f2_narrowed_wording_does_not_soften_the_check():
    """TRC-F2 - the words get smaller; the machine does not.

    The risk in a wording change is that someone reads the softer sentence as
    permission to soften the check. G1's `checks:` list is what actually runs,
    and it must be untouched by this issue.
    """
    import yaml
    data = yaml.safe_load(GUARDRAILS_YML.read_text(encoding="utf-8"))
    g1 = next(g for g in data["defaults"] if g.get("id") == "G1")

    expected = {"scenarios-have-tests", "declared-tests-resolve", "suite-passed",
                "changed-code-traces-to-scenario", "scenarios-are-executable"}
    assert set(g1.get("checks") or []) == expected, (
        "G1's checks list changed. This issue narrows the STATEMENT only - if "
        "the enforcement moved too, the wording change has quietly become a "
        "governance change and must stop.\n"
        f"  expected: {sorted(expected)}\n"
        f"  found   : {sorted(g1.get('checks') or [])}")
