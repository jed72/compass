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
#   compass tdd-red CMD...    Run a test command, assert it FAILS, record the
#                            red + the .red marker (honestly - the marker is
#                            only written after a real failure).
#                            --scenario SCN-xxx binds the red to a scenario, so
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
from compass_pkg.checks import NOTHING_TO_CHECK, _check_backfills_paid, _check_changed_code_traces, _check_claim_traces, _check_coherence_check_passes, _check_evidence_identity_matches, _check_command_passes, _check_declared_tests_resolve, _check_dod_evidence_typed, _check_gate_evidence, _check_human_approval, _check_no_trusted_rerun, _check_scenario_has_id_and_intent, _check_scenarios_are_executable, _check_scenarios_have_tests, _check_spike_conclusion_present, _check_spike_no_production_changes, _check_suite_passed
from compass_pkg.dashboard import _check_dashboard_current
from compass_pkg.core import FRAMEWORK_ROOT, exit_for_mode, find_governance, load_mode, load_task, load_yaml, mode_banner, reading_matches, resolve_task_dir



CHECK_FNS = {
    "scenarios-have-tests": _check_scenarios_have_tests,
    "scenarios-are-executable": _check_scenarios_are_executable,
    "declared-tests-resolve": _check_declared_tests_resolve,
    "suite-passed": _check_suite_passed,
    "changed-code-traces-to-scenario": _check_changed_code_traces,
    "scenario-has-id-and-intent": _check_scenario_has_id_and_intent,
    "claim-traces-to-scenario": _check_claim_traces,
    "gate-evidence-present": _check_gate_evidence,
    "dod-evidence-typed": _check_dod_evidence_typed,
    "human-approval-present": _check_human_approval,
    "backfills-paid": _check_backfills_paid,
    "spike-conclusion-present": _check_spike_conclusion_present,
    "spike-no-production-changes": _check_spike_no_production_changes,
    "coherence-check-passes": _check_coherence_check_passes,
    "no-trusted-rerun": _check_no_trusted_rerun,
    "command-passes": _check_command_passes,
    "evidence-identity-matches": _check_evidence_identity_matches,
    "dashboard-current": _check_dashboard_current,
}

