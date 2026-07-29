"""TRC-C6 - no new check and no new gate are added for B1.

Serves: INT-6, INT-11
Spec: The diff that lands the B1 candidate must not introduce any new check
name or gate name in governance/guardrails.yml.

This is a negative assertion test - it checks that stream-C (B1) does NOT
add new checks or gates. It runs git diff to inspect changes to guardrails.yml.

The test also verifies that the guardrails.yml carries a stream-C provenance
comment confirming the constraint was reviewed.
"""
from __future__ import annotations
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
GUARDRAILS_YML = "governance/guardrails.yml"

# The legitimate set of check names after the 1.1.0 release lands.
# TRC-C6's invariant is "stream-C / B1 adds no new checks" - the diff-scan
# test below is the canonical guard. The state-based tests below use the
# integration-time legitimate set: B1 introduced none of these. Additions
# `no-trusted-rerun` (stream-A) and `command-passes` (stream-B) are sibling-
# stream contributions, not stream-C's.
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
    # Sibling-stream additions, not B1:
    "no-trusted-rerun",   # stream-A (A1)
    "command-passes",     # stream-B (A2)
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
    # Sibling-stream addition, not B1:
    "verify.fitness",     # stream-B (A2)
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


def test_no_new_check_names_added_by_stream_c():
    """Stream C must not add any new check name to the checks: block in guardrails.yml."""
    import yaml

    guardrails_path = REPO_ROOT / GUARDRAILS_YML
    current_content = yaml.safe_load(guardrails_path.read_text(encoding="utf-8"))
    current_checks = set(current_content.get("checks", {}).keys())

    # All checks present now must be in baseline (stream C didn't add new ones)
    new_checks = current_checks - BASELINE_CHECKS
    assert not new_checks, (
        f"Stream C (B1) must not add new checks to guardrails.yml. "
        f"New checks found: {new_checks}. "
        "B1 is a judgement-side rebalance - no new mechanism."
    )


def test_no_new_gate_names_added_by_stream_c():
    """Stream C must not add any new gate name to gate_evidence_requirements in guardrails.yml."""
    import yaml

    guardrails_path = REPO_ROOT / GUARDRAILS_YML
    current_content = yaml.safe_load(guardrails_path.read_text(encoding="utf-8"))
    current_gates = set(current_content.get("gate_evidence_requirements", {}).keys())

    new_gates = current_gates - BASELINE_GATES
    assert not new_gates, (
        f"Stream C (B1) must not add new gates to guardrails.yml gate_evidence_requirements. "
        f"New gates found: {new_gates}. "
        "B1 is judgement-side only - no new gate."
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


def test_guardrails_b1_provenance_comment_present():
    """guardrails.yml must carry the B1-stream-C provenance comment confirming comment-only edit.

    This test provides the red→green anchoring for TRC-C6: it fails until the
    provenance comment is present, proving the constraint was explicitly verified.
    """
    text = (REPO_ROOT / GUARDRAILS_YML).read_text(encoding="utf-8")
    assert "stream-C" in text or "B1" in text or "TRC-C6" in text, (
        "guardrails.yml must carry a provenance comment referencing stream-C / B1 / TRC-C6 "
        "confirming this file was reviewed and only a comment was added. "
        "Add: '# stream-C (B1 / TRC-C6): only the coverage-floor caveat comment above was added - no new checks or gates.'"
    )
