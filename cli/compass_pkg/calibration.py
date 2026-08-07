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
# DEPENDENCY: PyYAML (`pip install pyyaml`). It is the only dependency; the
# rest is the Python 3 standard library. If PyYAML is missing the CLI says so
# clearly and exits.
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
try:
    import yaml
except ImportError:
    sys.stderr.write(
        "compass: PyYAML is required but not installed.\n"
        "  Install it with:  pip install pyyaml\n"
        "  (It is the CLI's only dependency.)\n"
    )
    sys.exit(3)


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
from compass_pkg.core import CompassError, find_compass_dir, find_governance, load_task, load_yaml, resolve_task_dir, save_task, normalize_spine



# --- command: calibration ---------------------------------------------------
# The Needle's feedback loop. The Needle reads context - judgement - and a
# framework about right-sizing process owes an answer to "is the right-sizing
# any good?" `compass calibration` is that answer: it reads the re-frame log
# across every task and reports whether the Needle is systematically over- or
# under-sizing. Read-only; it advises, it does not gate.

def _load_scope_bloat_phrases():
    """Load scope_bloat_phrases from signals.yml at runtime.

    Patterns are never hardcoded in the CLI - always read from the
    governance file. Returns an empty list if signals.yml is absent or
    unreadable (graceful degradation).
    """
    try:
        gov = find_governance()
        sig_path = os.path.join(gov, "signals.yml")
        if not os.path.isfile(sig_path):
            return []
        sig = load_yaml(sig_path)
        return list(sig.get("scope_bloat_phrases") or [])
    except CompassError:
        return []


def _find_reframe_debt(tasks, work):
    """Return a list of absorbed mis-frame records.

    For each issue, scan its devlog.md for scope_bloat_phrases.  An issue
    qualifies as 'reframe debt' when:
      - at least one scope-bloat phrase appears as the start of a devlog line
        (column-0 anchor - same rule as the stop-hook, for consistency), AND
      - task.yml.reframes has no entry whose date is >= the date of the
        matching devlog line.

    This function is strictly READ-ONLY; it never writes to any
    task.yml or any other file.
    Patterns are supplied by the caller from signals.yml.
    """
    phrases = _load_scope_bloat_phrases()
    if not phrases:
        return []

    debts = []
    for slug, task in tasks:
        devlog_path = os.path.join(work, slug, "devlog.md")
        if not os.path.isfile(devlog_path):
            continue

        try:
            with open(devlog_path, "r", encoding="utf-8") as fh:
                devlog_lines = fh.readlines()
        except OSError:
            continue

        # Latest reframe date for this task
        reframes = task.get("reassessments") or []
        reframe_dates = sorted(
            r.get("date", "") for r in reframes if r.get("date")
        )
        latest_reframe_date = reframe_dates[-1] if reframe_dates else ""

        # Match a phrase as a top-level statement (not nested in
        # quotes/indentation).  The phrase must appear at column 0 OR
        # immediately after an optional YYYY-MM-DD[: ] date prefix.
        # Lines starting with whitespace are skipped (indented/quoted context
        # must not fire - consistency with the stop-hook's TRC-X3 rule).
        import re as _re
        _DATE_PREFIX_PAT = r'^(?:\d{4}-\d{2}-\d{2}[: ]+)?'

        for phrase in phrases:
            compiled = _re.compile(_DATE_PREFIX_PAT + _re.escape(phrase))
            for raw_line in devlog_lines:
                line = raw_line.rstrip("\n")
                # Skip lines with leading whitespace (quoted/indented context)
                if line and line[0].isspace():
                    continue
                if not compiled.match(line):
                    continue
                # Extract a date from the line start (YYYY-MM-DD prefix, if any)
                line_date = ""
                m = _re.match(r'^(\d{4}-\d{2}-\d{2})', line)
                if m:
                    line_date = m.group(1)
                # Suppression: a reframe filed after (or on) the line date
                if latest_reframe_date:
                    if not line_date:
                        # No date on the devlog line → can't order; suppress
                        break
                    if latest_reframe_date >= line_date:
                        break  # reframe filed after or on the bloat line
                # Record the debt
                debts.append({
                    "task": slug,
                    "devlog_line": line,
                    "phrase": phrase,
                })
                break  # one match per phrase per task is enough

    return debts


