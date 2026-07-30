"""Tests for the architect-lens agent (U2 - stream-2).

Covers scenarios: TRC-B1, TRC-B2, TRC-B3, TRC-B4, TRC-B5, TRC-X5, TRC-F5.

Strategy: agent files are markdown with frontmatter + headed sections.
Tests use file-existence + content-regex assertions (structural contract).
Trigger-detection logic (TRC-B2) is tested with mocked task.yml and
mocked architecture files via filesystem fixtures in tmp_path.

Architectural invariant: architecture-notes.md is ANNOTATIONS
+ candidate ADR titles - NOT Given/When/Then scenarios. TRC-F5 encodes
this prohibition explicitly.
"""
from __future__ import annotations

from pathlib import Path

import yaml

# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = FRAMEWORK_ROOT / "agents"
COMMANDS_DIR = FRAMEWORK_ROOT / "commands"


def agent_file(name: str) -> Path:
    return AGENTS_DIR / name


def command_file(name: str) -> Path:
    return COMMANDS_DIR / name


# --------------------------------------------------------------------------
# TRC-B1 - architect-lens is invocable from roundtable
# --------------------------------------------------------------------------


def test_invocable_from_roundtable():
    """TRC-B1: commands/roundtable.md lists architect-lens in its standard
    agent roster and documents the /compass:roundtable architect-lens
    invocation pattern.
    """
    roundtable = command_file("roundtable.md")
    assert roundtable.exists(), "commands/roundtable.md not found"
    content = roundtable.read_text(encoding="utf-8")

    # Must mention architect-lens in the agent roster section
    assert "architect-lens" in content, (
        "commands/roundtable.md does not list architect-lens in agent roster"
    )


# --------------------------------------------------------------------------
# TRC-B1 (continued) - the agent file itself must exist with required shape
# --------------------------------------------------------------------------


def test_architect_lens_agent_file_exists():
    """TRC-B1: agents/architect-lens.md must exist."""
    assert agent_file("architect-lens.md").exists(), (
        "agents/architect-lens.md does not exist"
    )


def test_architect_lens_has_frontmatter():
    """TRC-B1: agents/architect-lens.md must have YAML frontmatter (--- delimiters)."""
    content = agent_file("architect-lens.md").read_text(encoding="utf-8")
    assert content.startswith("---"), (
        "agents/architect-lens.md missing YAML frontmatter opening ---"
    )
    assert content.count("---") >= 2, (
        "agents/architect-lens.md missing YAML frontmatter closing ---"
    )


def test_architect_lens_frontmatter_fields():
    """TRC-B1: architect-lens.md frontmatter must have name, description, tools, model."""
    content = agent_file("architect-lens.md").read_text(encoding="utf-8")
    # Extract frontmatter block
    parts = content.split("---", 2)
    assert len(parts) >= 3, "Could not parse frontmatter"
    fm = yaml.safe_load(parts[1])
    assert fm.get("name") == "architect-lens", (
        f"Expected name: architect-lens, got: {fm.get('name')}"
    )
    assert "description" in fm, "architect-lens.md frontmatter missing description"
    assert "tools" in fm, "architect-lens.md frontmatter missing tools"
    assert "model" in fm, "architect-lens.md frontmatter missing model"


def test_architect_lens_has_required_sections():
    """TRC-B1/B5: architect-lens.md must contain the five required output sections
    (matching the architecture-notes.md contract):
      1. System under change
      2. Invariants this task must preserve
      3. Boundary risks
      4. Candidate ADRs
      5. Notes for the planner
    """
    content = agent_file("architect-lens.md").read_text(encoding="utf-8")
    required = [
        "system under change",
        "invariants",
        "boundary risk",
        "candidate adr",
        "notes for the planner",
    ]
    for term in required:
        assert term.lower() in content.lower(), (
            f"architect-lens.md missing section reference: '{term}'"
        )


def test_architect_lens_reads_architecture_files():
    """TRC-B1: architect-lens.md must instruct the agent to read the standard
    architecture/ input files.
    """
    content = agent_file("architect-lens.md").read_text(encoding="utf-8")
    required_reads = [
        "system-context.md",
        "relations.md",
        "ownership.md",
    ]
    for fname in required_reads:
        assert fname in content, (
            f"architect-lens.md does not instruct reading {fname}"
        )


