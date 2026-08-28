# Delivery approach - Quick fix

> The change is small, safe, and on mapped ground. Stay out of the way.
> Still tested before it lands.

## Assess composes toward quick fix when

- size is `atomic` or `small`, **and**
- risk is `trivial` or `contained`, **and**
- familiarity is `brownfield-mapped` (or trivially-readable greenfield), **and**
- no routing guardrail (floor) raises the route, **and**
- role is `engineer` (a non-engineering role in play almost always pulls the
  route up, because it adds artifacts and gates).

Typical issues: copy fixes, a bounded bug fix with an obvious cause, adding a
small variant of an existing pattern, a config change with a known shape.

## Per-phase weight

| Phase | Weight on quick fix |
|---|---|
| Assess | Full. Always runs, always writes `delivery-approach.md`. ~minutes. |
| Define | **One scenario.** A single Given/When/Then that names the new behaviour. That scenario is the spec. |
| Refine | **Collapsed** - permitted only because the one scenario is unambiguous. If it is not unambiguous, triage does not compose quick fix. |
| Plan | **Collapsed** to a one-line "edit which file(s)" note in `delivery-approach.md`. No `technical-design.md`. |
| Breakdown | **Skipped.** Solo, current branch, no worktree. |
| Build | Full TDD: write the failing test for the scenario, make it green, refactor. Test surface = the one scenario plus its obvious edges. |
| Verify | Light gate: run the new test + the existing suite, paste output. |
| Ship | Trivial: commit on the current branch, one-line devlog entry. |

## Gate set

One gate, at Verify. Review dimensions: `correctness`, `governance`,
`traceability`. (Per `router.md`; a routing guardrail may add more - e.g. a
`touches:` tag could staple on `security` - but never removes these three.)

## Multiagent orchestration

Solo. No worktree. Breakdown is a no-op.

## De-scope ledger - what quick fix collapses or skips, and why it is safe

| Phase | Action | Standing justification |
|---|---|---|
| Refine | collapsed | The spec is a single scenario triage has certified unambiguous. Nothing to clarify. |
| Plan | collapsed to a one-liner | No design decision and no new architecture - size `atomic`/`small` on mapped familiarity means the plan is "edit this file." |
| Breakdown | skipped | One subtask of work. Parallelism would be pure overhead. |

These justifications are copied into the issue's `delivery-approach.md` so the skip is
auditable per-issue, not just per-route.

## quick fix may NOT

- Skip the tested-before-ship guardrail. A quick fix adapts test *surface*,
  never test *existence*. The red-before-green TDD strategy applies on
  quick fix - only a spike suspends it. The `pre-tool` hook enforces
  that strategy and quick fix does not exempt itself from it.
- Skip the define stage. "No scenario" is never an quick fix state - the one scenario is
  the minimum, not zero.
- Be used when *any* dimension reads high. If risk is `cross-cutting`,
  or familiarity is `brownfield-unmapped`, or size is `standard`+, triage
  composes a heavier route. quick fix is for issues that are small on *every*
  axis.
- Be used to "just get the change in" past a route triage actually
  composed heavier. That is route laundering, and `delivery-approach.md` makes it visible.
