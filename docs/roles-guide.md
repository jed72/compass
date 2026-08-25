# Compass - Roles Guide

Compass is not an engineering framework with hooks bolted on for everyone
else. It has five roles - engineer, product owner / manager, product
marketer, designer, QA - and all five are full pipeline citizens, with their
own entry points, their own vocabulary, and their own artifacts that plug into
the *same* pipeline.

The mechanism that makes that real instead of aspirational is one file:
`acceptance-criteria.md`, the shared scenario file. Every role reads it - each
through their own perspective. This document is about that mechanism. The centrepiece
is a single concrete scenario, read four different ways. Then: what each role
owns, where they enter, where they gate, and why the non-engineering roles are
upstream and parallel participants rather than downstream consumers.

---

## One spec, many roles

If every role kept its own spec, the specs would drift, and "alignment" would
mean reconciling four documents nobody fully trusts. Compass has one. The
product owner, the marketer, the engineer, QA, and the designer all look at
the *same* Given/When/Then scenarios - so when they disagree, they are
disagreeing about one concrete thing, not comparing translations.

The roles are different ways of reading one document, never different
documents. That is the safeguard. The moment there are two specs, there is no
spec.

---

## The centrepiece: one scenario, four roles

Here is a single scenario from an `acceptance-criteria.md` for a saved-export feature -
the kind of file `/compass:define` produces. We will read this exact
scenario four ways.

```gherkin
Scenario: Finance exports the month-end ledger
  Given a finance user with the "ledger:read" permission
  And the ledger has 14,200 posted entries for the selected month
  When they request a CSV export for that month
  Then a CSV download begins within 3 seconds
  And the file contains exactly the 14,200 posted entries
  And draft and voided entries are excluded
```

```
<!-- traceability id: TRC-A1 · serves: INT-1 -->
```

`INT-1`, in the spec's intent links, traces to `intent.md`: *"Finance pulls
month-end numbers without filing a data request."*

One scenario. Four ways of reading it.

### The product owner reads it for intent fidelity

The product owner's governing question: **does this scenario deliver the
outcome in `intent.md`?**

The intent document's outcome is "finance self-serves their month-end
numbers." So the
product owner walks the scenario against that. The permission gate
(`ledger:read`) is good - self-serve does not mean unguarded. "Within 3
seconds" matters - a self-serve tool that takes two minutes is not really
self-serve; the product owner would want that threshold to *be* in the
scenario, not assumed. "Exactly the 14,200 posted entries" with drafts and
voids excluded is the crux: if finance exports a file that includes drafts,
they have a number they cannot trust, and they are back to filing a data
request to get it reconciled - the outcome fails even though the export
"works."

