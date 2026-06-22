"""TRC-1 — scripts/swarm.sh strips markdown punctuation from branch-name cells.

The distribution-map.md §3 table has a fourth cell for the branch name. Users
may format that cell with backticks or bold for readability — the parser must
treat the cell value as a clean git ref name, not the literal-with-markdown
string.

Spec: .compass/work/swarm-script-strips-markdown/spec.feature.md (TRC-1).
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest


FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent
SWARM_SH = FRAMEWORK_ROOT / "scripts" / "swarm.sh"


def _init_project(project: Path) -> None:
    """Create a minimal git project at `project` with one commit on the default branch."""
    project.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=project, check=True)
    (project / "README.md").write_text("scaffold for swarm.sh test")
    subprocess.run(
        ["git", "-C", str(project), "add", "README.md"], check=True
    )
    subprocess.run(
        [
            "git", "-C", str(project),
            "-c", "user.email=test@example.com",
            "-c", "user.name=Test",
            "commit", "-q", "-m", "init",
        ],
        check=True,
    )


def _write_task_artifacts(task_dir: Path, branch_cell: str) -> None:
    """Write minimal route.md + distribution-map.md so swarm.sh runs.

    swarm.sh requires route.md to be present (Frame's output) and reads
    distribution-map.md to parse the streams. The route content is not deeply
    inspected beyond a grep for "Blast radius: critical" (which we don't set),
    so a stub is enough.
    """
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "route.md").write_text(
        f"# Route — {task_dir.name}\n\nReference route: Standard\n"
    )
    # R4: the worktree cap is read from task.yml (readings.blast_radius +
    # fired_guardrails), not route.md prose — so the fixture must provide it.
    (task_dir / "task.yml").write_text(
        f"task: {task_dir.name}\n"
        "readings:\n"
        "  blast_radius: contained\n"
        "  terrain: brownfield-mapped\n"
        "  magnitude: small\n"
        "  intent: delivery\n"
        "fired_guardrails: []\n"
    )
    map_md = (
        f"# Distribution Map — {task_dir.name}\n"
        "\n"
        "## 3. Scenario-group → stream mapping\n"
        "\n"
        "| Stream | Unit | Scenarios | Branch |\n"
        "|---|---|---|---|\n"
        f"| stream-1 | U1 | TRC-1 | {branch_cell} |\n"
    )
    (task_dir / "distribution-map.md").write_text(map_md)


@pytest.mark.parametrize(
    "input_cell,expected_branch",
    [
        ("`compass/foo/stream-1`", "compass/foo/stream-1"),
        ("**compass/foo/stream-2**", "compass/foo/stream-2"),
        ("`**compass/foo/stream-3**`", "compass/foo/stream-3"),
        ("compass/foo/stream-4", "compass/foo/stream-4"),
        ("  `compass/foo/stream-5`  ", "compass/foo/stream-5"),
    ],
    ids=[
        "single-backtick-wrap",
        "bold-wrap",
        "bold-plus-backtick",
        "no-formatting-regression",
        "leading-whitespace-plus-backtick",
    ],
)
def test_strips_markdown_from_branch_cell(tmp_path, input_cell, expected_branch):
    """Given a distribution-map row whose branch-name cell carries markdown
    formatting, when swarm.sh parses it, the branch name passed downstream
    is the markdown-stripped ref name.
    """
    assert SWARM_SH.is_file(), f"swarm.sh not found at {SWARM_SH}"

    project = tmp_path / "project"
    _init_project(project)

    task_slug = "test-swarm-task"
    task_dir = project / ".compass" / "work" / task_slug
    _write_task_artifacts(task_dir, input_cell)

    result = subprocess.run(
        ["bash", str(SWARM_SH), task_slug, "--dry-run"],
        cwd=project,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"swarm.sh exited {result.returncode}\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )

    # Match the "stream-1: WOULD create worktree <path> on branch <ref>" line.
    match = re.search(
        r"stream-1: WOULD create worktree \S+ on branch (\S+)",
        result.stdout,
    )
    assert match, f"Could not find stream-1 branch in output:\n{result.stdout}"
    actual_branch = match.group(1)

    assert actual_branch == expected_branch, (
        f"Expected clean branch {expected_branch!r}, got {actual_branch!r} "
        f"(input cell was {input_cell!r})"
    )
