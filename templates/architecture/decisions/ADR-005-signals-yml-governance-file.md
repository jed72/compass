---
id: ADR-005
title: Signals Yml Governance File
status: accepted
date: 2026-05-23
supersedes: ''
superseded_by: ''
---

## Context

Three framework mechanisms needed configurable patterns:
- The stop-hook's scope-bloat phrase detector (reframe nudge).
- The rework scanner's time window and public-surface patterns.
- Eventually, the architect-lens's trigger tags.

The patterns needed to be project-overridable (different projects have
different migration path conventions, public surface patterns, etc.) and
loaded at run time so the CLI is not hard-coded with opinions about any one
project's conventions.

Two locations were considered: folding the patterns into `governance/guardrails.yml`
alongside the hard checks, and a new sibling file `governance/signals.yml`.

## Decision

A new file `governance/signals.yml` ships alongside `guardrails.yml` and
`routing-policy.yml`.  It holds all *advisory signal* configurations.

Default content:
```yaml
version: 1.0.0
scope_bloat_phrases:
  - "more files than Plan estimated"
  - "narrow scope and spawn sibling"
  - ...
rework_scan:
  window_days: 14
  public_surface_patterns:
    - "/api/v[0-9]+/"
    - "pb\\."
  migration_paths:
    - "migrations/*.sql"
    - "**/migrations/*.sql"
```

Projects override by editing their own `governance/signals.yml`.

## Alternatives considered

| Alternative | Why considered | Why rejected |
|---|---|---|
| Fold into `guardrails.yml` | One fewer file | Guardrails are hard and blocking; signals are soft and advisory - mixing dilutes both |
| Put in `.compass/config.yml` | Config is already project-scoped | Config holds project knobs (test command, worktree root); governance content belongs in `governance/` |
| Hard-code in the CLI | Simplest implementation | Non-overridable; defeats the "adaptive" principle for project-specific conventions |

## Consequences

**Positive:**
- Clean three-file governance model: routing-policy.yml (routes), guardrails.yml (hard checks), signals.yml (advisory patterns).
- Projects can tune scope-bloat phrases and rework windows without forking the framework.
- `compass policy lint` validates signals.yml structure.

**Negative:**
- A third file for new adopters to become aware of.

**Neutral / follow-on:**
- Lens-trigger tags (when the architect-lens becomes more sophisticated) will be added as a new key in `signals.yml`, not a new file.

## References

- Clarifications Q9 (where patterns live)
- Plan DD-1 (signals.yml as a separate file)
- architecture-notes.md §2 Inv-2 (five guardrails, not six)
