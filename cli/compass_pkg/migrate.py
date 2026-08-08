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

from compass_pkg.core import normalize_spine

# v1 filename -> v2 filename, applied inside each issue directory.
V1_ARTIFACT_NAMES = {
    "brief.md": "prd.md",
    "spec.feature.md": "acceptance-criteria.md",
    "route.md": "delivery-approach.md",
    "clarifications.md": "requirements-review.md",
    "plan.md": "design.md",
    "spec.feature": "acceptance-criteria.feature",
}


def artifact_name_map():
    """The v1-to-v2 artifact map, read from the exempt data file
    (cli/migrate-map.yml) so the enforced CLI never teaches a v1 spelling;
    the in-module copy is the fallback for a bare checkout."""
    map_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "migrate-map.yml")
    try:
        with open(map_path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        artifacts = data.get("artifacts")
        if isinstance(artifacts, dict) and artifacts:
            return artifacts
    except OSError:
        pass
    return dict(V1_ARTIFACT_NAMES)


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
    Idempotent: a migrated tree reports nothing to do."""
    root = getattr(args, "root", None) or os.path.join(".compass", "work")
    if not os.path.isdir(root):
        print(f"compass migrate: no issue directories under {root} - "
              "nothing to examine.")
        return 0
    apply_mode = bool(getattr(args, "apply", False))
    changed = {}
    for entry in sorted(os.listdir(root)):
        d = os.path.join(root, entry)
        if not os.path.isdir(d):
            continue
        notes = (migrate_issue_dir(d) if apply_mode else plan_issue_dir(d))
        if notes:
            changed[entry] = notes
    if not changed:
        print("compass migrate: nothing to do - every issue directory "
              "already speaks schema 2.0.")
        return 0
    verb = "migrated" if apply_mode else "would change"
    noun = "issue directory" if len(changed) == 1 else "issue directories"
    print(f"compass migrate: {len(changed)} {noun} {verb} "
          f"under {root}:")
    for slug, notes in changed.items():
        print(f"  {slug}")
        for n in notes:
            print(f"    - {n}")
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
            with open(spine, "w", encoding="utf-8") as fh:
                yaml.safe_dump(migrated, fh, sort_keys=False,
                               default_flow_style=False, allow_unicode=True)
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
