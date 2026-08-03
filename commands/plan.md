---
description: Build the technical plan, run the governance check, and map distribution
allowed-tools: Read, Write, Edit, Glob, Grep
---

# /compass:plan

Plan turns the spec into a technical approach, checks it against governance,
and - on larger work - decides the parallel topology. Parallelism is *decided
here* and *executed in Distribute*.

## Setup

- Read `route.md`. The Plan weight tells you the shape: a one-line "edit which
  file(s)" note (Express - no `plan.md`), a real `plan.md` (Standard), or a
  full `plan.md` plus `distribution-map.md` (Expedition).
- Read `spec.feature.md` and `clarifications.md` - the plan is built on the
  hardened spec.
- Load the `governance-check` skill.
- Invoke the `planner` agent - it owns this phase.
- If a `brief.md` exists, this is where the **intent-fidelity gate** lands: the
  spec must be checked against the brief before Plan completes. Invoke
  `product-lens` to run it.

## Procedure

1. **Technical approach.** State the design. Record each design decision as an
   ADR-style note - what was chosen, what was rejected, why.
2. **Governance check.** Run `governance-check` against `governance/` - the
   guardrails (hard, blocking) and the applicable engineering strategies (soft,
   assessed). Read the machine-readable governance the CLI runs against:
   `guardrails.yml`, `strategies.md`, `routing-policy.yml`. `compass policy
   lint` structurally validates the governance YAML - run it if the project has
   tuned `governance/`. A plan that crosses a guardrail does not pass - revise
   the plan, never waive the guardrail. A plan that departs from a strategy may
   pass, but the departure is recorded.
3. **Distribution map** (when the work splits into independent units). Read the
   scenario groups from `spec.feature.md`; units that touch disjoint code and
   satisfy disjoint scenarios can run in parallel. On Standard a short list of
   2–3 units is enough; on Expedition write the full `distribution-map.md` from
   its template - even if a cap forces it solo, the map records what *could*
   have been parallel and why it wasn't. Stream count comes from the map;
   topology thresholds from `.compass/config.yml`; a routing guardrail can
   cap the count.
4. **Write `plan.md`** from `templates/plan.md` (and `distribution-map.md` from
   its template when applicable) into `.compass/work/<task-slug>/`.

## Hand-off

Close Plan by handing the technical approach to a human. This is the last review
before code is written, and the cheapest point at which to change the design.

> I have written the plan to `.compass/work/<task-slug>/plan.md`
> (and the distribution map to `distribution-map.md`).
>
> It records N design decisions, the governance check against all of
> `governance/`, and M work units.
>
> Worth a read before Build. Specifically, look for:
> - **Design decisions you would make differently** - each records what was
>   chosen and what was rejected, so the disagreement should be easy to locate.
> - **A decision with no alternative considered** - that is usually not a
>   decision yet.
> - **Work units that are not as independent as claimed** - optimistic
>   decomposition surfaces as a collision at integration, not here.
> - **Anything still unfinished** - `compass plan lint` reports placeholder
>   phrases, but a plan can be vague without using one.
>
> On approval this goes to Distribute, or straight to Build on a solo route.

## Gate

`plan.md` exists; the governance check passed (paste its result); if a brief
exists, the intent-fidelity gate passed; if the work is parallelisable, a
distribution map exists. Log to `devlog.md`. Next: `/compass:distribute` (or
straight to `/compass:build` on a solo route).
