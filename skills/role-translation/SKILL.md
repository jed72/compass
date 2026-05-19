---
name: role-translation
description: The "one spec, many lenses" mechanism — how the same spec.feature.md is read by the PM (intent), the marketer (claims), the engineer (tests), QA (coverage), and the designer (contracts). Triggers on any role-facing work and whenever a non-engineering role enters the pipeline.
---

# Role Translation

Compass is not an engineering framework with hooks bolted on for other people.
The four non-engineering roles are full pipeline citizens. The mechanism that
makes that real — instead of aspirational — is the **shared scenario file**.
`spec.feature.md` is the one artifact every role reads, each through their own
lens. This skill is how each lens works and how they stay coherent.

## Why one shared artifact

If every role had its own spec, the specs would drift, and "alignment" would
mean reconciling four documents nobody fully trusts. Compass has one. The PM,
the marketer, the engineer, QA, and the designer are all looking at the *same*
Given/When/Then scenarios — so when they disagree, they are disagreeing about
one concrete thing, not comparing translations. The scenario file is the
substrate; the lenses are how each role uses it.

## The five lenses

### Product owner / manager — the **intent** lens
Reads each scenario asking: *does this deliver the outcome in `brief.md`?*
- Walks every success signal in the brief and finds the scenario that delivers
  it. A signal with no scenario is a gap; a scenario that solves the literal
  request but misses the outcome is drift.
- Enters *upstream* of the spec — `brief.md` exists before the scenarios — and
  gates Plan: per the routing policy's blocking `role_rules`, the spec must be
  checked against the brief before Plan starts. Applied by the `product-lens`
  agent.

### Product marketer — the **claims** lens
Reads each scenario asking: *what can I truthfully say publicly because this
scenario exists and passes?*
- Every line of launch copy in `positioning.md` must point at a backing
  scenario. `launch-readiness.md` is the ledger: claim → scenario → status.
- Works *parallel* to the spec and gates Land — `verify.claims` is an immovable
  gate; no claim ships on a missing, red, or skipped scenario. Applied by the
  `marketing-lens` agent.

### Engineer — the **tests** lens
Reads each scenario asking: *how does this become a test, and what TDD cycle
does it seed?*
- The scenarios *are* the acceptance suite; each also seeds the unit-level
  red→green→refactor cycle. The chain is scenario → test → code.
- Owns Build and Verify's mechanical half. The engineer does not get a
  private spec — the scenario file is the spec, and the tests are derived from
  it, not invented alongside it.

### QA — the **coverage** lens
Reads each scenario asking: *which behaviours are exercised, and which edges are
not described at all?*
- Owns the Verify gate. Checks that the scenario set actually covers the
  behaviour space — not just that the listed scenarios pass, but that the
  unlisted edges were a deliberate choice, not an oversight.
- Has a real power: QA **can send a task back to Specify** if scenarios are
  uncoverable or the coverage has holes. Coverage gaps are a spec problem, found
  at Verify.

### Designer — the **contracts** lens
Reads — and *writes into* — the spec through UI contracts.
- `ui-contract.md` expresses UI behaviour as scenarios, and those scenarios
  *flow into* Specify. The designer feeds the shared file rather than consuming
  a finished one.
- A UI contract is a Given/When/Then like any other: given this state, when this
  interaction, then this observable interface outcome.

## How the lenses stay coherent

The lenses are different *readings*, not different *documents* — that is the
safeguard. But they still have to be reconciled, and the pipeline has specific
moments for it:

- **At Clarify**, the non-engineering roles review the spec together. This is
  where intent-lens, claims-lens, and contracts-lens disagreements surface
  while the spec is still cheap to change. An ambiguity one lens sees is logged
  in `clarifications.md` with its resolution.
- **At the gates**, the lenses become review dimensions — `claims` is the
  marketer's lens as a Verify dimension; the intent check is the PM's lens as a
  pre-Plan gate.
- **When two lenses conflict**, governance arbitrates by the conflict rule. A
  guardrail always beats a strategy — so a lens whose concern is a guardrail
  (the claims gate, traceability) wins over a lens leaning on a strategy.
  Strategy-vs-strategy is resolved by route context (the Needle's call) or by a
  human, often at `/compass:roundtable` — each non-engineering role curates its
  own strategies (product, voice & positioning) but none of them outranks a
  guardrail. A conflict that governance does not resolve is a
  `clarifications.md` entry and, if needed, a re-frame.

## How a non-engineering role enters the pipeline

A role is not a consultation; it is an entry point that *changes the route*.
When `/compass:intent`, `/compass:position`, or `/compass:design` opens a
session — or `/compass:roundtable` convenes several — the Needle reads the role
as the fourth dimension. A non-engineering role almost always pulls the route
heavier: it adds artifacts (`brief.md`, `positioning.md`, `ui-contract.md`) and
gates (the intent check, the claims gate). That weight is the framework working
as designed, not overhead to trim.

## Anti-patterns

- **The shadow spec** — a role keeping its own private requirements doc instead
  of reading and contributing to `spec.feature.md`. The moment there are two
  specs, there is no spec.
- **The downstream consultee** — treating the PM, marketer, or designer as a
  reviewer of finished engineering work. They are *in* the pipeline: the PM
  upstream of the spec, the marketer parallel to it, the designer feeding into
  it.
- **Lens collapse** — flattening a product owner's brief straight into an
  engineering task. The brief is upstream of the spec and the spec must be
  checked back against it; collapsing the two skips the intent-fidelity gate.
- **The unread spec** — a role that has an opinion about the product but has not
  read the scenario file. Every lens reads the *same* file; an opinion not
  grounded in it is not a lens, it is a preference.
