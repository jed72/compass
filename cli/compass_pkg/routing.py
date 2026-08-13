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
from compass_pkg.core import ASSESSMENT_KEY_MAP, CompassError, canonical_shape, display_shape, find_governance, load_task, load_yaml, reading_matches, resolve_task_dir, save_task, shape_stages
from compass_pkg.governance import governance_drift
from compass_pkg.task_spine import _annotate_gate_accepts



def evaluate_route(readings, policy):
    """Pure function: readings + policy -> the final route and everything that
    shaped it. This is the deterministic heart of Compass."""
    _vk = {"blast_radius": "risk", "terrain": "familiarity",
           "magnitude": "size", "intent": "goal",
           "touches_common": "labels_common"}
    vocab = {_vk.get(k, k): v
             for k, v in (policy.get("assessment_vocabulary")
                          or policy.get("reading_vocabulary") or {}).items()}
    shapes = policy.get("route_shapes", {})
    strategies = policy.get("routing_strategies", {})
    guardrails = policy.get("routing_guardrails", {})

    # --- validate the readings: a misclassification fails loudly -------------
    errors = []
    for dim in ("risk", "familiarity", "size"):
        if dim not in readings:
            errors.append(f"missing required reading: {dim}")
        elif dim in vocab and readings[dim] not in vocab[dim]:
            errors.append(
                f"reading {dim}={readings[dim]!r} is not in the vocabulary "
                f"{vocab[dim]}"
            )
    for dim in ("goal", "urgency", "role"):
        if dim in readings and dim in vocab and readings[dim] not in vocab[dim]:
            errors.append(
                f"reading {dim}={readings[dim]!r} is not in the vocabulary "
                f"{vocab[dim]}"
            )
    if errors:
        raise CompassError("invalid assessment:\n  - " + "\n  - ".join(errors))

    # --- 1. compose the candidate (routing strategies bias this) -------------
    candidate = strategies.get("default_route", "standard")
    candidate_via = "default_route (no shape matched)"
    for shape in strategies.get("default_shapes", []):
        if reading_matches(shape.get("when"), readings):
            candidate = shape["lean_toward"]
            candidate_via = f"{shape.get('id', '?')} ({shape.get('rationale', '')})"
            break

    final = candidate
    fired = []
    never_skip, required_phases, required_skills = set(), set(), set()
    required_artifacts, blocked_phases, role_gates = [], [], []
    max_worktrees, forbidden = None, set()

    def weight(route):
        return shapes.get(route, {}).get("weight", 0)

    # --- 2. floors raise the route / force phases (routing guardrails) -------
    floor_gates = []  # gates added by floors via add_gate (DD-1 / ADR-007)
    for fl in guardrails.get("floors", []):
        if not reading_matches(fl.get("when"), readings):
            continue
        changed = []
        forced = fl.get("force_minimum_route")
        if forced and weight(forced) > weight(final):
            changed.append(f"route raised {final} -> {forced}")
            final = forced
        if fl.get("require_phase"):
            required_phases.add(fl["require_phase"])
            changed.append(f"phase '{fl['require_phase']}' forced full-weight")
        if fl.get("require_skill"):
            required_skills.add(fl["require_skill"])
            changed.append(f"skill '{fl['require_skill']}' required")
        if fl.get("never_skip"):
            never_skip.update(fl["never_skip"])
            changed.append(f"never-skip: {', '.join(fl['never_skip'])}")
        if fl.get("add_gate"):
            floor_gates.append(fl["add_gate"])
            changed.append(f"gate '{fl['add_gate']}' added to the route's set")
        if changed:
            # The kind follows what the entry actually did, not which block it
            # sits in. An entry that only attaches a gate raises no minimum, so
            # calling it a floor is the same conflation the RP-REQUIRE ids were
            # introduced to end - and it would print "[RP-REQUIRE-003] floor:"
            # on screen, which reads as a contradiction.
            raises_minimum = any(
                k in fl for k in ("force_minimum_route", "require_phase",
                                  "require_skill", "never_skip"))
            fired.append({"id": fl.get("id", "?"),
                          "kind": "floor" if raises_minimum else "requirement",
                          "rationale": fl.get("rationale", ""), "changed": changed})

    # --- 2b. routing conflict: exploration must not silently become delivery -
    # If the candidate was a Spike and a routing floor would force it onto a
    # delivery route, that is NOT "Spike raised to Expedition" - it is "this is
    # not a Spike." A Spike ships nothing and must not touch production-critical
    # surface (approaches/spike.md). Auto-promoting it would quietly change the
    # *meaning* of the work from "explore" to "deliver." The honest answer is a
    # re-frame, so the evaluator stops and says so.
    if candidate == "spike" and final != "spike":
        floor_ids = [f["id"] for f in fired if f["kind"] == "floor"]
        raise CompassError(
            "routing conflict - exploration cannot silently become delivery.\n"
            f"  Intent is 'exploration' (a Spike candidate), but routing "
            f"guardrail(s) {floor_ids} would force at least '{final}'.\n"
            f"  A Spike ships nothing and must not touch production-critical "
            f"surface - that is its whole safety model (see the spike "
            f"reference doc).\n"
            f"  Re-frame: either scope a narrower discovery issue that does not "
            f"touch the risky surface, or set intent=delivery and accept the "
            f"'{final}' route deliberately. The point is that this is a choice "
            f"a human makes, not one the router makes silently."
        )

    # --- 3. caps limit scale-up ---------------------------------------------
    for cap in guardrails.get("caps", []):
        if not reading_matches(cap.get("when"), readings):
            continue
        changed = []
        if "max_worktrees" in cap:
            max_worktrees = cap["max_worktrees"]
            changed.append(f"max_worktrees capped at {cap['max_worktrees']}")
        if cap.get("forbid_route"):
            forbidden.add(cap["forbid_route"])
            changed.append(f"route '{cap['forbid_route']}' forbidden")
        if changed:
            fired.append({"id": cap.get("id", "?"), "kind": "cap",
                          "rationale": cap.get("rationale", ""), "changed": changed})

    # --- 4. role rules add enforced artifacts / blocks ----------------------
    for rr in guardrails.get("role_rules", []):
        if not reading_matches(rr.get("when"), readings):
            continue
        changed = []
        if rr.get("require_artifact"):
            required_artifacts.append(rr["require_artifact"])
            changed.append(f"artifact '{rr['require_artifact']}' required")
        if rr.get("block_phase"):
            blocked_phases.append({"phase": rr["block_phase"],
                                   "until": rr.get("until", "")})
            changed.append(f"phase '{rr['block_phase']}' blocked until: "
                           f"{rr.get('until', '')}")
        if rr.get("gate"):
            role_gates.append(rr["gate"])
            changed.append(f"gate '{rr['gate']}' added to the route's set")
        if changed:
            fired.append({"id": rr.get("id", "?"), "kind": "role_rule",
                          "rationale": rr.get("rationale", ""), "changed": changed})

    if final in forbidden:
        raise CompassError(
            f"routing conflict: the composed approach '{final}' is forbidden by "
            f"a cap for this assessment. Re-assess - the assessment and the "
            f"policy disagree, and that needs a human."
        )

    # --- 5. assemble the final shape ----------------------------------------
    shape = shapes.get(final)
    if not shape:
        raise CompassError(f"route '{final}' has no entry in route_shapes")
    phases = shape_stages(shape)
    for p in (never_skip | required_phases):
        if phases.get(p) in ("collapsed", "skipped", "light"):
            phases[p] = "full"
    gates = list(shape.get("gates", []))
    # Immovable gates and role-added gates apply to DELIVERY routes only. Spike
    # ships nothing - it carries only its own Conclude gate, by design. (A
    # spike that needs a delivery gate is not a spike; it graduates.)
    if final != "spike":
        for ig in guardrails.get("immovable_gates", []):
            if ig.get("gate") and ig["gate"] not in gates:
                gates.append(ig["gate"])
        for rg_gate in role_gates:  # gates added by a role rule (e.g. verify.claims)
            if rg_gate not in gates:
                gates.append(rg_gate)
        for fl_gate in floor_gates:  # gates added by a floor's add_gate (ADR-007)
            if fl_gate not in gates:
                gates.append(fl_gate)
    topology = shape.get("topology", "solo")
    if max_worktrees == 1 and topology in ("swarm", "solo-or-pair"):
        topology = "solo (capped to 1 worktree)"

    # --- soft advisory strategies (R10) -------------------------------------
    # These BIAS/ASSESS only - they never alter the route, gates, weight, or
    # topology. Surfaced for the Needle and the reviewer (e.g. regression-
    # baseline on shared/critical surface). A strategy, not a guardrail.
    applicable_strategies = []
    for adv in strategies.get("advisory_strategies", []):
        if reading_matches(adv.get("when"), readings):
            applicable_strategies.append({
                "id": adv.get("id", "?"),
                "strategy": adv.get("strategy", ""),
                "rationale": adv.get("rationale", ""),
            })

    return {
        "candidate_route": canonical_shape(candidate),
        "candidate_via": candidate_via,
        "delivery_approach": canonical_shape(final),
        "policy_rules_fired": fired,
        "stages": phases,
        "gates": gates,
        "topology": topology,
        "required_artifacts": required_artifacts,
        "required_skills": sorted(required_skills),
        "blocked_phases": blocked_phases,
        "max_worktrees": max_worktrees,
        "applicable_strategies": applicable_strategies,
    }


