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
import pathlib
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
from compass_pkg.core import CompassError, artifact_path, display_shape, find_compass_dir, find_upwards, load_yaml, normalize_spine



# --- command: task receipt ---------------------------------------------------
# `compass issue receipt --issue <slug>` renders a one-screen receipt of an issue:
# assessment -> delivery approach -> gates with verdicts -> evidence registry -> overall
# verdict. Read-only over .compass/work/<slug>/{task.yml, delivery-approach.md, evidence/}
# plus governance/guardrails.yml; never re-executes checks (INT-2 / ADR-005).
# Clustered here next to cmd_task_lint so Move 5C can relocate as one block.

def _receipt_resolve_task_dir(args):
    """Resolve an issue dir for the receipt, honouring --workdir if present.

    Returns (task_dir, slug, project_root). Raises CompassError with a
    receipt-specific message that names both the slug and the expected
    directory (TRC-D3).
    """
    workdir = getattr(args, "workdir", None)
    slug = args.task
    if workdir:
        project_root = os.path.abspath(workdir)
        compass_dir = os.path.join(project_root, ".compass")
    else:
        compass_dir = find_compass_dir()
        project_root = os.path.dirname(compass_dir)
    if not slug:
        ptr = os.path.join(compass_dir, "current-task")
        if os.path.isfile(ptr):
            with open(ptr, "r", encoding="utf-8") as fh:
                slug = fh.read().strip()
    if not slug:
        raise CompassError(
            "compass issue receipt: no --issue and no .compass/current-task pointer"
        )
    task_dir = os.path.join(compass_dir, "work", slug)
    if not os.path.isdir(task_dir):
        raise CompassError(
            f"compass issue receipt: issue '{slug}' not found at "
            f".compass/work/{slug} (looked under {task_dir})"
        )
    return task_dir, slug, project_root


def _receipt_gate_requirements(project_root):
    """Read gate_evidence_requirements from governance/guardrails.yml (DD-3).

    Returns {gate_id: frozenset(accepted_types)}. {} when the file is absent -
    type-mismatch detection then silently no-ops (degrades gracefully on
    projects that have not adopted governance, per ADR-006).
    """
    path = os.path.join(project_root, "governance", "guardrails.yml")
    if not os.path.isfile(path):
        return {}
    try:
        data = load_yaml(path) or {}
    except CompassError:
        return {}
    raw = data.get("gate_evidence_requirements") or {}
    return {
        k: frozenset(v) for k, v in raw.items()
        if isinstance(v, list) and v
    }


def _receipt_parse_route_md_readings(route_md_path):
    """Parse the four-readings table out of a delivery-approach.md file.

    Returns {key: (value, justification)} for the four dimensions; absent
    rows are simply not in the dict. If the file is missing or unparseable,
    returns {} - the caller renders "(no justification on file)" in that case.
    """
    import re as _re
    if not os.path.isfile(route_md_path):
        return {}
    text = open(route_md_path, "r", encoding="utf-8").read()
    out = {}
    for dim_labels, key in [
        (("Risk", "Blast" + " radius"), "risk"),  # v1 label built from
        # parts: the scan reads whole string literals, and this one exists
        # only to read old archives
        (("Familiarity", "Terrain"), "familiarity"),
        (("Size", "Magnitude"), "size"),
        (("Goal & role", "Intent & role"), "goal"),
    ]:
      for dim_label in dim_labels:
        m = _re.search(
            rf"\|\s*\*\*{_re.escape(dim_label)}\*\*\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|",
            text,
        )
        if m:
            out[key] = (m.group(1).strip(), m.group(2).strip())
            break
    return out


_RECEIPT_RULE = "=" * 80
_RECEIPT_LINE_CAP = 100

# Per DD-3: types not listed render as id+type+path. Listing extras here is the
# only piece that adapts when a type gains meaningful payload fields.
_RECEIPT_EVIDENCE_EXTRAS = {
    "test-run": ("scenario",),
    "manual-review": ("reviewer",),
    "human-approval": ("approver", "role", "decision"),
    "spike-conclusion": ("decision", "next_task"),
}


