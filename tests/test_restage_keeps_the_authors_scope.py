"""Shipping commits what the author staged, not the issue's whole scope.

Reported from the field (GitHub #58, filed against 2.0.0 and reproduced on
3.1.1). `_restage_owned()` recovers from a pre-commit hook that rewrites a
staged file, by re-adding what was staged. It also re-added the issue's entire
`changed_files:` list.

For any issue landed as a SEQUENCE of commits - normal for anything
non-trivial - that list names files belonging to commits not yet made. So the
author stages commit 1, a formatter fires, the retry runs, and commit 1
silently grows to the issue's whole declared scope.

What that did in the field: a module was landed as two commits - step
definitions first, then the registration that imports them. The re-stage
pulled the registration into the earlier commit, which then referenced a
module that did not exist yet and failed at collection when checked out
standalone. CI never saw it, because CI only builds the branch tip. It
surfaced only because each commit was checked out into a clean worktree.

The function's own docstring already argued against this: "Never `git add
-A`... so a hook that reformats fifty unrelated files cannot smuggle them into
the commit". The `owned` loop did not smuggle in unrelated files; it smuggled
in not-yet-ready ones.

Scenario ids: see .compass/work/field-feedback-hook-scope-and-restage/
acceptance-criteria.md.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CLI = ROOT / "cli" / "compass"


def _git(args, cwd):
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True,
                          text=True, timeout=60)


def _repo(tmp_path):
    """A repo mid-issue: two modules declared, only the first staged."""
    root = tmp_path / "repo"
    (root / "src").mkdir(parents=True)
    _git(["init", "-q", "-b", "main"], root)
    _git(["config", "user.email", "t@example.invalid"], root)
    _git(["config", "user.name", "Test"], root)

    work = root / ".compass" / "work" / "demo"
    work.mkdir(parents=True)
    (root / ".compass" / "config.yml").write_text("version: 1.0.0\n")
    (root / ".compass" / "current-task").write_text("demo\n")
    (work / "task.yml").write_text(
        'schema_version: "2.0"\ntask: demo\ncreated: "2026-08-14"\n'
        'status: active\ndelivery_approach: feature\n'
        'assessment:\n  risk: contained\n  familiarity: brownfield-mapped\n'
        '  size: small\n  goal: delivery\n  role: engineer\n  labels: []\n'
        'changed_files:\n'
        '  - path: src/steps.py\n    scenarios: [FF-3]\n'
        '  - path: src/registration.py\n    scenarios: [FF-3]\n')
    (work / "delivery-approach.md").write_text("# Delivery approach\n")

    (root / "src" / "steps.py").write_text("STEP = 1\n")
    (root / "src" / "registration.py").write_text("from steps import STEP\n")

    _git(["add", "-A"], root)
    _git(["commit", "-qm", "base"], root)

    # Now the issue's work: both modules change, but only the first is staged
    # for THIS commit. The second belongs to the next one.
    (root / "src" / "steps.py").write_text("STEP = 2\n")
    (root / "src" / "registration.py").write_text("from steps import STEP  # 2\n")
    # The issue's own artifacts move too - a devlog entry written as the work
    # happens. Without an actual change here the artifact directory has
    # nothing to re-stage, and FF-4 would pass whatever the code did.
    (work / "devlog.md").write_text("# Devlog\n\nStaged the steps.\n")
    _git(["add", "--", "src/steps.py"], root)

    # An auto-fixing pre-commit hook: it rewrites the staged file AND fails,
    # which is what ruff-format, black and prettier do under the pre-commit
    # framework. The failure is what forces ship-commit's retry path - the
    # path _restage_owned lives on.
    #
    # An earlier version of this fixture only rewrote the file. The commit
    # then succeeded first time (the rewrite was unstaged, so the index was
    # unchanged), the retry never ran, and this test passed without exercising
    # a single line of the code it exists to test.
    hooks = root / ".git" / "hooks"
    hooks.mkdir(parents=True, exist_ok=True)
    pc = hooks / "pre-commit"
    pc.write_text(
        "#!/bin/sh\n"
        "if [ ! -f .git/formatted ]; then\n"
        "  printf '# formatted\\n' >> src/steps.py\n"
        "  touch .git/formatted\n"
        "  exit 1\n"
        "fi\n"
        "exit 0\n")
    pc.chmod(0o755)
    return root


def _ship(root):
    return subprocess.run(
        [sys.executable, str(CLI), "ship-commit", "--issue", "demo",
         "-m", "commit one: the steps only"],
        cwd=str(root), capture_output=True, text=True, timeout=120)


def test_ff_3_restage_does_not_widen_the_commit(tmp_path):
    root = _repo(tmp_path)
    r = _ship(root)
    assert r.returncode == 0, f"{r.stdout}{r.stderr}"

    committed = _git(["show", "--name-only", "--pretty=format:", "HEAD"],
                     root).stdout.split()

    assert "src/steps.py" in committed, (
        f"the file the author staged is not in the commit: {committed}")
    assert "src/registration.py" not in committed, (
        f"the commit was widened to the issue's whole declared scope. "
        f"src/registration.py was staged for a LATER commit and is now in "
        f"this one, which makes this commit reference code it does not "
        f"contain: {committed}")


def test_ff_4_artifacts_are_still_restaged(tmp_path):
    """The control: the re-stage must keep doing what it exists for.

    Dropping the whole re-stage would satisfy FF-3 while re-opening the case
    it was written for - a hook rewrite leaving the commit without the
    issue's own artifacts.
    """
    root = _repo(tmp_path)
    r = _ship(root)
    assert r.returncode == 0, f"{r.stdout}{r.stderr}"

    committed = _git(["show", "--name-only", "--pretty=format:", "HEAD"],
                     root).stdout
    assert ".compass/work/demo" in committed, (
        f"the issue's artifact directory is missing from the commit:\n"
        f"{committed}")
