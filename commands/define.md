---
description: Acceptance criteria as BDD scenarios - the shared spec every role reads
allowed-tools: Read, Write, Edit, Glob, Grep
---

# /compass:define

Define turns intent into Given/When/Then acceptance criteria. This is the
**shared artifact** - the product owner reads it for intent fidelity, the
marketer for claims, the engineer for tests, QA for coverage. Write it so all
four roles can.

## Setup

- Read `delivery-approach.md`. Its weight for this stage tells you how deep
  to go: one scenario (quick fix), a small feature set (feature), full BDD
  discovery (initiative), or - on a **spike** - collapsed into *the question*
  (what do we need to learn, and what would a useful answer look like), not
  acceptance criteria for code. Honour it.
- Load the `bdd-specification` skill.
- If `delivery-approach.md` assesses familiarity as `brownfield-unmapped`,
  also load `blueprint-distillation` - reverse-engineer the *current*
  behaviour into scenarios **before** writing the scenarios for the change. A
  policy floor forces this; you cannot safely change what you have not first
  described.
- Invoke the `spec-author` agent - it owns this stage.
- Read any upstream role artifacts for this issue: `prd.md` (the outcome to
  hit), `ui-contract.md` (designer scenarios that flow in here),
  `positioning.md` (claims that will need backing scenarios).

## Procedure

1. **Discovery or distillation.** Greenfield: discover scenarios from the
   PRD or request. Brownfield-unmapped: distil current behaviour first, then
   add the change scenarios.
2. **Write scenarios** as Given/When/Then - happy path, the realistic edges,
   the failure modes that matter. Depth scales with the delivery approach,
   but never to zero: "no scenario" is never a valid state. On a quick fix
   the single scenario must be genuinely unambiguous, because the
   requirements review is collapsed on the strength of that.
3. **Group by independence.** On larger work, group scenarios by which touch
   disjoint surface - this grouping seeds the distribution map at the design
   stage.
4. **Maintain traceability** - load `traceability`; each scenario traces to
   an intent (the PRD, the request, the defect).
5. **Write `acceptance-criteria.md`** from `templates/acceptance-criteria.md`
   into `.compass/work/<task-slug>/` - the prose spec every role reads.
6. **Write the `scenarios:` block of `task.yml`** - the machine-readable
   index of the prose spec. Each scenario gets a stable `id`, a `title`, a
   linked `intent` id, and the `tests` that exercise it. This is what
   `compass check` reads to verify the acceptance-before-code and
   traceability guardrails; implementation then traces `changed_files` to
   these ids. On a spike, there are no scenarios - the block stays empty.

## Hotfix note

On a hotfix, this stage is **reproduce-first**: the spec is a failing
regression test that reproduces the defect - simultaneously the BDD scenario
and the TDD red. Write that test now; the proper scenario is promoted into
`acceptance-criteria.md` as the follow-up owed at ship time.

## Spike note

On a spike, this stage is **collapsed into the question**: the spike's spec
is "what do we need to learn, and what would a useful answer look like?" -
not Given/When/Then acceptance criteria, because a spike has no acceptance
criteria to be (its output is knowledge, not behaviour). Record the question
and the timebox; the BDD strategy does not apply here. See `approaches/spike.md`.

## Hand-off

Close this stage by handing the spec to a human, in these words or close to
them. The point is to make the review a deliberate moment rather than an
implied one - a reviewer who is told what to look for finds more than one who
is told a file is ready.

> I have written the acceptance criteria to
> `.compass/work/<task-slug>/acceptance-criteria.md`.
>
> It opens with a Summary - Goal, Approach, and Why now / what changes - so
> you can see what this delivers before reading any scenarios. Below that are
> N scenarios in M groups, each traced to an intent.
>
> Worth a cold read. Specifically, look for:
> - **Intent fidelity** - do these scenarios deliver the outcome you actually
>   want, not just the request as literally phrased?
> - **Untestable Thens** - any outcome that could not be observed from
>   outside.
> - **Missing failure modes** - what goes wrong here that no scenario covers?
> - **Ambiguous quantifiers** - "quickly", "large", "most" with no number.
>
> On approval this goes to refine - the requirements review - which QAs it
> against governance and resolves any ambiguity into a recorded decision.
> Nothing is built from it until then.

Fill in the real path, counts, and group names - a prompt that still says
`<task-slug>` has not been read by the person sending it.

## Gate

On delivery work: `acceptance-criteria.md` exists, every scenario is
Given/When/Then, every scenario traces to an intent, no described behaviour
is missing a scenario, and `task.yml`'s `scenarios:` block mirrors it - each
with an id, a linked intent, and at least one test. On a spike: the question
and timebox are recorded. Log to `devlog.md`. Next: `/compass:refine` (or
straight to `/compass:design` if `delivery-approach.md` collapsed the
requirements review - and it is skipped entirely on a spike).
