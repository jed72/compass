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


SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))  # realpath: resolve symlinks
FRAMEWORK_ROOT = os.path.dirname(SCRIPT_DIR)  # cli/.. == the compass repo root

COMPASS_VERSION = "3.3.0"    # the CLI's own version
COMPASS_SCHEMA_VERSION = "2.0"    # the task.yml schema this CLI writes
COMPASS_SCHEMA_VERSION_11 = "1.1"  # schema version that introduced task.yml.status


class CompassError(Exception):
    """A user-facing error: printed without a traceback, exits non-zero."""


# --- small helpers -----------------------------------------------------------

def load_yaml(path):
    if not os.path.isfile(path):
        raise CompassError(f"not found: {path}")
    with open(path, "r", encoding="utf-8") as fh:
        try:
            return yaml.safe_load(fh) or {}
        except yaml.YAMLError as exc:
            raise CompassError(f"invalid YAML in {path}: {exc}")


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def find_upwards(start, rel):
    """Walk up from `start` looking for a path `rel`; return its dir or None."""
    cur = os.path.abspath(start)
    while True:
        if os.path.exists(os.path.join(cur, rel)):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            return None
        cur = parent


#: The files that make a `governance/` directory a declaration rather than a
#: directory that happens to share the name. Both must be present for the
#: directory to be usable; either one alone means the project declared
#: governance Compass cannot apply.
GOVERNANCE_FILES = ("routing-policy.yml", "guardrails.yml")

#: Markers of the project's own boundary. The upward walk does not go above the
#: first directory holding one of these, so a stray `governance/` in an outer
#: repository or a home directory cannot stop work inside a project.
BOUNDARY_MARKERS = (".compass", ".git")


def _governance_refusal(gov_dir, present, missing):
    """The message an incomplete project governance directory earns.

    This is also the migration path. A project in this state works today -
    its guardrails are quietly ignored - and fails on its first command after
    upgrading, so the message has to be actionable without reading the source.
    Two ways out, each one step.
    """
    shipped = os.path.join(FRAMEWORK_ROOT, "governance")
    return CompassError(
        "this project declares governance that Compass cannot apply.\n\n"
        f"  found   : {os.path.join(gov_dir, present)}\n"
        f"  missing : {os.path.join(gov_dir, missing)}\n\n"
        "Compass will not use its own defaults in place of yours without "
        "telling you, so nothing here is being applied.\n\n"
        "To keep your governance, add the missing file and edit it from there:\n"
        f"  cp {os.path.join(shipped, missing)} {gov_dir}/\n\n"
        "To use the shipped defaults instead, remove:\n"
        f"  {os.path.join(gov_dir, present)}"
    )


def find_governance():
    """The governance directory in force: the project's own, or the shipped one.

    Walks up from the working directory looking for a `governance/` holding at
    least one recognised file, and stops at the project boundary. What it finds
    decides the answer:

    - both files      -> that directory
    - one file only   -> refuse, and say which is missing and how to fix it
    - neither file    -> keep walking; the directory declared nothing
    - nothing at all  -> the framework's shipped defaults, silently

    The refusal is the point. Discovery used to look for `routing-policy.yml`
    alone, so a project shipping `guardrails.yml` beside no policy silently got
    the framework's governance and never learned its own was being ignored -
    which contradicts the promise that a declared guardrail cannot quietly
    become advisory.
    """
    cur = os.path.abspath(os.getcwd())
    while True:
        gov_dir = os.path.join(cur, "governance")
        if os.path.isdir(gov_dir):
            present = [f for f in GOVERNANCE_FILES
                       if os.path.isfile(os.path.join(gov_dir, f))]
            if len(present) == len(GOVERNANCE_FILES):
                return gov_dir
            if present:
                missing = next(f for f in GOVERNANCE_FILES if f not in present)
                raise _governance_refusal(gov_dir, present[0], missing)
            # Neither file: a directory that shares the name has declared
            # nothing. Walk past it, exactly as before.

        # Stop at the project's own boundary, inclusive of the directory that
        # marks it. Without this a project that declares no governance would
        # inherit - and could be refused by - a directory its author may not
        # know exists. When no marker is ever found the walk reaches the
        # filesystem root, which is the behaviour that shipped before this and
        # is left alone deliberately.
        if any(os.path.exists(os.path.join(cur, m)) for m in BOUNDARY_MARKERS):
            break
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent

    shipped = os.path.join(FRAMEWORK_ROOT, "governance")
    if os.path.isfile(os.path.join(shipped, "routing-policy.yml")):
        return shipped
    raise CompassError(
        "could not find governance/ - neither a project-local one nor the "
        "framework's shipped defaults. Run from inside a Compass project or repo."
    )


