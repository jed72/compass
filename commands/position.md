---
description: Product marketer entry point - positioning and launch readiness, every claim traceable
argument-hint: "<what is being positioned>"
allowed-tools: Read, Write, Edit, Glob, Grep
---

# /compass:position

The product marketer entry point. The marketer works **parallel to the
define stage** - not downstream of a finished engineering process. Every
public claim must trace to a passing scenario; the claims gate blocks
shipping until it does.

**Subject:** $ARGUMENTS

## Setup

- Adopt the marketer's vocabulary - claims, voice, audience.
- Load `role-translation` - positioning is the claims perspective on the
  shared spec.
- Read `governance/strategies.md` - the marketer curates the voice &
  positioning strategies there; voice, claims discipline, and the honesty
  policy come from them. Read `governance/guardrails.md` too - the
  traceability guardrail keeps every public claim traced to a backing
  criterion.
- Read `acceptance-criteria.md` if it exists - claims point at scenarios.
- Invoke the `marketing-lens` agent.

## Procedure

1. **Write positioning.** From `templates/positioning.md`: the audience,
   the core message, and the claim set. For **every claim**, name the
   scenario in `acceptance-criteria.md` that backs it. A claim with no
   backing scenario is not yet a claim - it is either a scenario that needs
   writing (raise it with `spec-author` at the define stage) or a claim
   that must be dropped.
2. **Write launch readiness.** From `templates/launch-readiness.md`: the
   checklist of what must be true to launch - each claim backed, each
   backing scenario passing, voice consistent with the voice & positioning
   strategies, the honesty policy applied to what the product cannot yet
   do.
3. **Write `positioning.md` and `launch-readiness.md`** into
   `.compass/work/<task-slug>/`.

## How this shapes the delivery approach

The `product-marketer` role (see the delivery-approach rubric and the
routing policy's `role_rules`) adds the `positioning.md` /
`launch-readiness.md` artifacts, turns on the `claims` review dimension,
and **blocks shipping** until every claim in `positioning.md` traces to a
passing scenario. `verify.claims` is an immovable gate - no delivery
approach removes it.

## Gate

`positioning.md` and `launch-readiness.md` exist; every claim names a
backing scenario; voice is consistent with the voice & positioning
strategies in `governance/`. The claims gate is then carried into
`/compass:verify` and enforced at `/compass:ship`.
