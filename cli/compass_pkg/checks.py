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
from compass_pkg.core import CompassError, find_compass_dir, find_governance, load_yaml
from compass_pkg.tdd import _read_config



# --- command: check ----------------------------------------------------------

def _scenario_documented_in_spec(spec_path, scenario_id):
    """R1: a `verifiable: narrative` scenario is 'documented' when its gherkin
    block in spec.feature.md has a non-empty When AND Then. The When/Then is
    documentation-as-acceptance and lives only in the spec (it has no structured
    home to duplicate), so reading it is reading the artifact - NOT the R4
    prose-grep-for-a-machine-fact anti-pattern."""
    if not spec_path or not os.path.isfile(spec_path):
        return False
    try:
        lines = open(spec_path, encoding="utf-8").read().splitlines()
    except OSError:
        return False
    idx = None
    for i, ln in enumerate(lines):
        m = _re.search(r"<!--\s*traceability\s+id:\s*(\S+)", ln)
        if m and m.group(1).rstrip(" ·,") == scenario_id:
            idx = i
            break
    if idx is None:
        return False
    has_when = has_then = in_block = False
    for ln in lines[idx + 1:]:
        if _re.search(r"<!--\s*traceability\s+id:", ln):
            break                       # reached the next scenario
        if ln.strip().startswith("```"):
            if not in_block:
                in_block = True
                continue
            break                       # end of this scenario's gherkin block
        if in_block:
            if _re.match(r"\s*When\b", ln):
                has_when = True
            if _re.match(r"\s*Then\b", ln):
                has_then = True
    return has_when and has_then


def _test_id_resolves(test_id, project_root):
    """Does this declared test id point at something real on disk?

    Returns True (resolves), False (does not), or None (not file-shaped, so
    this check has no opinion).

    Resolution is by text, not by asking a test runner. Compass ships to
    projects using pytest, jest, go test and cargo, and a per-runner adapter is
    far more surface than the problem needs. The trade is that a name appearing
    only inside a comment would pass; the failure being caught is a name that
    appears nowhere at all.

    Ids that are not file-shaped are skipped rather than failed. Test ids in the
    wild are not all file references, and a false positive on a legitimate id
    teaches people to switch the check off. `verifiable: narrative` remains the
    sanctioned way to declare a scenario has no automated test.
    """
    import re as _re
    _re_ws = _re.compile(r"\s")
    tid = (test_id or "").strip()
    if not tid:
        return None

    if "::" in tid:
        file_part, name_part = tid.split("::", 1)
        name = name_part.split("::")[-1]
        name = name.split("[", 1)[0].strip()      # drop pytest parametrisation
    else:
        file_part, name = tid, None
        # Only treat it as a path if it looks like one; otherwise no opinion.
        if "/" not in file_part or "." not in os.path.basename(file_part):
            return None

    # A path has no whitespace in it. Prose that happens to mention a file -
    # "grep: governance/strategies.md carries S7" - is a description, not a
    # reference, and must not be reported as a broken path.
    file_part = file_part.strip()
    if not file_part or _re_ws.search(file_part):
        return None

    path = os.path.join(project_root, file_part.strip())
    if not os.path.isfile(path):
        return False
    if not name:
        return True

    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            body = fh.read()
    except OSError:
        return False
    return _re.search(r"\b" + _re.escape(name) + r"\b", body) is not None


def _check_declared_tests_resolve(task, task_dir):
    """G1: a scenario's declared test id must point at a test that exists.

    Without this, `compass check` reports green for a scenario naming a test
    nobody wrote - G1 and G3 are satisfied by a test being *named*, so the hole
    is invisible by construction.

    Scoped to tasks that are still `active` AND have already claimed
    `verify.correctness: pass`. Both conditions matter:

      * Before correctness is claimed, a declared test legitimately does not
        exist yet - TDD writes the id at Specify and the test at Build.
      * After a task lands, its spine is a historical record. Tests get renamed
        afterwards, and re-validating history against a moving codebase produces
        failures nobody can act on (ADR-006).
    """
    if (task.get("status") or "active") != "active":
        return True, "task is landed - declared test ids are a historical record"

    gates = {g.get("id"): g.get("status") for g in (task.get("gates") or [])}
    if gates.get("verify.correctness") != "pass":
        return True, ("correctness not yet claimed - declared tests are still a "
                      "plan, not a claim")

    project_root = os.path.dirname(find_compass_dir())
    broken, checked = [], 0
    for s in (task.get("scenarios") or []):
        if s.get("verifiable") == "narrative":
            continue
        for tid in (s.get("tests") or []):
            verdict = _test_id_resolves(tid, project_root)
            if verdict is None:
                continue
            checked += 1
            if not verdict:
                broken.append(f"{s.get('id', '?')}: {tid}")

    if broken:
        return False, ("declared test(s) do not resolve to a test on disk: "
                       + "; ".join(broken))
    return True, f"all {checked} declared test id(s) resolve"


