---
description: Show the Compass board - what's blocked, in progress, next up, and done
argument-hint: "[task-slug]"
allowed-tools: Read, Bash, Glob, Grep
---

# /compass:status

Report the state of Compass work on disk. Read-only - this changes nothing.

**Scope:** $ARGUMENTS - if a task slug is given, drill into just that task; if
empty, render the board across every task under `.compass/work/`.

`/compass:status` answers *"what should I look at?"*. For the managed
cross-task view - triage, blockers, owed-backfill aggregation, and the periodic
digest - use `/compass:flow`.

## What this command is for

Someone asking for status wants what they would get from glancing at a physical
board: what is blocked, what is moving, what is next, what is done. In plain
English, in a few lines, with detail available if they ask.

They do **not** want a per-task dump of routes, phases, gate fractions and
artifact codes. Those are Compass's internal vocabulary; making the reader
decode them to find their own work inverts what the command is for.

So: **the board is the default. Everything else is drill-down.**

## Procedure - no argument (the board)

1. **Read the tasks.** List `.compass/work/*/`; `task.yml` is each task's spine.
   Prefer one scripted pass over per-task tool calls - a mature repo may hold
   hundreds, and the reader is waiting.

2. **Place each task in exactly one column**, most urgent first:

   | column | means |
   |---|---|
   | **BLOCKED** | cannot progress without a decision or an unpaid debt being settled: `compass check` fails, an owed backfill, a missing human approval on an irreversible change |
   | **READY TO LAND** | all gates green and `compass check` passes, but not yet marked landed - finished work nobody has closed |
   | **IN PROGRESS** | started, not finished: a `status: active` task, or artifacts present without a terminal status |
   | **NEXT UP** | explicitly queued to start. If the status vocabulary has no queued state, say so plainly rather than guessing - see step 4 |
   | **DONE** | any terminal status (`landed`, `landed-direct`, `superseded`, `concluded`) |

3. **Write each column as prose, not a table.** Name the task and say *why it is
   in that column* - the reason is the useful part. Two or three sentences per
   column. Where a column has many members, name the ones needing a decision and
   give a count for the rest.

   For **DONE**, a count is almost always enough. Nobody scans finished work.

4. **Account for what cannot be placed.** A task with no `task.yml`, or no
   `status:` field, cannot honestly go in any column. Report the count on its own
   line. Do not quietly drop it and do not guess: a board that silently omits
   part of the work looks complete when it is not.

5. **Lead with anything blocking a Land**, and keep the whole thing to one
   screen. If the reader wants route, phase, gates or evidence they will ask -
   or run `/compass:status <task-slug>`.

### Shape of a good answer

```
BLOCKED (2)
  gcp-internal-test-env-apply owes BF-POSTAPPLY, and it is the terraform-apply
  task, so it needs a human sign-off to move. address-comprehensive-review's
  backfill is actually done - recorded as `paid: true` where the check wants
  `status: paid`, so it is a one-word fix rather than real work.

READY TO LAND (1)
  pypsa-api-v020-extensions - all six gates green, check passes. Just needs its
  status flipped.

IN PROGRESS (5)
  import-coordinate-crs-normalisation is furthest along (specified and planned,
  not verified). The other four are barely started.

NEXT UP
  Nothing is marked as queued - Compass has no state for it, so this cannot be
  answered from disk.

DONE 131 landed. 94 more tasks have no recorded state at all.
```

That is the whole report. It fits on a screen, every line supports a decision,
and no Compass vocabulary leaks into it beyond task names.

## Procedure - with a task slug (drill-down)

Here the internals *are* the point. Report:

- **Route** - from `route.md` / `task.yml`: the nearest reference route, the
  four dimension readings, and any routing guardrail that fired.
- **Phase** - inferred from which artifacts exist: `route.md` -> Frame done;
  `spec.feature.md` -> Specify; `clarifications.md` -> Clarify; `plan.md` ->
  Plan; `distribution-map.md` -> Distribute; `verification-report.md` -> Verify.
  Cross-check the route's de-scope ledger so a *collapsed* phase is not reported
  as *missing*.
- **Gates** - from `verification-report.md` and `task.yml`'s `gates:`. Run
  `compass check --task <slug>` for the mechanical view (read-only).
  **Say when a check passes vacuously.** "no changed_files recorded yet" and
  "0/N pass gates" are green lines that assert nothing; reading them as progress
  is how a task lands untraced.
- **Owed backfills** - scan `route.md`'s de-scope ledger and the route's
  standing obligations. Flag loudly:
  - an unpaid **Hotfix backfill** (route stub not completed, reproduction test
    not promoted to a scenario, no root-cause devlog line);
  - an **unbacked marketing claim** - a claim in `positioning.md` with no
    passing scenario behind it;
  - any de-scoped artifact still marked owed.

## Note

If `route.md` is missing for a directory under `work/`, that task was started
without Frame - flag it as a guardrail violation, not merely an incomplete task.
On the board, that belongs in BLOCKED.
