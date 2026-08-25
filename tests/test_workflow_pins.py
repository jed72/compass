"""Invariants on the framework's own CI workflow.

Two things must stay true of `.github/workflows/compass.yml`. It must SHA-pin
third-party actions, which is the same supply-chain stance `docs/security.md`
asks Compass consumers to take. And it must run the test suite, so that a
failing test can stop a merge rather than only failing on a contributor's
machine.

Traces to: .compass/work/sha-pin-workflow-actions/acceptance-criteria.md SCN-001,
and .compass/work/ci-runs-test-suite/acceptance-criteria.md SCN-001.
"""
from __future__ import annotations

import re
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "compass.yml"
USES_LINE = re.compile(r"uses:\s+([^\s@]+)@(\S+)")
SHA = re.compile(r"^[0-9a-f]{40}$")


def test_third_party_actions_are_sha_pinned():
    unpinned: list[str] = []
    for line in WORKFLOW.read_text().splitlines():
        match = USES_LINE.search(line)
        if match and not SHA.match(match.group(2)):
            unpinned.append(line.strip())
    assert not unpinned, (
        "third-party actions in .github/workflows/compass.yml are not "
        "SHA-pinned; each `uses:` ref must be a 40-char hex SHA:\n  "
        + "\n  ".join(unpinned)
    )


def test_ci_workflow_runs_the_test_suite():
    """CI must run the tests, not only the governance and structure checks.

    `compass ci` is governance lint plus the per-task guardrail checks. It does
    not run pytest. Without an explicit step, every test in this suite - the
    release invariants that cap the guardrail count, the house-style guards,
    all of it - runs only where someone happens to run it, and a pull request
    that breaks all of them goes green.
    """
    workflow = WORKFLOW.read_text()

    assert re.search(r"pip install[^\n]*\bpytest\b", workflow), (
        ".github/workflows/compass.yml does not install pytest. The workflow "
        "installs the CLI's runtime dependencies only, so a test step would "
        "fail with a missing module."
    )

    runs_suite = re.search(r"run:[^\n]*pytest", workflow) or re.search(
        r"run:[^\n]*make test", workflow
    )
    assert runs_suite, (
        ".github/workflows/compass.yml has no step that runs the test suite. "
        "validate.sh, the AST parse and `compass ci` do not run pytest, so "
        "nothing in tests/ gates a merge without one."
    )
