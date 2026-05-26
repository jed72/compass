# Architecture Decision Records — Compass Framework

This directory contains Compass's own Architecture Decision Records (ADRs).
These are the founding decisions that define how the framework itself works and
why. Every framework-touching task should read these before proposing changes
to the pipeline, routing, guardrails, strategies, or role model.

## Why ADRs matter here

Compass is a framework that recommends ADRs for adopting projects. These ADRs
are Compass practising what it preaches: the framework's own structural
decisions are recorded here as first-class artefacts, not buried in git history
or living only in conversation.

The architect-lens reads these ADRs when consulting on a framework-touching
task. When the lens cites "ADR-001" or "ADR-003", it is citing a decision
recorded in this directory.

## Numbering convention

ADRs are numbered sequentially: `ADR-001`, `ADR-002`, `ADR-003`, …

Rules:
- Numbers are **never reused**. If an ADR is superseded, the old number and
  file remain (with `status: superseded`). The new ADR gets the next available
  number.
- Numbers are **per-tree**. Compass's `architecture/decisions/` numbering
  starts at ADR-001. An adopting project's `architecture/decisions/` also
  starts at ADR-001 — these are different trees, different sequences.
- **Supersession** is via the `superseded_by` field, not by renumbering. If
  ADR-003 is replaced by a new decision, ADR-003 gains `superseded_by: ADR-007`
  and ADR-007 gains `supersedes: ADR-003`. The chain is navigable in both
  directions.
- The `compass adr new <slug>` subcommand assigns the next sequential number
  and registers the file here. On a swarm with concurrent worktrees, two
  streams may produce the same number — the orchestrator resolves the conflict
  at integration by renumbering one side (see ADR-001 for the decision context
  that informs this).

## Index

| ID | Title | Status | Principles covered |
|---|---|---|---|
| [ADR-001](ADR-001-judgement-and-mechanism-are-separated.md) | Judgement and mechanism are separated | accepted | Inv-1 (readings are sole judgement field), Inv-7 (mechanism is deterministic) |
| [ADR-002](ADR-002-framework-grows-by-adding-artifacts-not-rules.md) | The framework grows by adding artifacts and lenses, not by adding guardrails or routing dimensions | accepted | Inv-2 (five guardrails), Inv-3 (adaptive routing untouched) |
| [ADR-003](ADR-003-flow-advises-but-never-gates.md) | Flow advises but never gates | accepted | Inv-4 (Flow advises, never gates) |
| [ADR-004](ADR-004-one-spec-many-lenses.md) | One spec, many lenses; the lens annotates, never forks | accepted | Inv-5 (one spec, many lenses) |
| [ADR-005](ADR-005-state-lives-on-disk.md) | State lives on disk; conversation reconstructs from artifacts | accepted | Inv-6 (persistence over conversation) |
| [ADR-006](ADR-006-backward-compat-is-non-negotiable.md) | Backward compat is non-negotiable | accepted | Inv-8 (backward compat for projects without new surfaces) |
| [ADR-007](ADR-007-conditional-gate-promotion-via-floors.md) | Gates may be conditionally promoted from advisory to blocking via routing-policy floors; advisory gates write evidence but do not block Land | proposed | RG-FLOOR-004/005, verify.analyze (advisory-by-default lifecycle) |
| [ADR-008](ADR-008-cross-task-derived-artifacts.md) | Cross-task derived artifacts are generated from landed task scenarios at Land time; the derivation is reconstructible, idempotent, and never a source-of-truth | proposed | Inv-5, Inv-6, Inv-8 (living spec, derived at Land, silent overwrite contract) |
| [ADR-009](ADR-009-fitness-functions-are-project-guardrails.md) | Architectural fitness functions are project guardrails, not framework guardrails | proposed | Inv-2 (five guardrails), Inv-8 (backward compat; vacuous-clear on zero declarations), ADR-007 reuse (verify.fitness floor promotion) |

## Principle → ADR mapping

The eight invariants (Inv-1..Inv-8) from the Compass architectural bootstrap
(`cross-task-architectural-integrity/architecture-notes.md`) are covered by
these six ADRs:

| Invariant | Principle statement | ADR |
|---|---|---|
| Inv-1 | Frame is mandatory; `task.yml.readings` is the only judgement field | ADR-001 |
| Inv-2 | Five guardrails (G1–G5), not more | ADR-002 |
| Inv-3 | Adaptive routing is untouched; no new routes or dimensions added | ADR-002 |
| Inv-4 | Flow (cross-task signals) advises; it never gates or mutates | ADR-003 |
| Inv-5 | One spec (`spec.feature.md`), many lenses; lenses annotate, never fork | ADR-004 |
| Inv-6 | Every mechanism output is a named file on disk (persistence over conversation) | ADR-005 |
| Inv-7 | The mechanism is deterministic; given the same inputs, the same outputs | ADR-001 |
| Inv-8 | Backward compat: every new mechanism no-ops on projects that haven't adopted it | ADR-006 |

## Authoring a new ADR

Use `compass adr new <slug>` or copy `templates/architecture/decisions/ADR-template.md`.
Required frontmatter fields: `id`, `title`, `status`, `date`, `supersedes`,
`superseded_by`. Required sections: Context, Decision, Alternatives considered,
Consequences, References.

A decision without alternatives is an assertion, not a record. Every ADR must
enumerate at least one alternative that was genuinely considered and rejected.