# Per-check guidance for structured failure messages. Each entry has the
# *why it matters* and the *how to fix it* - the bits a check's own detail
# string usually does not have room for. The check returns the "what failed";
# this table supplies the rest. A failure with guidance reads like support;
# a failure without reads like bureaucracy.
CHECK_GUIDANCE = {
    "dashboard-current": {
        "why": "The issue's README is the page a reviewer approves from - it states which documents exist, which one is waiting on them, and what was deliberately left out. Generated from task.yml, so once the spine moves it is an assertion the record contradicts, and a reviewer has no way to tell.",
        "fix": "Run `compass issue dashboard` to regenerate it, then read the page again before approving anything from it. Never hand-edit it - the next regeneration discards the edit.",
    },
    "scenarios-have-tests": {
        "why": "Every scenario must have a test that exercises it - without one, the scenario is a wish, not a checkable acceptance criterion (the acceptance-before-code guardrail). EXCEPT a `verifiable: narrative` scenario (a failure-mode playbook), which is cleared by being documented - a non-empty When/Then in acceptance-criteria.md - not by a fabricated test.",
        "fix": "For an ordinary scenario, add at least one test reference to its `tests:` list in task.yml (or remove it). For a narrative scenario, mark it `verifiable: narrative` and give it a real When/Then body in acceptance-criteria.md - documentation is its acceptance.",
    },
    "suite-passed": {
        "why": "The tested-before-ship guardrail requires a recorded green test run.",
        "fix": "Run `compass tdd-green --scenario <SCN-ID> -- <your test command>` - it will run the test, confirm green, and record the evidence in task.yml's registry.",
    },
    "changed-code-traces-to-scenario": {
        "why": "Compass requires every production change to trace back to a stated acceptance criterion (the traceability guardrail).",
        "fix": "Edit task.yml: under each `changed_files:` entry, list the scenario id(s) that drove the change. Add a new scenario if the behaviour was unspecified.",
    },
    "scenario-has-id-and-intent": {
        "why": "Each scenario needs a stable id and an intent link so claims, tests, and code can reference it.",
        "fix": "Add `id:` (e.g. SCN-003) and `intent:` (the intent id from prd.md) fields to the scenario in task.yml.",
    },
    "claim-traces-to-scenario": {
        "why": "Public claims must trace to a scenario that backs them (traceability) - an unbacked claim is a promise the framework cannot prove.",
        "fix": "Add a backing `scenario:` field to the claim in task.yml, or remove the claim from `claims:`.",
    },
    "gate-evidence-present": {
        "why": "The evidence-not-assertion guardrail: a gate marked pass must point at registry evidence of the right type. A mechanical gate cannot be cleared with a written note.",
        "fix": "Add the evidence to the top-level `evidence:` registry with the correct `type:` (see governance/guardrails.yml `gate_evidence_requirements`), then reference its id under the gate's `evidence:` list.",
    },
    "human-approval-present": {
        "why": "The human-sign-off guardrail (a human signs off on the irreversible): this issue touches auth, payments, personal data, or migrations and needs a recorded approval.",
        "fix": "Add a `human-approval` evidence entry to the registry with approver, role, scope, decision=approved, and timestamp. Then reference it from the relevant gate's evidence.",
    },
    "backfills-paid": {
        "why": "Borrowed ceremony - a Hotfix follow-up or a de-scoped artifact - must be paid before an issue closes. Otherwise the audit trail has a hole.",
        "fix": "Complete each unpaid follow-up (writing the deferred artifact, promoting the reproduction scenario, etc.) and set its `status: paid` in task.yml.",
    },
    "spike-conclusion-present": {
        "why": "A Spike without a recorded conclusion is just untracked work - the conclusion is what makes the exploration accountable.",
        "fix": "Add a `spike-conclusion` evidence entry to the registry with `decision:` (discard | graduate-to-delivery | defer). If graduating, include `next_task:` linking the new delivery issue.",
    },
    "spike-no-production-changes": {
        "why": "A Spike's safety model is that it ships nothing - graduating to delivery must be a fresh triage, not a silent merge.",
        "fix": "Empty `changed_files:` in this Spike's task.yml. If the finding is worth keeping, run `/compass:triage` to start a new delivery issue that owns the code under a real route.",
    },
    "dod-evidence-typed": {
        "why": "The evidence-not-assertion guardrail: the Definition of Done is a typed gate. Every unchecked DoD box must reference typed evidence or a filed follow-up - narrative notes in devlog.md do not count.",
        "fix": (
            "For each bare unchecked DoD item: (a) add `(evidence: EV-<id>)` "
            "inline, where EV-<id> is an entry in the issue's evidence registry "
            "with an accepted type; or (b) add `(follow-up: BF-<id>)` inline and "
            "record BF-<id> in task.yml follow-ups with status: owed; or (c) tick "
            "the box `[x]` if a human has actually done the work."
        ),
    },
    "coherence-check-passes": {
        "why": "Evidence, not assertion: verify.analyze requires a recorded `compass analyze` run with zero coherence findings, backed by a `coherence-check` evidence entry.",
        "fix": "Run `compass analyze` - when verify.analyze is in the gate set it exits non-zero on findings, writes a `coherence-check` evidence record, and clears the gate only when there are zero findings. Resolve any reported orphaned scenarios, approach disagreements, or orphan claims first.",
    },
}


def summarise_counts(ran, failures, nothing_to_check=0):
    """The one-line verdict `compass check` ends on.

    Three of the default checks can clear with nothing to check - no BDD
    runner wired, no claims recorded, no project guardrails declared. Each is
    labelled honestly on its own line, but folding them into a single
    "all N passed" made the headline number claim more than was verified.
    They are reported apart so the count never overstates.
    """
    if failures:
        return f"compass check: FAIL - {failures} of {ran} check(s) failed."
    # No denominator on a pass. "12 of 15 passed" reads as three failures at
    # a glance, and the total is not a constant anyway - `G5 A human signs off
    # on the irreversible` only runs when the work touches auth, payments,
    # personal data or migrations, so it moves between issues. A denominator
    # is the right thing to print when checks FAILED, which is the branch
    # above.
    if nothing_to_check:
        return (f"compass check: PASS - {ran - nothing_to_check} check(s) "
                f"passed, {nothing_to_check} had nothing to check.")
    return f"compass check: PASS - all {ran} check(s) passed."


