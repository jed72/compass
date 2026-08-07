---
description: Pick up an existing Compass task from disk and continue it
argument-hint: "<task-slug>"
allowed-tools: Read, Write, Glob, Grep
---

# /compass:resume

Resume a task that already has state on disk - a later session, or a different
agent, picking up where the work was left. The artifacts were written precisely
so the process never has to be re-derived.

**Task:** $ARGUMENTS

## Procedure

1. **Locate the task.** Find `.compass/work/<task-slug>/`. If the slug is
   ambiguous or missing, list the available tasks and ask. Once found, write
   the slug into `.compass/current-task` - that pointer is how every `compass`
   call (and a later session) resolves to *this* task without a `--task` flag.
2. **Read `delivery-approach.md` and `task.yml` first.** `delivery-approach.md` is the human-readable
   contract for this task - the route, the per-phase weight, the gate set, the
   topology, the de-scope ledger; `task.yml` is its machine-readable spine, what
   the CLI reads. Everything else is read in light of them. If `delivery-approach.md` is a
   `--reframe` revision, read the latest revision.
3. **Read the artifacts in pipeline order** - `prd.md`, `acceptance-criteria.md`,
   `requirements-review.md`, `design.md`, `distribution-map.md`, role artifacts,
   `verification-report.md` - and the `devlog.md` for the running narrative.
4. **Determine where things stand.** Which phase is complete, which is next.
   Cross-check against the de-scope ledger so a collapsed phase counts as
   handled, not pending. Note any owed backfill.
5. **Report, then continue.** State plainly: the route, the last completed
   phase, the next command to run, and any blocker or owed backfill. Then
   continue from that phase - invoke the matching `/compass:*` command's
   procedure.

## When the artifacts do not answer the question

If `delivery-approach.md` does not explain the process from here, the Needle under-framed.
Say so and re-run Frame (`/compass:frame --reframe`) rather than improvising a
route. A guessed process is not a resumed task.
