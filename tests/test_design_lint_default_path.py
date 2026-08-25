"""`compass design lint` resolves the artifact it is named after.

The command was renamed from `plan lint` to `design lint` and the artifact
from `plan.md` to `technical-design.md`, but the default path was not migrated. With no
`--file` argument it looked for `plan.md`, failed to find it, and then printed
advice about `technical-design.md` - naming one filename in the search and a different
one in the explanation, which cannot both be right.

The effect on a real run: the design stage reports a visible error on every
issue that has a design, and the way past it is a `--file` argument nobody
should need.

Scenario ids: see docs/system-spec.md (group B).
"""

# The vocabulary rename landed on 2026-08-25: the assess and plan stages took
# the names their machine keys, skills and agents already used; `design` went
# back to the designer; design.md became technical-design.md and prd.md became
# intent.md. Spines and documents written before still load and resolve
# (ADR-006), so what moved is the CANONICAL spelling these tests assert - not
# what the framework computes. Re-pointed, not relaxed.
from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CLI = ROOT / "cli" / "compass"

# No placeholder phrase, so a clean lint means the file was read - not that the
# scanner found nothing because it read nothing.
CLEAN_DESIGN = """# Design - demo

## DD-1 - the chosen approach

Chosen: read the value from the spine. Rejected: recompute it on each call,
which would drift from the recorded assessment.
"""

SPINE = """schema_version: "2.0"
task: "demo"
created: "2026-08-13"
status: active
assessment:
  risk: contained
  familiarity: brownfield-mapped
  size: small
  goal: delivery
  role: engineer
  labels: []
delivery_approach: quick-fix
topology: solo
policy_rules_fired: []
stages: {frame: full, specify: light, clarify: collapsed, plan: collapsed,
  distribute: skipped, build: full, verify: light, land: light}
evidence: []
gates: []
scenarios: []
changed_files: []
claims: []
follow_ups: []
reassessments: []
friction: []
"""


def _project(tmp_path: pathlib.Path, *, with_design: bool) -> pathlib.Path:
    work = tmp_path / ".compass" / "work" / "demo"
    work.mkdir(parents=True)
    (tmp_path / ".compass" / "config.yml").write_text(
        "version: 1.0.0\n", encoding="utf-8")
    (tmp_path / ".compass" / "current-task").write_text("demo\n", encoding="utf-8")
    (work / "task.yml").write_text(SPINE, encoding="utf-8")
    if with_design:
        (work / "technical-design.md").write_text(CLEAN_DESIGN, encoding="utf-8")
    return tmp_path


def _lint(project: pathlib.Path):
    return subprocess.run(
        [sys.executable, str(CLI), "design", "lint"],
        cwd=str(project), capture_output=True, text=True, timeout=120,
    )


def test_rcd_b1_defaults_to_design_md(tmp_path):
    """With a technical-design.md present and no --file, the lint must find it."""
    project = _project(tmp_path, with_design=True)
    result = _lint(project)
    combined = result.stdout + result.stderr

    assert "no such file" not in combined.lower(), (
        f"`compass design lint` could not find the technical-design.md sitting in the "
        f"issue directory, so its default path is not the live artifact "
        f"name:\n{combined}"
    )
    assert result.returncode == 0, (
        f"the lint is advisory and must exit 0 when it finds a clean file; "
        f"got {result.returncode}\n{combined}"
    )


def test_rcd_b2_message_names_path_used(tmp_path):
    """When there is nothing to lint, the message must name what it looked for.

    The old error named `plan.md` in the search line and `technical-design.md` in the
    advice below it. A reader following that advice looks for a file the
    command never sought.
    """
    project = _project(tmp_path, with_design=False)
    result = _lint(project)
    combined = result.stdout + result.stderr

    assert "plan.md" not in combined, (
        f"the not-found message still names the retired artifact filename:\n"
        f"{combined}"
    )
    assert "technical-design.md" in combined, (
        f"the message does not name the file it looked for, so a reader "
        f"cannot tell what to create:\n{combined}"
    )
    assert "compass plan lint" not in combined, (
        f"the message labels itself with the retired command name:\n{combined}"
    )
