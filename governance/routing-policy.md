# Routing Policy - How the Needle Is Bounded and Biased

The Needle (the router - see `routes/router.md`) reads four context dimensions
during Frame and computes a route. This file governs that computation, using
the same split as the rest of `governance/`:

- **Routing guardrails** - hard. They *bound* what the Needle may do. A
  routing guardrail can force a route to be at least a certain weight, cap how
  far it may scale up, or staple on a gate that no route may remove. The
  Needle cannot route around these, and a human cannot override them per-task
  - changing one means amending this file.
- **Routing strategies** - soft. They *bias* what the Needle does by default -
  the route shapes it reaches for, the way it breaks ties. A routing strategy
  is the starting point; the Needle (or a human) can depart from it for a
  given task, and that departure is just recorded in `delivery-approach.md`.

This is the answer to the obvious objection to any adaptive framework - *"if
the process can flex, what stops it flexing to nothing?"* The routing
guardrails are what stop it. The flex is real, and it is bounded by this file.

The Needle applies this policy during Frame, after reading the four dimensions
and composing a candidate route, before writing `delivery-approach.md`. Every routing
guardrail that fires is recorded in `delivery-approach.md` with its rationale - so any
`delivery-approach.md` shows not just the route, but which bounds were active and why.

> **Version:** 0.2.0 · **Last amended:** {{DATE}}

**This document explains; `routing-policy.yml` enforces.** The companion
`governance/routing-policy.yml` is the machine-readable, authoritative policy -
it has the live floors, caps, immovable gates, role rules, and default shapes,
each with a stable id, and `compass route evaluate` runs it deterministically.
The YAML excerpts below are *illustrative*; where this prose and that file
could be read to differ, the `.yml` wins. The crucial boundary: the
four-dimension *readings* are judgement (the Needle produces them, and that
judgement is the adaptivity); this policy governs only what happens *after* -
composing and constraining the route from the readings, which is deterministic.

---

## Routing guardrails (hard - they bound the Needle)

### `floors` - a reading forces *at least* a given route

A floor says: "when the context looks like X, the route may not be lighter
than Y." Floors are how domain risk overrides the raw dimension readings - the
canonical case is that magnitude reads a one-line auth change as `atomic`, but
a floor forces it heavier because the blast radius of auth is not a function
of line count.

### `caps` - limits on scaling up

The mirror of floors. Where a floor stops the Needle going too light, a cap
stops it going too heavy in a way that adds risk. The default cap - critical
blast radius caps worktrees at 1 - encodes a real tradeoff: a swarm is speed,
but it is also coordination risk, and on a critical change the coordination
risk costs more than the speed saves.

### `immovable_gates` - gates no route may remove

Routes adapt *which* review dimensions apply. Immovable gates are the floor
under that adaptation: no reading, and no route, can drop one.

### blocking `role_rules` - a role's involvement enforces a gate

When a role's involvement makes a gate non-negotiable, that is a routing
guardrail. The two defaults wire the non-engineering roles in as enforced
participants, not optional consultees.

The shipped defaults (see `routing-policy.yml` for the live, id-tagged set):

- **floors** - `RG-FLOOR-001` critical blast radius → at least Expedition,
  never skip clarify/verify/land; `RG-FLOOR-002` brownfield-unmapped terrain →
  Specify runs full-weight with `blueprint-distillation`; `RG-FLOOR-003`
  touching auth/payments/personal-data/migrations → at least Expedition.
- **caps** - `RG-CAP-001` critical blast radius caps worktrees at 1.
- **immovable_gates** - `RG-GATE-001..004`: `verify.correctness`,
  `verify.governance`, `verify.regression`, `verify.claims`.
- **role_rules** - `RG-ROLE-001` the product-marketer's involvement blocks Land
  until claims trace to scenarios; `RG-ROLE-002` the product-owner's involvement
  gates Plan on the spec being checked against the brief.

The `verify.governance` immovable gate is what makes guardrail G5 ("a human
signs off on the irreversible") land in practice - a change that `touches`
irreversible surface is floored to Expedition, where the human checkpoint is
part of the gate set.

---

## Routing strategies (soft - they bias the Needle)

These are the Needle's defaults: the route shapes it reaches for, and how it
breaks ties. The Needle starts here and tunes; a departure is normal and is
recorded in `delivery-approach.md`, not punished.

```yaml
routing_strategies:
  # The reference route shapes the Needle composes toward. See routes/.
  default_shapes:
    - reading: { magnitude: [atomic, small], blast_radius: [trivial, contained], terrain: brownfield-mapped }
      lean_toward: express
    - reading: { magnitude: standard }
      lean_toward: standard
    - reading: { magnitude: [large, product] }
      lean_toward: expedition
    - reading: { urgency: live-defect, magnitude: [atomic, small] }
      lean_toward: hotfix
    - reading: { intent: exploration }      # "I need to understand this before I can frame it"
      lean_toward: spike

  # Tie-breaking biases.
  biases:
    - "When magnitude is genuinely unclear, estimate up - it is cheaper to
       collapse a phase that turned out easy than to discover mid-Build that
       the route was too light."
    - "A non-engineering role in play usually pulls the route heavier, because
       it adds artifacts and assessed strategies - but this is a bias, not a
       floor. A marketer glancing at a tiny change need not trigger Expedition."
    - "Prefer the lightest route that still clears the routing guardrails and
       the applicable gates. Ceremony is a cost; spend it where it buys safety."

  # Advisory role defaults (the blocking versions are routing guardrails above).
  role_defaults:
    - when: { role: designer }
      suggest_artifact: ui-contract.md
      rationale: "A new user-facing surface usually wants a UI contract; advisory."
```

---

## Schema reference

The authoritative structure is `routing-policy.yml`, validated by `compass
policy lint` - against the executable `schemas/routing-policy.schema.json`
(when `jsonschema` is installed) and the CLI's built-in linter. The
human-readable field-by-field companion is `schemas/routing-policy.reference.yml`.
In brief:

`when` conditions match against the readings - `blast_radius`, `terrain`,
`magnitude`, `role`, `intent`, `urgency` - or `touches_any` (a domain-tag list:
`auth`, `payments`, `personal-data`, `migrations`, `public-api`, …). A list
value means "any of".

Routing-guardrail keys: `force_minimum_route`, `require_phase`,
`require_skill`, `never_skip`, `max_worktrees`, `forbid_route`,
`block_phase` + `until`, `require_artifact`, `gate`. Every guardrail carries a
stable `id` (e.g. `RG-FLOOR-001`) so `delivery-approach.md` can name exactly which one
fired.

Routing-strategy keys: `lean_toward`, `suggest_artifact`, free-text `biases`.

---

## Amending this file

- **Loosening a routing guardrail weakens the framework for everyone,
  quietly.** It should be deliberate, logged, ideally reviewed - not a
  convenience edit mid-task. If a guardrail keeps being painful, fix the route
  that makes it painful; do not remove the guardrail.
- **Routing strategies are meant to be tuned.** Adjust `default_shapes` and
  `biases` freely as the team learns how its work actually distributes. That
  is the soft layer doing its job.
