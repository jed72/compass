# The Needle — Routing Logic

The Needle is the component that runs during **Frame**. It reads four context
dimensions, applies `governance/routing-policy.md`, and writes `route.md`. This
file is its rubric. The `adaptive-routing` skill is the procedural companion;
this is the reference.

The Needle does not pick a route from a list. It *scores four dimensions*,
*composes* a candidate route (biased by the routing strategies), *constrains*
it (bounded by the routing guardrails), and *explains* the result. The five
reference routes in this directory are common shapes the composition lands
near — not a menu.

---

## Step 1 — Score the four dimensions

For each dimension, the Needle assigns a value and writes a one-line
justification. If it cannot justify a value, it asks the human rather than
guessing — an unjustified reading is worse than a question.

### Blast radius — *if this goes wrong, how bad and how wide?*

| Value | Test |
|---|---|
| `trivial` | Wrong outcome is cosmetic or instantly obvious and instantly reversible. No data, no money, no auth, no other team. |
| `contained` | Failure is annoying but bounded to one feature/surface, recoverable without incident, no data loss. |
| `cross-cutting` | Failure spreads across features or services, or degrades something many users touch. Recovery needs coordination. |
| `critical` | Failure can lose data, lose money, breach auth/privacy, or cannot be cleanly rolled back. |

Blast radius is about *consequence*, never *effort*. A one-character change can
be `critical`.

### Terrain — *new code or existing code, and how well mapped?*

| Value | Test |
|---|---|
| `greenfield` | Net-new code with no existing behaviour to preserve. |
| `brownfield-mapped` | Existing code, and its current behaviour is already captured in scenarios (or trivially readable). |
| `brownfield-unmapped` | Existing code whose behaviour is *not* written down. A routing guardrail forces `blueprint-distillation` here — you cannot safely change what you have not first described. |

### Magnitude — *how much work is this, honestly?*

| Value | Test |
|---|---|
| `atomic` | One file, one obvious change, < ~30 min, no design decision. |
| `small` | 1–3 files, a known solution pattern, no new architecture. |
| `standard` | Several files, 1–3 days, one or two design decisions. |
| `large` | Multi-module, 1–2 weeks, real architecture, plausibly parallelisable. |
| `product` | A new system or subsystem, 2+ weeks, many independent work streams. |

Magnitude is the only dimension a person reliably over- or under-estimates.
When unsure, the Needle estimates *up* — it is cheaper to collapse a phase
that turned out easy than to discover mid-Build that the route was too light.

### Intent & role — *who is invoking, and what outcome are they after?*

| Value | Entry point | What it changes |
|---|---|---|
| `engineer` | `/compass:frame` | Standard pipeline ownership. |
| `product-owner` | `/compass:intent` | Adds `brief.md` upstream of the spec; inserts the intent-fidelity gate before Plan. |
| `product-marketer` | `/compass:position` | Adds `positioning.md` / `launch-readiness.md`; blocks Land on the claims gate. |
| `designer` | `/compass:design` | Adds `ui-contract.md`; UI contracts enter Specify as scenarios. |
| `qa` | joins at `/compass:verify` | Owns the Verify gate; can send a task back to Specify if scenarios are uncoverable. |

Intent is also *the actual outcome wanted*, not just the literal request. "Add
a CSV export" invoked by a product owner whose brief says "let finance
self-serve" may need more than a button. The Needle reads the brief if one
exists.

One intent value is not a role: **exploration** — "I cannot frame this well
enough to deliver it yet." Exploration intent composes toward the **Spike**
route (see `routes/spike.md`), the way live-defect urgency composes toward
Hotfix. The Needle still scores all four dimensions; the intent is what selects
the shape.

---

## Step 2 — Compose the candidate route

The candidate route is a composition, not a lookup. The Needle assembles it
from per-dimension contributions:

| The route is heavier when… | The route is lighter when… |
|---|---|
| blast radius is `cross-cutting`/`critical` | blast radius is `trivial` |
| terrain is `greenfield` or `brownfield-unmapped` | terrain is `brownfield-mapped` |
| magnitude is `large`/`product` | magnitude is `atomic`/`small` |
| a non-engineering role is involved (more artifacts, more gates) | only `engineer` is involved |