What the product owner is hunting for is **drift**: a scenario that solves the
literal request ("a CSV export") but misses the outcome ("numbers finance can
self-serve and trust"). They are also checking for **gaps** - every success
signal in the brief should have a scenario behind it - and **scope creep** -
scenarios beyond the brief with no recorded decision. Well-formed and faithful
are different tests, and this is the faithful test.

### The product marketer reads it for claims

The marketer's governing discipline: **what can I truthfully say publicly
because this scenario exists and passes?**

This one scenario backs several candidate claims. "Export your month-end
ledger in seconds" - backed, the scenario asserts "within 3 seconds." "Get the
posted numbers, not the noise" - backed, the scenario excludes drafts and
voids. But "export any report from anywhere in the product" - *not* backed by
this scenario; that is a claim reaching past the build, and the marketer's
move is to soften it, cut it, or file the scenario that would back it.

Every claim in `positioning.md` gets a backing-scenario slot pointing at a
`TRC-` id here. A claim with no backing scenario is a visible debt - the
template leaves the slot blank on purpose. `launch-readiness.md` is the
ledger: claim → scenario → verification status.

### The engineer reads it for tests

The engineer's governing question: **how does this become a test, and what TDD
cycle does it seed?**

This scenario *is* an acceptance-level test - Given/When/Then maps almost
directly onto arrange/act/assert. It also seeds the unit-level
red→green→refactor cycle: the permission check, the month-boundary filter, the
draft/void exclusion, the streaming response that has to start within 3
seconds. Each is a behaviour the engineer drives out test-first - write the
failing test, watch it fail for the right reason, make it green, refactor. The
chain is scenario → test → code.

The engineer does *not* get a private spec. The scenario file is the spec, and
the tests are derived from it, not invented alongside it. "Exactly the 14,200
posted entries" is not a detail the engineer can quietly reinterpret as
"roughly all the entries" - it is the assertion.

### QA reads it for coverage

QA's governing question: **which behaviours are exercised, and which edges are
not described at all?**

QA reads this scenario and immediately asks what is *missing*. What happens
with a finance user who has no `ledger:read` permission? What about a month
with zero posted entries - does the export produce an empty-but-valid CSV or
an error? What about 1.4 million entries instead of 14,200 - does "within 3
seconds" still hold, or does the scenario need a stated ceiling? What about an
entry posted and then voided *during* the export?

Some of those should become scenarios. Some are deliberate non-goals. QA's job
is to make sure the unlisted edges were a *choice*, not an oversight - and QA
has a real power here: **QA can send an issue back to the define stage** if the coverage
has holes or the scenarios are uncoverable. Coverage gaps are a spec problem,
and they are found at verify.

### The designer's perspective - writing *into* the spec

The fifth perspective is the designer's, and it is slightly different: the designer
does not just *read* the spec, they *write into* it. If this export had a
user-facing surface, the designer's `ui-contract.md` would carry scenarios
like:

```gherkin
Scenario: The export control communicates progress
  Given a finance user has requested a month-end export
  When the export is still generating after 1 second
  Then a progress indicator is shown
  And the control cannot be triggered a second time until it completes
```

That is a Given/When/Then like any other, and it *flows into* `acceptance-criteria.md`
at the define stage - it becomes an acceptance check and seeds the TDD
cycle exactly
like the engineer-facing scenarios. The designer feeds the shared file rather
than consuming a finished one.

### The architect-lens reads it against the project's architecture

The sixth perspective is the architect's, and like the designer's it is slightly
different: the architect-lens reads `acceptance-criteria.md` *and* the project's
cross-issue architectural artifacts under `architecture/`. Its governing
question: **does this scenario respect the system's invariants - the
boundaries in `relations.md`, the ownership rules in `ownership.md`, the
decisions codified in `decisions/ADR-*.md`?**

Take the finance export scenario above. The architect walks the scenario
against `architecture/relations.md` and asks: *which service generates this
export, and is the call path it implies allowed by the relations diagram?*
If `relations.md` says the dashboard service may not call the ledger service
directly (the export must go through the reporting service for caching and
audit), and the scenario as written implies a direct call, the architect-lens
flags the drift - *the scenario is well-formed and faithful to `intent.md`, but
it would cut a relation the architecture doesn't permit.* That is exactly the
kind of failure mode the perspective exists to catch.

The architect-lens does **not** write a parallel spec. The scenario file is
still the shared substrate; the perspective's output is `architecture-notes.md` in
the issue directory - annotations *on* `technical-design.md`, pointing at the relevant
ADR or relation each annotation defends:

```markdown
## Architecture notes for fix-export-cors

- **Scenario TRC-A1** crosses `dashboard → ledger`, which `relations.md`
  forbids (decided in `ADR-007 - reporting service owns ledger reads`).
  → Plan must route the export through the reporting service. Direct
    dashboard→ledger call is not an option.
- **Plan §2 DD-1** assumes the existing reporting service exposes a
  ledger-export endpoint. It does not. Either extend `reporting` or
  re-assess this issue to include that extension.
```

The architect-lens is **applied by `spec-author` and `planner` during the
pipeline** - it does *not* have its own `/compass:…` entry point and is *not*
counted as a sixth entry-point role. The other roles in this guide are
**entry-point roles** (each starts a Compass issue); the architect-lens is a
perspective-without-an-entry-point. That is why Compass ships ten agents but only
five entry-point roles: the architect-lens is the 10th agent and the 6th
perspective, applied at the define and design stages when the project ships an
`architecture/` directory. (Projects without `architecture/` get the
perspective as a no-op; the load degrades gracefully.)

QA still owns the verify gate; the `architect-lens` agent is *consulted*
at the design stage rather than gating it. But a design that one of its
annotations flags as architecturally unsound either gets re-designed or
sent back to the define stage - the
annotation is not advisory, it identifies a fact about the system that the
spec or plan needs to accept.

---

## What this demonstrates

Four roles, one scenario, four genuinely different things extracted from it -
intent fidelity, a set of backed claims, a TDD cycle, a coverage assessment -
and none of them required a separate document. When the product owner and the
marketer disagree about whether "in seconds" is a safe claim, they are
disagreeing about *this scenario's "within 3 seconds" line*, not about two
different specs. That is the whole design.

---

## Each role: entry point, artifacts, gates, strategies curated

The five roles, what they own, and how they wire into the pipeline:

| Role | Entry point | Primary artifacts | Where they gate | Strategies curated in `governance/strategies.md` |
|---|---|---|---|---|
| Product owner / manager | `/compass:intent` | `intent.md` | Intent-fidelity check before the design stage | Product strategies |
| Product marketer | `/compass:position` | `positioning.md`, `launch-readiness.md` | Claims gate at ship time | Voice & positioning strategies |
| Designer | `/compass:design` | `ui-contract.md` | UI contracts flow into the define stage as scenarios | (contributes the accessibility strategy) |
| Engineer | `/compass:assess` and the pipeline | `delivery-approach.md`, `technical-design.md`, code | Owns implementation; verify's mechanical half | Engineering strategies |
| QA | joins at `/compass:verify` | `verification-report.md` | Owns the verify gate | (guards the guardrails at verify) |

### Product owner / manager - `/compass:intent`

Enters **upstream of the spec**. `intent.md` exists before the scenarios do -
problem, desired outcome, success signals, constraints, non-goals. Assess
reads it: intent is the *actual outcome wanted*, not the literal
request. The `product-owner` role rule adds `intent.md` as a required artifact
and inserts the **intent-fidelity gate before the design stage** - the spec
must be checked against `intent.md` before design starts. The `product-lens`
agent applies this perspective, at the requirements review and at the
pre-design gate. The product owner curates the
product strategies in `governance/strategies.md` - adding and refining them as
the team forms opinions, never unilaterally rewriting a guardrail.

### Product marketer - `/compass:position`

Works **parallel to the spec**, not downstream of it. Drafts `positioning.md`
from `intent.md` and the emerging scenarios - claims written so the scenario
file can back them, not aspirational copy that outruns the build. Builds
`launch-readiness.md` as a claims-to-scenarios ledger. The `product-marketer`
role rule turns on the `claims` review dimension and **blocks shipping**
until every claim traces to a passing scenario; `verify.claims` is an
immovable gate - no delivery approach removes it. The `marketing-lens` agent applies this perspective and runs
the claims gate at ship time. The marketer curates the voice & positioning
strategies in `governance/strategies.md`.

### Designer - `/compass:design`

Feeds **into the spec**. UI contracts in Compass are not mockup annotations -
they are scenarios, Given/When/Then, written in the same form as the rest of
the spec so they compose cleanly when they reach the define stage. `ui-contract.md`
covers the empty state, the loading state, the error state, and the
accessibility expectations - not just the happy path - and must honour the
accessibility strategy in `governance/strategies.md` (and any project guardrail
the team has hardened from it). When `spec-author` defines the acceptance criteria, it folds the
UI contract scenarios into `acceptance-criteria.md`; because they are already
Given/When/Then, nothing is lost in translation.

### Engineer - `/compass:assess` and the pipeline

The engineer carries the pipeline's spine: triage, design,
implementation, and the mechanical half of verify. Reads the spec **for tests** - scenarios
become the acceptance suite and seed the TDD cycle. Curates the engineering
strategies in `governance/strategies.md`, checked at the design stage by
`governance-check`. The engineer is a full citizen too - but, importantly,
not the *only* citizen, and not the citizen the others report to.

### QA - joins at `/compass:verify`

Owns the **verify gate**. Reads the spec **for coverage** - not just that the
listed scenarios pass, but that the behaviour space is actually covered and
the unlisted edges were deliberate. The `verifier` agent runs the suites and
gathers evidence; the `reviewer` agent applies the review dimensions and
renders the gate decision; QA owns the gate those produce. QA guards the
guardrails at verify - confirming each cleared with evidence, not a
claim. QA's distinct power is the ability to **send an issue back to the
define stage** when scenarios are uncoverable or coverage has holes - a
coverage gap is a spec problem, surfaced at verify.

---

## The function with no role: delivery management

A reader counting roles will notice an omission. Most software orgs have a
delivery manager, a project manager, a scrum master - someone who runs the
*board* rather than a discipline. Compass has the function but deliberately
not the role.

The reason is structural. The other five roles each own a *perspective on the work* -
a way of reading `acceptance-criteria.md` that produces something the build needs.
Delivery management is not a perspective; it is a *view across issues*. Modelling it as
a role would mean a persona with turf and an inbox, "owning" the board and
"moving" work through it - and Compass has nothing for that persona to own,
because issue state is not a label anyone sets. It is inferred from the
artifacts on disk.

So delivery management is a **capability**: `/compass:flow`, backed by the
`flow-management` skill. Anyone runs it. It reads every issue's artifacts,
triages (guardrail violations, routes outgrown, stalls, owed follow-ups
aggregated across the board), surfaces what needs a human first, and writes a
periodic digest. It *advises* - it never gates and it never sets issue state.
The gates stay in the per-issue pipeline, next to the evidence. See
`methodology.md` §10 for the full rationale, and `commands/flow.md` for
the command.

The test of whether this was the right call: nothing about delivery management
needs a seat at the spec. It needs a view of the whole. A capability gives it
the view without inventing a persona to hold it.

---

## Why non-engineering roles are upstream and parallel, not downstream

The thing Compass refuses is the common shape where the product owner, the
marketer, and the designer are *reviewers of finished engineering work* - they
get handed a built thing and asked to bless it. In that shape their feedback
is either too late to act on or forces expensive rework, and so it gets
diluted into "looks good." The roles become decorative.

Compass puts them *in* the pipeline:

- The **product owner enters upstream of the spec.** `intent.md` exists before
  the scenarios, and the scenarios are checked back against it. The product
  owner is shaping what gets built, not reacting to what got built.
- The **marketer works parallel to the spec.** Claims are drafted *alongside*
  the scenarios, so an unbackable claim is caught while the spec is still
  cheap to change - not discovered at launch when the copy is written and the
  feature does not support it.
- The **designer feeds into the spec.** UI contracts are spec input, not
  spec commentary. The interaction behaviour is in the scenario file before
  Build starts.

A role in Compass is not a consultation - it is an entry point that *changes
the approach*. When `/compass:intent`, `/compass:position`, or `/compass:design`
opens a session, triage reads the role as part of the assessment, and a
non-engineering role almost always pulls the approach heavier: more
artifacts, more gates. That weight is the framework working as designed, not overhead to
trim. The proof that a role is a real citizen is that its involvement is
*enforced* - `verify.claims` is an immovable gate; the intent-fidelity check
blocks the design stage - not merely invited.

---

## When roles conflict - `/compass:roundtable`

The different ways of reading one document still have to be reconciled,
and the pipeline has specific moments for it. At **the requirements
review**, the non-engineering roles read the spec together - this is
where intent, claims, and contract disagreements surface while the spec
is still cheap to change;
an ambiguity one perspective sees is logged in `requirements-review.md` with its
resolution. At **the gates**, the roles become review dimensions.

When a choice genuinely sits *across* roles - a scope cut that affects a
marketing claim, an architecture call that changes the user's experience -
`/compass:roundtable` convenes several roles on one question, makes the
tradeoffs explicit, and records the decision in `devlog.md`. Each perspective speaks
in its own vocabulary; none speaks for another. When two roles genuinely
conflict, governance arbitrates by the conflict rule: a guardrail always beats
a strategy, and strategy-vs-strategy is resolved by the delivery approach
or a human.
A conflict governance does not resolve becomes a `requirements-review.md` entry and,
if it changes scope or the approach, a re-assessment.

---

## Anti-patterns

The role model fails in recognisable ways. Watch for these:

- **The shadow spec** - a role keeping its own private requirements document
  instead of reading and contributing to `acceptance-criteria.md`. The moment there
  are two specs, there is no spec.
- **The downstream consultee** - treating the product owner, marketer, or
  designer as a reviewer of finished engineering work. They are *in* the
  pipeline: the product owner upstream of the spec, the marketer parallel to
  it, the designer feeding into it.
- **Perspective collapse** - flattening a product owner's brief straight into an
  engineering issue. The brief is upstream of the spec, and the spec must be
  checked back against it; collapsing the two skips the intent-fidelity gate.
- **The unread spec** - a role with an opinion about the product who has not
  read the scenario file. Every perspective reads the *same* file; an opinion not
  grounded in it is not a perspective, it is a preference.
