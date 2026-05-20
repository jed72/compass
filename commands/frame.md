---
description: Run the Needle — read the terrain and compute the route for this task
argument-hint: "<task description> [--reframe]"
allowed-tools: Read, Write, Edit, Glob, Grep
---

# /compass:frame

Frame is the one phase that never skips. The Needle reads four context
dimensions — that is **judgement** — and then hands them to the CLI, which
**computes** the route deterministically. You do not pick a process, and you
do not compose the route in your head: you read the terrain, record the
readings, and `compass route evaluate` applies `governance/routing-policy.yml`
to produce the route. This is the determinism boundary — see
`docs/methodology.md` §6.

Frame works on day one with **zero project setup**: the shipped default
guardrails, strategies, and routing policy apply as-is, so `/compass:init` is
optional and not a prerequisite. If a project has run `/compass:init`, its
`governance/` extends those defaults — read whichever is in force.

**Task:** $ARGUMENTS

## Setup

- Load the `adaptive-routing` skill — it is the procedural companion to
  `routes/router.md`, which is the rubric.
- Read `governance/routing-policy.md` for the *why*. The machine-readable
  `governance/routing-policy.yml` is what `compass route evaluate` actually
  runs: the Needle is bound by its **routing guardrails** (hard — floors, caps,
  immovable gates, blocking role rules) and biased by its **routing
  strategies** (soft — default route shapes, tie-breaking biases). You do not
  apply these by hand; the CLI does.
- Read `.compass/config.yml` for genuine project knobs (test command, swarm
  worktree root). Routing rules are no longer here — they live in
  `routing-policy.yml`.
- For a non-trivial or ambiguous task, invoke the `navigator` agent to read the
  four dimensions.
- If a `brief.md`, `ui-contract.md`, or `positioning.md` already exists for
  this task, read it — intent is the *outcome wanted*, not just the literal
  request.

## `--reframe`

If `--reframe` is passed, this is a mid-task re-score, not a fresh frame —
typically because Build revealed the terrain was misread. Read the existing
`route.md` and `task.yml`, re-read the four dimensions, update `task.yml`'s
`readings:` block, then re-run `compass route evaluate --write --reason "..."`
to recompute the route. **Always pass `--reason`** on a re-frame: when the CLI
sees the route change, it records the re-frame in `task.yml`'s `reframes:` log,
and the reason is the calibration signal `compass calibration` reads. Then
write a **new revision** of `route.md` (keep the prior revision visible). A
re-frame is a normal event. A route quietly outgrown is the failure — and a
re-frame with no recorded reason is a signal thrown away.

Re-framing is also how a **Spike graduates**: the spike's findings become an
input to a fresh Frame for the real delivery work. If the new route is no
longer a Spike, remove the `.spike` marker so the TDD strategy is back in
force; if it is still a Spike, leave the marker in place.

## Procedure (follows `routes/router.md` exactly)

1. **Create the task spine.** Pick a task slug, make
   `.compass/work/<task-slug>/`, and write `task.yml` from `templates/task.yml`
   into it. This is the machine-readable spine the CLI reads and writes.
2. **Read the four dimensions — this is the judgement** — blast radius,
   terrain, magnitude, intent & role, plus `touches:` domain tags. Each gets a
   value and a one-line justification. If a value cannot be justified, ask the
   user rather than guessing. When magnitude is unsure, estimate *up*. Note:
   **exploration intent** — "I cannot frame this well enough to deliver it
   yet" — leads toward the **Spike** route, the way live-defect urgency leads
   toward Hotfix. Write these into `task.yml`'s `readings:` block. The readings
   are the only part of routing that is judgement — everything below is
   mechanism.
3. **Compute the route — this is the mechanism.** Run
   `compass route evaluate --task <slug> --write`. The CLI applies
   `routing-policy.yml` to the readings: it composes the candidate, applies the
   floors, caps, immovable gates, and blocking role rules, and folds the
   resulting `route`, `phases`, `gates` (status pending), `topology`, and
   `fired_guardrails` back into `task.yml`. You do not compose the route or
   apply a guardrail by hand — same readings + same policy => same route, every
   time. If the readings are a misclassification, the CLI fails loudly; re-read
   the dimension it rejected.
4. **Write `route.md`** from `templates/route.md` into the task dir, from the
   CLI's output. It must contain: the four readings with justifications; the
   computed route; every routing guardrail the CLI reported as fired (with its
   rationale); the final per-phase weight, gate set, and swarm topology; and
   **the de-scope ledger** — every phase the CLI marked collapsed or skipped,
   each with an explicit "safe to skip because…" line. A phase with no
   justification runs. `route.md` is the human-readable face of what
   `task.yml` records mechanically.
5. **Write the `.compass/current-task` pointer.** Write the task slug into
   `.compass/current-task` so every later `compass` call resolves to this task
   without a `--task` flag.
6. **On a Spike route, write the `.spike` marker.** If the CLI's route is
   Spike, create an empty marker file at `.compass/work/<task-slug>/.spike`.
   The route-aware pre-tool hook reads this to know the TDD strategy is
   suspended for this task (the hook does not block code edits). Do **not**
   create this marker on any other route.
7. **Confirm.** The readings are advisory until confirmed. Present the route,
   invite override of any *reading*, and if a reading changes, re-run
   `compass route evaluate --write` — never hand-edit the computed route.
   Record overrides in `route.md` with who and why. Immovable gates and floors
   cannot be overridden — a routing guardrail is governance speaking; changing
   one means amending `governance/routing-policy.yml`, not overriding a route.

## Gate

`task.yml` exists with a `readings:` block and a CLI-computed `route`/`phases`/
`gates`; `route.md` exists, every dimension has a justification, and every
skipped phase has a written reason; `.compass/current-task` points at the slug.
On a Spike route, the `.compass/work/<task-slug>/.spike` marker exists. Then
start a `devlog.md` entry and proceed to `/compass:specify`.
