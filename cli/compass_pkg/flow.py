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
from compass_pkg.core import CompassError, find_compass_dir, load_yaml, manifest_path, normalize_spine
from compass_pkg.rework import cmd_rework_scan



# --- command: flow ----------------------------------------------------------
# Cross-task flow view. Reads broadly; writes only when --digest is given.
# NEVER modifies any manifest.yml (Inv-4: Flow advises, never gates).

def cmd_flow(args):
    """Produce the flow board; with --digest also output a dated digest section
    to stdout. The digest includes the rework-scan section (TRC-D5) and a
    calibration summary. Exit code is always 0 - this is advisory.
    """
    work_root = getattr(args, "work_root", None)
    do_digest = getattr(args, "digest", False)

    # Resolve the work root
    if work_root is None:
        try:
            compass_dir = find_compass_dir()
            work_root = os.path.join(compass_dir, "work")
        except CompassError:
            work_root = ".compass/work"

    if not do_digest:
        # Live board mode: minimal - list tasks and their routes
        if not os.path.isdir(work_root):
            print("compass flow: no issues found - work root does not exist.")
            return 0
        slugs = [d for d in sorted(os.listdir(work_root))
                 if os.path.isdir(os.path.join(work_root, d))]
        if not slugs:
            print("compass flow: no issues under work root.")
            return 0
        # Grouped by lifecycle state, because a flat list reported stopped work
        # as in flight. Parked tasks accumulate while active ones close, so the
        # single number a planning view must not get wrong drifts further out
        # the longer the repo lives.
        groups = {"active": [], "queued": [], "parked": [], "landed": [],
                  "abandoned": [], "unreadable": []}
        for slug in slugs:
            task_yml = manifest_path(os.path.join(work_root, slug))
            if not os.path.isfile(task_yml):
                groups["unreadable"].append((slug, "?", "no manifest.yml"))
                continue
            try:
                t = normalize_spine(load_yaml(task_yml))
                # The live manifest key. This read `route`, retired by the
                # v2 rename, so every row on the board printed the
                # placeholder instead of the computed approach.
                route = t.get("delivery_approach", "?")
                # Absent means active: every manifest.yml written before the status
                # field existed omits it (ADR-006).
                status = t.get("status") or "active"
                note = t.get("parked_reason", "") if status == "parked" else ""
                groups.setdefault(status, []).append((slug, route, note))
            except Exception:                                   # noqa: BLE001
                groups["unreadable"].append((slug, "?", "unreadable manifest.yml"))

        # The board is a REPORT: every issue is listed, because a board that
        # omits part of the work looks complete when it is not. What it owes a
        # reader is a summary they can stop at - the counts - before 150 rows
        # of detail.
        from compass_pkg.terminal import Report

        headings = [
            ("active", "IN PROGRESS"),
            ("queued", "NEXT UP"),
            ("parked", "PARKED - stopped, can resume"),
            ("landed", "DONE"),
            ("abandoned", "ABANDONED - will not resume"),
        ]
        named = {k for k, _ in headings} | {"unreadable"}
        counts = {k: len(v) for k, v in groups.items() if v}
        rep = Report(args, title="compass flow - cross-issue board (advisory)")
        rep.summary(
            "compass flow - %d issue(s) across %d state(s). Advisory: this "
            "changes no issue state." % (len(slugs), len(counts)),
            ", ".join("%s %d" % (k, n) for k, n in sorted(counts.items()))
            or "nothing to report")

        def _row(r):
            slug, route, note = r
            return "%-40s approach=%s%s" % (slug, route,
                                            "  - %s" % note if note else "")

        for key, heading in headings:
            rep.section(heading, groups.get(key) or [], _row)
        for key in sorted(set(groups) - named):
            rep.section(key.upper(), groups[key], _row)
        rep.section("UNPLACEABLE - no readable manifest.yml, so no state to report",
                    groups["unreadable"], _row)
        rep.data(counts=counts)
        return rep.emit()

    # --digest mode: produce a digest including rework-scan
    import io as _io
    import contextlib as _cl

    today = datetime.date.today().isoformat()
    print(f"# Flow digest - {today}\n")
    print("> Advisory only. This digest does not modify any issue state (Inv-4).\n")

    # --- Rework scan section (TRC-D5) ---
    # Capture rework-scan output by invoking the scan logic directly
    import types as _types
    scan_args = _types.SimpleNamespace(
        root=work_root,
        window_days=None,
        format="markdown",
    )

    buf = _io.StringIO()
    with _cl.redirect_stdout(buf):
        cmd_rework_scan(scan_args)
    rework_section = buf.getvalue()

    print(rework_section)

    # --- Calibration summary ---
    print("## Calibration signal\n")
    # Enumerate tasks for calibration summary
    tasks = []
    if os.path.isdir(work_root):
        for d in sorted(os.listdir(work_root)):
            tp = manifest_path(os.path.join(work_root, d))
            if os.path.isfile(tp):
                try:
                    data = load_yaml(tp)
                    tasks.append((d, data))
                except CompassError:
                    pass
    total_reframes = sum(len(t.get("reassessments") or []) for _, t in tasks)
    if total_reframes == 0:
        print(f"No re-assessments recorded across {len(tasks)} issue(s). "
              f"Either the sizing is well-calibrated, or there is not enough history yet.\n")
    else:
        print(f"{total_reframes} re-assessment(s) recorded across {len(tasks)} issue(s). "
              f"Run `compass retro` for the full breakdown.\n")

    return 0


