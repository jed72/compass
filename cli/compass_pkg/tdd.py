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
from compass_pkg.core import CompassError, find_upwards, load_task, load_yaml, now_iso, resolve_task_dir, save_task



# --- commands: tdd-red / tdd-green ------------------------------------------

# R2 - exit-code-masking integrity for piped test commands.
# A command wrapped in `bash -c '... | tail'` returns the LAST pipeline stage's
# exit code (tail = 0), masking an inner test failure as a false green. Three
# layered signals defend against it (DD-2): (1) inject `set -o pipefail` into
# bash/zsh wrappers so a mid-pipeline failure propagates; (2) warn when the
# wrapped script is a top-level pipe ending in a pager/filter; (3) cross-check
# output for a known-runner fail-token even on a zero exit.
_PIPE_FILTER_CMDS = {"tail", "head", "grep", "cat", "less", "more", "tee", "sort",
                     "uniq", "wc", "awk", "sed"}
_PIPEFAIL_SHELLS = {"bash", "zsh"}


def _shell_wrapper_script(cmd):
    """If cmd is a shell wrapper (`bash -c <script>` / `sh -c <script>` / zsh),
    return (shell_basename, script_index, script). Else (None, None, None)."""
    if len(cmd) >= 3 and cmd[1] == "-c":
        base = os.path.basename(cmd[0])
        if base in ("bash", "sh", "zsh", "dash"):
            return base, 2, cmd[2]
    return None, None, None


def _final_pipe_filter(script):
    """If `script` is a top-level pipe (not `||`) whose final stage's command is
    a pager/filter, return that command's name. Else None."""
    if "|" not in script:
        return None
    # split on a single | that is not part of '||'
    parts = _re.split(r"(?<!\|)\|(?!\|)", script)
    if len(parts) < 2:
        return None
    last = parts[-1].strip()
    if not last:
        return None
    first_tok = last.split()[0]
    base = os.path.basename(first_tok)
    return base if base in _PIPE_FILTER_CMDS else None


def _output_fail_token(out):
    """Return a recognised runner fail-token if the output indicates a failure,
    even on a zero exit. Conservative - only strong, runner-specific patterns,
    so a passing run ('0 failed', '5 passed') is never flagged."""
    patterns = [
        r"\b[1-9]\d* failed\b",        # pytest:  "1 failed"
        r"(?m)^FAILED\b",              # pytest -v line, generic
        r"(?m)^--- FAIL",             # go test
        r"(?m)^FAIL\b",               # go test summary
        r"\bFAILURES!\b",             # junit-style
    ]
    for pat in patterns:
        m = _re.search(pat, out)
        if m:
            return m.group(0).strip()
    return None


def _run_test(cmd):
    """Run a test command and return (exit_code, combined_output, warnings).

    Hardens against pipeline exit-code masking (R2): pipefail is injected into
    bash/zsh `-c` wrappers; a pager/filter final stage raises a warning.
    """
    warnings = []
    run_cmd = list(cmd)
    shell, idx, script = _shell_wrapper_script(cmd)
    if script is not None:
        filt = _final_pipe_filter(script)
        if filt:
            warnings.append(
                f"pipe-masking risk: the exit code reflects the last pipeline "
                f"stage ({filt}), not your test. "
                + (f"`set -o pipefail` was injected so a mid-pipeline failure "
                   f"still propagates." if shell in _PIPEFAIL_SHELLS else
                   f"this {shell} wrapper cannot take `set -o pipefail` safely - "
                   f"the inner failure may be masked.")
            )
        if shell in _PIPEFAIL_SHELLS and "pipefail" not in script:
            run_cmd[idx] = "set -o pipefail\n" + script
    proc = subprocess.run(run_cmd, capture_output=True, text=True)
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out, warnings


