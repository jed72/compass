"""Tests for invisible triggering - TRC-C1, TRC-C2, TRC-C3, TRC-F3.

These are static content-assertion tests. Invisible triggering is prompt-only
(no new hook code). The test strategy:
  - Read CLAUDE.md and assert the intent-triggering rule paragraph is present.
  - Read each agent file and assert the supporting sentence is present.
  - Assert the rule does NOT instruct re-running Frame when a framed task is
    already active (TRC-F3 guard).
  - Assert the rule is ADDITIVE (the existing "Never skip Frame" text still
    present and untouched).

Manual-verification note (TRC-C1 / TRC-C3 behaviour at runtime):
  These tests verify the static content that produces the agent behaviour.
  The runtime behaviour (agent actually calling /compass:assess on natural-
  language intent) requires a live agent session; that is recorded as
  manual-review evidence in task.yml (EV-MANUAL-C1, EV-MANUAL-C3).
"""

# The vocabulary rename landed on 2026-08-25: the assess and plan stages took
# the names their machine keys, skills and agents already used; `design` went
# back to the designer; design.md became technical-design.md and prd.md became
# intent.md. Spines and documents written before still load and resolve
# (ADR-006), so what moved is the CANONICAL spelling these tests assert - not
# what the framework computes. Re-pointed, not relaxed.
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

CLAUDE_MD = REPO_ROOT / "CLAUDE.md"
AGENTS = {
    "spec-author": REPO_ROOT / "agents" / "spec-author.md",
    "planner":     REPO_ROOT / "agents" / "planner.md",
    "builder":     REPO_ROOT / "agents" / "builder.md",
    "orchestrator": REPO_ROOT / "agents" / "orchestrator.md",
}

# The exact paragraph that DD-6 requires (from plan.md §DD-6). The wording
# moved to the frozen v2 vocabulary in the session-instructions rename
# slice; the rule it pins is unchanged.
DD6_HEADING = "**Trigger triage on intent, not just the literal command.**"
DD6_CONTENT = (
    "When the user describes intent to build, change, or fix code"
    " - even if they do not type `/compass:assess` - "
    "invoke `/compass:assess` before any artifact-changing tool call."
)

# The existing paragraph that must remain untouched (additive-only check)
EXISTING_PARAGRAPH = "**Never skip triage.**"

# The phrase that must NOT appear as a re-frame trigger when a task is already
# active (TRC-F3 guard: invisible triggering must not re-frame an active task)
RE_FRAME_TRIGGER_PHRASES = [
    "re-run /compass:assess",
    "re-frame the task",
    "run /compass:assess again",
    "invoke /compass:assess again",
]

# Supporting sentence that must appear in each agent description
# The sentence follows the command rename: triage, not Frame.
AGENT_TRIGGER_SENTENCE = "Trigger triage on intent"


