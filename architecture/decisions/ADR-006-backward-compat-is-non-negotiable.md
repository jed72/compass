---
id: ADR-006
title: Backward compat is non-negotiable; every new mechanism no-ops cleanly on projects that have not adopted it
status: accepted
date: 2026-05-24
supersedes: ''
superseded_by: ''
---

## Context

Compass is used by projects at different stages of adoption. Some projects have
`architecture/`, `governance/signals.yml`, and the full tool suite. Others have
only the core framework files (`governance/routing-policy.yml`,
`governance/guardrails.yml`, `.compass/`). Some are on older task-spine schemas.

When a new Compass capability is released (e.g. `frame_load_architecture`, the
architect-lens, `compass rework-scan`), it runs against all projects that
upgrade Compass — including the ones that have not yet set up the new
capability's prerequisite files.

The question is: when a new mechanism encounters a project that has not
adopted its prerequisites, should it fail loudly, fail silently, or no-op
cleanly?

## Decision

Every new Compass mechanism no-ops cleanly on projects that have not adopted
its prerequisites.

Specifically:

- `frame_load_architecture` on a project without `architecture/` → returns
  empty `artifacts: []` and `adrs: []`, writes `architecture-loaded.yml` with
  the empty state, exits 0.
- The architect-lens on a project without `architecture/` → writes
  `architecture-notes.md` with a `WARNING:` prefix and heuristic analysis,
  proceeds, exits 0.
- `hooks/stop.sh` on a project without `governance/signals.yml` → skips signal
  scanning, proceeds, exits 0.
- `compass rework-scan` on a task with disjoint `changed_files` → produces an
  empty report, exits 0.
- `compass check` with a DoD section that has no typed evidence → passes the
  check (the check is for the presence of typed evidence when the DoD exists,
  not for the DoD's existence).
- Any `task.yml` file without a new optional field (e.g. `target_task` on
  backfills) → treated as if the field has its default/absent value.

Mandatory adoption of a new capability is a breaking change. Breaking changes
require a major version bump and an explicit migration guide.

## Alternatives considered

| Alternative | Why considered | Why rejected |
|---|---|---|
| Fail loudly when prerequisites are absent, forcing adoption | Ensures every project that upgrades Compass also sets up the full capability; prevents "partial adoption" drift | A team upgrading Compass for an unrelated fix (e.g. a bug fix in `compass check`) should not be forced to also set up `architecture/` before their tasks can Frame. Mandatory adoption converts an upgrade into a migration, blocking adoption entirely for teams that can't do both at once. |
| Produce a deprecation warning but still exit 0 | Communicates the gap without blocking | A warning that appears on every task for months while a team works on unrelated features becomes noise, is dismissed, and eventually turns off the signal that was meant to prompt adoption. No-op clean is more honest — the capability is simply absent, not degraded. |

## Consequences

**Positive:**
- Compass upgrades are safe to apply incrementally. A team can upgrade to a
  new Compass version on one task, verify nothing breaks, then adopt the new
  capability at their own pace.
- The no-op contract is testable: each mechanism's "absent prerequisites" path
  has explicit tests (TRC-A2, TRC-A5b in the prior task's suite; TRC-E2 in
  this task's suite).
- The contract is bilateral: framework maintainers can add capabilities knowing
  they will not break existing adopters; adopters can trust that upgrading is
  safe.

**Negative:**
- No-op clean means partial adoption is invisible. A project that has upgraded
  Compass but never created `architecture/` will never be told it is missing
  out. The framework cannot distinguish "made a choice not to adopt" from
  "forgot to set up". Teams that want enforcement must add their own
  project-level checks.
- The no-op contract creates an implicit obligation: every future mechanism
  must be designed with an absent-prerequisites path from the start. This is
  extra design work that is easy to skip under deadline pressure.

**Neutral / follow-on:**
- The `architecture/` tree itself follows this rule: Compass's own `architecture/`
  was absent until this task. Every Compass-framework task between the first
  task (cross-task-architectural-integrity) and this task ran with
  `frame_load_architecture` returning an empty record. None of those tasks
  failed.
- ADR supersession follows the same backward-compat principle: a superseded
  ADR's `superseded_by` field is set, but the file is not deleted. Projects
  that indexed the old ADR can still find the record and follow the chain.

## References

- Prior task's `architecture-notes.md` §2 Inv-8 (backward compat for projects without new surfaces)
- Prior task's `architecture-notes.md` §3 B-Risk 1–6 (all of which would violate Inv-8 if implemented)
- `tests/test_frame_loads_architecture.py::test_noop_when_absent` (TRC-A2 test)
- `docs/safety-contract.md` (the seven things Compass 1.0 guarantees)
