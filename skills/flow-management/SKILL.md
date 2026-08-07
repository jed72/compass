---
name: flow-management
description: Cross-task flow management for Compass - triage heuristics, the blocker protocol, and the periodic digest format. Triggers on /compass:flow and whenever someone asks about the state of work across more than one task.
---

# Flow Management

Compass is task-centric: every task carries its own route, artifacts, and
gates, and the pipeline guarantees a single task is well-run. Flow management
is the layer *above* that - the cross-task view. It is the delivery-management
function expressed as a **capability**, not a persona. There is no
"delivery manager" role in Compass; there is `/compass:flow`, which anyone can
run.

This skill is the craft behind that command: how to triage a board of tasks,
how to handle a blocker, and how to write the digest.

## Why this is a capability, not a role

The builder-style approach modelled delivery as a persona agent with turf - it
"owned" the board, "assigned" work, "moved" issues between columns. Compass
deliberately does not. Task state is not a label someone sets; it is *inferred
from the artifacts on disk*. A task is in Build because `design.md` exists and
`verification-report.md` does not - not because someone moved a card. So flow
management has nothing to *own* and nothing to *move*. Its entire job is to
read the artifacts, notice what the per-task pipeline structurally cannot
(because each task only sees itself), and put the right thing in front of a
human first.

## The flow toolkit

Flow management reads artifacts; it also has one CLI command of its own.
`compass retro` aggregates the `reframes` log across every task and
reports whether the Needle is systematically over- or under-sizing routes - the
framework's own feedback loop. It is read-only and never gates. Run it as part
of triage and fold its signal into the digest: "are we right-sizing process?"
is a cross-task question, and this is the command that answers it.

## Triage heuristics

Run these against every task directory under `.compass/work/`. Order of
severity, worst first:

1. **No `delivery-approach.md`** - a guardrail violation. Work was started without Frame.
   This outranks everything; a task with no computed route is unaccountable.
   The fix is to run Frame retroactively and reconcile.

2. **Route outgrown** - the devlog shows the task drifting past its route
   (a "Standard" task that has sprouted a fourth work stream; an "Express"
   task still open after days). The fix is `/compass:frame --reframe`, not
   pushing on. A route quietly outgrown is the failure mode Compass exists to
   prevent - flow management is where it gets caught when the task itself
   missed it.

3. **Stalled** - an in-progress phase with no `devlog.md` movement for longer
   than the route's expected cadence (Express: hours; Standard: a day or two;
   Expedition: longer, but each stream should still show movement). A stall is
   almost always a hidden blocker. Name the likely cause from the artifacts.

4. **Owed backfill sitting** - a task past Verify with an unpaid Hotfix
   backfill or an unbacked marketing claim. The per-task `/compass:status`
   flags this; flow's job is to make sure it does not sit ignored across the
   whole board.

5. **Healthy** - progressing in line with its route. Report it briefly; spend
   the attention on 1–4.

## Blocker protocol

When a task is blocked or stalled:

1. **Locate the blocker precisely.** Read the devlog and the latest artifact.
   "Blocked" is not a state - "blocked on a governance amendment decision",
   "blocked on a flaky integration test", "blocked waiting on a human to
   confirm the route override" are states.
2. **Name who or what unblocks it.** A human decision, another task landing
   first, an external dependency, a re-frame.
3. **Record it where the task lives** - append a dated line to that task's
   `devlog.md`. Flow management does not keep a separate blocker list; the
   devlog is the task's history and the blocker belongs in it.
4. **Escalate by surfacing, not by routing.** Flow management has no authority
   to reassign or reprioritise - it makes the blocker *visible* at the top of
   the flow report and, if a human decision is needed, says so plainly.

## The digest format

`/compass:flow --digest` writes `.compass/flow/digest-<date>.md`. It is
append-only history - a team reads it on a cadence (a weekly scheduled run is
the natural fit). Keep it short enough to read in two minutes.

```markdown
# Flow digest - {{DATE}}

## Needs a human
- {{decision or guardrail violation - or "nothing"}}

## Landed since last digest
- {{task-slug}} ({{route}}) - {{one line: what shipped}}

## In flight
- {{task-slug}} ({{route}}) - {{phase}} - {{health: healthy | stalled | off-route}}

## Blocked
- {{task-slug}} - blocked on {{precise blocker}}; needs {{who/what}}

## Owed backfills
- {{task-slug}} - {{unpaid Hotfix backfill | unbacked claim | de-scoped artifact}}

## Calibration
- {{`compass retro` signal - re-frame rate, lean toward over- or
  under-sizing, or "balanced" - or "not enough history yet"}}

## Next up
- {{tasks framed but not started, in route order}}
```

## What flow management must not do

- **It does not gate.** The gates live in the per-task pipeline, next to the
  evidence. Flow adds visibility, never another gate.
- **It does not set task state.** State is inferred from artifacts. If the
  board looks wrong, the artifacts are wrong - fix those, not a label.
- **It does not own tasks.** No assignment, no turf. It reads, triages, and
  surfaces. The moment flow management starts "managing people" instead of
  "surfacing reality", it has drifted back into the persona model Compass
  replaced.
