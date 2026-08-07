"""The v2 artifact names - templates and the CLI plumbing that resolves them.

First half of the artifact-rename slice of the v2 plan: the templates carry
the v2 filenames, two new intake templates exist, and the CLI resolves every
per-issue artifact by its v2 name while still accepting the v1 name - the
work archive keeps v1 filenames until the machine-spine slice migrates it,
and `compass check`, `analyze`, `receipt`, `next`, `flow`, and the
derivation must read both generations in the meantime.

Docstrings cite the acceptance criteria by TRC id; the criteria live in the
issue's archived spec, indexed in its `task.yml`.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "cli"))

# The rename map this slice ships. verification-report.md, task.yml,
# distribution-map.md, positioning.md, launch-readiness.md, ui-contract.md,
# and devlog.md keep their names - they are already plain English.
V2_TO_V1 = {
    "prd.md": "brief.md",
    "acceptance-criteria.md": "spec.feature.md",
    "delivery-approach.md": "route.md",
    "requirements-review.md": "clarifications.md",
    "design.md": "plan.md",
}
NEW_INTAKE_TEMPLATES = {"bug-report.md", "incident.md"}


def test_templates_carry_the_v2_names():
    """TRC-A1: the template set speaks v2 - every renamed template exists
    under its v2 name, no template keeps a v1 name, and the two new intake
    templates exist."""
    names = {p.name for p in (REPO_ROOT / "templates").iterdir() if p.is_file()}
    missing = (set(V2_TO_V1) | NEW_INTAKE_TEMPLATES) - names
    leftover = set(V2_TO_V1.values()) & names
    assert not missing, f"templates missing their v2 names: {sorted(missing)}"
    assert not leftover, f"templates still carrying v1 names: {sorted(leftover)}"


def test_artifact_path_prefers_v2_and_accepts_v1(tmp_path):
    """TRC-A2: the resolver returns the v2-named file when present, falls
    back to the v1 name (the un-migrated archive), and names absent
    artifacts by their v2 name so new issues write v2 files."""
    from compass_pkg import core

    for v2_name, v1_name in V2_TO_V1.items():
        kind_dir = tmp_path / v2_name.replace(".md", "")
        kind_dir.mkdir()
        # Absent: resolve to the v2 name, so writers create v2 files.
        assert Path(core.artifact_path(str(kind_dir), v2_name)).name == v2_name
        # v1 only (an un-migrated issue directory): resolve to the v1 file.
        (kind_dir / v1_name).write_text("v1")
        assert Path(core.artifact_path(str(kind_dir), v2_name)).name == v1_name
        # Both present: the v2 file wins.
        (kind_dir / v2_name).write_text("v2")
        assert Path(core.artifact_path(str(kind_dir), v2_name)).name == v2_name


def test_readers_resolve_v1_and_v2_issue_directories(tmp_path):
    """TRC-A3: the acceptance-criteria reader (the derivation's and the
    checks' shared entry) finds the file in both an un-migrated issue
    directory and a v2-named one."""
    from compass_pkg import core

    old_dir = tmp_path / "old-issue"
    old_dir.mkdir()
    (old_dir / "spec.feature.md").write_text("# old spec")
    new_dir = tmp_path / "new-issue"
    new_dir.mkdir()
    (new_dir / "acceptance-criteria.md").write_text("# new criteria")

    old = core.artifact_path(str(old_dir), "acceptance-criteria.md")
    new = core.artifact_path(str(new_dir), "acceptance-criteria.md")
    assert Path(old).read_text() == "# old spec"
    assert Path(new).read_text() == "# new criteria"


def test_bdd_extraction_output_is_named_for_acceptance_criteria():
    """TRC-A4: the extracted runnable Gherkin file is named
    acceptance-criteria.feature, not spec.feature, when no features dir is
    configured."""
    from compass_pkg import bdd

    out = bdd.default_extract_path("/tmp/some-issue-dir")
    assert Path(out).name == "acceptance-criteria.feature", (
        f"extraction output is {Path(out).name}; the v2 name is "
        "acceptance-criteria.feature"
    )