def _load_friction_threshold():
    """Load friction.recurrence_threshold from signals.yml at runtime.

    Mirrors _load_scope_bloat_phrases (never hardcode the value in
    the CLI - read it from the governance file). Defaults to 2 when signals.yml
    is absent or the block is unset (ADR-006: clean no-op for non-adopters; and
    2 mirrors `calibration`'s own >=2 up/down-sizing thresholds).
    """
    default = 2
    try:
        gov = find_governance()
        sig_path = os.path.join(gov, "signals.yml")
        if not os.path.isfile(sig_path):
            return default
        sig = load_yaml(sig_path)
        fr = sig.get("friction") or {}
        n = fr.get("recurrence_threshold", default)
        n = int(n)
        return n if n >= 1 else default
    except (CompassError, ValueError, TypeError):
        return default


def _aggregate_friction(tasks, threshold):
    """Aggregate the `friction:` lists across issues into recurring clusters.

    Grouping is by case/whitespace-normalised `proposed_change` (clarifications
    Q2 - exact-normalised, never semantic: the aggregator is mechanism, so it
    must be reproducible, ADR-001). A cluster is `recurring` when it is proposed
    by at least `threshold` distinct issues. Pure function; reads nothing, writes
    nothing.
    """
    import re as _re

    def _norm(s):
        return _re.sub(r"\s+", " ", (s or "").strip()).lower()

    clusters = {}
    by_category = {}
    n_with_friction = 0
    for slug, t in tasks:
        fr = t.get("friction") or []
        if fr:
            n_with_friction += 1
        for e in fr:
            if not isinstance(e, dict):
                continue
            cat = e.get("category", "other")
            by_category[cat] = by_category.get(cat, 0) + 1
            pc = e.get("proposed_change") or ""
            key = _norm(pc)
            if not key:
                continue  # nothing to cluster on; still counted by category
            c = clusters.setdefault(
                key, {"proposed_change": pc.strip(), "categories": set(),
                      "tasks": set()})
            c["categories"].add(cat)
            c["tasks"].add(slug)

    recurring, below = [], []
    for c in clusters.values():
        item = {
            "proposed_change": c["proposed_change"],
            "categories": sorted(c["categories"]),
            "tasks": sorted(c["tasks"]),
            "count": len(c["tasks"]),
        }
        (recurring if item["count"] >= threshold else below).append(item)
    recurring.sort(key=lambda x: (-x["count"], x["proposed_change"]))
    below.sort(key=lambda x: x["proposed_change"])
    return {
        "threshold": threshold,
        "tasks_with_friction": n_with_friction,
        "by_category": dict(sorted(by_category.items(), key=lambda kv: -kv[1])),
        "recurring": recurring,
        "below_threshold": below,
    }


def _cmd_calibration_friction(args, tasks):
    """The `compass calibration --friction` view. Read-only; exit 0 always
    (Inv: friction advises, never gates - like rework-scan and flow)."""
    threshold = _load_friction_threshold()
    agg = _aggregate_friction(tasks, threshold)

    fmt = getattr(args, "format", "markdown") or "markdown"
    if fmt == "json":
        print(json.dumps(agg, indent=2))
        return 0

    print(f"compass retro --friction - {agg['tasks_with_friction']} "
          f"issue(s) with recorded friction\n")
    if agg["tasks_with_friction"] == 0:
        print("No friction recorded - nothing to aggregate. Either Compass is "
              "staying out of the way, or\nthere is not enough history yet.")
        return 0

    print("Friction by category:")
    for cat, n in agg["by_category"].items():
        print(f"  {cat:<16}: {n}")
    print()
    print(f"Recurring friction (>= {threshold} issues) - candidate framework "
          f"changes:")
    if agg["recurring"]:
        for c in agg["recurring"]:
            cats = ", ".join(c["categories"])
            print(f"  [{cats}] {c['proposed_change']}")
            print(f"      {c['count']} issues: {', '.join(c['tasks'])}")
    else:
        print("  (none yet - no proposed change has recurred across enough "
              "issues)")
    if agg["below_threshold"]:
        print()
        print(f"Below threshold (not yet a trend): "
              f"{len(agg['below_threshold'])} item(s)")
    print()
    print("Advisory only. Claude or a human reads these and drafts targeted "
          "changes to\ngovernance/ or the routes - the loop never edits "
          "governance itself (ADR-001).")
    return 0


