"""guardrails.yml gains no new check name and no new gate name.

Adding a check or a gate is adding mechanism, and the framework grows by
checks and strategies deliberately, never by accident (ADR-002). These tests
make such an addition visible in review rather than silent.

This is a negative assertion test: it checks that no new check name or gate
name has appeared in guardrails.yml relative to main.

It also verifies that the empty `project:` list carries a comment saying the
emptiness is deliberate.
"""
from __future__ import annotations
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
GUARDRAILS_YML = "governance/guardrails.yml"

# The known-legitimate check names.
# The invariant is that guardrails.yml gains no new check names. The
# structural comparison against main below is the canonical guard; the
# state-based tests use this list as the known-legitimate set.
BASELINE_CHECKS = {
    "scenarios-have-tests",
    "suite-passed",
    "changed-code-traces-to-scenario",
    "scenario-has-id-and-intent",
    "claim-traces-to-scenario",
    "gate-evidence-present",
    "human-approval-present",
    "backfills-paid",
    "spike-conclusion-present",
    "spike-no-production-changes",
    "dod-evidence-typed",
    "coherence-check-passes",
    # Added alongside the checks above:
    "no-trusted-rerun",   # refuses to clear a test-run that only passed on a rerun
    "command-passes",     # runs a project-declared command and requires exit 0
}

# The legitimate set of gate names in gate_evidence_requirements after landing.
BASELINE_GATES = {
    "verify.correctness",
    "verify.regression",
    "verify.security",
    "verify.governance",
    "verify.traceability",
    "verify.claims",
    "verify.clarity",
    "spike.conclude",
    "verify.analyze",
    # Added with project-declared fitness functions:
    "verify.fitness",
}


def _guardrails_on_main() -> dict | None:
    """guardrails.yml as it stands on main, or None if main is not reachable.

    CI clones at depth 1, so the main ref is often absent there and no
    comparison is possible. Returning None makes the caller pass rather than
    fail on a missing ref, which is what a branch-relative test can honestly
    do in a shallow checkout.
    """
    import yaml

    result = subprocess.run(
        ["git", "show", f"main:{GUARDRAILS_YML}"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None
    return yaml.safe_load(result.stdout)


def _mechanism(data: dict) -> dict:
    """The parts of guardrails.yml that are mechanism rather than prose.

    Everything a check, a gate, or the CLI acts on. Free text (`name`,
    `statement`, `description`) is deliberately excluded: rewording a
    guardrail is an editorial act, adding one is a structural act, and only
    the second is what this file guards against.
    """
    def rules(items):
        return {
            r["id"]: {
                "checks": sorted(r.get("checks", [])),
                "checked_at": sorted(r.get("checked_at", [])),
                "applies_when": r.get("applies_when"),
                "params": r.get("params"),
            }
            for r in (items or [])
        }

    return {
        "top_level_keys": sorted(data.keys()),
        "check_names": sorted(data.get("checks", {})),
        "evidence_types": sorted(data.get("evidence_types", {})),
        "gate_evidence_requirements": {
            gate: sorted(types)
            for gate, types in (data.get("gate_evidence_requirements") or {}).items()
        },
        "defaults": rules(data.get("defaults")),
        "spike_guardrails": rules(data.get("spike_guardrails")),
        "project": rules(data.get("project")),
    }


def test_no_new_check_names_added():
    """No new check name has appeared in the checks: block in guardrails.yml."""
    import yaml

    guardrails_path = REPO_ROOT / GUARDRAILS_YML
    current_content = yaml.safe_load(guardrails_path.read_text(encoding="utf-8"))
    current_checks = set(current_content.get("checks", {}).keys())

    new_checks = current_checks - BASELINE_CHECKS
    assert not new_checks, (
        f"guardrails.yml gained new checks: {new_checks}. A new check is new\n"
        "mechanism: add it here deliberately, with the change that introduces it."
    )


def test_no_new_gate_names_added():
    """No new gate name has appeared in gate_evidence_requirements."""
    import yaml

    guardrails_path = REPO_ROOT / GUARDRAILS_YML
    current_content = yaml.safe_load(guardrails_path.read_text(encoding="utf-8"))
    current_gates = set(current_content.get("gate_evidence_requirements", {}).keys())

    new_gates = current_gates - BASELINE_GATES
    assert not new_gates, (
        f"guardrails.yml gained new gates: {new_gates}. A new gate is new\n"
        "mechanism: add it here deliberately, with the change that introduces it."
    )


def test_guardrails_gains_no_mechanism_on_this_branch():
    """No branch may add mechanism to guardrails.yml: same checks, gates, rules.

    This compares the parsed structure against main rather than the raw text.
    An earlier version required every added line to be a comment, which meant
    any edit to the prose inside the file - rewording a guardrail statement,
    or the repository-wide punctuation sweep - read as a structural change.
    Prose is editorial and free to change; the mechanism is what must not grow.
    """
    import yaml

    baseline = _guardrails_on_main()
    if baseline is None:
        return  # main not reachable (shallow clone); nothing to compare against

    current = yaml.safe_load((REPO_ROOT / GUARDRAILS_YML).read_text(encoding="utf-8"))
    before, after = _mechanism(baseline), _mechanism(current)

    for field in sorted(before):
        assert before[field] == after[field], (
            f"guardrails.yml changed mechanism in {field!r} relative to main.\n"
            f"  on main: {before[field]!r}\n"
            f"  now:     {after[field]!r}\n"
            "Guardrails are capped at five and grow by checks and strategies, "
            "not by new rules (ADR-002). Rewording prose is fine; adding a "
            "check, gate, evidence type, or rule is not."
        )


def test_empty_project_guardrails_are_explained():
    """The empty `project:` list says why it is empty.

    An empty list looks identical whether it is deliberate or an oversight, and
    the difference matters: it is what makes an adopting repo see no
    project-level check until it declares one. A reader should not have to
    guess which it is.

    This replaces an earlier test that required a comment naming an internal
    work stream. That comment asserted a past review rather than proving
    anything, and the guarantee it claimed is now checked directly by
    `test_guardrails_gains_no_mechanism_on_this_branch` above and by
    `test_no_project_guardrails_declared_in_framework_repo`.
    """
    text = (REPO_ROOT / GUARDRAILS_YML).read_text(encoding="utf-8")
    idx = text.find("project: []")
    assert idx != -1, "guardrails.yml must ship with an empty project: [] list"
    trailing = text[idx:].splitlines()[1:3]
    assert any(l.lstrip().startswith("#") and l.strip() != "#" for l in trailing), (
        "The empty `project: []` list must be followed by a comment explaining "
        "that it is deliberate, so a reader can tell it apart from an oversight."
    )
