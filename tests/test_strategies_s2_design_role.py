"""TRC-C1 - S2 names both governance and design-feedback roles.

Serves: INT-6
Spec: governance/strategies.md S2 section should name:
  - red-before-green as the way to satisfy G1 (governance role)
  - the design-feedback role
  - the framing that TDD is less about testing and more about good design
"""
from __future__ import annotations
from pathlib import Path

STRATEGIES_MD = Path(__file__).parent.parent / "governance" / "strategies.md"


def _read_s2_section() -> str:
    """Extract the S2 section text from strategies.md."""
    text = STRATEGIES_MD.read_text(encoding="utf-8")
    # Find S2 heading and extract until next heading or end
    lines = text.splitlines()
    in_s2 = False
    s2_lines = []
    for line in lines:
        if line.strip().startswith("### S2"):
            in_s2 = True
            s2_lines.append(line)
            continue
        if in_s2:
            # Stop at next strategy heading (### S3 etc) or section heading
            if line.startswith("### S") and not line.startswith("### S2"):
                break
            if line.startswith("## ") or line.startswith("# "):
                break
            s2_lines.append(line)
    return "\n".join(s2_lines)


def test_s2_names_governance_role():
    """S2 must mention satisfying guardrail G1 - the governance role."""
    s2 = _read_s2_section()
    assert "G1" in s2, (
        "S2 section in strategies.md must mention G1 (the governance/guardrail role). "
        f"Found S2 section:\n{s2}"
    )


def test_s2_names_design_feedback_role():
    """S2 must name the design-feedback role explicitly."""
    s2 = _read_s2_section()
    s2_lower = s2.lower()
    assert "design" in s2_lower, (
        "S2 section in strategies.md must name the design-feedback role. "
        f"Found S2 section:\n{s2}"
    )
    # Should have both 'design' and some notion of feedback
    assert any(word in s2_lower for word in ["design-feedback", "design feedback", "good design", "design tool"]), (
        "S2 section must explicitly name the design-feedback role "
        "(design-feedback, good design, or design tool). "
        f"Found S2 section:\n{s2}"
    )


def test_s2_frames_tdd_as_design_tool():
    """S2 must include the framing that TDD is less about testing and more about good design."""
    s2 = _read_s2_section()
    s2_lower = s2.lower()
    assert "less about testing" in s2_lower or "more about" in s2_lower, (
        "S2 must include the framing: 'TDD is less about testing and more about good design'. "
        f"Found S2 section:\n{s2}"
    )
    assert "good design" in s2_lower or "design" in s2_lower, (
        "S2 must reference 'good design' as the framing. "
        f"Found S2 section:\n{s2}"
    )
