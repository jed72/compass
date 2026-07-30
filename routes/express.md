# Route - Express

> The change is small, safe, and on mapped ground. Stay out of the way.
> Still tested before it lands.

## The Needle composes toward Express when

- magnitude is `atomic` or `small`, **and**
- blast radius is `trivial` or `contained`, **and**
- terrain is `brownfield-mapped` (or trivially-readable greenfield), **and**
- no routing guardrail (floor) raises the route, **and**
- role is `engineer` (a non-engineering role in play almost always pulls the
  route up, because it adds artifacts and gates).

Typical tasks: copy fixes, a bounded bug fix with an obvious cause, adding a
small variant of an existing pattern, a config change with a known shape.

## Per-phase weight

| Phase | Weight on Express |
|---|---|
| Frame | Full. Always runs, always writes `route.md`. ~minutes. |
| Specify | **One scenario.** A single Given/When/Then that names the new behaviour. That scenario is the spec. |
| Clarify | **Collapsed** - permitted only because the one scenario is unambiguous. If it is not unambiguous, the Needle does not compose Express. |
| Plan | **Collapsed** to a one-line "edit which file(s)" note in `route.md`. No `plan.md`. |
| Distribute | **Skipped.** Solo, current branch, no worktree. |
| Build | Full TDD: write the failing test for the scenario, make it green, refactor. Test surface = the one scenario plus its obvious edges. |
| Verify | Light gate: run the new test + the existing suite, paste output. |
| Land | Trivial: commit on the current branch, one-line devlog entry. |

## Gate set

One gate, at Verify. Review dimensions: `correctness`, `governance`,
`traceability`. (Per `router.md`; a routing guardrail may add more - e.g. a
`touches:` tag could staple on `security` - but never removes these three.)

## Swarm topology

Solo. No worktree. Distribute is a no-op.

## De-scope ledger - what Express collapses or skips, and why it is safe

| Phase | Action | Standing justification |
|---|---|---|
| Clarify | collapsed | The spec is a single scenario the Needle has certified unambiguous. Nothing to clarify. |
| Plan | collapsed to a one-liner | No design decision and no new architecture - magnitude `atomic`/`small` on mapped terrain means the plan is "edit this file." |
| Distribute | skipped | One stream of work. Parallelism would be pure overhead. |

These justifications are copied into the task's `route.md` so the skip is
auditable per-task, not just per-route.

## Express may NOT

- Skip guardrail G1 (tested before it lands). Express adapts test *surface*,
  never test *existence*. The red-before-green TDD strategy applies on
  Express - only the Spike route suspends it. The `pre-tool` hook enforces
  that strategy and Express does not exempt itself from it.
- Skip Specify. "No scenario" is never an Express state - the one scenario is
  the minimum, not zero.
- Be used when *any* dimension reads high. If blast radius is `cross-cutting`,
  or terrain is `brownfield-unmapped`, or magnitude is `standard`+, the Needle
  composes a heavier route. Express is for tasks that are small on *every*
  axis.
- Be used to "just get the change in" past a route the Needle actually
  composed heavier. That is route laundering, and `route.md` makes it visible.
