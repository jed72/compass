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

# The vocabulary rename landed on 2026-08-25: the assess and plan stages took
# the names their machine keys, skills and agents already used; `design` went
# back to the designer; design.md became technical-design.md and prd.md became
# intent.md. Spines and documents written before still load and resolve
# (ADR-006), so what moved is the CANONICAL spelling these tests assert - not
# what the framework computes. Re-pointed, not relaxed.
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "cli"))

# The rename map this slice ships. verification-report.md, task.yml,
# distribution-map.md, positioning.md, launch-readiness.md, ui-contract.md,
# and devlog.md keep their names - they are already plain English.
V2_TO_V1 = {
    "intent.md": "brief.md",
    "acceptance-criteria.md": "spec.feature.md",
    "delivery-approach.md": "route.md",
    "requirements-review.md": "clarifications.md",
    "technical-design.md": "plan.md",
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


def test_artifact_path_resolves_v2_names_only(tmp_path):
    """TRC-A2 (as amended by the machine-spine slice): the runtime resolver
    speaks v2 filenames only - the v1 fallback it carried during the
    transition retired when the archive migrated, and the old-name map
    lives in the migration module."""
    from compass_pkg import core

    d = tmp_path / "issue"
    d.mkdir()
    (d / "brief.md").write_text("v1")
    (d / "intent.md").write_text("v2")
    resolved = Path(core.artifact_path(str(d), "intent.md"))
    assert resolved.name == "intent.md" and resolved.read_text() == "v2"


def test_migration_renames_a_v1_issue_directory(tmp_path):
    """TRC-A3 (as amended by the machine-spine slice): an un-migrated issue
    directory becomes resolvable by migrating it - the migration module
    owns the v1 filename map the runtime no longer consults."""
    from compass_pkg import core, migrate

    old_dir = tmp_path / "old-issue"
    old_dir.mkdir()
    (old_dir / "spec.feature.md").write_text("# old spec")
    notes = migrate.migrate_issue_dir(str(old_dir))
    assert any("spec.feature.md" in n for n in notes)
    resolved = Path(core.artifact_path(str(old_dir), "acceptance-criteria.md"))
    assert resolved.read_text() == "# old spec"


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