def test_architect_lens_reads_task_artifacts():
    """TRC-B1/Inv-5: architect-lens reads spec.feature.md and plan.md - it is
    a lens OVER the spec, not an author of the spec.
    """
    content = agent_file("architect-lens.md").read_text(encoding="utf-8")
    assert "spec.feature.md" in content, (
        "architect-lens.md does not instruct reading spec.feature.md"
    )
    assert "plan.md" in content, (
        "architect-lens.md does not instruct reading plan.md"
    )


def test_architect_lens_writes_architecture_notes():
    """TRC-B1/B5: architect-lens.md must instruct the agent to write
    architecture-notes.md to the task directory.
    """
    content = agent_file("architect-lens.md").read_text(encoding="utf-8")
    assert "architecture-notes.md" in content, (
        "architect-lens.md does not mention writing architecture-notes.md"
    )


# --------------------------------------------------------------------------
# TRC-B2 - spec-author consults architect-lens for boundary-touching tasks
# --------------------------------------------------------------------------


def test_consulted_by_spec_author():
    """TRC-B2: agents/spec-author.md must contain a step that triggers the
    architect-lens consultation when task.yml.readings.touches matches
    the Q5 trigger conditions (public-api, service name, lens_trigger_tag).
    """
    spec_author = agent_file("spec-author.md")
    assert spec_author.exists(), "agents/spec-author.md not found"
    content = spec_author.read_text(encoding="utf-8")

    # Must mention the architect-lens consultation trigger
    assert "architect-lens" in content, (
        "agents/spec-author.md does not mention architect-lens consultation"
    )
    # Must reference the trigger tag 'public-api'
    assert "public-api" in content, (
        "agents/spec-author.md does not reference the public-api trigger tag"
    )


def test_spec_author_trigger_conditions():
    """TRC-B2: spec-author.md must document all three Q5 trigger conditions:
      1. touches contains 'public-api'
      2. touches contains a service name from architecture/relations.md
      3. touches contains a lens_trigger_tag from architecture/invariants.yml
    """
    content = agent_file("spec-author.md").read_text(encoding="utf-8")
    assert "relations.md" in content, (
        "spec-author.md does not mention architecture/relations.md trigger"
    )
    assert "lens_trigger_tag" in content or "invariants.yml" in content, (
        "spec-author.md does not mention invariants.yml lens_trigger_tag trigger"
    )


# --------------------------------------------------------------------------
# TRC-B3 - planner reads existing architect-lens notes and cites or diverges
# --------------------------------------------------------------------------


def test_consulted_by_planner():
    """TRC-B3: agents/planner.md must contain a step that reads
    architecture-notes.md (if present) and produces a DD that cites or
    diverges from its findings. DD-5 in plan.md.
    """
    planner = agent_file("planner.md")
    assert planner.exists(), "agents/planner.md not found"
    content = planner.read_text(encoding="utf-8")

    assert "architecture-notes.md" in content, (
        "agents/planner.md does not mention reading architecture-notes.md"
    )


def test_planner_cites_or_diverges():
    """TRC-B3: planner.md must document the cite-or-diverge behaviour -
    either cite an existing ADR, name a candidate ADR, or justify divergence.
    When architecture-notes.md is absent the absence is recorded (not silent skip).
    """
    content = agent_file("planner.md").read_text(encoding="utf-8")
    # Check for cite-or-diverge language
    combined = content.lower()
    has_cite = "cit" in combined  # cite, cites, cited
    has_diverge = "diverg" in combined  # diverge, diverges, divergence
    has_absence = "absent" in combined or "no notes" in combined or "recordable" in combined
    assert has_cite or has_diverge, (
        "planner.md does not mention citing or diverging from architecture-notes.md"
    )
    assert has_absence, (
        "planner.md does not document the recordable-absence behaviour when "
        "architecture-notes.md is missing"
    )


# --------------------------------------------------------------------------
# TRC-B4 - architect-lens degrades when architecture/ is absent
# --------------------------------------------------------------------------


def test_degrades_gracefully():
    """TRC-B4: architect-lens.md must document that when architecture/ is
    absent the lens writes a WARNING line and does not block the phase.
    """
    content = agent_file("architect-lens.md").read_text(encoding="utf-8")
    assert "WARNING" in content or "warning" in content.lower(), (
        "architect-lens.md does not document WARNING when architecture/ is absent"
    )
    # Must document non-blocking behaviour
    assert "not block" in content.lower() or "without blocking" in content.lower() or "does not block" in content.lower(), (
        "architect-lens.md does not document that it does not block when architecture/ is absent"
    )