def find_compass_dir():
    """The project's .compass/ directory (walking up from cwd)."""
    proj = find_upwards(os.getcwd(), ".compass")
    if not proj:
        raise CompassError(
            "no .compass/ directory found - run from inside a Compass project."
        )
    return os.path.join(proj, ".compass")


def load_mode():
    """Read the adoption mode from .compass/config.yml: 'enforced' (default)
    or 'advisory'. In advisory mode every failure is still reported, but the
    CLI exits 0 - useful for piloting Compass without blocking delivery."""
    try:
        cfg_path = os.path.join(find_compass_dir(), "config.yml")
        if os.path.isfile(cfg_path):
            cfg = load_yaml(cfg_path) or {}
            mode = str(cfg.get("mode") or "enforced").strip().lower()
            if mode in ("advisory", "enforced"):
                return mode
    except CompassError:
        pass
    return "enforced"


def mode_banner(mode):
    """The visible banner so an advisory run is never mistaken for enforced."""
    if mode == "advisory":
        return ("[mode: advisory] - every failure below is reported but NOT "
                "blocking; exit code will be 0. Set `mode: enforced` in "
                ".compass/config.yml when the team is ready.")
    return "[mode: enforced]"


def exit_for_mode(failures, mode):
    """0 in advisory; 1 in enforced when there are failures; 0 otherwise."""
    if failures and mode == "advisory":
        return 0
    return 1 if failures else 0


def resolve_task_dir(slug=None):
    """Resolve an issue's working directory.

    Priority: explicit slug > .compass/current-task pointer > most recently
    modified dir under .compass/work/ (with a warning - ambiguous).
    """
    compass_dir = find_compass_dir()
    work = os.path.join(compass_dir, "work")
    if slug:
        d = os.path.join(work, slug)
        if not os.path.isdir(d):
            raise CompassError(f"no issue directory for slug '{slug}' under {work}")
        return d
    pointer = os.path.join(compass_dir, "current-task")
    if os.path.isfile(pointer):
        with open(pointer, "r", encoding="utf-8") as fh:
            s = fh.read().strip()
        if s:
            d = os.path.join(work, s)
            if os.path.isdir(d):
                return d
            sys.stderr.write(
                f"compass: .compass/current-task points at '{s}' but that "
                f"issue directory does not exist - ignoring.\n"
            )
    # fallback: most recently modified - warn, because this is the fragile path
    if not os.path.isdir(work):
        raise CompassError(f"no issues found: {work} does not exist")
    candidates = [
        os.path.join(work, d) for d in os.listdir(work)
        if os.path.isdir(os.path.join(work, d))
    ]
    if not candidates:
        raise CompassError(f"no issue directories under {work}")
    if len(candidates) > 1:
        sys.stderr.write(
            "compass: no --issue slug and no .compass/current-task pointer - "
            "falling back to the most recently modified issue directory. This "
            "is ambiguous; write .compass/current-task to be sure.\n"
        )
    return max(candidates, key=os.path.getmtime)


def load_task(task_dir):
    path = os.path.join(task_dir, "task.yml")
    if not os.path.isfile(path):
        raise CompassError(
            f"no task.yml in {task_dir} - has triage run? task.yml is the "
            f"machine-readable issue spine."
        )
    task = load_yaml(path)
    # schema_version compatibility: a major mismatch is unsafe to silently run
    # against - the shape may have changed. Same major is OK (additive); absent
    # is OK in 1.0 for back-compat with pre-versioned files.
    sv = task.get("schema_version")
    if sv:
        try:
            major = str(sv).split(".")[0]
        except Exception:
            major = None
        if major is not None and major not in ("1", "2"):
            raise CompassError(
                f"{path}: schema_version is '{sv}', but this CLI handles "
                f"'{COMPASS_SCHEMA_VERSION}' (and reads 1.x by key "
                f"normalisation). Update Compass, or migrate the task.yml."
            )
    return normalize_spine(task), path


