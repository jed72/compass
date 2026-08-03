---
description: Run scenarios as acceptance tests, apply review dimensions, check the gates
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# /compass:verify

Verify proves the work with evidence - pasted command output and artifacts,
never assertion. "It works" is not a gate-passing statement on any delivery
route. QA owns this gate.

## On a Spike route

Read `route.md`. On a **Spike**, Verify is **Conclude** - not a test gate but
a findings check: *did we answer the question?* It runs none of the review
dimensions (a spike ships nothing), and its one gate is "the question is
answered - or explicitly answered with 'inconclusive, here is why' - and the
finding is written down." If the route is a Spike, follow `routes/spike.md`'s
Conclude step instead of the delivery procedure below. The rest of this
command is for delivery routes.

## Setup

- Read `route.md` for the gate set and which review dimensions apply. The
  dimension set scales with the route (see the table in `routes/router.md`);
  `correctness`, `governance`, and `traceability` are always on for a delivery
  route - they are the default guardrails in review form. The routing policy's
  `immovable_gates` are stapled on regardless.
- Load the `evidence-gates` skill.
- Invoke the `verifier` agent (runs the suites) and the `reviewer` agent
  (applies the review dimensions).
- If the product-marketer role is in play, the `claims` dimension applies -
  `marketing-lens` reviews here too.
- QA owns this gate and can send the task back to Specify if scenarios are
  uncoverable.

## Procedure

1. **Scenarios as acceptance tests.** Run every scenario in `spec.feature.md`
   as an acceptance check. They are the same artifact the spec was - read now
   at verification time.
2. **TDD suite.** Run the full test suite. Paste the output.
3. **Run `compass check`.** This is the **mechanical half** of the Verify gate:
   the CLI runs the `guardrails.yml` checks against `task.yml` and `evidence/` -
   every scenario has a test, the suite passed (`evidence/green.json`), every
   changed file traces to a scenario, every `pass` gate has resolving evidence,
   and so on. It exits non-zero on any failure. The `reviewer` agent still does
   the *judgement* dimensions (clarity, security depth, governance-as-assessed)
   - `compass check` is the checkable backbone, not the whole gate.
4. **Review dimensions.** Apply each dimension `route.md` lists -
   `correctness`, `governance`, `traceability`, and as the route requires
   `regression`, `security` (scaled or full), `clarity`, `claims`. The
   `governance` dimension checks the work against `governance/`: the guardrails
   (hard, evidence-backed - `compass check` is the mechanical part) and the
   applicable strategies (assessed as judgement, reported distinctly). On a
   swarm, verify per-stream first, then again on the combined result.
5. **Update the gates in `task.yml`.** As each gate is cleared, the `verifier`
   sets its `status` to `pass` and points its `evidence:` at the artifact
   (`evidence/green.json`, a report path). `compass check`'s
   `gate-evidence-present` check verifies every `pass` gate has a pointer that
   resolves - a gate marked pass with no evidence fails the check.
6. **Write `verification-report.md`** from `templates/verification-report.md`:
   each dimension, each gate, the evidence, pass/fail.

## Gate

`compass check` passes (paste its output - that is the mechanical half); every
required *judgement* dimension passed with evidence; every gate in `task.yml`
is `pass` with a resolving evidence pointer; `verification-report.md` is
written, and its **Definition of Done** checklist (items 1–5) is fully checked -
that is the exit gate out of Verify. Items 6–7 of that checklist are carried
into Land. If anything fails, the task does not advance - fix it or send it
back. Log to `devlog.md`. Next: `/compass:land`.

## Answering the reviewer

Load `receiving-code-review`. Verify every suggestion against the code before
acting on it: a suggestion that is right about the smell and wrong about the
cause is the normal case, and implementing it verbatim leaves the smell and adds
a change nobody needed. Where the reviewer is wrong, push back with technical
reasoning rather than preference or seniority. Record what you did with each
comment - a resolved thread with no reply is a decision nobody can audit.
