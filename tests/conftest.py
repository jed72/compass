"""Pytest fixtures for the Compass CLI test suite.

These tests are hermetic: each test gets its own temporary project directory
with a fresh `.compass/` layout, and the CLI is invoked via `subprocess.run`
in that directory. Nothing is shared between tests.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest
import yaml


# --- locate the CLI and the framework root ----------------------------------
# tests/ lives at the framework root, so the CLI is next to it.
FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent
CLI_PATH = FRAMEWORK_ROOT / "cli" / "compass"


@pytest.fixture(scope="session")
def cli_path() -> Path:
    """Absolute path to the compass CLI executable."""
    assert CLI_PATH.is_file(), f"compass CLI not found at {CLI_PATH}"
    return CLI_PATH


@pytest.fixture(scope="session")
def framework_root() -> Path:
    """The compass framework root (containing governance/, schemas/, cli/)."""
    return FRAMEWORK_ROOT


# --- the temp project layout -----------------------------------------------

DEFAULT_GOVERNANCE_FILES = ("routing-policy.yml", "guardrails.yml")


def _copy_governance(src_root: Path, dest: Path) -> None:
    """Copy the shipped governance/ files into a temp project so the test can
    mutate them without touching the real repo."""
    src = src_root / "governance"
    dst = dest / "governance"
    dst.mkdir(parents=True, exist_ok=True)
    for name in DEFAULT_GOVERNANCE_FILES:
        shutil.copyfile(src / name, dst / name)
    # also copy the .md files (lint doesn't need them, but it's hygienic)
    for md in src.glob("*.md"):
        shutil.copyfile(md, dst / md.name)


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A fresh Compass project on disk.

    Layout:
        <tmp>/
          governance/routing-policy.yml + guardrails.yml   (copies of shipped)
          .compass/config.yml                              (mode: enforced)
          .compass/work/                                   (empty)
    """
    _copy_governance(FRAMEWORK_ROOT, tmp_path)
    compass_dir = tmp_path / ".compass"
    (compass_dir / "work").mkdir(parents=True, exist_ok=True)
    (compass_dir / "config.yml").write_text(
        "version: 1.0.0\nmode: enforced\n", encoding="utf-8"
    )
    return tmp_path


@pytest.fixture
def make_task(project: Path):
    """Return a callable that materialises a task directory with a task.yml.

    Usage:
        task_dir = make_task("my-slug", {"readings": {...}, ...})
        # task_dir == project/.compass/work/my-slug
        # .compass/current-task is set to "my-slug"
    """

    def _make(slug: str, body: Dict[str, Any], *, set_current: bool = True) -> Path:
        task_dir = project / ".compass" / "work" / slug
        task_dir.mkdir(parents=True, exist_ok=True)
        # ensure required minimum keys unless caller fully overrides
        body = dict(body)
        body.setdefault("task", slug)
        body.setdefault("created", "2026-05-15")
        path = task_dir / "task.yml"
        with path.open("w", encoding="utf-8") as fh:
            yaml.safe_dump(body, fh, sort_keys=False)
        if set_current:
            (project / ".compass" / "current-task").write_text(slug, encoding="utf-8")
        return task_dir

    return _make


@pytest.fixture
def write_evidence_file(project: Path):
    """Return a callable that writes an evidence JSON next to the task dir.

    The `path` returned is relative to the task_dir (i.e. `evidence/green.json`).
    """

    def _write(task_dir: Path, name: str, payload: Dict[str, Any]) -> str:
        ev_dir = task_dir / "evidence"
        ev_dir.mkdir(parents=True, exist_ok=True)
        full = ev_dir / name
        with full.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh)
        return f"evidence/{name}"

    return _write


# --- the CLI invocation helper ---------------------------------------------


class CliResult:
    """The return type from `run_cli` - exit code + stdout + stderr."""

    def __init__(self, proc: subprocess.CompletedProcess):
        self.returncode: int = proc.returncode
        self.stdout: str = proc.stdout or ""
        self.stderr: str = proc.stderr or ""
        # convenience: both streams joined
        self.combined: str = self.stdout + "\n" + self.stderr

    def __repr__(self) -> str:  # makes test failures readable
        return (
            f"CliResult(exit={self.returncode!r})\n"
            f"--- stdout ---\n{self.stdout}\n"
            f"--- stderr ---\n{self.stderr}\n"
        )


@pytest.fixture
def run_cli(cli_path: Path, project: Path):
    """Return a callable that invokes the compass CLI inside `project`.

    Usage:
        result = run_cli("route", "evaluate", "--task", "slug", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
    """

    def _run(*args: str, cwd: Optional[Path] = None,
             extra_env: Optional[Dict[str, str]] = None,
             input_text: Optional[str] = None,
             timeout: int = 10) -> CliResult:
        # Default timeout 10s - the CLI's real operations finish in under a
        # second; anything beyond 10s is a hang, and a hang should fail fast
        # rather than compounding 30s * 93 tests on a slow environment.
        env = dict(os.environ)
        if extra_env:
            env.update(extra_env)
        proc = subprocess.run(
            [sys.executable, str(cli_path), *args],
            cwd=str(cwd or project),
            capture_output=True,
            text=True,
            env=env,
            input=input_text,
            timeout=timeout,
        )
        return CliResult(proc)

    return _run


# --- governance editing helpers --------------------------------------------


@pytest.fixture
def edit_governance(project: Path):
    """Load + save a governance YAML file in the temp project.

    Usage:
        with edit_governance("guardrails.yml") as g:
            g["defaults"].append({...})
    """

    class _Editor:
        def __init__(self, name: str):
            self.path = project / "governance" / name
            self.data: Dict[str, Any] = yaml.safe_load(self.path.read_text())

        def __enter__(self):
            return self.data

        def __exit__(self, *_):
            with self.path.open("w", encoding="utf-8") as fh:
                yaml.safe_dump(self.data, fh, sort_keys=False)

    return _Editor


# --- fixture file loader (used by test_route_selection) ---------------------


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def load_route_fixtures() -> List[Dict[str, Any]]:
    """Load the route YAML fixtures in tests/fixtures/routes/."""
    out = []
    rdir = FIXTURES_DIR / "routes"
    for f in sorted(rdir.glob("*.yml")):
        data = yaml.safe_load(f.read_text())
        data["__file__"] = f.name
        out.append(data)
    return out
