---
name: bdd-specification
description: How to write Given/When/Then scenarios that double as the acceptance suite — scenario granularity, the qualities of a runnable scenario, and how depth scales by route. Triggers during Specify and Clarify.
---

# BDD Specification

**BDD is strategy S1** — expressing acceptance criteria as Given/When/Then
scenarios. It is the strong, shipped-on default *way* to satisfy **guardrail
G2**: *acceptance defined before it is built — stated, and checkable*. Keep that
relationship straight.

- **G2 is the guardrail** — hard, checkable. No code is written that no stated,
  checkable acceptance criterion describes. The outcome — acceptance is stated
  and it is checkable — is non-negotiable on every delivery route.
- **BDD is the strategy** — Given/When/Then is the *form*. It is strong and
  shipped-on, but it is a strategy: a context where the form genuinely does not
  fit is a recorded strategy deviation, not a framework violation. The hard
  line is that acceptance exists and is checkable; G/W/G is the default way to
  make it so.

In Compass the BDD spec is not documentation that precedes the tests — it *is*
the tests, read at a different time. `spec.feature.md` is written once at
Specify and run as the acceptance check at Verify. It is also the one artifact
five roles read (see `role-translation`). Write it knowing all of that.

## What a scenario is

```
Scenario: <a behaviour, named as an outcome>
  Given <the world is in this concrete, specific state>
  When  <exactly one triggering action happens>
  Then  <this observable, checkable outcome holds>
```

A scenario is a single behaviour with a single trigger. It is concrete enough
that someone could execute it by hand and concrete enough that a test can
assert it automatically — those are the same bar.

## The qualities of a good scenario

- **Concrete state.** "Given a user" is too vague. "Given a user with a
  verified email and no active subscription" can be set up and asserted.
- **One When.** Two actions in `When` means two scenarios. The trigger is
  singular.
- **Observable Then.** The outcome must be checkable from outside — a returned
  value, a stored state, a rendered element, an emitted event. "Then it works"
  is not a Then. "Then the response is 402 and no charge row is written" is.
- **Declarative, not procedural.** Describe *what* is true, not the click-path
  to get there. The implementation can change; the behaviour should not.
- **Named as an outcome.** "Scenario: expired token is rejected" beats
  "Scenario: test token". The name is the first thing the PM, marketer, and QA
  read.

## Scenario granularity — splitting and merging

- **Split** when a scenario has an "and" in its `When`, or branches in its
  `Then` ("Then either X or Y"), or needs a paragraph of `Given` — those are
  multiple behaviours wearing one name.
- **Merge** when two scenarios differ only in an incidental value and assert the
  same behaviour — use a scenario outline / examples table instead of copying.
- The unit is *one behaviour*, not one feature and not one line of code. A
  feature is a set of scenarios; a line of code traces *up* to a scenario but is
  not one-to-one with it.

## How depth scales by route

The vocabulary never changes. The depth does — and the route tells you how much.

- **Express** — exactly one scenario. The happy path of the new behaviour, no
  more. If you cannot capture it in one unambiguous scenario, the route was
  mis-composed: it is not Express. Say so and send it back to Frame.
- **Standard** — a small feature set: the happy path, the realistic edges, and
  the failure modes that actually matter. Not every conceivable edge — the ones
  with real consequence.
- **Expedition** — full discovery. Work the brief and the problem space for the
  whole behaviour set. Then **group the scenarios by independence** — disjoint
  code, disjoint scenarios — because that grouping is what seeds the
  distribution map the Planner builds.
- **Hotfix** — the scenario *is* a failing regression test that reproduces the
  defect. It is written reproduce-first, before any fix, and it is
  simultaneously the BDD scenario and the TDD red. At Land it gets promoted into
  a properly-formed Given/When/Then scenario as part of the mandatory backfill.
- **Spike** — the BDD strategy does **not** run. A spike has no acceptance
  criteria — its output is knowledge, not behaviour — so Specify collapses to
  the *question* ("what do we need to learn, and what would a useful answer look
  like?") and Clarify is skipped. You write no scenario file on a Spike. If the
  spike graduates, real scenarios are written when it re-frames into a delivery
  route, where G2 applies in full.

## Clarify — QA the spec against itself and against governance

Clarify is where the spec is verified *as a spec*, before anyone builds from it.
Walk it for:

- **Contradictions** — two scenarios that cannot both hold.
- **Gaps** — a stated outcome (or a brief success signal) with no scenario.
- **Untestable Thens** — outcomes that cannot be observed from outside.
- **Ambiguous quantifiers** — "quickly", "most", "large" with no number.
- **Governance conflicts** — scenarios that cross a guardrail (a project
  coverage or security floor, an irreversible-surface rule) or that depart from
  an applicable strategy without a recorded reason. A guardrail conflict is a
  must-fix; a strategy departure is a note and a conversation.

Record each ambiguity, its resolution, and who resolved it in
`clarifications.md`. Clarify may be *light* on Standard; it may be *collapsed*
on Express only because the one scenario was certified unambiguous; it is
*skipped* on Spike because the unknown is the point; it is never simply
*absent* where the route or a routing guardrail calls for it.

## Anti-patterns

- **The implementation scenario** — `Given the cache is warm, When flushCache()
  is called…`. That tests the code's shape, not its behaviour. Scenarios outlive
  implementations.
- **The unfalsifiable Then** — "Then the user has a good experience." If it
  cannot fail, it cannot pass; it is not a scenario.
- **The orphan-creating spec** — leaving real behaviour with no scenario.
  Guardrail G2 forbids code that no stated acceptance criterion describes; the
  spec is where you prevent the orphan, not Verify.
- **The novel** — a scenario with five `Given` lines and three `When` lines.
  Split it.
