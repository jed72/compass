"""Tests for `compass analyze` - Group A coherence and failure-mode scenarios.

Covers the group A consistency checks and their failure modes, one test
function per scenario, named below.

Each test invokes `compass analyze` via subprocess in an isolated project
directory (using the `project`/`run_cli` fixtures from conftest.py).
"""

# These tests assert the current file names; files written under older
# names still load (ADR-006).

# These tests assert the current stage names; manifests written under
# older names still load (ADR-006).
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict

import pytest
import yaml

# ---------------------------------------------------------------------------
# Helpers - build minimal issue fixtures
# ---------------------------------------------------------------------------

_MINIMAL_READINGS = {
    "risk": "contained",
    "familiarity": "brownfield-mapped",
    "size": "small",
    "intent": "delivery",
    "role": "engineer",
    "labels": [],
}

_CRITICAL_READINGS = {
    "risk": "critical",
    "familiarity": "brownfield-mapped",
    "size": "large",
    "intent": "delivery",
    "role": "engineer",
    "labels": [],
}

_AUTH_READINGS = {
    "risk": "contained",
    "familiarity": "brownfield-mapped",
    "size": "small",
    "intent": "delivery",
    "role": "engineer",
    "labels": ["auth"],
}


def _write_task(task_dir: Path, body: Dict[str, Any]) -> None:
    task_dir.mkdir(parents=True, exist_ok=True)
    with (task_dir / "manifest.yml").open("w", encoding="utf-8") as fh:
        yaml.safe_dump(body, fh, sort_keys=False)


def _minimal_task(slug: str, readings: Dict | None = None) -> Dict[str, Any]:
    return {
        "schema_version": "1.0",
        "task": slug,
        "created": "2026-05-25",
        "readings": readings or dict(_MINIMAL_READINGS),
        "delivery_approach": "express",
        "stages": {
            "assess": "full",
            "define": "light",
            "refine": "collapsed",
            "plan": "collapsed",
            "breakdown": "skipped",
            "implement": "full",
            "verify": "light",
            "ship": "light",
        },
        "gates": [
            {"id": "verify.correctness", "status": "pending", "evidence": []},
            {"id": "verify.governance", "status": "pending", "evidence": []},
            {"id": "verify.traceability", "status": "pending", "evidence": []},
        ],
        "scenarios": [],
        "evidence": [],
        "changed_files": [],
        "claims": [],
        "follow_ups": [],
        "policy_rules_fired": [],
        "topology": "solo",
    }


def _write_brief(task_dir: Path, intents: list[str]) -> None:
    """Write a minimal intent.md with intent lines the parser can find."""
    lines = ["# Brief\n\n## Intents\n"]
    for intent_id in intents:
        lines.append(f"<!-- intent: {intent_id} -->\n")
        lines.append(f"- {intent_id}: some intent statement\n")
    (task_dir / "intent.md").write_text("".join(lines), encoding="utf-8")


def _write_spec(task_dir: Path, scenarios: list[dict]) -> None:
    """Write a minimal acceptance-criteria.md with scenario blocks."""
    lines = ["# Spec\n\n"]
    for scn in scenarios:
        scn_id = scn["id"]
        intent_id = scn.get("intent", "INT-1")
        lines.append(f"### Scenario: {scn.get('title', scn_id)}\n")
        lines.append(f"<!-- traceability id: {scn_id} · serves: {intent_id} -->\n\n")
    (task_dir / "acceptance-criteria.md").write_text("".join(lines), encoding="utf-8")