def _receipt_truncate(text, width=_RECEIPT_LINE_CAP):
    """ASCII-safe line truncation. Honours DD-2 (no ANSI; bytes stable across
    terminals/CI). Tail "..." indicates the cut."""
    if len(text) <= width:
        return text
    if width <= 3:
        return text[:width]
    return text[:width - 3] + "..."


def _receipt_wrap_ids(head, ids, width=_RECEIPT_LINE_CAP):
    """`head` followed by `ids`, wrapping instead of cutting an identifier.

    Identifiers are the receipt's join keys - a reader follows one from a gate
    to the registry entry that defines it. Truncating one mid-token breaks
    that link silently, so a list that will not fit continues on an indented
    line rather than losing its tail.
    """
    if not ids:
        return [_receipt_truncate(head + "(none)", width)]
    cont = " " * len(head.rstrip()) if len(head) < width // 2 else "      "
    out, current, first = [], head, True
    for i, ident in enumerate(ids):
        piece = str(ident) + ("," if i < len(ids) - 1 else "")
        candidate = current + ("" if first else " ") + piece
        if len(candidate) > width and not first:
            out.append(current)
            current, first = cont + piece, False
            continue
        current, first = candidate, False
    out.append(current)
    return out


def _receipt_parse_topology_override(approach_path):
    """Find a recorded topology override in the delivery-approach record.

    An override lives in the record as a table row whose first cell is
    "Topology" and whose from-to cell reads like "swarm -> solo" (either
    arrow spelling). Returns the overridden-to value, or None. Tolerant by
    design - the record is prose, and a receipt that cannot parse it
    simply shows the computed topology.
    """
    import re as _re
    if not approach_path or not os.path.isfile(approach_path):
        return None
    for line in open(approach_path, "r", encoding="utf-8").read().splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if len(cells) >= 2 and cells[0].lower() == "topology":
            m = _re.search(r"(?:->|\u2192)\s*([a-z][a-z-]*)", cells[1])
            if m:
                return m.group(1)
    return None