def _check_scenarios_have_tests(task, task_dir):
    scns = task.get("scenarios") or []
    if not scns:
        return False, "no scenarios in task.yml"
    spec_path = os.path.join(task_dir, "spec.feature.md")
    missing_test, undocumented, documented_narr = [], [], 0
    for s in scns:
        sid = s.get("id", "?")
        # R1: narrative scenarios are assessed on documentation, never on a
        # test - so an incidental command does not buy a pass, and a documented
        # playbook does not need a fabricated one.
        if s.get("verifiable") == "narrative":
            if _scenario_documented_in_spec(spec_path, sid):
                documented_narr += 1
            else:
                undocumented.append(sid)
        elif not s.get("tests"):
            missing_test.append(sid)
    problems = []
    if missing_test:
        problems.append(f"scenarios with no test: {', '.join(missing_test)}")
    if undocumented:
        problems.append(
            f"narrative scenario(s) not documented (empty When/Then in "
            f"spec.feature.md): {', '.join(undocumented)}")
    if problems:
        return False, "; ".join(problems)
    if documented_narr:
        return True, (f"all {len(scns)} scenario(s) accounted for "
                      f"({documented_narr} documented narrative, exempt from "
                      f"tests-required)")
    return True, f"all {len(scns)} scenario(s) list a test"


def _spec_sha256(task_dir):
    """Hash of the task's spec.feature.md, or None when there is no spec.

    This is what makes a recorded BDD run verifiable later. Comparing the
    record's timestamp against the spec's mtime would be simpler and wrong:
    `git checkout` and `git clone` rewrite mtimes, so a fresh CI clone would
    read every stale record as current - a false green in exactly the place it
    matters most.
    """
    path = os.path.join(task_dir, "spec.feature.md")
    if not os.path.isfile(path):
        return None
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _check_scenarios_are_executable(task, task_dir):
    """Every scenario in task.yml was accounted for by the project's BDD runner.

    Reads the record written by `compass bdd verify`; never runs the suite.
    `compass check` is the fast mechanical gate - it runs in CI, in hooks, and
    on machines that never installed the project's dev dependencies, so it
    cannot depend on a BDD runner being present.

    The overwhelmingly common case is a project that has wired no runner at
    all. That passes, with a reason. A check that penalised projects for not
    opting in would be worse than no check (ADR-006).
    """
    proj = _read_config(task_dir).get("project") or {}
    runner = (proj.get("bdd_runner") or "").strip()
    if not runner:
        return True, ("no BDD runner wired (project.bdd_runner is unset) - "
                      "nothing to verify; see examples/bdd-adapters/ to opt in")

    scenario_ids = [s.get("id") for s in (task.get("scenarios") or [])
                    if isinstance(s, dict) and s.get("id")]
    if not scenario_ids:
        return True, "no scenarios recorded yet - nothing to verify"

    record_path = os.path.join(task_dir, "evidence", "bdd-run.json")
    if not os.path.isfile(record_path):
        return False, (f"project.bdd_runner is '{runner}' but no BDD run is on "
                       f"record - run `compass bdd verify -- <run command>`")
    try:
        with open(record_path, "r", encoding="utf-8") as fh:
            record = json.load(fh)
    except Exception as exc:                            # noqa: BLE001
        return False, f"evidence/bdd-run.json is unreadable ({exc})"

    current = _spec_sha256(task_dir)
    recorded = record.get("spec_sha256")
    if not current or not recorded:
        # A record with no spec hash cannot be shown to describe the spec it
        # claims to verify. Unverifiable is not the same as verified - treating
        # it as a pass is how a run made before the spec existed stays green
        # through every later edit.
        return False, ("the BDD run on record carries no spec hash, so it "
                       "cannot be shown to match the current spec.feature.md - "
                       "re-run `compass bdd verify`")
    if current != recorded:
        return False, ("the recorded BDD run describes a different "
                       "spec.feature.md than the one on disk - the spec has "
                       "changed since it ran, so the record is stale. Re-run "
                       "`compass bdd verify`.")

    if record.get("method") == "unverified":
        return True, ("the BDD run passed, but this runner does not report "
                      "which scenarios it bound and Compass has no tag selector "
                      "for it - so the binding is unverified rather than "
                      "unmet. See examples/bdd-adapters/ for a runner Compass "
                      "can verify.")

    seen = set(record.get("scenarios_seen") or [])
    missing = [sid for sid in scenario_ids if sid not in seen]
    if missing:
        return False, ("the BDD runner never accounted for: %s. Each needs a "
                       "step definition the runner can bind."
                       % ", ".join(missing))
    return True, ("all %d scenario(s) accounted for by %s"
                  % (len(scenario_ids), runner))


