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
from compass_pkg.checks import _spec_sha256
from compass_pkg.core import CompassError, find_upwards, load_yaml, now_iso, resolve_task_dir
from compass_pkg.tdd import _read_config, _run_test



# --- command: bdd extract ----------------------------------------------------
# Lifts the Gherkin out of a task's spec.feature.md into a plain .feature file a
# real BDD runner (pytest-bdd, cucumber-js, behave, godog) can execute. This is
# what turns the scenario-to-test link from a convention an engineer maintains
# into a fact a runner establishes.
#
# The four functions below are deliberately kept as one contiguous, separable
# block so they can be lifted into their own module later without untangling
# anything.

# A Compass scenario in spec.feature.md always looks like this:
#
#   ### Scenario: <title>
#   <!-- traceability id: TRC-A1 · serves: INT-1 -->
#
#   ```gherkin
#   Scenario: <title>
#     Given ...
#   ```
#
# THE ANCHOR IS THE TRACEABILITY COMMENT, NOT THE FENCE. Compass documents
# contain illustrative Gherkin that is not an acceptance criterion (a proposal
# showing what a scenario looks like, this very comment block). Extracting every
# ```gherkin fence would turn those illustrations into scenarios. Requiring the
# traceability comment means only real, id-carrying scenarios are extracted.
_TRC_COMMENT_RE = re.compile(
    r"<!--\s*traceability id:\s*(?P<trc>TRC-[A-Za-z0-9_]+)\b.*?-->", re.S)
_SCENARIO_HEADING_RE = re.compile(r"^###\s+Scenario:\s*(?P<title>.+?)\s*$")
_FENCE_OPEN_RE = re.compile(r"^\s*```+\s*gherkin\s*$", re.I)
_FENCE_CLOSE_RE = re.compile(r"^\s*```+\s*$")
_GHERKIN_STEP_RE = re.compile(
    r"^\s*(Given|When|Then|And|But|\*)\s+\S", re.I)
_GHERKIN_SCENARIO_RE = re.compile(r"^\s*Scenario:\s*(?P<title>.+?)\s*$")


class ParsedScenario(object):
    """One extracted scenario, with enough context to report a good error."""

    __slots__ = ("trc_id", "heading_title", "fence_title", "steps", "line_no")

    def __init__(self, trc_id, heading_title, fence_title, steps, line_no):
        self.trc_id = trc_id
        self.heading_title = heading_title
        self.fence_title = fence_title
        self.steps = steps
        self.line_no = line_no


def scan_spec_markdown(text):
    """Parse spec.feature.md into ParsedScenario records, in document order.

    Only a gherkin fence introduced by a `traceability id:` comment is picked
    up; everything else in the document is prose. Returns [] when the document
    contains no such fence - the caller decides whether that is an error.
    """
    lines = text.splitlines()
    out = []
    pending_heading = None       # most recent "### Scenario:" title
    pending_trc = None           # most recent traceability id
    pending_line = 0

    i = 0
    while i < len(lines):
        line = lines[i]

        m = _SCENARIO_HEADING_RE.match(line)
        if m:
            pending_heading = m.group("title")
            pending_line = i + 1
            i += 1
            continue

        m = _TRC_COMMENT_RE.search(line)
        if m:
            pending_trc = m.group("trc")
            i += 1
            continue

        if _FENCE_OPEN_RE.match(line):
            body = []
            i += 1
            while i < len(lines) and not _FENCE_CLOSE_RE.match(lines[i]):
                body.append(lines[i])
                i += 1
            i += 1                                  # step past the closing fence
            if pending_trc is None:
                # An illustration, not a scenario. Deliberately ignored - see
                # the note on the anchor above.
                pending_heading = None
                continue
            fence_title = None
            steps = []
            for b in body:
                sm = _GHERKIN_SCENARIO_RE.match(b)
                if sm and fence_title is None:
                    fence_title = sm.group("title")
                    continue
                if b.strip():
                    steps.append(b.strip())
            out.append(ParsedScenario(
                trc_id=pending_trc,
                heading_title=pending_heading,
                fence_title=fence_title,
                steps=steps,
                line_no=pending_line or i,
            ))
            pending_trc = None
            pending_heading = None
            continue

        i += 1

    return out


