"""`scripts/multiagent.sh` must seed each worktree with the task's artifacts.

A worktree created by `git worktree add` contains only what git tracks. In a
project that commits `.compass/work/` that is enough - the task directory comes
along with everything else. The framework repository deliberately does NOT
commit its own (`.gitignore`: `/.compass/work/`, `/.compass/current-task`), and
neither does any project that treats task state as local. There, a fresh
worktree arrives with no spec, no plan, and no charter, and `resolve_issue_dir`
raises because there is no work directory to resolve against.

That makes the documented swarm flow unusable in exactly the repository that
documents it. This was found by running `scripts/multiagent.sh` for a real task and
then looking inside the worktree it made.

Spec: .compass/work/executable-bdd-and-richer-plans/acceptance-criteria.md (TRC-E1..E3).
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SWARM = ROOT / "scripts" / "multiagent.sh"
SLUG = "seed-demo"

MAP = """# Distribution Map - seed-demo

## 3. Scenario-group → stream mapping

| Stream | Owns work unit(s) | Owns scenario ids | Branch name |
|---|---|---|---|
| stream-1 | U1 | TRC-A1 | seed-demo/stream-1 |
| stream-2 | U2 | TRC-B1 | seed-demo/stream-2 |
"""

TASK_YML = """schema_version: '1.1'
task: seed-demo
created: '2026-08-03'
status: active
readings:
  blast_radius: contained
  terrain: greenfield
  magnitude: standard
  intent: delivery
  urgency: none
  role: engineer
  touches: []
route: standard
topology: solo-or-pair
fired_guardrails: []
phases:
  frame: full
  specify: full
  clarify: light
  plan: full
  distribute: solo-or-pair
  build: full
  verify: full
  land: full
evidence: []
gates: []
scenarios: []
changed_files: []
claims: []
backfills: []
reframes: []
friction: []
"""


def _git(cwd, *args):
    return subprocess.run(["git", "-C", str(cwd), *args],
                          capture_output=True, text=True, check=True)


@pytest.fixture
def seeded_project(tmp_path):
    """A git repo with one Compass task, whose .compass/work/ is gitignored -
    the arrangement that exposes the gap."""
    repo = tmp_path / "proj"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "T")

    (repo / ".gitignore").write_text("/.compass/work/\n/.compass/current-task\n")
    compass = repo / ".compass"
    (compass / "work" / SLUG).mkdir(parents=True)
    (compass / "config.yml").write_text(
        "version: 1.0.0\nmode: enforced\nswarm:\n"
        f"  worktree_root: \"{tmp_path / 'wt'}\"\n")

    task_dir = compass / "work" / SLUG
    (task_dir / "manifest.yml").write_text(TASK_YML)
    (task_dir / "delivery-approach.md").write_text("# Route - seed-demo\n")
    (task_dir / "distribution-map.md").write_text(MAP)
    (task_dir / "acceptance-criteria.md").write_text("# Spec - seed-demo\n")
    (task_dir / "devlog.md").write_text("# Devlog - seed-demo\n")
    (compass / "current-task").write_text(SLUG + "\n")

    (repo / "README.md").write_text("# demo\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "init")
    return repo, tmp_path / "wt"


def _run_swarm(repo):
    return subprocess.run(
        ["bash", str(SWARM), SLUG],
        cwd=str(repo), capture_output=True, text=True, timeout=120,
    )


# ---------------------------------------------------------------------------
# TRC-E1 - a created worktree carries the task's artifacts
# ---------------------------------------------------------------------------

def test_trc_e1_worktree_carries_task_dir(seeded_project):
    repo, wt_root = seeded_project
    result = _run_swarm(repo)
    assert result.returncode == 0, result.stdout + result.stderr

    for stream in ("stream-1", "stream-2"):
        wt = wt_root / f"{SLUG}-{stream}"
        assert wt.is_dir(), f"{stream} worktree was not created"

        task_dir = wt / ".compass" / "work" / SLUG
        assert task_dir.is_dir(), (
            f"{stream}: the worktree has no task directory - a builder there "
            f"has no spec, no plan and no charter"
        )
        for artifact in ("manifest.yml", "delivery-approach.md", "acceptance-criteria.md",
                         "distribution-map.md"):
            assert (task_dir / artifact).is_file(), (
                f"{stream}: {artifact} did not come across")

        pointer = wt / ".compass" / "current-task"
        assert pointer.is_file(), f"{stream}: no current-task pointer"
        assert pointer.read_text().strip() == SLUG


# ---------------------------------------------------------------------------
# TRC-E2 - a builder in a seeded worktree can resolve its task
# ---------------------------------------------------------------------------

def test_trc_e2_seeded_worktree_resolves_task(seeded_project):
    repo, wt_root = seeded_project
    assert _run_swarm(repo).returncode == 0

    wt = wt_root / f"{SLUG}-stream-1"
    result = subprocess.run(
        [sys.executable, str(ROOT / "cli" / "compass"), "next"],
        cwd=str(wt), capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, (
        "a builder in a seeded worktree cannot resolve its task:\n"
        f"{result.stdout}\n{result.stderr}")
    assert "no tasks found" not in (result.stdout + result.stderr)


# ---------------------------------------------------------------------------
# TRC-E3 - re-running the swarm does not clobber a builder's work
# ---------------------------------------------------------------------------

def test_trc_e3_reseeding_is_non_destructive(seeded_project):
    """multiagent.sh documents itself as idempotent: an existing worktree is left
    as-is. A seeding step that copied unconditionally would break that on the
    second run - the run where a builder has work to lose."""
    repo, wt_root = seeded_project
    assert _run_swarm(repo).returncode == 0

    devlog = wt_root / f"{SLUG}-stream-1" / ".compass" / "work" / SLUG / "devlog.md"
    devlog.write_text("# Devlog - seed-demo\n\n## builder entry that must survive\n")

    result = _run_swarm(repo)
    assert result.returncode == 0, result.stdout + result.stderr

    assert "builder entry that must survive" in devlog.read_text(), (
        "re-running multiagent.sh overwrote a builder's devlog entry"
    )
