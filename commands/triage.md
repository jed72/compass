---
description: Assess the work - risk, familiarity, size, goal - and compute the delivery approach
argument-hint: "<issue description> [--reassess]"
allowed-tools: Read, Write, Edit, Glob, Grep
---

# /compass:triage

Triage is the one stage that never skips. It reads the four assessment
dimensions - that is **judgement** - and then hands them to the CLI, which
**computes** the delivery approach deterministically. You do not pick a
process, and you do not compose the approach in your head: you assess the
work, record the assessment, and `compass approach evaluate` applies
`governance/routing-policy.yml` to produce the approach. This is the
determinism boundary - see `docs/methodology.md` §6.

Triage works on day one with **zero project setup**: the shipped default
guardrails, strategies, and routing policy apply as-is, so `/compass:init` is
optional and not a prerequisite. If a project has run `/compass:init`, its
`governance/` extends those defaults - read whichever is in force.

**Issue:** $ARGUMENTS

## Setup

- Load the `adaptive-routing` skill - it is the procedural companion to the
  delivery-approach rubric (`routes/router.md`).
- Read `governance/routing-policy.md` for the *why*. The machine-readable
  `governance/routing-policy.yml` is what `compass approach evaluate` actually
  runs: triage is bound by its **policy floors, caps, immovable gates, and
  blocking role rules** (hard) and biased by its **default shapes and
  tie-breaking biases** (soft). You do not apply these by hand; the CLI does.
- Read `.compass/config.yml` for genuine project knobs (test command, swarm
  worktree root). Routing rules are not here - they live in
  `routing-policy.yml`.
- For a non-trivial or ambiguous issue, invoke the `navigator` agent to read
  the four dimensions.
- If a `prd.md`, `ui-contract.md`, or `positioning.md` already exists for
  this issue, read it - intent is the *outcome wanted*, not just the literal
  request.

## `--reassess`

(The retired spelling `--reframe` is accepted for one major version and
means the same thing.)

If `--reassess` is passed, this is a mid-flight re-assessment, not a fresh
triage - typically because implementation revealed the assessment was
misread. Read the existing `delivery-approach.md` and `task.yml`, re-read the
four dimensions, update the spine's `assessment:` block, then re-run
`compass approach evaluate --write --reason "..."` to recompute the approach.
**Always pass `--reason`** on a re-assessment: when the CLI sees the approach
change, it records the event in the spine's `reassessments:` log, and the
reason is the signal `compass retro` reads. Then write a **new
revision** of `delivery-approach.md` (keep the prior revision visible). A
re-assessment is a normal event. An approach quietly outgrown is the
failure - and a re-assessment with no recorded reason is a signal thrown
away.

Re-assessing is also how a **spike graduates**: the spike's findings become
an input to a fresh triage for the real delivery work. If the new approach is
no longer a spike, remove the `.spike` marker so the TDD strategy is back in
force; if it is still a spike, leave the marker in place.

## Procedure (follows the delivery-approach rubric exactly)

1. **Create the issue spine.** Pick a slug, make `.compass/work/<task-slug>/`,
   and write `task.yml` from `templates/task.yml` into it. This is the
   machine-readable spine the CLI reads and writes.
1a. **Load project architecture if present.** Call
    `frame_load_architecture(project_root, task_dir)` - the internal CLI
    helper. It scans `architecture/` at the project root (sibling to
    `governance/`), reads any narrative files (`system-context.md`,
    `relations.md`, `ownership.md`) and the optional structured file
    (`invariants.yml`), collects any `ADR-*.md` files from
    `architecture/decisions/`, and writes the result to
    `.compass/work/<task-slug>/architecture-loaded.yml`. If `architecture/`
    does not exist the file is written with empty `artifacts: []` and
    `adrs: []` - no error (backward compat). If `invariants.yml` exists but
    is not valid YAML, triage fails loudly with the file path and parse error
    in the message - a malformed structured artifact is never silently
    swallowed. `architecture-loaded.yml` is the **downstream agents' input**
    for all architectural context in this session; see `docs/methodology.md`
    for the contract. **Do not write load state into the spine's
    `assessment:`** - that block is the judgement only.
2. **Read the four dimensions - this is the judgement** - risk, familiarity,
   size, goal & role, plus the `labels:` domain tags. Each gets a value and a
   one-line justification. If a value cannot be justified, ask the user
   rather than guessing. When size is unsure, estimate *up*. Note:
   **exploration goal** - "I cannot state this well enough to deliver it
   yet" - leads toward a **spike**, the way live-defect urgency leads toward
   a hotfix. Write these into the spine's `assessment:` block. The assessment
   is the only part of the computation that is judgement - everything below
   is mechanism.
3. **Compute the delivery approach - this is the mechanism.** Run
   `compass approach evaluate --task <slug> --write`. The CLI applies
   `routing-policy.yml` to the assessment: it composes the candidate shape,
   applies the floors, caps, immovable gates, and blocking role rules, and
   folds the resulting `delivery_approach`, `stages`, `gates` (status
   pending), `topology`, and `policy_rules_fired` back into `task.yml`. You
   do not compose the approach or apply a policy rule by hand - same
   assessment + same policy => same approach, every time. If the assessment
   is a misclassification, the CLI fails loudly; re-read the dimension it
   rejected.
4. **Write `delivery-approach.md`** from `templates/delivery-approach.md`
   into the issue directory, from the CLI's output. It must contain: the four
   dimensions with justifications; the computed approach; every policy rule
   the CLI reported as fired (with its rationale); the final per-stage
   weight, gate set, and topology; and **the de-scope ledger** - every stage
   the CLI marked collapsed or skipped, each with an explicit "safe to skip
   because..." line. A stage with no justification runs.
   `delivery-approach.md` is the human-readable face of what `task.yml`
   records mechanically.
5. **Write the `.compass/current-task` pointer.** Write the slug into
   `.compass/current-task` so every later `compass` call resolves to this
   issue without a `--task` flag.
6. **On a spike, write the `.spike` marker.** If the CLI's approach is a
   spike, create an empty marker file at `.compass/work/<task-slug>/.spike`.
   The approach-aware pre-tool hook reads this to know the TDD strategy is
   suspended for this issue (the hook does not block code edits). Do **not**
   create this marker on any other approach.
7. **Confirm.** The assessment is advisory until confirmed. Present the
   approach, invite override of any *dimension*, and if a dimension changes,
   re-run `compass approach evaluate --write` - never hand-edit the computed
   approach. Record overrides in `delivery-approach.md` with who and why.
   Immovable gates and floors cannot be overridden - a policy floor is
   governance speaking; changing one means amending
   `governance/routing-policy.yml`, not overriding one issue's approach.

## Gate

`task.yml` exists with an `assessment:` block and a CLI-computed
`delivery_approach`/`stages`/`gates`; `delivery-approach.md` exists, every
dimension has a justification, and every skipped stage has a written reason;
`.compass/current-task` points at the slug. On a spike, the
`.compass/work/<task-slug>/.spike` marker exists. Then start a `devlog.md`
entry and proceed to `/compass:define`.
