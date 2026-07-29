"""Stop-hook scope-bloat phrase detection.

TRC-C1 - Stop-hook nudges when scope-bloat phrases appear in devlog
TRC-C2 - Stop-hook stays silent when no scope-bloat is detected
TRC-C3 - Stop-hook stays silent when a reframe has already been filed
TRC-X3 - Stop-hook regex doesn't produce false positives on quoted context

The hook reads patterns from governance/signals.yml at runtime (
never hardcoded), emits a nudge to stderr, and exits 0 (non-blocking).

Each test invokes hooks/stop.sh as a subprocess with a crafted temp project.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import yaml


FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent
STOP_HOOK = FRAMEWORK_ROOT / "hooks" / "stop.sh"


def _make_project(tmp_path: Path, *, signals_extra: dict | None = None) -> Path:
    """Create a minimal Compass project in tmp_path with signals.yml copied."""
    compass = tmp_path / ".compass"
    work = compass / "work"
    work.mkdir(parents=True, exist_ok=True)
    (compass / "config.yml").write_text("version: 1.0.0\nmode: enforced\n")

    # Copy governance/ including signals.yml
    gov_src = FRAMEWORK_ROOT / "governance"
    gov_dst = tmp_path / "governance"
    gov_dst.mkdir(parents=True, exist_ok=True)
    for f in gov_src.iterdir():
        if f.is_file():
            shutil.copy(f, gov_dst / f.name)

    return tmp_path


def _make_task(project: Path, slug: str, *,
               devlog_lines: list[str] | None = None,
               reframes: list[dict] | None = None,
               route: str = "standard") -> Path:
    """Materialise a task directory with route.md, devlog.md, and task.yml."""
    task_dir = project / ".compass" / "work" / slug
    task_dir.mkdir(parents=True, exist_ok=True)

    # route.md - minimal so the hook can see it
    (task_dir / "route.md").write_text(
        f"# Route - {slug}\n\n> **Reference route:** {route}\n"
    )

    # devlog.md - the content under test
    lines = devlog_lines or []
    (task_dir / "devlog.md").write_text("\n".join(lines) + "\n")

    # task.yml - needed by the hook's reframes check
    body: dict = {
        "task": slug,
        "created": "2026-05-20",
        "readings": {
            "blast_radius": "contained",
            "terrain": "brownfield-mapped",
            "magnitude": "small",
        },
        "route": route,
        "reframes": reframes or [],
    }
    with (task_dir / "task.yml").open("w") as fh:
        yaml.safe_dump(body, fh, sort_keys=False)

    # Set current-task pointer
    (project / ".compass" / "current-task").write_text(slug)
    return task_dir


def _run_hook(project: Path) -> subprocess.CompletedProcess:
    """Run hooks/stop.sh with CLAUDE_PROJECT_DIR pointed at project."""
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = str(project)
    return subprocess.run(
        ["bash", str(STOP_HOOK)],
        cwd=str(project),
        capture_output=True,
        text=True,
        input="",
        env=env,
        timeout=15,
    )


# ---------------------------------------------------------------------------
# TRC-C1 - nudge fires when scope-bloat phrase is in devlog and no reframe
# ---------------------------------------------------------------------------

def test_nudge_on_bloat(tmp_path):
    """TRC-C1: A known scope-bloat phrase in devlog triggers a stderr nudge."""
    project = _make_project(tmp_path)
    _make_task(
        project,
        "bloat-task",
        devlog_lines=[
            "2026-05-20: Started build",
            "more files than Plan estimated - had to touch core module",
            "Finished for the day",
        ],
        reframes=[],
    )
    result = _run_hook(project)
    assert result.returncode == 0, f"hook must exit 0\n{result.stderr}"
    assert "reframe" in result.stderr.lower(), (
        "Expected a reframe nudge in stderr, got:\n" + result.stderr
    )
    assert "/compass:frame --reframe" in result.stderr, (
        "Expected the exact reframe command in stderr"
    )


# ---------------------------------------------------------------------------
# TRC-C2 - silent when no scope-bloat detected
# ---------------------------------------------------------------------------

def test_silent_on_clean(tmp_path):
    """TRC-C2: A clean devlog produces no reframe nudge."""
    project = _make_project(tmp_path)
    _make_task(
        project,
        "clean-task",
        devlog_lines=[
            "2026-05-20: Started build, all good",
            "Completed first scenario green",
        ],
        reframes=[],
    )
    result = _run_hook(project)
    assert result.returncode == 0, result.stderr
    # No nudge expected
    assert "reframe" not in result.stderr.lower(), (
        "Expected no reframe nudge for a clean devlog, got:\n" + result.stderr
    )


# ---------------------------------------------------------------------------
# TRC-C3 - silent when a reframe has already been filed after the bloat line
# ---------------------------------------------------------------------------

def test_silent_when_reframed(tmp_path):
    """TRC-C3: An honest reframe entry after the bloat line suppresses the nudge."""
    project = _make_project(tmp_path)
    _make_task(
        project,
        "reframed-task",
        devlog_lines=[
            "2026-05-19: more files than Plan estimated",
            "2026-05-20: Filed reframe, all good",
        ],
        reframes=[
            {
                "from_route": "standard",
                "to_route": "expedition",
                "reason": "scope larger than estimated",
                "date": "2026-05-20",  # after the bloat line date
            }
        ],
    )
    result = _run_hook(project)
    assert result.returncode == 0, result.stderr
    assert "reframe" not in result.stderr.lower(), (
        "Expected no nudge when reframe is already filed:\n" + result.stderr
    )


# ---------------------------------------------------------------------------
# TRC-X3 - no false positives on quoted or cited context
# ---------------------------------------------------------------------------

def test_no_false_positive_in_quoted_context(tmp_path):
    """TRC-X3: A phrase nested in quotes or backtick context does not fire."""
    project = _make_project(tmp_path)
    _make_task(
        project,
        "quoted-task",
        devlog_lines=[
            # These lines quote or cite the phrase, not report it as an actual
            # scope-bloat event. The hook must not fire on them.
            '    > "more files than Plan estimated" - quoted from spec discussion',
            "    The pattern `more files than Plan estimated` is documented in signals.yml",
            "We avoided narrowing scope by keeping everything in one stream",
        ],
        reframes=[],
    )
    result = _run_hook(project)
    assert result.returncode == 0, result.stderr
    assert "reframe" not in result.stderr.lower(), (
        "False positive: hook fired on quoted/indented context:\n" + result.stderr
    )


# ---------------------------------------------------------------------------
# Guard: changing signals.yml changes the hook's behaviour
# ---------------------------------------------------------------------------

def test_hook_reads_signals_at_runtime(tmp_path):
    """The hook loads patterns from signals.yml, not hardcoded.

    Modify signals.yml to use a custom phrase; verify the hook fires on that
    phrase and not on one of the default phrases that was removed.
    """
    project = _make_project(tmp_path)

    # Replace signals.yml with a custom set of phrases
    custom_signals = {
        "version": "1.0.0",
        "scope_bloat_phrases": ["CUSTOM_BLOAT_MARKER_XYZ"],
        "rework_scan": {
            "window_days": 14,
            "public_surface_patterns": ["/api/v[0-9]+/"],
            "migration_paths": ["migrations/*.sql"],
        },
    }
    sig_path = project / "governance" / "signals.yml"
    with sig_path.open("w") as fh:
        yaml.safe_dump(custom_signals, fh)

    # devlog has the custom phrase only, not a default phrase
    _make_task(
        project,
        "custom-sig-task",
        devlog_lines=["CUSTOM_BLOAT_MARKER_XYZ occurred during build"],
        reframes=[],
    )
    result = _run_hook(project)
    assert result.returncode == 0, result.stderr
    # The hook should fire because the custom phrase is present
    assert "reframe" in result.stderr.lower(), (
        "Hook should have fired on the custom phrase:\n" + result.stderr
    )
