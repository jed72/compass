---
id: ADR-003
title: Flow advises but never gates
status: accepted
date: 2026-05-24
supersedes: ''
superseded_by: ''
---

## Context

Compass has two layers of cross-task visibility: per-task gates (checked by
`compass check` at Verify and Land, which can block a task) and cross-task
signals (surfaced by `/compass:flow`, `compass rework-scan`, and
`compass calibration`, which aggregate patterns across tasks).

There was a design choice to make about the cross-task layer: should a
detected rework signal or calibration anomaly block the current task, or
merely inform?

The blocking model has intuitive appeal: if rework is detected early, forcing
a pause could save downstream cost. A team with a high re-frame rate might
benefit from a mandatory `compass calibration` checkpoint before new tasks
start.

## Decision

Flow (and all cross-task signal mechanisms) advises but never gates.

`/compass:flow`, `compass rework-scan`, and `compass calibration` are
read-only over `.compass/work/*/task.yml`. They read disk and report; they do
not write task state, do not set gates to blocked, do not trigger re-frames.

A rework signal from `compass rework-scan` writes a report to
`.compass/flow/rework-<date>.md` and exits 0. Detection is not a failure
condition; it is information.

A calibration anomaly from `compass calibration` writes a calibration report.
It does not annotate any task spine as "miscalibrated". The human decides
whether to re-frame.

The per-task gates (`compass check`) are the only mechanism that can block a
task from landing. Cross-task signals inform the next Frame; they do not
retroactively gate a completed Verify.

## Alternatives considered

| Alternative | Why considered | Why rejected |
|---|---|---|
| `compass rework-scan` exits non-zero when rework is detected, blocking CI | Makes rework visible as a hard failure, not a soft signal; integrates with PR checks | Exit non-zero on detection turns an advisory signal into a gate. Rework is often legitimate scope evolution, not a process failure. A blocking gate would create pressure to suppress the detection rather than respond to it. |
| `/compass:flow` writes a `flow-blocked: true` flag into task.yml when a blocker is found | Gives the cross-task layer a write path for urgency | Violates the read-only contract. If Flow can write, it becomes a parallel authority on task state alongside Frame. Two authorities on task state is the root cause of the fragmentation Compass was designed to eliminate. |

## Consequences

**Positive:**
- No cross-task mechanism can block a task. A team under deadline pressure can
  acknowledge a rework signal and proceed; the signal is recorded but not
  coercive.
- Flow's read-only contract means it can be added to any project without risk
  of side effects. It cannot corrupt task spines.
- The calibration feedback loop (Frame readings → re-frames → calibration →
  better readings next time) works because calibration is advisory. If it were
  a gate, teams would game the re-frame entries to avoid triggering it.

**Negative:**
- Advisory signals can be ignored. A team that ignores rework signals
  accumulates technical debt without any hard reminder. The framework cannot
  prevent this — it can only make the cost visible.

**Neutral / follow-on:**
- This decision does not prevent an adopter from wiring `compass rework-scan`
  into a CI check that fails the build. That is the adopter's choice on their
  infrastructure; it does not change the framework's default behaviour.
- Future cross-task capabilities (e.g. dependency graphs, impact analysis)
  should follow the same advisory-only pattern.

## References

- Prior task's `architecture-notes.md` §2 Inv-4 (Flow advises, never gates)
- Prior task's `architecture-notes.md` §3 B-Risk 3 (rework-scan blocking on detection)
- Prior task's `architecture-notes.md` §3 B-Risk 5 (calibration mutating task.yml)
- `docs/methodology.md` §"Beyond the per-task pipeline"
- `CLAUDE.md` §"Beyond the per-task pipeline"
