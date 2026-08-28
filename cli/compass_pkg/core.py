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


SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))  # realpath: resolve symlinks
FRAMEWORK_ROOT = os.path.dirname(SCRIPT_DIR)  # cli/.. == the compass repo root

COMPASS_VERSION = "4.0.0"    # the CLI's own version
COMPASS_SCHEMA_VERSION = "2.0"    # the manifest.yml schema this CLI writes
COMPASS_SCHEMA_VERSION_11 = "1.1"  # schema version that introduced manifest.yml.status


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


def resolve_issue_dir(slug=None):
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


# The manifest's filenames, current first and retired second. A FALLBACK the
# lookup tries second, never a substitution for the current name.
#
# The retired value is here rather than inline because a blanket rename over
# the tree has already collapsed a compatibility map to an identity once - on
# 2026-08-25, taking the fallback with it - and did it again to this very
# function during the manifest sweep, rewriting the pair to
# ("manifest.yml", "manifest.yml"). `test_nir_d3` asserts the two differ, so
# the same edit fails instead of passing silently.
MANIFEST_NAMES = ("manifest.yml", "task" + ".yml")


def manifest_path(task_dir):
    """The issue's manifest, by whichever name it carries on disk.

    Current name first, retired name second - the same order every other
    renamed artifact resolves in. A project that has not run `compass migrate`
    still reads, which ADR-006 requires and which matters more here than
    anywhere else: `.compass/work/` is gitignored in this repository, so its
    records have no git history to restore from.
    """
    for name in MANIFEST_NAMES:
        candidate = os.path.join(task_dir, name)
        if os.path.isfile(candidate):
            return candidate
    return os.path.join(task_dir, "manifest.yml")


def load_manifest(task_dir):
    path = manifest_path(task_dir)
    if not os.path.isfile(path):
        raise CompassError(
            f"no manifest.yml in {task_dir} - has the issue been assessed? "
            f"The manifest is what every command reads."
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
                f"normalisation). Update Compass, or migrate the manifest.yml."
            )
    return normalize_spine(task), path


# The 1.x -> 2.0 manifest key map. Read-side only: every loader normalises to
# the v2 canonical keys, so the rest of the CLI speaks one vocabulary and an
# un-migrated 1.x manifest (an adopter tree mid-upgrade, or the migration tool
# reading its own input) keeps working. Writers always emit 2.0.
SPINE_KEY_MAP = {
    # The root key naming the issue. It was `task`, which terminology.yml
    # bans with replacement `issue` - so half the artifact's name was retired
    # and the other half ungoverned. Old files still load through this row.
    "task": "issue",
    "readings": "assessment",
    "route": "delivery_approach",
    "phases": "stages",
    "fired_guardrails": "policy_rules_fired",
    "backfills": "follow_ups",
    "reframes": "reassessments",
    # ADR-023. Anthropic's platform docs split single-agent work from
    # multiagent work, and fan out "independent subtasks"; `topology` and
    # `stream` were Compass-only words for both. Manifests written before the
    # rename keep loading through these two rows (ADR-006).
    "topology": "orchestration",
    "stream_ceiling": "subtask_ceiling",
}
ASSESSMENT_KEY_MAP = {
    "blast_radius": "risk",
    "terrain": "familiarity",
    "magnitude": "size",
    "intent": "goal",
    "touches": "labels",
}


def migrate_map_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        os.pardir, "migrate-map.yml")