# --- command: route evaluate -------------------------------------------------

def cmd_route_evaluate(args):
    gov = find_governance()
    policy = load_yaml(os.path.join(gov, "routing-policy.yml"))

    task = None
    task_path = None
    if args.reading:
        readings = {}
        for pair in args.reading:
            if "=" not in pair:
                raise CompassError(f"--assessment expects key=value, got: {pair}")
            k, v = pair.split("=", 1)
            k = ASSESSMENT_KEY_MAP.get(k, k)
            if k == "labels":
                readings[k] = [t.strip() for t in v.split(",") if t.strip()]
            else:
                readings[k] = v.strip()
    else:
        task_dir = resolve_task_dir(args.task)
        task, task_path = load_task(task_dir)
        readings = task.get("assessment")
        if not readings:
            raise CompassError(
                f"{task_path} has no assessment block - triage records the "
                f"four dimensions there before the approach is evaluated."
            )

    result = evaluate_route(readings, policy)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        # Provenance first. route.md records which guardrails fired and why; it
        # said nothing about WHICH POLICY produced those answers, so a reader
        # could not tell a genuinely light route from a stale-governance one.
        print(f"  policy          : {os.path.join(gov, 'routing-policy.yml')} "
              f"(v{policy.get('version', 'unknown')})")
        drift = governance_drift(gov)
        if drift.drifted:
            fw = drift.framework_versions.get("routing-policy.yml", "unknown")
            print(f"  POLICY DRIFT    : this policy is missing {drift.count} "
                  f"rule(s)/check(s) that framework v{fw} ships - "
                  f"run `compass policy lint` for the list")
        elif not drift.comparable:
            print(f"  policy drift    : not compared ({drift.reason})")
        print(f"  assessment      : {json.dumps(readings)}")
        print(f"  candidate shape : {display_shape(result['candidate_route'])}  "
              f"<- {result['candidate_via']}")
        print(f"  FINAL APPROACH  : {display_shape(result['delivery_approach'])}")
        if result["policy_rules_fired"]:
            print("  policy rules fired:")
            for f in result["policy_rules_fired"]:
                print(f"    [{f['id']}] {f['kind']}: {f['rationale']}")
                for c in f["changed"]:
                    print(f"        - {c}")
        else:
            print("  policy rules fired: none")
        print(f"  topology        : {result['topology']}")
        print("  per-stage weight:")
        for p, w in result["stages"].items():
            print(f"    {p:<11}: {w}")
        print(f"  gate set        : {', '.join(result['gates'])}")
        if result["required_artifacts"]:
            print(f"  required artifacts: {', '.join(result['required_artifacts'])}")
        if result["required_skills"]:
            print(f"  required skills : {', '.join(result['required_skills'])}")
        if result["blocked_phases"]:
            for b in result["blocked_phases"]:
                print(f"  BLOCKED phase   : {b['phase']} until {b['until']}")
        if result.get("applicable_strategies"):
            print("  advisory strategies (soft - assessed, never gating):")
            for s in result["applicable_strategies"]:
                print(f"    [{s['id']}] {s['strategy']}: {s['rationale']}")

    # --write: fold the result back into task.yml
    if args.write:
        if task is None:
            raise CompassError("--write needs an issue (use --issue or run in a "
                               "issue; it cannot write with ad-hoc --assessment)")
        # Re-frame detection, on the route's CONTENT rather than its name.
        # Keying on the name discarded real re-frames: a task whose governance
        # was updated went from 7 gates to 9 under the same route name and
        # logged nothing, taking its `--reason` with it. Route weight is not the
        # only thing that matters about a route.
        prior = {
            "delivery_approach": task.get("delivery_approach"),
            "stages": task.get("stages"),
            "topology": task.get("topology"),
            "gates": sorted(g.get("id") for g in (task.get("gates") or [])
                            if isinstance(g, dict)),
            "policy_rules_fired": sorted(
                f.get("id") for f in (task.get("policy_rules_fired") or [])
                if isinstance(f, dict)),
        }
        now = {
            "delivery_approach": result["delivery_approach"],
            "stages": result["stages"],
            "topology": result.get("topology"),
            "gates": sorted(result.get("gates") or []),
            "policy_rules_fired": sorted(
                f.get("id") for f in (result["policy_rules_fired"] or [])
                if isinstance(f, dict)),
        }
        # Only fields that were ALREADY recorded can have changed. A task whose
        # phases or gates were never written is being filled in for the first
        # time - `--write` after a bare `route:` is materialisation, not a
        # re-frame, and logging it would put noise into the signal this exists
        # to sharpen.
        changed = {k: {"from": prior[k], "to": now[k]}
                   for k in prior if prior[k] and prior[k] != now[k]}
        reframed = bool(prior["delivery_approach"]) and bool(changed)
        if reframed:
            reason = args.reason or "(reason not given - fill this in)"
            # The kind keeps calibration honest. Logging a governance-driven
            # weight-up as a plain re-frame would read as the Needle
            # under-sizing - and it is not: the readings were right, the policy
            # under them moved. Only `judgement` feeds the re-sizing aggregate.
            kind = getattr(args, "kind", None) or "judgement"
            task.setdefault("reassessments", []).append({
                "from_route": prior["delivery_approach"],
                "to_route": result["delivery_approach"],
                "kind": kind,
                "changed": changed,
                "reason": reason,
                "date": datetime.date.today().isoformat(),
            })
        task["schema_version"] = "2.0"
        task["delivery_approach"] = result["delivery_approach"]
        task["policy_rules_fired"] = result["policy_rules_fired"]
        task["stages"] = result["stages"]
        # seed the gate list (status pending) without clobbering existing state
        existing = {g.get("id"): g for g in task.get("gates", []) if isinstance(g, dict)}
        task["gates"] = [
            existing.get(gid, {"id": gid, "status": "pending", "evidence": []})
            for gid in result["gates"]
        ]
        # ensure the evidence registry exists at the top level
        task.setdefault("evidence", [])
        task["topology"] = result["topology"]
        save_task(task, task_path)
        _annotate_gate_accepts(task_path)   # R6-6: seed accepted-type comments
        print(f"\n  wrote route, phases, gates -> {task_path}")
        if not reframed and getattr(args, "reason", None):
            print("  no route change detected - the --reason was NOT recorded. "
                  "The route, phases, gates, topology and fired guardrails are "
                  "all identical to what was already on record.")
        if reframed:
            print(f"  RE-FRAME recorded ({task['reassessments'][-1]['kind']}): "
                  f"{prior['delivery_approach']} -> {result['delivery_approach']}"
                  + (f"  [changed: {', '.join(sorted(changed))}]" if changed else ""))
            if not args.reason:
                sys.stderr.write(
                    "compass: re-frame recorded with no reason. Re-run with "
                    "--reason \"...\" or edit task.yml's last `reframes` "
                    "entry - the reason is the calibration signal.\n"
                )
    return 0