def _receipt_render(task, slug, route_readings, gate_requirements=None,
                    topology_override=None):
    """Render the one-screen receipt for an issue. Returns a string.

    Sections (TRC-A1 order):
      1. header  - slug + landed/in-progress status
      2. readings + justifications
      3. route + fired routing guardrails
      4. gates + verdicts + evidence ids
      5. evidence registry (id, type, path)
      6. overall verdict line
    """
    lines = []
    schema_version = str(task.get("schema_version") or "")
    # 2.0 is the current schema; anything else (or absent) is legacy - 1.x
    # spines are readable by normalisation but reported as legacy. ADR-006:
    # render meaningfully on pre-feature task.ymls, do not crash.
    is_legacy = not schema_version.startswith("2.")
    # status: in 1.0 there is no status field - those tasks are treated as
    # active by the rest of the CLI, and the receipt does the same. Honesty:
    # a legacy task with no status cannot be reported as cleanly landed.
    raw_status = task.get("status")
    is_landed = (raw_status == "landed")
    if is_landed:
        header_status = "landed"
    elif raw_status == "active" or raw_status is None:
        header_status = "IN PROGRESS - not yet landed"
    else:
        header_status = str(raw_status).upper()
    schema_note = f" - schema {schema_version or '1.0'} (legacy)" if is_legacy else ""

    # 1. header
    lines.append(_RECEIPT_RULE)
    lines.append(f"Receipt - {slug} ({header_status}){schema_note}")
    lines.append(_RECEIPT_RULE)
    lines.append("")

    # 2. readings + justifications
    lines.append("Assessment")
    lines.append("----------")
    readings = task.get("assessment") or {}
    for label, key in [
        ("risk", "risk"),
        ("familiarity", "familiarity"),
        ("size", "size"),
        ("goal", "goal"),
    ]:
        if key == "goal":
            role = readings.get("role") or "engineer"
            intent_v = readings.get("goal") or "(not recorded)"
            value = f"{intent_v} ({role})"
        else:
            value = str(readings.get(key) or "(not recorded)")
        justification = "(no justification on file)"
        if key in route_readings:
            justification = route_readings[key][1]
        lines.append(_receipt_truncate(
            f"  {label:<14}  {value:<22}  {justification}"))
    touches = readings.get("labels") or []
    if touches:
        lines.append(_receipt_truncate(
            f"  {'labels':<14}  {', '.join(touches)}"))
    lines.append("")

    # 3. the delivery approach + fired policy rules
    lines.append("Approach")
    lines.append("--------")
    route_name = task.get("delivery_approach")
    shape_shown = display_shape(route_name) if route_name else "(not recorded)"
    topology = task.get("topology") or ""
    topology_shown = topology
    if topology_override and topology_override != topology:
        topology_shown = (f"{topology} (overridden: {topology_override} - "
                          "see the delivery approach)")
    # Triage records a ceiling, breakdown records a topology. A spine may
    # legitimately carry either: an archived one has the topology word triage
    # used to write, and an in-flight one has only the ceiling until the
    # distribution map exists. Printing the empty slot said nothing.
    if topology_shown:
        detail = f"topology: {topology_shown}"
    else:
        ceiling = task.get("stream_ceiling")
        detail = ("parallel streams: unbounded by policy" if ceiling is None
                  else f"parallel streams: up to {ceiling}")
    lines.append(_receipt_truncate(f"  {shape_shown}  ({detail})"))
    # No v1-key fallback: the spine is normalised on load (see
    # normalize_spine), so a 1.x `fired_guardrails` has already become
    # this key by the time the receipt reads it.
    fired = task.get("policy_rules_fired") or []
    if fired:
        lines.append("  policy rules fired:")
        for g in fired:
            gid = g.get("id", "?") if isinstance(g, dict) else str(g)
            rationale = g.get("rationale", "") if isinstance(g, dict) else ""
            # Meaning first, code in brackets. This line used to read
            # "<id>: <rationale>", so a reader met an unresolvable code and
            # learned what it did only afterwards - the defect S7 forbids, in
            # the receipt of the release that forbids it. The code stays: it
            # carries the traceability and it is what someone searches for.
            lines.append(_receipt_truncate(
                f"    {rationale.rstrip().rstrip('.')} ({gid})"
                if rationale else f"    ({gid})"))
    else:
        lines.append("  policy rules fired: none")
    lines.append("")

    # 4. gates + verdicts + evidence ids
    # The verdict label is honest about the recorded state (TRC-C1, TRC-C2):
    # a pass referencing wrong-typed evidence is type-mismatch; a pass with no
    # evidence is unsupported. The receipt reports; it does not enforce.
    lines.append("Gates")
    lines.append("-----")
    gates = task.get("gates") or []
    evidence_by_id = {ev.get("id"): ev for ev in (task.get("evidence") or [])
                      if isinstance(ev, dict) and ev.get("id")}
    any_fail = False
    any_caveat = False
    requirements = gate_requirements or {}
    for g in gates:
        gid = g.get("id", "?")
        gstatus = g.get("status", "pending")
        ev_ids = g.get("evidence") or []
        if gstatus == "fail":
            verdict = "[ FAIL ]"
            any_fail = True
        elif gstatus == "pass":
            if not ev_ids:
                verdict = "[ UNSUPPORTED ]"
                any_caveat = True
            else:
                req_types = requirements.get(gid)
                if req_types:
                    ev_types = {evidence_by_id.get(eid, {}).get("type")
                                for eid in ev_ids}
                    ev_types.discard(None)
                    if ev_types and not (ev_types & req_types):
                        verdict = "[ TYPE-MISMATCH ]"
                        any_caveat = True
                    else:
                        verdict = "[ PASS ]"
                else:
                    verdict = "[ PASS ]"
        elif gstatus == "pending":
            # A pending gate is not a clean land. This set neither any_fail nor
            # any_caveat, so a receipt with every gate PENDING and no evidence
            # at all still printed "landed cleanly" - and the receipt is the
            # audit artefact, the thing someone reads instead of re-deriving.
            verdict = "[ PENDING ]"
            any_caveat = True
        else:
            verdict = f"[ {gstatus.upper()} ]"
            any_caveat = True
        # Wrap the evidence list rather than truncating it. A cut identifier
        # is worse than a bare one: "EV-ANALYZE-signup-email-va..." cannot be
        # matched to the entry that defines it further down this same
        # receipt, so it identifies nothing. Prose still truncates - a cut
        # sentence is still readable.
        head = f"  {gid:<26} {verdict:<18} evidence: "
        lines.extend(_receipt_wrap_ids(head, ev_ids))
    lines.append("")

    # 5. evidence registry - type-specific minimal fields rendered alongside
    # the path (TRC-B1). The dispatch table covers only types with meaningful
    # extras; any future type without an entry renders id+type+path (DD-3 -
    # adding an evidence type to governance/guardrails.yml does not require a
    # renderer change, it just lands as a path-only entry until/unless someone
    # adds an extras tuple here).
    lines.append("Evidence")
    lines.append("--------")
    evs = task.get("evidence") or []
    if not evs:
        lines.append("  (no evidence recorded)")
    else:
        # Column width follows the widest id actually present. A fixed width
        # of 8 shoved every other column off its grid the moment one long
        # generated id appeared.
        # Sized to the widest id present, but CAPPED. One auto-generated id -
        # `EV-ANALYZE-<slug>-<timestamp>` runs to 51 characters - would
        # otherwise set the column for all of them and crush the readable
        # column to nothing. A long id overflows its cell and shifts that one
        # row; every other row keeps its grid, and the words stay legible.
        id_w = min(14, max(8, *(len(str(e.get("id", "?"))) for e in evs
                                if isinstance(e, dict))))
        # An identifier appears with its meaning on first use (the cold-reader
        # strategy). A scenario's meaning is its title, which the spine
        # already holds - so print it rather than making the reader resolve
        # `TRC-B1` from somewhere else.
        titles = {s.get("id"): s.get("title")
                  for s in (task.get("scenarios") or [])
                  if isinstance(s, dict) and s.get("title")}
        # One line per entry, and the readable part first. This used to print a
        # narrow id/type/path row and push the extras onto an indented
        # continuation line - so 28 entries took 44 lines, sixteen of them
        # two-line and twelve one-line, with no row to scan down. The scenario
        # title, the only human-readable content in the block, sat on the
        # continuation line while the widest column held a path derivable from
        # the id for most entries.
        #
        # Column order follows what a reader wants in order: WHAT was proved,
        # HOW strongly, then WHERE to find it. The path is last because it is
        # the first thing worth losing when the line is capped.
        rows = []
        for ev in evs:
            if not isinstance(ev, dict):
                continue
            eid = str(ev.get("id", "?"))
            etype = str(ev.get("type", "?"))
            extras = _RECEIPT_EVIDENCE_EXTRAS.get(etype, ())
            # What this proves, in words. A scenario's title is held in the
            # spine, so print it rather than making the reader resolve the id.
            # What this proves, in words.
            #
            # A scenario's title says it outright, so use the title alone - the
            # spine holds it, and making the reader resolve `TRC-B1` from
            # somewhere else is the defect this column exists to remove.
            #
            # Every other type keeps ALL its declared fields, joined on one
            # line. A human sign-off means nothing without who approved, in
            # what role, and what they decided; a spike conclusion means
            # nothing without the decision and where it went. Those are the
            # type-specific minimal fields, and dropping any of them would lose
            # information rather than noise.
            proves = ""
            scenario = ev.get("scenario")
            if "scenario" in extras and titles.get(scenario):
                # Id AND title. The title is the content and the id is the
                # cross-reference - dropping the id looked tidier and broke the
                # trace for any record whose evidence id does not already carry
                # it. Ids written by the CLI do (`EV-T-TRC-A1`), so it reads as
                # mild repetition there; a hand-written `EV-X` would otherwise
                # have lost its link to the scenario entirely.
                proves = f"{scenario} - {titles[scenario]}"
            else:
                proves = ", ".join(f"{k}: {ev.get(k)}"
                                   for k in extras if ev.get(k) is not None)
            if not proves:
                # No scenario behind it - a baseline, a review, a sweep. The
                # filename is what it is called, so use that rather than
                # leaving the column blank: "mutation-proof-group-A" reads.
                stem = pathlib.PurePosixPath(str(ev.get("path", ""))).stem
                proves = stem.replace("-", " ").replace("_", " ")
            rows.append((eid, etype, proves))

        # Issue-level records - baselines, reviews, sweeps - have no scenario
        # behind them. Grouping them after the per-scenario rows stops the two
        # kinds interleaving in whatever order they were written.
        # Per-scenario records first, then the issue-level ones, so the two
        # kinds do not interleave in whatever order they were written.
        rows.sort(key=lambda r: (not r[0].startswith("EV-T-"), ))
        # The path column is gone. It was the widest thing on the row, it is
        # derivable from the id for most entries, and once the line was capped
        # it rendered as "evidence/gr..." - which looks like information and is
        # not. The id identifies the record; anyone who needs the file can
        # resolve it. Dropping it buys the width back for the readable column.
        # Width maths, spelled out because getting it wrong silently truncates
        # whichever column is last: two spaces of indent, the id, two spaces,
        # the readable column, two spaces, the type. The type width comes from
        # the rows actually present rather than a guessed constant.
        type_w = max((len(r[1]) for r in rows), default=0)
        proves_w = max(4, _RECEIPT_LINE_CAP - 2 - id_w - 2 - 2 - type_w)
        for eid, etype, proves in rows:
            shown = proves if len(proves) <= proves_w else proves[:proves_w - 1] + "\u2026"
            lines.append(_receipt_truncate(
                f"  {eid:<{id_w}}  {shown:<{proves_w}}  {etype}"))
    lines.append("")

    # 5b. follow-ups (rendered only when any exist)
    backfills = task.get("follow_ups") or []
    if backfills:
        lines.append("Follow-ups")
        lines.append("----------")
        for b in backfills:
            if not isinstance(b, dict):
                continue
            bid = b.get("id", "?")
            bstatus = b.get("status", "?")
            bdesc = b.get("description", "")
            marker = ("[ OUTSTANDING ]" if bstatus == "outstanding"
                      else "[ resolved ]")
            lines.append(_receipt_truncate(
                f"  {bid:<8}  {marker:<15} {bdesc}"))
        lines.append("")

    # 6. overall verdict
    lines.append(_RECEIPT_RULE)
    n_owed = sum(1 for b in backfills if isinstance(b, dict)
                 and b.get("status") == "outstanding")
    if not is_landed:
        verdict_line = "Verdict: not yet landed"
    elif any_fail:
        verdict_line = "Verdict: FAILED - does not satisfy its own gates"
    elif n_owed:
        verdict_line = (f"Verdict: landed with caveats - "
                        f"{n_owed} follow-up(s) outstanding")
    elif any_caveat:
        verdict_line = "Verdict: landed with caveats"
    else:
        verdict_line = "Verdict: landed cleanly"
    lines.append(verdict_line)

    return "\n".join(lines)


