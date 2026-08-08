# Governance - Strategies and Guardrails

Compass is governed by two kinds of thing, and keeping them separate is the
point of this directory.

- **Guardrails** - few, hard, checkable, blocking. The things that must never
  happen. A guardrail is cleared only with evidence, and a failed guardrail
  stops the work. See `guardrails.md`.
- **Strategies** - many, soft, directional, assessed. How the team tends to
  work and what it prefers. A strategy *biases* a decision; it does not block
  it. See `strategies.md`.

A third file, `routing-policy.md`, applies the same split to triage
itself: routing guardrails *bound* what triage may do, routing strategies
*bias* what it does by default.

This replaces the older single "constitution." The constitution model jammed
soft preferences, hard limits, and routing rules into one document under one
connotation - "supremacy" - and that conflation caused real problems: it made
governance a heavy all-or-nothing artifact you had to author before you could
start, and it let advisory judgements get dressed up as hard gates. Strategies
and guardrails un-conflate those.

---

## Why the split matters

**It is a gradient, not a threshold.** A constitution is all-or-nothing - you
have one or you don't, and a half-written one feels broken. Strategies and
guardrails have a valid *light* state: the shipped default guardrails, the
shipped default method strategies, and zero project-specific additions. That
is a complete, usable governance state, not a skipped step. A team starts
there and *accretes* strategies as it forms opinions, and adds a guardrail
only when it hits something that must never recur. This is what makes
`/compass:init` optional and "frame-and-go" honest - see `docs/quickstart.md`.

**It keeps honest things honest.** Guardrails are *checkable* - a test ran, a
scan passed, a human approved. Strategies are *assessed* - is this clear, does
it fit our voice, is this the simplest thing that works. Naming them
differently stops a judgement call being presented as a hard gate. "Evidence
over assertion" (the evidence-not-assertion guardrail) applies cleanly to guardrails; strategies are
honestly the reviewer's judgement, and are labelled as such.

**It right-sizes rigour.** The form of a practice can be a strategy while its
outcome is a guardrail. Compass's headline example: *being tested before it
lands* is the tested-before-ship guardrail - hard, checkable, universal. *Red-green-refactor* is a
default strategy - the strong, shipped-on way to get there, but a spike
can suspend it. A one-character typo fix still has to be tested before it
lands; it does not have to perform the red-green ritual. That distinction is
how Compass avoids using a sledgehammer on a nut without giving up the floor.

---

## The conflict rule

When two pieces of governance disagree:

1. **A guardrail always beats a strategy.** No strategy, however sensible,
   licenses crossing a guardrail.
2. **Guardrail vs guardrail** should not happen - if it does, the guardrail
   set has a bug; fix the set, do not improvise around it.
3. **Strategy vs strategy** is resolved by context: triage picks based on
   the route at triage, or a human picks (often via `/compass:roundtable`).
   A strategy losing a context call is normal - that is what "soft" means.

This replaces the old "constitution supremacy." There is no single supreme
document; there is a small hard set that wins, and a larger soft set that
guides.

---

## Curation

Strategies are cheap to add, which is their strength and their risk. A pile of
stale, contradictory strategies is its own kind of mess. So:

- Review `strategies.md` periodically - `/compass:flow` is a natural prompt.
  Drop strategies the team no longer follows; a strategy nobody applies is
  noise.
- Be slow to add guardrails and slower to remove them. A guardrail is a
  promise the whole framework keeps; the shipped five are deliberately few.
- When a strategy keeps getting overridden the same way, that is a signal -
  either the strategy is wrong, or the thing overriding it should be written
  down. Resolve it; do not let it drift.

---

## Files

| File | Holds | Nature |
|---|---|---|
| `guardrails.md` | The 5 shipped default guardrails + a project-guardrails section | Hard, checkable, blocking |
| `strategies.md` | The shipped default method strategies (incl. BDD and TDD) + a project-strategies section | Soft, assessed, accretive |
| `routing-policy.md` | Routing guardrails (bound triage) + routing strategies (bias triage) | Both, applied to routing |
| `signals.yml` | Advisory patterns: scope-bloat phrases the stop-hook nudges on, the rework-scan window, public-surface patterns | Soft signals - *not* guardrails; advisory only |
| `quarantine.yml` | Records of intermittent tests explicitly quarantined with a tracking issue | Pairs with the `no-trusted-rerun` rule on evidence-not-assertion (see `strategies.md` §6) |

The framework ships these with sane, active defaults. `/compass:init` copies
them into a project so the team can extend them; until then, the shipped
defaults apply as-is. Editing is accretion, not a precondition.
