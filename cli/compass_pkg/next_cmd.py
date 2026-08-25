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
from compass_pkg.core import artifact_path, load_yaml, resolve_task_dir, normalize_spine

# --- command: next -----------------------------------------------------------
# TRC-C4 through TRC-C10, TRC-F6
#
# `compass next` reads task.yml + route.md and prints ONE line: the next
# phase, the next uncleared gate, and route-aware collapsed-phase markers.
# It is strictly READ-ONLY over .compass/work/<task>/ - no file is written
# or created (TRC-C7).  It derives its answer from task.yml + route.md only
# (TRC-C8); nothing else is read.
#
# Output format (devlog: chosen for clarity without colour escapes):
#   "<NextPhase> [gate: <gate-id>][ | <phase> is collapsed on this route]"
# When all phases are complete / landed:
#   "all phases complete"
# When route.md is missing:
#   exit non-zero with a message naming route.md
# When task.yml is missing (Frame not yet run):
#   exit non-zero with a message naming Frame
#
# The canonical phase order Compass follows:
# The CURRENT keys. `normalize_spine` maps a retired key forward on load, so a
# list written in the retired spelling stops matching every spine it reads -
# and `compass next` then reports the wrong stage rather than failing, which is
# how it was caught.
_PHASE_ORDER = [
    "assess",
    "define",
    "refine",
    "plan",
    "breakdown",
    "implement",
    "verify",
    "ship",
]

# Weights that indicate a phase was deliberately excluded from this route
_SKIPPED_WEIGHTS = {"skipped", "collapsed"}


def _next_active_phase(phases: dict) -> str | None:
    """Return the slug of the next phase that actively runs on this route.

    Skipped / collapsed phases are bypassed.  Returns None when every phase
    has a skipped weight (degenerate route) or phases is empty.
    """
    for p in _PHASE_ORDER:
        weight = (phases.get(p) or "").strip().lower()
        if weight not in _SKIPPED_WEIGHTS:
            return p
    return None


def _detect_collapsed_phases(phases: dict) -> list:
    """Return phase names (title-cased) that are collapsed on this route."""
    out = []
    for p in _PHASE_ORDER:
        weight = (phases.get(p) or "").strip().lower()
        if weight == "collapsed":
            out.append(p.capitalize())
    return out


def _first_pending_gate(gates: list) -> str | None:
    """Return the id of the first gate whose status is not 'pass'."""
    for g in (gates or []):
        if isinstance(g, dict) and g.get("status") != "pass":
            return g.get("id")
    return None


def _all_gates_pass(gates: list) -> bool:
    """True when every gate is marked pass."""
    if not gates:
        return False
    return all(
        isinstance(g, dict) and g.get("status") == "pass"
        for g in gates
    )


def _current_phase_from_task(task: dict) -> str | None:
    """Determine the current (active) phase from task.yml.

    Priority:
      1. task.yml top-level `current_phase` field (builder sets this).
      2. Fall back to the first non-skipped phase in the phases map.
    """
    cp = task.get("current_phase")
    if cp and isinstance(cp, str):
        return cp.strip().lower()
    phases = task.get("stages") or {}
    return _next_active_phase(phases)


def cmd_next(args):
    """compass next - what comes next on this issue's route?

    Reads task.yml + delivery-approach.md and prints ONE line.
    Strictly read-only (TRC-C7).
    """
    task_dir = resolve_task_dir(getattr(args, "task", None))

    # --- task.yml: must exist (Frame check) ---
    task_path = os.path.join(task_dir, "task.yml")
    if not os.path.isfile(task_path):
        sys.stdout.write(
            "Triage has not run for this issue - task.yml is missing.\n"
            f"  Run /compass:triage to start the issue at: {task_dir}\n"
        )
        return 2

    task = normalize_spine(load_yaml(task_path))

    # --- route.md: must exist (TRC-F6) ---
    route_md_path = artifact_path(task_dir, "delivery-approach.md")
    if not os.path.isfile(route_md_path):
        sys.stdout.write(
            f"delivery-approach.md is missing from {task_dir}\n"
            "  Run /compass:triage to produce delivery-approach.md before using compass next.\n"
        )
        return 2

    # --- completed task (TRC-C6) ---
    status = task.get("status", "")
    gates = task.get("gates") or []
    if status == "landed" or _all_gates_pass(gates):
        sys.stdout.write("all phases complete\n")
        return 0

    # --- determine next phase and collapsed siblings (TRC-C4, TRC-C5) ---
    phases = task.get("stages") or {}
    current_phase = _current_phase_from_task(task)

    # The "next phase" is the current_phase (the one in progress, or the
    # first non-skipped phase on a fresh task).
    next_phase = current_phase
    if not next_phase:
        # No current phase derivable - route is complete or degenerate
        sys.stdout.write("all phases complete\n")
        return 0

    # Find the first pending gate for the "next gate" display
    pending_gate = _first_pending_gate(gates)

    # Collapsed phases on this route (TRC-C5)
    collapsed = _detect_collapsed_phases(phases)

    # --- compose the one-line output (TRC-C4) ---
    parts = [next_phase.capitalize()]
    if pending_gate:
        parts[0] += f" [gate: {pending_gate}]"
    if collapsed:
        parts.append(f"{', '.join(collapsed)} collapsed on this route")

    sys.stdout.write(" | ".join(parts) + "\n")
    return 0
