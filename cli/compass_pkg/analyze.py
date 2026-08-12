#!/usr/bin/env python3
# =============================================================================
# compass - the Compass CLI
# =============================================================================
# The deterministic half of Compass. The Needle (an LLM or a human) produces
# the four-dimension *readings* - that is judgement, and judgement is the
# adaptivity. Everything downstream of the readings is mechanical, and this is
# where the mechanism lives:
#
#   compass route evaluate   Apply governance/routing-policy.yml to a task's
#                            readings -> the final route, deterministically.
#                            Same readings + same policy => same route, always.
#   compass check            Run the governance/guardrails.yml checks against a
#                            task's task.yml + evidence/. The checkable backbone
#                            of the Verify gate.
#   compass tdd-red CMD...    Run a test command, assert it FAILS, record
#                            evidence/red.json + the .red marker (honestly -
#                            the marker is only written after a real failure).
#                            --scenario SCN-xxx binds the red to a scenario, so
#                            it proves relevance, not just that something broke.
#   compass tdd-green CMD...  Run a test command, assert it PASSES, record
#                            evidence/green.json, clear the .red marker.
#                            --scenario binds the green the same way.
#   compass policy lint       Structurally validate routing-policy.yml and
#                            guardrails.yml - including that every guardrail's
#                            declared check is actually implemented in the CLI.
#   compass task lint [F]     Structurally validate a task.yml.
#   compass calibration       The Needle's feedback loop - aggregate the
#                            re-frame log across all tasks and report whether
#                            routing is systematically over- or under-sizing.
#   compass ci               The full mechanical gate suite (policy lint +
#                            task lint + check for every task) - for CI.
#
# DEPENDENCY: PyYAML, bundled at cli/vendor/yaml/ and pinned in
# THIRD-PARTY-NOTICES.md. It is resolved by compass_pkg/__init__.py and is
# the only third-party code Compass ships; everything else is the Python 3
# standard library.
#
# GOVERNANCE RESOLUTION: the CLI looks for a project-local `governance/`
# (walking up from the working directory); if there is none, it falls back to
# the framework's shipped `governance/` next to this script. That fallback is
# the "gradient, not threshold" rule in code - the defaults work with zero
# project setup.
# =============================================================================

import argparse
import datetime
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile

# --- dependency check --------------------------------------------------------
# compass_pkg/__init__.py already verified the bundled copy resolves - or
# exited 3 with a clear message naming the absolute path it checked - before
# this module's own code ever runs (DD-2 of zero-friction-install). By the
# time this line runs, `yaml` is already imported and cached, so this is
# never anything but a normal import.
import yaml


# Regex to match a DoD checklist item:
#   - [ ] ...  or  - [x] ...  (allow variable whitespace after the dash)
import re as _re


# --- command: rework-scan ---------------------------------------------------
# Cross-task rework scanner (R4). Reads every task.yml under --root (default:
# .compass/work/) and detects add-then-delete patterns within the configured
# window. Output is Markdown (default) or JSON (--format json). This is a
# SIGNAL, not a gate - exit code is always 0 unless the scan itself errors.
# Patterns are loaded from governance/signals.yml at runtime, never hardcoded.
# Suitable for piping into .compass/flow/rework-<date>.md.
#
# Detection modes:
#   1. Simple add-then-delete: file added by task A, deleted by task B within
#      window_days.
#   2. Public-surface churn: the path matches a public_surface_patterns regex
#      AND the same file is added then deleted.
#   3. Migration pair: a file matching migration_paths (glob) is added in task
#      A, and a semantically paired drop migration is added in task B within
#      window_days.
#
# Architectural invariant: Inv-4 (Flow advises, never gates). This command is
# read-only over the task directory tree; it writes nothing.

import fnmatch
import re as _re
from compass_pkg.check_cmd import cmd_check
from compass_pkg.core import COMPASS_SCHEMA_VERSION, COMPASS_VERSION, CompassError, artifact_path, exit_for_mode, find_compass_dir, load_mode, load_yaml, mode_banner, normalize_spine, now_iso, resolve_task_dir, save_task
from compass_pkg.governance import cmd_policy_lint
from compass_pkg.policy import cmd_task_lint



