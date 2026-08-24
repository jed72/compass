"""The worked example in docs/five-minutes.md must match what the CLI does.

This is the onboarding document - the first thing an adopter runs. It carried
a transcript that had drifted from the code: a reading value (`intent:
engineering`) that is not in the vocabulary and makes `route evaluate` fail,
a gate set naming one gate where the policy computes three, and a check count
from an older version of the check suite.

The point of these tests is that the transcript cannot silently drift again:
the readings are fed to the real CLI, and the documented route and gate set
are compared to what it actually returns.
"""
import pathlib
import re
import subprocess
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
COMPASS_CLI = ROOT / "cli" / "compass"
DOC = ROOT / "docs" / "five-minutes.md"


def _documented_readings():
    """The `readings:` block from the worked example's task.yml snippet."""
    text = DOC.read_text(encoding="utf-8")
    m = re.search(r"```yaml\n(.*?schema_version.*?assessment:.*?)```", text, re.S)
    assert m, "docs/five-minutes.md must show a task.yml snippet with assessment:"
    parsed = yaml.safe_load(m.group(1))
    return parsed["assessment"]


def _evaluate(readings, *flags):
    args = [sys.executable, str(COMPASS_CLI), "approach", "evaluate", *flags]
    for key, value in readings.items():
        args += ["--assessment", f"{key}={value}"]
    return subprocess.run(args, capture_output=True, text=True, cwd=ROOT, timeout=30)


def test_worked_example_readings_are_accepted_by_the_cli():
    """Every reading value in the doc is in the routing policy's vocabulary."""
    result = _evaluate(_documented_readings())
    assert result.returncode == 0, (
        "docs/five-minutes.md documents readings the CLI rejects:\n"
        f"{result.stdout}\n{result.stderr}"
    )


def test_worked_example_route_and_gates_match_the_cli():
    """The documented FINAL ROUTE and gate set are the ones the CLI computes.

    Against --verbose: the doc shows both views, and this checks the detailed
    one because that is where the labels below live. The evaluator came under
    the terminal output contract on 2026-08-24 and moved them there; what the
    CLI computes is unchanged.
    """
    out = _evaluate(_documented_readings(), "--verbose").stdout
    doc = DOC.read_text(encoding="utf-8")

    # "FINAL ROUTE" became "FINAL APPROACH" with the CLI-voice slice.
    for label in ("FINAL APPROACH", "gate set"):
        m = re.search(rf"^\s*{label}\s*:\s*(.+)$", out, re.M)
        assert m, f"the evaluator printed no '{label}' line:\n{out}"
        actual = m.group(1).strip()
        assert re.search(rf"{re.escape(label)}\s*:\s*{re.escape(actual)}", doc), (
            f"docs/five-minutes.md's transcript does not show the real {label} "
            f"({actual!r}). Re-run `compass approach evaluate` and paste the output."
        )