# The 1.x -> 2.0 spine key map. Read-side only: every loader normalises to
# the v2 canonical keys, so the rest of the CLI speaks one vocabulary and an
# un-migrated 1.x spine (an adopter tree mid-upgrade, or the migration tool
# reading its own input) keeps working. Writers always emit 2.0.
SPINE_KEY_MAP = {
    "readings": "assessment",
    "route": "delivery_approach",
    "phases": "stages",
    "fired_guardrails": "policy_rules_fired",
    "backfills": "follow_ups",
    "reframes": "reassessments",
}
ASSESSMENT_KEY_MAP = {
    "blast_radius": "risk",
    "terrain": "familiarity",
    "magnitude": "size",
    "intent": "goal",
    "touches": "labels",
}


def normalize_spine(task):
    """Return the spine with v2 canonical keys, whatever generation it was
    written in. A v2 key present alongside its v1 twin wins; the v1 key is
    dropped either way. Idempotent on a v2 spine."""
    if not isinstance(task, dict):
        return task
    out = {}
    for k, v in task.items():
        k2 = SPINE_KEY_MAP.get(k, k)
        if k2 in out and k in SPINE_KEY_MAP:
            continue
        out[k2] = v
    a = out.get("assessment")
    if isinstance(a, dict):
        a2 = {}
        for k, v in a.items():
            k2 = ASSESSMENT_KEY_MAP.get(k, k)
            if k2 in a2 and k in ASSESSMENT_KEY_MAP:
                continue
            a2[k2] = v
        out["assessment"] = a2
    # Follow-up states renamed with the CLI-voice slice: 1.x spines carry
    # owed/paid; readers see outstanding/resolved. Value map, mirroring the
    # key map above; the migrate tool rewrites them on disk in its slice.
    if out.get("delivery_approach") in SHAPE_VALUE_MAP:
        out["delivery_approach"] = SHAPE_VALUE_MAP[out["delivery_approach"]]
    fups = out.get("follow_ups")
    if isinstance(fups, list):
        for f in fups:
            if isinstance(f, dict) and f.get("status") in FOLLOW_UP_STATUS_MAP:
                f["status"] = FOLLOW_UP_STATUS_MAP[f["status"]]
    # Triage used to record a `topology:` word; it now records a
    # `stream_ceiling:` number, because it cannot know a topology before the
    # distribution map exists. A spine written before that change carries the
    # word and no ceiling, so the word is read as the ceiling it always
    # implied. The recorded topology is KEPT: an archived spine says what it
    # said, and breakdown legitimately writes a topology of its own.
    if out.get("stream_ceiling") is None and "stream_ceiling" not in out:
        topo = out.get("topology")
        if isinstance(topo, str) and topo:
            # A capped 1.x spine recorded the sentence
            # "solo (capped to 1 worktree)"; its first word is the topology.
            out["stream_ceiling"] = TOPOLOGY_STREAM_CEILING.get(
                topo.split(" ")[0], None)
    # The on-disk schema_version is preserved: readers must be able to say
    # honestly what generation a spine was written in (the receipt reports
    # legacy spines). Writers stamp the current version when they save.
    return out


# The topology words a pre-ceiling spine could carry, and the ceiling each
# always implied. `swarm` is None - unbounded - for the same reason the
# evaluator's table says so: no number for it exists anywhere in the policy.
TOPOLOGY_STREAM_CEILING = {"solo": 1, "solo-or-pair": 2, "swarm": None}


# 1.x follow-up states -> their v2 spellings, applied read-side by
# normalize_spine above.
FOLLOW_UP_STATUS_MAP = {"owed": "outstanding", "paid": "resolved"}

# 1.x shape values -> the v2 change-type values (machine spelling,
# hyphenated). Read-side via normalize_spine; the evaluator
# canonicalises its own writes through the same map; the migrator
# persists it.
SHAPE_VALUE_MAP = {
    "express": "quick-fix",
    "standard": "feature",
    "expedition": "initiative",
}