Concretely, the Needle decides, per phase:

- **Specify** — how many scenarios, discovery vs. distillation, how deep.
- **Clarify** — full pass, light pass, or collapsed (only collapsible when the
  spec is a single unambiguous scenario *and* no routing guardrail requires it).
- **Plan** — "edit this file" one-liner, a real technical plan, or a plan plus
  a distribution map.
- **Distribute** — skipped (solo), pair, or swarm. Stream count comes from the
  distribution map; topology thresholds come from `.compass/config.yml`.
- **Build** — test surface target, scaled to blast radius.
- **Verify** — which review dimensions apply (see below), how many gates.
- **Land** — trivial integration vs. coordinated multi-worktree merge; which
  backfills are owed.

Most compositions land near one of the five reference routes
(`express`, `standard`, `expedition`, `hotfix`, `spike`). The Needle names the
nearest reference route in `route.md` for shared vocabulary, then lists any
phase-level deviations from it. A route that is "Standard, but Verify also runs
the security dimension because blast radius is cross-cutting" is a perfectly
normal output — that is the framework working as designed.

### Review dimensions by route (the default; routing guardrails can add but not remove)

| Dimension | Express | Standard | Expedition | Hotfix | Spike |
|---|---|---|---|---|---|
| correctness | ✓ | ✓ | ✓ | ✓ | — |
| governance | ✓ | ✓ | ✓ | ✓ | — |
| traceability | ✓ | ✓ | ✓ | ✓ | — |
| regression | — | ✓ | ✓ | ✓ | — |
| security | — | scaled | ✓ | ✓ | — |
| clarity | — | ✓ | ✓ | — | — |
| claims | if role | if role | ✓ | if role | — |

"scaled" = applied in proportion to blast radius. "if role" = applied when the
product-marketer role is in play. `correctness`, `governance`, `traceability`
are on for every delivery route because they *are* the default guardrails in
review form. **Spike** runs none of these — it ships nothing, so it has only
its own Conclude gate ("was the question answered?"); see `routes/spike.md`.

---

## Step 3 — Constrain with the routing guardrails

The candidate route — already biased by the routing strategies in Step 2 — is
now bounded by the **routing guardrails** in `governance/routing-policy.md`:

1. **floors** raise the route or force phases/skills back to full weight.
2. **caps** limit scale-up (e.g. the worktree ceiling on critical blast radius).
3. **immovable_gates** are stapled on regardless of route.
4. **blocking role_rules** add required artifacts and phase blocks.

Every routing guardrail that fires is recorded. The Needle never applies a
constraint silently — if Express became Expedition, `route.md` says which floor
did it and quotes the floor's rationale.

---

## Step 4 — Write `route.md` and confirm

The Needle writes `.compass/work/<task-slug>/route.md` from
`templates/route.md`. It contains:

- the four dimension readings, each with its one-line justification;
- the composed candidate route;
- every routing guardrail that fired and what it changed;
- the final route: per-phase weight, the gate set, the swarm topology;
- **the de-scope ledger** — every phase or check that is collapsed or skipped,
  each with an explicit "safe to skip because…" line. A phase with no
  justification cannot be skipped; if the Needle cannot justify a skip, the
  phase runs.

Routing is **advisory until confirmed**. The human can override any reading or
the final route — overrides are recorded in `route.md` too, with who and why.
What cannot be overridden: an `immovable_gate`, or a `floor` (a routing
guardrail is governance speaking; changing it means amending
`governance/routing-policy.md`, not overriding a route).

---

## Re-framing mid-task

If Build reveals the terrain was misread — the "small" change is unspooling
into a multi-module refactor — the correct move is to **stop and re-frame**,
not to push on with a route you no longer believe. `/compass:frame --reframe`
re-scores the dimensions, writes a new `route.md` revision, and records what
changed and why. A re-frame is a normal event, not a failure. A route quietly
outgrown is the failure.
