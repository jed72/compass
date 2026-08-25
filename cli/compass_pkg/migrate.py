# =============================================================================
# The archive migration core - 1.x issue directories to schema 2.0.
#
# This module owns the whole v1-to-v2 on-disk mapping: the spine keys (via
# core.normalize_spine) and the artifact filenames (the map below, which
# moved here from the runtime resolver when the repository's own archive
# migrated - the runtime resolves v2 names only; this module is what reads
# old trees). The user-facing `compass migrate` verb in its own slice wraps
# migrate_tree with dry-run and reporting; the internal verb exists so this
# repository could migrate itself as the first fixture.
# =============================================================================
import os

import yaml

from compass_pkg.core import CompassError, normalize_spine

# v1 filename -> v2 filename, applied inside each issue directory.
V1_ARTIFACT_NAMES = {
    "brief.md": "intent.md",
    "spec.feature.md": "acceptance-criteria.md",
    "route.md": "delivery-approach.md",
    "clarifications.md": "requirements-review.md",
    "plan.md": "technical-design.md",
    "design.md": "technical-design.md",
    "prd.md": "intent.md",
    "spec.feature": "acceptance-criteria.feature",
}


# The reader lives in `core` - see its note. `migrate` imports `core` already,
# so keeping it there is what stops the import cycle.
from compass_pkg.core import migrate_map_path as _map_path
from compass_pkg.core import migrate_map_section as _map_section


def artifact_name_map():
    """The v1-to-v2 artifact map, read from the exempt data file
    (cli/migrate-map.yml) so the enforced CLI never teaches a v1 spelling;
    the in-module copy is the fallback for a bare checkout."""
    return _map_section("artifacts", V1_ARTIFACT_NAMES)


# The stage-key renames, in the same shape and for the same reason as the
# artifact names above: the enforced CLI must not carry a retired spelling in a
# string literal, so the mapping lives in the exempt data file and this is only
# the fallback for a bare checkout with no framework install.
V1_STAGE_KEYS = {
    "frame": "assess",
    "specify": "define",
    "clarify": "refine",
    "distribute": "breakdown",
    "build": "implement",
    "land": "ship",
}


def stage_key_map():
    """The retired-to-current stage keys, read from the exempt data file."""
    return _map_section("stage_keys", V1_STAGE_KEYS)


def colliding_artifacts(task_dir):
    """Retired filenames in this directory that claim the same current name.

    `artifacts:` is many-to-one in two places, because two renames landed on
    the same document: `brief.md` and `prd.md` both become `intent.md`, and
    `plan.md` and `design.md` both become `technical-design.md`. A directory
    holding both members of a pair has two files claiming one name, and no
    rule in the map says which is the real one.

    Returns {current_name: [retired names present]}, entries with two or more
    sources only. The caller refuses; picking by dict order silently kept the
    older file, which is the stale one.
    """
    sources = {}
    for old_name, new_name in artifact_name_map().items():
        if os.path.exists(os.path.join(task_dir, old_name)):
            sources.setdefault(new_name, []).append(old_name)
    return {new: sorted(olds) for new, olds in sources.items() if len(olds) > 1}


