"""The pre-tool hook finds the project it is enforcing, or refuses.

`PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"` assumed the working directory
is the repository root. When Claude Code is started anywhere else - a
subdirectory, or a parent - the hook looked for `.compass/` in the wrong
place, found nothing, and blocked every code edit while reporting that triage
had not run. It had.

Two failures in one line. The resolution was wrong, and the diagnostic named
a cause that was not the cause, which cost a demo rehearsal a symlink
workaround before anyone questioned the message.

The fix walks up from the working directory, and refuses when it finds
nothing - an enforcement path that cannot tell what it is enforcing must
never wave an edit through. That is the same failure 2.1.0 fixed one layer
down, where a missing vendored library made this hook exit 3 and the runtime
read it as "allow".

Scenario ids: see docs/system-spec.md (group A).
"""
from __future__ import annotations

import json
import pathlib
import shutil
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
HOOK = ROOT / "hooks" / "pre-tool.sh"

BLOCK, ALLOW = 2, 0

SPINE = """schema_version: "2.0"
task: "{slug}"
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


def _project(tmp_path: pathlib.Path, *, with_work: bool = True) -> pathlib.Path:
    """A minimal project tree: .compass/ with one triaged issue."""
    proj = tmp_path / "proj"
    (proj / "src" / "deep" / "deeper").mkdir(parents=True)
    (proj / "src" / "app.py").write_text("x = 1\n", encoding="utf-8")
    compass = proj / ".compass"
    compass.mkdir()
    (compass / "config.yml").write_text("version: 1.0.0\n", encoding="utf-8")
    if with_work:
        work = compass / "work" / "demo"
        work.mkdir(parents=True)
        (work / "task.yml").write_text(SPINE.format(slug="demo"), encoding="utf-8")
        (work / "delivery-approach.md").write_text("# approach\n", encoding="utf-8")
        (compass / "current-task").write_text("demo\n", encoding="utf-8")
        # The `.red` marker matters to the test, not just to the fixture: it
        # is what makes a correctly-resolved project ALLOW the edit. Without
        # it both the resolved and the unresolved case block - for completely
        # different reasons - and a test comparing exit codes passes while
        # measuring nothing. The first version of this file did exactly that.
        (work / ".red").write_text("", encoding="utf-8")
    return proj


def _run(cwd: pathlib.Path, target: pathlib.Path, env_project=None):
    """Invoke the hook as the runtime does: JSON on stdin, verdict as exit code."""
    payload = json.dumps({
        "tool_name": "Edit",
        "tool_input": {"file_path": str(target)},
    })
    env = {"PATH": "/usr/bin:/bin:/usr/local/bin", "HOME": str(cwd)}
    if env_project is not None:
        env["CLAUDE_PROJECT_DIR"] = str(env_project)
    return subprocess.run(
        ["bash", str(HOOK)], input=payload, cwd=str(cwd),
        capture_output=True, text=True, timeout=120, env=env,
    )


def test_rcd_a1_resolves_from_subdirectory(tmp_path):
    """The verdict must not depend on which directory the session started in."""
    proj = _project(tmp_path)
    target = proj / "src" / "app.py"

    from_root = _run(proj, target)
    from_deep = _run(proj / "src" / "deep" / "deeper", target)

    assert from_deep.returncode == from_root.returncode, (
        f"the hook gave a different verdict from a subdirectory "
        f"(root={from_root.returncode}, subdir={from_deep.returncode}). It "
        f"resolved a different project root, so it enforced a different "
        f"issue - or none.\nsubdir stderr: {from_deep.stderr}"
    )


def test_rcd_a2_unresolvable_root_blocks(tmp_path):
    """No .compass/ anywhere above: refuse, never wave through.

    The control that matters. A hook that cannot find what it is enforcing
    has two options, and exactly one of them is safe.
    """
    outside = tmp_path / "elsewhere"
    (outside / "src").mkdir(parents=True)
    target = outside / "src" / "app.py"
    target.write_text("x = 1\n", encoding="utf-8")

    result = _run(outside, target)

    assert result.returncode == BLOCK, (
        f"the hook exited {result.returncode} with no project to enforce. "
        f"Anything but {BLOCK} lets the edit through, which is a guardrail "
        f"switched off silently.\nstderr: {result.stderr}"
    )
    assert result.stderr.strip(), (
        "the hook blocked without saying why - the failure 2.1.0 fixed one "
        "layer down was exactly a silent refusal"
    )


def test_rcd_a3_message_names_real_cause(tmp_path):
    """The diagnostic must not blame triage for a resolution failure."""
    outside = tmp_path / "elsewhere"
    (outside / "src").mkdir(parents=True)
    target = outside / "src" / "app.py"
    target.write_text("x = 1\n", encoding="utf-8")

    err = _run(outside, target).stderr.lower()

    assert "could not locate" in err or "no compass project" in err, (
        f"the message does not say that the project directory could not be "
        f"located:\n{err}"
    )
    assert str(outside).lower() in err, (
        f"the message does not name the directory it searched from, so a "
        f"reader cannot tell where it looked:\n{err}"
    )
    assert "triage" not in err or "could not locate" in err.split("triage")[0], (
        f"the message still blames triage for a resolution failure. That is "
        f"the misdiagnosis that cost the rehearsal a symlink workaround:\n{err}"
    )


def test_rcd_a4_missing_work_dir_still_says_so(tmp_path):
    """The control for A3: a genuine 'triage has not run' still says so.

    Without this, A3 passes against a hook that has simply stopped telling
    the two cases apart.
    """
    proj = _project(tmp_path, with_work=False)
    target = proj / "src" / "app.py"

    result = _run(proj, target)
    err = result.stderr.lower()

    assert result.returncode == BLOCK, (
        f"a project with no triaged issue must block, got {result.returncode}"
    )
    assert "triage" in err, (
        f"the hook resolved the project but did not say that triage has not "
        f"run - the two failures are now indistinguishable in the other "
        f"direction:\n{err}"
    )


def test_rcd_a2b_the_walk_does_not_escape_the_repository(tmp_path):
    """A project with no .compass/ must not inherit an ancestor's issue.

    Found at the verify stage, in the security dimension, in this issue's own
    fix. Walking up from the working directory is right; walking up *without
    a bound* is not. A user working in a repository that has never been
    triaged, underneath a parent that happens to hold a .compass/ - a
    monorepo, or a stray one in $HOME - would have the hook resolve the
    stranger's issue and enforce it. If that issue happens to hold a `.red`
    marker, the edit is ALLOWED: a fail-open path, in the fix whose whole
    purpose was to close one.

    The repository is the outer bound of a project. A directory holding .git
    and no .compass/ is a project that has not been triaged, and the honest
    answer there is to refuse, not to borrow someone else's answer.
    """
    outer = tmp_path / "outer"
    (outer / ".compass" / "work" / "someone-elses").mkdir(parents=True)
    (outer / ".compass" / "config.yml").write_text("version: 1.0.0\n", encoding="utf-8")
    (outer / ".compass" / "work" / "someone-elses" / "task.yml").write_text(
        SPINE.format(slug="someone-elses"), encoding="utf-8")
    (outer / ".compass" / "work" / "someone-elses" / "delivery-approach.md").write_text(
        "# approach\n", encoding="utf-8")
    (outer / ".compass" / "current-task").write_text("someone-elses\n", encoding="utf-8")
    # The stranger's issue is mid-red, which is what makes this dangerous:
    # inheriting it would permit the edit rather than merely mis-report.
    (outer / ".compass" / "work" / "someone-elses" / ".red").write_text("", encoding="utf-8")

    inner = outer / "untriaged-repo"
    (inner / ".git").mkdir(parents=True)
    (inner / "src").mkdir()
    target = inner / "src" / "app.py"
    target.write_text("x = 1\n", encoding="utf-8")

    result = _run(inner, target)

    assert result.returncode == BLOCK, (
        f"the hook exited {result.returncode} for an untriaged repository, "
        f"by resolving a .compass/ above it. That enforces a stranger's "
        f"issue - and because that issue is mid-red, it ALLOWS the edit.\n"
        f"stderr: {result.stderr}"
    )
    assert "someone-elses" not in result.stderr, (
        f"the hook named another project's issue:\n{result.stderr}"
    )


def test_rcd_a4b_a_project_before_its_first_triage_is_told_to_triage(tmp_path):
    """An explicit project root with no .compass/ yet means triage, not lost.

    Every project's first edit hits this. `.compass/` does not exist until
    triage runs, so treating "no .compass/ here" as "I could not find your
    project" tells the author to fix a working directory that is already
    correct, or to set a variable that is already set. That is the same fault
    the resolution fix was written to remove, one branch earlier.
    """
    proj = tmp_path / "fresh"
    (proj / "src").mkdir(parents=True)
    target = proj / "src" / "app.py"
    target.write_text("x = 1\n", encoding="utf-8")

    result = _run(proj, target, env_project=proj)
    err = result.stderr.lower()

    assert result.returncode == BLOCK, "an untriaged project must still block"
    assert "triage" in err, (
        f"the hook did not mention triage on a project that simply has not "
        f"been triaged yet:\n{err}"
    )
    assert "could not locate" not in err, (
        f"the hook claims it could not find the project, though the project "
        f"root was given to it explicitly:\n{err}"
    )


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash required")
def test_rcd_a1b_explicit_project_dir_still_wins(tmp_path):
    """CLAUDE_PROJECT_DIR stays authoritative when the host sets it.

    The fix replaces the *fallback*, not the contract. Without this, a change
    that ignored the variable entirely would pass every scenario above.
    """
    proj = _project(tmp_path)
    target = proj / "src" / "app.py"

    explicit = _run(tmp_path, target, env_project=proj)
    implicit = _run(proj, target)

    assert explicit.returncode == implicit.returncode, (
        f"setting CLAUDE_PROJECT_DIR gave a different verdict "
        f"({explicit.returncode}) than resolving from inside the project "
        f"({implicit.returncode})\nstderr: {explicit.stderr}"
    )
