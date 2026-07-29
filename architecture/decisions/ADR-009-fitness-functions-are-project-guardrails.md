---
id: ADR-009
title: Architectural fitness functions are project guardrails, not framework guardrails
status: proposed
date: 2026-05-25
supersedes: ''
superseded_by: ''
---

## Context

Architectural fitness functions are a way for a team to declare the structural
properties their codebase must maintain - module dependency direction, "no
cycles in the domain layer", latency budgets, "no public method longer than
N lines" - and run those declarations continuously on every change. The
design question this ADR records: how should a Compass project declare
fitness functions and have them checked?

Three options were considered:

1. Ship a curated set of framework-level fitness checks (like `no-trusted-rerun`
   or `coherence-check-passes`) that every adopter gets.
2. Require CLI maintainers to write a per-project `CHECK_FN` in `cli/compass`
   for each fitness function an adopter wants.
3. Provide a generic `command-passes` check that adopters use to declare their
   own fitness functions as project guardrails - no framework changes required
   per adopter.

The design question is where the ownership boundary sits: does the framework
own the fitness functions (options 1 and 2), or does the project own them
(option 3)?

## Decision

**Fitness functions live as project guardrails using the generic `command-passes`
check. The framework ships no fitness functions itself.**

An adopter declares a fitness function by adding to `governance/guardrails.yml`
under `project:`:

```yaml
project:
  - id: F1
    name: "Module dependency direction"
    statement: "Modules respect the public-API → internal direction."
    checks: [command-passes]
    params:
      command: "pytest tests/architecture/test_module_directions.py -q"
      timeout_seconds: 300   # optional; default 300
    checked_at: [verify]
```

`compass check` runs the command via `subprocess.run(shell=True, timeout=…, cwd=<project_root>)`.
Exit 0 → pass (emits `command-output` evidence). Non-zero → fail (emits `command-output`
evidence with exit code + stderr).

The `verify.fitness` gate is advisory by default and promoted to blocking by
routing floors `RG-FLOOR-006` (blast_radius ∈ {cross-cutting, critical}) and
`RG-FLOOR-007` (touches ∈ {auth, payments, personal-data, migrations}) -
following the ADR-007 precedent for `verify.analyze`.

When `verify.fitness` is in a task's gate set and zero project guardrails
declare `command-passes`, the gate clears by vacuity: `compass check` writes a
`command-output` evidence entry noting that 0 project guardrails are declared,
and the gate passes. This preserves the routing contract (the gate was earned;
it must be tracked) without imposing a tax on projects that haven't declared
fitness functions yet (ADR-006).

## Alternatives considered

| Alternative | Why considered | Why rejected |
|---|---|---|
| Ship a curated framework fitness suite | Simple for adopters - just works out of the box | The framework cannot know the project's architecture; any curated set would be wrong for most adopters. It would violate ADR-002 (framework grows by adding artifacts and lenses, not by adding project-specific guardrails). |
| Hand-written `CHECK_FN` per project | Direct: the CLI implements exactly what each project needs | Requires a CLI maintainer change per adopter - contradicting USP-4 (gradient from zero; zero-setup). ADR-002's growth model is checks + strategies; per-project CLI hacks are not that model. |
| Make `verify.fitness` immovable (always blocking) | Simplest mental model | Violates USP-1 (per-task computed routing). A task that doesn't touch architecture doesn't need fitness blocking. ADR-007's floor mechanism is exactly the right home for conditional promotion. |
| Use `verify.governance` evidence to gate fitness results | Reuse an existing gate | Fitness evidence is structurally different from governance evidence (command output vs. review); conflating them would blur the evidence-type model that ADR-007 relies on. |

## Consequences

**Positive:**
- Adopters can declare fitness functions with zero CLI changes - edit
  `governance/guardrails.yml`, add a `command-passes` project guardrail.
- The framework stays at five guardrails (ADR-002 honoured): `command-passes`
  is a CHECK_FN registered under G4, not a sixth guardrail.
- The pattern is reusable: any future "project-declared, route-promoted" gate
  follows the same shape (`command-passes` + a floor in `routing-policy.yml`).
- The vacuous-clear prevents cross-cutting tasks from being blocked by
  fitness gates on projects that simply haven't declared any yet (USP-4).

**Negative:**
- The `shell=True` execution model means the command runs with the project's
  inherited PATH and environment - convenient, but authors must be aware that
  the command is committed to `governance/guardrails.yml` and runs as the
  checking user.
- `timeout_seconds: 0` disables the timeout; this is documented as discouraged
  (a fitness function that never terminates is silently advisory).

**Neutral:**
- `compass policy lint` validates `command-passes` project guardrails: the
  `command:` field must be present and must be a non-empty string. Malformed
  declarations fail lint before any task relies on them (TRC-FM1).
- The `architect-lens` can surface missing fitness coverage as a boundary
  risk in `architecture-notes.md` by checking whether the project's `project:`
  section in `guardrails.yml` contains any `command-passes` entries.

## References

- `ADR-002` - framework grows by checks/strategies, not guardrails or dimensions
- `ADR-006` - backward compat: zero declared fitness functions → no-op
- `ADR-007` - the floor mechanism this ADR reuses for verify.fitness promotion
- `governance/guardrails.yml` - where `command-passes` is registered and
  `verify.fitness` gate_evidence_requirements are declared
- `governance/routing-policy.yml` - `RG-FLOOR-006` and `RG-FLOOR-007`
