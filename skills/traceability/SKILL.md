---
name: traceability
description: Maintaining the code→scenario→intent and claim→scenario chains continuously, so the chain becomes the audit trail. Triggers whenever an artifact is written — during Specify, Build, Verify, and any role-facing work.
---

# Traceability

Traceability is **guardrail G3**. Two chains, maintained on every route,
updated *as you go* — not reconstructed at the end:

```
code → scenario → intent
claim → scenario
```

The chain is not paperwork. It *is* the audit trail. When it is intact, anyone
can pick any line of code and walk it up to the reason it exists; anyone can
pick any public claim and walk it down to the proof it is true. When it is
broken, you have code nobody can explain or claims nobody can stand behind —
and that is a Verify no-pass.

## The two chains, link by link

### code → scenario → intent

- **code → scenario.** Every unit of production code traces up to a scenario in
  `spec.feature.md` that motivates it. Not one-to-one — a scenario may need
  several units, a unit may serve several scenarios — but *onto*: no code
  without at least one scenario above it. Guardrail G2 forbids code no stated
  acceptance criterion describes; this link is how that is observable.
- **scenario → intent.** Every scenario traces up to an intent — the brief
  success signal, the ticket, the product outcome it serves. A scenario with no
  intent above it is a scenario nobody asked for.

### claim → scenario

- Every public claim — launch copy, docs, marketing, a sentence in the
  changelog — traces down to a scenario that, when it passes, makes the claim
  true. This is the marketer's `launch-readiness.md` ledger and it is an
  immovable gate at Land.

## How to maintain it continuously

The discipline is *continuous*, and that is the whole craft — a chain rebuilt
at the end is a chain that was guessed.

- **At Specify** — the Spec Author tags each scenario with its intent reference
  as the scenario is written. The upper half of the chain exists before any
  code does.
- **At Build** — the Builder records the scenario each unit serves *as the unit
  is written* — a comment, a test name, a commit message convention, whatever
  the project uses. The link is made at the moment the code is made, when the
  reason is still in your head. Recovering it later is archaeology.
- **Alongside Specify/Land** — the Marketing Lens adds a `claim → scenario` row
  to `launch-readiness.md` as each claim is drafted. A claim with no row is not
  yet a shippable claim.
- **At Verify** — the Reviewer runs `traceability` as a review dimension: walk
  the chains, find the breaks. It is on every delivery route because it is
  guardrail G3 in review form.

## What a break looks like — and what to do

- **Orphan code** — a unit with no scenario above it. Either it implements
  behaviour that needs a scenario (file it with the Spec Author), or it is dead
  code (delete it). Code does not get to exist unexplained.
- **Orphan scenario** — a scenario with no intent above it. Either find the
  intent it serves, or question whether the scenario should exist. Scenarios
  nobody asked for are scope creep with a Given/When/Then on it.
- **Orphan claim** — a public claim with no scenario below it. The marketer's
  three moves: file the missing scenario, soften the claim until a real
  scenario backs it, or cut the claim. It never ships orphaned — `verify.claims`
  is immovable.
- **Stale link** — a scenario was rewritten and the code above it now traces to
  a scenario that no longer says what the code does. Re-point the link; a link
  to the wrong place is worse than a missing one because it lies.

## How the chain becomes the audit trail

Run end to end, the chains answer the questions an audit asks without anyone
reconstructing anything:

- *Why does this code exist?* — walk up: scenario, then intent.
- *Is this feature actually built?* — walk down from the intent: scenarios,
  then code, then the passing tests.
- *Can we say this publicly?* — walk down from the claim to the scenario and
  check its Verify status.
- *What breaks if we change this scenario?* — walk down to every unit of code
  and every claim that traces to it.

That is why it is maintained continuously and on every route, including
Express and Hotfix. The audit trail is not a document you write; it is a
property the chain *has* — but only if every link was made when the work was.

## Anti-patterns

- **End-of-task reconstruction** — building the chain at Verify from memory.
  You are guessing, and the guesses look exactly like real links.
- **The decorative reference** — a scenario tag that points vaguely at a feature
  rather than precisely at a scenario. Precision is what makes the walk work.
- **Letting Hotfix skip it** — "we were in a hurry." The reproduction test
  traces to the defect; the promoted scenario traces to an intent. The chain
  holds at 3am.
- **Claims that outrun scenarios** — drafting launch copy for behaviour the spec
  does not yet describe and intending to "backfill the scenario." The scenario
  comes first, or the claim is not real.
