"""Acceptance tests for `compass plan lint` (task readable-specs-and-flow).

`compass plan lint` scans a plan.md for placeholder phrases that mean the plan
is not actually finished - "TBD", "TODO", "implement later", "add appropriate
error handling" - and for work units that promise tests without containing any.

Two properties matter as much as the detection itself, and both are tested here:

  * It is ADVISORY. It always exits 0. A hit is a note for the planner, never a
    block. This is fixed by DD-2 in the task's plan.md: the CLI may read a prose
    artifact to advise, but may not gate on its structure.
  * It ignores fenced code blocks and blockquotes. Without that, the check fires
    on every document that explains it - including the governance-check skill,
    the writing guide, and the plan for this very task.

Spec: .compass/work/readable-specs-and-flow/spec.feature.md (TRC-C1, C1b, C2, C5).
"""
import subprocess
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
COMPASS_CLI = ROOT / "cli" / "compass"


def _plan_lint(tmp_path, body, name="design.md"):
    """Write `body` to a temp plan and run `compass plan lint --file` on it."""
    plan = tmp_path / name
    plan.write_text(body)
    result = subprocess.run(
        [sys.executable, str(COMPASS_CLI), "plan", "lint", "--file", str(plan)],
        capture_output=True, text=True, timeout=30,
    )
    return result


# ---------------------------------------------------------------------------
# TRC-C1 - the four prohibited phrases are reported with their line numbers
# ---------------------------------------------------------------------------

def test_trc_c1_reports_each_prohibited_phrase(tmp_path):
    body = "\n".join([
        "# Plan - example",              # 1
        "",                              # 2
        "## 1. Approach",                # 3
        "",                              # 4
        "The retry policy is TBD.",      # 5
        "",                              # 6
        "TODO: decide the batch size.",  # 7
        "",                              # 8
        "We will implement later.",      # 9
        "",                              # 10
        "Then add appropriate error handling.",  # 11
    ])
    result = _plan_lint(tmp_path, body)
    out = result.stdout + result.stderr

    for phrase in ("TBD", "TODO", "implement later", "add appropriate error handling"):
        assert phrase.lower() in out.lower(), f"'{phrase}' was not reported"

    for lineno in (5, 7, 9, 11):
        assert f"line {lineno}" in out, (
            f"Hit on line {lineno} not reported with its line number.\nOutput:\n{out}"
        )


def test_trc_c1_clean_plan_reports_nothing(tmp_path):
    """A finished plan produces no hits - otherwise the check is noise."""
    body = "\n".join([
        "# Plan - example",
        "",
        "## 1. Approach",
        "",
        "Add a retry with a 30 second ceiling, then fail the job.",
    ])
    result = _plan_lint(tmp_path, body)

    assert result.returncode == 0
    assert "line " not in result.stdout, (
        f"Clean plan produced hits:\n{result.stdout}"
    )


# ---------------------------------------------------------------------------
# TRC-C1b - a work unit that promises tests but contains none
# ---------------------------------------------------------------------------

def test_trc_c1b_incomplete_work_unit_reported(tmp_path):
    body = "\n".join([
        "# Plan - example",
        "",
        "## 4. Work units",
        "",
        "U1 parses the ledger export.",
        "Write tests for the above.",
    ])
    result = _plan_lint(tmp_path, body)
    out = (result.stdout + result.stderr).lower()

    assert "write tests for the above" in out, (
        "A work unit promising tests with none below it was not reported"
    )


def test_trc_c1b_not_reported_when_tests_follow(tmp_path):
    """The rule is about an empty promise, so a promise that is kept is fine."""
    body = "\n".join([
        "# Plan - example",
        "",
        "## 4. Work units",
        "",
        "U1 parses the ledger export.",
        "Write tests for the above:",
        "",
        "- `tests/test_ledger.py::test_excludes_drafts`",
        "- `tests/test_ledger.py::test_rejects_unbalanced_rows`",
    ])
    result = _plan_lint(tmp_path, body)
    out = (result.stdout + result.stderr).lower()

    assert "write tests for the above" not in out, (
        f"Reported an incomplete work unit even though tests follow it:\n{out}"
    )


# ---------------------------------------------------------------------------
# TRC-C2 - advisory: hits are reported, the command still succeeds
# ---------------------------------------------------------------------------

def test_trc_c2_hit_reported_with_exit_zero(tmp_path):
    body = "# Plan - example\n\nTODO: finish this.\n"
    result = _plan_lint(tmp_path, body)

    assert "TODO" in (result.stdout + result.stderr), "The hit was not reported"
    assert result.returncode == 0, (
        "compass plan lint must exit 0 even with hits - it is advisory, never a "
        f"gate (DD-2). Got exit {result.returncode}."
    )


def test_trc_c2_missing_file_is_an_error_not_a_silent_pass(tmp_path):
    """Advisory means "does not block on findings", not "never fails". Being
    pointed at a file that is not there is a usage error and must be visible."""
    result = subprocess.run(
        [sys.executable, str(COMPASS_CLI), "plan", "lint",
         "--file", str(tmp_path / "nope.md")],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode != 0
    assert "nope.md" in (result.stdout + result.stderr)


# ---------------------------------------------------------------------------
# TRC-C5 - quoted prose is not a placeholder
# ---------------------------------------------------------------------------

def test_trc_c5_fenced_and_quoted_text_ignored(tmp_path):
    """The documents that explain the check must not trip it."""
    body = "\n".join([
        "# Plan - example",
        "",
        "## 2. Design decisions",
        "",
        "The check reports phrases such as:",
        "",
        "```",
        "TBD",
        "TODO: decide this",
        "implement later",
        "add appropriate error handling",
        "```",
        "",
        "> A plan that says TODO is not a finished plan.",
        "",
        "The approach is settled and needs no further decision.",
    ])
    result = _plan_lint(tmp_path, body)

    assert result.returncode == 0
    assert "line " not in result.stdout, (
        "Phrases quoted inside a fenced block or a blockquote were reported as "
        f"placeholders:\n{result.stdout}"
    )


def test_trc_c5_real_hit_after_a_fence_is_still_found(tmp_path):
    """Fence handling must not swallow the rest of the file."""
    body = "\n".join([
        "# Plan - example",       # 1
        "",                       # 2
        "```",                    # 3
        "TODO: an example",       # 4
        "```",                    # 5
        "",                       # 6
        "The batch size is TBD.", # 7
    ])
    result = _plan_lint(tmp_path, body)
    out = result.stdout + result.stderr

    assert "line 7" in out, f"A real hit after a closed fence was missed:\n{out}"
    assert "line 4" not in out, f"A hit inside the fence was reported:\n{out}"


# ---------------------------------------------------------------------------
# Dogfooding: this task's own plan must survive its own check
# ---------------------------------------------------------------------------

def test_plan_lint_is_clean_on_this_tasks_own_plan():
    """The plan that specified this check quotes the phrases it forbids. If the
    check cannot read that plan without complaining, it is not usable."""
    plan = ROOT / ".compass/work/readable-specs-and-flow/plan.md"
    if not plan.exists():          # the task directory is not shipped to adopters
        return
    result = subprocess.run(
        [sys.executable, str(COMPASS_CLI), "plan", "lint", "--file", str(plan)],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0
    assert "line " not in result.stdout, (
        f"compass plan lint reports placeholders in its own plan:\n{result.stdout}"
    )