def derive_friction(slug, task, work):
    """Assemble the `source: derived` friction entries for one issue from signals
    the CLI already computes - recorded reframes and absorbed reframe-debt.

    A reframe is a Frame that mis-read the terrain; reframe-debt is a mis-frame
    absorbed without one being filed. Both are friction by definition. Pure: it
    reads task.yml + devlog (via _find_reframe_debt) and writes nothing. Derived
    entries carry no `proposed_change` - a reframe does not propose a specific
    governance change; it is the recurrence of *human*-proposed changes that the
    aggregator clusters on.
    """
    entries = []
    for rf in (task.get("reassessments") or []):
        if not isinstance(rf, dict):
            continue
        fr = rf.get("from_route", "?")
        to = rf.get("to_route", "?")
        reason = (rf.get("reason") or "").strip()
        obs = f"reframe {fr} -> {to}"
        if reason:
            obs += f": {reason}"
        entries.append({
            "phase": "frame",
            "category": "mis-route",
            "observation": obs,
            "source": "derived",
        })
    for d in _find_reframe_debt([(slug, task)], work):
        entries.append({
            "phase": "frame",
            "category": "mis-route",
            "observation": ("absorbed scope-bloat without a reframe: "
                            f"{d['devlog_line']}"),
            "source": "derived",
        })
    return entries


def cmd_friction_capture(args):
    """Private entry point for `compass _friction-capture --internal`, called by
    the Land procedure. Assembles the issue's `friction:` list from derived
    signals plus an optional human note and writes it into the issue spine.

    It writes ONLY the friction section - never a follow-up or a gate. Friction
    is a strategy-class signal and must never become something that blocks Land
    (ADR-002). The derivation is mechanism; the `--note` is the only
    judgement input, supplied human-side (ADR-001).
    """
    if not getattr(args, "internal", False):
        raise CompassError(
            "compass _friction-capture: the --internal flag is required - this "
            "is an in-framework entry point called by the Land procedure, not a "
            "public verb.")
    task_dir = resolve_task_dir(getattr(args, "task", None))
    task, path = load_task(task_dir)
    slug = os.path.basename(os.path.normpath(task_dir))
    work = os.path.join(find_compass_dir(), "work")

    entries = derive_friction(slug, task, work)

    note = getattr(args, "note", None)
    if note:
        human = {
            "phase": getattr(args, "note_phase", None) or None,
            "category": getattr(args, "note_category", None) or "other",
            "observation": note,
            "source": "human",
        }
        if human["phase"] is None:
            del human["phase"]
        entries.append(human)

    # Merge rather than replace. Derived entries are a pure function of the
    # task's current state, so they are recomputed and replace the previous
    # derived set; human notes are observations that cannot be recomputed, so
    # they accumulate. An earlier version assigned the whole list, which meant a
    # second run silently discarded every note the first had recorded.
    existing = task.get("friction") or []
    kept_human = [e for e in existing if e.get("source") == "human"]
    new_human = [e for e in entries if e.get("source") == "human"]
    seen = {e.get("observation") for e in kept_human}
    kept_human += [e for e in new_human if e.get("observation") not in seen]
    entries = [e for e in entries if e.get("source") != "human"] + kept_human

    if entries:
        task["friction"] = entries
        save_task(task, path)
        print(f"compass _friction-capture: recorded {len(entries)} friction "
              f"entry(ies) -> {path}")
        for e in entries:
            print(f"  [{e['source']}/{e['category']}] {e.get('observation', '')}")
    else:
        # Recording nothing is a valid, common outcome (TRC-A5). Leave the key
        # absent so a task that hit no friction stays a clean no-op (ADR-006).
        print("compass _friction-capture: no friction derived and no note "
              "supplied - nothing recorded (a valid, common outcome).")
    return 0



# --- process-impact telemetry ------------------------------------------------
# "Earn the gate": does the ceremony a route buys correlate with shipping faster
# or breaking less? Computed from task.yml alone - `created` and
# `land_timestamp` are already in the spine, so no git call is needed and the
# report is deterministic by construction rather than by discipline.
#
# The hard part is not the arithmetic, it is refusing to report what the data
# cannot support. A project with no hotfixes has a change-fail rate that is
# UNMEASURABLE, not zero; printing "0%" would read as excellent stability and
# mean silence.