def migrate_map_section(name, fallback):
    """One section of `cli/migrate-map.yml`, or the in-module copy of it.

    THE READER LIVES HERE, not in the migration module, because `core` must not
    import `migrate` - that is the import cycle `test_cli_module_split` exists
    to prevent, and it caught this on the first run. `migrate` imports `core`
    already, so the dependency runs one way.

    The mapping itself stays in the data file: this module is a scanned
    surface, and the map has to name six retired words. The fallback is for a
    bare checkout with no framework install, and a test proves it equal to the
    file with the file made unreadable - a guard that reads the file both times
    is comparing it with itself.
    """
    try:
        with open(migrate_map_path(), encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
    except OSError:
        # No framework install beside this module - use the in-module copy.
        return dict(fallback)
    except yaml.YAMLError as exc:
        # A corrupt map is not a missing map. Falling back here would migrate
        # some manifests and not others, with nothing said; every reader of
        # every manifest goes through this path, so it fails loudly instead.
        raise CompassError(
            f"{migrate_map_path()} is not valid YAML, so retired names cannot "
            f"be migrated: {exc}")
    if not isinstance(data, dict):
        raise CompassError(
            f"{migrate_map_path()} must be a mapping of section name to "
            f"rename table; found {type(data).__name__}")
    section = data.get(name)
    if isinstance(section, dict) and section:
        return section
    return dict(fallback)


# The fallback copy. Retired spellings in a scanned surface would normally be a
# violation; this is the one place they are unavoidable, and the scan exemption
# for it is recorded in governance/terminology.yml.
_V1_STAGE_KEYS = {
    "frame": "assess", "specify": "define", "clarify": "refine",
    "distribute": "breakdown", "build": "implement", "land": "ship",
}


def _stage_key_renames():
    return migrate_map_section("stage_keys", _V1_STAGE_KEYS)


def normalize_spine(task):
    """Return the manifest with v2 canonical keys, whatever generation it was
    written in. A v2 key present alongside its v1 twin wins; the v1 key is
    dropped either way. Idempotent on a v2 manifest."""
    if not isinstance(task, dict):
        return task
    out = {}
    for k, v in task.items():
        k2 = SPINE_KEY_MAP.get(k, k)
        if k2 in out and k in SPINE_KEY_MAP:
            continue
        out[k2] = v
    # Stage keys. `frame` was banned as a phase name at the v2 freeze and
    # survived as a live machine key, because governance/*.yml is not a scanned
    # surface. Ninety-four landed issues carry the retired spellings, so they
    # are mapped forward on load and rewritten on disk by `compass migrate`
    # (ADR-006: accept both, remove the old at the major version).
    st = out.get("stages")
    if isinstance(st, dict):
        renames = _stage_key_renames()
        mapped = {}
        for k, v in st.items():
            k2 = renames.get(k, k)
            if k2 in mapped and k in renames:
                continue
            mapped[k2] = v
        out["stages"] = mapped

    a = out.get("assessment")
    if isinstance(a, dict):
        a2 = {}
        for k, v in a.items():
            k2 = ASSESSMENT_KEY_MAP.get(k, k)
            if k2 in a2 and k in ASSESSMENT_KEY_MAP:
                continue
            a2[k2] = v
        out["assessment"] = a2
    # Follow-up states renamed with the CLI-voice slice: 1.x manifests carry
    # owed/paid; readers see outstanding/resolved. Value map, mirroring the
    # key map above; the migrate tool rewrites them on disk in its slice.
    if out.get("delivery_approach") in SHAPE_VALUE_MAP:
        out["delivery_approach"] = SHAPE_VALUE_MAP[out["delivery_approach"]]
    fups = out.get("follow_ups")
    if isinstance(fups, list):
        for f in fups:
            if isinstance(f, dict) and f.get("status") in FOLLOW_UP_STATUS_MAP:
                f["status"] = FOLLOW_UP_STATUS_MAP[f["status"]]
    # Gate ids. ADR-023 renamed `verify.fitness` to `verify.architecture`.
    # This is not cosmetic: `compass check` looks a gate's accepted evidence
    # types up BY ID, and an id that no longer resolves yields None, which
    # skips the type requirement instead of failing it. An archived gate would
    # then clear with a written note - the one thing a mechanical gate refuses.
    gates = out.get("gates")
    if isinstance(gates, list):
        gate_renames = migrate_map_section("gate_ids", GATE_ID_MAP)
        for g in gates:
            if isinstance(g, dict) and g.get("id") in gate_renames:
                g["id"] = gate_renames[g["id"]]
    # Evidence types. ADR-023 renamed `coherence-check` to `consistency-check`;
    # a manifest written before that keeps clearing its gate (ADR-006).
    ev = out.get("evidence")
    if isinstance(ev, list):
        ev_renames = migrate_map_section("values", {}).get(
            "evidence_type", EVIDENCE_TYPE_MAP)
        for entry in ev:
            if isinstance(entry, dict) and entry.get("type") in ev_renames:
                entry["type"] = ev_renames[entry["type"]]
    # Friction categories. ADR-023 retired `ceremony`, and the enum holds
    # single tokens, so the pair became over-weight / under-weight. A manifest
    # written before that keeps loading (ADR-006).
    friction = out.get("friction")
    if isinstance(friction, list):
        renames = migrate_map_section("values", {}).get(
            "friction_category", FRICTION_CATEGORY_MAP)
        for entry in friction:
            if isinstance(entry, dict) and entry.get("category") in renames:
                entry["category"] = renames[entry["category"]]
    # Assess used to record an orchestration word; it now records a
    # `subtask_ceiling:` number, because it cannot know the shape before the
    # distribution map exists. A manifest written before that change carries the
    # word and no ceiling, so the word is read as the ceiling it always
    # implied. The recorded word is KEPT: an archived manifest says what it
    # said, and breakdown legitimately writes an orchestration of its own.
    if out.get("subtask_ceiling") is None:
        word = out.get("orchestration")
        if isinstance(word, str) and word:
            # A capped 1.x manifest recorded the sentence
            # "solo (capped to 1 worktree)"; its first word is the one to read.
            out["subtask_ceiling"] = RETIRED_ORCHESTRATION_CEILING.get(
                word.split(" ")[0], None)
    # The on-disk schema_version is preserved: readers must be able to say
    # honestly what generation a manifest was written in (the receipt reports
    # legacy manifests). Writers stamp the current version when they save.
    return out


# The orchestration words a pre-ceiling manifest could carry, and the ceiling
# each always implied. `multiagent` is None - unbounded - for the same reason the
# evaluator's table said so: no number for it exists anywhere in the policy.
#
# This table is why ADR-023 could retire the words rather than rename them.
# They were already only being converted to these three numbers before
# anything used them, so the route shapes now declare the number and the
# conversion is gone from `routing`. The table stays here because archived
# manifests still carry the words and have to keep reading.
RETIRED_ORCHESTRATION_CEILING = {"solo": 1, "solo-or-pair": 2, "swarm": None}  # vocabulary-scan: allow - names the retired words archived manifests carry (ADR-006)


# 1.x follow-up states -> their v2 spellings, applied read-side by
# normalize_spine above.
FOLLOW_UP_STATUS_MAP = {"owed": "outstanding", "paid": "resolved"}

# The in-module fallback for the friction rename, used when no framework
# install is present to read cli/migrate-map.yml from.
FRICTION_CATEGORY_MAP = {"over-ceremony": "over-weight",
                         "under-ceremony": "under-weight"}

# The in-module fallback for the evidence-type rename, same contract.
EVIDENCE_TYPE_MAP = {"coherence-check": "consistency-check"}

# The in-module fallback for the gate-id rename, same contract.
GATE_ID_MAP = {"verify.fitness": "verify.architecture"}

# The in-module fallback for the guardrail check rename. A project that ran
# /compass:init before ADR-023 names the retired spelling in its own
# guardrails.yml; the check still ships, so resolve the name rather than
# reporting it as unimplemented.
CHECK_NAME_MAP = {"coherence-check-passes": "consistency-check-passes"}

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
# layer prints. The manifest keeps the machine value; the terminal never
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


# The stage-name half of the same boundary: nothing retired is printed,
# whatever the key underneath is called.
#
# THIS MAP IS KEYED ON THE CURRENT KEYS, not the retired ones. `normalize_spine`
# maps a retired key forward on load, so by the time anything is displayed the
# key is already `assess`, `define` and so on - a map still keyed on `frame`
# would silently stop matching and print the raw key.
#
# It IS an identity map now, and that is the point rather than an oversight.
# The accept phase kept `assess` displaying as "triage" and `plan` as "design"
# so the internals could move without changing a word anyone read; the command
# renames landed next, and the two halves finally agree.
#
# The map stays rather than being deleted, so the display layer remains the one
# place a stage name is chosen. The next rename edits this table instead of
# hunting for print sites - which is what the two entries above used to be for.
STAGE_DISPLAY = {
    "assess": "assess",
    "define": "define",
    "refine": "refine",
    "plan": "plan",
    "breakdown": "breakdown",
    "implement": "implement",
    "verify": "verify",
    "ship": "ship",
}


def display_stage(value):
    """The v2 pipeline-stage name for a machine stage key."""
    return STAGE_DISPLAY.get(str(value or ""), str(value or ""))


def save_manifest(task, path):
    with open(path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(task, fh, sort_keys=False, default_flow_style=False)


# --- architecture loading (Frame mechanism) ----------------------------------
# Inv-1: readings stays judgement-only. The load record goes to
# architecture-loaded.yml (a separate file), never into manifest.yml.readings.
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

    # Write to task dir (never to manifest.yml.readings - Inv-1)
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
    raw = dict(shape.get("stages") or shape.get("phases") or {})
    # And the KEYS inside it, not only the block's own name. A policy written
    # before this rename says `frame:` where the current one says `assess:`,
    # and the evaluator prints these straight - so without this the tool that
    # computes the approach is the loudest place a retired name still appears.
    renames = _stage_key_renames()
    out = {}
    for k, v in raw.items():
        k2 = renames.get(k, k)
        if k2 in out and k in renames:
            continue
        out[k2] = v
    return out


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

    148 issue directories predate the registry. A missing one is the
    ordinary case, never a fault.
    """
    path = manifest_path(task_dir)
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


# Kinds this framework renamed, and the filename a landed issue still holds.
# Read-side only: the resolver finds the old file, and `compass migrate`
# rewrites it on disk (ADR-006).
_RENAMED_KIND_FILES = {
    # kind -> the filename a LANDED issue still holds. The values are the
    # RETIRED names on purpose: this map is the only reason an issue that
    # shipped before the rename still resolves. It is a FALLBACK the lookup
    # tries SECOND, never a substitution for the current name.
    #
    # A blanket rename over the tree rewrote both values to the current
    # filenames on 2026-08-25, quietly collapsing the map to an identity and
    # taking the compatibility path with it. `test_trc_b2` asserts each value
    # differs from its key, so the same edit fails instead of passing.
    "technical-design": "design.md",
    "intent": "prd.md",
}


def _flat_names(kind):
    """Every filename to try for a kind, in preference order.

    The name this framework writes TODAY always comes first; a renamed kind
    appends the retired filename, so an issue that landed before the rename
    still resolves.

    The order is load-bearing in both directions, and getting it wrong is
    silent either way. This returned the retired name ALONE until 2026-08-25,
    which made the lookup blind to every document written after the rename -
    `compass issue dashboard` reported a technical design sitting on disk as
    "not written yet". Preferring the retired name where both files exist is
    the opposite failure: every reader would quietly take the stale document.
    """
    current = kind if kind.endswith(".md") else kind + ".md"
    retired = _RENAMED_KIND_FILES.get(kind)
    if retired and retired != current:
        return [current, retired]
    return [current]


def _flat_name(kind):
    """The filename a kind is written under today.

    Only the current name. For the retired one a landed issue may still hold,
    ask `_flat_names`.
    """
    return _flat_names(kind)[0]


def _first_flat_on_disk(task_dir, kind):
    """The first of a kind's candidate filenames that is actually there."""
    for candidate in _flat_names(kind):
        path = os.path.join(task_dir, candidate)
        if os.path.isfile(path):
            return path
    return None


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
    # Current name first, then the retired one - the same order, through the
    # same helper, as `resolve_artifact`. Two functions that both find an
    # artifact must not disagree about which file they found, and they did:
    # this one grew the fallback while the other kept looking only for the
    # retired name.
    flat = _first_flat_on_disk(task_dir, kind)
    if flat is not None:
        return flat
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
    flat = _first_flat_on_disk(task_dir, kind)
    # Both names, so a reader chasing an absence is not sent looking for a file
    # the framework does not write any more.
    tried = " or ".join(_flat_names(kind))

    if entry is not None and entry.get("status") == "omitted":
        return (OMITTED, None,
                entry.get("reason") or "omitted, with no reason recorded")

    if entry is not None and entry.get("path"):
        registered = os.path.join(task_dir, entry["path"])
        if os.path.isfile(registered):
            return FOUND, registered, "the registered path"
        if flat is not None:
            return FOUND, flat, (
                "the flat filename - the registered path %s is not there"
                % entry["path"])
        return (UNRESOLVABLE, None,
                "%s names %s, which does not exist, and there is no %s either"
                % (entry.get("id", "the entry"), entry["path"], tried))

    if flat is not None:
        return FOUND, flat, "the flat filename"
    return ABSENT, None, "no registry entry and no %s" % tried


def issue_arg(p):
    """The `--issue SLUG` argument, which many verbs take identically.

    One line repeated is one line to drift, and it was what pushed this file
    past the cap that keeps logic out of the entry point. The cap surfaced real
    duplication rather than an arbitrary limit, so the duplication went.
    """
    p.add_argument("--issue", dest="task", metavar="SLUG",
                   help="issue slug (default: current-task pointer)")
    return p
