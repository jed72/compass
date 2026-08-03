---
name: bdd-specification
description: How to write Given/When/Then scenarios that double as the acceptance suite - scenario granularity, the qualities of a runnable scenario, and how depth scales by route. Triggers during Specify and Clarify.
---

# BDD Specification

**BDD is strategy S1** - expressing acceptance criteria as Given/When/Then
scenarios. It is the strong, shipped-on default *way* to satisfy **guardrail
G2**: *acceptance defined before it is built - stated, and checkable*. Keep that
relationship straight.

- **G2 is the guardrail** - hard, checkable. No code is written that no stated,
  checkable acceptance criterion describes. The outcome - acceptance is stated
  and it is checkable - is non-negotiable on every delivery route.
- **BDD is the strategy** - Given/When/Then is the *form*. It is strong and
  shipped-on, but it is a strategy: a context where the form genuinely does not
  fit is a recorded strategy deviation, not a framework violation. The hard
  line is that acceptance exists and is checkable; G/W/G is the default way to
  make it so.

In Compass the BDD spec is not documentation that precedes the tests - it *is*
the tests, read at a different time. `spec.feature.md` is written once at
Specify and run as the acceptance check at Verify. It is also the one artifact
five roles read (see `role-translation`). Write it knowing all of that.

## Example-first refinement chain

Good BDD scenarios do not appear fully formed. They emerge through a
disciplined refinement chain: **vague idea → concrete examples → acceptance
criteria → at least one executable specification each**.

1. **Start with the vague idea.** "Users should be able to reset their
   password." This is a wish, not a spec. It is the right starting point -
   not the ending point.

2. **Generate concrete examples.** Ask: *what does that look like in the
   real world?* A user with a valid email who asks for a reset link, gets a
   link. A user whose token has expired, cannot use the old link. A user who
   has already reset once today, hits a rate limit. Concrete examples ground
   abstract wishes in observable events.

3. **Distil into acceptance criteria.** Each example suggests a criterion:
   "Given a valid, unexpired reset token, the user can set a new password."
   At this step you are also applying the ubiquitous language - the shared
   vocabulary of the domain that every role (engineer, product owner, QA,
   marketer) uses consistently. Terms that are vague in conversation become
   precise in criteria. "Expired" gets a definition; "rate limit" gets a
   number.

4. **Write at least one executable specification per criterion.** The
   criterion becomes a Given/When/Then scenario. A criterion with no
   runnable scenario is a wish that never became a check - and guardrail G2
   refuses that: acceptance must be *stated and checkable*. One runnable
   scenario per criterion is the minimum; multiple scenarios cover the edges.

### Naming discipline

Scenario names carry the refinement: they state an **outcome**, not a step.
"should" as a prefix disciplines this well - "should reject an expired
token" names a required outcome, not a call-path.

- *Prefer:* `Scenario: expired token should be rejected`
- *Avoid:* `Scenario: test token expiry check`

The ubiquitous language is not optional. When "user," "subscriber," and
"account" are used interchangeably in scenarios, they carry different
implications to different readers. Pick the domain term and use it
consistently - the spec is the contract between all five roles.

### What stays refused

**User stories** ("As a [role], I want [feature], so that [outcome]") are
refused as a per-role spec format in Compass - see **ADR-004 (one spec, many
lenses)**. The rationale: a user story format embeds a single role's
perspective into the spec, which means one role's spec and another role's
spec diverge. Compass uses one `spec.feature.md` that all five roles read
through their own lens (see `role-translation`), not five separate
role-scoped artifacts. The BDD scenario *is* the shared artifact; the
role-translation lens is how each role reads it. User stories as a format
are fine upstream of Compass (in a brief, a brief or a Jira ticket) - they
are not the spec, and they do not replace the scenario.

## The Summary comes before the scenarios

A spec opens with a **Summary** in prose, above the role-guide block, before a
single Given/When/Then. Three fields:

- **Goal** - one sentence, what this change delivers in user terms.
- **Approach** - two to three sentences, the shape of the change at the level a
  lens reviewer would want.
- **Why now / what changes** - one short paragraph, the visible outcome and what
  an adjacent role would notice afterwards.

This is strategy **S7** (write for a cold reader) applied to the spec itself. A
reviewer opening a spec they did not write should be able to say what is being
built and why before deciding whether to read the scenarios in detail. Without
it they have to synthesise that picture from the Gherkin - easy for the author,
progressively harder for everyone else, and the point at which review quietly
stops happening.

The Summary is **additive**. It does not replace scenarios, and it is not a
place to restate them. Length scales with the route the same way scenario depth
does: Express one to two sentences per field, Standard ordinary paragraphs,
Expedition up to 200 words per field where the work warrants it.

## Self-review before Clarify

When `spec.feature.md` is written, run these four scans over it yourself before
handing off. **Fix what you find inline** - edit the spec directly. Do not write
a review artifact, and do not invoke a reviewer agent or subagent for this.

1. **Placeholder scan** - any unfilled `{{...}}` left in the file, including the
   three Summary fields (Goal, Approach, Why now / what changes). An unfilled
   Summary is the most common one, because it is written first and easiest to
   defer.
2. **Orphan-intent scan** - every `INT-n` in the intent-links table has at least
   one scenario serving it. An intent with no scenario is a stated outcome
   nobody agreed to check.
3. **Untestable-Then scan** - any `Then` phrased as "it works", "is correct",
   "behaves properly", or "feels right". If it cannot fail, it cannot pass.
4. **Ambiguous-quantifier scan** - "quickly", "large", "most", "soon" with no
   number attached. Either attach the number or cut the word.