def plan_issue_dir(task_dir):
    """The dry-run twin of migrate_issue_dir: compute the change notes
    without writing anything."""
    notes = []
    for old_name, new_name in artifact_name_map().items():
        old_p = os.path.join(task_dir, old_name)
        new_p = os.path.join(task_dir, new_name)
        if os.path.exists(old_p) and not os.path.exists(new_p):
            notes.append(f"would rename {old_name} -> {new_name}")
    spine = os.path.join(task_dir, "task.yml")
    if os.path.isfile(spine):
        with open(spine, encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or {}
        migrated = normalize_spine(raw)
        if str(migrated.get("schema_version", "")).split(".")[0] != "2":
            migrated["schema_version"] = "2.0"
        if migrated != raw:
            notes.append("would rewrite the spine to schema 2.0")
    return notes


def cmd_migrate(args):
    """`compass migrate [root]` - dry-run by default; --apply executes.

    Wraps the core this repository's own archive migration proved.
    Idempotent: a migrated tree reports nothing to do.

    Refuses before writing anything if any directory holds two retired files
    that claim the same current name - see colliding_artifacts. The whole run
    stops rather than that one directory, because a partly-migrated tree is
    harder to reason about than one that was not touched."""
    root = getattr(args, "root", None) or os.path.join(".compass", "work")
    if not os.path.isdir(root):
        print(f"compass migrate: no issue directories under {root} - "
              "nothing to examine.")
        return 0
    apply_mode = bool(getattr(args, "apply", False))
    dirs = [e for e in sorted(os.listdir(root))
            if os.path.isdir(os.path.join(root, e))]

    # Checked across the whole tree BEFORE anything is written, and reported
    # on a dry run too - a dry run that promises a rename the apply cannot
    # perform is worse than the refusal.
    collisions = []
    for entry in dirs:
        for new_name, olds in colliding_artifacts(
                os.path.join(root, entry)).items():
            collisions.append("  %s: %s both become %s"
                              % (entry, " and ".join(olds), new_name))
    if collisions:
        raise CompassError(
            "two retired filenames claim the same current name, and nothing "
            "in the map says which is the real document:\n"
            + "\n".join(collisions)
            + "\n\nNothing was changed. Open both files, keep the one that is "
              "current, and move or delete the other - then re-run. Picking "
              "one automatically would silently keep whichever came first, "
              "which is the older file.")

    # One directory failing must not take the report with it. The notes used
    # to be printed after the loop, so an unparseable spine raised out of the
    # whole command: every rename already performed stayed on disk, unnamed,
    # under a raw traceback. Both spellings still resolve, so the half-migrated
    # tree WORKS - which is precisely why nobody would notice.
    changed = {}
    failed = {}
    for entry in dirs:
        d = os.path.join(root, entry)
        try:
            notes = (migrate_issue_dir(d) if apply_mode else plan_issue_dir(d))
        except Exception as exc:                    # noqa: BLE001
            # Deliberately broad: whatever one directory does wrong, the other
            # 109 still get migrated and reported. The reason is carried into
            # the report rather than swallowed.
            failed[entry] = "%s: %s" % (type(exc).__name__, exc)
            continue
        if notes:
            changed[entry] = notes

    if not changed and not failed:
        print("compass migrate: nothing to do - every issue directory "
              "already speaks schema 2.0.")
        return 0

    if changed:
        verb = "migrated" if apply_mode else "would change"
        noun = "issue directory" if len(changed) == 1 else "issue directories"
        print(f"compass migrate: {len(changed)} {noun} {verb} "
              f"under {root}:")
        for slug, notes in changed.items():
            print(f"  {slug}")
            for n in notes:
                print(f"    - {n}")

    if failed:
        noun = "directory" if len(failed) == 1 else "directories"
        print()
        print(f"compass migrate: {len(failed)} {noun} could NOT be migrated:")
        for slug, why in failed.items():
            print(f"  {slug}")
            print(f"    - {why}")
        print()
        print(f"{len(changed)} migrated, {len(failed)} left as they were. "
              "Fix the files named above and re-run - migration is "
              "idempotent, so the ones already done are skipped.")
        return 1

    if not apply_mode:
        print()
        print("This was a dry run - nothing was written. "
              "Run `compass migrate --apply` to execute.")
    return 0


def migrate_issue_dir(task_dir):
    """Migrate one issue directory in place: rename v1-named artifacts and
    rewrite the spine with v2 keys. Idempotent - a migrated directory is
    left untouched. Returns a list of human-readable change notes."""
    notes = []
    for old_name, new_name in artifact_name_map().items():
        old_p = os.path.join(task_dir, old_name)
        new_p = os.path.join(task_dir, new_name)
        if os.path.exists(old_p) and not os.path.exists(new_p):
            os.rename(old_p, new_p)
            notes.append(f"renamed {old_name} -> {new_name}")
    spine = os.path.join(task_dir, "task.yml")
    if os.path.isfile(spine):
        with open(spine, encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or {}
        migrated = normalize_spine(raw)
        if str(migrated.get("schema_version", "")).split(".")[0] != "2":
            migrated["schema_version"] = "2.0"
        if migrated != raw:
            # Serialise first, then replace atomically. `open(spine, "w")`
            # empties the file before safe_dump writes a byte, so a dump that
            # raised - an unexpected object type in the spine will do it - left
            # task.yml empty and the issue with no record at all. os.replace is
            # atomic on every platform Compass supports.
            body = yaml.safe_dump(migrated, sort_keys=False,
                                  default_flow_style=False, allow_unicode=True)
            tmp = spine + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                fh.write(body)
            os.replace(tmp, spine)
            notes.append("spine keys and values -> schema 2.0")
    return notes


def migrate_tree(work_root):
    """Migrate every issue directory under a work root. Returns
    {slug: [notes]} for the directories that changed."""
    changed = {}
    if not os.path.isdir(work_root):
        return changed
    for slug in sorted(os.listdir(work_root)):
        d = os.path.join(work_root, slug)
        if not os.path.isdir(d):
            continue
        notes = migrate_issue_dir(d)
        if notes:
            changed[slug] = notes
    return changed


def cmd_migrate_archive(args):
    """compass _migrate-archive --internal - migrate this repository's own
    work archive (and any work roots passed) to schema 2.0."""
    if not getattr(args, "internal", False):
        print("compass: compass _migrate-archive: the --internal flag is "
              "required. This is a private entry point - the user-facing "
              "migration verb ships in its own slice.")
        return 2
    roots = args.roots or [os.path.join(".compass", "work")]
    total = 0
    for root in roots:
        changed = migrate_tree(root)
        for slug, notes in changed.items():
            total += len(notes)
            print(f"  {root}/{slug}: {'; '.join(notes)}")
    print(f"compass _migrate-archive: {total} change(s) applied.")
    return 0