# --- command: analyze -------------------------------------------------------
# `compass analyze` - cross-artifact coherence check (TRC-A1…A13, F1, F4, F5)
#
# Reads a task's artifacts (brief.md, spec.feature.md, route.md, task.yml,
# positioning.md if present) and emits a structured coherence report.
#
# Finding types (Inv-7 - baked in, not from signals.yml):
#   orphaned-intent  - a scenario in spec/task.yml links to an intent id that
#                      does not appear in brief.md
#   route-disagreement - route.md and task.yml describe different phase weights
#                        for the same phase
#   orphan-claim     - positioning.md lists a claim id that no scenario links to
#   missing-artifact - an artifact required by the route's non-collapsed phase
#                      is absent (route-aware: legitimately omitted artifacts
#                      on collapsed/skipped phases are not flagged)
#
# Mode selection (DD-5 / ADR-007):
#   Gate-clearing mode  - verify.analyze is in task.yml.gates:
#       exits non-zero on any finding; evidence type `coherence-check`;
#       id prefix `EV-ANALYZE-<task>-<ts>`
#   Advisory mode - verify.analyze NOT in gates:
#       exits 0 even on findings; evidence type `command-output`;
#       id prefix `EV-ANALYZE-ADVISORY-<task>-<ts>`
#
# Invariants honoured:
#   Inv-1 / Inv-4 - strictly read-only over task.yml; never writes to
#                   task.yml.readings or task.yml.gates
#   Inv-7         - finding taxonomy is structural, not from signals.yml
#   Inv-8         - no brief.md / spec.feature.md → exits 0 ("no artifacts")
#   OQ-1 boundary - never asserts whether gate evidence exists or passes;
#                   that is compass check's job


# Phases that require brief.md to be present. On collapsed/skipped Specify
# the brief is legitimately absent. Route-aware: only flag missing brief
# when Specify is full-weight.
_SPECIFY_FULL_WEIGHTS = {"full"}

# Phases that would be checked for route-disagreement
_KNOWN_PHASES = {
    "frame", "specify", "clarify", "plan", "distribute",
    "build", "verify", "land",
}

# Human-readable phase name → task.yml key (lowercase map)
_PHASE_NAME_MAP = {
    "frame": "frame",
    "specify": "specify",
    "clarify": "clarify",
    "plan": "plan",
    "distribute": "distribute",
    "build": "build",
    "verify": "verify",
    "land": "land",
}