def _check_suite_passed(task, task_dir):
    # Read test-run entries from the registry. A task may have multiple
    # test-run entries (one per scenario binding); at least one must resolve
    # to a green-recorded file (exit_code 0), and any scenario binding must be
    # a real scenario in task.yml.
    registry = [e for e in (task.get("evidence") or [])
                if isinstance(e, dict) and e.get("type") == "test-run"]
    if not registry:
        return False, ("no test-run evidence in the registry - run "
                       "`compass tdd-green` to record a passing suite")
    scn_ids = {s.get("id") for s in (task.get("scenarios") or []) if isinstance(s, dict)}
    green = []
    for entry in registry:
        path = entry.get("path")
        if not path:
            return False, f"test-run evidence {entry.get('id', '?')} has no `path`"
        full = path if os.path.isabs(path) else os.path.join(task_dir, path)
        if not os.path.isfile(full):
            return False, f"test-run evidence {entry.get('id', '?')} path does not resolve: {path}"
        try:
            data = json.load(open(full, encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return False, f"test-run evidence {entry.get('id', '?')} unreadable: {exc}"
        if data.get("exit_code") != 0:
            return False, (f"test-run evidence {entry.get('id', '?')} records "
                           f"exit_code {data.get('exit_code')} - not green")
        scn = entry.get("scenario") or data.get("scenario")
        if scn and scn_ids and scn not in scn_ids:
            return False, (f"test-run evidence {entry.get('id', '?')} is bound "
                           f"to scenario '{scn}' which is not in task.yml")
        green.append(entry)
    bindings = [e.get("scenario") for e in green if e.get("scenario")]
    bound = f", bound to scenarios {sorted(set(bindings))}" if bindings else ""
    return True, f"{len(green)} test-run(s) on record, all green{bound}"


def _git_out(args, cwd):
    """Run a git command, returning stdout or "" - never raising."""
    try:
        r = subprocess.run(["git", *args], cwd=cwd, capture_output=True,
                           text=True, timeout=10)
        return r.stdout if r.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def _path_was_deleted(path, project_root):
    """Did git record this path being deleted? Then its absence IS the change.

    Removing dead code is legitimate work, and the file it removes is
    legitimately absent afterwards. Only git can tell that apart from a record
    that has rotted.
    """
    return bool(_git_out(["log", "--diff-filter=D", "--oneline", "-1", "--", path],
                         project_root).strip())


def _renamed_to(path, project_root):
    """Where git thinks a vanished path moved to, or None.

    A moved file is the common case and the fix is mechanical, so the error
    hands over the new path rather than starting an investigation.

    Rename records are read from history rather than with `--follow <path>`:
    `--follow` on a path that no longer exists reports the move as a delete
    plus an add, which is exactly the distinction being drawn here. The scan is
    bounded to the most recent rename commits - this is a hint, not an audit.
    """
    out = _git_out(["log", "--diff-filter=R", "-M", "--name-status",
                    "--format=", "-50"], project_root)
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) == 3 and parts[0].startswith("R") and parts[1] == path:
            return parts[2]
    return None


def _check_changed_code_traces(task, task_dir):
    changed = task.get("changed_files") or []
    scn_ids = {s.get("id") for s in (task.get("scenarios") or [])}
    if not changed:
        return True, "no changed_files recorded yet"
    problems = []
    for cf in changed:
        path = cf.get("path", "?")
        refs = cf.get("scenarios") or []
        if not refs:
            problems.append(f"{path} (no scenario)")
        else:
            dangling = [r for r in refs if r not in scn_ids]
            if dangling:
                problems.append(f"{path} -> unknown scenario(s) {', '.join(dangling)}")
    if problems:
        return False, "changed files not traced: " + "; ".join(problems)

    # A trace to a file that is no longer there is not a trace. The mapping
    # above can be perfect while every path points at nothing - which is how a
    # task reached all-gates-green with half its recorded paths dead, moved by
    # an ordinary refactor. A guard that cannot fail is not a guard.
    #
    # Scoped the same way as `declared-tests-resolve`, and for the same reasons:
    #   * A landed task's spine is a historical record. Files move afterwards,
    #     and re-validating history against a moving codebase produces failures
    #     nobody can act on (ADR-006) - so it is reported, never failed.
    #   * Before correctness is claimed the record is still being built.
    project_root = os.path.dirname(find_compass_dir())
    missing = []
    for cf in changed:
        path = cf.get("path")
        if not path or os.path.exists(os.path.join(project_root, path)):
            continue
        # Rename first: `git log --diff-filter=D -- <path>` reports a rename as
        # a deletion too, so asking "was it deleted?" first would silently
        # excuse every moved file - the exact rot this check exists to catch.
        moved_to = _renamed_to(path, project_root)
        if moved_to:
            missing.append(f"{path} (moved to {moved_to}?)")
            continue
        if _path_was_deleted(path, project_root):
            continue          # the deletion WAS the change
        missing.append(path)

    landed = (task.get("status") or "active") != "active"
    gates = {g.get("id"): g.get("status") for g in (task.get("gates") or [])}
    claimed = gates.get("verify.correctness") == "pass"

    if missing and not landed and claimed:
        return False, (
            f"{len(missing)} traced path(s) no longer exist: "
            + "; ".join(missing)
            + " - update changed_files to the current path, or remove the entry "
              "if the file was deleted"
        )
    if missing:
        why = "landed - historical record" if landed else "correctness not yet claimed"
        return True, (
            f"all {len(changed)} changed file(s) trace to a scenario, but "
            f"{len(missing)} no longer exist ({'; '.join(missing)}) - reported "
            f"only, because the task is {why}"
        )
    return True, (f"all {len(changed)} changed file(s) trace to a scenario "
                  f"and are present on disk")


def _check_scenario_has_id_and_intent(task, task_dir):
    scns = task.get("scenarios") or []
    if not scns:
        return False, "no scenarios in task.yml"
    problems = []
    for i, s in enumerate(scns):
        if not s.get("id"):
            problems.append(f"scenario #{i + 1} has no id")
        if not s.get("intent"):
            problems.append(f"scenario {s.get('id', '#' + str(i + 1))} has no linked intent")
    if problems:
        return False, "; ".join(problems)
    return True, f"all {len(scns)} scenario(s) have an id and a linked intent"


def _check_claim_traces(task, task_dir):
    claims = task.get("claims") or []
    scn_ids = {s.get("id") for s in (task.get("scenarios") or [])}
    if not claims:
        return True, "no claims recorded (no marketer in play, or none yet)"
    problems = []
    for c in claims:
        ref = c.get("scenario")
        if not ref:
            problems.append(f"claim {c.get('id', '?')} has no backing scenario")
        elif ref not in scn_ids:
            problems.append(f"claim {c.get('id', '?')} -> unknown scenario {ref}")
    if problems:
        return False, "; ".join(problems)
    return True, f"all {len(claims)} claim(s) trace to a scenario"


def _check_gate_evidence(task, task_dir):
    gates = task.get("gates") or []
    if not gates:
        return False, "no gates in task.yml - has the route been evaluated?"
    registry = {e.get("id"): e for e in (task.get("evidence") or [])
                if isinstance(e, dict) and e.get("id")}
    # Load the evidence typing rules. The one extra yaml load per `check` run is
    # negligible, and it keeps the check signature simple.
    try:
        gpolicy = load_yaml(os.path.join(find_governance(), "guardrails.yml"))
    except CompassError:
        gpolicy = {}
    known_types = set((gpolicy.get("evidence_types") or {}).keys())
    requirements = gpolicy.get("gate_evidence_requirements") or {}

    problems = []
    for g in gates:
        if g.get("status") != "pass":
            continue
        gid = g.get("id", "?")
        ev = g.get("evidence")
        # Gates now reference evidence by id (a list). Reject the older inline
        # {type, path} dict form explicitly - the registry is the model.
        if isinstance(ev, dict):
            problems.append(f"{gid} uses the old inline-evidence shape "
                            f"({{type, path}}); convert to evidence ids "
                            f"referencing entries in the top-level "
                            f"`evidence:` registry. See templates/task.yml.")
            continue
        if isinstance(ev, str):
            ev = [ev]   # tolerate a bare id string as a one-element list
        if not ev:
            problems.append(f"{gid} marked pass with no evidence")
            continue
        accepted = requirements.get(gid)
        types_seen = set()
        for ev_id in ev:
            entry = registry.get(ev_id)
            if not entry:
                problems.append(f"{gid} references evidence id '{ev_id}' which "
                                f"is not in the task's evidence registry")
                continue
            etype = entry.get("type")
            epath = entry.get("path")
            if not etype:
                problems.append(f"evidence {ev_id} has no `type`")
                continue
            if known_types and etype not in known_types:
                problems.append(f"evidence {ev_id} type '{etype}' is not a "
                                f"known type ({sorted(known_types)})")
                continue
            types_seen.add(etype)
            if epath and not os.path.exists(os.path.join(task_dir, epath)) \
                    and not os.path.exists(epath):
                problems.append(f"evidence {ev_id} ({etype}) path does not "
                                f"resolve: {epath}")
        if accepted and not (types_seen & set(accepted)):
            problems.append(f"{gid} requires evidence of type {accepted} but "
                            f"its referenced evidence is {sorted(types_seen)} - "
                            f"a mechanical gate cannot be cleared with the "
                            f"wrong kind of evidence")
    if problems:
        # R6-5: enumerate one problem per line so two mismatched gates surface
        # as two distinct, readable failures - not one concatenated string.
        return False, "\n         ".join(problems)
    passed = [g.get("id") for g in gates if g.get("status") == "pass"]
    return True, f"{len(passed)}/{len(gates)} pass gate(s), all backed by registry evidence of accepted type"


def _parse_dod_lines(task_dir):
    """Read verification-report.md from task_dir and return a list of DoD
    line strings found under the "Definition of Done" heading.

    Returns an empty list if the file is absent or the section is missing.
    This is the correct backward-compat behaviour (TRC-X4): no file → no
    items → check passes.
    """
    report_path = os.path.join(task_dir, "verification-report.md")
    if not os.path.isfile(report_path):
        return []
    with open(report_path, "r", encoding="utf-8") as fh:
        lines = fh.readlines()
    in_dod = False
    dod_lines = []
    for line in lines:
        stripped = line.rstrip("\n")
        # Detect the heading - allow any heading level (##, ###, ####)
        if stripped.strip().lstrip("#").strip() == "Definition of Done":
            in_dod = True
            continue
        if in_dod:
            # A new heading (line starting with #) ends the section
            if stripped.strip().startswith("#"):
                break
            dod_lines.append(stripped)
    return dod_lines

_DOD_ITEM_RE = _re.compile(r"^\s*-\s+\[([ xX])\]\s*(.*)")
_EVIDENCE_TAG_RE = _re.compile(r"\(evidence:\s*(EV-[^\)]+)\)")
_BACKFILL_TAG_RE = _re.compile(r"\(backfill:\s*(BF-[^\)]+)\)")

# Evidence types accepted for DoD evidence (all types that represent real,
# typed evidence - not the catch-all `artifact` which is the weakest).
_DOD_ACCEPTED_EVIDENCE_TYPES = {
    "test-run",
    "command-output",
    "manual-review",
    "human-approval",
    "security-review",
    "migration-plan",
    "rollback-plan",
    "claim-review",
    "artifact",  # weakest but still typed - accepted for DoD
    "spike-conclusion",
}


def _check_dod_evidence_typed(task, task_dir):
    """Parse the DoD section of verification-report.md and enforce the
    inline-tag rule (DD-3):

    - `- [x] ...`                  → passes (human ticked it)
    - `- [ ] (evidence: EV-id) ...` → passes if EV-id is in the evidence
                                       registry with an accepted type
    - `- [ ] (backfill: BF-id) ...` → passes if BF-id is in task.yml
                                       backfills with status: owed
    - `- [ ] <bare description>`   → FAILS (evidence, not assertion - G4)

    Cross-task half (TRC-E3): scan sibling task.yml files for backfills with
    target_task equal to this task's slug and status: owed - any such entry
    blocks this task's Land.
    """
    dod_lines = _parse_dod_lines(task_dir)

    # Build lookup structures from the current task
    ev_registry = {
        e.get("id"): e
        for e in (task.get("evidence") or [])
        if isinstance(e, dict) and e.get("id")
    }
    backfills = {
        b.get("id"): b
        for b in (task.get("backfills") or [])
        if isinstance(b, dict) and b.get("id")
    }

    problems = []
    item_count = 0

    for raw in dod_lines:
        m = _DOD_ITEM_RE.match(raw)
        if not m:
            continue  # not a checklist item - skip (comments, blank lines, etc.)
        item_count += 1
        checked, rest = m.group(1), m.group(2)

        if checked.lower() == "x":
            # Human-ticked - passes unconditionally
            continue

        # Unchecked - must have an inline tag
        ev_match = _EVIDENCE_TAG_RE.search(rest)
        bf_match = _BACKFILL_TAG_RE.search(rest)

        if not ev_match and not bf_match:
            # Bare unchecked - fails G4 (evidence, not assertion)
            desc = rest.strip() or raw.strip()
            problems.append(
                f"bare unchecked DoD item (no evidence or backfill tag): "
                f"'{desc}' - add (evidence: EV-<id>) or (backfill: BF-<id>) "
                f"inline tag, or tick the box if done. G4: evidence, not "
                f"assertion."
            )
            continue

        if ev_match:
            ev_id = ev_match.group(1).strip()
            entry = ev_registry.get(ev_id)
            if not entry:
                problems.append(
                    f"DoD item references evidence id '{ev_id}' which is not "
                    f"in task.yml evidence registry"
                )
            elif entry.get("type") not in _DOD_ACCEPTED_EVIDENCE_TYPES:
                problems.append(
                    f"DoD item references evidence '{ev_id}' with type "
                    f"'{entry.get('type')}' which is not an accepted DoD "
                    f"evidence type"
                )
            # else: passes

        if bf_match:
            bf_id = bf_match.group(1).strip()
            bf_entry = backfills.get(bf_id)
            if not bf_entry:
                problems.append(
                    f"DoD item references backfill id '{bf_id}' which is not "
                    f"in task.yml backfills"
                )
            elif bf_entry.get("status") not in ("owed", "paid"):
                problems.append(
                    f"backfill '{bf_id}' has unrecognised status "
                    f"'{bf_entry.get('status')}' (must be 'owed' or 'paid')"
                )
            # status: owed or paid both pass here; paying is a separate
            # concern tracked by _check_backfills_paid

    # Cross-task check (TRC-E3): scan sibling tasks for backfills that
    # target this task and are still owed. Use the directory name as the slug
    # (authoritative) in preference to task.get("task") which may be a
    # template placeholder; the directory name is always the true slug.
    this_slug = os.path.basename(task_dir) or task.get("task") or ""
    sibling_problems = _check_inbound_backfills(task_dir, this_slug)
    problems.extend(sibling_problems)

    if problems:
        return False, "; ".join(problems)

    if item_count == 0:
        return True, "DoD section is empty or absent - nothing to evidence"
    return True, f"all {item_count} DoD item(s) are typed or human-ticked"


def _check_inbound_backfills(task_dir, this_slug):
    """Scan sibling task directories for backfills with target_task == this_slug
    and status: owed. Each such entry is a blocking cross-task debt."""
    problems = []
    # task_dir is .compass/work/<slug>/; sibling dirs are alongside it
    work_dir = os.path.dirname(task_dir)
    if not os.path.isdir(work_dir):
        return problems
    for entry in os.listdir(work_dir):
        sibling = os.path.join(work_dir, entry)
        if sibling == task_dir:
            continue
        tp = os.path.join(sibling, "task.yml")
        if not os.path.isfile(tp):
            continue
        try:
            with open(tp, "r", encoding="utf-8") as fh:
                try:
                    import yaml as _yaml
                    sibling_task = _yaml.safe_load(fh) or {}
                except Exception:
                    continue
        except OSError:
            continue
        for bf in (sibling_task.get("backfills") or []):
            if not isinstance(bf, dict):
                continue
            if (bf.get("target_task") == this_slug
                    and bf.get("status") == "owed"):
                src_slug = sibling_task.get("task") or entry
                problems.append(
                    f"cross-task block: task '{src_slug}' has backfill "
                    f"'{bf.get('id', '?')}' (status: owed) targeting this "
                    f"task - pay it with `compass backfill pay --task "
                    f"{src_slug} {bf.get('id', '?')}` before Land"
                )
    return problems


def _check_human_approval(task, task_dir):
    # Approvals are typed evidence in the registry. G5 applies when the task
    # touches irreversible surface (the routing policy floors it to Expedition);
    # this check verifies a `human-approval` entry with decision=approved and
    # the required structured fields.
    registry = task.get("evidence") or []
    approvals = [e for e in registry if isinstance(e, dict)
                 and e.get("type") == "human-approval"]
    approved = [a for a in approvals if a.get("decision") == "approved"]
    if not approved:
        return False, ("no human-approval evidence with decision=approved - "
                       "G5 applies because this task touches irreversible "
                       "surface. Add a `human-approval` entry to the evidence "
                       "registry with approver, role, scope, decision, and "
                       "timestamp.")
    a = approved[0]
    missing = [k for k in ("approver", "role", "scope", "timestamp")
               if not a.get(k)]
    if missing:
        return False, (f"approval {a.get('id', '?')} is missing required "
                       f"field(s): {', '.join(missing)}. A human-approval "
                       f"evidence entry must record who approved, in what role, "
                       f"the scope, and when.")
    return True, (f"approval on record: {a.get('approver')} "
                  f"({a.get('role')}) - scope: {a.get('scope')}")


def _check_backfills_paid(task, task_dir):
    bfs = task.get("backfills") or []
    unpaid = [b.get("id", "?") for b in bfs if b.get("status") != "paid"]
    if unpaid:
        return False, f"unpaid backfill(s): {', '.join(unpaid)}"
    return True, "no owed backfills" if not bfs else f"all {len(bfs)} backfill(s) paid"


def _check_spike_conclusion_present(task, task_dir):
    registry = task.get("evidence") or []
    concs = [e for e in registry if isinstance(e, dict)
             and e.get("type") == "spike-conclusion"]
    if not concs:
        return False, ("no `spike-conclusion` evidence on record - a Spike "
                       "must record what it learned and a close-out decision "
                       "(discard | graduate-to-delivery | defer) before it "
                       "closes")
    c = concs[0]
    valid = ["discard", "graduate-to-delivery", "defer"]
    decision = c.get("decision")
    if decision not in valid:
        return False, (f"spike-conclusion {c.get('id', '?')} has "
                       f"decision={decision!r}; it must be one of {valid}")
    if decision == "graduate-to-delivery" and not c.get("next_task"):
        return False, (f"spike-conclusion {c.get('id', '?')} graduates to "
                       f"delivery, but `next_task:` is empty - link the new "
                       f"task (e.g. .compass/work/<new-slug>/). Graduation is "
                       f"a fresh Frame, not a merge.")
    nt = f" -> {c['next_task']}" if c.get("next_task") else ""
    return True, f"spike close-out on record: {decision}{nt}"


def _check_spike_no_production_changes(task, task_dir):
    cf = task.get("changed_files") or []
    if cf:
        paths = [c.get("path", "?") for c in cf if isinstance(c, dict)]
        return False, (f"a Spike must not list production changed_files "
                       f"(found: {paths}). Exploration code stays on a scratch "
                       f"branch; if the finding is acted on, a fresh Frame "
                       f"owns the code under a real route's guardrails. This "
                       f"is the safety model - a Spike cannot silently become "
                       f"delivery.")
    return True, "no production changed_files (correct - a Spike ships nothing)"


def _load_quarantine_registry(gov_dir):
    """Load governance/quarantine.yml and return a set of quarantined test ids.

    Returns a dict mapping test id -> entry, so callers can check for
    tracking_task presence. Returns an empty dict if quarantine.yml is absent
    (zero-setup default, ADR-006).
    """
    path = os.path.join(gov_dir, "quarantine.yml")
    if not os.path.isfile(path):
        return {}
    try:
        data = load_yaml(path)
    except CompassError:
        return {}
    result = {}
    for entry in (data.get("quarantined") or []):
        if isinstance(entry, dict) and entry.get("test"):
            result[entry["test"]] = entry
    return result


def _check_no_trusted_rerun(task, task_dir):
    """G4 extension (TRC-A3, TRC-A4, TRC-A5, TRC-FM3 / DD-3): verify that
    no test-run evidence records a rerun-to-green without either:
      (a) the test being listed in governance/quarantine.yml with a tracking_task, OR
      (b) evidence with attempts:1 (clean first pass), OR
      (c) no attempts field at all (old evidence - backward compat, TRC-A5).

    Failure cases (DD-3):
      - rerun_without_change: true AND test not quarantined → FAIL
      - attempts > 1 AND rerun_without_change absent → FAIL (incomplete evidence)

    This check reads governance/quarantine.yml at runtime; the registry is
    loaded lazily so zero-setup projects (no quarantine.yml) pass trivially.
    """
    registry_entries = [
        e for e in (task.get("evidence") or [])
        if isinstance(e, dict) and e.get("type") == "test-run"
    ]
    if not registry_entries:
        return True, "no test-run evidence to evaluate"

    # Load quarantine registry once
    try:
        gov = find_governance()
    except CompassError:
        gov = None
    quarantine = _load_quarantine_registry(gov) if gov else {}

    problems = []
    notes = []
    for entry in registry_entries:
        path = entry.get("path")
        ev_id = entry.get("id", "?")
        # Try to read the evidence file to get attempts/rerun_without_change
        green_data = {}
        if path:
            full = path if os.path.isabs(path) else os.path.join(task_dir, path)
            if os.path.isfile(full):
                try:
                    green_data = json.load(open(full, encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    green_data = {}
        # Also check the registry entry itself for the fields (tdd-green upserts
        # them there from the payload)
        attempts = green_data.get("attempts") if "attempts" in green_data else entry.get("attempts")
        rerun_flag = (green_data.get("rerun_without_change")
                      if "rerun_without_change" in green_data
                      else entry.get("rerun_without_change"))
        test_id = green_data.get("test") or entry.get("test")

        # Case 1: TRC-A5 backward compat - no attempts field → trivial pass
        if attempts is None:
            continue

        # Case 2: attempts > 1, rerun_without_change absent → incomplete evidence
        if isinstance(attempts, int) and attempts > 1 and rerun_flag is None:
            problems.append(
                f"evidence {ev_id}: attempts={attempts} but rerun_without_change "
                f"marker is absent - incomplete evidence cannot clear G4. "
                f"Either add the marker (with evidence that no source change "
                f"intervened) or quarantine the test in governance/quarantine.yml "
                f"with a tracking_task (TRC-FM3)"
            )
            continue

        # Case 3: rerun_without_change: true → test must be quarantined
        if rerun_flag:
            if not test_id:
                problems.append(
                    f"evidence {ev_id}: rerun_without_change:true but no `test` "
                    f"field to look up in the quarantine registry - add the test "
                    f"id to the evidence record"
                )
                continue
            if test_id not in quarantine:
                problems.append(
                    f"evidence {ev_id}: test '{test_id}' ran {attempts} time(s) "
                    f"and passed without a source change (rerun_without_change:true) "
                    f"but is not in governance/quarantine.yml - a rerun-to-green is "
                    f"the loss of the most useful signal (S5). Fix the root cause "
                    f"or add the test to governance/quarantine.yml with a "
                    f"tracking_task (TRC-A3)"
                )
            else:
                q_entry = quarantine[test_id]
                notes.append(
                    f"evidence {ev_id}: test '{test_id}' is quarantined "
                    f"(tracking: {q_entry.get('tracking_task', '?')}) - "
                    f"rerun-to-green noted; fix tracked"
                )

    if problems:
        return False, "; ".join(problems)
    note_str = f" (quarantine notes: {len(notes)})" if notes else ""
    return True, f"no trusted-rerun violations{note_str}"


def _check_coherence_check_passes(task, task_dir):
    """G4 extension (ADR-007 / DD-2): verify.analyze requires a coherence-check
    evidence entry with zero findings. Only runs when verify.analyze is in the
    task's gate set. If the gate is absent, this check trivially passes (the
    task is not subject to the coherence-check requirement)."""
    gates = task.get("gates") or []
    gate_ids = [g.get("id") for g in gates if isinstance(g, dict)]
    if "verify.analyze" not in gate_ids:
        return True, "verify.analyze not in gate set - coherence check not required"
    # Gate is present: look for a coherence-check typed evidence entry
    registry = {e.get("id"): e for e in (task.get("evidence") or [])
                if isinstance(e, dict) and e.get("id")}
    coherence_entries = [e for e in registry.values()
                         if e.get("type") == "coherence-check"]
    if not coherence_entries:
        return False, ("no coherence-check evidence on record - run "
                       "`compass analyze` to produce the required "
                       "coherence-check evidence for verify.analyze")
    # Check that the most recent entry records zero findings
    entry = coherence_entries[-1]
    path = entry.get("path")
    if path:
        full = path if os.path.isabs(path) else os.path.join(task_dir, path)
        if os.path.isfile(full):
            try:
                data = json.load(open(full, encoding="utf-8"))
                n = data.get("finding_count", None)
                if n is not None and n != 0:
                    return False, (f"coherence-check evidence records "
                                   f"{n} finding(s) - resolve them before "
                                   f"clearing verify.analyze")
            except (OSError, json.JSONDecodeError):
                pass  # readable but corrupt - gate-evidence-present catches it
    return True, "coherence-check evidence on record - verify.analyze gate cleared"


def _check_command_passes(task, task_dir):
    """A2 (ADR-009 / DD-2): run each project guardrail's declared `command:`
    and report pass/fail.

    Behaviour:
    - When verify.fitness is in the gate set but zero project guardrails
      declare check: command-passes → vacuous-clear (DD-6).
    - For each project guardrail with check: command-passes, run
      subprocess.run(shell=True, timeout=timeout_seconds) from the project
      root (inferred as the directory 2 levels above task_dir, which is
      .compass/work/<slug>).
    - All commands must exit 0 for the check to pass.
    - If any command exits non-zero, the check fails with exit code + stderr.

    This check is purely mechanical: no network call, no LLM client (TRC-F2).
    """
    # Locate the project root (2 levels up from task_dir: .compass/work/<slug>)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(task_dir)))
    if not os.path.isdir(project_root):
        project_root = os.getcwd()

    # Load the guardrails to find project guardrails with check: command-passes
    try:
        gov = find_governance()
        gpolicy = load_yaml(os.path.join(gov, "guardrails.yml"))
    except CompassError:
        gpolicy = {}

    project_guardrails = gpolicy.get("project") or []
    cp_guardrails = [
        g for g in project_guardrails
        if isinstance(g, dict) and "command-passes" in (g.get("checks") or [])
    ]

    # Vacuous-clear (DD-6): verify.fitness in gate set, zero command-passes
    # guardrails declared → the gate has nothing to check; it clears by vacuity.
    if not cp_guardrails:
        return True, ("verify.fitness: 0 project guardrails declared with "
                      "command-passes; clearing by vacuity (no fitness functions "
                      "to check - declare project guardrails with "
                      "`check: command-passes` to add fitness functions)")

    failures = []
    for g in cp_guardrails:
        params = g.get("params") or {}
        command = params.get("command")
        if not command or not isinstance(command, str):
            failures.append(
                f"project guardrail {g.get('id', '?')}: missing or non-string "
                f"`command` in params - declaration is malformed"
            )
            continue
        timeout = params.get("timeout_seconds", 300)
        if timeout == 0:
            timeout = None  # 0 = no timeout (discouraged, as per DD-2)
        try:
            proc = subprocess.run(
                command,
                shell=True,
                timeout=timeout,
                capture_output=True,
                text=True,
                cwd=project_root,
            )
            if proc.returncode != 0:
                stderr_snippet = (proc.stderr or "").strip()[:200]
                failures.append(
                    f"project guardrail {g.get('id', '?')} "
                    f"({g.get('name', 'unnamed')}): command exited {proc.returncode}"
                    + (f"; stderr: {stderr_snippet}" if stderr_snippet else "")
                )
        except subprocess.TimeoutExpired:
            failures.append(
                f"project guardrail {g.get('id', '?')} "
                f"({g.get('name', 'unnamed')}): command timed out "
                f"after {timeout}s"
            )
        except Exception as exc:
            failures.append(
                f"project guardrail {g.get('id', '?')} "
                f"({g.get('name', 'unnamed')}): command error: {exc}"
            )

    if failures:
        return False, "; ".join(failures)

    n = len(cp_guardrails)
    return True, (f"{n} command-passes guardrail(s) all exited 0 - "
                  f"architectural fitness checks pass")
