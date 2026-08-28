# Architectural architecture checks and the verify.fitness gate

Split out of `SKILL.md`: it applies only when a project has declared a architecture check, which most have not.

## Architectural architecture checks and the verify.fitness gate

The `verify.fitness` gate is the route-promoted pattern for architectural
architecture checks - project-declared `command-passes` guardrails that assert
structural properties of the codebase (e.g. "modules respect the dependency
direction", "no cyclic imports in the domain layer"). Adopters declare each
architecture check as a project guardrail in `governance/guardrails.yml` with
`check: command-passes` and a `params.command:` that exits 0 on pass. The gate
is advisory by default and promoted to blocking by routing floors `RP-REQUIRE-003`
(risk ∈ {cross-cutting, critical}) and `RP-REQUIRE-004` (touches ∈
irreversible domains) - following the same promotion pattern as `verify.analyze`
(ADR-007). When no project guardrails declare `command-passes`, the gate clears
without checking anything: a project that has not yet declared any architecture checks sees no
behavioural change (ADR-006; ADR-009). Evidence type accepted: `command-output`
(the subprocess result) or `test-run` (if the architecture check is run as part
of a test suite).

See ADR-009 - *Architectural architecture checks are project guardrails, not
framework guardrails* - for the ownership-boundary decision and the full list
of alternatives considered.