**This complements Clarify; it does not replace it.** Clarify still runs on
Standard and heavier routes, and it does things this cannot: it QAs the spec
against governance, resolves contradictions, and records an ambiguity ledger
with owners. The self-check is simply what a spec-author owes Clarify - the
cheap findings fixed by whoever made them, so Clarify's attention goes to the
questions that actually need a decision.

**On Express, where Clarify is collapsed, this self-check *is* the QA.** Record
that you ran it, and what it found, in `devlog.md`. A self-check that happened
only in conversation did not happen (S4).

*Why there is no subagent critic here.* The Superpowers project shipped a
subagent review loop between spec and plan and then removed it, reporting
regression testing across five versions and five trials that found identical
quality scores whether the loop ran or not, at roughly 25 minutes of overhead
per run. Compass has not repeated that measurement and takes the published
result at face value. Compass already has
two review roles that earn their cost: **Clarify**, which QAs the spec against
governance, and the **reviewer** agent at Verify. A third pass between them
would double the time without measurably improving the spec.

## What a scenario is

```
Scenario: <a behaviour, named as an outcome>
  Given <the world is in this concrete, specific state>
  When  <exactly one triggering action happens>
  Then  <this observable, checkable outcome holds>
```

A scenario is a single behaviour with a single trigger. It is concrete enough
that someone could execute it by hand and concrete enough that a test can
assert it automatically - those are the same bar.

## The qualities of a good scenario

- **Concrete state.** "Given a user" is too vague. "Given a user with a
  verified email and no active subscription" can be set up and asserted.
- **One When.** Two actions in `When` means two scenarios. The trigger is
  singular.
- **Observable Then.** The outcome must be checkable from outside - a returned
  value, a stored state, a rendered element, an emitted event. "Then it works"
  is not a Then. "Then the response is 402 and no charge row is written" is.
- **Declarative, not procedural.** Describe *what* is true, not the click-path
  to get there. The implementation can change; the behaviour should not.
- **Named as an outcome.** "Scenario: expired token is rejected" beats
  "Scenario: test token". The name is the first thing the PM, marketer, and QA
  read.

## Scenario granularity - splitting and merging

- **Split** when a scenario has an "and" in its `When`, or branches in its
  `Then` ("Then either X or Y"), or needs a paragraph of `Given` - those are
  multiple behaviours wearing one name.
- **Merge** when two scenarios differ only in an incidental value and assert the
  same behaviour - use a scenario outline / examples table instead of copying.
- The unit is *one behaviour*, not one feature and not one line of code. A
  feature is a set of scenarios; a line of code traces *up* to a scenario but is
  not one-to-one with it.

## How depth scales by route

The vocabulary never changes. The depth does - and the route tells you how much.

- **Express** - exactly one scenario. The happy path of the new behaviour, no
  more. If you cannot capture it in one unambiguous scenario, the route was
  mis-composed: it is not Express. Say so and send it back to Frame.
- **Standard** - a small feature set: the happy path, the realistic edges, and
  the failure modes that actually matter. Not every conceivable edge - the ones
  with real consequence.
- **Expedition** - full discovery. Work the brief and the problem space for the
  whole behaviour set. Then **group the scenarios by independence** - disjoint
  code, disjoint scenarios - because that grouping is what seeds the
  distribution map the Planner builds.
- **Hotfix** - the scenario *is* a failing regression test that reproduces the
  defect. It is written reproduce-first, before any fix, and it is
  simultaneously the BDD scenario and the TDD red. At Land it gets promoted into
  a properly-formed Given/When/Then scenario as part of the mandatory backfill.
- **Spike** - the BDD strategy does **not** run. A spike has no acceptance
  criteria - its output is knowledge, not behaviour - so Specify collapses to
  the *question* ("what do we need to learn, and what would a useful answer look
  like?") and Clarify is skipped. You write no scenario file on a Spike. If the
  spike graduates, real scenarios are written when it re-frames into a delivery
  route, where G2 applies in full.

## Clarify - QA the spec against itself and against governance

Clarify is where the spec is verified *as a spec*, before anyone builds from it.
Walk it for:

- **Contradictions** - two scenarios that cannot both hold.
- **Gaps** - a stated outcome (or a brief success signal) with no scenario.
- **Untestable Thens** - outcomes that cannot be observed from outside.
- **Ambiguous quantifiers** - "quickly", "most", "large" with no number.
- **Governance conflicts** - scenarios that cross a guardrail (a project
  coverage or security floor, an irreversible-surface rule) or that depart from
  an applicable strategy without a recorded reason. A guardrail conflict is a
  must-fix; a strategy departure is a note and a conversation.

Record each ambiguity, its resolution, and who resolved it in
`clarifications.md`. Clarify may be *light* on Standard; it may be *collapsed*
on Express only because the one scenario was certified unambiguous; it is
*skipped* on Spike because the unknown is the point; it is never simply
*absent* where the route or a routing guardrail calls for it.

## Anti-patterns

- **The implementation scenario** - `Given the cache is warm, When flushCache()
  is called…`. That tests the code's shape, not its behaviour. Scenarios outlive
  implementations.
- **The unfalsifiable Then** - "Then the user has a good experience." If it
  cannot fail, it cannot pass; it is not a scenario.
- **The orphan-creating spec** - leaving real behaviour with no scenario.
  Guardrail G2 forbids code that no stated acceptance criterion describes; the
  spec is where you prevent the orphan, not Verify.
- **The novel** - a scenario with five `Given` lines and three `When` lines.
  Split it.