def canonical_shape(value):
    # The v2 machine spelling for a delivery-approach value.
    return SHAPE_VALUE_MAP.get(str(value or ""), value)

# Machine delivery-approach values -> the v2 change-type names the display
# layer prints. The spine keeps the machine value; the terminal never
# shows it (the receipt is the most shareable screen Compass produces).
SHAPE_DISPLAY = {
    "express": "quick fix",
    "standard": "feature",
    "expedition": "initiative",
    # the v2 machine spelling renders without the hyphen
    "quick-fix": "quick fix",
}


def display_shape(value):
    """The v2 change-type name for a machine delivery-approach value."""
    return SHAPE_DISPLAY.get(str(value or ""), str(value or ""))


# The stage-name half of the same boundary. The spine and the routing policy
# keep the keys they have always had - renaming them needs a back-compat shim
# for every spine on disk, and is the rename slice's work - but nothing
# retired is printed, whatever the key underneath is called.
STAGE_DISPLAY = {
    "frame": "triage",
    "specify": "define",
    "clarify": "refine",
    "plan": "design",
    "distribute": "breakdown",
    "build": "implement",
    "verify": "verify",
    "land": "ship",
}


def display_stage(value):
    """The v2 pipeline-stage name for a machine stage key."""
    return STAGE_DISPLAY.get(str(value or ""), str(value or ""))