def _write_evidence(task_dir, name, payload):
    ev_dir = os.path.join(task_dir, "evidence")
    os.makedirs(ev_dir, exist_ok=True)
    path = os.path.join(ev_dir, name + ".json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    # also drop the full log next to it
    log_path = os.path.join(ev_dir, name + ".log")
    with open(log_path, "w", encoding="utf-8") as fh:
        fh.write(payload.get("_full_log", ""))
    return path


def _resolve_scenario(task_dir, scenario):
    """Validate a --scenario binding. A red/green that proves a test ran is
    weaker than one bound to the scenario it is evidence FOR - relevance, not
    just failure. If the task has a scenarios block, the id must be in it."""
    if not scenario:
        return None
    try:
        task, _ = load_task(task_dir)
    except CompassError:
        return scenario  # no task.yml yet - record the binding, can't check it
    ids = {s.get("id") for s in (task.get("scenarios") or []) if isinstance(s, dict)}
    if ids and scenario not in ids:
        raise CompassError(
            f"--scenario '{scenario}' is not a scenario id in this task's "
            f"task.yml (scenarios: {sorted(ids)}). Bind to a real scenario, or "
            f"add it to task.yml first."
        )
    return scenario


# R7 - coverage-floor neutralisation + the test_micro_command knob.
# R8 - the sanctioned verified-by kinds for an honest non-unit red.
_VERIFIED_BY_KINDS = {"regression", "e2e", "typecheck", "live"}


def _read_config(task_dir):
    """Load .compass/config.yml for the project containing task_dir. {} on miss."""
    root = find_upwards(task_dir, ".compass") or task_dir
    path = os.path.join(root, ".compass", "config.yml")
    try:
        cfg = load_yaml(path)
        return cfg if isinstance(cfg, dict) else {}
    except CompassError:
        return {}


def _micro_command(args, task_dir):
    """The command a TDD micro-run executes: the explicit `-- <cmd>` if given,
    else project.test_micro_command, else project.test_command (R7)."""
    if args.command:
        return list(args.command)
    proj = _read_config(task_dir).get("project") or {}
    cmd = proj.get("test_micro_command") or proj.get("test_command")
    if not cmd:
        return None
    import shlex
    return shlex.split(cmd)


def _is_pytest_command(cmd):
    """Does this command invoke pytest? Used for both the coverage flag and the
    exit-code reading below, since both are pytest-specific."""
    if not cmd:
        return False
    base = os.path.basename(str(cmd[0]))
    return base.startswith("pytest") or "pytest" in cmd


def _pytest_cov_available():
    """Is pytest-cov actually loadable in the environment that will run pytest?

    `--cov-fail-under` is a pytest-cov flag, not a pytest one. Injecting it
    where the plugin cannot load makes pytest exit 4 (usage error) without
    running a single test. Projects legitimately disable plugin autoload -
    PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 is the standard cure for plugins that hang
    on init in clean environments - and there the flag is always rejected.
    """
    if os.environ.get("PYTEST_DISABLE_PLUGIN_AUTOLOAD"):
        return False
    try:
        import importlib.util
        return importlib.util.find_spec("pytest_cov") is not None
    except Exception:
        return False


def _neutralise_coverage(cmd):
    """R7: for a recognised pytest micro-run, inject --cov-fail-under=0 so a
    project-wide coverage floor cannot refuse a passing targeted test. The
    micro-run is never the coverage gate - the full suite at Verify is. An
    explicit --cov-fail-under is preserved (the full-suite floor is respected);
    a non-pytest command is left untouched.

    The flag is added only when pytest-cov can actually load. Adding a flag the
    runner will reject turns a real test run into a usage error, which is a
    worse failure than the coverage floor this exists to work around.
    """
    if not cmd:
        return cmd
    if any("--cov-fail-under" in str(c) for c in cmd):
        return cmd
    if _is_pytest_command(cmd) and _pytest_cov_available():
        return list(cmd) + ["--cov-fail-under=0"]
    return cmd


# A non-zero exit does NOT mean "a test failed". A runner exits non-zero for
# reasons that mean the opposite - no test ran at all. Recording one of those as
# a red writes the .red marker, which hooks/pre-tool.sh treats as proof that a
# real failure was observed. A typo would then unlock a code edit.
#
# pytest: 1 = tests failed · 2 = interrupted · 3 = internal error
#         4 = usage error  · 5 = no tests collected
_NO_TEST_RAN_EXITS = {
    2: "it was interrupted before finishing (pytest exit 2)",
    3: "the runner hit an internal error (pytest exit 3)",
    4: "the runner rejected an argument (pytest exit 4, a usage error)",
    5: "no test was collected by that path (pytest exit 5)",
}


def _red_rejection_reason(code, command):
    """Why this exit must not be recorded as a red, or None if it may be.

    Only applied to commands recognisable as pytest, because these codes are
    pytest's. An unrecognised runner keeps the permissive behaviour: narrowing
    that would break every project using a runner Compass cannot identify.
    """
    if not _is_pytest_command(command):
        return None
    return _NO_TEST_RAN_EXITS.get(code)


def cmd_tdd_red(args):
    task_dir = resolve_task_dir(args.task)
    scenario = _resolve_scenario(task_dir, getattr(args, "scenario", None))
    verified_by = getattr(args, "verified_by", None)
    if verified_by and verified_by not in _VERIFIED_BY_KINDS:
        raise CompassError(
            f"compass tdd-red: --verified-by '{verified_by}' is not a recognised "
            f"kind. Allowed: {sorted(_VERIFIED_BY_KINDS)}. A verified-by red ties "
            f"the scenario's acceptance to a non-unit guard (a typecheck, an e2e "
            f"or regression suite, a live run) for changes with no natural unit red."
        )
    command = _micro_command(args, task_dir)
    if not command:
        raise CompassError("compass tdd-red needs a test command, e.g. "
                           "`compass tdd-red --scenario SCN-001 -- pytest tests/test_x.py`"
                           " (or set project.test_micro_command in .compass/config.yml)")
    command = _neutralise_coverage(command)
    code, out, warnings = _run_test(command)
    for w in warnings:
        sys.stderr.write(f"compass tdd-red: warning - {w}\n")
    excerpt = "\n".join(out.splitlines()[-25:])
    if code == 0:
        raise CompassError(
            "compass tdd-red: the test command PASSED (exit 0) - there is no "
            "red to record. Strategy S2 is red-before-green: write a test that "
            "actually fails first.\n--- output (tail) ---\n" + excerpt
        )
    rejection = _red_rejection_reason(code, command)
    if rejection:
        raise CompassError(
            "compass tdd-red: the test command DID NOT RUN - %s. That is not a "
            "failing test, so there is no red to record.\n"
            "A .red marker means a real, observed failure is on record; the "
            "pre-tool hook unlocks code edits on the strength of it. Fix the "
            "command so the test actually runs, then try again.\n"
            "  command: %s\n--- output (tail) ---\n%s"
            % (rejection, " ".join(command), excerpt)
        )
    payload = {
        "command": " ".join(command),
        "scenario": scenario,          # the scenario this red is evidence FOR
        "exit_code": code,
        "passed": False,
        "timestamp": now_iso(),
        "log_excerpt": excerpt,
        "_full_log": out,
    }
    if verified_by:
        payload["verified_by"] = verified_by   # R8: a sanctioned non-unit red
    ev_path = _write_evidence(task_dir, "red", payload)
    open(os.path.join(task_dir, ".red"), "w").close()  # the hook reads this
    payload.pop("_full_log", None)
    bound = f" (bound to {scenario})" if scenario else " (unbound - consider --scenario)"
    print(f"compass tdd-red: failing test recorded (exit {code}){bound}.")
    print(f"  evidence : {ev_path}")
    print(f"  marker   : {os.path.join(task_dir, '.red')}  (the pre-tool hook "
          f"will now allow code edits)")
    return 0


def _source_tree_hash(project_root):
    """Compute a stable SHA-256 of the source tree under project_root.

    Covers all *.py, *.md, *.yml, *.yaml, *.json, *.toml files, ordered by
    their relative path (deterministic). Excludes .compass/, .git/,
    __pycache__/, .venv/, node_modules/, and evidence/ directories.

    Returns a hex digest string. Performance target: < 200 ms on typical
    project trees (< 100 MB of source files).

    DD-7: hash is content + path, deterministic. Used by cmd_tdd_green to
    detect whether any source file changed between two invocations.
    """
    _EXCLUDED_DIRS = {".compass", ".git", "__pycache__", ".venv",
                      "node_modules", "evidence"}
    _INCLUDED_EXTS = {".py", ".md", ".yml", ".yaml", ".json", ".toml"}

    h = hashlib.sha256()
    # Walk the tree in sorted order to be deterministic across file systems
    for root, dirs, files in os.walk(project_root):
        # Prune excluded directories in-place so os.walk skips them
        dirs[:] = sorted(d for d in dirs if d not in _EXCLUDED_DIRS)
        for fname in sorted(files):
            ext = os.path.splitext(fname)[1].lower()
            if ext not in _INCLUDED_EXTS:
                continue
            full = os.path.join(root, fname)
            rel = os.path.relpath(full, project_root)
            # Hash the relative path (so renames are detected) then content
            h.update(rel.encode("utf-8", errors="replace"))
            try:
                with open(full, "rb") as fh:
                    h.update(fh.read())
            except OSError:
                pass  # file disappeared mid-walk - skip it
    return h.hexdigest()


def _tdd_state_path(task_dir):
    """Path to the CLI-internal sidecar that tracks the source-tree hash and
    attempt counter between tdd-green invocations. Not part of task.yml schema.
    """
    return os.path.join(task_dir, "evidence", ".tdd-state.json")


def _load_tdd_state(task_dir, scenario):
    """Load the per-scenario TDD state from the sidecar file.

    Returns a dict with keys: 'tree_hash' (str), 'attempts' (int),
    'scenario' (str|None). Returns a fresh empty state if absent or unreadable.
    """
    path = _tdd_state_path(task_dir)
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            return {}
        # State is keyed by scenario id (or "" for unbound runs)
        key = scenario or ""
        return data.get(key) or {}
    except (OSError, json.JSONDecodeError):
        return {}


def _save_tdd_state(task_dir, scenario, tree_hash, attempts, command=None):
    """Persist the per-scenario TDD state in the sidecar file."""
    path = _tdd_state_path(task_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    existing = {}
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                existing = json.load(fh) or {}
        except (OSError, json.JSONDecodeError):
            existing = {}
    key = scenario or ""
    existing[key] = {"tree_hash": tree_hash, "attempts": attempts,
                     "command": command}
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(existing, fh, indent=2)


def cmd_tdd_green(args):
    task_dir = resolve_task_dir(args.task)
    scenario = _resolve_scenario(task_dir, getattr(args, "scenario", None))
    verified_by = getattr(args, "verified_by", None)
    if verified_by and verified_by not in _VERIFIED_BY_KINDS:
        raise CompassError(
            f"compass tdd-green: --verified-by '{verified_by}' is not a "
            f"recognised kind. Allowed: {sorted(_VERIFIED_BY_KINDS)}.")
    command = _micro_command(args, task_dir)
    if not command:
        raise CompassError("compass tdd-green needs a test command (-- <cmd>) "
                           "or project.test_micro_command in .compass/config.yml")
    command = _neutralise_coverage(command)
    code, out, warnings = _run_test(command)
    for w in warnings:
        sys.stderr.write(f"compass tdd-green: warning - {w}\n")
    excerpt = "\n".join(out.splitlines()[-25:])
    if code != 0:
        raise CompassError(
            f"compass tdd-green: the test command FAILED (exit {code}) - not "
            f"green yet. The .red marker is left in place.\n"
            f"--- output (tail) ---\n" + excerpt
        )
    # R2 signal (3): output-token cross-check. A zero exit whose output carries
    # a known-runner fail-token is a suspected masked failure - refuse rather
    # than record a clean green on a contradictory signal (TRC-R2-5).
    fail_token = _output_fail_token(out)
    if fail_token:
        raise CompassError(
            f"compass tdd-green: the command exited 0 but its output shows a "
            f"failure token ('{fail_token}') - a possible masked failure. "
            f"Refusing to record a green on a contradictory signal. The .red "
            f"marker is left in place.\n--- output (tail) ---\n" + excerpt
        )

    # --- DD-7: attempts + rerun_without_change detection --------------------
    # Find the project root: walk up from the task_dir to the directory that
    # contains .compass/ - that is the project root the hash covers.
    project_root = find_upwards(task_dir, ".compass") or task_dir
    current_hash = _source_tree_hash(project_root)
    prior_state = _load_tdd_state(task_dir, scenario)
    prior_hash = prior_state.get("tree_hash")
    prior_attempts = prior_state.get("attempts") or 0

    # The command matters as much as the tree. Running the SAME assertion again
    # with nothing changed is the flaky-test laundering this flag exists to
    # catch; running a DIFFERENT one - the narrow suite, then the full suite,
    # which is what Verify asks for - is a new assertion, not a retry.
    current_command = " ".join(command)
    prior_command = prior_state.get("command")

    if prior_hash is None:
        # First invocation for this scenario - clean first pass
        attempts = 1
        rerun_without_change = False
    elif prior_hash == current_hash and prior_command == current_command:
        # Same tree, same command: nothing changed and nothing new was asked
        attempts = prior_attempts + 1
        rerun_without_change = True
    else:
        # Either the tree changed (real work) or the command did (a different
        # assertion). Both are legitimate progress.
        attempts = prior_attempts + 1
        rerun_without_change = False

    # Persist the updated state for the next invocation
    _save_tdd_state(task_dir, scenario, current_hash, attempts, current_command)

    payload = {
        "command": " ".join(command),
        "scenario": scenario,          # the scenario this green is evidence FOR
        "exit_code": 0,
        "passed": True,
        "attempts": attempts,
        "timestamp": now_iso(),
        "log_excerpt": excerpt,
        "_full_log": out,
    }
    # BF-1: always record the marker when attempts > 1. Absence of the field on
    # a multi-attempt record fails the no-trusted-rerun check (DD-3: incomplete
    # evidence cannot clear G4). The marker is informative either way - true
    # means "no source change between attempts" (the failure mode S5 protects
    # against), false means "source did change" (a legitimate red→green path).
    if attempts > 1:
        payload["rerun_without_change"] = rerun_without_change
    if verified_by:
        payload["verified_by"] = verified_by   # R8: carry the guard kind forward
    ev_path = _write_evidence(task_dir, "green", payload)
    # If scenario-bound, also write a scenario-specific copy so multiple
    # scenarios' green records do not overwrite each other.
    rel_path = "evidence/green.json"
    if scenario:
        scn_name = "green-" + scenario.replace("/", "_")
        _write_evidence(task_dir, scn_name, payload)
        rel_path = f"evidence/{scn_name}.json"
    # Upsert a test-run entry in the task's evidence registry - the registry
    # is what `compass check` reads, so the green has to land there.
    _upsert_test_run_evidence(task_dir, scenario, rel_path)
    red_marker = os.path.join(task_dir, ".red")
    if os.path.exists(red_marker):
        os.remove(red_marker)
    bound = f" (bound to {scenario})" if scenario else " (unbound - consider --scenario)"
    print(f"compass tdd-green: passing suite recorded (exit 0){bound}.")
    print(f"  evidence : {ev_path}")
    print("  registry : task.yml `evidence:` updated with the test-run entry")
    print("  marker   : .red cleared - red -> green is on record.")
    return 0


def _upsert_test_run_evidence(task_dir, scenario, rel_path):
    """Append or update a test-run entry in task.yml's evidence registry.
    Same scenario -> update in place; new -> append. This is what makes the
    green visible to `compass check`, which reads the registry, not the file."""
    task_path = os.path.join(task_dir, "task.yml")
    if not os.path.isfile(task_path):
        return  # no task.yml - Frame hasn't run; nothing to update
    try:
        task = load_yaml(task_path)
    except CompassError:
        return
    if not isinstance(task, dict):
        return
    reg = task.get("evidence") or []
    if not isinstance(reg, list):
        return
    existing = None
    for e in reg:
        if (isinstance(e, dict) and e.get("type") == "test-run"
                and e.get("scenario") == scenario):
            existing = e
            break
    if existing:
        existing["path"] = rel_path
    else:
        base = f"EV-T-{scenario}" if scenario else "EV-T"
        used = {e.get("id") for e in reg if isinstance(e, dict)}
        ev_id, n = base, 1
        while ev_id in used:
            n += 1
            ev_id = f"{base}-{n}"
        entry = {"id": ev_id, "type": "test-run", "path": rel_path}
        if scenario:
            entry["scenario"] = scenario
        reg.append(entry)
    task["evidence"] = reg
    save_task(task, task_path)
