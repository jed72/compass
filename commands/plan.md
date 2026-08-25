---
description: Write the design, run the governance check, and map the distribution
allowed-tools: Read, Write, Edit, Glob, Grep
---

# /compass:plan

Design turns the spec into a technical approach, checks it against
governance, and - on larger work - decides the parallel topology.
Parallelism is *decided here* and *executed at breakdown*.

(The designer's entry point is `/compass:design` - it produces the UI
contract, upstream of the acceptance criteria. This command is the
engineering planning stage: its machine key, its skill `plan-authoring`
and its agent `planner` have all said `plan` since v2, and the command
now says it too.)

## Setup

- Read `delivery-approach.md`. Its weight for this stage tells you the
  shape: a one-line "edit which file(s)" note (quick fix - no `technical-design.md`), a
  real `technical-design.md` (feature), or a full `technical-design.md` plus
  `distribution-map.md` (initiative).
- Read `acceptance-criteria.md` and `requirements-review.md` - the design is
  built on the hardened spec.
- Load the `plan-authoring` skill - how to write the design itself: what a
  work unit is, what makes one genuinely independent of another, and the
  self-review the author owes the reviewer before the design is handed over.
- Load the `governance-check` skill.
- Invoke the `planner` agent - it owns this stage.
- If a `intent.md` exists, this is where the **intent-fidelity gate** lands: the
  spec must be checked against the PRD before the design completes. Invoke
  `product-lens` to run it.

## Procedure

1. **Technical approach.** State the design. Record each design decision as
   an ADR-style note - what was chosen, what was rejected, why.
2. **Governance check.** Run `governance-check` against `governance/` - the
   guardrails (hard, blocking) and the applicable engineering strategies
   (soft, assessed). Read the machine-readable governance the CLI runs
   against: `guardrails.yml`, `strategies.md`, `routing-policy.yml`.
   `compass policy lint` structurally validates the governance YAML - run it
   if the project has tuned `governance/`. A design that crosses a guardrail
   does not pass - revise the design, never waive the guardrail. A design
   that departs from a strategy may pass, but the departure is recorded.
3. **Distribution map** (when the work splits into independent units). Read
   the scenario groups from `acceptance-criteria.md`; units that touch
   disjoint code and satisfy disjoint scenarios can run in parallel. On a
   feature a short list of 2-3 units is enough; on an initiative write the
   full `distribution-map.md` from its template - even if a cap forces it
   solo, the map records what *could* have been parallel and why it wasn't.
   Stream count comes from the map; topology thresholds from
   `.compass/config.yml`; a policy cap can bound the count.
4. **Write `technical-design.md`** from `templates/technical-design.md` (and
   `distribution-map.md` from its template when applicable) into
   `.compass/work/<task-slug>/`.

## Hand-off

Close the design by handing the technical approach to a human. This is the
last review before code is written, and the cheapest point at which to change
the design.

> I have written the design to `.compass/work/<task-slug>/technical-design.md`
> (and the distribution map to `distribution-map.md`).
>
> It records N design decisions, the governance check against all of
> `governance/`, and M work units.
>
> Worth a read before implementation. Specifically, look for:
> - **Design decisions you would make differently** - each records what was
>   chosen and what was rejected, so the disagreement should be easy to
>   locate.
> - **A decision with no alternative considered** - that is usually not a
>   decision yet.
> - **Work units that are not as independent as claimed** - optimistic
>   decomposition surfaces as a collision at integration, not here.
> - **Anything still unfinished** - `compass design lint` reports placeholder
>   phrases, but a design can be vague without using one.
>
> On approval this goes to breakdown, or straight to implementation on solo
> work.

## Gate

`technical-design.md` exists; the governance check passed (record its result and link
the record); if a PRD
exists, the intent-fidelity gate passed; if the work is parallelisable, a
distribution map exists. Log to `devlog.md`. Next: `/compass:breakdown` (or
straight to `/compass:implement` on solo work).
