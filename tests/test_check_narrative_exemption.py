"""R1 - `scenarios-have-tests` (G1) honours the scenario taxonomy: a
`verifiable: narrative` scenario clears the check by being DOCUMENTED (a
non-empty When/Then in spec.feature.md), not by carrying a fabricated test -
and not merely by carrying an incidental command.
"""
from __future__ import annotations

GHERKIN = "```gherkin"


def _body(scenario):
    return {
        "task": "narr", "created": "2026-06-22",
        "readings": {"blast_radius": "contained", "terrain": "brownfield-mapped",
                     "magnitude": "small", "intent": "delivery"},
        "route": "standard",
        "scenarios": [scenario],
        "evidence": [], "gates": [], "changed_files": [],
    }


def _write_spec(task_dir, scenario_id, *, documented, title="a behaviour"):
    lines = [
        "# Spec", "", "## Group A", "",
        f"### Scenario: {title}",
        f"<!-- traceability id: {scenario_id} · serves: INT-1 -->", "",
        GHERKIN,
        f"Scenario: {title}",
        "  Given some starting state",
    ]
    if documented:
        lines += ["  When the documented action happens",
                  "  Then the documented outcome holds"]
    lines += ["```", ""]
    (task_dir / "spec.feature.md").write_text("\n".join(lines))


def _scenarios_line(combined):
    for ln in combined.splitlines():
        if "scenarios-have-tests" in ln and ("PASS" in ln or "FAIL" in ln):
            return ln
    return ""


def test_baseline_narrative_without_test_fails(run_cli, make_task):
    """TRC-R1-1 (regression guard): a narrative scenario whose body is NOT
    documented still FAILS - narrative buys documentation-as-acceptance, not a
    free pass."""
    task_dir = make_task("narr-base",
                         _body({"id": "SCN-N", "intent": "INT-1",
                                "verifiable": "narrative", "tests": []}))
    _write_spec(task_dir, "SCN-N", documented=False)
    r = run_cli("check", "--task", "narr-base")
    assert "FAIL" in _scenarios_line(r.stdout + r.stderr), r


def test_documented_narrative_passes(run_cli, make_task):
    """TRC-R1-2: a documented narrative scenario with no test clears the check."""
    task_dir = make_task("narr-doc",
                         _body({"id": "SCN-N", "intent": "INT-1",
                                "verifiable": "narrative", "tests": []}))
    _write_spec(task_dir, "SCN-N", documented=True)
    r = run_cli("check", "--task", "narr-doc")
    assert "PASS" in _scenarios_line(r.stdout + r.stderr), r


def test_non_narrative_without_test_still_fails(run_cli, make_task):
    """TRC-R1-3: the exemption is narrow - a delivery scenario with no test
    still fails."""
    task_dir = make_task("narr-deliv",
                         _body({"id": "SCN-D", "intent": "INT-1", "tests": []}))
    _write_spec(task_dir, "SCN-D", documented=True)   # a body, but not narrative
    r = run_cli("check", "--task", "narr-deliv")
    line = _scenarios_line(r.stdout + r.stderr)
    assert "FAIL" in line and "SCN-D" in (r.stdout + r.stderr), r


def test_undocumented_narrative_fails_weaker_assertion(run_cli, make_task):
    """TRC-R1-4: an empty-body narrative scenario fails on the documentation
    assertion (not 'no test') - documented, not anything-goes."""
    task_dir = make_task("narr-empty",
                         _body({"id": "SCN-E", "intent": "INT-1",
                                "verifiable": "narrative", "tests": []}))
    _write_spec(task_dir, "SCN-E", documented=False)
    r = run_cli("check", "--task", "narr-empty")
    combined = r.stdout + r.stderr
    assert "SCN-E" in combined and "not documented" in combined.lower(), r


def test_incidental_command_not_rewarded(run_cli, make_task):
    """TRC-R1-5: a narrative scenario carrying an incidental command but no
    documented body still FAILS - assessed on documentation, not 'has a test'."""
    task_dir = make_task("narr-cmd",
                         _body({"id": "SCN-CMD-BARE", "intent": "INT-1",
                                "verifiable": "narrative",
                                "tests": ["scripts/diagnose.sh"]}))
    _write_spec(task_dir, "SCN-CMD-BARE", documented=False)
    r = run_cli("check", "--task", "narr-cmd")
    combined = r.stdout + r.stderr
    assert "FAIL" in _scenarios_line(combined), r
    assert "SCN-CMD-BARE" in combined and "not documented" in combined.lower(), r
