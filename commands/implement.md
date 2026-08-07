---
description: Implement via TDD - red, green, refactor - one builder per worktree
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# /compass:implement

Implementation is where code is written, and it is written test-first. The
red-before-green TDD strategy applies on every delivery approach, including a
quick fix - a change is introduced by a test that fails first. The approach
adapts how much *surface* the tests cover. The one exception is a **spike**:
there the TDD strategy is suspended (the pre-tool hook is approach-aware and
does not block), because exploration is not delivery - but the
tested-before-ship guardrail still applies to anything a spike *graduates*
into real delivery work.

## Setup

- Read `delivery-approach.md` for the test-surface target (scaled to risk)
  and the topology.
- Read `acceptance-criteria.md` - scenarios become the acceptance suite and
  seed the TDD cycle. Read `design.md` for the approach.
- Load the `tdd-discipline` skill.
- Invoke the `builder` agent - **one per worktree** on a pair or swarm
  topology, each owning its scenario set from the distribution map. On solo
  work, one builder on the current branch.
- On a swarm, the `orchestrator` is already watching: it detects when two
  streams are converging on shared surface and intervenes *before* they
  collide. Cross-stream changes go through the orchestrator, never builder
  to builder.
- **Capture the regression baseline first (a shipped strategy).** If
  `delivery-approach.md` assesses risk as cross-cutting or critical - or
  `compass approach evaluate` surfaced `regression-baseline` under the
  advisory strategies - run the designated existing suite
  (`project.regression_baseline_suite`, else `project.test_command`)
  **green now, before editing shared code**, and record it as `test-run`
  evidence on `verify.regression`. Re-run it after the change. This is soft
  (assessed, never gating), but it is captured up front, not as an
  afterthought - it catches a high-consequence break in behaviour you did
  not mean to touch.

## The cycle, per scenario

1. **Red.** Write the failing test for the scenario, then run
   `compass tdd-red -- <failing test command>`. The CLI runs the test,
   asserts it actually FAILS, records `evidence/red.json`, and drops the
   `.red` marker - honestly, only after a real failure. If the test passes,
   the CLI refuses and says so: you skipped red. The `hooks/pre-tool.sh`
   hook reads `.red` to allow the code edit. Do not touch markers by hand -
   the CLI owns them. (On a spike the hook does not block - the TDD strategy
   is suspended; see the spike note.)
2. **Green.** Write the smallest correct change that makes the test pass,
   then run `compass tdd-green -- <test command>`. The CLI asserts it
   PASSES, records `evidence/green.json`, and clears `.red`. If it still
   fails, the CLI leaves `.red` in place - you are not green yet.
3. **Refactor.** Clean up with the suite green. On a hotfix, refactor only
   if the refactor itself is low-risk.
4. **Record the change.** For each production file you touched, add an entry
   to `task.yml`'s `changed_files:` - its path and the scenario id(s) it
   traces to. This is the code-to-criterion half of the traceability
   guardrail, and `compass check` verifies it.
5. Keep the traceability chain live as you go - code to scenario to intent -
   not at the end.

## Hotfix note

On a hotfix the reproduction test is already red from the define stage.
Implementation is expedited: make it green with the smallest correct change
to the **root cause** (not the symptom - a symptom fix owes a follow-up
initiative).

## Spike note

On a spike, implementation *is* exploration. The red-before-green TDD
strategy is suspended and the pre-tool hook does not block - you write code
freely to answer the question, and that code is assumed throwaway. Nothing
ships from a spike: the only exit that keeps code is *graduating*
(re-assessing into real delivery work), where the tested-before-ship
guardrail applies in full. See `routes/spike.md`.

## When the failure is unexpected

Load the `systematic-debugging` skill. It is four phases - instrument at the
boundaries, compare against a working case, test one hypothesis at a time,
fix through a failing test - and one escape clause that matters here more
than the phases do:

**After three consecutive fixes that did not hold, stop.** Three failures in
a row means the model you are debugging against does not match the system,
and a fourth guess damages code that was not broken. That is a triage
signal - see the reassessment trigger below.

## Reassessment trigger

If implementation reveals the assessment was misread - a "small" change
unspooling into a multi-module refactor - **stop and re-assess**
(`/compass:triage --reassess`). Pushing on with a delivery approach you no
longer believe is the failure mode.

## Gate

On delivery work: every scenario has a test; every test went red before
green (`evidence/red.json` then `evidence/green.json` on record); the suite
is green; every changed production file is recorded in `task.yml`'s
`changed_files:` traced to a scenario. On a spike: the question was explored
and the findings are captured - there is no test gate, because nothing
ships. Log progress to `devlog.md`. Next: `/compass:verify`.