IMPACT_SAMPLE_FLOOR = 20   # landed tasks before any correlation is reported
IMPACT_GROUP_FLOOR = 3     # tasks in a route group before that group is shown


def _impact_days(created, landed):
    """Whole days between an issue's `created` date and its `land_timestamp`."""
    if not created or not landed:
        return None
    try:
        c = datetime.date.fromisoformat(str(created)[:10])
        l = datetime.date.fromisoformat(str(landed)[:10])
    except ValueError:
        return None
    return max((l - c).days, 0)


def _median(xs):
    xs = sorted(xs)
    if not xs:
        return None
    m = len(xs) // 2
    return float(xs[m]) if len(xs) % 2 else (xs[m - 1] + xs[m]) / 2.0


def compute_impact(tasks):
    """issues: [(slug, data)]. Returns a dict; pure, no I/O, no clock."""
    landed = [(s, d) for s, d in tasks if (d or {}).get("status") == "landed"]
    hotfixes = [(s, d) for s, d in landed if d.get("delivery_approach") == "hotfix"]
    delivery = [(s, d) for s, d in landed if d.get("delivery_approach") != "hotfix"]

    lead, excluded, by_route = [], 0, {}
    for slug, d in delivery:
        days = _impact_days(d.get("created"), d.get("land_timestamp"))
        if days is None:
            excluded += 1
            continue
        lead.append(days)
        route = d.get("delivery_approach", "?")
        g = by_route.setdefault(route, {"n": 0, "lead": [], "gates": set()})
        g["n"] += 1
        g["lead"].append(days)
        g["gates"].add(len(d.get("gates") or []))

    dates = sorted(str(d.get("land_timestamp"))[:10] for _, d in landed
                   if d.get("land_timestamp"))
    span_days = 0
    if len(dates) >= 2:
        try:
            span_days = (datetime.date.fromisoformat(dates[-1])
                         - datetime.date.fromisoformat(dates[0])).days
        except ValueError:
            span_days = 0

    declared = [(s, d) for s, d in hotfixes if d.get("repairs")]
    delivery_slugs = {s for s, _ in delivery}

    # Count DISTINCT delivery tasks that were repaired - not the number of
    # hotfixes that named one. Three hotfixes against one task is one failed
    # task, not three; the earlier formula reported 150%.
    repaired = sorted({str(d["repairs"]) for _, d in declared
                       if str(d["repairs"]) in delivery_slugs})
    unknown_targets = sorted({str(d["repairs"]) for _, d in declared
                              if str(d["repairs"]) not in delivery_slugs})

    # None, never 0.0, whenever the number would be a lie. That is not only the
    # "no hotfixes" case: hotfixes that declare no `repairs:` target produce a
    # 0% that means "nobody said what they were fixing", which reads as perfect
    # stability. Both are unmeasurable, and both must render as a sentence.
    rate = None
    if declared and delivery:
        rate = 100.0 * len(repaired) / len(delivery)

    restore = [x for x in (_impact_days(d.get("created"), d.get("land_timestamp"))
                           for _, d in hotfixes) if x is not None]

    return {
        "n_landed": len(landed),
        "n_delivery": len(delivery),
        "lead_median": _median(lead),
        "lead_excluded": excluded,
        "span_days": span_days,
        "lands_per_week": (round(len(landed) / (span_days / 7.0), 2)
                           if span_days >= 7 else None),
        "hotfixes": len(hotfixes),
        "hotfixes_declared": len(declared),
        "repaired": repaired,
        "unknown_targets": unknown_targets,
        "change_fail_rate": rate,
        "restore_median": _median(restore),
        "by_route": by_route,
        "withheld": (None if len(landed) >= IMPACT_SAMPLE_FLOOR else
                     "%d landed issue(s); %d required"
                     % (len(landed), IMPACT_SAMPLE_FLOOR)),
    }


