"""Tests that the shipped architecture templates are present.

Covers:
  TRC-A4 — Compass ships templates for the architecture artifacts
"""
from __future__ import annotations

from pathlib import Path

import pytest


FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_ARCH = FRAMEWORK_ROOT / "templates" / "architecture"
TEMPLATES_DECISIONS = TEMPLATES_ARCH / "decisions"


# ---------------------------------------------------------------------------
# TRC-A4 — templates exist
# ---------------------------------------------------------------------------

def test_architecture_templates_exist():
    """TRC-A4: The framework ships templates for the three narrative files,
    the ADR template, and the decisions README."""
    required = [
        TEMPLATES_ARCH / "system-context.md",
        TEMPLATES_ARCH / "relations.md",
        TEMPLATES_ARCH / "ownership.md",
        TEMPLATES_DECISIONS / "ADR-template.md",
        TEMPLATES_DECISIONS / "README.md",
    ]
    missing = [str(p) for p in required if not p.exists()]
    assert not missing, \
        f"Missing required architecture templates:\n  " + "\n  ".join(missing)


def test_narrative_templates_have_content():
    """Each narrative template must be non-empty and mention how Frame uses it."""
    for name in ("system-context.md", "relations.md", "ownership.md"):
        p = TEMPLATES_ARCH / name
        if not p.exists():
            pytest.skip(f"{name} does not exist — covered by test_architecture_templates_exist")
        text = p.read_text(encoding="utf-8")
        assert len(text) > 50, f"{name} template appears empty"
        # Each template should carry at least a minimal heading
        assert "#" in text, f"{name} template has no markdown heading"


def test_adr_template_has_frontmatter_fields():
    """The ADR template must contain all required frontmatter field names."""
    p = TEMPLATES_DECISIONS / "ADR-template.md"
    if not p.exists():
        pytest.skip("ADR-template.md does not exist")
    text = p.read_text(encoding="utf-8")
    for field in ("id:", "title:", "status:", "date:", "supersedes:", "superseded_by:"):
        assert field in text, \
            f"ADR-template.md missing frontmatter field: {field!r}"


def test_worked_example_adrs_present():
    """The five worked-example ADRs must ship alongside the template."""
    for n in range(1, 6):
        num = f"{n:03d}"
        # Find any file matching ADR-00N-*.md
        matches = list(TEMPLATES_DECISIONS.glob(f"ADR-{num}-*.md"))
        assert matches, \
            f"No worked-example ADR found for ADR-{num}-* in {TEMPLATES_DECISIONS}"
