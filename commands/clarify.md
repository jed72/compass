---
description: Resolve spec ambiguities and QA the spec against itself and against governance
allowed-tools: Read, Write, Edit, Glob, Grep
---

# /compass:clarify

Clarify hardens the spec before any plan is built on it. It resolves
ambiguities and QAs `spec.feature.md` against itself and against `governance/` -
the guardrails and strategies.

## First: is Clarify in play?

Read `route.md`. Clarify is **collapsed on Express** (the single scenario was
certified unambiguous at Specify), **collapsed on Hotfix** (the reproduction
*is* the clarification), and **skipped on Spike** (there is nothing to QA - the
behaviour is the unknown). If `route.md` collapsed or skipped it, stop - say
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

## Setup

- Load `bdd-specification`; the `spec-author` agent owns this continuation.
- Read `governance/` - the spec is QA'd against the guardrails and the
  applicable strategies here.
- If a non-engineering role is in play, this is where they review: invoke
  `product-lens` (intent fidelity against `brief.md`) and/or `marketing-lens`
  (every planned claim has a candidate scenario).

## Procedure

1. **Self-QA the spec.** Contradictory scenarios? Undefined terms? Edges named
   but not specified? Failure modes missing?
2. **Governance QA.** Does the spec hold the guardrails (especially G2 -
   acceptance defined and checkable, G3 - traceability) and respect the
   applicable strategies, including the voice strategies where claims are
   involved?
3. **Resolve.** For each ambiguity, either resolve it (update `spec.feature.md`)
   or record it as an open question with an owner. An unresolved ambiguity is
   not allowed to silently pass into Plan.
4. **Write `clarifications.md`** from `templates/clarifications.md`: the
   ambiguity ledger, each entry resolved or assigned.

## Re-frame trigger

If Clarify reveals the spec is bigger or more ambiguous than the route assumed,
**stop and re-frame** (`/compass:frame --reframe`) - do not push a Standard
route through an Expedition-shaped problem.

## Gate

`clarifications.md` exists; every ambiguity is resolved or owned; the spec
passes governance QA; and the **Definition of Ready** checklist at the foot
of `clarifications.md` is fully checked - that is the entry gate into Plan, and
an unchecked box stops Plan from starting. Log to `devlog.md`. Next:
`/compass:plan`.
