# Routes

A **route** is the computed shape of the pipeline for one issue: how heavy each
of the eight phases is, which gates apply, and whether work runs solo or as a
swarm. Approaches are *composed* by triage from the four context dimensions
(see `router.md`) - they are not picked from this list.

The five files here are **reference shapes**: the common shapes that
composition lands near. Triage names the nearest reference shape in
`delivery-approach.md` so everyone shares vocabulary, then records any per-phase deviation
from it. "Standard, but Verify adds the security dimension" is a normal,
expected output.

| Route | One-line character | Read |
|---|---|---|
| **quick fix** | The change is small, safe, and on mapped ground - stay out of the way, but still tested before it lands. | `express.md` |
| **Standard** | The default working shape - full pipeline, solo or pair, two gates. | `standard.md` |
| **initiative** | Big, cross-cutting, or greenfield - full weight, governance check, agent swarm across worktrees. | `expedition.md` |
| **Hotfix** | Something is broken in production now - reproduce-first, expedited Build, mandatory follow-up. | `hotfix.md` |
| **Spike** | You do not understand the problem well enough to frame it - explore freely, then graduate or discard. Nothing ships from here. | `spike.md` |

Every route, no matter how light or how exploratory, obeys the **default
guardrails** (the five defaults in `governance/guardrails.md`). What a route adapts is
*ceremony* and *strategy* - Spike, for instance, suspends the red-before-green
TDD strategy, but it cannot suspend the tested-before-ship guardrail, because nothing lands from a
Spike without graduating to a real route first. If a route file ever seems to
permit crossing a guardrail, that is a bug in the route file -
`docs/methodology.md` and `governance/guardrails.md` are the authority.

## How to read a route file

Each file states, in order: when triage composes toward it; the per-phase
weight; the gate set; the swarm topology; the de-scope ledger (what it
collapses or skips, and the standing justification for each); and what it is
*not* allowed to do.
