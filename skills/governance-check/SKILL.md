---
name: governance-check
description: How to check a finished design against the guardrails and strategies in force. Load at the plan stage.
---

# Governance Check

Compass is governed by two kinds of thing, and the governance check is the
moment they are applied to a plan, spec, or change. It is not one rubber stamp
against one supreme document - it is three distinct walks against three
distinct files in `governance/`, and each has its own standard of proof.

- `guardrails.md` - **hard, checkable, blocking.** A guardrail is cleared with
  evidence; a failed guardrail stops the work. A guardrail beats a strategy.
- `strategies.md` - **soft, assessed, accretive.** A strategy is judged, not
  cleared; following it is the default, departing from it is allowed *and
  recorded*. A strategy never stops the work on its own.
- `routing-policy.md` - the same split applied to the router: **routing
  guardrails** bound the route, **routing strategies** bias it.

This replaces the old single "constitution check." There is no supreme
document to walk five sections of; there is a small hard set to clear and a
larger soft set to assess. The version model from the old file still applies -
`guardrails.md`, `strategies.md`, and `routing-policy.md` each carry a version
header; if your cached understanding predates the last amendment, you are
checking against a stale file.

## Before you start

Read the *current* `governance/` files at the project root. Check the version
on each. If `/compass:init` has not been run, the framework's shipped
`governance/` defaults apply as-is - and that is a valid, complete governance
state, not a missing prerequisite. Governance is a **gradient, not a
threshold**: "the shipped default guardrails, the shipped default strategies,
and zero project additions" is a fully legitimate thing to check against. Do
not treat an un-extended `governance/` as a reason to stop.

## Walk 1 - the guardrails (hard, evidence)

Walk the plan, spec, or change against every applicable guardrail - the five
shipped defaults and any project guardrails.

The five default guardrails:

- **Tested before it lands.** Is the work shaped so that nothing reaches
  `main` without a passing automated test it traces to? At Plan, this means the
  plan introduces work test-first (the TDD strategy is how) and the test
  surface is planned. At Verify, it is cleared with the recorded run.
- **Acceptance defined before it is built.** Does every piece of planned
  code trace to a stated, checkable acceptance criterion that exists *before*
  the code? The BDD strategy (Given/When/Then scenarios) is the default way to
  satisfy this; the guardrail itself is the outcome - acceptance is stated and checkable.
- **Traceability holds.** Are both chains planned for and intact -
  code → acceptance criterion → intent, and public claim → backing criterion?
- **Evidence, not assertion.** This one is *about* the others: a guardrail
  is cleared with artifacts and command output, never a claim. When you record
  a guardrail result, the proof is the artifact.
- **A human signs off on the irreversible.** Does anything that can lose
  data, move money, or breach auth or privacy have an explicit human checkpoint
  before it lands? Check the plan routes such work to where the checkpoint
  happens.

Then any project guardrails - concrete, measurable floors a project has added
(a coverage floor, a no-secrets-committed rule, a tested-rollback rule). Floors
only ratchet up: a plan may exceed a floor, never fall short of one.

**The standard of proof is evidence.** At Plan you are checking the plan is
*shaped* to clear each guardrail; at Verify the guardrail is *cleared* with the
verifier's artifacts. Either way: "looks fine" is not a result. For each
guardrail, record **clears** (with the evidence, or the plan element that will
produce it) or **fails** (with the specific guardrail and how it is crossed). A
plan that crosses a guardrail does not proceed - it is revised, or the issue
re-frames. There is nothing to waive a guardrail *for*; a guardrail beats every
strategy and every convenience.

## Walk 2 - the strategies (soft, assessed)

Walk the same plan, spec, or change against the applicable strategies - the
shipped default method strategies (including **BDD** and **TDD**) and any
project strategies (product, engineering, voice & positioning).

The standard here is different and you must keep it different. A strategy is
**assessed**, not cleared:

- Did the work follow the strategy? This is honest judgement - is this the
  simplest thing that works (the simplest thing that works), does it follow the team's engineering
  strategies, does the copy fit the voice strategies.
- Where it departed from a strategy, **is the departure recorded?** A recorded
  departure is the system working, not a failure. An *unrecorded* departure is
  the thing to flag - not because the departure is wrong, but because it was
  silent.
- Record the result **as judgement**, clearly labelled as judgement - never
  dressed up as evidence. A strategy not followed is a note and a conversation,
  not an automatic stop.

