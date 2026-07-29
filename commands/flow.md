---
description: The cross-task flow view - triage, blockers, owed backfills, and the periodic digest across all Compass work
argument-hint: "[--digest]"
allowed-tools: Read, Write, Bash, Glob, Grep
---

# /compass:flow

`/compass:status` looks *down* into one task. `/compass:flow` looks *across*
every task - it is the delivery-management function as a capability, not a
persona. Anyone can run it; it is not a role entry point.

Compass is task-centric by design: each task carries its own route, artifacts,
and gates. But a team runs many tasks at once, and nothing in the per-task
pipeline answers "what is the state of *everything*, and what needs a human's
attention first?" That is this command.

**Mode:** $ARGUMENTS - default is the live flow board; `--digest` writes a
dated digest file (see below).

## Setup

- Load the `flow-management` skill - it carries the triage heuristics, the
  blocker protocol, and the digest format.
- This command reads broadly and writes only the digest. It never edits a
  task's artifacts - task state is inferred from artifacts on disk, never
  set by a label.

## Procedure

1. **Enumerate.** List every task directory under `.compass/work/`. For each,
   read `route.md`, `task.yml` (the machine-readable spine), and whichever phase
   artifacts exist. To report a task's *mechanical* gate status you may run
   `compass check --task <slug>` - it is read-only and changes nothing.

2. **Triage each task.** Apply the `flow-management` triage heuristics:
   - **No `route.md`** → a guardrail violation (work started without Frame).
     Surface this above everything else.
   - **Stalled** → an in-progress phase with no `devlog.md` movement for longer
     than the route's expected cadence. Flag it and name the likely blocker.
   - **Route outgrown** → signs in the devlog that the task no longer fits its
     route. Recommend `/compass:frame --reframe`.
   - **Healthy** → progressing in line with its route.

3. **Build the board.** Group every task by pipeline phase: Framed · Specifying
   · Clarifying · Planning · Building · Verifying · Landing · Landed. One line
   per task: slug · route · phase · health · owner.

4. **Surface blockers.** For every blocked or stalled task, state what it is
   blocked on and who or what can unblock it. Anything needing a human decision
   goes to the top.

5. **Aggregate owed backfills.** `/compass:status` flags backfills per task;
   `/compass:flow` collects them all into one list - every unpaid Hotfix
   backfill, every unbacked marketing claim, every de-scoped artifact still
   owed, across all tasks.

6. **Read the calibration signal.** Run `compass calibration` - it reads the
   `reframes:` log across every task and reports whether the Needle is
   systematically over- or under-sizing routes (a run of "up" re-frames means
   the Needle keeps reading work lighter than it is). This is the framework's
   own feedback loop: a framework about right-sizing process has to be able to
   tell whether the right-sizing is any good. Surface the signal; if it leans,
   the fix is in `governance/routing-policy.yml` or the Frame rubric, not in
   any one task.

7. **Run rework-scan.** Run `compass rework-scan --format markdown` and embed
   the output in the report as a "Rework scan" section. This surfaces
   cross-task add-then-delete patterns within the configured window
   (`governance/signals.yml rework_scan.window_days`). The scan is a signal -
   it never gates, never modifies task state, and always exits 0 on detection
   (Inv-4: Flow advises, never gates). If the section is empty, record
   "0 rework instances detected" to confirm the scan ran.

8. **Report**, ordering by what needs attention first: human decisions →
   guardrail violations → blockers → owed backfills → rework signals →
   calibration signal → healthy in-flight → landed.

## `--digest`

With `--digest`, also write a dated digest to `.compass/flow/digest-{{DATE}}.md`
using the format in the `flow-management` skill: landed since the last digest,
in flight, blocked, owed backfills, rework signals, and next up. The digest is
the artifact a team reviews on a cadence - and `/compass:flow --digest` is a
natural fit for a scheduled task (e.g. a weekly run). It is append-only
history: never overwrite a prior digest.

The digest must include a **Rework scan** section produced by
`compass rework-scan --format markdown`. This section is informational - it
does not change any task's state, and a non-empty rework report does not block
or gate anything.

## Note

`/compass:flow` advises; it does not gate. The gates live in the per-task
pipeline where the evidence is. Flow's job is to make sure no task is quietly
stuck, off-route, or sitting on an unpaid debt - not to add another gate.