def _parse_intent_ids_from_brief(brief_path: str) -> set:
    """Extract intent ids from prd.md.

    Scans for lines matching:
      <!-- intent: INT-xxx --> (explicit traceability comment)
      - INT-xxx: ...            (bullet-list intent declaration)
    Returns a set of intent id strings.
    """
    intent_ids = set()
    if not os.path.isfile(brief_path):
        return intent_ids
    with open(brief_path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            # comment form: <!-- intent: INT-xxx -->
            m = _re.match(r'<!--\s*intent:\s*(\S+)\s*-->', line)
            if m:
                intent_ids.add(m.group(1))
                continue
            # bullet form: - INT-xxx: ...  or  * INT-xxx: ...
            m = _re.match(r'^[-*]\s+(INT-\S+?):\s+', line)
            if m:
                intent_ids.add(m.group(1))
    return intent_ids


def _parse_scenario_intents_from_spec(spec_path: str) -> dict:
    """Extract {scenario_id: intent_id} from acceptance-criteria.md traceability comments.

    Looks for lines like:
      <!-- traceability id: SCN-001 · serves: INT-1 -->
    """
    scenario_intents = {}
    if not os.path.isfile(spec_path):
        return scenario_intents
    with open(spec_path, "r", encoding="utf-8") as fh:
        for line in fh:
            m = _re.search(
                r'<!--\s*traceability\s+id:\s*(\S+).*?serves:\s*(\S+)',
                line
            )
            if m:
                scn_id = m.group(1).rstrip(" ·,")
                intent_id = m.group(2).rstrip(" ·,*/-->")
                scenario_intents[scn_id] = intent_id
    return scenario_intents


def _parse_claim_ids_from_positioning(positioning_path: str) -> set:
    """Extract claim ids from positioning.md.

    Scans for:
      <!-- claim: CLM-1 -->
      - CLM-1: ...
    """
    claim_ids = set()
    if not os.path.isfile(positioning_path):
        return claim_ids
    with open(positioning_path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            m = _re.match(r'<!--\s*claim:\s*(\S+)\s*-->', line)
            if m:
                claim_ids.add(m.group(1))
                continue
            m = _re.match(r'^[-*]\s+(CLM-\S+?):\s+', line)
            if m:
                claim_ids.add(m.group(1))
    return claim_ids


def _parse_claimed_scenario_ids_from_spec(spec_path: str) -> set:
    """Extract scenario ids that are referenced as backing claims.

    Looks for:
      <!-- claims: CLM-1 -->
      <!-- backed-by: SCN-001 -->
    Returns set of scenario ids that a claim is backed by.
    """
    # For simplicity, also return the scenario ids found in the spec
    # (the spec's traceability comment already lists the scenario id)
    return set(_parse_scenario_intents_from_spec(spec_path).keys())


def _parse_phase_weights_from_route_md(route_md_path: str) -> dict:
    """Extract {phase_name_lower: weight} from a delivery-approach.md file.

    Looks for a Markdown table with Phase | Weight columns.
    Also handles the per-phase weight section.
    """
    weights = {}
    if not os.path.isfile(route_md_path):
        return weights
    with open(route_md_path, "r", encoding="utf-8") as fh:
        lines = fh.readlines()
    in_phase_table = False
    for line in lines:
        stripped = line.strip()
        # Detect phase table header: | Phase | Weight |
        if _re.match(r'\|\s*Phase\s*\|\s*Weight', stripped, _re.IGNORECASE):
            in_phase_table = True
            continue
        if in_phase_table:
            # separator row
            if _re.match(r'\|[-| ]+\|', stripped):
                continue
            # data row: | Clarify | full |
            m = _re.match(r'\|\s*(\w[\w\s-]*?)\s*\|\s*(\S+)\s*\|', stripped)
            if m:
                phase = m.group(1).strip().lower()
                weight = m.group(2).strip().lower()
                weights[phase] = weight
            elif stripped.startswith("#") or not stripped.startswith("|"):
                in_phase_table = False
    return weights


def _parse_route_from_route_md(route_md_path: str) -> str | None:
    """Extract the reference route name from delivery-approach.md.

    Looks for: **Reference route:** Express  (or similar)
    Returns the route string (lowercase) or None.
    """
    if not os.path.isfile(route_md_path):
        return None
    with open(route_md_path, "r", encoding="utf-8") as fh:
        for line in fh:
            m = _re.search(r'[Rr]eference\s+route[:\s]*[*]*\s*(\w+)', line)
            if m:
                return m.group(1).strip().lower()
    return None


def _analyze_task(task_dir: str, project_root: str | None = None) -> dict:
    """Analyze an issue's artifacts for coherence and return a report dict.

    The report dict has:
      findings: list of {type, subject, detail} dicts
      task_slug: str
      mode: 'gate' | 'advisory'
      has_verify_analyze_gate: bool

    This function is strictly read-only over all issue artifacts (Inv-1 / Inv-4).
    It never writes to task.yml or any other file; the caller (cmd_analyze)
    writes the evidence record.

    Finding types (Inv-7):
      orphaned-intent    - scenario links to an intent not in prd.md
      route-disagreement - delivery-approach.md phase weight differs from task.yml phases
      orphan-claim       - positioning.md claim has no backing scenario
      missing-artifact   - a required artifact is absent (route-aware)
    """
    task_path = os.path.join(task_dir, "task.yml")
    if not os.path.isfile(task_path):
        raise CompassError(
            f"no task.yml in {task_dir} - has triage run? "
            f"compass analyze cannot run before it."
        )
    try:
        task = normalize_spine(load_yaml(task_path))
    except CompassError:
        raise  # re-raise: parse error propagates to cmd_analyze

    task_slug = task.get("task") or os.path.basename(task_dir)
    findings = []

    # Determine mode from gate set (DD-5 / ADR-007)
    gate_ids = [g.get("id") for g in (task.get("gates") or []) if isinstance(g, dict)]
    has_analyze_gate = "verify.analyze" in gate_ids

    # --- No artifacts to analyze (Inv-8) ------------------------------------
    brief_path = artifact_path(task_dir, "prd.md")
    spec_path = artifact_path(task_dir, "acceptance-criteria.md")
    route_md_path = artifact_path(task_dir, "delivery-approach.md")
    positioning_path = os.path.join(task_dir, "positioning.md")

    has_brief = os.path.isfile(brief_path)
    has_spec = os.path.isfile(spec_path)
    has_positioning = os.path.isfile(positioning_path)

    if not has_brief and not has_spec:
        # Bare-repo path: no artifacts to analyze
        return {
            "findings": [],
            "task_slug": task_slug,
            "mode": "gate" if has_analyze_gate else "advisory",
            "has_verify_analyze_gate": has_analyze_gate,
            "no_artifacts": True,
        }

    # --- 1. Route-aware missing-artifact check ------------------------------
    # Only check for brief.md when Specify is expected to run at full weight.
    phases = task.get("stages") or {}
    specify_weight = str(phases.get("specify", "full")).lower()
    if specify_weight in _SPECIFY_FULL_WEIGHTS and not has_brief:
        findings.append({
            "type": "missing-artifact",
            "subject": "prd.md",
            "detail": (
                f"prd.md is absent but the define stage is '{specify_weight}' - "
                f"a full-weight Specify requires a brief."
            ),
        })

    # --- 2. Orphaned-intent check -------------------------------------------
    # Scenarios in task.yml with an intent that is not in brief.md.
    # Only when brief.md exists (no brief → no intents to check against,
    # but we may have already flagged missing-artifact above).
    if has_brief:
        declared_intents = _parse_intent_ids_from_brief(brief_path)
        task_scenarios = [
            s for s in (task.get("scenarios") or []) if isinstance(s, dict)
        ]
        for scn in task_scenarios:
            scn_id = scn.get("id", "?")
            intent_id = scn.get("intent")
            if intent_id and declared_intents and intent_id not in declared_intents:
                findings.append({
                    "type": "orphaned-intent",
                    "subject": scn_id,
                    "detail": (
                        f"scenario '{scn_id}' links to intent '{intent_id}' which "
                        f"does not appear in prd.md (declared intents: "
                        f"{sorted(declared_intents)})"
                    ),
                })
        # Also check spec.feature.md's scenario-intent links
        if has_spec:
            spec_scenario_intents = _parse_scenario_intents_from_spec(spec_path)
            for scn_id, intent_id in spec_scenario_intents.items():
                if intent_id and declared_intents and intent_id not in declared_intents:
                    # Deduplicate: only report if not already caught from task.yml
                    already = any(
                        f["type"] == "orphaned-intent" and f["subject"] == scn_id
                        for f in findings
                    )
                    if not already:
                        findings.append({
                            "type": "orphaned-intent",
                            "subject": scn_id,
                            "detail": (
                                f"acceptance-criteria.md: scenario '{scn_id}' links to "
                                f"intent '{intent_id}' which does not appear in "
                                f"prd.md (declared intents: {sorted(declared_intents)})"
                            ),
                        })

    # --- 3. Route-disagreement check ----------------------------------------
    # Compare route.md per-phase weights against task.yml phases.
    if os.path.isfile(route_md_path):
        route_md_phases = _parse_phase_weights_from_route_md(route_md_path)
        task_phases = {k.lower(): str(v).lower() for k, v in phases.items()}
        for phase in _KNOWN_PHASES:
            md_weight = route_md_phases.get(phase)
            task_weight = task_phases.get(phase)
            if md_weight is not None and task_weight is not None:
                if md_weight != task_weight:
                    findings.append({
                        "type": "route-disagreement",
                        "subject": phase.title(),
                        "detail": (
                            f"delivery-approach.md says '{phase}' is '{md_weight}' but "
                            f"task.yml says '{task_weight}'"
                        ),
                    })

    # --- 4. Orphan-claim check -----------------------------------------------
    # Claims in positioning.md that have no scenario backing them.
    # (OQ-1 boundary: we check whether a claim names a scenario id, not whether
    # the scenario passes - that is compass check / verify.claims's job.)
    if has_positioning:
        claim_ids = _parse_claim_ids_from_positioning(positioning_path)
        # Collect all scenario ids from task.yml and spec
        task_scn_ids = {
            s.get("id") for s in (task.get("scenarios") or [])
            if isinstance(s, dict) and s.get("id")
        }
        spec_scn_ids = set()
        if has_spec:
            spec_scn_ids = set(_parse_scenario_intents_from_spec(spec_path).keys())
        all_scn_ids = task_scn_ids | spec_scn_ids

        # Check task.yml claims as well
        task_claims = {
            c.get("id"): c.get("scenario")
            for c in (task.get("claims") or [])
            if isinstance(c, dict) and c.get("id")
        }

        for claim_id in claim_ids:
            # An orphan claim is one with no backing scenario id
            if claim_id in task_claims:
                # claim is in task.yml - check it has a scenario
                backing = task_claims[claim_id]
                if not backing:
                    findings.append({
                        "type": "orphan-claim",
                        "subject": claim_id,
                        "detail": (
                            f"claim '{claim_id}' is in task.yml claims but has "
                            f"no backing scenario"
                        ),
                    })
            else:
                # Claim is only in positioning.md - it must name a scenario
                # We can't check the link without task.yml.claims, so flag it
                findings.append({
                    "type": "orphan-claim",
                    "subject": claim_id,
                    "detail": (
                        f"claim '{claim_id}' in positioning.md has no backing "
                        f"scenario in task.yml claims"
                    ),
                })

    return {
        "findings": findings,
        "task_slug": task_slug,
        "mode": "gate" if has_analyze_gate else "advisory",
        "has_verify_analyze_gate": has_analyze_gate,
        "no_artifacts": False,
    }


def _write_analyze_evidence(task_dir: str, task_slug: str, report: dict,
                             is_gate_mode: bool) -> str:
    """Write the analyze evidence file and return the file path (relative to task_dir).

    Gate-clearing: type=coherence-check, prefix EV-ANALYZE-<task>-<ts>
    Advisory:      type=command-output,  prefix EV-ANALYZE-ADVISORY-<task>-<ts>

    The file is JSON; the task.yml evidence registry is NOT written here
    (Inv-1 / Inv-4 - analyze is strictly read-only over task.yml).
    cmd_analyze calls this and then upserts into the registry separately only
    in gate-clearing mode (to let compass check clear verify.analyze).
    """
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if is_gate_mode:
        ev_id = f"EV-ANALYZE-{task_slug}-{ts}"
        ev_type = "coherence-check"
    else:
        ev_id = f"EV-ANALYZE-ADVISORY-{task_slug}-{ts}"
        ev_type = "command-output"

    payload = {
        "id": ev_id,
        "type": ev_type,
        "task": task_slug,
        "timestamp": now_iso(),
        "mode": "gate" if is_gate_mode else "advisory",
        "finding_count": len(report.get("findings", [])),
        "findings": report.get("findings", []),
    }

    ev_dir = os.path.join(task_dir, "evidence")
    os.makedirs(ev_dir, exist_ok=True)
    filename = f"{ev_id}.json"
    full_path = os.path.join(ev_dir, filename)
    with open(full_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)

    return f"evidence/{filename}", ev_id, ev_type


def _upsert_analyze_evidence_registry(task_dir: str, ev_id: str,
                                       ev_type: str, rel_path: str) -> None:
    """Upsert the analyze evidence entry into task.yml's evidence registry.

    Only called in gate-clearing mode so compass check can locate the
    coherence-check evidence when clearing verify.analyze.

    This is the ONE write to task.yml that analyze is permitted: adding an
    entry to the top-level `evidence:` list. It does NOT write to
    task.yml.readings or task.yml.gates (Inv-1 / Inv-4).
    """
    task_path = os.path.join(task_dir, "task.yml")
    if not os.path.isfile(task_path):
        return
    try:
        task = normalize_spine(load_yaml(task_path))
    except CompassError:
        return
    if not isinstance(task, dict):
        return
    reg = task.get("evidence") or []
    if not isinstance(reg, list):
        return
    # Remove any previous coherence-check entry (replace with fresh run)
    reg = [e for e in reg if not (isinstance(e, dict) and
                                   e.get("type") == "coherence-check")]
    reg.append({"id": ev_id, "type": ev_type, "path": rel_path})
    task["evidence"] = reg
    save_task(task, task_path)


def cmd_analyze(args):
    """compass analyze - cross-artifact coherence check.

    Strictly read-only over task.yml (Inv-1 / Inv-4). Writes one evidence
    file (coherence-check or command-output type) to evidence/.

    Exit codes:
      0 - zero coherence findings (or advisory mode regardless of findings,
          or Inv-8 bare-repo path)
      1 - one or more coherence findings AND verify.analyze gate is present
      2 - input error (malformed task.yml, issue not framed, etc.)
    """
    task_dir = resolve_task_dir(getattr(args, "task", None))
    project_root = os.path.dirname(os.path.dirname(task_dir))  # .compass/work/<slug>/../../

    # TRC-F1: malformed task.yml → exit non-zero, stderr names the file and error
    try:
        report = _analyze_task(task_dir, project_root)
    except CompassError as exc:
        # Re-raise so main() prints it to stderr with exit 2
        raise

    task_slug = report["task_slug"]
    is_gate_mode = report["has_verify_analyze_gate"]
    findings = report.get("findings", [])
    no_artifacts = report.get("no_artifacts", False)

    # Inv-8: no artifacts → exit 0 with informational message
    if no_artifacts:
        print(f"compass analyze: no artifacts to analyze for issue '{task_slug}'.")
        print("  (no prd.md and no acceptance-criteria.md found - bare-repo path)")
        return 0

    # Print the report
    mode_str = "gate-clearing" if is_gate_mode else "advisory"
    print(f"compass analyze - issue '{task_slug}' (mode: {mode_str})")
    if is_gate_mode:
        print("  verify.analyze gate is in the route's gate set.")
    else:
        print("  verify.analyze gate is NOT in the route's gate set - advisory mode.")

    if not findings:
        print(f"\n  findings: 0 - all coherence checks clean.")
    else:
        print(f"\n  findings: {len(findings)}")
        for i, f in enumerate(findings, 1):
            print(f"    [{i}] type: {f['type']}")
            print(f"        subject: {f['subject']}")
            print(f"        detail: {f['detail']}")

    # Write evidence (always, regardless of findings count)
    rel_path, ev_id, ev_type = _write_analyze_evidence(
        task_dir, task_slug, report, is_gate_mode
    )
    print(f"\n  evidence: {rel_path} (type: {ev_type}, id: {ev_id})")

    # In gate-clearing mode: upsert into task.yml evidence registry
    if is_gate_mode:
        _upsert_analyze_evidence_registry(task_dir, ev_id, ev_type, rel_path)
        print("  registry: task.yml `evidence:` updated with the coherence-check entry")

    if is_gate_mode:
        # Advisory: the advisory evidence file has been written
        # (even though we called the gate path for the registry update)
        pass
    else:
        print(f"\n  [advisory] findings above are informational - Land is not blocked.")

    if findings and is_gate_mode:
        print(f"\ncompass analyze: FAIL - {len(findings)} coherence finding(s).")
        return 1
    if findings:
        # Advisory mode still found something. The old summary hardcoded
        # "0 finding(s), coherence checks clean" here, so the command listed
        # its findings and then denied having any - and the evidence JSON,
        # which recorded the real count, disagreed with the line a human reads.
        print(f"\ncompass analyze: PASS (advisory) - {len(findings)} coherence "
              f"finding(s) reported above; they do not block Land on this route.")
        return 0
    print("\ncompass analyze: PASS - 0 finding(s), coherence checks clean.")
    return 0


# --- command: ci ------------------------------------------------------------
# The full mechanical gate suite, for CI / pre-merge. It is a convenience: it
# just runs the checks that already exist - `policy lint`, then `task lint` and
# `check` for every task under .compass/work/ - and aggregates the exit codes.
# CI integration is genuinely this small: run `compass ci`, honour the exit
# code. See ci/README.md.

# Lifecycle states meaning "not in flight". An issue in one of these has no
# acceptance criteria yet, by design, so the gate checks have nothing to read.
_NOT_IN_FLIGHT = ("queued", "parked", "abandoned")


def _issue_status(slug):
    """The issue's lifecycle status, or '' if it cannot be read.

    An unreadable spine is not treated as not-in-flight: it falls through to
    the checks, which report the problem properly rather than skipping it.
    """
    try:
        spine = load_yaml(os.path.join(resolve_task_dir(slug), "task.yml"))
    except Exception:
        return ""
    if not isinstance(spine, dict):
        return ""
    return (spine.get("status") or "").strip()


def cmd_ci(args):
    import types
    mode = load_mode()
    print(f"compass ci - the full mechanical gate suite "
          f"(compass {COMPASS_VERSION}, schema {COMPASS_SCHEMA_VERSION})")
    print(f"{mode_banner(mode)}\n")
    failures = 0
    checked = 0
    skipped = 0

    print("[1] governance policy")
    if cmd_policy_lint(types.SimpleNamespace()):
        failures += 1

    slugs = []
    try:
        work = os.path.join(find_compass_dir(), "work")
        if os.path.isdir(work):
            slugs = sorted(d for d in os.listdir(work)
                           if os.path.isfile(os.path.join(work, d, "task.yml")))
    except CompassError:
        pass

    if not slugs:
        print("\n  no issues under .compass/work/ - governance policy only.")
    for slug in slugs:
        print(f"\n[issue] {slug}")
        # The lint runs for every issue, whatever its stage. It validates the
        # spine's own structure - schema version, required keys, vocabulary -
        # and a malformed spine is malformed whether or not the work has
        # started. Skipping it once let a spine the linter rejects outright
        # sit in a repository while the sweep reported everything clean.
        if cmd_task_lint(types.SimpleNamespace(task=slug, file=None)):
            failures += 1

        # The gate checks are different. An issue that has not started has no
        # acceptance criteria and no evidence, correctly so - the framework
        # asks for work to be triaged early, and failing the sweep for
        # complying teaches people to stop. Skip those, name the issue, and
        # say why: an issue that vanished from the output would be worse than
        # one that failed, because nobody would know it was there.
        status = _issue_status(slug)
        if status in _NOT_IN_FLIGHT:
            print(f"  gate checks skipped - status is '{status}', so the "
                  f"acceptance criteria and evidence a check looks for do "
                  f"not exist yet. The spine itself was still linted.")
            skipped += 1
            continue
        print()
        # cmd_check honours the mode itself - but to know whether it had real
        # failures (regardless of mode's effect on its exit), check ran already
        # and we capture exit. For ci aggregation in advisory mode we still
        # want to honour mode at the top level, so call cmd_check and let it
        # return; failures captured here mean "this group had problems."
        checked += 1
        if cmd_check(types.SimpleNamespace(task=slug)):
            failures += 1

    print("\n" + "=" * 60)
    if failures:
        print(f"compass ci: FAIL - {failures} check group(s) failed.")
    else:
        # Say what was actually done rather than making a blanket claim. The
        # summary is the line a CI reader reads; when it said "every issue"
        # while the run had skipped some, the skip lines further up were the
        # part nobody scrolled back for.
        counted = f"{checked} issue(s) fully checked"
        if skipped:
            counted += f", {skipped} lint-only (not in flight)"
        print(f"compass ci: PASS - governance valid; every spine lints clean; "
              f"{counted}.")
    return exit_for_mode(failures, mode)
