---
id: ADR-022
title: The issue record is a manifest
status: accepted
date: 2026-08-27
supersedes: ''
superseded_by: ''
---

## Context

Compass named its central artifact twice and governed neither name.

Prose called it the **issue spine**. The file on disk was `task.yml` under
`.compass/work/<task-slug>/`. The module was `task_spine.py`. `task` is banned
in `governance/terminology.yml` with replacement `issue`, and `--task` was
already in `retired_machine_names` - so half the name was retired and the
other half was ungoverned.

Measured before the change:

| | |
|---|---|
| `spine` across the repository | **521** |
| `terms:` entries | 59, and **`spine` was not one of them** |
| uses glossed in place | **26** |
| `task.yml` | 773 uses across 182 files |
| `task_dir` / `task_spine` identifiers | 1,118 |
| issue directories on disk | 176 |

**The 26 glossed uses are the argument.** "The machine-readable issue spine"
is the sentence you write when you know the word will not land on its own. A
term readers arrive knowing is not explained on use, and this one was
explained 26 times.

`terminology.yml` states that the vocabulary is frozen and that changing it
carries the same ceremony as a decision record. This is that record. The file
is at `2.0.0-pre14`, so the 60th term goes in **before** 2.0.0 is cut - riding
that release rather than opening a second migration event, which is the
pattern ADR-012 already broke once by freezing the vocabulary "for years" and
seeing a second rename land three weeks later.

## Decision

**`issue spine` becomes `issue manifest`**, everywhere:

| Surface | Was | Is |
|---|---|---|
| prose | issue spine | issue manifest |
| the file | `task.yml` | `manifest.yml` |
| its root key | `task:` | `issue:` |
| the path slug | `<task-slug>` | `<issue-slug>` |
| the module | `task_spine.py` | `manifest.py` |
| the helpers | `resolve_task_dir`, `load_task`, `save_task` | `resolve_issue_dir`, `load_manifest`, `save_manifest` |

**Why `manifest`.** The file lists an issue's assessment, delivery approach,
stages, gates, scenarios, evidence and changed files, and points at the prose
artifacts beside it. That is what a manifest is, and engineers have already
met the word in that exact sense - `package.json`, `Cargo.toml`, a Kubernetes
manifest. The brief's constraint was that the replacement must be a term teams
already understand rather than a metaphor Compass has to teach, and the
mechanical form of that test is: **the word can be used in a sentence with no
apposition after it.** "Written into the issue manifest" stands. "Written into
the issue spine" reaches for a definition, and 26 sentences took it.

**Why `resolve_issue_dir` and not `resolve_manifest_dir`.** What it resolves
is the *issue's directory*, which holds the manifest among other files. Naming
it after one of its contents would be a second wrong name.

## Alternatives considered

**Rename the prose only.** Cheapest, and it leaves `task.yml` on disk under a
name the vocabulary bans. A half-renamed noun teaches a reader that Compass's
names are approximate, which is worse than either end state.

**Keep the module and helpers, rename only the artifact.** Rejected once the
cost was measured: the review guessed "a few hundred call sites" and the
actual figure is **105** - `resolve_task_dir` 45, `load_task` 28, `save_task`
23, `task_spine` 9. At 105 the argument for leaving them collapses, and the
alternative is `load_task` reading a manifest, which is this decision's own
problem one layer down and harder to see.

**`issue.yml` rather than `manifest.yml`.** The directory is already the
issue: `.compass/work/<issue-slug>/issue.yml` says "issue" twice and still
does not say what the file holds.

## Consequences

**Backward compatibility holds, and is demonstrated rather than assumed.**
`cli/migrate-map.yml` gains one row and `SPINE_KEY_MAP` gains one entry; the
read side resolves `manifest.yml` first and `task.yml` second, the same order
every other renamed artifact uses. A project that never runs `compass migrate`
keeps working (ADR-006).

**The archive is migrated, not frozen** (ADR-020). `compass migrate` renames
the file and maps the key on the same pass.

**The migration was rehearsed against a copy of the real archive before the
tree was touched**, because `.compass/work/` is gitignored in this repository
and its 176 records have no git history to restore from. That rehearsal found
three defects that would each have left the tree half-migrated:

1. `schemas/task.schema.json` still required `task` and forbade `issue`, so
   every old file stopped loading the moment the key map changed.
2. `compass migrate` named `task.yml` *after* the rename loop had moved it, so
   it wrote `manifest.yml` files that still carried `task:` inside.
3. The reader hard-coded the old filename, so nothing could read what the
   migrator had just written.

All three were found on the copy. None reached the real archive. The ordering
that produced that - tables and read side, then migrator, then sweep, then
module - is the safety argument and is recorded in the issue's design.

**`spine` is now banned** and covered by the vocabulary scan, which it never
was. It survives only in `cli/migrate-map.yml` (which must name both
spellings and is exempt from the scan for that reason), in the ban itself, in
this record, and in source comments explaining the change.

## References

- `.compass/work/name-the-issue-record/` - the issue, its measurements and its
  verification.
- ADR-006 - backward compatibility within a major version.
- ADR-012 - the vocabulary freeze this record amends.
- ADR-020 - the archive is migrated, not frozen.
