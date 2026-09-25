"""`scripts/validate.sh --help` prints what is under its headings.

The help text filtered the header with a pattern that wanted three spaces
before each numbered line, where the header has two. So `--help` printed the
headings "EXIT CODES" and "WHAT IT CHECKS" with nothing under them.

Scenario id: VHP-1, in the delivery approach of issue
`validate-help-prints-headings-only`.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _help() -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(ROOT / "scripts" / "validate.sh"), "--help"],
                          capture_output=True, text=True, timeout=60)


def test_vhp_1_help_prints_both_exit_codes():
    result = _help()
    assert result.returncode == 0
    assert "0  everything resolves" in result.stdout
    assert "1  one or more checks failed" in result.stdout


def test_vhp_1_help_prints_every_check():
    text = " ".join(_help().stdout.split())
    for n in range(1, 9):
        assert f"{n}. " in text, f"check {n} is missing from --help"
    assert "The kit layer is present" in text


def test_vhp_1_help_is_not_prefixed_with_the_comment_marker():
    assert not any(line.startswith("#") for line in _help().stdout.splitlines())
