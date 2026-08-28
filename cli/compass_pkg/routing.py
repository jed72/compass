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
from compass_pkg.core import _stage_key_renames, ASSESSMENT_KEY_MAP, CompassError, canonical_shape, display_shape, display_stage, find_governance, load_manifest, load_yaml, reading_matches, resolve_issue_dir, save_manifest, shape_stages
from compass_pkg.governance import governance_drift
from compass_pkg.manifest import _annotate_gate_accepts



# How many parallel subtasks each route shape permits is stated by the policy
# as a number, so a cap can be compared against it directly. A null ceiling
# means UNBOUNDED, not that the number is unknown.
# Nothing in routing-policy.yml or .compass/config.yml states a multiagent width -
# the only cap the policy carries is RP-CAP-001's max_worktrees: 1, and the
# config file says in as many words that the worktree cap is a routing
# concern it does not hold. An earlier draft wrote 8 here; that is a
# configurable-looking number frozen into a literal, and it would have
# misreported the day anyone set a real cap. A ceiling on a multiagent can only
# come from a cap, or from the distribution map at breakdown.
# Route shapes declare `subtask_ceiling` as a number since ADR-023. The word
# -> number lookup that used to live here is gone; `core` keeps its own copy
# for reading archived manifests, which still carry the words.


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
    candidate_via = "the policy default (no shape matched)"
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
    # Artifacts a rule earns, beside the gates a rule earns. What an issue
    # documents is a routed output like its stages and its gate set: judgement
    # produces the assessment, and the mechanism produces everything downstream.
    # A hand-assembled artifact list is a form, which is the thing this
    # framework exists to remove.
    rule_artifacts = []
    for fl in guardrails.get("floors", []):
        if not reading_matches(fl.get("when"), readings):
            continue
        changed = []
        forced = fl.get("force_minimum_route")
        if forced and weight(forced) > weight(final):
            changed.append(f"approach raised {display_shape(final)} -> "
                           f"{display_shape(forced)}")
            final = forced
        if fl.get("require_phase"):
            # Canonicalised, for the same reason as `never_skip` below. These
            # names are looked up in the shape's stage map, which
            # `shape_stages` has already canonicalised - so a floor naming the
            # retired key asked for an entry that is never there, found
            # nothing, and raised nothing. No error and the floor still
            # reported as fired. `never_skip` got this treatment in the v2
            # rename and this line, seven above it, did not.
            required = _stage_key_renames().get(fl["require_phase"],
                                                fl["require_phase"])
            required_phases.add(required)
            changed.append(f"stage '{display_stage(required)}' "
                           f"forced full-weight")
        if fl.get("require_skill"):
            required_skills.add(fl["require_skill"])
            changed.append(f"skill '{fl['require_skill']}' required")
        if fl.get("never_skip"):
            # Canonicalise the stage names a floor rule lists, the same way
            # `shape_stages` canonicalises the keys a shape declares. A policy
            # written before this rename says `clarify` here, and this list is
            # printed - so without it the evaluator names a retired stage in
            # the sentence explaining why a stage cannot be skipped.
            _renames = _stage_key_renames()
            fl = dict(fl, never_skip=[_renames.get(x, x) for x in fl["never_skip"]])
            never_skip.update(fl["never_skip"])
            changed.append("never-skip: " + ", ".join(
                display_stage(s) for s in fl["never_skip"]))
        if fl.get("add_gate"):
            floor_gates.append(fl["add_gate"])
            changed.append(f"gate '{fl['add_gate']}' added to the "
                           f"approach's gate set")
        if fl.get("add_artifact"):
            rule_artifacts.append((fl["add_artifact"], fl.get("rationale", "")))
            changed.append(f"artifact '{fl['add_artifact']}' added to the "
                           f"approach's artifact set")
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
            changed.append(
                f"approach '{display_shape(cap['forbid_route'])}' forbidden")
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
            changed.append(f"stage '{display_stage(rr['block_phase'])}' "
                           f"blocked until: {rr.get('until', '')}")
        if rr.get("gate"):
            role_gates.append(rr["gate"])
            changed.append(f"gate '{rr['gate']}' added to the "
                           f"approach's gate set")
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
    # A CEILING, not a decision. Assess cannot know the orchestration: the
    # evaluator has no concept of a work unit, `routing-policy.yml` says
    # nothing about independence or subtasks, and the distribution map that
    # decides parallelism is written at design - three stages later. So the
    # evaluator reports how many parallel subtasks this approach PERMITS, and
    # breakdown sets the actual orchestration once the map exists.
    #
    # It stays a number so a cap can be compared against it. The previous code
    # wrote the sentence "solo (capped to 1 worktree)" into a machine field.
    # --- the artifact set --------------------------------------------------
    # The shape says what this size and risk of work ordinarily documents; a
    # rule adds what a dimension the shape cannot see has earned. Nothing is
    # recorded as "omitted" here: a document the assessment never earned was
    # never a candidate, and writing a reason for it would be the bookkeeping
    # this is meant to remove. `omitted` is for a human deliberately dropping
    # something that WAS earned.
    artifacts = []
    for kind, depth in (shape.get("artifacts") or {}).items():
        artifacts.append({
            "id": "ART-" + str(kind).upper().replace("-", "_"),
            "kind": kind, "status": "draft", "depth": depth,
            # The reason names the rule that earned it, in the reader's words.
            # It deliberately does not repeat the kind - the row already says
            # which document this is, and "initiative earns it (prd)" told a
            # reviewer nothing they could not see.
            "reason": "every %s carries %s" % (
                display_shape(final),
                "one" if depth == "full" else "a light one"),
        })
    # A role rule already demands documents via `require_artifact` - a marketer
    # needs launch-readiness, a product owner a brief. That is the same idea
    # from the role's side, so it joins the same set rather than living in a
    # second list nothing renders.
    for req in required_artifacts:
        kind = req[:-3] if str(req).endswith(".md") else str(req)
        rule_artifacts.append((kind, "a role in play requires it"))

    for kind, why in rule_artifacts:
        if any(a["kind"] == kind for a in artifacts):
            continue
        artifacts.append({
            "id": "ART-" + str(kind).upper().replace("-", "_"),
            "kind": kind, "status": "draft", "depth": "full",
            "reason": why or "added by a policy rule",
        })

    subtask_ceiling = shape.get("subtask_ceiling", 1)
    if max_worktrees is not None:
        subtask_ceiling = (max_worktrees if subtask_ceiling is None
                           else min(subtask_ceiling, max_worktrees))

    # --- soft advisory strategies (R10) -------------------------------------
    # These BIAS/ASSESS only - they never alter the route, gates, weight, or
    # subtask ceiling. Surfaced for the Needle and the reviewer (e.g. regression-
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
        "artifacts": artifacts,
        "subtask_ceiling": subtask_ceiling,
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
        task_dir = resolve_issue_dir(args.task)
        task, task_path = load_manifest(task_dir)
        readings = task.get("assessment")
        if not readings:
            raise CompassError(
                f"{task_path} has no assessment block - triage records the "
                f"four dimensions there before the approach is evaluated."
            )

    result = evaluate_route(readings, policy)

    from compass_pkg.terminal import Emitter, mark_handled, resolve_mode

    # This verb renders all three modes itself, including the JSON document it
    # shipped with. Saying so keeps the generic fallback in main() out of the
    # way - without it, that fallback wrapped this verb's own JSON in its
    # "unconverted verb" envelope and every key moved a level down.
    mark_handled()
    _mode = resolve_mode(args)
    if _mode == "json":
        print(json.dumps(result, indent=2))
    elif _mode != "verbose":
        # The default view. Everything below this branch is what --verbose
        # still prints, unchanged: the provenance line, the raw assessment,
        # the per-stage weights and the full gate list. That detail is real,
        # and a person deciding whether the approach looks right does not need
        # all of it on the first screen - they need the approach, the rules
        # that produced it, and where it was written.
        _fired = [str(f["rationale"]).rstrip().rstrip(".")
                  + " (%s, %s)" % (f["id"], f["kind"])
                  for f in result["policy_rules_fired"]]
        _ceiling = result["subtask_ceiling"]
        _concerns = []
        # Policy drift is a CONCERN, not provenance. The plain "which policy
        # file did I read" line is detail and lives under --verbose, but a
        # project running a policy that is missing rules the framework ships
        # gets a lighter approach than it should - and a reader has no way to
        # tell that from a genuinely light one. It belongs on the first screen.
        _drift = governance_drift(gov)
        if _drift.drifted:
            _fw = _drift.framework_versions.get("routing-policy.yml", "unknown")
            _concerns.append(
                "this project's policy is missing %d rule(s) or check(s) that "
                "framework v%s ships - run `compass policy lint`"
                % (_drift.count, _fw))
        if result["blocked_phases"]:
            _concerns += ["%s is blocked until %s" % (b["phase"], b["until"])
                          for b in result["blocked_phases"]]
        if result["required_artifacts"]:
            _concerns.append("documents required: "
                             + ", ".join(result["required_artifacts"]))
        _e = Emitter(mode=_mode,
                     evidence_out=getattr(args, "evidence_out", None))
        _e.hand_off(
            outcome="%s - %d gate(s), %s"
                    % (display_shape(result["delivery_approach"]),
                       len(result["gates"]),
                       "unbounded parallel subtasks" if _ceiling is None
                       else "up to %d parallel subtask(s)" % _ceiling),
            # Only if it is actually there. `delivery-approach.md` is written
            # by the triage command, not by the evaluator, so a first evaluate
            # was telling the reader to open a file that did not exist.
            read=(_approach_doc if task is not None
                  and os.path.isfile(_approach_doc := os.path.join(
                      task_dir, "delivery-approach.md")) else None),
            items=_fired or ["no policy rule fired - the shape is the "
                             "assessment's default"],
            concerns=_concerns,
            next_step=None if args.write else
            "nothing recorded - re-run with --write to fold this into the manifest")
        _e.flush()
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
            seen_effects = set()
            for f in result["policy_rules_fired"]:
                # Meaning first, code in brackets. This printed
                # "[RP-FLOOR-002] floor: You cannot safely..." - a bare
                # identifier opening the first screen a new user ever sees.
                # The receipt's renderer was corrected for exactly this and
                # this one was missed; the two print the same data through
                # different code, which is how they came apart.
                # The KIND stays. It says whether the rule raised the whole
                # approach or only attached a single gate, and an earlier issue
                # exists because every entry in the floors block reported
                # itself as a floor including the four that only add a gate.
                # Dropping it to shorten the line would have quietly undone
                # that work.
                rationale = str(f['rationale']).rstrip().rstrip('.')
                print(f"    {rationale} ({f['id']}, {f['kind']})")
                for c in f["changed"]:
                    if c in seen_effects:
                        continue
                    seen_effects.add(c)
                    print(f"        - {c}")
        else:
            print("  policy rules fired: none")
        ceiling = result["subtask_ceiling"]
        permits = ("unbounded by policy" if ceiling is None
                   else f"up to {ceiling}")
        print(f"  parallel subtasks: {permits} (a ceiling - breakdown sets "
              f"the orchestration once the distribution map exists)")
        print("  per-stage weight:")
        for p, w in result["stages"].items():
            print(f"    {display_stage(p):<11}: {w}")
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

    # --write: fold the result back into manifest.yml
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
            "subtask_ceiling": task.get("subtask_ceiling"),
            "gates": sorted(g.get("id") for g in (task.get("gates") or [])
                            if isinstance(g, dict)),
            "policy_rules_fired": sorted(
                f.get("id") for f in (task.get("policy_rules_fired") or [])
                if isinstance(f, dict)),
        }
        now = {
            "delivery_approach": result["delivery_approach"],
            "stages": result["stages"],
            "subtask_ceiling": result.get("subtask_ceiling"),
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
        # Seed the artifact registry the same way the gate list is seeded:
        # what routing computed, without clobbering a status or path a stage
        # has already recorded against an entry.
        recorded = {a.get("kind"): a for a in task.get("artifacts", [])
                    if isinstance(a, dict)}
        merged = []
        for a in result["artifacts"]:
            keep = recorded.get(a["kind"])
            if keep:
                keep = dict(keep)
                keep["reason"] = a["reason"]      # the rule that earned it
                merged.append(keep)
            else:
                merged.append(a)
        # A human-recorded omission of something routing no longer earns is
        # kept: it is a decision someone took, not stale computed output.
        for kind, a in recorded.items():
            if a.get("status") == "omitted" and not any(m["kind"] == kind for m in merged):
                merged.append(a)
        task["artifacts"] = merged
        # ensure the evidence registry exists at the top level
        task.setdefault("evidence", [])
        task["subtask_ceiling"] = result["subtask_ceiling"]
        # Assess never records an orchestration: breakdown owns it, once the
        # distribution map says whether independent subtasks exist.
        task.pop("orchestration", None)
        save_manifest(task, task_path)
        _annotate_gate_accepts(task_path)   # R6-6: seed accepted-type comments
        print(f"\n  wrote route, phases, gates -> {task_path}")
        if not reframed and getattr(args, "reason", None):
            print("  no route change detected - the --reason was NOT recorded. "
                  "The route, phases, gates, ceiling and fired guardrails are "
                  "all identical to what was already on record.")
        if reframed:
            print(f"  RE-FRAME recorded ({task['reassessments'][-1]['kind']}): "
                  f"{prior['delivery_approach']} -> {result['delivery_approach']}"
                  + (f"  [changed: {', '.join(sorted(changed))}]" if changed else ""))
            if not args.reason:
                sys.stderr.write(
                    "compass: re-frame recorded with no reason. Re-run with "
                    "--reason \"...\" or edit manifest.yml's last `reframes` "
                    "entry - the reason is the calibration signal.\n"
                )
    return 0
