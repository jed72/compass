"""`tdd-red` and `tdd-green` do not break a pytest run that turns plugin
autoload off.

Both add `--cov-fail-under=0` to a pytest command so a project's coverage
floor cannot refuse a narrow run. The flag belongs to pytest-cov. Where the
plugin does not load, pytest rejects the flag with a usage error and runs
nothing. The check read `PYTEST_DISABLE_PLUGIN_AUTOLOAD` from the calling
environment only, so `env PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest`
got the flag and failed.

Scenario ids: CFA-1 to CFA-3, in the delivery approach of issue
`coverage-flag-with-autoload-off`.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "cli"))

from compass_pkg import tdd  # noqa: E402

FLAG = "--cov-fail-under=0"


@pytest.fixture
def cov_loads(monkeypatch):
    """Answer "pytest-cov is installed" whatever this machine has."""
    monkeypatch.delenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", raising=False)
    monkeypatch.setattr("importlib.util.find_spec", lambda name: object())


@pytest.mark.parametrize("cmd", [
    ["env", "PYTEST_DISABLE_PLUGIN_AUTOLOAD=1", "python3", "-m", "pytest", "-q"],
    ["PYTEST_DISABLE_PLUGIN_AUTOLOAD=1", "python3", "-m", "pytest", "-q"],
    ["python3", "-m", "pytest", "-p", "no:cov", "-q"],
    ["python3", "-m", "pytest", "-p", "no:pytest_cov", "-q"],
])
def test_cfa_1_a_command_that_turns_the_plugin_off_gets_no_flag(cov_loads, cmd):
    assert FLAG not in tdd._neutralise_coverage(cmd)


def test_cfa_2_the_variable_in_the_calling_environment_gets_no_flag(
        cov_loads, monkeypatch):
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    assert FLAG not in tdd._neutralise_coverage(["python3", "-m", "pytest"])


@pytest.mark.parametrize("cmd", [
    ["python3", "-m", "pytest", "-q"],
    ["env", "PYTEST_DISABLE_PLUGIN_AUTOLOAD=1", "python3", "-m", "pytest",
     "-p", "pytest_cov", "-q"],
])
def test_cfa_3_a_command_where_the_plugin_loads_keeps_the_flag(cov_loads, cmd):
    assert FLAG in tdd._neutralise_coverage(cmd)