class TestCLAUDEMdInvisibleTriggering:
    """TRC-C1 / TRC-C2 / TRC-C3 - CLAUDE.md carries the intent-trigger rule."""

    def test_claude_md_exists(self):
        """CLAUDE.md must exist."""
        assert CLAUDE_MD.is_file(), f"CLAUDE.md not found at {CLAUDE_MD}"

    def test_intent_trigger_heading_present(self):
        """TRC-C1 / TRC-C3 - CLAUDE.md must contain the DD-6 trigger heading."""
        content = CLAUDE_MD.read_text(encoding="utf-8")
        assert DD6_HEADING in content, (
            f"CLAUDE.md is missing the intent-trigger heading:\n  {DD6_HEADING!r}\n"
            "Add the DD-6 paragraph per plan.md §DD-6."
        )

    def test_intent_trigger_content_present(self):
        """TRC-C1 / TRC-C3 - CLAUDE.md must contain the DD-6 trigger body."""
        content = CLAUDE_MD.read_text(encoding="utf-8")
        assert DD6_CONTENT in content, (
            "CLAUDE.md is missing the intent-trigger body text. "
            "Add the DD-6 paragraph per plan.md §DD-6."
        )

    def test_explicit_invocation_still_works(self):
        """TRC-C2 - CLAUDE.md must state that explicit invocation always works."""
        content = CLAUDE_MD.read_text(encoding="utf-8")
        assert "Explicit invocation of any Compass command always works" in content, (
            "CLAUDE.md must clarify that explicit invocation still works "
            "(TRC-C2 / BR-011 additive-not-replacement). "
            "Add the clarifying phrase per plan.md §DD-6."
        )

    def test_existing_never_skip_frame_preserved(self):
        """TRC-C2 - the existing 'Never skip Frame' paragraph is untouched."""
        content = CLAUDE_MD.read_text(encoding="utf-8")
        assert EXISTING_PARAGRAPH in content, (
            f"The existing paragraph {EXISTING_PARAGRAPH!r} is missing from "
            "CLAUDE.md. The DD-6 edit must be ADDITIVE - do not replace existing text."
        )

    def test_never_skip_frame_comes_before_trigger_rule(self):
        """The new rule is added AFTER the existing paragraph, not before."""
        content = CLAUDE_MD.read_text(encoding="utf-8")
        existing_pos = content.find(EXISTING_PARAGRAPH)
        trigger_pos = content.find(DD6_HEADING)
        assert existing_pos != -1, "Existing 'Never skip Frame' paragraph not found."
        assert trigger_pos != -1, "Trigger heading not found."
        assert existing_pos < trigger_pos, (
            "The DD-6 trigger heading must appear AFTER the existing "
            "'Never skip Frame' paragraph. Current ordering is reversed."
        )


class TestCLAUDEMdNoReframe:
    """TRC-F3 - invisible triggering must NOT instruct re-framing an active task."""

    def test_no_re_frame_trigger_phrases(self):
        """TRC-F3 - CLAUDE.md must not instruct re-running Frame on an active task."""
        content = CLAUDE_MD.read_text(encoding="utf-8").lower()
        # Check around the intent-trigger paragraph specifically
        trigger_idx = content.find("trigger triage on intent")
        if trigger_idx == -1:
            # If paragraph not yet there, the test for its presence will catch it
            return
        # Look at a window around the trigger paragraph (500 chars each side)
        window = content[max(0, trigger_idx - 100):trigger_idx + 500]
        for phrase in RE_FRAME_TRIGGER_PHRASES:
            assert phrase not in window, (
                f"TRC-F3 violation: the invisible-triggering paragraph must not "
                f"instruct re-running Frame when a task is already framed. "
                f"Found {phrase!r} near the trigger paragraph."
            )


class TestAgentDescriptionsTrigger:
    """TRC-C1 / TRC-C3 - agent descriptions mention the intent-trigger."""

    def test_spec_author_has_trigger_sentence(self):
        """spec-author.md must mention intent-driven Frame triggering."""
        content = AGENTS["spec-author"].read_text(encoding="utf-8")
        assert AGENT_TRIGGER_SENTENCE in content, (
            f"agents/spec-author.md is missing the intent-trigger sentence "
            f"(must contain: {AGENT_TRIGGER_SENTENCE!r}). "
            "Add one supporting sentence per plan.md §DD-6."
        )

    def test_planner_has_trigger_sentence(self):
        """planner.md must mention intent-driven Frame triggering."""
        content = AGENTS["planner"].read_text(encoding="utf-8")
        assert AGENT_TRIGGER_SENTENCE in content, (
            f"agents/planner.md is missing the intent-trigger sentence "
            f"(must contain: {AGENT_TRIGGER_SENTENCE!r})."
        )

    def test_builder_has_trigger_sentence(self):
        """builder.md must mention intent-driven Frame triggering."""
        content = AGENTS["builder"].read_text(encoding="utf-8")
        assert AGENT_TRIGGER_SENTENCE in content, (
            f"agents/builder.md is missing the intent-trigger sentence "
            f"(must contain: {AGENT_TRIGGER_SENTENCE!r})."
        )

    def test_orchestrator_has_trigger_sentence(self):
        """orchestrator.md must mention intent-driven Frame triggering."""
        content = AGENTS["orchestrator"].read_text(encoding="utf-8")
        assert AGENT_TRIGGER_SENTENCE in content, (
            f"agents/orchestrator.md is missing the intent-trigger sentence "
            f"(must contain: {AGENT_TRIGGER_SENTENCE!r})."
        )
