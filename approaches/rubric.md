# Assess - the sizing rubric

Assess is the component that runs at the start of every issue. It reads four assessment
dimensions, applies `governance/routing-policy.md`, and writes `delivery-approach.md`. This
file is its rubric. The `adaptive-routing` skill is the procedural companion;
this is the reference.

Assess does not pick a route from a list. It *scores four dimensions*,
*composes* a candidate route (biased by the routing strategies), *constrains*
it (bounded by the routing guardrails), and *explains* the result. The five
reference shapes in this directory are common shapes the composition lands
near - not a menu.

---

## Step 1 - Score the four dimensions

For each dimension, triage assigns a value and writes a one-line
justification. If it cannot justify a value, it asks the human rather than
guessing - an unjustified reading is worse than a question.

### risk - *if this goes wrong, how bad and how wide?*

| Value | Test |
|---|---|
| `trivial` | Wrong outcome is cosmetic or instantly obvious and instantly reversible. No data, no money, no auth, no other team. |
| `contained` | Failure is annoying but bounded to one feature/surface, recoverable without incident, no data loss. |
| `cross-cutting` | Failure spreads across features or services, or degrades something many users touch. Recovery needs coordination. |
| `critical` | Failure can lose data, lose money, breach auth/privacy, or cannot be cleanly rolled back. |

risk is about *consequence*, never *effort*. A one-character change can
be `critical`.

### Familiarity - *new code or existing code, and how well mapped?*

| Value | Test |
|---|---|
| `greenfield` | Net-new code with no existing behaviour to preserve. |
| `brownfield-mapped` | Existing code, and its current behaviour is already captured in scenarios (or trivially readable). |
| `brownfield-unmapped` | Existing code whose behaviour is *not* written down. A routing guardrail forces `blueprint-distillation` here - you cannot safely change what you have not first described. |

### Size - *how much work is this, honestly?*

| Value | Test |
|---|---|
| `atomic` | One file, one obvious change, < ~30 min, no design decision. |
| `small` | 1–3 files, a known solution pattern, no new architecture. |
| `standard` | Several files, 1–3 days, one or two design decisions. |
| `large` | Multi-module, 1–2 weeks, real architecture, plausibly parallelisable. |
| `product` | A new system or subsystem, 2+ weeks, many independent work streams. |

Size is the only dimension a person reliably over- or under-estimates.
When unsure, triage estimates *up* - it is cheaper to collapse a phase
that turned out easy than to discover mid-Build that the route was too light.

### Intent & role - *who is invoking, and what outcome are they after?*

| Value | Entry point | What it changes |
|---|---|---|
| `engineer` | `/compass:assess` | Standard pipeline ownership. |
| `product-owner` | `/compass:intent` | Adds `intent.md` upstream of the spec; inserts the intent-fidelity gate before Plan. |
| `product-marketer` | `/compass:position` | Adds `positioning.md` / `launch-readiness.md`; blocks shipping on the claims gate. |
| `designer` | `/compass:design` | Adds `ui-contract.md`; UI contracts enter the define stage as scenarios. |
| `qa` | joins at `/compass:verify` | Owns the Verify gate; can send an issue back to define if scenarios are uncoverable. |

Intent is also *the actual outcome wanted*, not just the literal request. "Add
a CSV export" invoked by a product owner whose brief says "let finance
self-serve" may need more than a button. Assess reads the brief if one
exists.

One intent value is not a role: **exploration** - "I cannot frame this well
enough to deliver it yet." Exploration intent composes toward the **Spike**
route (see `approaches/spike.md`), the way live-defect urgency composes toward
Hotfix. Assess still scores all four dimensions; the intent is what selects
the shape.

---

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

## Step 4 - Write `delivery-approach.md` and confirm

Assess writes `.compass/work/<task-slug>/delivery-approach.md` from
`templates/delivery-approach.md`. It contains:

- the four dimension assessment, each with its one-line justification;
- the composed candidate route;
- every routing guardrail that fired and what it changed;
- the final route: per-phase weight, the gate set, the swarm topology;
- **the de-scope ledger** - every phase or check that is collapsed or skipped,
  each with an explicit "safe to skip because…" line. A phase with no
  justification cannot be skipped; if triage cannot justify a skip, the
  phase runs.

Routing is **advisory until confirmed**. The human can override any reading or
the final route - overrides are recorded in `delivery-approach.md` too, with who and why.
What cannot be overridden: an `immovable_gate`, or a `floor` (a routing
guardrail is governance speaking; changing it means amending
`governance/routing-policy.md`, not overriding a route).

---

## Re-framing mid-issue

If Build reveals the familiarity was misread - the "small" change is unspooling
into a multi-module refactor - the correct move is to **stop and re-assess**,
not to push on with a route you no longer believe. `/compass:assess --reassess`
re-scores the dimensions, writes a new `delivery-approach.md` revision, and records what
changed and why. A re-assess is a normal event, not a failure. A route quietly
outgrown is the failure.
