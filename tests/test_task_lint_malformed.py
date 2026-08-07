"""`compass task lint` must report a malformed task.yml, not crash on it.

The command exists to tell an author what is wrong with their task.yml. When a
scenario or a changed_files entry was written as a bare string instead of a
mapping, the lint called `.get()` on it and died with an AttributeError - the
one input it was built for was the one input it could not survive, and the
traceback said nothing about what to fix.
"""
import pathlib
import subprocess
import sys
import textwrap

ROOT = pathlib.Path(__file__).resolve().parent.parent
COMPASS_CLI = ROOT / "cli" / "compass"

MALFORMED = textwrap.dedent(
    """\
    schema_version: "1.1"
    task: t
    readings:
      blast_radius: contained
      terrain: greenfield
      magnitude: small
    scenarios:
      - "SCN-001 written as a bare string"
    changed_files:
      - "src/thing.py"
    """
)


def _project(tmp_path, task_yml):
    work = tmp_path / ".compass" / "work" / "t"
    work.mkdir(parents=True)
    (work / "task.yml").write_text(task_yml, encoding="utf-8")
    (tmp_path / ".compass" / "current-task").write_text("t\n", encoding="utf-8")
    return tmp_path


def _lint(cwd):
    return subprocess.run(
        [sys.executable, str(COMPASS_CLI), "task", "lint", "--task", "t"],
        capture_output=True, text=True, cwd=cwd, timeout=30,
    )


def test_lint_reports_a_bare_string_scenario_instead_of_crashing(tmp_path):
    result = _lint(_project(tmp_path, MALFORMED))
    combined = result.stdout + result.stderr
    assert "Traceback" not in combined, (
        f"`task lint` crashed on a malformed task.yml:\n{combined}"
    )
    assert result.returncode != 0, "a malformed task.yml must fail the lint"
    assert "scenario #1" in combined, (
        f"the bare-string scenario was not reported:\n{combined}"
    )
    assert "changed_files" in combined, (
        f"the bare-string changed_files entry was not reported:\n{combined}"
    )


def test_lint_reports_non_mapping_readings_instead_of_crashing(tmp_path):
    bad = MALFORMED.replace(
        "readings:\n  blast_radius: contained\n  terrain: greenfield\n  magnitude: small",
        "readings: contained",
    )
    result = _lint(_project(tmp_path, bad))
    combined = result.stdout + result.stderr
    assert "Traceback" not in combined, (
        f"`task lint` crashed on non-mapping readings:\n{combined}"
    )
    assert result.returncode != 0
    assert "assessment" in combined
