"""A queued issue is not asked for an assessment it cannot have.

`compass ci` is a release gate (docs/releasing.md step 4), and it was failing
eight queued issues for not having been assessed - which is what queued means.

The fix is deliberately one field for one status. `cmd_ci`'s own comment says
why the lint must otherwise run for every issue at every stage: "a malformed
manifest is malformed whether or not the work has started. Skipping it once let a
manifest the linter rejects outright sit in a repository while the sweep reported
everything clean." So the boundary tests below matter as much as the first one.

Scenario id: CIQ-A1 in
.compass/work/ci-fails-a-queued-issue-for-being-queued/acceptance-criteria.md
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CLI = REPO_ROOT / "cli" / "compass"


def _lint(tmp_path, manifest):
    d = tmp_path / ".compass" / "work" / "demo"
    d.mkdir(parents=True, exist_ok=True)
    (tmp_path / ".compass" / "config.yml").write_text("version: 1.0.0\n")
    (d / "manifest.yml").write_text(yaml.safe_dump(manifest, sort_keys=False))
    return subprocess.run(
        [sys.executable, str(CLI), "issue", "lint", "--issue", "demo"],
        cwd=str(tmp_path), capture_output=True, text=True, timeout=120)


_BASE = {"schema_version": "2.0", "task": "demo", "created": "2026-08-26"}


def test_ciq_a1_a_queued_issue_needs_no_assessment(tmp_path):
    """The defect: filing work early should not redden the repository.

    `cmd_ci`'s own words - the framework "asks for work to be triaged early,
    and failing the sweep for complying teaches people to stop".
    """
    run = _lint(tmp_path, dict(_BASE, status="queued"))
    assert run.returncode == 0, (
        "a queued issue was failed for not having been assessed, which is "
        "what queued means:\n" + run.stdout + run.stderr)


def test_ciq_a1b_an_active_issue_still_needs_one(tmp_path):
    """The boundary, and the reason this is one field rather than a status skip.

    An active issue with no assessment is work started without triage - the one
    rule Compass says is never skipped. Relaxing it for `active` would waive
    that rule rather than acknowledge that a queued issue has not reached it.
    """
    run = _lint(tmp_path, dict(_BASE, status="active"))
    assert run.returncode != 0, (
        "an ACTIVE issue with no assessment passed - work started without "
        "triage is the one thing this lint exists to catch")
    assert "assessment" in (run.stdout + run.stderr).lower()


def test_ciq_a1c_a_queued_issue_malformed_otherwise_still_fails(tmp_path):
    """The other boundary. The lint still runs; only one field stands down.

    Skipping the lint wholesale for queued issues is what `cmd_ci` warns
    against in as many words: it "let a manifest the linter rejects outright sit
    in a repository while the sweep reported everything clean".
    """
    run = _lint(tmp_path, dict(_BASE, status="queued", scenarios="not-a-list"))
    assert run.returncode != 0, (
        "a queued issue with a malformed manifest passed - the lint has been "
        "skipped for the status rather than relaxed for one field:\n"
        + run.stdout + run.stderr)