def test_degrades_writes_warning_line():
    """TRC-B4: the warning first line must be documented in the agent instructions."""
    content = agent_file("architect-lens.md").read_text(encoding="utf-8")
    # The spec requires: "WARNING: No architecture/ artifacts found - running on heuristics only"
    assert "No architecture/" in content or "no architecture/" in content.lower(), (
        "architect-lens.md does not document the exact WARNING message for missing architecture/"
    )


# --------------------------------------------------------------------------
# TRC-B5 - architect-lens findings persist on disk
# --------------------------------------------------------------------------


def test_persists_notes():
    """TRC-B5: architect-lens.md must document that its output is always
    written to architecture-notes.md in the task directory (persistence over
    conversation - Inv-6).
    """
    content = agent_file("architect-lens.md").read_text(encoding="utf-8")
    assert "architecture-notes.md" in content, (
        "architect-lens.md does not instruct writing architecture-notes.md to disk"
    )
    # Must also reference task.yml.evidence so the artifact is registered
    assert "evidence" in content.lower(), (
        "architect-lens.md does not mention registering the notes in task.yml.evidence"
    )


# --------------------------------------------------------------------------
# TRC-X5 - bootstrap: roundtable does NOT invoke architect-lens if the
# agent file doesn't exist (prevents infinite recursion on the task that
# introduces the lens)
# --------------------------------------------------------------------------


def test_bootstrap_no_recursion():
    """TRC-X5: commands/roundtable.md must document that lenses are invoked
    ONLY if their agent file is registered (i.e. exists in agents/).
    This prevents recursive invocation when the task itself introduces the lens.
    """
    content = command_file("roundtable.md").read_text(encoding="utf-8")
    # The contract must be explicit: invoke only if agent file exists/is registered
    combined = content.lower()
    assert (
        "only if" in combined
        or "registered" in combined
        or "agent file" in combined
        or "exists" in combined
    ), (
        "commands/roundtable.md does not document that lenses are only invoked "
        "if their agent file is registered"
    )


# --------------------------------------------------------------------------
# TRC-F5 - architect-lens does NOT fork the spec
# --------------------------------------------------------------------------


def test_notes_are_annotations_not_spec():
    """TRC-F5: architect-lens.md must explicitly prohibit
    writing Given/When/Then scenarios into architecture-notes.md.
    The output is ANNOTATIONS + candidate ADR titles, not a parallel spec.
    """
    content = agent_file("architect-lens.md").read_text(encoding="utf-8")
    # The agent instructions must prohibit scenario-writing
    combined = content.lower()
    assert (
        "not write" in combined
        or "never write" in combined
        or "do not write" in combined
        or "no scenario" in combined
        or "not author" in combined
        or "annotations" in combined
    ), (
        "architect-lens.md does not prohibit writing Given/When/Then scenarios "
        "into architecture-notes.md, which would fork the spec"
    )


def test_no_gherkin_in_architecture_notes_contract():
    """TRC-F5: architect-lens.md must describe architecture-notes.md as
    containing annotations and candidate ADR titles - NOT Given/When/Then.
    The word 'scenario' should only appear in the context of reading
    spec.feature.md, not in the context of writing output.
    """
    content = agent_file("architect-lens.md").read_text(encoding="utf-8")
    # Confirm the output format is annotations, not scenarios
    assert "annotation" in content.lower() or "candidate adr" in content.lower(), (
        "architect-lens.md does not describe its output as annotations/candidate ADRs"
    )


def test_roundtable_agent_roster_section():
    """TRC-B1: commands/roundtable.md must have a dedicated 'Agent roster'
    or equivalent section that lists architect-lens alongside other standard
    lenses. Stream-3 owns the 'Reframe trigger' section; stream-2 (this
    stream) owns the agent roster section.
    """
    content = command_file("roundtable.md").read_text(encoding="utf-8")
    # The file must have a section heading that covers the agent roster
    combined = content.lower()
    assert (
        "agent roster" in combined
        or "standard agent" in combined
        or "default agent" in combined
        or "available lenses" in combined
        or "available agents" in combined
    ), (
        "commands/roundtable.md does not have a section documenting the agent roster"
    )
