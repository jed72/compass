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
#                            task's manifest.yml + evidence/. The checkable backbone
#                            of the Verify gate.
#   compass tdd-red CMD...    Run a test command, assert it FAILS, record the
#                            red + the .red marker (honestly - the marker is
#                            only written after a real failure).
#                            --scenario TRC-xxx binds the red to a scenario, so
#                            it proves relevance, not just that something broke.
#   compass tdd-green CMD...  Run a test command, assert it PASSES, record the
#                            green, clear the .red marker.
#                            --scenario binds the green the same way.
#                            THE BINDING DECIDES THE FILENAME: a bound run
#                            writes evidence/green-<scenario>.json, an unbound
#                            one writes evidence/green.json, and only that file
#                            is written - so recording one scenario cannot
#                            destroy a record another gate is citing.
#   compass policy lint       Structurally validate routing-policy.yml and
#                            guardrails.yml - including that every guardrail's
#                            declared check is actually implemented in the CLI.
#   compass task lint [F]     Structurally validate a manifest.yml.
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
# Cross-task rework scanner (R4). Reads every manifest.yml under --root (default:
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
from compass_pkg.core import COMPASS_SCHEMA_VERSION, COMPASS_VERSION, CompassError, artifact_path, exit_for_mode, find_compass_dir, load_mode, load_yaml, manifest_path, mode_banner, normalize_spine, now_iso, resolve_issue_dir, save_manifest
from compass_pkg.governance import cmd_policy_lint
from compass_pkg.policy import cmd_task_lint



# --- command: analyze -------------------------------------------------------
# `compass analyze` - cross-artifact consistency check (TRC-A1…A13, F1, F4, F5)
#
# Reads a task's artifacts (brief.md, spec.feature.md, route.md, manifest.yml,
# positioning.md if present) and emits a structured coherence report.
#
# Finding types (Inv-7 - baked in, not from signals.yml):
#   orphaned-intent  - a scenario in spec/manifest.yml links to an intent id that
#                      does not appear in brief.md
#   route-disagreement - route.md and manifest.yml describe different phase weights
#                        for the same phase
#   orphan-claim     - positioning.md lists a claim id that no scenario links to
#   missing-artifact - an artifact required by the route's non-collapsed phase
#                      is absent (route-aware: legitimately omitted artifacts
#                      on collapsed/skipped phases are not flagged)
#
# Mode selection (DD-5 / ADR-007):
#   Gate-clearing mode  - verify.analyze is in manifest.yml.gates:
#       exits non-zero on any finding; evidence type `consistency-check`;
#       id prefix `EV-ANALYZE-<task>-<ts>`
#   Advisory mode - verify.analyze NOT in gates:
#       exits 0 even on findings; evidence type `command-output`;
#       id prefix `EV-ANALYZE-ADVISORY-<task>-<ts>`
#
# Invariants honoured:
#   Inv-1 / Inv-4 - strictly read-only over manifest.yml; never writes to
#                   manifest.yml.readings or manifest.yml.gates
#   Inv-7         - finding taxonomy is structural, not from signals.yml
#   Inv-8         - no brief.md / spec.feature.md → exits 0 ("no artifacts")
#   OQ-1 boundary - never asserts whether gate evidence exists or passes;
#                   that is compass check's job


# Phases that require brief.md to be present. On collapsed/skipped Specify
# the brief is legitimately absent. Route-aware: only flag missing brief
# when Specify is full-weight.
_SPECIFY_FULL_WEIGHTS = {"full"}

# The stages this checks for approach-disagreement. CURRENT keys:
# `normalize_spine` maps a retired key forward on load, so a set written in the
# retired spelling matches nothing and every check below falls to its default.
_KNOWN_PHASES = {
    "assess", "define", "refine", "plan", "breakdown",
    "implement", "verify", "ship",
}

