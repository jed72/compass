"""The stop hook checks the artifacts that exist today.

Found by adding hooks/ to the vocabulary scan, which is the argument for
adding it: two of this hook's checks named artifacts the v2 rename retired,
and neither could reach a correct verdict any more.

  * The reproduction-scenario check read `spec.feature.md`, with no fallback
    to `acceptance-criteria.md`. On every issue written since the rename that
    file is absent, so the hook took the "does not exist" branch and reported
    "the reproduction test was never promoted to a scenario" - on hotfixes
    where it demonstrably had been. A check that can no longer succeed is the
    mirror image of one that can no longer fail, and it is worse in one
    respect: it trains people to ignore it.

  * The outstanding-follow-up scan looked for a section headed "Owed
    backfills". The template writes "Outstanding follow-ups", so the scan
    matched nothing and the check never fired.

Both are the same defect as `compass check`'s placeholder header: a value
renamed on one side of a boundary and not the other, invisible because
nothing failed.

Scenario ids: see docs/system-spec.md (group G).
"""
from __future__ import annotations

import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
HOOK = ROOT / "hooks" / "stop.sh"

# The fixture is built from the SHIPPED TEMPLATE, not hand-typed. The first
# version of this file invented `**Reference approach:**` and
# `## Outstanding follow-ups` - neither of which appears in
# templates/delivery-approach.md or in any archived record - so the test proved
# only that the regex matched a string written for the test. That is the exact
# defect it was written to catch, one level up.
TEMPLATE = (ROOT / "templates" / "delivery-approach.md").read_text(encoding="utf-8")


def _hotfix_record() -> str:
    """A delivery-approach record shaped like the template's, for a hotfix.

    Fills the template's approach placeholder rather than replacing its
    headings, so if the template's wording changes this fixture changes with
    it and the hook's detector has to keep up.
    """
    text = TEMPLATE.replace(
        "{{quick fix | feature | initiative | hotfix | spike}}", "hotfix")
    return text + "\n- [ ] FU-1 promote the reproduction test into a scenario\n"


SPEC_WITH_REPRO = """# Acceptance criteria - demo

### SCN-1 - the reproduction, promoted

```gherkin
Given the defect reproduces
 When the fix is applied
 Then the regression test covers it
```
"""


SPINE = '''schema_version: "2.0"
task: "demo"
created: "2026-08-13"
status: active
assessment: {risk: contained, familiarity: brownfield-mapped, size: small,
  goal: delivery, urgency: live-defect, role: engineer, labels: []}
delivery_approach: hotfix
topology: solo
policy_rules_fired: []
stages: {frame: full, specify: light, clarify: collapsed, plan: collapsed,
  distribute: skipped, build: full, verify: full, land: full}
evidence: []
gates: []
scenarios: []
changed_files: []
claims: []
follow_ups:
- id: FU-1
  status: outstanding
  description: promote the reproduction test into a real scenario
reassessments: []
friction: []
'''


def _project(tmp_path, *, spec_body=None, spec_name="acceptance-criteria.md"):
    work = tmp_path / ".compass" / "work" / "demo"
    work.mkdir(parents=True)
    (tmp_path / ".compass" / "config.yml").write_text(
        "version: 1.0.0\n", encoding="utf-8")
    (work / "manifest.yml").write_text(SPINE, encoding="utf-8")
    (work / "delivery-approach.md").write_text(_hotfix_record(), encoding="utf-8")
    if spec_body is not None:
        (work / spec_name).write_text(spec_body, encoding="utf-8")
    return tmp_path


def _run(project):
    return subprocess.run(
        ["bash", str(HOOK)], input="{}", cwd=str(project),
        capture_output=True, text=True, timeout=120,
        env={"PATH": "/usr/bin:/bin:/usr/local/bin", "HOME": str(project),
             "CLAUDE_PROJECT_DIR": str(project)},
    )


def test_a_promoted_reproduction_is_recognised(tmp_path):
    """The live acceptance artifact, with a reproduction scenario in it."""
    project = _project(tmp_path, spec_body=SPEC_WITH_REPRO)
    out = _run(project).stderr

    assert "never promoted" not in out and "does not exist" not in out, (
        f"the hook reported the reproduction scenario missing, though "
        f"acceptance-criteria.md contains one - it is still reading the "
        f"retired artifact name:\n{out}"
    )


def test_a_missing_reproduction_is_still_reported(tmp_path):
    """The control. Reading the live artifact must not stop the check firing."""
    project = _project(tmp_path, spec_body="# Acceptance criteria - demo\n")
    out = _run(project).stderr

    assert "reproduction" in out.lower(), (
        f"a hotfix whose acceptance criteria contain no reproduction scenario "
        f"was not reported:\n{out}"
    )


def test_an_outstanding_follow_up_is_reported(tmp_path):
    """The section scan must match the heading the template actually writes."""
    project = _project(tmp_path, spec_body=SPEC_WITH_REPRO)
    out = _run(project).stderr

    assert "follow-up" in out.lower() or "follow up" in out.lower(), (
        f"the unchecked item under 'Outstanding follow-ups' was not reported - "
        f"the scan is still looking for the retired section heading:\n{out}"
    )