def _write_route_md(task_dir: Path, route: str, phases: dict | None = None) -> None:
    """Write a minimal delivery-approach.md, in the v1 shape, that names the
    delivery approach and per-phase weights."""
    if phases is None:
        phases = {
            "Frame": "full", "Specify": "light", "Clarify": "collapsed",
            "Plan": "collapsed", "Distribute": "skipped", "Build": "full",
            "Verify": "light", "Land": "light",
        }
    lines = [f"# Route - test-task\n\n**Reference route:** {route.title()}\n\n"]
    lines.append("## Per-phase weight\n\n")
    lines.append("| Phase | Weight |\n|---|---|\n")
    for phase, weight in phases.items():
        lines.append(f"| {phase} | {weight} |\n")
    (task_dir / "delivery-approach.md").write_text("".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Coherent artifacts pass cleanly (TRC-A1)
# ---------------------------------------------------------------------------

def test_trc_a1_coherent_artifacts_pass_cleanly(project: Path, run_cli):
    """Coherent artifacts get exit 0 and zero findings (TRC-A1)."""
    slug = "coherent-task"
    task_dir = project / ".compass" / "work" / slug
    task_dir.mkdir(parents=True, exist_ok=True)

    # Write a manifest.yml with an intent-linked scenario
    body = _minimal_task(slug)
    body["scenarios"] = [{"id": "SCN-001", "intent": "INT-1", "title": "foo", "tests": []}]
    _write_task(task_dir, body)

    # intent.md declares INT-1
    _write_brief(task_dir, ["INT-1"])
    # acceptance-criteria.md links SCN-001 -> INT-1
    _write_spec(task_dir, [{"id": "SCN-001", "intent": "INT-1"}])
    # delivery-approach.md agrees with manifest.yml
    _write_route_md(task_dir, "express")

    (project / ".compass" / "current-task").write_text(slug, encoding="utf-8")

    result = run_cli("analyze")
    assert result.returncode == 0, f"Expected exit 0:\n{result}"
    combined = result.stdout + result.stderr
    # "PASS - no coherence findings" replaced "PASS - 0 finding(s)" on
    # 2026-08-24: a verdict reading "PASS - 1 finding(s)" was the problem, and
    # the fix was to stop pairing the word PASS with a count. The intent - a
    # clean run says plainly that it found nothing - is unchanged.
    assert "no coherence finding" in combined.lower() or \
        "0 finding" in combined.lower() or "zero finding" in combined.lower() or \
           "no finding" in combined.lower() or "findings: 0" in combined.lower() or \
           "clean" in combined.lower(), \
        f"Expected zero findings message:\n{result}"


# ---------------------------------------------------------------------------
# A scenario with no upstream intent is flagged as orphaned (TRC-A2)
# ---------------------------------------------------------------------------

def test_trc_a2_orphaned_scenario_flagged(project: Path, run_cli):
    """A scenario with no upstream intent gets a non-zero exit (gate mode)
    and an orphaned finding (TRC-A2)."""
    slug = "orphan-scn-task"
    task_dir = project / ".compass" / "work" / slug
    task_dir.mkdir(parents=True, exist_ok=True)

    body = _minimal_task(slug)
    # SCN-orphan has no matching intent in intent.md
    body["scenarios"] = [{"id": "SCN-orphan", "intent": "INT-MISSING", "title": "orphan", "tests": []}]
    # Put the issue in gate-clearing mode so findings → non-zero exit
    body["gates"] = [
        {"id": "verify.correctness", "status": "pending", "evidence": []},
        {"id": "verify.analyze", "status": "pending", "evidence": []},
    ]
    _write_task(task_dir, body)

    _write_brief(task_dir, ["INT-1"])  # INT-MISSING is not here
    _write_spec(task_dir, [{"id": "SCN-orphan", "intent": "INT-MISSING"}])
    _write_route_md(task_dir, "express")

    (project / ".compass" / "current-task").write_text(slug, encoding="utf-8")

    result = run_cli("analyze")
    assert result.returncode != 0, f"Expected non-zero exit:\n{result}"
    combined = result.stdout + result.stderr
    assert "SCN-orphan" in combined, f"Expected SCN-orphan in output:\n{result}"
    assert "orphan" in combined.lower(), f"Expected 'orphan' in output:\n{result}"


# ---------------------------------------------------------------------------
# A route-disagreement finding fires when delivery-approach.md disagrees with manifest.yml (TRC-A3)
# ---------------------------------------------------------------------------

def test_trc_a3_route_disagreement_flagged(project: Path, run_cli):
    """delivery-approach.md says 'Clarify: full' but manifest.yml says
    'clarify: collapsed', so `analyze` exits non-zero (TRC-A3)."""
    slug = "route-disagree-task"
    task_dir = project / ".compass" / "work" / slug
    task_dir.mkdir(parents=True, exist_ok=True)

    body = _minimal_task(slug)
    # manifest.yml says clarify: collapsed
    body["stages"]["refine"] = "collapsed"
    body["scenarios"] = [{"id": "SCN-001", "intent": "INT-1", "title": "foo", "tests": []}]
    # Gate mode so findings → non-zero
    body["gates"] = [
        {"id": "verify.correctness", "status": "pending", "evidence": []},
        {"id": "verify.analyze", "status": "pending", "evidence": []},
    ]
    _write_task(task_dir, body)

    _write_brief(task_dir, ["INT-1"])
    _write_spec(task_dir, [{"id": "SCN-001", "intent": "INT-1"}])
    # delivery-approach.md says Clarify: full (disagrees with manifest.yml's collapsed)
    _write_route_md(task_dir, "express", phases={
        "Frame": "full", "Specify": "light", "Clarify": "full",
        "Plan": "collapsed", "Distribute": "skipped", "Build": "full",
        "Verify": "light", "Land": "light",
    })

    (project / ".compass" / "current-task").write_text(slug, encoding="utf-8")

    result = run_cli("analyze")
    assert result.returncode != 0, f"Expected non-zero exit:\n{result}"
    combined = result.stdout + result.stderr
    assert "refine" in combined.lower(), f"Expected 'Clarify' in output:\n{result}"
    assert "route-disagreement" in combined.lower() or "disagree" in combined.lower(), \
        f"Expected route-disagreement finding:\n{result}"


# ---------------------------------------------------------------------------
# Claim with no backing scenario is flagged (TRC-A4)
# ---------------------------------------------------------------------------

def test_trc_a4_orphan_claim_flagged(project: Path, run_cli):
    """positioning.md has CLM-1 but no scenario in the spec links to it, so
    `analyze` exits non-zero (TRC-A4)."""
    slug = "orphan-claim-task"
    task_dir = project / ".compass" / "work" / slug
    task_dir.mkdir(parents=True, exist_ok=True)

    body = _minimal_task(slug)
    body["scenarios"] = [{"id": "SCN-001", "intent": "INT-1", "title": "foo", "tests": []}]
    # Gate mode so findings → non-zero
    body["gates"] = [
        {"id": "verify.correctness", "status": "pending", "evidence": []},
        {"id": "verify.analyze", "status": "pending", "evidence": []},
    ]
    _write_task(task_dir, body)

    _write_brief(task_dir, ["INT-1"])
    _write_spec(task_dir, [{"id": "SCN-001", "intent": "INT-1"}])
    _write_route_md(task_dir, "express")

    # positioning.md lists CLM-1 but no scenario links to it
    positioning = (
        "# Positioning\n\n"
        "## Claims\n\n"
        "<!-- claim: CLM-1 -->\n"
        "- CLM-1: some marketing claim\n"
    )
    (task_dir / "positioning.md").write_text(positioning, encoding="utf-8")

    (project / ".compass" / "current-task").write_text(slug, encoding="utf-8")

    result = run_cli("analyze")
    assert result.returncode != 0, f"Expected non-zero exit:\n{result}"
    combined = result.stdout + result.stderr
    assert "CLM-1" in combined, f"Expected CLM-1 in output:\n{result}"
    assert "orphan" in combined.lower(), f"Expected 'orphan' in output:\n{result}"


# ---------------------------------------------------------------------------
# Same artifacts and policy yield the same verdict (determinism) (TRC-A5)
# ---------------------------------------------------------------------------

def test_trc_a5_determinism(project: Path, run_cli):
    """Two runs on unchanged artifacts produce an identical verdict: findings
    and exit code (TRC-A5)."""
    import re as _re
    slug = "determinism-task"
    task_dir = project / ".compass" / "work" / slug
    task_dir.mkdir(parents=True, exist_ok=True)

    body = _minimal_task(slug)
    body["scenarios"] = [{"id": "SCN-001", "intent": "INT-1", "title": "foo", "tests": []}]
    _write_task(task_dir, body)
    _write_brief(task_dir, ["INT-1"])
    _write_spec(task_dir, [{"id": "SCN-001", "intent": "INT-1"}])
    _write_route_md(task_dir, "express")

    (project / ".compass" / "current-task").write_text(slug, encoding="utf-8")

    result1 = run_cli("analyze")
    result2 = run_cli("analyze")

    assert result1.returncode == result2.returncode, \
        "Same inputs must yield same exit code"

    # Strip lines that contain timestamps or unique evidence IDs from the output
    # before comparing - the evidence file name carries a timestamp by design
    # (DD-5), but the report content (findings, mode, issue name) must be
    # identical.
    def _strip_evidence_line(out: str):
        """Drop run-specific lines case-insensitively and return the count, so
        a renamed evidence line fails every run instead of one run in ten."""
        kept, dropped = [], 0
        for l in out.splitlines():
            low = l.strip().lower()
            if low.startswith("evidence:") or low.startswith("registry:"):
                dropped += 1
                continue
            kept.append(l)
        return "\n".join(kept), dropped

    out1, dropped1 = _strip_evidence_line(result1.stdout.strip())
    out2, dropped2 = _strip_evidence_line(result2.stdout.strip())

    # If the evidence line is ever renamed again, this fails on the next run
    # instead of failing one run in ten.
    assert dropped1 and dropped2, (
        "no evidence line was stripped, so the timestamped path is still in "
        "the comparison and this test will fail intermittently whenever two "
        "runs cross a second boundary. The line analyze prints must have been "
        f"renamed:\n{result1.stdout}")
    assert out1 == out2, \
        f"Non-deterministic report content:\nRun 1:\n{out1}\nRun 2:\n{out2}"


# ---------------------------------------------------------------------------
# Analyze opens no network or model client on its decision path (TRC-A6)
# ---------------------------------------------------------------------------

def test_trc_a6_no_network_no_model_client(project: Path, run_cli):
    """The `analyze` module must not import any HTTP or LLM client library
    (TRC-A6).

    Checks that the compass CLI source (specifically the `analyze`-related
    functions) does not import network or LLM client libraries.
    """
    # Read the compass CLI source and check the `analyze` section for bad imports.
    FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent.parent
    cli_path = FRAMEWORK_ROOT / "cli" / "compass"
    assert cli_path.is_file(), f"CLI not found at {cli_path}"

    src = cli_path.read_text(encoding="utf-8")

    # Extract just the `analyze` section (between the `analyze` marker and cmd_ci)
    analyze_start = src.find("# --- command: analyze ---")
    analyze_end = src.find("# --- command: ci ---")
    if analyze_start >= 0 and analyze_end > analyze_start:
        analyze_src = src[analyze_start:analyze_end]
    else:
        analyze_src = src  # fall back to whole file - conservative check

    # None of these should appear in the `analyze` section
    bad_libs = ["requests", "httpx", "urllib.request", "openai", "anthropic", "boto3", "aiohttp"]
    found = [lib for lib in bad_libs if lib in analyze_src]
    assert not found, \
        f"Network/LLM client library references found in analyze code: {found}"

    # Also run `analyze` to confirm no network socket is opened.
    # We check this by running `analyze` in a subprocess - if it completes quickly
    # and without errors, no network call was made (network calls would hang).
    slug = "no-network-task"
    task_dir = project / ".compass" / "work" / slug
    task_dir.mkdir(parents=True, exist_ok=True)

    body = _minimal_task(slug)
    body["scenarios"] = [{"id": "SCN-001", "intent": "INT-1", "title": "foo", "tests": []}]
    _write_task(task_dir, body)
    _write_brief(task_dir, ["INT-1"])
    _write_spec(task_dir, [{"id": "SCN-001", "intent": "INT-1"}])
    _write_route_md(task_dir, "express")

    (project / ".compass" / "current-task").write_text(slug, encoding="utf-8")

    # Should complete well under 1s (no network), timeout=5s
    result = run_cli("analyze", timeout=5)
    assert result.returncode == 0, f"analyze failed unexpectedly:\n{result}"


# ---------------------------------------------------------------------------
# Incoherence below the verify.analyze gate threshold warns but does not block ship (TRC-A7)
# ---------------------------------------------------------------------------

def test_trc_a7_advisory_mode_does_not_block(project: Path, run_cli):
    """A delivery approach without the verify.analyze gate makes `analyze`
    exit 0 even on findings, and advisory evidence is recorded (TRC-A7)."""
    slug = "advisory-task"
    task_dir = project / ".compass" / "work" / slug
    task_dir.mkdir(parents=True, exist_ok=True)

    body = _minimal_task(slug)
    # Insert an orphan scenario (INT-MISSING not in brief)
    body["scenarios"] = [{"id": "SCN-orphan", "intent": "INT-MISSING", "title": "x", "tests": []}]
    # The delivery approach has no verify.analyze gate (risk=contained, no auth)
    body["gates"] = [
        {"id": "verify.correctness", "status": "pending", "evidence": []},
        {"id": "verify.governance", "status": "pending", "evidence": []},
        {"id": "verify.traceability", "status": "pending", "evidence": []},
    ]
    _write_task(task_dir, body)
    _write_brief(task_dir, ["INT-1"])  # INT-MISSING absent
    _write_spec(task_dir, [{"id": "SCN-orphan", "intent": "INT-MISSING"}])
    _write_route_md(task_dir, "express")

    (project / ".compass" / "current-task").write_text(slug, encoding="utf-8")

    result = run_cli("analyze")
    # Advisory mode: findings exist but exit code should be 0
    assert result.returncode == 0, \
        f"Advisory analyze (no verify.analyze gate) must exit 0 even with findings:\n{result}"

    combined = result.stdout + result.stderr
    # Should mention "advisory"
    assert "advisory" in combined.lower(), \
        f"Expected 'advisory' in output:\n{result}"

    # Evidence file should be written with ADVISORY prefix
    ev_dir = task_dir / "evidence"
    advisory_files = list(ev_dir.glob("EV-ANALYZE-ADVISORY-*")) if ev_dir.exists() else []
    assert len(advisory_files) >= 1, \
        f"Expected an EV-ANALYZE-ADVISORY-* evidence file in {ev_dir}:\n{result}"


# ---------------------------------------------------------------------------
# Incoherence on a delivery approach that earns the verify.analyze gate blocks ship (TRC-A8)
# ---------------------------------------------------------------------------

def test_trc_a8_gate_mode_blocks_on_findings(project: Path, run_cli):
    """A delivery approach with the verify.analyze gate makes `analyze` exit
    non-zero on findings (TRC-A8)."""
    slug = "gate-task"
    task_dir = project / ".compass" / "work" / slug
    task_dir.mkdir(parents=True, exist_ok=True)

    body = _minimal_task(slug)
    body["assessment"] = dict(_CRITICAL_READINGS)
    body["delivery_approach"] = "expedition"
    body["scenarios"] = [{"id": "SCN-orphan", "intent": "INT-MISSING", "title": "x", "tests": []}]
    # The delivery approach has the verify.analyze gate
    body["gates"] = [
        {"id": "verify.correctness", "status": "pending", "evidence": []},
        {"id": "verify.governance", "status": "pending", "evidence": []},
        {"id": "verify.traceability", "status": "pending", "evidence": []},
        {"id": "verify.analyze", "status": "pending", "evidence": []},
    ]
    _write_task(task_dir, body)
    _write_brief(task_dir, ["INT-1"])
    _write_spec(task_dir, [{"id": "SCN-orphan", "intent": "INT-MISSING"}])
    _write_route_md(task_dir, "expedition")

    (project / ".compass" / "current-task").write_text(slug, encoding="utf-8")

    result = run_cli("analyze")
    assert result.returncode != 0, \
        f"Gate mode analyze with findings must exit non-zero:\n{result}"

    # Gate-mode evidence must use the `EV-ANALYZE-` prefix (not ADVISORY)
    ev_dir = task_dir / "evidence"
    gate_files = list(ev_dir.glob("EV-ANALYZE-[!A]*")) + list(ev_dir.glob("EV-ANALYZE-[0-9]*")) \
        if ev_dir.exists() else []
    # Also check for non-ADVISORY files more broadly
    all_ev = list(ev_dir.glob("EV-ANALYZE-*")) if ev_dir.exists() else []
    advisory_ev = list(ev_dir.glob("EV-ANALYZE-ADVISORY-*")) if ev_dir.exists() else []
    non_advisory_ev = [f for f in all_ev if f not in advisory_ev]
    assert len(non_advisory_ev) >= 1, \
        f"Expected a non-advisory EV-ANALYZE-* evidence file:\n{result}"


# ---------------------------------------------------------------------------
# `analyze` is never promoted to a gate globally (TRC-A9)
# ---------------------------------------------------------------------------

def test_trc_a9_analyze_not_a_global_gate(project: Path, run_cli):
    """Issues on a delivery approach without verify.analyze are not blocked
    by `analyze` (TRC-A9)."""
    for i, slug in enumerate(["no-gate-task-1", "no-gate-task-2"]):
        task_dir = project / ".compass" / "work" / slug
        task_dir.mkdir(parents=True, exist_ok=True)

        body = _minimal_task(slug)
        # Orphan scenario - findings exist
        body["scenarios"] = [{"id": "SCN-orphan", "intent": "INT-MISSING", "title": "x", "tests": []}]
        # The delivery approach does not have verify.analyze
        body["gates"] = [
            {"id": "verify.correctness", "status": "pending", "evidence": []},
            {"id": "verify.governance", "status": "pending", "evidence": []},
            {"id": "verify.traceability", "status": "pending", "evidence": []},
        ]
        _write_task(task_dir, body)
        _write_brief(task_dir, ["INT-1"])
        _write_spec(task_dir, [{"id": "SCN-orphan", "intent": "INT-MISSING"}])
        _write_route_md(task_dir, "express")

    # Run `analyze` for each issue
    for slug in ["no-gate-task-1", "no-gate-task-2"]:
        (project / ".compass" / "current-task").write_text(slug, encoding="utf-8")
        result = run_cli("analyze")
        assert result.returncode == 0, \
            f"Task '{slug}' without verify.analyze gate must not be blocked:\n{result}"


# ---------------------------------------------------------------------------
# An artifact a delivery approach legitimately omits is not flagged (TRC-A10)
# ---------------------------------------------------------------------------

def test_trc_a10_legitimately_omitted_artifact_not_flagged(project: Path, run_cli):
    """A hotfix delivery approach without intent.md gets no missing-artifact
    finding (TRC-A10)."""
    slug = "hotfix-task"
    task_dir = project / ".compass" / "work" / slug
    task_dir.mkdir(parents=True, exist_ok=True)

    # Hotfix delivery approach - intent.md is legitimately absent (reproduce-first,
    # no define stage)
    body = _minimal_task(slug)
    body["delivery_approach"] = "hotfix"
    body["stages"] = {
        "assess": "light",
        "define": "reproduce-first",
        "refine": "collapsed",
        "plan": "collapsed",
        "breakdown": "skipped",
        "implement": "expedited",
        "verify": "full",
        "ship": "full-plus-backfill",
    }
    body["scenarios"] = [{"id": "SCN-001", "intent": "INT-1", "title": "foo", "tests": []}]
    _write_task(task_dir, body)

    # No intent.md - the delivery approach legitimately omits it
    # acceptance-criteria.md still exists (minimal)
    _write_spec(task_dir, [{"id": "SCN-001", "intent": "INT-1"}])
    _write_route_md(task_dir, "hotfix", phases={
        "Frame": "light", "Specify": "reproduce-first", "Clarify": "collapsed",
        "Plan": "collapsed", "Distribute": "skipped", "Build": "expedited",
        "Verify": "full", "Land": "full-plus-backfill",
    })

    (project / ".compass" / "current-task").write_text(slug, encoding="utf-8")

    result = run_cli("analyze")
    combined = result.stdout + result.stderr
    # No "missing intent" or "missing-artifact" finding about intent.md
    assert "intent.md" not in combined or "missing" not in combined.lower(), \
        f"Hotfix route must not flag missing brief.md:\n{result}"
    # Should not flag orphaned scenarios either (spec links INT-1 but no intent.md - that's OK on hotfix)
    # The key assertion: no route-disagreement finding (delivery-approach.md and manifest.yml agree on hotfix)
    assert "route-disagreement" not in combined.lower(), \
        f"No route-disagreement expected for consistent hotfix:\n{result}"


# ---------------------------------------------------------------------------
# Analyze reports only coherence findings, not evidence findings (TRC-A11)
# ---------------------------------------------------------------------------

def test_trc_a11_no_evidence_findings(project: Path, run_cli):
    """An issue missing gate evidence is not reported by `analyze`: that is
    `compass check`'s job (TRC-A11)."""
    slug = "no-evidence-task"
    task_dir = project / ".compass" / "work" / slug
    task_dir.mkdir(parents=True, exist_ok=True)

    body = _minimal_task(slug)
    body["scenarios"] = [{"id": "SCN-001", "intent": "INT-1", "title": "foo", "tests": []}]
    # Gate is 'pass' but NO evidence referenced - compass check would fail this
    # But `analyze` must not report it
    body["gates"] = [
        {"id": "verify.correctness", "status": "pass", "evidence": []},  # missing evidence!
    ]
    _write_task(task_dir, body)
    _write_brief(task_dir, ["INT-1"])
    _write_spec(task_dir, [{"id": "SCN-001", "intent": "INT-1"}])
    _write_route_md(task_dir, "express")

    (project / ".compass" / "current-task").write_text(slug, encoding="utf-8")

    result = run_cli("analyze")
    combined = result.stdout + result.stderr
    # analyze must NOT report the missing evidence (that's compass check's job)
    assert "no evidence" not in combined.lower() or "gate" not in combined.lower(), \
        f"analyze should not report missing gate evidence:\n{result}"
    # The analysis should produce 0 coherence findings (everything is coherent)
    # specifically: no "missing-artifact", no "orphaned-intent", no "route-disagreement"
    assert "missing-artifact" not in combined.lower(), \
        f"analyze should report zero evidence-type findings:\n{result}"


# ---------------------------------------------------------------------------
# Analyze gate promotion is driven by routing-policy, not hard-coded (TRC-A12)
# ---------------------------------------------------------------------------

def test_trc_a12_gate_promotion_driven_by_policy(project: Path, run_cli):
    """The routing-policy floor RP-REQUIRE-001 adds verify.analyze to an
    issue with labels=[auth]; the evaluator writes it to manifest.yml.gates
    (TRC-A12)."""
    slug = "auth-task"
    task_dir = project / ".compass" / "work" / slug
    task_dir.mkdir(parents=True, exist_ok=True)

    body = _minimal_task(slug)
    body["assessment"] = dict(_AUTH_READINGS)  # labels: [auth]
    body["delivery_approach"] = "expedition"
    body["scenarios"] = [{"id": "SCN-001", "intent": "INT-1", "title": "foo", "tests": []}]
    _write_task(task_dir, body)
    _write_brief(task_dir, ["INT-1"])
    _write_spec(task_dir, [{"id": "SCN-001", "intent": "INT-1"}])
    _write_route_md(task_dir, "expedition")

    (project / ".compass" / "current-task").write_text(slug, encoding="utf-8")

    # Run compass approach evaluate --write to apply the policy (including new floors)
    result = run_cli("approach", "evaluate", "--write")
    assert result.returncode == 0, f"route evaluate --write failed:\n{result}"

    # Load the updated manifest.yml
    import yaml as _yaml
    with (task_dir / "manifest.yml").open("r", encoding="utf-8") as fh:
        updated = _yaml.safe_load(fh)

    gate_ids = [g["id"] for g in updated.get("gates", []) if isinstance(g, dict)]
    assert "verify.analyze" in gate_ids, \
        f"Expected verify.analyze in gates after route evaluate on auth task:\n{gate_ids}"

    # And check the fired_guardrails contains a reference to the floor
    fired = updated.get("policy_rules_fired", [])
    fired_ids = [f.get("id") for f in fired]
    assert any("FLOOR-00" in (fid or "") for fid in fired_ids), \
        f"Expected a floor to fire in fired_guardrails:\n{fired_ids}"


# ---------------------------------------------------------------------------
# Analyze completes within the interactive latency target (<3s p95) (TRC-A13)
# ---------------------------------------------------------------------------

def test_trc_a13_latency_under_3s(project: Path, run_cli):
    """20 runs of `analyze` against a fixture keep p95 under 3000ms (TRC-A13)."""
    slug = "latency-task"
    task_dir = project / ".compass" / "work" / slug
    task_dir.mkdir(parents=True, exist_ok=True)

    body = _minimal_task(slug)
    body["scenarios"] = [{"id": "SCN-001", "intent": "INT-1", "title": "foo", "tests": []}]
    _write_task(task_dir, body)
    _write_brief(task_dir, ["INT-1"])
    _write_spec(task_dir, [{"id": "SCN-001", "intent": "INT-1"}])
    _write_route_md(task_dir, "express")

    (project / ".compass" / "current-task").write_text(slug, encoding="utf-8")

    RUNS = 20
    # Use a generous per-invocation timeout to allow for system load in CI.
    # The actual `analyze` command is ~100-500ms; 10s is a generous ceiling.
    durations = []
    for _ in range(RUNS):
        start = time.perf_counter()
        result = run_cli("analyze", timeout=10)
        elapsed = time.perf_counter() - start
        durations.append(elapsed)

    durations.sort()
    # p95 index for 20 samples - index 18 (0-based, sorted ascending)
    p95_idx = int(RUNS * 0.95) - 1
    p95 = durations[p95_idx]
    # The 3s p95 target is provisional (BF-1)
    assert p95 < 3.0, \
        f"p95 latency {p95:.3f}s exceeds 3s target. Durations: {[f'{d:.3f}' for d in durations]}\n" \
        f"NOTE: this test is sensitive to system load. Run in isolation if flaky."


# ---------------------------------------------------------------------------
# Analyze on a malformed manifest.yml exits non-zero with structured error (TRC-F1)
# ---------------------------------------------------------------------------

def test_trc_f1_malformed_task_yml(project: Path, run_cli):
    """manifest.yml with a YAML parse error gets a non-zero exit, and stderr
    names the file (TRC-F1)."""
    slug = "malformed-task"
    task_dir = project / ".compass" / "work" / slug
    task_dir.mkdir(parents=True, exist_ok=True)

    # Write invalid YAML
    (task_dir / "manifest.yml").write_text(
        "task: malformed-task\nreadings: {blast_radius: [broken yaml\n",
        encoding="utf-8",
    )

    (project / ".compass" / "current-task").write_text(slug, encoding="utf-8")

    result = run_cli("analyze")
    assert result.returncode != 0, f"Expected non-zero exit for malformed YAML:\n{result}"
    assert "manifest.yml" in result.stderr or "manifest.yml" in result.stdout, \
        f"Expected manifest.yml path in error output:\n{result}"
    # No partial evidence left behind
    ev_dir = task_dir / "evidence"
    partial = list(ev_dir.glob("EV-ANALYZE-*")) if ev_dir.exists() else []
    assert len(partial) == 0, \
        f"No partial analyze evidence should be written on parse error:\n{partial}"


# ---------------------------------------------------------------------------
# Analyze on an issue that has not yet been assessed reports clearly (TRC-F4)
# ---------------------------------------------------------------------------

def test_trc_f4_unframed_task(project: Path, run_cli):
    """A slug with no manifest.yml gets a non-zero exit, and stderr says the
    issue does not exist and names the slug (TRC-F4)."""
    # Point current-task at a slug that has no manifest.yml
    slug = "unframed-task"
    (project / ".compass" / "current-task").write_text(slug, encoding="utf-8")
    # Do not create the issue directory or manifest.yml

    result = run_cli("analyze")
    assert result.returncode != 0, f"Expected non-zero exit for unframed task:\n{result}"
    combined = result.stdout + result.stderr
    # Do not assert on "frame": the slug `unframed-task` contains it, so such
    # an assertion passes whatever the tool prints.
    assert "does not exist" in combined.lower(), \
        f"the message does not say what is wrong with the issue:\n{result}"
    assert "unframed-task" in combined, \
        f"the message does not name the issue it could not find:\n{result}"
    # Must not report a coherence finding (the issue has simply not been assessed)
    assert "orphan" not in combined.lower() and \
           "route-disagreement" not in combined.lower() and \
           "missing-artifact" not in combined.lower(), \
        f"Must not report coherence findings for unframed task:\n{result}"


# ---------------------------------------------------------------------------
# A hand-edit to manifest.yml made by a tool is caught by `analyze` (TRC-F5)
# ---------------------------------------------------------------------------

def test_trc_f5_hand_edited_route_caught(project: Path, run_cli):
    """manifest.yml's delivery_approach field hand-edited to disagree with
    delivery-approach.md gets a route-disagreement finding (gate mode, so
    non-zero exit) (TRC-F5)."""
    slug = "hand-edited-task"
    task_dir = project / ".compass" / "work" / slug
    task_dir.mkdir(parents=True, exist_ok=True)

    body = _minimal_task(slug)
    body["scenarios"] = [{"id": "SCN-001", "intent": "INT-1", "title": "foo", "tests": []}]
    # Hand-edit: manifest.yml says 'expedition' phases but delivery-approach.md
    # says 'express' phases.
    # That is a route-disagreement finding: a tool hand-edited the
    # delivery_approach field.
    body["delivery_approach"] = "expedition"
    body["stages"] = {
        "assess": "full", "define": "full", "refine": "full",
        "plan": "full", "breakdown": "swarm", "implement": "full",
        "verify": "full", "ship": "full",
    }
    # Gate mode so findings → non-zero
    body["gates"] = [
        {"id": "verify.correctness", "status": "pending", "evidence": []},
        {"id": "verify.analyze", "status": "pending", "evidence": []},
    ]
    _write_task(task_dir, body)
    _write_brief(task_dir, ["INT-1"])
    _write_spec(task_dir, [{"id": "SCN-001", "intent": "INT-1"}])
    # delivery-approach.md says express with express phases - disagrees with manifest.yml's expedition phases
    _write_route_md(task_dir, "express", phases={
        "Frame": "full", "Specify": "light", "Clarify": "collapsed",
        "Plan": "collapsed", "Distribute": "skipped", "Build": "full",
        "Verify": "light", "Land": "light",
    })

    (project / ".compass" / "current-task").write_text(slug, encoding="utf-8")

    result = run_cli("analyze")
    assert result.returncode != 0, \
        f"Expected non-zero exit for hand-edited route field:\n{result}"
    combined = result.stdout + result.stderr
    assert "route-disagreement" in combined.lower() or "disagree" in combined.lower(), \
        f"Expected route-disagreement finding:\n{result}"


# ---------------------------------------------------------------------------
# The route-disagreement check must read the table the shipped template writes
# ---------------------------------------------------------------------------

# Copied from templates/delivery-approach.md's "4a. Per-stage weight" section:
# the header word, the prose stage names, the capitalised weights, and a weight
# cell carrying a trailing note. Every one of those defeated the parser.
_TEMPLATE_SHAPED_TABLE = """# Delivery approach - demo

### 4a. Per-stage weight

| Stage | Weight | Why |
|---|---|---|
| Assess | Full | Always. This document is the output. |
| Define acceptance criteria | full | The compatibility rule is the whole risk. |
| Requirements review | collapsed | One scenario, certified unambiguous. |
| Design | full | A real design decision sits here. |
| Break down the work | full, streams unbounded by policy | Disjoint files. |
| Implement | full | |
| Test & review | full | Eight gates. |
| Ship | full | |
"""


def _weights(tmp_path, body):
    from compass_pkg.analyze import _parse_phase_weights_from_route_md

    p = tmp_path / "delivery-approach.md"
    p.write_text(body, encoding="utf-8")
    return _parse_phase_weights_from_route_md(str(p))


def test_the_parser_reads_the_table_the_template_writes(tmp_path):
    """The parser must read the table the shipped template writes: a
    `| Stage |` header, prose stage names, and a weight cell with a trailing
    note. Each fix alone still returns almost nothing, so the test asserts
    all three together.
    """
    got = _weights(tmp_path, _TEMPLATE_SHAPED_TABLE)
    assert got == {
        "assess": "full",
        "define": "full",
        "refine": "collapsed",
        "plan": "full",
        "breakdown": "full",
        "implement": "full",
        "verify": "full",
        "ship": "full",
    }, got


def test_the_parser_still_reads_the_retired_header(tmp_path):
    """The control: records written under the old header keep parsing.

    51 delivery-approach records are on disk and some say `| Phase |`. Fixing
    the header must not swap one blind spot for another.
    """
    body = _TEMPLATE_SHAPED_TABLE.replace("| Stage | Weight", "| Phase | Weight")
    assert _weights(tmp_path, body).get("plan") == "full"
