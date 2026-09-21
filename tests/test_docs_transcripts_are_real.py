"""The worked example in docs/five-minutes.md must match what the CLI does.

The worked example's assessment is fed to the real CLI, and the documented
approach and gates are compared with what it returns, so the transcript in
this onboarding document - the first thing an adopter runs - cannot
silently drift from the code again.
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
    """The `assessment:` block from the worked example's manifest.yml snippet."""
    text = DOC.read_text(encoding="utf-8")
    m = re.search(r"```yaml\n(.*?schema_version.*?assessment:.*?)```", text, re.S)
    assert m, "docs/five-minutes.md must show a manifest.yml snippet with assessment:"
    parsed = yaml.safe_load(m.group(1))
    return parsed["assessment"]


def _evaluate(readings, *flags):
    args = [sys.executable, str(COMPASS_CLI), "approach", "evaluate", *flags]
    for key, value in readings.items():
        args += ["--assessment", f"{key}={value}"]
    return subprocess.run(args, capture_output=True, text=True, cwd=ROOT, timeout=30)


def test_worked_example_readings_are_accepted_by_the_cli():
    """Every assessment value in the doc is in the routing policy's vocabulary."""
    result = _evaluate(_documented_readings())
    assert result.returncode == 0, (
        "docs/five-minutes.md documents readings the CLI rejects:\n"
        f"{result.stdout}\n{result.stderr}"
    )


def test_worked_example_route_and_gates_match_the_cli():
    """The documented FINAL APPROACH and gate set are the ones the CLI
    computes.

    Against --verbose: the doc shows both views, and this checks the
    detailed one because that is where the labels below live. The labels
    appear only under --verbose.
    """
    out = _evaluate(_documented_readings(), "--verbose").stdout
    doc = DOC.read_text(encoding="utf-8")

    for label in ("FINAL APPROACH", "gate set"):
        m = re.search(rf"^\s*{label}\s*:\s*(.+)$", out, re.M)
        assert m, f"the evaluator printed no '{label}' line:\n{out}"
        actual = m.group(1).strip()
        assert re.search(rf"{re.escape(label)}\s*:\s*{re.escape(actual)}", doc), (
            f"docs/five-minutes.md's transcript does not show the real {label} "
            f"({actual!r}). Re-run `compass approach evaluate` and paste the output."
        )
