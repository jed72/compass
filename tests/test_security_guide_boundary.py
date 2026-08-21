"""The security guide describes the trust boundary that exists.

Issue: claims-match-what-is-proved. Scenarios TRC-C1, TRC-C2 and TRC-C3.

The finding, from an outside engineering review of 3.2.0: the guide argued that
a hostile project guardrail cannot name a check and have the CLI run it, because
the check must already be registered. `command-passes` IS a registered check,
and its YAML parameter is the command - run through a shell, from the project
root. The registry is not the boundary the guide described.

Its second argument does not hold either. Continuous integration normally runs
on a pull request before anyone approves it, so review is not what stands
between an untrusted contribution and the runner.

This issue fixes the description only. The mechanism - an opt-in, a refusal on
untrusted pull requests, an allowlist - is separate work.
"""

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
GUIDE = REPO_ROOT / "docs" / "security.md"


def _flatten(text: str) -> str:
    """Strip markdown emphasis and collapse whitespace.

    Backticks AND asterisks, because a phrase that happens to carry a bold run
    or wraps across a line is the same sentence to a reader, and a check that
    misses it is failing on formatting rather than on meaning.
    """
    text = text.replace("`", "").replace("**", "").replace("*", "")
    return " ".join(text.split())


def _text() -> str:
    return _flatten(GUIDE.read_text(encoding="utf-8"))


def _section() -> str:
    """The part of the guide that discusses project guardrails."""
    body = GUIDE.read_text(encoding="utf-8")
    parts = re.split(r"^## ", body, flags=re.M)
    for part in parts:
        head = part.split("\n", 1)[0].lower()
        # Either wording finds it. The heading is the document's to choose;
        # this check only needs to locate the section, and pinning it to one
        # exact title would make an improvement to the prose look like a
        # regression.
        if "project guardrail" in head or "project governance" in head:
            return _flatten(part)
    raise AssertionError(
        "docs/security.md has no section heading about project guardrails or "
        "project governance - either it was removed or renamed, and this "
        "check can no longer find the claims it exists to police")


# --- TRC-C1 -----------------------------------------------------------------

def test_c1_guide_says_project_governance_is_executable():
    """TRC-C1 - a project guardrail can run a command, and the guide says so."""
    s = _section().lower()

    # Phrases, not words. The first version of this test asked whether
    # "command-passes" and "shell" appeared anywhere in the section. Both
    # recur several times for unrelated reasons, so no change to the section
    # could make it fail - it passed over prose it had not read. Its own
    # mutation proof is what caught that, the second time in this issue.
    assert "whose parameter is the command" in s, (
        "the section does not say that the check's parameter IS the command. "
        "Naming command-passes without saying that leaves the reader thinking "
        "it is configuration")
    assert "subprocess.run" in s and "shell=true" in s, (
        "the section does not show how the command is executed. A reader "
        "reviewing a governance change needs to know it reaches a shell")
    assert "as code, not as configuration" in s, (
        "the section does not tell a reviewer to read a project governance "
        "file as code rather than as configuration - which is the one "
        "behaviour change this section is asking for")


def test_c1b_the_registry_is_no_longer_offered_as_a_defence():
    """TRC-C1 - the misleading claim is withdrawn, in one of two valid ways.

    Deleting it is fine. So is quoting it and saying why it was wrong, which is
    better for a reader who read the old version and wants to know what
    changed. What is not fine is the sentence still standing as a defence, so
    this checks that if the words are present they are marked as withdrawn.
    """
    claim = "cannot just name a check and have the cli run it"
    s = _section().lower()
    if claim not in s:
        return
    assert "used to claim" in s or "were wrong" in s or "no longer" in s, (
        "the guide still carries the sentence saying a hostile guardrail "
        "cannot name a check and have the CLI run it, with nothing marking it "
        "as withdrawn. command-passes is exactly that check")


# --- TRC-C2 -----------------------------------------------------------------

def test_c2_guide_does_not_rely_on_pr_review():
    """TRC-C2 - CI runs before approval, so review is not the boundary."""
    s = _section().lower()

    assert "before" in s and ("approv" in s or "review" in s), (
        "the section does not say that continuous integration normally runs "
        "before a pull request is approved")
    assert "runs before" in s or "before it is approved" in s or "before anyone" in s, (
        "the guide does not state plainly that CI runs before approval, which "
        "is what makes pull-request review the wrong boundary to cite")


# --- TRC-C3 -----------------------------------------------------------------

def test_c3_guide_names_the_issue_that_closes_it():
    """TRC-C3 - a known gap reads differently from one nobody has noticed.

    The citation must be something a reader outside this machine can open.
    The framework's own .compass/work/ is gitignored, so a local issue slug
    would be a reference only its author can follow - worse than saying
    nothing, because it reads as a citation.
    """
    s = _section()
    m = re.search(r"github\.com/[\w.-]+/[\w.-]+/issues/(\d+)|#(\d+)", s)
    assert m, (
        "the section does not cite a public issue for the work that closes "
        "this gap. A reader cannot tell a known gap from an unnoticed one")

    low = s.lower()
    assert "opt-in" in low or "opt in" in low or "allowlist" in low, (
        "the section names an issue but not what that work would change")