def validate_scenarios(scenarios, spec_path):
    """Return a list of human-readable problems. Empty list means valid.

    Collects rather than raises so a spec with three problems reports the first
    with its location, instead of failing on whichever one the parser reached.
    """
    problems = []
    if not scenarios:
        problems.append(
            "%s contains no Gherkin scenarios. A scenario is a '### Scenario:' "
            "heading, a '<!-- traceability id: TRC-... -->' comment, and a "
            "```gherkin fence - the comment is what marks a fence as a real "
            "scenario rather than an illustration." % spec_path)
        return problems

    seen = {}
    for s in scenarios:
        where = "%s:%d" % (spec_path, s.line_no)
        if s.fence_title is None:
            problems.append(
                "%s: %s - the gherkin fence has no 'Scenario:' line."
                % (where, s.trc_id))
            continue
        if s.heading_title is not None and s.heading_title != s.fence_title:
            problems.append(
                "%s: %s - the title drifts between the heading and the fence.\n"
                "  heading: %s\n  fence  : %s"
                % (where, s.trc_id, s.heading_title, s.fence_title))
        if not s.steps:
            problems.append(
                "%s: %s - the scenario has no steps." % (where, s.trc_id))
        else:
            bad = [st for st in s.steps if not _GHERKIN_STEP_RE.match(st)]
            if bad:
                problems.append(
                    "%s: %s - not valid Gherkin; a step must start with Given, "
                    "When, Then, And, or But.\n  offending line: %s"
                    % (where, s.trc_id, bad[0]))
        if s.trc_id in seen:
            problems.append(
                "%s: %s is used twice (also at line %d)."
                % (where, s.trc_id, seen[s.trc_id]))
        seen[s.trc_id] = s.line_no
    return problems


def render_feature(slug, scenarios, spec_rel_path):
    """Render the .feature text. Pure: no clock, no absolute paths, no randomness.

    Determinism is the point - the output is diffable and committable, and
    `compass bdd extract` run twice over an unchanged spec produces
    byte-identical bytes.
    """
    lines = [
        "# Derived from %s by `compass bdd extract`." % spec_rel_path,
        "# Do not hand-edit - your edits are overwritten on the next extract.",
        "# Edit the source spec instead.",
        "",
        "Feature: %s" % slug,
        "",
    ]
    for s in scenarios:
        lines.append("  @%s" % s.trc_id)
        lines.append("  Scenario: %s" % s.fence_title)
        for step in s.steps:
            lines.append("    %s" % step)
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def atomic_write(path, text):
    """Write via a temp file in the destination directory, then rename.

    A malformed spec must leave no partial output behind, and a crash mid-write
    must not corrupt a file a runner may already be reading. Rename within one
    directory is atomic on POSIX; writing in place is not.
    """
    directory = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".compass-bdd-", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _bdd_out_path(args, task_dir, slug):
    """Resolve where the .feature goes: --out, then config, then the task dir.

    The task directory is the zero-config default so the verb works before a
    project has edited anything (ADR-006); `project.bdd_features_dir` exists for
    adopters whose runner expects a conventional features/ directory.
    """
    explicit = getattr(args, "out", None)
    if explicit:
        return explicit
    proj = _read_config(task_dir).get("project") or {}
    features_dir = proj.get("bdd_features_dir")
    if features_dir:
        root = find_upwards(task_dir, ".compass") or task_dir
        if not os.path.isabs(features_dir):
            features_dir = os.path.join(root, features_dir)
        return os.path.join(features_dir, "%s.feature" % slug)
    return os.path.join(task_dir, "spec.feature")


_ZERO_COLLECTED = re.compile(
    r"\b0\s+(scenarios?|tests?|features?|steps?)\b|no tests ran|"
    r"collected 0 items|0 scenarios \(", re.I)
_SOME_COLLECTED = re.compile(
    r"\b([1-9]\d*)\s+(scenarios?|tests?)\b|collected ([1-9]\d*) item", re.I)


def _probe_collected(out, runner=""):
    """Did the tag actually bind to at least one scenario?

    Exit code alone is not enough, and believing it was a real defect: pytest
    exits 5 on an empty collection, but **cucumber-js and behave exit 0** when a
    tag filter matches nothing. A probe that trusted the exit code reported
    every scenario as bound for two of the four shipped adapters - a check that
    verified nothing while saying it had.

    So read the count the runner prints. An explicit zero is decisive; otherwise
    require a positive count. Silence is treated as "not collected", because the
    failure that matters here is a false pass.
    """
    # behave is a special case, and getting it wrong broke a correct project.
    # Its --dry-run summary ALWAYS opens "0 features passed, 0 failed, ..."
    # regardless of whether the tag matched, so the generic zero-match below
    # reads every behave probe as unbound. What distinguishes the two is the
    # `untested` count: a matched tag leaves scenarios untested (dry run), a
    # non-matching one leaves them merely skipped.
    if "behave" in (runner or "").lower():
        m = re.search(r"(\d+)\s+untested", out)
        return bool(m and int(m.group(1)) > 0)
    if _ZERO_COLLECTED.search(out):
        return False
    m = _SOME_COLLECTED.search(out)
    return bool(m and any(g and int(g) > 0 for g in m.groups()))


def _bdd_tag_selector(runner, command):
    """How to ask this runner to select one scenario tag, or None if unknown.

    Every runner Compass targets supports tag selection - that is why
    `compass bdd extract` writes tags rather than comments (see the extractor's
    note on the anchor). The flag differs per runner, so this maps the ones we
    know and returns None for the rest, which downgrades verification to a
    weaker method rather than guessing wrong.
    """
    joined = " ".join(command).lower()
    r = (runner or "").lower()
    if "pytest" in r or "pytest" in joined:
        return lambda tag: ["--collect-only", "-q", "-m", tag]
    if "cucumber" in r or "behave" in r:
        return lambda tag: ["--dry-run", "--tags", "@" + tag]
    if "godog" in r or "godog" in joined:
        # godog is driven through `go test`, so its flags are passed with the
        # -godog. prefix rather than as bare arguments.
        return lambda tag: ["-args", "-godog.tags=@" + tag, "-godog.dry-run"]
    return None