# --- living system spec derivation (Subtask B, DD-3, DD-4, ADR-008) ---------
#
# derive_system_spec(project_root) is the internal helper that produces
# docs/system-spec.md by walking every .compass/work/*/manifest.yml whose
# status == 'landed'.
#
# Design constraints honoured here:
#   Inv-5  - annotation over per-task specs, never a parallel spec; the
#            derived file carries the DERIVED FILE header (TRC-B10).
#   Inv-6  - all derivation inputs live on disk; no in-memory accumulation
#            beyond the walk (TRC-B8 reconstructibility).
#   Inv-8  - backward compat: manifest.yml files with no `status` field
#            (schema 1.0) are treated as active (not landed), so they are
#            excluded from the derivation (TRC-B2, TRC-B11, DD-3).
#   ADR-008 §3 - idempotent; deterministic order (land_timestamp, then
#             task slug as tiebreaker); supersession (same intent id →
#             latest-landed wins for current section, earlier → archive).
#   ADR-008 §4 - never source-of-truth; DERIVED FILE header on line 1;
#             silent overwrite on next Land (TRC-B9).
#   TRC-B5 - brand-new project with no landed tasks produces a stub file.

_DERIVED_HEADER = (
    "<!-- DERIVED FILE - do not hand-edit; "
    "edit .compass/work/<task>/acceptance-criteria.md -->"
)