def render_impact(r):
    out = ["compass retro --impact - process signal (advisory)", ""]
    if not r["n_landed"]:
        out.append("  Nothing to measure yet - no landed issues on record.")
        return "\n".join(out)

    out.append("  lead time     median %s day(s) over %d issue(s)%s"
               % (r["lead_median"], r["n_delivery"],
                  "" if not r["lead_excluded"]
                  else ", %d excluded (missing a timestamp)" % r["lead_excluded"]))
    out.append("  land freq     %s per week, over a span of %d day(s)"
               % (r["lands_per_week"] if r["lands_per_week"] is not None
                  else "not computable (span under a week)", r["span_days"]))

    if r["change_fail_rate"] is None:
        # NOT "0%". Gate on the RATE, not on hotfix presence: a project with
        # hotfixes that declare no target is just as unmeasurable, and gating on
        # presence crashed on a hotfix-only history.
        if not r["hotfixes"]:
            why = "no hotfixes recorded"
        elif not r["hotfixes_declared"]:
            why = ("%d hotfix(es) recorded, none declaring a `repairs:` target"
                   % r["hotfixes"])
        else:
            why = "no delivery issues to measure against"
        out.append("  change-fail   %s, so change-fail cannot be measured" % why)
        if r["hotfixes"]:
            out.append("                restore time  median %s day(s) across "
                       "%d hotfix(es)" % (r["restore_median"], r["hotfixes"]))
    else:
        cov = ("%d of %d hotfix(es) declared a `repairs:` target"
               % (r["hotfixes_declared"], r["hotfixes"]))
        out.append("  change-fail   %.1f%% of delivery issues were later repaired "
                   "(%s)" % (r["change_fail_rate"], cov))
        if r["repaired"]:
            out.append("                repaired: %s" % ", ".join(r["repaired"]))
        if r["unknown_targets"]:
            out.append("                %d `repairs:` target(s) name no landed "
                       "delivery issue and were not counted: %s"
                       % (len(r["unknown_targets"]),
                          ", ".join(r["unknown_targets"])))
        out.append("  restore time  median %s day(s) across %d hotfix(es)"
                   % (r["restore_median"], r["hotfixes"]))

    out.append("")
    out.append("  by route:")
    for route, g in sorted(r["by_route"].items()):
        gates = ", ".join(str(x) for x in sorted(g["gates"]))
        if g["n"] < IMPACT_GROUP_FLOOR:
            out.append("    %-12s n=%d  (under %d - not summarised)  gates=%s"
                       % (route, g["n"], IMPACT_GROUP_FLOOR, gates))
        else:
            out.append("    %-12s n=%d  lead median %s day(s)  gates=%s"
                       % (route, g["n"], _median(g["lead"]), gates))

    out.append("")
    if r["withheld"]:
        out.append("  CORRELATIONS WITHHELD - %s." % r["withheld"])
        out.append("  Below that sample any correlation between route, gate count")
        out.append("  and outcome is noise wearing a number.")
    else:
        out.append("  Read the by-route figures as a hypothesis to test, not a")
        out.append("  verdict. This is single-project observational data: the")
        out.append("  variables are not controlled, and a heavier route is chosen")
        out.append("  BECAUSE work looks riskier, so slower lead times on heavy")
        out.append("  routes may reflect the work rather than the ceremony.")
    return "\n".join(out)