def cmd_bdd_verify(args):
    """compass bdd verify -- <run command> - run the BDD suite and record it.

    The producer half of `scenarios-are-executable`. This may depend on the
    project's BDD runner, because a project only runs it when it has one;
    `compass check` may not, which is why the two are separate commands.

    It records the spec's content hash alongside the scenario ids the runner
    reported, so a later check can tell whether the run still describes the
    spec it claims to verify.
    """
    task_dir = resolve_task_dir(getattr(args, "task", None))
    task_yaml = load_yaml(os.path.join(task_dir, "task.yml")) or {}
    proj = _read_config(task_dir).get("project") or {}
    command = list(getattr(args, "command", None) or [])
    if not command:
        declared = proj.get("bdd_run_command")
        if declared:
            command = shlex.split(declared)
    if not command:
        raise CompassError(
            "compass bdd verify needs a run command, e.g. `compass bdd verify "
            "-- pytest tests/` (or set project.bdd_run_command in "
            ".compass/config.yml)")

    code, out, _warnings = _run_test(command)

    # Which scenarios did the runner actually bind?
    #
    # Scraping stdout for TRC ids does not work, and finding that out cost a
    # dogfood run that recorded zero scenarios against a suite that passed
    # three. The tags `compass bdd extract` writes become *marks* in the
    # runner - they are selectable, not printed. Nothing in a normal run's
    # output names them.
    #
    # So ask the runner instead, using the tag selection the tags exist for:
    # collect (do not execute) each tag in turn and see whether anything
    # matches. Collection is cheap, and this asks the exact question the check
    # needs - "is this scenario bound to something the runner can run?"
    scenario_ids = [s.get("id") for s in (task_yaml.get("scenarios") or [])
                    if isinstance(s, dict) and s.get("id")]
    seen, method = [], "tag-probe"
    selector = _bdd_tag_selector(proj.get("bdd_runner") or "", command)
    if selector:
        for sid in scenario_ids:
            probe = list(command) + selector(sid)
            probe_code, probe_out, _ = _run_test(probe)
            if probe_code == 0 and _probe_collected(
                    probe_out, proj.get("bdd_runner") or ""):
                seen.append(sid)
    else:
        # Unknown runner: fall back to scraping, and say so in the record so a
        # reader knows the result is weaker than a probe.
        method = "output-scrape"
        # Word-boundary match: a bare `in` reports SCN-1 as seen when only
        # SCN-10 was printed.
        seen = [s for s in scenario_ids
                if re.search(r"\b%s\b" % re.escape(s), out)]
    seen = sorted(set(seen))

    payload = {
        "command": " ".join(command),
        "exit_code": code,
        "passed": code == 0,
        "timestamp": now_iso(),
        "spec_sha256": _spec_sha256(task_dir),
        "scenarios_seen": seen,
        "runner": proj.get("bdd_runner") or "unknown",
        "method": method,
        "log_excerpt": "\n".join(out.splitlines()[-25:]),
    }
    ev_dir = os.path.join(task_dir, "evidence")
    os.makedirs(ev_dir, exist_ok=True)
    path = os.path.join(ev_dir, "bdd-run.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")

    print(f"compass bdd verify: recorded {len(seen)} scenario(s) from the "
          f"runner (exit {code}).")
    print(f"  evidence : {path}")
    if code != 0:
        print("  note     : the suite did not pass. The record is still "
              "written - `scenarios-are-executable` reports which scenarios "
              "were accounted for, and `suite-passed` is what judges green.")
    return 0


def cmd_bdd_extract(args):
    """compass bdd extract - spec.feature.md -> a runnable .feature file."""
    task_dir = resolve_task_dir(getattr(args, "task", None))
    slug = os.path.basename(os.path.normpath(task_dir))
    spec_path = os.path.join(task_dir, "spec.feature.md")
    if not os.path.isfile(spec_path):
        raise CompassError(
            "no spec.feature.md for task '%s' - Specify must run first (%s)"
            % (slug, spec_path))

    with open(spec_path, "r", encoding="utf-8") as fh:
        text = fh.read()

    scenarios = scan_spec_markdown(text)

    # Validate EVERYTHING before writing ANYTHING. This is what makes a failed
    # extract leave the filesystem exactly as it was.
    problems = validate_scenarios(scenarios, os.path.relpath(spec_path, os.getcwd()))
    if problems:
        sys.stderr.write("compass bdd extract: %d problem(s) found; nothing written.\n"
                         % len(problems))
        for p in problems:
            sys.stderr.write("  %s\n" % p)
        return 1

    out_path = _bdd_out_path(args, task_dir, slug)
    spec_rel = os.path.join(".compass", "work", slug, "spec.feature.md")
    atomic_write(out_path, render_feature(slug, scenarios, spec_rel))
    sys.stdout.write("%s\n" % out_path)
    return 0
