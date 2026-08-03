---
description: Capture behaviour as BDD scenarios - the shared spec every role reads
allowed-tools: Read, Write, Edit, Glob, Grep
---

# /compass:specify

Specify turns intent into Given/When/Then scenarios. This is the **shared
artifact** - the product owner reads it for intent fidelity, the marketer for
claims, the engineer for tests, QA for coverage. Write it so all four lenses
can.

## Setup

- Read `route.md`. The Specify weight there tells you how deep to go: one
  scenario (Express), a small feature set (Standard), full BDD discovery
  (Expedition), or - on a **Spike** - collapsed into *the question* (what do we
  need to learn, and what would a useful answer look like), not acceptance
  criteria for code. Honour it.
- Load the `bdd-specification` skill.
- If `route.md` reads terrain as `brownfield-unmapped`, also load
  `blueprint-distillation` - reverse-engineer the *current* behaviour into
  scenarios **before** writing the scenarios for the change. A routing
  guardrail forces this; you cannot safely change what you have not first
  described.
- Invoke the `spec-author` agent - it owns this phase.
- Read any upstream role artifacts for this task: `brief.md` (the outcome to
  hit), `ui-contract.md` (designer scenarios that flow in here), `positioning.md`
  (claims that will need backing scenarios).

## Procedure

1. **Discovery or distillation.** Greenfield: discover scenarios from the
   brief/request. Brownfield-unmapped: distil current behaviour first, then add
   the change scenarios.
2. **Write scenarios** as Given/When/Then - happy path, the realistic edges,
   the failure modes that matter. Depth scales with the route, but never to
   zero: "no scenario" is never a valid state. On Express the single scenario
   must be genuinely unambiguous, because Clarify is collapsed on the strength
   of that.
3. **Group by independence.** On larger routes, group scenarios by which
   touch disjoint surface - this grouping seeds the distribution map in Plan.
4. **Maintain traceability** - load `traceability`; each scenario traces to an
   intent (the brief, the request, the defect).
5. **Write `spec.feature.md`** from `templates/spec.feature.md` into
   `.compass/work/<task-slug>/` - the prose spec every role reads.
6. **Write the `scenarios:` block of `task.yml`** - the machine-readable index
   of the prose spec. Each scenario gets a stable `id`, a `title`, a linked
   `intent` id, and the `tests` that exercise it. This is what `compass check`
   reads to verify guardrails G2 and G3; Build then traces `changed_files` to
   these ids. On a Spike, there are no scenarios - the block stays empty.

## Hotfix note

On a Hotfix route, Specify is **reproduce-first**: the spec is a failing
regression test that reproduces the defect - simultaneously the BDD scenario
and the TDD red. Write that test now; the proper scenario is promoted into
`spec.feature.md` during the Land backfill.

## Spike note

On a Spike route, Specify is **collapsed into the question**: the spike's spec
is "what do we need to learn, and what would a useful answer look like?" - not
Given/When/Then acceptance criteria, because a spike has no acceptance criteria
to be (its output is knowledge, not behaviour). Record the question and the
timebox; the BDD strategy does not apply here. See `routes/spike.md`.

## Hand-off

Close Specify by handing the spec to a human, in these words or close to them.
The point is to make the review a deliberate moment rather than an implied one -
a reviewer who is told what to look for finds more than one who is told a file
is ready.

> I have written the spec to `.compass/work/<task-slug>/spec.feature.md`.
>
> It opens with a Summary - Goal, Approach, and Why now / what changes - so you
> can see what this delivers before reading any scenarios. Below that are N
> scenarios in M groups, each traced to an intent.
>
> Worth a cold read. Specifically, look for:
> - **Intent fidelity** - do these scenarios deliver the outcome you actually
>   want, not just the request as literally phrased?
> - **Untestable Thens** - any outcome that could not be observed from outside.
> - **Missing failure modes** - what goes wrong here that no scenario covers?
> - **Ambiguous quantifiers** - "quickly", "large", "most" with no number.
>
> On approval this goes to Clarify, which QAs it against governance and resolves
> any ambiguity into a recorded decision. Nothing is built from it until then.

Fill in the real path, counts, and group names - a prompt that still says
`<task-slug>` has not been read by the person sending it.

## Gate

On a delivery route: `spec.feature.md` exists, every scenario is
Given/When/Then, every scenario traces to an intent, no described behaviour is
missing a scenario, and `task.yml`'s `scenarios:` block mirrors it - each with
an id, a linked intent, and at least one test. On a Spike: the question and
timebox are recorded. Log to `devlog.md`. Next: `/compass:clarify` (or straight
to `/compass:plan` if `route.md` collapsed Clarify - and Clarify is skipped
entirely on Spike).
