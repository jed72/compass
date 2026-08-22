# Delivery approach - Feature

> The default working shape. Full pipeline at moderate weight, solo or pair.

## Triage composes toward a feature approach when

- size is `standard` (several files, 1–3 days, one or two design
  decisions), **and**
- risk is `contained` or a low end of `cross-cutting`, **and**
- familiarity is either greenfield-bounded or brownfield (mapped or unmapped - if
  unmapped, a routing guardrail adds `blueprint-distillation` to define),
  **and**
- no floor forces initiative.

Typical issues: a new feature of normal size, a refactor of one module, an
integration with one external service, a meaningful bug fix with design
choices in it.

## Per-phase weight

| Stage | Weight on a feature approach |
|---|---|
| Triage | Full. `delivery-approach.md` written. |
| Define | A small **feature set** of scenarios - happy path, the realistic edges, the failure modes that matter. Brownfield-unmapped: distil current behaviour into scenarios first. |
| Refine | **Light-to-full pass.** Resolve ambiguities, QA the spec against itself and against governance. Writes `requirements-review.md`. |
| Plan | **Real `design.md`.** Technical approach, the one or two design decisions stated, governance check run. If the work splits into 2–3 independent units, a short distribution map. |
| Breakdown | **Solo or pair.** Solo on the current branch by default; pair (2–3 worktrees) if the distribution map shows clean independence and `.compass/config.yml` thresholds are met. |
| Build | Full TDD per scenario. Test surface scaled to `contained`/`cross-cutting` risk. |
| Verify | **Two gates** - one mid-Build checkpoint, one at the end. |
| Ship | Integrate (merge pair worktrees if used), run regression, update living docs, one devlog entry. |

## Gate set

Two gates. Review dimensions: `correctness`, `governance`, `traceability`,
`regression`, `clarity`, and `security` *scaled to risk*. `claims` is
added if the product-marketer role is in play.

## Swarm topology

Solo by default. Pair (2–3 worktrees, one `builder` agent each, no dedicated
orchestrator - the lead builder integrates) when the distribution map shows
genuinely independent units and the size justifies the setup cost.

## De-scope ledger - what a feature approach collapses or skips, and why it is safe

| Item | Action | Standing justification |
|---|---|---|
| Dedicated orchestrator agent | skipped | At ≤3 streams the integration is small enough for the lead builder; a separate orchestrator is overhead. |
| Full distribution map | reduced to a short list | Independence among 2–3 units is verifiable by reading; the full mapping ceremony is for swarm-scale work. |

If the requirements review finds the spec is bigger or more ambiguous
than the feature approach assumed,
re-assess - do not push a feature approach through an initiative-shaped problem.

## Standard may NOT

- Skip the requirements review entirely. Standard's spec is a feature set, not a single
  certified-unambiguous scenario - there is always something to QA. The requirements review
  may be *light*, never *absent*.
- Run a swarm. Four or more streams is initiative territory; it needs the
  orchestrator and the full distribution map. If the work wants a swarm, the
  triage mis-composed - re-assess to initiative.
- Drop the regression dimension. Standard touches enough surface that
  "nothing previously passing now fails" must be checked.