def cmd_task_receipt(args):
    try:
        task_dir, slug, project_root = _receipt_resolve_task_dir(args)
    except CompassError as exc:
        sys.stderr.write(f"{exc}\n")
        return 1
    task = normalize_spine(load_yaml(os.path.join(task_dir, "task.yml")) or {})
    approach_path = artifact_path(task_dir, "delivery-approach.md")
    route_readings = _receipt_parse_route_md_readings(approach_path)
    gate_requirements = _receipt_gate_requirements(project_root)
    print(_receipt_render(task, slug, route_readings, gate_requirements,
                          _receipt_parse_topology_override(approach_path)))
    return 0


# --- command: adr ------------------------------------------------------------
# `compass adr new <slug>` creates a sequentially-numbered ADR file under
# architecture/decisions/ and registers it in the README.md index.
#
# Inv-7: sequential within a tree at invocation time; concurrent worktrees may
#         collide and surface the conflict as a normal git merge conflict (DD-8).
# Inv-8: the directory is created if absent.

_ADR_TEMPLATE = """\
---
id: {id}
title: {title}
status: proposed
date: {date}
supersedes: ''
superseded_by: ''
---

## Context

<!-- Describe the situation that necessitated this decision. -->

## Decision

<!-- State the decision clearly and concisely. -->

## Alternatives considered

<!-- List alternatives that were evaluated and why they were not chosen. -->

## Consequences

<!-- Describe the positive and negative consequences of this decision. -->

## References

<!-- Link to ADRs, issues, or documents that influenced this decision. -->
"""

