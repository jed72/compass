"""The CI token posture Compass declares, and the one it recommends.

A workflow that declares no `permissions:` block gets whatever the repository
or organisation default happens to be - which on many repositories is a
read-write token. Compass runs project-declared commands on that runner, so the
token it hands them is part of what a compromised command could reach.

These tests read every workflow file in the repository, not only the ones in
the conventional directory. The reference workflow Compass publishes for
adopters to copy lives under `ci/`, and it is the file the advice is actually
about: a guard scoped to `.github/workflows/` alone would pass while the
published example went unfixed.

Scenario ids trace to .compass/work/project-commands-are-a-trust-boundary/
acceptance-criteria.md - group D, and TRC-E2 from group E.
"""
from __future__ import annotations

from pathlib import Path
from typing import List

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
REFERENCE_WORKFLOW = REPO_ROOT / "ci" / "github-actions.yml"
SECURITY_GUIDE = REPO_ROOT / "docs" / "security.md"
SAFETY_CONTRACT = REPO_ROOT / "docs" / "safety-contract.md"


def _workflow_files() -> List[Path]:
    """Every GitHub Actions workflow in this repository.

    Two locations, and both matter for different reasons. `.github/workflows/`
    is what actually runs here. `ci/` holds the reference workflow Compass
    ships for adopters, which runs nowhere but is copied everywhere.
    """
    found: List[Path] = []
    workflows_dir = REPO_ROOT / ".github" / "workflows"
    if workflows_dir.is_dir():
        found.extend(sorted(p for p in workflows_dir.iterdir()
                            if p.suffix in (".yml", ".yaml")))
    if REFERENCE_WORKFLOW.is_file():
        found.append(REFERENCE_WORKFLOW)
    return found


def _declares_permissions(path: Path) -> bool:
    """Does this workflow declare permissions, at the top level or per job?

    Parsed rather than grepped: a `permissions:` string could appear in a
    comment, and a comment grants nothing.
    """
    doc = yaml.safe_load(path.read_text())
    if not isinstance(doc, dict):
        return False
    if "permissions" in doc:
        return True
    jobs = doc.get("jobs")
    if isinstance(jobs, dict):
        return all(isinstance(j, dict) and "permissions" in j
                   for j in jobs.values()) and bool(jobs)
    return False


def test_d1_reference_workflow_declares_permissions():
    """TRC-D1: the workflow Compass ships for adopters declares the token
    permissions it needs, and they are the narrowest the job requires.

    Advice a project does not follow in the example it publishes is advice
    nobody follows.
    """
    assert REFERENCE_WORKFLOW.is_file(), "the reference workflow is missing"
    doc = yaml.safe_load(REFERENCE_WORKFLOW.read_text())

    assert "permissions" in doc, (
        "the reference workflow declares no `permissions:` block, so an "
        "adopter copying it gets whatever their repository default is")

    perms = doc["permissions"]
    assert isinstance(perms, dict) and perms, (
        "the reference workflow's permissions block is not a mapping of "
        "scopes: " + repr(perms))
    assert set(perms) == {"contents"} and perms["contents"] == "read", (
        "the reference workflow grants more than it needs - running checks "
        "requires reading the checkout and nothing else: " + repr(perms))


def test_d2_every_workflow_declares_permissions():
    """TRC-D2: Compass's own workflow follows the posture it recommends, and
    this check fails if ANY workflow file in the repository declares none."""
    files = _workflow_files()
    assert files, "no workflow files found - this guard is reading nothing"

    missing = [str(p.relative_to(REPO_ROOT)) for p in files
               if not _declares_permissions(p)]
    assert not missing, (
        "these workflow files declare no `permissions:` block, so their token "
        "is whatever the repository default happens to be: " + ", ".join(missing))


def test_d2_guard_covers_the_shipped_reference_workflow():
    """TRC-D2, the part that is easy to get wrong.

    The guard above is only worth having if it reads the published reference
    as well as the workflows that run here. Scoping it to the conventional
    directory would leave the file adopters copy unchecked - the
    instance-not-the-class mistake.
    """
    assert REFERENCE_WORKFLOW in _workflow_files(), (
        "the shipped reference workflow is not in the set this guard reads, "
        "so the file adopters actually copy is unchecked")


def test_d3_guide_states_what_the_project_must_configure():
    """TRC-D3: the security guide says what Compass refuses on its own, what
    the project must configure itself, and which of the two is the boundary."""
    guide = SECURITY_GUIDE.read_text()

    assert "allow_project_commands" in guide, (
        "the guide does not name the opt-in, so a reader cannot act on it")
    assert "COMPASS_CONTRIBUTION_TRUST" in guide, (
        "the guide does not name the signal a project sets on an unrecognised "
        "CI provider, which is the one thing they must configure themselves")
    assert "permissions:" in guide, (
        "the guide does not tell a project to declare its workflow token "
        "permissions, which is the half Compass cannot do for them")
    assert "push access" in guide, (
        "the guide does not state the limit - a contributor with push access "
        "is not defended against - so a reader will over-trust this")


def test_e2_contract_covers_the_opt_in_case():
    """TRC-E2: the safety contract's guarantee about declared guardrails still
    holds once a guardrail can be disabled by configuration.

    The answer is that it is not silent, not that the guarantee bends.
    """
    contract = SAFETY_CONTRACT.read_text()

    guarantee = contract.split("2. **A declared guardrail cannot silently")
    assert len(guarantee) == 2, (
        "guarantee 2 is no longer where this test reads it - the wording this "
        "check depends on has moved or changed")
    body = guarantee[1].split("3. **")[0]

    assert "allow_project_commands" in body or "configuration" in body, (
        "guarantee 2 does not reach the case where a guardrail is disabled by "
        "project configuration, which is now possible:\n" + body)
    assert "not checked" in body or "nothing to check" in body, (
        "guarantee 2 does not say that a configuration-disabled guardrail is "
        "reported as not-checked rather than as passing:\n" + body)


def test_d3_guide_does_not_overclaim_the_refusal():
    """TRC-D3: the guide must not describe the refusal as unforgeable.

    It nearly did. On a `pull_request` event the contribution controls its own
    workflow file, so it controls the environment Compass reads - the cheap
    forgeries fail, but a determined one can still write a payload outside the
    checkout. A guide that promised more than that would be the same defect
    this issue exists to fix, one layer up.
    """
    prose = " ".join(SECURITY_GUIDE.read_text().split())

    assert "cannot forge" not in prose, (
        "the guide claims the refusal rests on a signal that cannot be forged, "
        "which is not true on a pull_request event")
    assert "not unforgeable" in prose, (
        "the guide does not state that the refusal can be forged with "
        "deliberate effort, so a reader will over-trust it")
    assert "withholds your secrets" in prose, (
        "the guide does not name what actually bounds a fork pull request - "
        "GitHub withholding secrets and issuing a read-only token")
