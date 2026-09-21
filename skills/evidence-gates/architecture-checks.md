# Architecture checks and the verify.architecture gate

Applies only when a project has declared an architecture check, which most
have not.

## Architecture checks and the verify.architecture gate

The `verify.architecture` gate is the pattern where a routing floor promotes
architecture checks to blocking - project-declared `command-passes`
guardrails that assert structural properties of the codebase (e.g. "modules
respect the dependency direction", "no cyclic imports in the domain layer").
Adopters declare each architecture check as a project guardrail in
`governance/guardrails.yml` with `check: command-passes` and a
`params.command:` that exits 0 on pass. The gate:

- is advisory by default;
- is promoted to blocking by routing floors `RP-REQUIRE-003` (risk ∈
  {cross-cutting, critical}) and `RP-REQUIRE-004` (labels ∈ irreversible
  domains) - following the same promotion pattern as `verify.analyze`
  (`architecture/decisions/ADR-007-conditional-gate-promotion-via-floors.md`);
- clears without checking anything when no project guardrails declare
  `command-passes`: a project that has not yet declared any architecture
  checks sees no behavioural change
  (`architecture/decisions/ADR-006-backward-compat-is-non-negotiable.md`;
  `architecture/decisions/ADR-009-fitness-functions-are-project-guardrails.md`).

Evidence type accepted: `command-output`
(the subprocess result) or `test-run` (if the architecture check is run as part
of a test suite).

See `architecture/decisions/ADR-009-fitness-functions-are-project-guardrails.md`
- titled *"Architectural fitness functions are project guardrails, not
framework guardrails"* (a fitness function is an automated check that a
codebase keeps a structural property) - for the ownership-boundary decision
and the full list of alternatives considered.