def derive_system_spec(project_root: str) -> None:
    """Derive docs/system-spec.md from all landed manifest.yml files.

    This is the sole implementation of the living-system-spec derivation
    (ADR-008).  It is invoked by ``compass _derive-system-spec --internal``
    from ``scripts/integrate.sh`` after combined regression passes.

    It is idempotent: running it twice on unchanged inputs produces a
    byte-identical ``docs/system-spec.md``.

    Args:
        project_root: absolute path to the project root (the directory that
            contains ``.compass/``).
    """
    project_root = os.path.abspath(project_root)
    compass_work = os.path.join(project_root, ".compass", "work")

    # ---- 1. Collect landed tasks -------------------------------------------
    # Walk .compass/work/*/manifest.yml; keep only status == 'landed'.
    # Tasks without a `status` field (schema 1.0) are treated as active.
    # Process order: land_timestamp ascending, then task slug ascending.
    landed = []  # list of dicts: {slug, task_dir, task, land_timestamp}
    if os.path.isdir(compass_work):
        for slug in sorted(os.listdir(compass_work)):
            task_dir = os.path.join(compass_work, slug)
            yml_path = manifest_path(task_dir)
            if not os.path.isfile(yml_path):
                continue
            try:
                with open(yml_path, encoding="utf-8") as fh:
                    task = normalize_spine(yaml.safe_load(fh) or {})
            except yaml.YAMLError:
                continue
            if not isinstance(task, dict):
                continue
            status = task.get("status")
            if status != "landed":
                continue
            land_ts = task.get("land_timestamp", "")
            landed.append({
                "slug": slug,
                "task_dir": task_dir,
                "issue": task,
                "land_timestamp": str(land_ts) if land_ts else "",
            })

    # Sort: land_timestamp ascending, task slug as tiebreaker
    landed.sort(key=lambda x: (x["land_timestamp"], x["slug"]))

    # ---- 2. Build the current-behaviour and archived-behaviour tables ------
    # Key: intent id → winner entry  (dict with slug, scn_id, scn_title, ts, date)
    current: dict = {}    # intent_id -> entry
    archived: list = []   # list of archived entries

    for item in landed:
        slug = item["slug"]
        task = item["issue"]
        task_dir = item["task_dir"]
        land_ts = item["land_timestamp"]
        # Parse a date string from land_timestamp for display
        land_date = land_ts[:10] if len(land_ts) >= 10 else land_ts

        # Read the scenarios block from manifest.yml
        scenarios = task.get("scenarios") or []
        for scn in scenarios:
            if not isinstance(scn, dict):
                continue
            scn_id = scn.get("id", "")
            scn_title = scn.get("title", "")
            intent = scn.get("intent", "")
            if not intent:
                intent = scn_id  # fall back to id if no intent
            # A scenario may serve more than one intent, and the manifest schema
            # accepts either a string or a list of them. It answers for each
            # id separately: keying on the whole list instead would invent a
            # composite intent that supersedes neither of the real ones.
            intents = intent if isinstance(intent, list) else [intent]
            for one_intent in intents:
                entry = {
                    "slug": slug,
                    "scn_id": scn_id,
                    "scn_title": scn_title,
                    "intent": one_intent,
                    "land_timestamp": land_ts,
                    "land_date": land_date,
                }
                if one_intent in current:
                    # Supersession: the current winner is archived
                    archived.append(current[one_intent])
                current[one_intent] = entry

    # ---- 3. Compose the derived spec text ----------------------------------
    lines = [
        _DERIVED_HEADER,
        "",
        "# System Specification (derived)",
        "",
        "> This file is automatically generated at ship time from the "
        "`.compass/work/<task>/acceptance-criteria.md` files of all landed issues.",
        "> **Do not hand-edit** - edits are silently overwritten on the next ship.",
        "> Edit the source: `.compass/work/<task>/acceptance-criteria.md`.",
        "",
    ]

    if current:
        lines += [
            "## Current Behaviour",
            "",
        ]
        # Sort current entries by intent id for deterministic output
        for intent_id in sorted(current.keys()):
            entry = current[intent_id]
            lines += [
                f"### {entry['scn_title'] or entry['scn_id']}",
                "",
                f"- **Scenario id:** `{entry['scn_id']}`",
                f"- **Intent:** `{entry['intent']}`",
                f"- **Source issue:** `{entry['slug']}`",
                f"- **Landed:** {entry['land_date']}",
                "",
            ]
    else:
        lines += [
            "## Current Behaviour",
            "",
            "> No landed scenarios yet.",
            "",
        ]

    if archived:
        lines += [
            "---",
            "",
            "## Archived Behaviour",
            "",
            "> These scenarios were superseded by a later-landed scenario "
            "with the same intent id.",
            "",
        ]
        # Sort archived entries: land_timestamp, then scn_id for determinism
        archived_sorted = sorted(archived, key=lambda x: (x["land_timestamp"], x["scn_id"]))
        for entry in archived_sorted:
            lines += [
                f"### {entry['scn_title'] or entry['scn_id']} _(archived)_",
                "",
                f"- **Scenario id:** `{entry['scn_id']}`",
                f"- **Intent:** `{entry['intent']}`",
                f"- **Source issue:** `{entry['slug']}`",
                f"- **Landed:** {entry['land_date']}",
                "",
            ]

    content = "\n".join(lines)

    # ---- 3b. Normalise house style on write ---------------------------------
    # Scenario titles from landed tasks are copied verbatim, and four historic
    # ones contain em dashes. docs/system-spec.md is tracked, and this
    # repository forbids em dashes in tracked files - so a faithful copy
    # produces a file that fails the repository's own style test.
    #
    # The normalisation happens HERE, on the output, and never on the sources.
    # Those acceptance-criteria.md files are a record of what was specified at the
    # time; editing them to suit a generator would rewrite history, and would
    # have to be repeated in every adopter's archive. A generator owns its
    # output, so it owns its output's style.
    # \u2014 is the em dash, written as an escape: this file is tracked, and
    # the style test would otherwise flag the normaliser for containing the
    # character it exists to remove.
    # Normalise at the substitution site only. A follow-up global
    # `.replace("  -  ", " - ")` also rewrote titles that never contained an em
    # dash at all - that was the corruption, and it is what this replaces.
    # [ \t] not \s: \s matches newlines, so an em dash at the end of a line
    # swallowed the break and joined a heading to the bullet list after it.
    content = re.sub(r"[ \t]*\u2014[ \t]*", " - ", content)

    # ---- 4. Write atomically -----------------------------------------------
    out_dir = os.path.join(project_root, "docs")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "system-spec.md")
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(content)


def cmd_derive_system_spec(args):
    """Private CLI entry point for ``compass _derive-system-spec --internal``.

    This subcommand is intentionally excluded from ``compass --help`` (the
    leading-underscore convention per DD-4).  It is only for in-framework
    callers (currently ``scripts/integrate.sh``).

    The ``--internal`` flag is mandatory - without it the command errors out
    (belt-and-suspenders protection against accidental direct invocation).
    """
    if not getattr(args, "internal", False):
        raise CompassError(
            "compass _derive-system-spec: the --internal flag is required. "
            "This is a private entry point for scripts/integrate.sh - "
            "it is not part of the public CLI surface."
        )

    # Resolve project root from the current working directory
    # (walk up to find .compass/, fall back to cwd for brand-new projects).
    try:
        compass_dir = find_compass_dir()
        project_root = os.path.dirname(compass_dir)
    except CompassError:
        # Brand-new project with no .compass/ yet - use cwd
        project_root = os.getcwd()

    derive_system_spec(project_root)
    print("compass _derive-system-spec: docs/system-spec.md derived.")
