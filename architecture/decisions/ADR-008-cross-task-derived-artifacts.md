---
id: ADR-008
title: Cross-task derived artifacts are generated from landed task scenarios at Land time; the derivation is reconstructible, idempotent, and never a source-of-truth
status: proposed
date: 2026-05-25
supersedes: ''
superseded_by: ''
---

## Context

Compass tasks accumulate scenario-level behaviour definitions in per-task
`spec.feature.md` files. After many tasks land, there is no single document
that describes the system's current behaviour — a reader must diff across
every landed task to understand what is currently true.

A "living system spec" that summarises current-behaviour across all landed
tasks would solve this. The question is: what kind of artifact is it, and
when and how is it produced?

Two naive answers fail:
- **Authoritative parallel spec:** a second file that teams hand-edit
  alongside per-task specs. This creates two sources of truth, divergence,
  and maintenance burden (ADR-004 explicitly rejects parallel specs).
- **Event registry:** a separate database or registry tracking landed
  behaviour changes. This adds a new on-disk concept (BR-009 friction) and
  breaks the "all state lives on disk in readable files" model (ADR-005).

The correct answer is a *derived artifact* — generated deterministically
from the authoritative per-task `spec.feature.md` files at Land time, with
a silent-overwrite contract, and carrying a "DERIVED FILE" header that makes
the contract visible.

## Decision

**The living system spec is a derived artifact, produced at Land time, that
is never a source-of-truth.**

The derivation algorithm:

1. Walk every `.compass/work/*/task.yml` whose `status` field equals
   `landed`. Tasks with `status: active` or tasks whose `task.yml` pre-dates
   the `status` field (schema_version `'1.0'`) are silently skipped.
2. For each landed task, read its `scenarios:` block and the linked
   `spec.feature.md` to recover the full Given/When/Then text.
3. Compose a `docs/system-spec.md` file with two sections:
   - **Current behaviour:** one entry per scenario, from the latest-landed
     task that defines a scenario for a given `intent` id. When two scenarios
     share the same intent id, the later-landed scenario wins.
   - **Archived behaviour:** scenarios that were superseded by a
     later-landed scenario with the same intent id. Each archive entry
     records the source task slug and the Land date that retired it.
4. Process tasks in Land-timestamp order (ascending), with task slug as the
   tiebreaker for tasks that landed in the same second.
5. Write the file atomically. The first non-empty line is:
   `<!-- DERIVED FILE — do not hand-edit; edit .compass/work/<task>/spec.feature.md -->`
6. The derivation is invoked from `scripts/integrate.sh` after combined
   regression passes, via the private CLI entry point
   `compass _derive-system-spec --internal`. The `--internal` flag is
   mandatory; without it the subcommand errors out. The subcommand is
   excluded from `compass --help` (leading-underscore convention).

**Backward compat (ADR-006):** `status` is an optional field in
`task.yml` schema `'1.1'`. The derivation walker treats absent or `'1.0'`-
schema task.ymls as `status: active` (not landed). Every existing adopter
task.yml continues to lint clean and is simply skipped by the walker.

**Idempotency:** re-running the derivation against unchanged inputs produces
a byte-identical `docs/system-spec.md`. The derivation has no in-memory
accumulation beyond the task walk.

**Reconstructibility:** deleting `docs/system-spec.md` and re-running the
derivation produces an identical file. The only inputs are the landed
task.ymls and their linked spec.feature.md files, all of which live on disk
under `.compass/work/` (ADR-005).

## Alternatives considered

| Alternative | Why considered | Why rejected |
|---|---|---|
| Hand-maintained living spec | Simple to understand; no code required | Creates a second source of truth; maintenance burden grows with every task; divergence is inevitable (ADR-004) |
| Separate registry file (e.g. `.compass/landed.yml`) | Provides a clean query interface | Adds a new on-disk concept; a second source of truth for landed state (the `task.yml.status` field is sufficient); breaks the "all task state lives in its task directory" rule |
| Derive on demand (not at Land) | Could be triggered any time | ADR-001: mechanism actions are predictable and bounded; an on-demand derivation that runs at arbitrary times is harder to reason about and harder to test; Land is the natural moment because it is when the landed set changes |
| Append-only (never overwrite old entries) | Preserves history inline | Makes the current-behaviour section unreadable; the archive appendix already serves the history need |
| Third public CLI verb (`compass spec`) | Clean public surface | Clarifications Q5 caps the new public verbs at `analyze` and `next`; a third verb violates the legibility budget (NFR-LEG-001); the private `_derive-system-spec` entry point is sufficient because the only caller is `scripts/integrate.sh` |

## Consequences

**Positive:**
- `docs/system-spec.md` is always a faithful summary of current behaviour
  across landed tasks, with no hand-maintenance required.
- The silent-overwrite contract means hand-edits are cheap to make (the
  editor knows they will be overwritten) and the file is always trustworthy
  after Land.
- The derivation is fully reconstructible from on-disk state alone — no
  database, no registry, no conversation context required (ADR-005).
- Backward compat: existing task.ymls without `status` are silently skipped,
  so adopters do not need to migrate before upgrading.

**Negative:**
- The `task.yml.status` schema change (`schema_version: '1.0'` → `'1.1'`)
  requires a schema update. The linter must accept both versions.
- `docs/system-spec.md` is empty or a stub until the first task lands;
  on a brand-new project it is created as part of the first Land.
- The "latest-landed wins" supersession rule is simple but lossy — it does
  not merge conflicting scenario text, it picks the winner. Future work could
  surface conflicts explicitly (TRC-F2 constrains this to "defined and
  stable", not "always merged").

## References

- `architecture-notes.md` §2 Inv-5, Inv-6, Inv-8 — invariants this decision must preserve
- `architecture-notes.md` §3 B-Risk 3, B-Risk 4 — concrete risks for the schema bump and integrate.sh call
- ADR-004 — one spec, many lenses; this decision follows the annotation-not-fork model
- ADR-005 — state lives on disk; the derivation honours this
- ADR-006 — backward compat is non-negotiable; the `status` field is optional with a safe default
- `plan.md` DD-3, DD-4 — the design decisions this ADR codifies
- `spec.feature.md` Group B (TRC-B1…B11, TRC-F2) — the acceptance scenarios
