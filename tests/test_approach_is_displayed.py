"""The computed delivery approach is displayed, not a placeholder.

The v2 rename moved the spine key from `route` to `delivery_approach`. Two
display sites kept reading the old key, so both fell to their default:

    check_cmd.py:264   f"(route: {task.get('route', '?')})"
    flow.py:141        route = t.get("route", "?")

`compass check`'s header printed `route: ?` on every run, and the cross-issue
board printed `route=?` on every row - confirmed against all 18 in-flight
issues in this repository. The value was sitting in the spine the whole time.

Neither was caught by the vocabulary scan, which covers `cli/compass_pkg/`,
because it skipped string literals with no whitespace as machine identifiers -
and `'route'` is exactly that shape. ADR-015 records the widening.

Spec: .compass/work/rehearsal-cli-defects/acceptance-criteria.md (group E).
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CLI = ROOT / "cli" / "compass"

SPINE = """schema_version: "2.0"
task: "{slug}"
created: "2026-08-13"
status: {status}
assessment:
  risk: contained
  familiarity: brownfield-mapped
  size: small
  goal: delivery
  role: engineer
  labels: []
delivery_approach: {approach}
topology: solo
policy_rules_fired: []
stages: {{frame: full, specify: light, clarify: collapsed, plan: collapsed,
  distribute: skipped, build: full, verify: light, land: light}}
evidence: []
gates: []
scenarios: []
changed_files: []
claims: []
follow_ups: []
reassessments: []
friction: []
"""


def _project(tmp_path: pathlib.Path, issues) -> pathlib.Path:
    (tmp_path / ".compass").mkdir(parents=True)
    (tmp_path / ".compass" / "config.yml").write_text(
        "version: 1.0.0\nmode: enforced\n", encoding="utf-8")
    for slug, approach, status in issues:
        work = tmp_path / ".compass" / "work" / slug
        work.mkdir(parents=True)
        (work / "task.yml").write_text(
            SPINE.format(slug=slug, approach=approach, status=status),
            encoding="utf-8")
        (work / "delivery-approach.md").write_text("# approach\n", encoding="utf-8")
    (tmp_path / ".compass" / "current-task").write_text(
        issues[0][0] + "\n", encoding="utf-8")
    shutil.copytree(ROOT / "governance", tmp_path / "governance")
    shutil.copytree(ROOT / "schemas", tmp_path / "schemas")
    return tmp_path


def _run(project, *argv):
    return subprocess.run(
        [sys.executable, str(CLI), *argv],
        cwd=str(project), capture_output=True, text=True, timeout=180,
    )


def _header(text):
    for line in text.splitlines():
        if line.startswith("compass check - "):
            return line
    return ""


def test_rcd_e1_check_header_names_approach(tmp_path):
    project = _project(tmp_path, [("demo", "feature", "active")])
    result = _run(project, "check", "--issue", "demo")
    header = _header(result.stdout + result.stderr)

    assert header, f"no header line in:\n{result.stdout}\n{result.stderr}"
    assert "feature" in header, (
        f"the header does not name the issue's computed approach:\n  {header}"
    )
    assert "?" not in header, (
        f"the header still prints a placeholder where the approach belongs:\n"
        f"  {header}"
    )


def test_rcd_e2_flow_board_names_approach(tmp_path):
    project = _project(tmp_path, [
        ("alpha", "feature", "active"),
        ("beta", "quick-fix", "active"),
    ])
    result = _run(project, "flow")
    out = result.stdout + result.stderr

    rows = [ln for ln in out.splitlines()
            if "alpha" in ln or "beta" in ln]
    assert rows, f"no issue rows on the board:\n{out}"

    assert "feature" in out and "quick-fix" in out, (
        f"the board does not name each issue's computed approach:\n{out}"
    )
    for row in rows:
        assert "=?" not in row and ": ?" not in row, (
            f"a board row still prints a placeholder for the approach:\n"
            f"  {row}"
        )


def test_rcd_e2b_an_unreadable_spine_is_still_surfaced(tmp_path):
    """The control: a spine that cannot be read must not vanish from the board.

    Reading a different key could have turned an unreadable issue into a
    silently absent one, which is worse than the placeholder this change
    removes - a row that says "I could not read this" is information, and a
    missing row is not.

    Note what this does NOT assert. An unreadable issue is reported by being
    grouped as unreadable with a reason, not by printing "?" in the approach
    column. An earlier version of this test looked for the "?" and failed
    against correct behaviour: the placeholder is in the internal tuple but
    was never displayed for this group.
    """
    project = _project(tmp_path, [("alpha", "feature", "active")])
    broken = project / ".compass" / "work" / "broken"
    broken.mkdir(parents=True)
    (broken / "task.yml").write_text("{[not: valid yaml\n", encoding="utf-8")

    out = _run(project, "flow").stdout
    row = [ln for ln in out.splitlines() if "broken" in ln]

    assert row, f"the unreadable issue is missing from the board entirely:\n{out}"
    assert "unreadable" in row[0].lower(), (
        f"the board lists the issue but does not say its spine could not be "
        f"read:\n  {row[0]}"
    )
