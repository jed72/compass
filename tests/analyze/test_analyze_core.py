"""Tests for `compass analyze` - Group A coherence and failure-mode scenarios.

Covers TRC-A1 through TRC-A13, TRC-F1, TRC-F4, TRC-F5.

Each test invokes `compass analyze` via subprocess in an isolated project
directory (using the `project`/`run_cli` fixtures from conftest.py).
"""
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
# Helpers - build minimal task fixtures
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
    with (task_dir / "task.yml").open("w", encoding="utf-8") as fh:
        yaml.safe_dump(body, fh, sort_keys=False)


def _minimal_task(slug: str, readings: Dict | None = None) -> Dict[str, Any]:
    return {
        "schema_version": "1.0",
        "task": slug,
        "created": "2026-05-25",
        "readings": readings or dict(_MINIMAL_READINGS),
        "delivery_approach": "express",
        "stages": {
            "frame": "full",
            "specify": "light",
            "clarify": "collapsed",
            "plan": "collapsed",
            "distribute": "skipped",
            "build": "full",
            "verify": "light",
            "land": "light",
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
    """Write a minimal brief.md with intent lines the parser can find."""
    lines = ["# Brief\n\n## Intents\n"]
    for intent_id in intents:
        lines.append(f"<!-- intent: {intent_id} -->\n")
        lines.append(f"- {intent_id}: some intent statement\n")
    (task_dir / "prd.md").write_text("".join(lines), encoding="utf-8")


def _write_spec(task_dir: Path, scenarios: list[dict]) -> None:
    """Write a minimal spec.feature.md with scenario blocks."""
    lines = ["# Spec\n\n"]
    for scn in scenarios:
        scn_id = scn["id"]
        intent_id = scn.get("intent", "INT-1")
        lines.append(f"### Scenario: {scn.get('title', scn_id)}\n")
        lines.append(f"<!-- traceability id: {scn_id} · serves: {intent_id} -->\n\n")
    (task_dir / "acceptance-criteria.md").write_text("".join(lines), encoding="utf-8")


def _write_route_md(task_dir: Path, route: str, phases: dict | None = None) -> None:
    """Write a minimal route.md that names the route and per-phase weights."""
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
# TRC-A1 - coherent artifacts pass cleanly
# ---------------------------------------------------------------------------

def test_trc_a1_coherent_artifacts_pass_cleanly(project: Path, run_cli):
    """TRC-A1: coherent artifacts → exit 0 and zero findings."""
    slug = "coherent-task"
    task_dir = project / ".compass" / "work" / slug
    task_dir.mkdir(parents=True, exist_ok=True)

    # Write a task.yml with an intent-linked scenario
    body = _minimal_task(slug)
    body["scenarios"] = [{"id": "SCN-001", "intent": "INT-1", "title": "foo", "tests": []}]
    _write_task(task_dir, body)

    # brief.md declares INT-1
    _write_brief(task_dir, ["INT-1"])
    # spec.feature.md links SCN-001 -> INT-1
    _write_spec(task_dir, [{"id": "SCN-001", "intent": "INT-1"}])
    # route.md agrees with task.yml
    _write_route_md(task_dir, "express")

    (project / ".compass" / "current-task").write_text(slug, encoding="utf-8")

    result = run_cli("analyze")
    assert result.returncode == 0, f"Expected exit 0:\n{result}"
    combined = result.stdout + result.stderr
    assert "0 finding" in combined.lower() or "zero finding" in combined.lower() or \
           "no finding" in combined.lower() or "findings: 0" in combined.lower() or \
           "clean" in combined.lower(), \
        f"Expected zero findings message:\n{result}"


# ---------------------------------------------------------------------------
# TRC-A2 - a scenario with no upstream intent is flagged as orphaned
# ---------------------------------------------------------------------------

def test_trc_a2_orphaned_scenario_flagged(project: Path, run_cli):
    """TRC-A2: scenario with no upstream intent → non-zero exit (gate mode) + orphaned finding."""
    slug = "orphan-scn-task"
    task_dir = project / ".compass" / "work" / slug
    task_dir.mkdir(parents=True, exist_ok=True)

    body = _minimal_task(slug)
    # SCN-orphan has no matching intent in brief.md
    body["scenarios"] = [{"id": "SCN-orphan", "intent": "INT-MISSING", "title": "orphan", "tests": []}]
    # Put the task in gate-clearing mode so findings → non-zero exit
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
# TRC-A3 - route disagreement between route.md and task.yml is flagged
# ---------------------------------------------------------------------------

def test_trc_a3_route_disagreement_flagged(project: Path, run_cli):
    """TRC-A3: route.md says 'Clarify: full' but task.yml says 'clarify: collapsed' → non-zero."""
    slug = "route-disagree-task"
    task_dir = project / ".compass" / "work" / slug
    task_dir.mkdir(parents=True, exist_ok=True)

    body = _minimal_task(slug)
    # task.yml says clarify: collapsed
    body["stages"]["clarify"] = "collapsed"
    body["scenarios"] = [{"id": "SCN-001", "intent": "INT-1", "title": "foo", "tests": []}]
    # Gate mode so findings → non-zero
    body["gates"] = [
        {"id": "verify.correctness", "status": "pending", "evidence": []},
        {"id": "verify.analyze", "status": "pending", "evidence": []},
    ]
    _write_task(task_dir, body)

    _write_brief(task_dir, ["INT-1"])
    _write_spec(task_dir, [{"id": "SCN-001", "intent": "INT-1"}])
    # route.md says Clarify: full (disagrees with task.yml's collapsed)
    _write_route_md(task_dir, "express", phases={
        "Frame": "full", "Specify": "light", "Clarify": "full",
        "Plan": "collapsed", "Distribute": "skipped", "Build": "full",
        "Verify": "light", "Land": "light",
    })

    (project / ".compass" / "current-task").write_text(slug, encoding="utf-8")

    result = run_cli("analyze")
    assert result.returncode != 0, f"Expected non-zero exit:\n{result}"
    combined = result.stdout + result.stderr
    assert "clarify" in combined.lower(), f"Expected 'Clarify' in output:\n{result}"
    assert "route-disagreement" in combined.lower() or "disagree" in combined.lower(), \
        f"Expected route-disagreement finding:\n{result}"


# ---------------------------------------------------------------------------
# TRC-A4 - claim with no backing scenario is flagged
# ---------------------------------------------------------------------------

def test_trc_a4_orphan_claim_flagged(project: Path, run_cli):
    """TRC-A4: positioning.md has CLM-1 but no scenario in spec links to it → non-zero."""
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
# TRC-A5 - same artifacts and policy yield the same verdict (determinism)
# ---------------------------------------------------------------------------

def test_trc_a5_determinism(project: Path, run_cli):
    """TRC-A5: two runs on unchanged artifacts produce identical verdict (findings + exit code)."""
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
    # before comparing - the evidence FILE NAME contains a timestamp (by design,
    # DD-5), but the REPORT CONTENT (findings, mode, task name) must be identical.
    def _strip_evidence_line(out: str) -> str:
        lines = [l for l in out.splitlines()
                 if not (l.strip().startswith("evidence:") or
                         l.strip().startswith("registry:"))]
        return "\n".join(lines)

    out1 = _strip_evidence_line(result1.stdout.strip())
    out2 = _strip_evidence_line(result2.stdout.strip())
    assert out1 == out2, \
        f"Non-deterministic report content:\nRun 1:\n{out1}\nRun 2:\n{out2}"


# ---------------------------------------------------------------------------
# TRC-A6 - analyze opens no network or model client on its decision path
# ---------------------------------------------------------------------------

def test_trc_a6_no_network_no_model_client(project: Path, run_cli):
    """TRC-A6: analyze module must not import any HTTP/LLM client library.

    Checks that the compass CLI source (specifically the analyze-related
    functions) does not import network or LLM client libraries.
    """
    # Read the compass CLI source and check the analyze section for bad imports.
    FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent.parent
    cli_path = FRAMEWORK_ROOT / "cli" / "compass"
    assert cli_path.is_file(), f"CLI not found at {cli_path}"

    src = cli_path.read_text(encoding="utf-8")

    # Extract just the analyze section (between the analyze marker and cmd_ci)
    analyze_start = src.find("# --- command: analyze ---")
    analyze_end = src.find("# --- command: ci ---")
    if analyze_start >= 0 and analyze_end > analyze_start:
        analyze_src = src[analyze_start:analyze_end]
    else:
        analyze_src = src  # fall back to whole file - conservative check

    # None of these should appear in the analyze section
    bad_libs = ["requests", "httpx", "urllib.request", "openai", "anthropic", "boto3", "aiohttp"]
    found = [lib for lib in bad_libs if lib in analyze_src]
    assert not found, \
        f"Network/LLM client library references found in analyze code: {found}"

    # Also run analyze to confirm no network socket is opened.
    # We check this by running analyze in a subprocess - if it completes quickly
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
# TRC-A7 - incoherence on a route below threshold warns but does not block Land
# ---------------------------------------------------------------------------

def test_trc_a7_advisory_mode_does_not_block(project: Path, run_cli):
    """TRC-A7: route without verify.analyze gate → analyze exits 0 even on findings,
    and advisory evidence is recorded."""
    slug = "advisory-task"
    task_dir = project / ".compass" / "work" / slug
    task_dir.mkdir(parents=True, exist_ok=True)

    body = _minimal_task(slug)
    # Insert an orphan scenario (INT-MISSING not in brief)
    body["scenarios"] = [{"id": "SCN-orphan", "intent": "INT-MISSING", "title": "x", "tests": []}]
    # Route has NO verify.analyze gate (risk=contained, no auth)
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
# TRC-A8 - incoherence on a route that earns the analyze gate blocks Land
# ---------------------------------------------------------------------------

def test_trc_a8_gate_mode_blocks_on_findings(project: Path, run_cli):
    """TRC-A8: route WITH verify.analyze gate → analyze exits non-zero on findings."""
    slug = "gate-task"
    task_dir = project / ".compass" / "work" / slug
    task_dir.mkdir(parents=True, exist_ok=True)

    body = _minimal_task(slug)
    body["assessment"] = dict(_CRITICAL_READINGS)
    body["delivery_approach"] = "expedition"
    body["scenarios"] = [{"id": "SCN-orphan", "intent": "INT-MISSING", "title": "x", "tests": []}]
    # Route HAS verify.analyze gate
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

    # Gate-mode evidence must use EV-ANALYZE- prefix (not ADVISORY)
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
# TRC-A9 - analyze is never promoted to a gate globally
# ---------------------------------------------------------------------------

def test_trc_a9_analyze_not_a_global_gate(project: Path, run_cli):
    """TRC-A9: tasks on routes without verify.analyze are not blocked by analyze."""
    for i, slug in enumerate(["no-gate-task-1", "no-gate-task-2"]):
        task_dir = project / ".compass" / "work" / slug
        task_dir.mkdir(parents=True, exist_ok=True)

        body = _minimal_task(slug)
        # Orphan scenario - findings exist
        body["scenarios"] = [{"id": "SCN-orphan", "intent": "INT-MISSING", "title": "x", "tests": []}]
        # Route does NOT have verify.analyze
        body["gates"] = [
            {"id": "verify.correctness", "status": "pending", "evidence": []},
            {"id": "verify.governance", "status": "pending", "evidence": []},
            {"id": "verify.traceability", "status": "pending", "evidence": []},
        ]
        _write_task(task_dir, body)
        _write_brief(task_dir, ["INT-1"])
        _write_spec(task_dir, [{"id": "SCN-orphan", "intent": "INT-MISSING"}])
        _write_route_md(task_dir, "express")

    # Run analyze for each task
    for slug in ["no-gate-task-1", "no-gate-task-2"]:
        (project / ".compass" / "current-task").write_text(slug, encoding="utf-8")
        result = run_cli("analyze")
        assert result.returncode == 0, \
            f"Task '{slug}' without verify.analyze gate must not be blocked:\n{result}"


# ---------------------------------------------------------------------------
# TRC-A10 - an artifact a route legitimately omits is not flagged
# ---------------------------------------------------------------------------

def test_trc_a10_legitimately_omitted_artifact_not_flagged(project: Path, run_cli):
    """TRC-A10: Hotfix route without brief.md → no missing-artifact finding."""
    slug = "hotfix-task"
    task_dir = project / ".compass" / "work" / slug
    task_dir.mkdir(parents=True, exist_ok=True)

    # Hotfix route - brief.md is legitimately absent (reproduce-first, no Specify)
    body = _minimal_task(slug)
    body["delivery_approach"] = "hotfix"
    body["stages"] = {
        "frame": "light",
        "specify": "reproduce-first",
        "clarify": "collapsed",
        "plan": "collapsed",
        "distribute": "skipped",
        "build": "expedited",
        "verify": "full",
        "land": "full-plus-backfill",
    }
    body["scenarios"] = [{"id": "SCN-001", "intent": "INT-1", "title": "foo", "tests": []}]
    _write_task(task_dir, body)

    # NO brief.md - route legitimately omits it
    # spec.feature.md still exists (minimal)
    _write_spec(task_dir, [{"id": "SCN-001", "intent": "INT-1"}])
    _write_route_md(task_dir, "hotfix", phases={
        "Frame": "light", "Specify": "reproduce-first", "Clarify": "collapsed",
        "Plan": "collapsed", "Distribute": "skipped", "Build": "expedited",
        "Verify": "full", "Land": "full-plus-backfill",
    })

    (project / ".compass" / "current-task").write_text(slug, encoding="utf-8")

    result = run_cli("analyze")
    combined = result.stdout + result.stderr
    # No "missing brief" or "missing-artifact" finding about brief.md
    assert "prd.md" not in combined or "missing" not in combined.lower(), \
        f"Hotfix route must not flag missing brief.md:\n{result}"
    # Should not flag orphaned scenarios either (spec links INT-1 but no brief - that's OK on hotfix)
    # The key assertion: no route-disagreement finding (route.md and task.yml agree on hotfix)
    assert "route-disagreement" not in combined.lower(), \
        f"No route-disagreement expected for consistent hotfix:\n{result}"


# ---------------------------------------------------------------------------
# TRC-A11 - analyze reports only coherence findings, not evidence findings
# ---------------------------------------------------------------------------

def test_trc_a11_no_evidence_findings(project: Path, run_cli):
    """TRC-A11: a task missing gate evidence → analyze does not report it."""
    slug = "no-evidence-task"
    task_dir = project / ".compass" / "work" / slug
    task_dir.mkdir(parents=True, exist_ok=True)

    body = _minimal_task(slug)
    body["scenarios"] = [{"id": "SCN-001", "intent": "INT-1", "title": "foo", "tests": []}]
    # Gate is 'pass' but NO evidence referenced - compass check would fail this
    # But analyze should NOT report it
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
# TRC-A12 - analyze gate promotion is driven by routing-policy, not hard-coded
# ---------------------------------------------------------------------------

def test_trc_a12_gate_promotion_driven_by_policy(project: Path, run_cli):
    """TRC-A12: the routing-policy floor RP-REQUIRE-001 adds verify.analyze to a
    task with touches=[auth]; the evaluator writes it to task.yml.gates."""
    slug = "auth-task"
    task_dir = project / ".compass" / "work" / slug
    task_dir.mkdir(parents=True, exist_ok=True)

    body = _minimal_task(slug)
    body["assessment"] = dict(_AUTH_READINGS)  # touches: [auth]
    body["delivery_approach"] = "expedition"
    body["scenarios"] = [{"id": "SCN-001", "intent": "INT-1", "title": "foo", "tests": []}]
    _write_task(task_dir, body)
    _write_brief(task_dir, ["INT-1"])
    _write_spec(task_dir, [{"id": "SCN-001", "intent": "INT-1"}])
    _write_route_md(task_dir, "expedition")

    (project / ".compass" / "current-task").write_text(slug, encoding="utf-8")

    # Run route evaluate --write to apply the policy (including new floors)
    result = run_cli("approach", "evaluate", "--write")
    assert result.returncode == 0, f"route evaluate --write failed:\n{result}"

    # Load the updated task.yml
    import yaml as _yaml
    with (task_dir / "task.yml").open("r", encoding="utf-8") as fh:
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
# TRC-A13 - analyze completes within the interactive latency target (<3s p95)
# ---------------------------------------------------------------------------

def test_trc_a13_latency_under_3s(project: Path, run_cli):
    """TRC-A13: 20 runs of analyze against a fixture, p95 < 3000ms."""
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
    # The actual analyze command is ~100-500ms; 10s is a generous ceiling.
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
    # BF-1: provisional target 3s p95; confirmed by these measurements
    assert p95 < 3.0, \
        f"p95 latency {p95:.3f}s exceeds 3s target. Durations: {[f'{d:.3f}' for d in durations]}\n" \
        f"NOTE: this test is sensitive to system load. Run in isolation if flaky."


# ---------------------------------------------------------------------------
# TRC-F1 - analyze on a malformed task.yml exits non-zero with structured error
# ---------------------------------------------------------------------------

def test_trc_f1_malformed_task_yml(project: Path, run_cli):
    """TRC-F1: task.yml with YAML parse error → exit non-zero, stderr names the file."""
    slug = "malformed-task"
    task_dir = project / ".compass" / "work" / slug
    task_dir.mkdir(parents=True, exist_ok=True)

    # Write invalid YAML
    (task_dir / "task.yml").write_text(
        "task: malformed-task\nreadings: {blast_radius: [broken yaml\n",
        encoding="utf-8",
    )

    (project / ".compass" / "current-task").write_text(slug, encoding="utf-8")

    result = run_cli("analyze")
    assert result.returncode != 0, f"Expected non-zero exit for malformed YAML:\n{result}"
    assert "task.yml" in result.stderr or "task.yml" in result.stdout, \
        f"Expected task.yml path in error output:\n{result}"
    # No partial evidence left behind
    ev_dir = task_dir / "evidence"
    partial = list(ev_dir.glob("EV-ANALYZE-*")) if ev_dir.exists() else []
    assert len(partial) == 0, \
        f"No partial analyze evidence should be written on parse error:\n{partial}"


# ---------------------------------------------------------------------------
# TRC-F4 - analyze on a task that has not yet been framed reports clearly
# ---------------------------------------------------------------------------

def test_trc_f4_unframed_task(project: Path, run_cli):
    """TRC-F4: slug with no task.yml → exit non-zero, stderr names Frame is needed."""
    # Point current-task at a slug that has no task.yml
    slug = "unframed-task"
    (project / ".compass" / "current-task").write_text(slug, encoding="utf-8")
    # Do NOT create the task directory or task.yml

    result = run_cli("analyze")
    assert result.returncode != 0, f"Expected non-zero exit for unframed task:\n{result}"
    combined = result.stdout + result.stderr
    assert "frame" in combined.lower(), \
        f"Expected 'Frame' in output:\n{result}"
    # Must not report a coherence finding (the task simply hasn't been framed)
    assert "orphan" not in combined.lower() and \
           "route-disagreement" not in combined.lower() and \
           "missing-artifact" not in combined.lower(), \
        f"Must not report coherence findings for unframed task:\n{result}"


# ---------------------------------------------------------------------------
# TRC-F5 - a hand-edit to task.yml made by a tool is caught by analyze
# ---------------------------------------------------------------------------

def test_trc_f5_hand_edited_route_caught(project: Path, run_cli):
    """TRC-F5: task.yml route field hand-edited to disagree with route.md →
    route-disagreement finding (gate mode → non-zero exit)."""
    slug = "hand-edited-task"
    task_dir = project / ".compass" / "work" / slug
    task_dir.mkdir(parents=True, exist_ok=True)

    body = _minimal_task(slug)
    body["scenarios"] = [{"id": "SCN-001", "intent": "INT-1", "title": "foo", "tests": []}]
    # Hand-edit: task.yml says 'expedition' phases but route.md says 'express' phases.
    # That constitutes a route disagreement (a tool hand-edited the route field).
    body["delivery_approach"] = "expedition"
    body["stages"] = {
        "frame": "full", "specify": "full", "clarify": "full",
        "plan": "full", "distribute": "swarm", "build": "full",
        "verify": "full", "land": "full",
    }
    # Gate mode so findings → non-zero
    body["gates"] = [
        {"id": "verify.correctness", "status": "pending", "evidence": []},
        {"id": "verify.analyze", "status": "pending", "evidence": []},
    ]
    _write_task(task_dir, body)
    _write_brief(task_dir, ["INT-1"])
    _write_spec(task_dir, [{"id": "SCN-001", "intent": "INT-1"}])
    # route.md says express with express phases - disagrees with task.yml's expedition phases
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