### The no-placeholders check

Before committing `technical-design.md`, run:

```
compass plan lint
```

It reports phrases that mean the plan is not actually finished - `TBD`, `TODO`,
"implement later", "add appropriate error handling" - and work units that
promise tests without naming any. These are the most common form of plan failure
in the wild: not a wrong decision, but a decision quietly deferred to whoever
builds it, who then makes it alone and unrecorded.

It belongs in this walk because **a reported hit is a note, rather than a
stop**. The command always exits 0 - the shell's success code, whatever it
reports. Assess each hit as judgement: either fill the gap in, or record why
the placeholder legitimately stands (a genuinely deferred decision with a
named owner is a plan, an unowned `TBD` is a gap). It never blocks Plan on any
route, and no floor promotes it to a gate.

Two things it deliberately does not do. It ignores text inside fenced code
blocks (the triple-backtick kind) and blockquotes (lines opening with `>`),
because every document explaining the check has to quote the phrases it looks
for. And it does not judge softer patterns - a work unit described only as
"similar to the one above", or an approach section that restates the spec
without saying how. Those need reading, which is your job in this walk, not
the command's.

Two of the default strategies are approach-aware: **BDD** and **TDD**
are suspended on a spike. If you are checking a Spike, do not flag the
absence of scenarios or red-before-green as a strategy failure - that
suspension is the route working as designed.

## Walk 3 - the routing policy

Confirm the plan is consistent with `routing-policy.md`:

- **Routing guardrails** - did every floor that should have fired, fire? Is the
  route the plan assumes consistent with the caps (e.g. the worktree cap on
  critical risk)? Are the `immovable_gates` and blocking `role_rules`
  reflected in the plan's gate set and artifact list? A plan that quietly
  assumes a lighter route than the routing guardrails allow fails here.
- **Routing strategies** - did the route follow the default shapes and biases,
  or is a departure recorded in `delivery-approach.md`? A recorded departure is fine; a
  silent one is the flag.

## How to run the check (Plan phase)

1. Read the current `governance/` files; confirm each version.
2. Walk 1 - guardrails - against `technical-design.md` and the spec it builds on. Record
   per guardrail: **clears** (with evidence or the plan element that produces
   it) or **fails** (with the specific guardrail).
3. Walk 2 - strategies - against the same. Record per strategy as **judgement**:
   followed, or departed-and-recorded, or departed-silently (flag it).
4. Walk 3 - routing policy - confirm the plan's assumed route is within the
   routing guardrails and consistent with the routing strategies.
5. Write all three results into `technical-design.md`, with the guardrail findings and the
   strategy assessment **visibly separate** - evidence on one side, judgement
   on the other.
6. A failed guardrail **stops the plan** - revise or re-assess. A strategy
   departure does **not** stop the plan; record it and, if it matters, raise it.
   That asymmetry is the whole point of the split.
7. If a guardrail itself seems wrong, that is an amendment conversation (change
   `guardrails.md`, bump the version, log it) - never a quiet override
   mid-issue. If a strategy keeps getting overridden the same way, that is a
   curation signal - fix the strategy or write down the thing overriding it.

## Anti-patterns

- **The rubber stamp** - "governance check: pass" with no per-guardrail,
  per-strategy detail. If you cannot name what you checked, you did not check.
- **Conflating the two walks** - clearing a guardrail on judgement, or treating
  a strategy departure as a hard stop. The standards of proof are different on
  purpose; collapsing them is the failure the strategies/guardrails split was
  built to prevent.
- **The dressed-up strategy** - recording a strategy assessment as if it were
  evidence-backed. It is judgement; label it.
- **The convenience override** - treating a guardrail as advisory because
  honouring it is inconvenient. A guardrail beats every strategy and every
  deadline; inconvenience is not a counter-argument.
- **Checking the stale file** - reviewing against a `governance/` file older
  than its last amendment.
- **Floor erosion** - reading a project guardrail floor as a target to *hit*
  rather than a minimum to *clear*. Floors only ratchet up.
- **Silent route assumption** - a plan that assumes a lighter route than the
  routing guardrails permit, without anyone noticing the policy was bypassed.
- **Treating an un-extended `governance/` as broken** - the shipped defaults
  are a complete state. Governance is a gradient; check against whatever is
  there, defaults included.