_ADR_README_HEADER = """\
# Architecture Decision Records

This directory contains the project's Architecture Decision Records (ADRs).

Each ADR captures one significant architectural decision: its context, the
choice made, the alternatives considered, and the consequences.

## Numbering

ADRs are numbered sequentially.  `compass adr new <slug>` assigns the next
available number so the index is always in creation order.  When two worktrees
create ADRs concurrently, a git merge conflict on this README signals the
collision; resolve by renumbering one side.

## Index

| ID | Title | Status |
|---|---|---|
"""


def _adr_readme_row(adr_id: str, title: str, status: str, path: str) -> str:
    return f"| {adr_id} | {title} | {status} |\n"


def cmd_adr_new(args):
    """Create a new numbered ADR file and register it in the decisions README."""
    slug = args.slug
    if not slug:
        raise CompassError("compass adr new requires a slug argument")
    # Sanitise slug: lowercase, replace spaces/underscores with hyphens
    slug = slug.strip().lower().replace(" ", "-").replace("_", "-")

    # Find the architecture/decisions directory
    proj = find_upwards(os.getcwd(), os.path.join("architecture", "decisions"))
    if proj:
        decisions_dir = os.path.join(proj, "architecture", "decisions")
    else:
        # Not found walking up - create relative to cwd
        decisions_dir = os.path.join(os.getcwd(), "architecture", "decisions")

    os.makedirs(decisions_dir, exist_ok=True)

    # Count existing ADR-*.md files to determine the next number
    existing = sorted(
        f for f in os.listdir(decisions_dir)
        if f.startswith("ADR-") and f.endswith(".md")
           and f != "ADR-template.md"
    )
    next_num = len(existing) + 1
    num_str = f"{next_num:03d}"
    adr_id = f"ADR-{num_str}"
    filename = f"ADR-{num_str}-{slug}.md"
    full_path = os.path.join(decisions_dir, filename)

    if os.path.exists(full_path):
        raise CompassError(
            f"{full_path} already exists. If you are in a concurrent worktree, "
            f"this is expected - rename one side when the streams integrate."
        )

    title_words = slug.replace("-", " ").title()
    content = _ADR_TEMPLATE.format(
        id=adr_id,
        title=title_words,
        date=datetime.date.today().isoformat(),
    )
    with open(full_path, "w", encoding="utf-8") as fh:
        fh.write(content)

    # Update README.md index
    readme_path = os.path.join(decisions_dir, "README.md")
    if os.path.exists(readme_path):
        readme_text = open(readme_path, encoding="utf-8").read()
    else:
        readme_text = _ADR_README_HEADER

    row = _adr_readme_row(adr_id, title_words, "proposed", filename)
    if adr_id not in readme_text:
        with open(readme_path, "a", encoding="utf-8") as fh:
            # If the file was just created (header only), the table is already
            # there; append row.  If we appended the header we need a trailing
            # newline before the row.
            fh.write(row)

    # The caveat is split across two lines: one 129-character line is not a
    # line a person reads, and this one is worth reading.
    from compass_pkg.terminal import say

    return say(args, f"compass adr new: created {full_path}",
               detail=[f"registered in {readme_path}",
                       "NOTE: if another worktree creates ADRs at the same "
                       "time, the",
                       "      numbers will collide - renumber when the "
                       "streams integrate."],
               path=full_path, index=readme_path)