def _print_check_result(check_name, passed, detail, indent="    "):
    """Print one check's result with structured why/fix on failure."""
    if passed:
        print(f"{indent}PASS {check_name}: {detail}")
        return
    print(f"{indent}FAIL {check_name}")
    print(f"{indent}     what: {detail}")
    g = CHECK_GUIDANCE.get(check_name)
    if g:
        print(f"{indent}     why : {g['why']}")
        print(f"{indent}     fix : {g['fix']}")


def cmd_check(args):
    gov = find_governance()
    guardrails = load_yaml(os.path.join(gov, "guardrails.yml"))
    task_dir = resolve_task_dir(args.task)
    task, _ = load_task(task_dir)
    readings = task.get("assessment") or {}
    mode = load_mode()

    # Route-aware: a Spike does not need the delivery guardrails (G1-G5 do not
    # apply - a spike ships nothing), but it IS controlled: it must conclude,
    # and it must not silently produce production change. `compass check` runs
    # `spike_guardrails` from guardrails.yml on a Spike route instead of the
    # delivery defaults.
    if task.get("delivery_approach") == "spike":
        spike_gs = list(guardrails.get("spike_guardrails", []))
        print(f"compass check - issue '{os.path.basename(task_dir)}' (approach: spike)")
        print(f"{mode_banner(mode)}\n")
        if not spike_gs:
            print("  WARNING: no `spike_guardrails:` defined in guardrails.yml - a Spike is uncontrolled.")
            return exit_for_mode(1, mode)
        failures = 0
        ran = 0
        for g in spike_gs:
            gid = g.get("id", "?")
            print(f"  {gid} {g.get('name', '')}")
            for check_name in g.get("checks", []):
                fn = CHECK_FNS.get(check_name)
                ran += 1
                if fn is None:
                    failures += 1
                    _print_check_result(check_name, False,
                        "declared spike guardrail check has NO CLI implementation")
                    continue
                try:
                    passed, detail = fn(task, task_dir)
                except Exception as exc:
                    passed, detail = False, f"check errored: {exc}"
                if not passed:
                    failures += 1
                _print_check_result(check_name, passed, detail)
            print()

        # Backfills are cross-cutting and a Spike is the route that most often
        # OWES one - a graduating spike leaves ceremony behind by design. The
        # spike branch used to return before the shared backfill block below,
        # so a Spike with an owed backfill reported "concluded and contained"
        # and the word "backfill" never appeared.
        ran += 1
        try:
            passed, detail = _check_backfills_paid(task, task_dir)
        except Exception as exc:                        # noqa: BLE001
            passed, detail = False, f"check errored: {exc}"
        print("  outstanding follow-ups")
        _print_check_result("backfills-paid", passed, detail)
        print()
        if not passed:
            failures += 1

        print("-" * 60)
        if failures:
            print(f"compass check: FAIL - {failures} of {ran} Spike check(s) failed.")
        else:
            print(f"compass check: PASS - all {ran} Spike check(s) passed. "
                  "Spike is concluded and contained.")
        return exit_for_mode(failures, mode)

    all_guardrails = list(guardrails.get("defaults", [])) + list(guardrails.get("project", []))
    declared_checks = guardrails.get("checks") or {}
    failures = 0
    ran = 0
    # Checks that cleared with nothing to inspect. Counted apart so the
    # summary never reports a check that inspected nothing as something it
    # verified.
    nothing_to_check = 0
    # Reads `delivery_approach`, the live spine key. This said `route` - the
    # key the v2 rename retired - so it fell to its default and printed a
    # placeholder on every run, with the real value sitting in the spine.
    print(f"compass check - issue '{os.path.basename(task_dir)}' "
          f"(approach: {task.get('delivery_approach', '?')})")
    print(f"{mode_banner(mode)}\n")

    # A guardrail the project's file OMITS produced no output at all: not
    # "skipped", nothing. On a task touching auth, against a governance copy
    # without G5, this printed G1-G4 and returned its normal result. Report the
    # ones that are absent AND would have applied here - task-scoped on purpose,
    # because a full inventory printed on every task is a message nobody reads.
    # `compass policy lint` is where the full inventory lives.
    declared_ids = {g.get("id") for g in all_guardrails}
    try:
        fw_guardrails = load_yaml(
            os.path.join(FRAMEWORK_ROOT, "governance", "guardrails.yml"))
        fw_defaults = (fw_guardrails.get("defaults") or []) if isinstance(
            fw_guardrails, dict) else []
    except Exception:                                   # noqa: BLE001
        fw_defaults = []
    for fg in fw_defaults:
        fid = fg.get("id")
        if fid in declared_ids:
            continue
        applies = fg.get("applies_when")
        if applies and not reading_matches(applies, readings):
            continue          # absent, but would not have applied here anyway
        print(f"  {fid} {fg.get('name', '')}: ABSENT from this project's "
              f"governance, and it applies to this assessment - the framework "
              f"defines it but governance/guardrails.yml does not. Run "
              f"`compass policy lint`.")

    for g in all_guardrails:
        gid = g.get("id", "?")
        applies = g.get("applies_when")
        if applies and not reading_matches(applies, readings):
            print(f"  {gid} {g.get('name', '')}: not applicable for this assessment - skipped")
            continue
        print(f"  {gid} {g.get('name', '')}")
        for check_name in g.get("checks", []):
            fn = CHECK_FNS.get(check_name)
            ran += 1
            if fn is None:
                # A declared guardrail check with no implementation is the one
                # thing that quietly breaks the guardrail/strategy model: the
                # team believes they have a hard, blocking check, and they do
                # not. So this FAILS - loudly - rather than warning.
                failures += 1
                _print_check_result(check_name, False,
                    "declared guardrail check has NO CLI implementation - "
                    "it cannot run, so it is not a guardrail. Implement it "
                    "in CHECK_FNS, or move the guardrail to strategies.md.")
                continue
            try:
                passed, detail = fn(task, task_dir)
            except Exception as exc:  # a check should never crash the run
                passed, detail = False, f"check errored: {exc}"

            # A check may declare `blocking_when:` in guardrails.yml - a
            # reading-scoped condition, exactly like a guardrail's
            # `applies_when:`. Below that threshold a finding is reported and
            # does not fail the run. The condition lives in governance as data;
            # only its evaluation is here, which is the side of ADR-001's
            # boundary mechanism belongs on.
            blocking_when = (declared_checks.get(check_name) or {}).get(
                "blocking_when")
            if (not passed and blocking_when
                    and not reading_matches(blocking_when, readings)):
                passed = True
                detail = ("advisory for this assessment - %s. It blocks when %s."
                          % (detail, json.dumps(blocking_when)))

            if not passed:
                failures += 1
            elif passed is NOTHING_TO_CHECK:
                nothing_to_check += 1
            _print_check_result(check_name, passed, detail)
        print()

    # backfills are cross-cutting - always run them
    ran += 1
    try:
        # Every other check is wrapped - "a check should never crash the run" -
        # and this one was not, so a `backfills:` list of strings took down
        # check, receipt, rework-scan, flow --digest and ci with a traceback.
        passed, detail = _check_backfills_paid(task, task_dir)
    except Exception as exc:                            # noqa: BLE001
        passed, detail = False, f"check errored: {exc}"
    print("  outstanding follow-ups")
    _print_check_result("backfills-paid", passed, detail)
    print()
    if not passed:
        failures += 1

    print("-" * 60)
    print(summarise_counts(ran, failures, nothing_to_check))
    return exit_for_mode(failures, mode)
