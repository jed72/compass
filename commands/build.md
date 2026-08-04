---
description: Implement via TDD - red, green, refactor - one builder per worktree
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# /compass:build

Build is where code is written, and it is written test-first. The red-before-green
TDD strategy applies on every delivery route, including Express - a change is
introduced by a test that fails first. The route adapts how much *surface* the
tests cover. The one exception is **Spike**: there the TDD strategy is suspended
(the pre-tool hook is route-aware and does not block), because exploration is not
delivery - but G1 still applies to anything a Spike *graduates* into a real route.

## Setup

- Read `route.md` for the test-surface target (scaled to blast radius) and the
  topology.
- Read `spec.feature.md` - scenarios become the acceptance suite and seed the
  TDD cycle. Read `plan.md` for the approach.
- Load the `tdd-discipline` skill.
- Invoke the `builder` agent - **one per worktree** on a pair or swarm route,
  each owning its scenario set from the distribution map. On a solo route, one
  builder on the current branch.
- On a swarm, the `orchestrator` is already watching: it detects when two
  streams are converging on shared surface and intervenes *before* they
  collide. Cross-stream changes go through the orchestrator, never builder to
  builder.
- **Capture the regression baseline first (strategy S6).** If `route.md` reads
  `blast_radius` cross-cutting or critical - or `compass route evaluate`
  surfaced `regression-baseline` under `applicable_strategies` - run the
  designated existing suite (`project.regression_baseline_suite`, else
  `project.test_command`) **green now, before editing shared code**, and record
  it as `test-run` evidence on `verify.regression`. Re-run it after the change.
  This is soft (assessed, never gating), but it is captured up front, not as an
  afterthought - it catches a high-consequence break in behaviour you did not
  mean to touch.

## The cycle, per scenario

1. **Red.** Write the failing test for the scenario, then run
   `compass tdd-red -- <failing test command>`. The CLI runs the test, asserts
   it actually FAILS, records `evidence/red.json`, and drops the `.red` marker -
   honestly, only after a real failure. If the test passes, the CLI refuses and
   says so: you skipped red. The `hooks/pre-tool.sh` hook reads `.red` to allow
   the code edit. Do not touch markers by hand - the CLI owns them. (On a Spike
   route the hook does not block - the TDD strategy is suspended; see the Spike
   note.)
2. **Green.** Write the smallest correct change that makes the test pass, then
   run `compass tdd-green -- <test command>`. The CLI asserts it PASSES, records
   `evidence/green.json`, and clears `.red`. If it still fails, the CLI leaves
   `.red` in place - you are not green yet.
3. **Refactor.** Clean up with the suite green. On Hotfix, refactor only if the
   refactor itself is low-risk.
4. **Record the change.** For each production file you touched, add an entry to
   `task.yml`'s `changed_files:` - its path and the scenario id(s) it traces to.
   This is the code → criterion half of guardrail G3, and `compass check`
   verifies it.
5. Keep the traceability chain live as you go - code → scenario → intent - not
   at the end.

## Hotfix note

On Hotfix the reproduction test is already red from Specify. Build is
expedited: make it green with the smallest correct change to the **root cause**
(not the symptom - a symptom fix owes a follow-up Expedition).

## Spike note

On a Spike route Build *is* Explore. The red-before-green TDD strategy is
suspended and the pre-tool hook does not block - you write code freely to
answer the question, and that code is assumed throwaway. Nothing lands from a
Spike: the only exit that keeps code is *graduating* (re-framing into a real
route), where G1 - tested before it lands - applies in full. See
`routes/spike.md`.

## When the failure is unexpected

Load the `systematic-debugging` skill. It is four phases - instrument at the
boundaries, compare against a working case, test one hypothesis at a time, fix
through a failing test - and one escape clause that matters here more than the
phases do:

**After three consecutive fixes that did not hold, stop.** Three failures in a
row means the model you are debugging against does not match the system, and a
fourth guess damages code that was not broken. That is a routing signal - see
the re-frame trigger below.

## Re-frame trigger

If Build reveals the terrain was misread - a "small" change unspooling into a
multi-module refactor - **stop and re-frame** (`/compass:frame --reframe`).
Pushing on with a route you no longer believe is the failure mode.

## Gate

On a delivery route: every scenario has a test; every test went red before
green (`evidence/red.json` then `evidence/green.json` on record); the suite is
green; every changed production file is recorded in `task.yml`'s
`changed_files:` traced to a scenario. On a Spike: the question was explored and
the findings are captured - there is no test gate, because nothing lands. Log
progress to `devlog.md`. Next: `/compass:verify`.
