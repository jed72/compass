---
id: ADR-004
title: Lens First Planner Second
status: accepted
date: 2026-05-23
supersedes: ''
superseded_by: ''
---

## Context

The architect-lens and the planner both produce design-decision content.
When a task introduces a new service interaction, both need to weigh in.
The question is: who runs first, and who reads whom?

Three orderings were considered: lens-first (lens writes notes, planner reads
them), planner-first (planner writes DDs, lens annotates), and parallel (both
run without reading each other, merged by a human).

## Decision

The architect-lens runs first; the planner reads and cites.

Order of operations:
1. Architect-lens runs at Specify (auto-triggered) or via
   `/compass:roundtable architect-lens`.  It writes `architecture-notes.md`.
2. Planner runs at Plan.  It reads `architecture-notes.md` and writes
   `plan.md §2` DDs that either cite an existing ADR, name a candidate ADR
   to author at Build, or explicitly justify divergence.
3. Planner never re-invokes the lens.  If `architecture-notes.md` is missing,
   the planner records a "no lens consultation applied" note in `plan.md` -
   not a silent skip.

## Alternatives considered

| Alternative | Why considered | Why rejected |
|---|---|---|
| Planner first, lens annotates | Planner already owns plan.md | Lens would need to edit a file it doesn't own; blurs responsibility |
| Parallel, human merges | No ordering dependency | Human merge step adds ceremony; ordering is cheap and makes the dependency explicit |
| Lens has authority over plan | Strong architectural enforcement | Planner remains the single owner of plan.md; lens is advisory, not authoritative |

## Consequences

**Positive:**
- Clear dependency direction: lens → planner (never planner → lens).
- Planner's DDs are always informed by architectural context.
- No recursive invocation risk.

**Negative:**
- Lens must run before Specify finalises, which requires early consultation.

**Neutral / follow-on:**
- If `architecture-notes.md` is absent (no architecture/ in the project), the
  planner records the absence explicitly.  This is a recordable absence, not
  a silent skip (Strategy S4 - persistence over conversation).

## References

- Clarifications Q3 (architect-lens vs planner split)
- Plan DD-5 (lens-first/planner-second design decision)
- architecture-notes.md §2 Inv-5 (one spec, many lenses)
