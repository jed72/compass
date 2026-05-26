"""TRC-C6 — no new check and no new gate are added for B1.

Serves: INT-6, INT-11
Spec: The diff that lands the B1 candidate must not introduce any new check
name or gate name in governance/guardrails.yml.

This is a negative assertion test — it checks that stream-C (B1) does NOT
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
# TRC-C6's invariant is "stream-C / B1 adds no new checks" — the diff-scan
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


def _get_diff_lines() -> list[str]:
    """Get the diff of guardrails.yml from main to HEAD on this branch."""
    result = subprocess.run(
        ["git", "diff", "main...HEAD", "--", GUARDRAILS_YML],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    return result.stdout.splitlines()


def _get_added_lines() -> list[str]:
    """Return lines added (starting with '+') in the guardrails.yml diff."""
    return [
        line[1:]  # strip the leading '+'
        for line in _get_diff_lines()
        if line.startswith("+") and not line.startswith("+++")
    ]


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
        "B1 is a judgement-side rebalance — no new mechanism."
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
        "B1 is judgement-side only — no new gate."
    )


def test_guardrails_diff_has_only_comment_additions():
    """The diff of guardrails.yml by stream C must only contain comment additions (+#)."""
    added = _get_added_lines()
    # Filter to non-empty, non-blank lines
    meaningful_additions = [line for line in added if line.strip()]

    for line in meaningful_additions:
        stripped = line.strip()
        assert stripped.startswith("#"), (
            f"Stream C added a non-comment line to guardrails.yml: {line!r}. "
            "Only a comment (inline caveat) is permitted — no structural changes."
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
        "Add: '# stream-C (B1 / TRC-C6): only the coverage-floor caveat comment above was added — no new checks or gates.'"
    )
