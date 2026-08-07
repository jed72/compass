---
description: Resolve spec ambiguities and QA the spec against itself and against governance
allowed-tools: Read, Write, Edit, Glob, Grep
---

# /compass:clarify

Clarify hardens the spec before any plan is built on it. It resolves
ambiguities and QAs `acceptance-criteria.md` against itself and against `governance/` -
the guardrails and strategies.

## First: is Clarify in play?

Read `delivery-approach.md`. Clarify is **collapsed on Express** (the single scenario was
certified unambiguous at Specify), **collapsed on Hotfix** (the reproduction
*is* the clarification), and **skipped on Spike** (there is nothing to QA - the
behaviour is the unknown). If `delivery-approach.md` collapsed or skipped it, stop - say
so, confirm the de-scope reason still holds, and point the user to
`/compass:plan`. Do not re-add a phase the route skipped, and do not skip one
it kept.

On a collapsed- or skipped-Clarify route the **Definition of Ready** is
satisfied by construction - Express by the Needle certifying the single
scenario unambiguous, Hotfix by the reproduction test being the spec, Spike by
having no acceptance criteria to be ready against - so there is no separate
checklist to fill. On Standard and Expedition it is the explicit gate below.

On Standard, Clarify is a light-to-full pass - light, never absent. On
Expedition it is a full pass with an explicit ambiguity ledger and
non-engineering role review.

## What Specify already did - and what is left for you

The spec-author ran a four-scan self-review inline at the end of Specify,
before handing the spec over: a **placeholder** scan, an **orphan**-intent
scan, an **untestable**-`Then` scan, and an **ambiguous**-quantifier scan.
Those findings were fixed in place by whoever made them. It runs on every
route, including Express.

**Clarify does not repeat them.** Re-running four mechanical scans over a file
someone has just scanned spends a phase to find nothing. If you do hit one
still outstanding, that means the self-review was skipped - say so, then fix
it; do not quietly absorb it as your own work.

What is left for you is everything the author could not settle alone:

- **Contradictions** between scenarios that cannot both hold.
- **Gaps** across the whole set - a stated outcome, or a `prd.md` success
  signal, with no scenario.
- **Governance conflicts** - a scenario that crosses a guardrail, or departs
  from an applicable strategy with no recorded reason.
- **Ambiguities that need a decision** rather than a correction, each recorded
  in `requirements-review.md` with its resolution and who made it.

The dividing line is who can close the finding. An unfilled placeholder has one
correct answer and the author already knows it. "Which of these two scenarios
is wrong?" does not, and that is what a phase with a reviewer in it is for. The
same split is written from the other side in
`skills/bdd-specification/SKILL.md`.

## Setup

- Load `bdd-specification`; the `spec-author` agent owns this continuation.
- Read `governance/` - the spec is QA'd against the guardrails and the
  applicable strategies here.
- If a non-engineering role is in play, this is where they review: invoke
  `product-lens` (intent fidelity against `prd.md`) and/or `marketing-lens`
  (every planned claim has a candidate scenario).

## Procedure

1. **Self-QA the spec.** Contradictory scenarios? Undefined terms? Edges named
   but not specified? Failure modes missing?
2. **Governance QA.** Does the spec hold the guardrails (especially G2 -
   acceptance defined and checkable, G3 - traceability) and respect the
   applicable strategies, including the voice strategies where claims are
   involved?
3. **Resolve.** For each ambiguity, either resolve it (update `acceptance-criteria.md`)
   or record it as an open question with an owner. An unresolved ambiguity is
   not allowed to silently pass into Plan.
4. **Write `requirements-review.md`** from `templates/requirements-review.md`: the
   ambiguity ledger, each entry resolved or assigned.

## Re-frame trigger

If Clarify reveals the spec is bigger or more ambiguous than the route assumed,
**stop and re-frame** (`/compass:frame --reframe`) - do not push a Standard
route through an Expedition-shaped problem.

## Hand-off

Close Clarify by handing the ambiguity ledger to a human. This is the last
review before work is planned against the spec, so the questions here are about
decisions, not wording.

> I have written the ambiguity ledger to
> `.compass/work/<task-slug>/requirements-review.md`, and updated `acceptance-criteria.md`
> where a resolution changed it.
>
> N ambiguities were found and resolved. The ones that changed what gets built
> are: <short list>.
>
> Worth a read before Plan. Specifically, look for:
> - **Decisions you disagree with** - each entry records what was decided and by
>   whom; a resolution recorded is not the same as a resolution you would make.
> - **Resolutions that quietly widened scope** - a question answered by adding
>   work should be visible as such.
> - **The Definition of Ready** - every box is checked, and each one is meant to
>   be true rather than ticked.
>
> On approval this goes to Plan, which turns the spec into a technical approach
> and runs the governance check against it.

## Gate

`requirements-review.md` exists; every ambiguity is resolved or owned; the spec
passes governance QA; and the **Definition of Ready** checklist at the foot
of `requirements-review.md` is fully checked - that is the entry gate into Plan, and
an unchecked box stops Plan from starting. Log to `devlog.md`. Next:
`/compass:plan`.
