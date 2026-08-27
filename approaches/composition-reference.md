# How an approach is composed and constrained

Split out of `rubric.md`, and deliberately **not** part of the assess read.

This describes what `compass approach evaluate` does: how a candidate shape
is composed from the four dimensions, and how floors, caps, immovable gates
and role rules then constrain it. A session does not do any of it by hand -
that is the determinism boundary. The CLI computes; you read the dimensions
and run the command.

Read this when tuning `governance/routing-policy.yml`, or when you need to
understand why the CLI returned the approach it did. `compass approach
evaluate --verbose` prints which rules fired for any assessment, and that is
usually the faster answer.

## Step 2 - Compose the candidate route

The candidate route is a composition, not a lookup. Assess assembles it
from per-dimension contributions:

| The route is heavier when… | The route is lighter when… |
|---|---|
| risk is `cross-cutting`/`critical` | risk is `trivial` |
| familiarity is `greenfield` or `brownfield-unmapped` | familiarity is `brownfield-mapped` |
| size is `large`/`product` | size is `atomic`/`small` |
| a non-engineering role is involved (more artifacts, more gates) | only `engineer` is involved |

Concretely, triage decides, per phase:

- **Define** - how many scenarios, discovery vs. distillation, how deep.
- **Refine** - full pass, light pass, or collapsed (only collapsible when the
  spec is a single unambiguous scenario *and* no routing guardrail requires it).
- **Plan** - "edit this file" one-liner, a real technical plan, or a plan plus
  a distribution map.
- **Breakdown** - skipped (solo), pair, or swarm. Stream count comes from the
  distribution map; topology thresholds come from `.compass/config.yml`.
- **Build** - test surface target, scaled to risk.
- **Verify** - which review dimensions apply (see below), how many gates.
- **Ship** - trivial integration vs. coordinated multi-worktree merge; which
  follow-ups are owed.

Most compositions land near one of the five reference shapes
(`express`, `standard`, `expedition`, `hotfix`, `spike`). Assess names the
nearest reference shape in `delivery-approach.md` for shared vocabulary, then lists any
phase-level deviations from it. A route that is "Standard, but Verify also runs
the security dimension because risk is cross-cutting" is a perfectly
normal output - that is the framework working as designed.

### Review dimensions by route (the default; routing guardrails can add but not remove)

| Dimension | quick fix | Standard | initiative | Hotfix | Spike |
|---|---|---|---|---|---|
| correctness | ✓ | ✓ | ✓ | ✓ | - |
| governance | ✓ | ✓ | ✓ | ✓ | - |
| traceability | ✓ | ✓ | ✓ | ✓ | - |
| regression | - | ✓ | ✓ | ✓ | - |
| security | - | scaled | ✓ | ✓ | - |
| clarity | - | ✓ | ✓ | - | - |
| claims | if role | if role | ✓ | if role | - |

"scaled" = applied in proportion to risk. "if role" = applied when the
product-marketer role is in play. `correctness`, `governance`, `traceability`
are on for every delivery approach because they *are* the default guardrails in
review form. **Spike** runs none of these - it ships nothing, so it has only
its own Conclude gate ("was the question answered?"); see `approaches/spike.md`.

---

## Step 3 - Constrain with the routing guardrails

The candidate route - already biased by the routing strategies in Step 2 - is
now bounded by the **routing guardrails** in `governance/routing-policy.md`:

1. **floors** raise the route or force phases/skills back to full weight.
2. **caps** limit scale-up (e.g. the worktree ceiling on critical risk).
3. **immovable_gates** are stapled on regardless of route.
4. **blocking role_rules** add required artifacts and phase blocks.

Every routing guardrail that fires is recorded. Assess never applies a
constraint silently - if quick fix became initiative, `delivery-approach.md` says which floor
did it and quotes the floor's rationale.

---

