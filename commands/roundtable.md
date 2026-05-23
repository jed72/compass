---
description: Convene multiple role lenses on a question, surface the tradeoffs, record the decision
argument-hint: "<the question or decision to work through>"
allowed-tools: Read, Write, Edit, Glob, Grep
---

# /compass:roundtable

Convene several role lenses on one question, make the tradeoffs explicit, and
record the decision. Use this when a choice genuinely sits across roles — a
scope cut that affects a marketing claim, an architecture call that changes the
user's experience, a priority conflict between intent and effort.

**Question:** $ARGUMENTS

## Setup

- Load `role-translation` — the whole point of a roundtable is one question
  read through several lenses without flattening any of them.
- Read the relevant task artifacts so the discussion is grounded in what is
  actually on disk: `route.md`, `brief.md`, `spec.feature.md`, `plan.md`,
  `positioning.md`, `ui-contract.md` — whichever bear on the question.
- Read `governance/` — a roundtable cannot decide its way past a guardrail.
  Strategy-vs-strategy tension is exactly what a roundtable *is* for; a
  guardrail is not up for negotiation.

## Agent roster

The following agents are part of the standard roundtable roster and may be
convened by name:

| Agent | Invocation | Auto-trigger condition |
|---|---|---|
| `product-lens` | `/compass:roundtable product-lens` | When a product owner is in play (`brief.md` exists) |
| `marketing-lens` | `/compass:roundtable marketing-lens` | When a marketer is in play (`positioning.md` exists) |
| `architect-lens` | `/compass:roundtable architect-lens` | When `task.yml.readings.touches` contains `public-api`, a service name from `architecture/relations.md`, or a `lens_trigger_tag` from `architecture/invariants.yml` |
| `planner` | `/compass:roundtable planner` | On request |
| `reviewer` | `/compass:roundtable reviewer` | On request |

**Registration contract:** a lens is invoked only if its agent file exists in
`agents/`. If the file does not exist, `/compass:roundtable` skips that lens
and records the absence in `devlog.md` rather than failing. This prevents
recursive invocation when a task itself introduces a new lens — the bootstrap
case (see TRC-X5 in the spec and `agents/architect-lens.md` §How you work).

**Named invocation:** pass the agent name as a positional argument:
```
/compass:roundtable architect-lens
```
This convenes only the architect-lens, regardless of auto-trigger conditions.
The lens writes `architecture-notes.md` to the task directory.

**Auto-convene (no args):** when invoked with no positional agent name,
`/compass:roundtable` auto-convenes every lens whose trigger condition is met
for the current task.

## Procedure

1. **Pick the table.** Convene the lenses the question actually needs — some
   of `product-lens`, `marketing-lens`, `architect-lens`, `planner`,
   `reviewer`, and the designer or QA perspective. Name who is at the table
   and why.
2. **State the question** crisply, with the constraints that bound it (the
   guardrails, the route, fixed deadlines).
3. **Each lens speaks in its own vocabulary.** The product owner argues intent
   fidelity; the marketer argues claims and voice; the planner argues
   feasibility and architecture; the reviewer argues risk and the guardrails.
   Do not let one lens speak for another.
4. **Surface the tradeoffs** explicitly — what each option costs each lens.
   Note where lenses agree and where they genuinely conflict.
5. **Record the decision.** Append to the task's `devlog.md`: the question, who
   was at the table, the options, the tradeoffs, the decision, and the
   rationale. If the decision changes scope or route, that is a trigger to
   re-frame (`/compass:frame --reframe`) — say so.

## Reframe trigger

Some roundtable outcomes do more than record a tradeoff — they change the
scope, the boundary, or the migration surface of the current task. When that
happens, a re-frame is not optional.

**Any roundtable outcome that changes a service boundary or migration scope
must end with a re-frame:**

```
/compass:frame --reframe --reason "<roundtable id> — <what changed and why>"
```

Examples of outcomes that require a re-frame:

- The roundtable decides to extend a planned migration to cover an adjacent
  service that was not in the original scope.
- A boundary call moves a module from one service to another, adding files
  that were not in `plan.md`.
- A scope cut removes a deliverable that was in `spec.feature.md`.

In all these cases, file the re-frame immediately after the roundtable
decision is recorded in `devlog.md`. The re-frame is the calibration signal
that `compass calibration` reads — absorbing a mis-frame silently loses the
signal.

## Gate

The decision is written to `devlog.md` with its rationale and the tradeoffs it
accepted. A roundtable that ends without a recorded decision has not finished.
If the decision touches the route, follow it with a re-frame.