# Human-readable phase name → manifest.yml key (lowercase map)
# The names a human writes in delivery-approach.md, and the manifest key each one
# means. Both the retired and the current spelling map to the CURRENT key,
# because a prose record written months ago still says the retired word while
# the manifest it describes has been normalised forward.
_PHASE_NAME_MAP = {
    "assess": "assess", "triage": "assess", "frame": "assess",
    "define": "define", "specify": "define",
    "refine": "refine", "clarify": "refine",
    "plan": "plan", "design": "plan",
    "breakdown": "breakdown", "distribute": "breakdown",
    "implement": "implement", "build": "implement",
    "verify": "verify",
    "ship": "ship", "land": "ship",
    # The PROSE names, which are what the shipped template actually writes in
    # its stage table and therefore what every real record on disk says. Only
    # the one-word keys above were here, so five of the eight rows in a
    # template-shaped record matched nothing and the consistency check compared
    # three stages while reporting on all of them.
    "define acceptance criteria": "define",
    "acceptance criteria": "define",
    "requirements review": "refine",
    "technical design": "plan",
    "break down the work": "breakdown",
    "test & review": "verify",
    "test and review": "verify",
}


def _parse_intent_ids_from_brief(brief_path: str) -> set:
    """Extract intent ids from intent.md.

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
      <!-- traceability id: TRC-A1 · serves: INT-1 -->
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
      <!-- backed-by: TRC-A1 -->
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
        # BOTH header words. The template writes `| Stage | Weight | Notes |`
        # and has since the v2 rename of `phases:` to `stages:`; this matched
        # only `Phase`, so it found no table at all in a record written from
        # the shipped template - and an empty weight map reads downstream as
        # "nothing disagreed" rather than "nothing was read".
        if _re.match(r'\|\s*(?:Phase|Stage)\s*\|\s*Weight', stripped,
                     _re.IGNORECASE):
            in_phase_table = True
            continue
        if in_phase_table:
            # separator row
            if _re.match(r'\|[-| ]+\|', stripped):
                continue
            # Data row: `| Requirements review | collapsed | ... |`. The name
            # cell takes anything but a pipe, because the real names are
            # phrases and one of them ("Test & review") carries an ampersand.
            # The weight cell is read whole and then cut at the first comma or
            # space, because records write "full, subtasks unbounded by policy"
            # and the weight is the first word of it.
            m = _re.match(r'\|\s*([A-Za-z][^|]*?)\s*\|\s*([^|]+?)\s*\|',
                          stripped)
            if m:
                phase = m.group(1).strip().lower()
                weight = _re.split(r'[,\s]', m.group(2).strip().lower(), 1)[0]
                # Through the name map, so a prose record written months ago
                # meets the manifest it describes. Without this the parser returns
                # `distribute` while the normalised manifest holds `breakdown`,
                # the comparison finds no key in common, and every
                # disagreement is silently skipped - the check reporting clean
                # because the two halves stopped speaking the same language.
                weights[_PHASE_NAME_MAP.get(phase, phase)] = weight
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
    It never writes to manifest.yml or any other file; the caller (cmd_analyze)
    writes the evidence record.

    Finding types (Inv-7):
      orphaned-intent    - scenario links to an intent not in intent.md
      route-disagreement - delivery-approach.md phase weight differs from manifest.yml phases
      orphan-claim       - positioning.md claim has no backing scenario
      missing-artifact   - a required artifact is absent (route-aware)
    """
    task_path = manifest_path(task_dir)
    if not os.path.isfile(task_path):
        raise CompassError(
            f"no manifest.yml in {task_dir} - has triage run? "
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
    brief_path = artifact_path(task_dir, "intent.md")
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
    # NO DEFAULT OF "full". This read `phases.get("specify", "full")`, and when
    # the key was renamed to `define` the lookup missed, fell to the default,
    # and reported every hotfix as owing a brief - a defaulted lookup turning a
    # rename into a false finding rather than a crash.
    specify_weight = str(phases.get("define", phases.get("specify", ""))).lower()
    if specify_weight in _SPECIFY_FULL_WEIGHTS and not has_brief:
        findings.append({
            "type": "missing-artifact",
            "subject": "intent.md",
            "detail": (
                f"intent.md is absent but the define stage is '{specify_weight}' - "
                f"a full-weight define stage requires a brief."
            ),
        })

    # --- 2. Orphaned-intent check -------------------------------------------
    # Scenarios in manifest.yml with an intent that is not in brief.md.
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
                        f"does not appear in intent.md (declared intents: "
                        f"{sorted(declared_intents)})"
                    ),
                })
        # Also check spec.feature.md's scenario-intent links
        if has_spec:
            spec_scenario_intents = _parse_scenario_intents_from_spec(spec_path)
            for scn_id, intent_id in spec_scenario_intents.items():
                if intent_id and declared_intents and intent_id not in declared_intents:
                    # Deduplicate: only report if not already caught from manifest.yml
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
                                f"intent.md (declared intents: {sorted(declared_intents)})"
                            ),
                        })

    # --- 3. Route-disagreement check ----------------------------------------
    # Compare route.md per-phase weights against manifest.yml phases.
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
                            f"manifest.yml says '{task_weight}'"
                        ),
                    })

    # --- 4. Orphan-claim check -----------------------------------------------
    # Claims in positioning.md that have no scenario backing them.
    # (OQ-1 boundary: we check whether a claim names a scenario id, not whether
    # the scenario passes - that is compass check / verify.claims's job.)
    if has_positioning:
        claim_ids = _parse_claim_ids_from_positioning(positioning_path)
        # Collect all scenario ids from manifest.yml and spec
        task_scn_ids = {
            s.get("id") for s in (task.get("scenarios") or [])
            if isinstance(s, dict) and s.get("id")
        }
        spec_scn_ids = set()
        if has_spec:
            spec_scn_ids = set(_parse_scenario_intents_from_spec(spec_path).keys())
        all_scn_ids = task_scn_ids | spec_scn_ids

        # Check manifest.yml claims as well
        task_claims = {
            c.get("id"): c.get("scenario")
            for c in (task.get("claims") or [])
            if isinstance(c, dict) and c.get("id")
        }

        for claim_id in claim_ids:
            # An orphan claim is one with no backing scenario id
            if claim_id in task_claims:
                # claim is in manifest.yml - check it has a scenario
                backing = task_claims[claim_id]
                if not backing:
                    findings.append({
                        "type": "orphan-claim",
                        "subject": claim_id,
                        "detail": (
                            f"claim '{claim_id}' is in manifest.yml claims but has "
                            f"no backing scenario"
                        ),
                    })
            else:
                # Claim is only in positioning.md - it must name a scenario
                # We can't check the link without manifest.yml.claims, so flag it
                findings.append({
                    "type": "orphan-claim",
                    "subject": claim_id,
                    "detail": (
                        f"claim '{claim_id}' in positioning.md has no backing "
                        f"scenario in manifest.yml claims"
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

    Gate-clearing: type=consistency-check, prefix EV-ANALYZE-<task>-<ts>
    Advisory:      type=command-output,  prefix EV-ANALYZE-ADVISORY-<task>-<ts>

    The file is JSON; the manifest.yml evidence registry is NOT written here
    (Inv-1 / Inv-4 - analyze is strictly read-only over manifest.yml).
    cmd_analyze calls this and then upserts into the registry separately only
    in gate-clearing mode (to let compass check clear verify.analyze).
    """
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if is_gate_mode:
        ev_id = f"EV-ANALYZE-{task_slug}-{ts}"
        ev_type = "consistency-check"
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
    """Upsert the analyze evidence entry into manifest.yml's evidence registry.

    Only called in gate-clearing mode so compass check can locate the
    consistency-check evidence when clearing verify.analyze.

    This is the ONE write to manifest.yml that analyze is permitted: adding an
    entry to the top-level `evidence:` list. It does NOT write to
    manifest.yml.readings or manifest.yml.gates (Inv-1 / Inv-4).
    """
    task_path = manifest_path(task_dir)
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
    # Remove any previous consistency-check entry (replace with fresh run)
    reg = [e for e in reg if not (isinstance(e, dict) and
                                   e.get("type") == "consistency-check")]
    reg.append({"id": ev_id, "type": ev_type, "path": rel_path})
    task["evidence"] = reg
    save_manifest(task, task_path)


def cmd_analyze(args):
    """compass analyze - cross-artifact consistency check.

    Strictly read-only over manifest.yml (Inv-1 / Inv-4). Writes one evidence
    file (consistency-check or command-output type) to evidence/.

    Exit codes:
      0 - zero coherence findings (or advisory mode regardless of findings,
          or Inv-8 bare-repo path)
      1 - one or more coherence findings AND verify.analyze gate is present
      2 - input error (malformed manifest.yml, issue not framed, etc.)
    """
    task_dir = resolve_issue_dir(getattr(args, "task", None))
    project_root = os.path.dirname(os.path.dirname(task_dir))  # .compass/work/<slug>/../../

    # TRC-F1: malformed manifest.yml → exit non-zero, stderr names the file and error
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
        print("  (no intent.md and no acceptance-criteria.md found - bare-repo path)")
        return 0

    # A REPORT: every finding is listed, and the summary says how many there
    # are and whether they block, which is what a reader is here to learn.
    from compass_pkg.terminal import Report

    mode_str = "gate-clearing" if is_gate_mode else "advisory"
    rel_path, ev_id, ev_type = _write_analyze_evidence(
        task_dir, task_slug, report, is_gate_mode
    )
    if is_gate_mode:
        _upsert_analyze_evidence_registry(task_dir, ev_id, ev_type, rel_path)

    blocks = bool(findings) and is_gate_mode
    # Not "PASS - 1 finding(s)". The verdict word is the one that gets read,
    # and "PASS" with a count after it reads as a clean result. A run that
    # found something says so; only a run that found nothing says PASS.
    if blocks:
        verdict = "FAIL - %d coherence finding(s), and they block shipping" % len(findings)
    elif findings:
        verdict = ("%d coherence finding(s) - advisory on this approach, so "
                   "they do not block shipping" % len(findings))
    else:
        verdict = "PASS - no coherence findings"
    rep = Report(args, title="compass analyze")
    rep.summary(
        "compass analyze - issue '%s' (%s): %s." % (task_slug, mode_str, verdict),
        ("The verify.analyze gate is in this approach's gate set."
         if is_gate_mode else
         "The verify.analyze gate is NOT in this approach's gate set, so these "
         "findings do not block shipping."),
        # Path only. The type and the id are in --json; what a reader needs
        # from a summary line is the file they can open.
        "Evidence: %s" % rel_path)
    rep.section("findings", list(findings),
                lambda f: "%-20s %-28s %s" % (f["type"], f["subject"],
                                              f["detail"]))
    rep.data(issue=task_slug, gate_mode=is_gate_mode, blocks=blocks,
             finding_count=len(findings), evidence={"path": rel_path,
                                                    "id": ev_id, "type": ev_type},
             registry_updated=bool(is_gate_mode))
    rep.emit()
    return 1 if blocks else 0


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

    An unreadable manifest is not treated as not-in-flight: it falls through to
    the checks, which report the problem properly rather than skipping it.
    """
    try:
        manifest = load_yaml(os.path.join(resolve_issue_dir(slug), "manifest.yml"))
    except Exception:
        return ""
    if not isinstance(manifest, dict):
        return ""
    return (manifest.get("status") or "").strip()


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
                           if os.path.isfile(manifest_path(os.path.join(work, d))))
    except CompassError:
        pass

    if not slugs:
        print("\n  no issues under .compass/work/ - governance policy only.")
    for slug in slugs:
        print(f"\n[issue] {slug}")
        # The lint runs for every issue, whatever its stage. It validates the
        # manifest's own structure - schema version, required keys, vocabulary -
        # and a malformed manifest is malformed whether or not the work has
        # started. Skipping it once let a manifest the linter rejects outright
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
                  f"not exist yet. The manifest itself was still linted.")
            skipped += 1
            continue
        print()
        # cmd_check honours the mode itself - but to know whether it had real
        # failures (regardless of mode's effect on its exit), check ran already
        # and we capture exit. For ci aggregation in advisory mode we still
        # want to honour mode at the top level, so call cmd_check and let it
        # return; failures captured here mean "this group had problems."
        checked += 1
        # The caller's mode is FORWARDED. A bare namespace resolved to the
        # default view, so CI logs got each issue's four-line summary ending
        # "run with --verbose" - and `compass ci --verbose` printed the same
        # summary, because the flag never reached the check. The one place a
        # reader cannot re-run interactively was the one place that advice was
        # dead.
        if cmd_check(types.SimpleNamespace(
                task=slug, _mode=getattr(args, "_mode", None),
                evidence_out=getattr(args, "evidence_out", None))):
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
        print(f"compass ci: PASS - governance valid; every manifest lints clean; "
              f"{counted}.")
    return exit_for_mode(failures, mode)
