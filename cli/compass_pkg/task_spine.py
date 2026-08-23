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
from compass_pkg.core import CompassError, find_governance, load_task, load_yaml, now_iso, resolve_task_dir, save_task, normalize_spine



# --- command: land-commit ---------------------------------------------------
# R5 - the Land commit step, made robust to auto-fixing pre-commit hooks.
# An auto-fixer (ruff format/--fix) rewrites a staged file and aborts the
# commit; pre-commit stashes the unstaged delta, the commit no-ops, and HEAD
# does not move - yet nothing notices, so an unattended Land believes it landed
# when it didn't. land-commit (DD-5) does all three R5 fixes: (a) best-effort
# clean-first via the pre-commit framework when present; (b) detect the no-op
# (HEAD unchanged), re-stage the hook's fixes, and retry once; (c) ALWAYS
# verify HEAD advanced and error loudly if not.


def _git(args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


# Files Compass writes itself that live outside any issue's directory. They
# belong in the commit that ships the issue they describe, but no author
# declares them as `changed_files` - the framework wrote them.
#
# A NAMED SET, deliberately not a `.compass/` prefix. A prefix would re-admit
# a sibling issue's artifacts, or a concurrent agent's in-progress work in the
# same tree, which is precisely the collision this scope check exists to stop.
FRAMEWORK_OWNED_PATHS = frozenset({
    ".compass/current-task",
})


def _land_scope(task, slug):
    """The paths a Land commit is allowed to contain.

    An issue's own `changed_files`, its artifact directory, and the framework's
    own bookkeeping files above. Anything else in the commit belongs to someone
    else - a concurrent agent's edits, untracked scratch, or the unrelated
    files a repo-wide formatter just rewrote.
    """
    owned = {
        cf["path"] for cf in (task.get("changed_files") or [])
        if isinstance(cf, dict) and cf.get("path")
    }
    return owned, f".compass/work/{slug}/"


def _out_of_scope(staged, owned, artifact_dir):
    return sorted(
        p for p in staged
        if p not in owned
        and p not in FRAMEWORK_OWNED_PATHS
        and not p.startswith(artifact_dir)
    )


def cmd_land_commit(args):
    import shutil
    cwd = os.getcwd()
    msg = args.message
    files = getattr(args, "files", None) or []

    # Confirm we are in a git work tree.
    inside = _git(["rev-parse", "--is-inside-work-tree"], cwd)
    if inside.returncode != 0:
        raise CompassError("compass land-commit: not inside a git repository.")

    # Stage any explicitly named paths.
    for f in files:
        _git(["add", "--", f], cwd)

    # Nothing staged → explicit error, never a retry loop (TRC-R5-F2).
    if _git(["diff", "--cached", "--quiet"], cwd).returncode == 0:
        raise CompassError(
            "compass land-commit: nothing staged to land. Stage the artifacts "
            "first (e.g. `git add <paths>`), then re-run."
        )

    # The task's declared scope. Everything below re-stages against this rather
    # than against the whole tree: a Land commit must contain what the task
    # says it changed, and nothing else. A repo-wide auto-formatter plus a
    # whole-tree re-stage once took a real index from ~23 task files to 1,574,
    # including a concurrent agent's uncommitted work.
    # Best-effort: `land-commit` has always worked in a repo with no task
    # directory at all, and must keep doing so. Without a task there is no
    # declared scope to check against - the re-stage below stays scoped either
    # way.
    owned, artifact_dir, slug = set(), "\0none", None
    try:
        _scope_dir = resolve_task_dir(getattr(args, "task", None))
        _scope_task, _ = load_task(_scope_dir)
        slug = os.path.basename(str(_scope_dir).rstrip("/"))
        owned, artifact_dir = _land_scope(_scope_task, slug)
    except (CompassError, OSError, KeyError):
        pass

    staged_now = _git(["diff", "--cached", "--name-only"], cwd).stdout.split()

    # The scope check needs a declared scope. A task with no `changed_files`
    # has not said what it owns, so there is nothing to check against and
    # refusing would break every task that does not record them (ADR-006:
    # a new mechanism no-ops for projects that have not adopted it). The
    # re-stage below is still scoped in that case - it re-stages what was
    # staged, never the whole tree.
    stray = _out_of_scope(staged_now, owned, artifact_dir) if owned else []
    if stray:
        raise CompassError(
            "compass land-commit: refusing to commit - "
            f"{len(stray)} staged path(s) are outside issue '{slug}'s declared "
            "scope:\n  " + "\n  ".join(stray[:20])
            + ("\n  ... and %d more" % (len(stray) - 20) if len(stray) > 20 else "")
            + "\n\nA ship commit contains the issue's `changed_files` and its "
            f"artifact directory ({artifact_dir}). If these paths belong to "
            "this issue, record them first:\n"
            "  compass changed-file add <path> --scenario <SCN-ID>\n"
            "Otherwise unstage them (`git restore --staged <path>`) - they may "
            "belong to another issue or another agent working in this tree."
        )

    head_before = _git(["rev-parse", "HEAD"], cwd).stdout.strip()

    def _restage_owned():
        """Re-stage this issue's paths after a hook rewrote them.

        Never `git add -A`. The set is what was already staged for this land,
        plus the issue's artifact directory - so a hook that reformats fifty
        unrelated files cannot smuggle them into the commit, and neither can
        another agent working in the same tree.

        It deliberately does NOT re-add the issue's whole `changed_files:`
        list. That list names every file the issue will touch, including files
        belonging to commits not yet made - so on an issue landed as a
        sequence of commits, re-adding it widened the current commit to the
        issue's entire declared scope. In the field that put a module's
        registration into the commit before the module itself, producing a
        commit that referenced code it did not contain: unbisectable,
        unrevertable, and green in CI, because CI only builds the branch tip.

        Recovering from a hook rewrite only needs what was already staged.
        """
        for path in sorted(set(staged_now) | set(files)):
            _git(["add", "--", path], cwd)
        if os.path.isdir(os.path.join(cwd, artifact_dir)):
            _git(["add", "--", artifact_dir], cwd)

    # (a) best-effort clean-first: only if the pre-commit framework is set up.
    if shutil.which("pre-commit") and os.path.isfile(
            os.path.join(cwd, ".pre-commit-config.yaml")):
        names = _git(["diff", "--cached", "--name-only"], cwd).stdout.split()
        if names:
            subprocess.run(["pre-commit", "run", "--files", *names],
                           cwd=cwd, capture_output=True, text=True)
            _restage_owned()  # re-stage what the hooks rewrote, scoped

    # First commit attempt.
    c1 = _git(["commit", "-m", msg], cwd)
    head_after = _git(["rev-parse", "HEAD"], cwd).stdout.strip()

    retried = False
    if head_after == head_before:
        # (b) the commit no-op'd - a hook likely auto-fixed and aborted. Stage
        # whatever it rewrote and retry exactly once, within the task's scope.
        _restage_owned()
        retried = True
        if _git(["diff", "--cached", "--quiet"], cwd).returncode != 0:
            _git(["commit", "-m", msg], cwd)
            head_after = _git(["rev-parse", "HEAD"], cwd).stdout.strip()

    # (c) ALWAYS verify HEAD advanced - the land's evidence is the moved HEAD.
    if head_after == head_before:
        log = ((c1.stdout or "") + (c1.stderr or ""))[-800:]
        raise CompassError(
            "compass land-commit: HEAD did not advance"
            + (" after a retry" if retried else "")
            + " - the land did NOT happen. A pre-commit hook may be aborting "
            "the commit repeatedly; resolve it and re-run.\n"
            "--- commit output (tail) ---\n" + log
        )

    # Success. Mark the task landed only now that HEAD is confirmed advanced -
    # AND only if its gates actually cleared.
    #
    # Guardrail G1 is "checked at Verify and Land". This used to write
    # `status: landed` on the strength of git HEAD moving alone, so a task
    # whose `compass check` failed before the commit was still recorded as
    # landed afterwards. The status is what `calibration`, the living-spec
    # derivation and every cross-task report read, so an unverified land
    # silently entered the record as a clean one.
    landed_note = ""
    if getattr(args, "task", None):
        try:
            task_dir = resolve_task_dir(args.task)
            task_path = os.path.join(task_dir, "task.yml")
            if os.path.isfile(task_path):
                task = normalize_spine(load_yaml(task_path))
                if isinstance(task, dict):
                    unmet = [g.get("id", "?") for g in (task.get("gates") or [])
                             if isinstance(g, dict) and g.get("status") != "pass"]
                    if unmet:
                        landed_note = (
                            "\n  NOT marked landed: %d gate(s) have not "
                            "passed (%s).\n  The commit stands - shipping is a "
                            "record, not a rubber stamp. Clear the gates and "
                            "re-run, or set status by hand if this issue "
                            "genuinely lands unverified."
                            % (len(unmet), ", ".join(unmet)))
                    else:
                        task["status"] = "landed"
                        task["land_timestamp"] = now_iso()
                        save_task(task, task_path)
                        landed_note = "\n  issue marked landed."
        except CompassError:
            pass  # status update is best-effort; the commit already succeeded

    suffix = " (after one retry)" if retried else ""
    print(f"compass land-commit: committed{suffix}. "
          f"HEAD {head_before[:8]} -> {head_after[:8]}" + landed_note)
    return 0


# --- commands: task-spine mutators (R9) + gate pass (R6) ---------------------
# Thin, schema-owning mutators so the task.yml spine below `readings` is never
# hand-edited YAML. `compass gate pass` is the shared R6/R9 command: it flips a
# gate to pass (R9) AND validates the evidence type against
# gate_evidence_requirements at write time (R6) - so a mismatch is caught
# before it is recorded, not discovered later at `compass check`.


def _load_gate_requirements():
    """Return (gate_evidence_requirements, known_evidence_types) from
    guardrails.yml. Empty/empty on any load failure."""
    try:
        g = load_yaml(os.path.join(find_governance(), "guardrails.yml"))
    except CompassError:
        return {}, set()
    return (g.get("gate_evidence_requirements") or {},
            set((g.get("evidence_types") or {}).keys()))


def cmd_gate_pass(args):
    task_dir = resolve_task_dir(args.task)
    task, task_path = load_task(task_dir)
    gates = task.get("gates") or []
    gate = next((g for g in gates
                 if isinstance(g, dict) and g.get("id") == args.gate_id), None)
    if gate is None:
        raise CompassError(
            f"compass gate pass: '{args.gate_id}' is not a gate in this issue "
            f"({[g.get('id') for g in gates]}). Has the route been evaluated?"
        )
    ev_ids = args.evidence or []
    if not ev_ids:
        raise CompassError("compass gate pass needs --evidence <id> [<id> ...]")
    registry = {e.get("id"): e for e in (task.get("evidence") or [])
                if isinstance(e, dict)}
    reqs, _known = _load_gate_requirements()
    accepted = reqs.get(args.gate_id)
    types_seen = set()
    for eid in ev_ids:
        entry = registry.get(eid)
        if not entry:
            raise CompassError(
                f"compass gate pass: evidence id '{eid}' is not in the issue's "
                f"evidence registry ({sorted(registry)}). Record it first with "
                f"`compass evidence add` (or `compass tdd-green` for a test-run)."
            )
        types_seen.add(entry.get("type"))
    if accepted and not (types_seen & set(accepted)):
        raise CompassError(
            f"compass gate pass: {args.gate_id} accepts evidence of type "
            f"{accepted}, but the evidence you gave is {sorted(types_seen)}. A "
            f"mechanical gate cannot be cleared with the wrong kind of evidence. "
            f"Point it at evidence of an accepted type."
        )
    gate["status"] = "pass"
    gate["evidence"] = list(ev_ids)
    save_task(task, task_path)
    print(f"compass gate pass: {args.gate_id} -> pass "
          f"(evidence: {', '.join(ev_ids)}).")
    return 0


def cmd_scenario_add(args):
    task_dir = resolve_task_dir(args.task)
    task, task_path = load_task(task_dir)
    scns = task.setdefault("scenarios", [])
    if any(isinstance(s, dict) and s.get("id") == args.scenario_id for s in scns):
        raise CompassError(
            f"compass scenario add: scenario '{args.scenario_id}' already "
            f"exists. Edit it directly if a change was intended."
        )
    scns.append({
        "id": args.scenario_id,
        "title": args.title or args.scenario_id,
        "intent": args.intent,
        "tests": list(args.test or []),
    })
    save_task(task, task_path)
    print(f"compass scenario add: {args.scenario_id} added.")
    return 0


def cmd_changed_file_add(args):
    task_dir = resolve_task_dir(args.task)
    task, task_path = load_task(task_dir)
    cfs = task.setdefault("changed_files", [])
    existing = next((c for c in cfs
                     if isinstance(c, dict) and c.get("path") == args.path), None)
    if existing:
        scns = set(existing.get("scenarios") or [])
        scns.add(args.scenario)
        existing["scenarios"] = sorted(scns)
    else:
        cfs.append({"path": args.path, "scenarios": [args.scenario]})
    save_task(task, task_path)
    print(f"compass changed-file add: {args.path} -> {args.scenario}.")
    return 0


def cmd_evidence_add(args):
    task_dir = resolve_task_dir(args.task)
    task, task_path = load_task(task_dir)
    _reqs, known = _load_gate_requirements()
    if known and args.type not in known:
        raise CompassError(
            f"compass evidence add: '{args.type}' is not a known evidence type "
            f"({sorted(known)})."
        )
    reg = task.setdefault("evidence", [])
    if any(isinstance(e, dict) and e.get("id") == args.evidence_id for e in reg):
        raise CompassError(
            f"compass evidence add: evidence id '{args.evidence_id}' already "
            f"exists. Use a fresh id."
        )
    # Validate the file against its declared type HERE, not two phases later.
    # `evidence add --type test-run --path run.txt` used to be accepted, and
    # `compass check` then failed with "test-run evidence unreadable" - a
    # set-then-discover-at-check round trip, out of context and hard to act on.
    # Only types with a real shape contract are checked; a manual review or an
    # artifact can be any file.
    abs_path = args.path if os.path.isabs(args.path) else os.path.join(
        task_dir, args.path)
    if not os.path.exists(abs_path):
        raise CompassError(
            f"compass evidence add: no file at '{args.path}' (looked in "
            f"{task_dir}). Evidence is a record on disk - register it after the "
            f"file exists, or fix the path.")
    if args.type == "test-run":
        try:
            with open(abs_path, encoding="utf-8") as fh:
                json.load(fh)
        except (ValueError, OSError):
            raise CompassError(
                f"compass evidence add: '{args.path}' is not a run record. "
                f"`test-run` means the JSON that `compass tdd-green` writes "
                f"(command, exit_code, passed), because the tested-before-ship "
                f"checks read "
                f"those fields.\n"
                f"  For a raw log, use --type command-output.\n"
                f"  For a real run, record it with `compass tdd-green -- <cmd>` "
                f"and it registers itself.")

    entry = {"id": args.evidence_id, "type": args.type, "path": args.path}
    if getattr(args, "scenario", None):
        entry["scenario"] = args.scenario
    reg.append(entry)
    save_task(task, task_path)
    print(f"compass evidence add: {args.evidence_id} ({args.type}) added.")
    return 0


def _annotate_gate_accepts(task_path):
    """R6-6: annotate each gate in the gates block with a `# accepts: [...]`
    comment naming its accepted evidence types (from guardrails.yml). A seeding
    nicety - yaml round-trips drop it, so it is re-applied after each route
    evaluate --write."""
    reqs, _known = _load_gate_requirements()
    if not reqs:
        return
    try:
        with open(task_path, "r", encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except OSError:
        return
    out, in_gates = [], False
    for line in lines:
        if _re.match(r"^gates:\s*$", line):
            in_gates = True
            out.append(line)
            continue
        if in_gates and _re.match(r"^[A-Za-z_]", line):
            in_gates = False     # a new top-level key ends the gates block
        if in_gates:
            m = _re.match(r"^(\s*)-\s+id:\s*([^\s#]+)", line)
            if m:
                indent, gid = m.group(1), m.group(2)
                acc = reqs.get(gid)
                if acc:
                    out.append(f"{indent}# accepts: {acc}")
        out.append(line)
    with open(task_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")


# --- compass task set-status ------------------------------------------------
# The last routine hand-edit of the spine. Before this, the terminal flip was a
# scripted `str.replace` on task.yml - reported from the field as brittle and
# repeated across every Land - and each new status value below would have been
# set the same way.

TASK_STATUSES = ("active", "queued", "parked", "landed", "abandoned")


def cmd_task_set_status(args):
    status = args.status
    if status not in TASK_STATUSES:
        raise CompassError(
            f"compass issue set-status: '{status}' is not an issue status. "
            f"Permitted: {', '.join(TASK_STATUSES)}.\n"
            "  queued    - recorded as next up, not started\n"
            "  active    - in flight\n"
            "  parked    - stopped, phases so far still valid, can resume\n"
            "  landed    - shipping completed; only this grants living-spec eligibility\n"
            "  abandoned - will not resume"
        )

    task_dir = resolve_task_dir(getattr(args, "task", None))
    task, path = load_task(task_dir)

    # `land-commit` refuses to write `landed` over gates that have not passed.
    # A second door into the same field must not be an easier one, or the
    # refusal is advice rather than a rule.
    if status == "landed":
        unmet = [g.get("id", "?") for g in (task.get("gates") or [])
                 if isinstance(g, dict) and g.get("status") != "pass"]
        if unmet:
            raise CompassError(
                f"compass issue set-status: refusing to mark '{task.get('issue')}' "
                f"landed - {len(unmet)} gate(s) have not passed "
                f"({', '.join(unmet)}). Shipping is a record, not a rubber stamp. "
                "Clear the gates and re-run."
            )
        task["land_timestamp"] = now_iso()

    task["status"] = status
    reason = getattr(args, "reason", None)
    if status == "parked":
        if reason:
            task["parked_reason"] = reason
        task["parked_at"] = now_iso()
    elif reason:
        task["note"] = reason

    save_task(task, path)
    detail = f" ({reason})" if reason else ""
    print(f"compass issue set-status: {task.get('issue')} -> {status}{detail}.")
    return 0
