---
description: Test and review - run scenarios as acceptance tests, apply the review dimensions, check the gates
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# /compass:verify

Verify proves the work with evidence - recorded command output and artifacts
a reader can open, never assertion. "It works" is not a gate-passing statement on any delivery
approach. QA owns this gate.

## On a spike

Read `delivery-approach.md`. On a **spike**, verify is **conclude** - not a
test gate but a findings check: *did we answer the question?* It runs none of
the review dimensions (a spike ships nothing), and its one gate is "the
question is answered - or explicitly answered with 'inconclusive, here is
why' - and the finding is written down." If the approach is a spike, follow
`${CLAUDE_PLUGIN_ROOT}/approaches/spike.md`'s conclude step instead of the delivery procedure below.
The rest of this command is for delivery work.

## Setup

- Read `delivery-approach.md` for the gate set and which review dimensions
  apply. The dimension set scales with the approach (see the table in the
  delivery-approach rubric, `${CLAUDE_PLUGIN_ROOT}/approaches/rubric.md`); `correctness`,
  `governance`, and `traceability` are always on for delivery work - they
  are the default guardrails in review form. The routing policy's
  `immovable_gates` are stapled on regardless.
- Load the `evidence-gates` skill.
- Invoke the `verifier` agent (runs the suites) and the `reviewer` agent
  (applies the review dimensions).
- If the product-marketer role is in play, the `claims` dimension applies -
  `marketing-lens` reviews here too.
- If this issue is itself a sweep, rename, or cleanup touching many files,
  verify it the way `governance/strategies.md` `S9` describes: a fresh agent
  that has not seen the change, not its author.
- A guard offered as part of the change is accepted on a demonstrated failure
  rather than a passing test - `governance/strategies.md` `S10` states the
  method.
- Where a review comment and the author disagree about a quantity - how many
  call sites, how much output, how often it fires - the number is measured
  and reported before either position is defended
  (`governance/strategies.md` `S11`).
- QA owns this gate and can send the issue back to the define stage if
  scenarios are uncoverable.

## Procedure

1. **Scenarios as acceptance tests.** Run every scenario in
   `acceptance-criteria.md` as an acceptance check. They are the same
   artifact the spec was - read now at verification time.
2. **TDD suite.** Run the full test suite through `compass tdd-green -- <cmd>`,
   which confirms it passes and writes the record. Link that record from the
   report rather than reproducing the run inside it.
3. **Run `compass check`.** This is the **mechanical half** of the verify
   gate: the CLI runs the `guardrails.yml` checks against `task.yml` and
   `evidence/` - every scenario has a test, the suite passed
   (a green record on file), every changed file traces to a scenario, every
   `pass` gate has resolving evidence, and so on. It exits non-zero on any
   failure. The `reviewer` agent still does the *judgement* dimensions
   (clarity, security depth, governance-as-assessed) - `compass check` is
   the checkable backbone, not the whole gate.
4. **Review dimensions.** Apply each dimension `delivery-approach.md`
   lists - `correctness`, `governance`, `traceability`, and as the approach
   requires `regression`, `security` (scaled or full), `clarity`, `claims`.
   The `governance` dimension checks the work against `governance/`: the
   guardrails (hard, evidence-backed - `compass check` is the mechanical
   part) and the applicable strategies (assessed as judgement, reported
   distinctly). On a swarm, verify per-stream first, then again on the
   combined result.
5. **Update the gates in `task.yml`.** As each gate is cleared, the
   `verifier` sets its `status` to `pass` and points its `evidence:` at the
   artifact (the scenario-bound green record, a report path). `compass check`'s
   `gate-evidence-present` check verifies every `pass` gate has a pointer
   that resolves - a gate marked pass with no evidence fails the check.
6. **Write `verification-report.md`** from
   `${CLAUDE_PLUGIN_ROOT}/templates/verification-report.md`: each dimension, each gate, the
   evidence, pass/fail.

## Voice

A verification report is evidence a person reads, not a status board. Say
what passed and what it means - never that the issue is "ready for the next
command." See `skills/compass-runtime/writing-voice.md`.

## Gate

`compass check` passes (record its output with `compass evidence add` and link
the record - that is the mechanical half);
every required *judgement* dimension passed with evidence; every gate in
`task.yml` is `pass` with a resolving evidence pointer;
`verification-report.md` is written, and its **Definition of Done**
checklist (items 1-5) is fully checked - that is the exit gate out of
verify. Items 6-7 of that checklist are carried into ship. If anything
fails, the issue does not advance - fix it or send it back. Log to
`devlog.md`. Next: `/compass:ship`.

## Answering the reviewer

Load `receiving-code-review`. Verify every suggestion against the code
before acting on it: a suggestion that is right about the smell and wrong
about the cause is the normal case, and implementing it verbatim leaves the
smell and adds a change nobody needed. Where the reviewer is wrong, push
back with technical reasoning rather than preference or seniority. Record
what you did with each comment - a resolved thread with no reply is a
decision nobody can audit.