def save_task(task, path):
    with open(path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(task, fh, sort_keys=False, default_flow_style=False)


# --- architecture loading (Frame mechanism) ----------------------------------
# Inv-1: readings stays judgement-only. The load record goes to
# architecture-loaded.yml (a separate file), never into task.yml.readings.
# Inv-7: deterministic - same inputs produce same output; sha256 per artifact
#         lets downstream agents detect mid-task drift.
# Inv-8: backward compat - absence of architecture/ is silent (empty record).

#: Narrative files Frame looks for under architecture/ (in order).
_NARRATIVE_FILES = [
    "architecture/system-context.md",
    "architecture/relations.md",
    "architecture/ownership.md",
]

#: The optional structured file.
_INVARIANTS_FILE = "architecture/invariants.yml"


def _file_sha256(path: str) -> str:
    """Return the hex SHA-256 digest of the file at *path*."""
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _scan_adrs(arch_dir: str) -> list:
    """Return a list of ADR summary dicts from architecture/decisions/ADR-*.md.

    Each dict: {id, path, title, status}
    Frontmatter is parsed as YAML between the first pair of '---' lines.
    Raises ValueError on malformed YAML frontmatter (TRC-X1 - fail loudly on
    bad structured input, naming the file path and the parse error).
    Files with no frontmatter delimiters have their id/title/status inferred
    from the filename (missing frontmatter is not an error; bad YAML is).
    """
    decisions_dir = os.path.join(arch_dir, "decisions")
    if not os.path.isdir(decisions_dir):
        return []
    adrs = []
    for name in sorted(os.listdir(decisions_dir)):
        if not (name.startswith("ADR-") and name.endswith(".md")):
            continue
        # Derive id from filename as the reliable fallback.
        stem = name[:-3]  # strip .md
        parts = stem.split("-", 2)       # ADR-NNN-slug
        adr_id = "-".join(parts[:2]) if len(parts) >= 2 else stem
        rel_path = f"architecture/decisions/{name}"
        title, status = stem, "proposed"
        full = os.path.join(decisions_dir, name)
        text = open(full, encoding="utf-8").read()  # noqa: WPS515
        # Extract YAML frontmatter between first two '---' lines
        if text.startswith("---"):
            end = text.find("\n---", 3)
            if end != -1:
                fm_text = text[3:end].strip()
                try:
                    fm = yaml.safe_load(fm_text) or {}
                except yaml.YAMLError as exc:
                    raise ValueError(
                        f"ADR parse error in {full}: {exc}"
                    ) from exc
                title = fm.get("title", title)
                status = fm.get("status", status)
                if fm.get("id"):
                    adr_id = fm["id"]
        adrs.append({"id": adr_id, "path": rel_path,
                     "title": title, "status": status})
    return adrs


def frame_load_architecture(project_root: str, task_dir: str) -> dict:
    """Load the project's architecture/ artifacts into a structured record.

    Writes ``.compass/work/<task>/architecture-loaded.yml`` and returns the
    same dict.  Never raises on absent files (Inv-8).  Does raise on malformed
    invariants.yml (TRC-X1 - fail loudly on bad structured input).

    Schema (schema_version 1.0):
        schema_version: "1.0"
        loaded_at: <ISO timestamp>
        artifacts:
          - path: <relative to project_root>
            sha256: <hex>
            type: narrative | structured
            parsed: <inline content>   # structured only
        adrs:
          - id: "ADR-001"
            path: <relative path>
            title: <string>
            status: proposed | accepted | superseded
    """
    arch_dir = os.path.join(project_root, "architecture")
    artifacts: list = []

    if os.path.isdir(arch_dir):
        # 1. Narrative files
        for rel in _NARRATIVE_FILES:
            full = os.path.join(project_root, rel)
            if os.path.isfile(full):
                artifacts.append({
                    "path": rel,
                    "sha256": _file_sha256(full),
                    "type": "narrative",
                })

        # 2. Optional structured file - fail loudly on bad YAML (TRC-X1)
        inv_rel = _INVARIANTS_FILE
        inv_full = os.path.join(project_root, inv_rel)
        if os.path.isfile(inv_full):
            raw = open(inv_full, encoding="utf-8").read()
            try:
                parsed = yaml.safe_load(raw)
            except yaml.YAMLError as exc:
                raise CompassError(
                    f"invariants.yml parse error in {inv_full}: {exc}"
                )
            artifacts.append({
                "path": inv_rel,
                "sha256": _file_sha256(inv_full),
                "type": "structured",
                "parsed": parsed,
            })

        # 3. Discover ADRs
        adrs = _scan_adrs(arch_dir)
    else:
        # architecture/ absent - backward compat: produce an empty record
        adrs = []

    record = {
        "schema_version": "1.0",
        "loaded_at": now_iso(),
        "artifacts": artifacts,
        "adrs": adrs,
    }

    # Write to task dir (never to task.yml.readings - Inv-1)
    os.makedirs(task_dir, exist_ok=True)
    out_path = os.path.join(task_dir, "architecture-loaded.yml")
    with open(out_path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(record, fh, sort_keys=False, default_flow_style=False,
                       allow_unicode=True)

    return record


# --- the route evaluator (the deterministic core) ---------------------------

# when-condition dimension keys: a project policy written against the v1
# names keeps matching until it migrates.
def shape_stages(shape):
    """A route shape's per-stage weights, tolerating the retired key name.

    The policy-side analogue of SPINE_KEY_MAP: a project routing policy
    written before the v2 freeze says `phases:` where the current one says
    `stages:`. Living here rather than at the call site keeps every retired
    spelling in the one module that is allowed to name them, so the
    vocabulary scan can enforce that rule everywhere else.
    """
    return dict(shape.get("stages") or shape.get("phases") or {})


_WHEN_KEY_MAP = {
    "blast_radius": "risk", "terrain": "familiarity",
    "magnitude": "size", "intent": "goal", "touches": "labels",
    "touches_any": "labels_any", "touches_common": "labels_common",
}


def reading_matches(when, assessment):
    """Does a `when:` condition match the assessment? List value == any-of.
    Special key `labels_any`: intersect against the assessment's `labels`.
    Special key `any_of`: a list of sub-conditions, matching if ANY matches.

    Keys are otherwise ANDed, so `any_of` alongside another key means "that
    key AND one of these". `any_of` exists because a rule sometimes has to
    fire on genuinely alternative conditions - the human-sign-off guardrail
    applies to the four irreversible domains OR to critical risk, and
    expressing that as separate rules would split one rule into two that can
    drift apart.
    """
    for key, val in (when or {}).items():
        key = _WHEN_KEY_MAP.get(key, key)
        if key == "any_of":
            clauses = val if isinstance(val, list) else [val]
            if not any(reading_matches(c, assessment) for c in clauses):
                return False
        elif key == "labels_any":
            wanted = val if isinstance(val, list) else [val]
            have = assessment.get("labels") or []
            if not any(t in have for t in wanted):
                return False
        else:
            allowed = val if isinstance(val, list) else [val]
            if assessment.get(key) not in allowed:
                return False
    return True


# --- per-issue artifact names ------------------------------------------------
# The archive speaks the v2 filenames; the v1 fallback this function once
# carried retired when the repository's own archive migrated. The old-name
# map lives in compass_pkg.migrate, which is what reads un-migrated trees.
# The four answers a lookup can give. OMITTED and UNRESOLVABLE both mean "no
# document here" and they mean opposite things - one is a decision, the other is
# a broken record. Collapsing them is how a document stops being read while the
# review page reports it as deliberately left out.
FOUND = "found"
OMITTED = "omitted"
UNRESOLVABLE = "unresolvable"
ABSENT = "absent"


def _registry(task_dir):
    """The issue's artifact registry, or [] when it has none.

    Eighty-eight issues landed before this existed. A missing registry is the
    ordinary case, never a fault.
    """
    path = os.path.join(task_dir, "task.yml")
    if not os.path.isfile(path):
        return []
    try:
        task = load_yaml(path)
    except CompassError:
        return []
    arts = (task or {}).get("artifacts") if isinstance(task, dict) else None
    return arts if isinstance(arts, list) else []


def _entry_for(task_dir, kind):
    for e in _registry(task_dir):
        if isinstance(e, dict) and e.get("kind") == kind:
            return e
    return None


def _flat_name(kind):
    """The old flat filename for a kind - `design` -> `design.md`."""
    return kind if kind.endswith(".md") else kind + ".md"


def artifact_path(task_dir, name):
    """The on-disk path of a per-issue artifact, by its v2 filename.

    Registry-aware, and unchanged for its callers: it still returns a path. A
    registered path wins; the flat filename is the fallback, so an issue with
    no registry - or one whose registry does not mention this document - keeps
    working exactly as before.

    Callers that need to know WHY that is the answer want resolve_artifact().
    """
    kind = name[:-3] if name.endswith(".md") else name
    entry = _entry_for(task_dir, kind)
    if entry and entry.get("path"):
        registered = os.path.join(task_dir, entry["path"])
        if os.path.isfile(registered):
            return registered
    return os.path.join(task_dir, name)


def resolve_artifact(task_dir, kind):
    """Where a document is, and why that is the answer.

    Returns (state, path, reason):

      FOUND        path is real; reason says which route found it.
      OMITTED      the registry records a deliberate omission, with its reason.
      UNRESOLVABLE an entry names a path that is not there, and the flat
                   filename is not there either. The reason names both paths
                   tried, because the entry is wrong and someone has to fix it.
      ABSENT       no entry and no file. Ordinary for an issue that predates the
                   registry; not a fault on its own.
    """
    entry = _entry_for(task_dir, kind)
    flat = os.path.join(task_dir, _flat_name(kind))

    if entry is not None and entry.get("status") == "omitted":
        return (OMITTED, None,
                entry.get("reason") or "omitted, with no reason recorded")

    if entry is not None and entry.get("path"):
        registered = os.path.join(task_dir, entry["path"])
        if os.path.isfile(registered):
            return FOUND, registered, "the registered path"
        if os.path.isfile(flat):
            return FOUND, flat, (
                "the flat filename - the registered path %s is not there"
                % entry["path"])
        return (UNRESOLVABLE, None,
                "%s names %s, which does not exist, and there is no %s either"
                % (entry.get("id", "the entry"), entry["path"],
                   _flat_name(kind)))

    if os.path.isfile(flat):
        return FOUND, flat, "the flat filename"
    return ABSENT, None, "no registry entry and no %s" % _flat_name(kind)


def issue_arg(p):
    """The `--issue SLUG` argument, which many verbs take identically.

    One line repeated is one line to drift, and it was what pushed this file
    past the cap that keeps logic out of the entry point. The cap surfaced real
    duplication rather than an arbitrary limit, so the duplication went.
    """
    p.add_argument("--issue", dest="task", metavar="SLUG",
                   help="issue slug (default: current-task pointer)")
    return p
