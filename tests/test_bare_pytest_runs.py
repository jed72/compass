"""The suite runs with nothing added to PYTHONPATH.

Scenario BPF-1 of `bare-pytest-fails-on-two-tests`.

Two tests import from the `tests` package. Nothing put the repository root on
`sys.path`, so `pytest -q` from the root failed both with
`ModuleNotFoundError: No module named 'tests'` and only passed when the caller
exported PYTHONPATH first.

That is worse than an inconvenience. `compass tdd-green -- pytest -q` is the
documented way to record a passing suite and it spawns the command without the
caller's shell prefix, so the `verify.regression` gate could not be cleared by
following the instructions Compass gives. The two failures also read exactly
like real ones on a clean checkout.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_bpf_1_the_repository_root_is_importable_without_pythonpath():
    """A subprocess with PYTHONPATH removed can still `import tests`.

    Run as a subprocess with the variable stripped, because this process was
    started by whatever the developer typed and may already carry it - a check
    that reads its own inherited environment proves nothing about a clean one.
    """
    import os

    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    # The console script, and the bodies actually run. `python -m pytest` puts
    # the working directory on sys.path and would pass whatever the config
    # says; `--collect-only` never reaches the import that fails. The first
    # version of this test did both, and passed against the live defect.
    r = subprocess.run(
        ["pytest", "-q", "-p", "no:randomly",
         "tests/test_long_sentences.py", "tests/test_trace_rot_detection.py"],
        cwd=str(ROOT), env=env, capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, (
        "collecting two tests that import from `tests` fails with no "
        "PYTHONPATH set, so a bare `pytest` is red on a clean checkout and "
        "`compass tdd-green -- pytest -q` cannot clear the regression gate:\n"
        + (r.stdout + r.stderr)[-1500:])


def test_bpf_1_the_project_declares_how_its_suite_is_run():
    """`compass tdd-green` and the regression-baseline strategy both ask the
    config for the test command. An empty one means Compass has no answer to
    "how is this project's suite run", on the project whose subject is that
    question."""
    import re

    cfg = (ROOT / ".compass" / "config.yml").read_text(encoding="utf-8")
    m = re.search(r"^\s*test_command:\s*(.+)$", cfg, re.M)
    assert m, "config.yml declares no test_command key at all"
    value = m.group(1).split("#")[0].strip().strip('"\'')
    assert value, (
        "`test_command` is empty, so `compass tdd-green` and the "
        "regression-baseline strategy have nothing to run")
    assert "pytest" in value, (
        f"test_command is {value!r}, which does not run this project's suite")
