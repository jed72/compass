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

## Procedure

1. **Pick the table.** Convene the lenses the question actually needs — some
   of `product-lens`, `marketing-lens`, `planner`, `reviewer`,
   and the designer or QA perspective. Name who is at the table and why.
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

## Gate

The decision is written to `devlog.md` with its rationale and the tradeoffs it
accepted. A roundtable that ends without a recorded decision has not finished.
If the decision touches the route, follow it with a re-frame.