def cmd_calibration(args):
    if getattr(args, "impact", False):
        return _cmd_calibration_impact(args)

    compass_dir = find_compass_dir()
    work = os.path.join(compass_dir, "work")
    weights = {}
    try:
        policy = load_yaml(os.path.join(find_governance(), "routing-policy.yml"))
        weights = {r: s.get("weight", 0)
                   for r, s in (policy.get("route_shapes") or {}).items()}
    except CompassError:
        pass

    tasks = []
    if os.path.isdir(work):
        for d in sorted(os.listdir(work)):
            tp = os.path.join(work, d, "task.yml")
            if os.path.isfile(tp):
                try:
                    tasks.append((d, normalize_spine(load_yaml(tp))))
                except CompassError:
                    pass

    # --- friction view (TRC-B*) - a flag on calibration, not a new verb.
    # Read-only, exit 0 always; handles the empty corpus gracefully.
    if getattr(args, "friction", False):
        return _cmd_calibration_friction(args, tasks)

    if not tasks:
        print("compass retro: no issues under .compass/work/ yet - "
              "nothing to calibrate against.")
        return 0

    dist, no_route = {}, []
    for slug, t in tasks:
        r = t.get("delivery_approach")
        if r:
            dist[r] = dist.get(r, 0) + 1
        else:
            no_route.append(slug)

    reframed_tasks, total = 0, 0
    ups = downs = sideways = 0
    transitions = {}
    for slug, t in tasks:
        rfs = t.get("reassessments") or []
        if rfs:
            reframed_tasks += 1
        for rf in rfs:
            total += 1
            fr, to = rf.get("from_route"), rf.get("to_route")
            transitions[f"{fr} -> {to}"] = transitions.get(f"{fr} -> {to}", 0) + 1
            wf, wt = weights.get(fr, 0), weights.get(to, 0)
            if wt > wf:
                ups += 1
            elif wt < wf:
                downs += 1
            else:
                sideways += 1

    print(f"compass retro - {len(tasks)} issue(s) under .compass/work/\n")
    print("Route distribution:")
    for r in sorted(dist, key=lambda x: weights.get(x, 99)):
        print(f"  {r:<12}: {dist[r]}")
    if no_route:
        print(f"  (no route)  : {len(no_route)}  <- Frame did not complete: "
              f"{', '.join(no_route)}")
    print()
    pct = round(100 * reframed_tasks / len(tasks))
    print("Re-framing:")
    print(f"  issues that re-framed : {reframed_tasks} of {len(tasks)} ({pct}%)")
    print(f"  total re-frames      : {total}")
    if total:
        print("  direction:")
        print(f"    up   (Needle under-sized) : {ups}")
        print(f"    down (Needle over-sized)  : {downs}")
        if sideways:
            print(f"    sideways                  : {sideways}")
        print("  transitions:")
        for k, v in sorted(transitions.items(), key=lambda x: -x[1]):
            print(f"    {k} : {v}")
    print()
    print("Signal:")
    if total == 0:
        print("  No re-frames recorded - either routing is well-calibrated, or")
        print("  there is not enough history yet. Revisit after more issues.")
    elif ups >= 2 and ups > downs * 2:
        print(f"  {ups} up-reframes vs {downs} down - a lean toward UNDER-sizing.")
        print("  Triage is reading size or risk low. Tune routing-policy.yml")
        print("  `default_shapes`, or sharpen the sizing rubric in the")
        print("  delivery-approach reference docs.")
    elif downs >= 2 and downs > ups * 2:
        print(f"  {downs} down-reframes vs {ups} up - a lean toward OVER-sizing.")
        print("  The Needle is reading risk high; the routes may be heavier")
        print("  than the work warrants. Review routing-policy.yml.")
    else:
        print(f"  {ups} up / {downs} down - roughly balanced, re-frame rate "
              f"{pct}%.")
        print("  Routing looks reasonably calibrated; keep watching the trend.")

    # --- Reframe debt (TRC-C5) -----------------------------------------------
    # Read devlogs for scope-bloat signals that were absorbed without a reframe.
    # Strictly read-only - no task.yml is written here.
    # Patterns loaded from signals.yml at runtime (never hardcoded).
    # Inv-4: advisory only - this section reports, never gates.
    debts = _find_reframe_debt(tasks, work)
    if debts:
        print()
        print("Reframe debt - absorbed mis-frames, signal lost:")
        print("  Each entry below is an issue where a scope-bloat signal was")
        print("  detected in devlog.md but no reframe was filed afterwards.")
        print("  These are missed calibration signals. File a reframe retroactively")
        print("  with: /compass:triage --reassess --reason \"<why scope grew>\"")
        print()
        for d in debts:
            print(f"  issue    : {d['task']}")
            print(f"  signal  : {d['devlog_line']!r}")
            print()
    return 0


def _cmd_calibration_impact(args):
    """compass calibration --impact. Advisory: always exits 0, writes nothing."""
    try:
        work = os.path.join(find_compass_dir(), "work")
    except CompassError:
        work = ".compass/work"
    tasks = []
    if os.path.isdir(work):
        for slug in sorted(os.listdir(work)):
            path = os.path.join(work, slug, "task.yml")
            if os.path.isfile(path):
                try:
                    tasks.append((slug, normalize_spine(load_yaml(path))))
                except CompassError:
                    continue
    print(render_impact(compute_impact(tasks)))
    return 0
