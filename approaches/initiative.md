# Delivery approach - Initiative

> Big, cross-cutting, or greenfield. Full weight, every gate, agent swarm
> across worktrees.

## Assess composes toward initiative when

- size is `large` or `product`, **or**
- risk is `critical` (a floor forces this regardless of size),
  **or**
- familiarity is `greenfield` at scale or `brownfield-unmapped` and large, **or**
- a routing guardrail (floor) forces it (e.g. `labels: [auth, payments, migrations]`).

Typical issues: a new subsystem, a multi-module refactor, a migration, anything
touching auth/payments/personal-data at more than trivial size, a product
launch's worth of work.

## Per-phase weight

| Phase | Weight on initiative |
|---|---|
| Assess | Full, plus explicit `touches:` tagging - initiative is where domain floors most often fire. |
| Define | **Full BDD discovery.** Greenfield: scenario discovery from the brief. Brownfield: `blueprint-distillation` of current behaviour *then* the new scenarios. Scenarios are grouped by independence - this grouping seeds the distribution map. |
| Refine | **Full pass.** Self-QA, governance QA, and an explicit ambiguity ledger. Non-engineering roles review here. |
| Plan | **Full `technical-design.md` + `distribution-map.md`.** Architecture, every design decision recorded as an ADR-style note, governance check, and the mapping of scenario groups → independent work streams. |
| Breakdown | **Swarm.** `scripts/swarm.sh` creates one git worktree per stream; one `builder` agent per worktree; one `orchestrator` agent that writes no feature code. |
| Build | Full TDD inside each worktree, in parallel. The orchestrator watches for streams converging on shared surface and intervenes before they collide. |
| Verify | **All gates, all dimensions.** Per-stream verification, then combined verification after integration. |
| Ship | `scripts/integrate.sh`: orchestrated merge of all worktrees, full regression across the combined result, living-docs update, every owed follow-up resolved. |

## Gate set

All gates. Review dimensions: `correctness`, `governance`, `traceability`,
`regression`, `security` (full, not scaled), `clarity`, `claims`. Plus every
`immovable_gate` from the routing policy. Plus a mid-route checkpoint gate
per worktree.

## Swarm topology

Swarm: 4+ streams, capped by the routing-guardrail `caps` in
`governance/routing-policy.yml` (recorded in `delivery-approach.md` by the CLI). Note the
standing cap - **`critical` risk caps worktrees at 1** even on
initiative, because coordination risk on a critical change outweighs the
parallelism. An initiative can therefore be heavy *and* solo; that is
intentional, not a contradiction.

Roles: `orchestrator` coordinates and integrates; `builder` agents implement,
one per worktree; `verifier` and `reviewer` run at the gates; `product-lens`
and `marketing-lens` apply role checks at the requirements review and at
Ship time.

## De-scope ledger - what initiative collapses or skips

Nothing. initiative is the route with an empty de-scope ledger by definition -
it is what the other routes are measured against. The only reductions allowed
are ones a `cap` imposes (e.g. the worktree cap), and those are recorded as
*cap-driven*, not as de-scopes.

## initiative may NOT

- Run without a `distribution-map.md`, even if it ends up solo (capped). The
  map is the record of *what could have been parallel and why it wasn't*.
- Let a `builder` agent touch a sibling worktree. Cross-stream changes go
  through the orchestrator. This is what makes the isolation real.
- Skip the combined-regression step at ship time. Per-stream green does not imply
  integrated green - the whole point of the orchestrator's ship role is to
  prove the combination.
- Be down-routed mid-issue to "save time." If initiative turns out to be
  overkill, that is a re-assess (`/compass:assess --reassess`) with a written
  reason - not a quiet down-shift.
