---
id: ADR-007
title: Gates may be conditionally promoted from advisory to blocking via routing-policy floors; advisory gates write evidence but do not block Land
status: proposed
date: 2026-05-25
supersedes: ''
superseded_by: ''
---

## Context

Compass has two classes of gate today: **immovable gates** (`verify.correctness`, `verify.governance`, `verify.traceability`) baked into every delivery route's `route_shapes.*.gates` list, and **role-conditioned gates** (`verify.claims` via `RG-ROLE-001`) added when a specific role is in play. Both are unconditional once their trigger condition holds: immovable gates always block; role-conditioned gates always block when the role is present.

The `compass analyze` capability needs a third lifecycle: a gate that is **advisory** on routes whose blast radius does not warrant it and **blocking** on routes whose readings *do* warrant it - *advisory by default; a gate only by route, never globally*. The same pattern would apply to future capabilities (e.g. a hypothetical `verify.migration-plan` that should block on migration-touching tasks but not others).

The framework also requires that the promotion rule be encoded in `governance/routing-policy.yml`, not hard-coded in `cli/compass` - both to honour ADR-001 (the evaluator applies policy; it does not encode it) and to satisfy `TRC-A12` (the gate-promotion test reads the policy file).

The existing floor schema supports `force_minimum_route`, `never_skip`, `require_phase`, and `require_skill` - none of which adds a gate to a matched route's gate set.

## Decision

Extend the routing-policy floor schema with a new optional property `add_gate: <gate-id>`. A floor with `add_gate` adds the named gate to the matched route's `task.yml.gates` list, with `status: pending`, exactly as if the gate had been in the route shape's gates list from the start. The new floor entries that introduce `verify.analyze` are:

```yaml
- id: RG-FLOOR-004
  when: { blast_radius: critical }
  add_gate: verify.analyze
  rationale: "Cross-artifact coherence checked before high-care work lands."

- id: RG-FLOOR-005
  when: { touches_any: [auth, payments, personal-data, migrations] }
  add_gate: verify.analyze
  rationale: "Irreversible-surface tasks have coherence checked before Land."
```

The OR semantics from the originating requirement (clarifications Q7) are expressed as two separate floor entries - consistent with the existing policy that each floor has a single `when:` clause.

When a route is below the promotion threshold and `compass analyze` is invoked, the analyze report writes as advisory evidence: a typed `command-output` entry with id prefix `EV-ANALYZE-ADVISORY-<task>-<timestamp>`. Advisory evidence does not satisfy `gate-evidence-present` for `verify.analyze` (because `gate_evidence_requirements` for `verify.analyze` accepts only the typed `coherence-check` evidence type), so an advisory run cannot accidentally clear the gate if the route is later re-framed and the gate is added.

`verify.analyze`'s mechanical check is `coherence-check-passes`, registered as a `CHECK_FN` under guardrail G4 - not as a new guardrail. The five-guardrail count stays at five (ADR-002 honoured).

## Alternatives considered

| Alternative | Why considered | Why rejected |
|---|---|---|
| Add `verify.analyze` directly to each `route_shapes.*.gates` list that should have it | Avoids extending the floor schema | Duplicates the gate-promotion logic across multiple shape definitions; couples the shape definitions to the floor's condition; if `RG-FLOOR-003`'s irreversible-surface conditions ever change, the gate list must be updated in two places |
| Have the route evaluator infer `verify.analyze` from `touches`/`blast_radius` readings without a floor rule | Smallest schema change | Fails `TRC-A12` (the gate must be driven by routing-policy, not hard-coded in the CLI); violates ADR-001 (evaluator's job is to apply, not encode) |
| Add `verify.analyze` as a sixth guardrail (G6) | Most direct enforcement | ADR-002 explicitly rejects guardrail growth as the mechanism for new checks. The framework grows by adding artifacts and lenses; `verify.analyze` is a CHECK_FN under G4 |
| Add `verify.analyze` as an immovable gate (always on, every route) | Simplest mental model | Violates the per-task computed routing principle and the "advisory by default" requirement - promoting a check to a gate globally imposes ceremony irrespective of route, exactly what the adaptive-routing pattern exists to avoid |

## Consequences

**Positive:**
- A third gate-lifecycle class (advisory-with-conditional-promotion) is available for future capabilities that don't warrant unconditional gating but do warrant gating on high-care work.
- The `add_gate` floor property is reusable - a future `verify.migration-plan` or `verify.architecture-review` could follow the same pattern.
- The conditions for promotion are visible in `governance/routing-policy.yml` and testable by reading the same file (TRC-A12).
- The advisory/blocking split is encoded in the evidence type system, not in the gate-presence check, so a misconfigured advisory run cannot accidentally clear a blocking gate.

**Negative:**
- The routing-policy schema gains one property (`add_gate`); `schemas/routing-policy.schema.json` and `compass policy lint` must be updated. This is a small additive change but extends the public schema surface adopters validate against.
- The reuse of `RG-FLOOR-003`'s exact conditions for the new floor (`auth, payments, personal-data, migrations`) couples the analyze gate to that list. If `RG-FLOOR-003` is ever loosened, `verify.analyze`'s promotion threshold loosens with it. This is intentional - the framework's notion of "irreversible-surface tasks" should be one list, not many - but it should be cited explicitly when either floor is amended.

**Neutral / follow-on:**
- The framework will need a clear pattern for documenting which gates use which lifecycle. Suggested: `governance/guardrails.md` gains a "Gate lifecycle" subsection that distinguishes immovable, role-conditioned, and floor-conditioned gates.
- If a future capability needs a `remove_gate` floor (a gate that *should not* apply on certain routes), this ADR establishes the symmetric pattern; that addition would be a separate ADR amendment.

## References

- `ADR-001` (judgement and mechanism are separated - the evaluator's role boundary)
- `ADR-002` (framework grows by artifacts and lenses, not guardrails or dimensions)
- `governance/routing-policy.yml` - the file the floors live in
- `governance/guardrails.yml` - the file the new check + evidence type are registered in
