# Comparison proposal — requirements analysis

A business-analysis pass over `docs/proposals/comparison.md`. The proposal is a
strategy document: it fixes a set of non-negotiable invariants ("the hard line"),
weighs four competing frameworks, and lands on a prioritised shortlist of three
candidate capabilities, each carrying a "guard" it must respect.

This document turns that proposal into **buildable requirements**. It does not
re-argue the strategy; it extracts the vocabulary, enumerates the constraints the
candidates must honour, and expresses each candidate as Given/When/Then scenarios
with measurable quality targets. Everything traces back to a line range in
`comparison.md`; where it leans on the project's `CLAUDE.md` / methodology that is
noted, and anything not stated in either source is flagged as an assumption.

## Scope

- **Domain:** Compass — an adaptive, mechanically-enforced spec-driven development
  framework for coding agents.
- **In scope:** the three adoption-shortlist candidates (`comparison.md:146-158`) —
  `compass analyze`, the living system spec, and invisible skill triggering plus
  `compass next` — together with the invariants and per-candidate guards that
  constrain how they may be built.
- **Out of scope:** the four surveyed frameworks themselves, and the explicitly
  *refused* ideas (`comparison.md:160-163`), captured here only as negative
  constraints (BR-012…BR-016) so the build cannot drift into them.
- **Audience:** whoever specs, builds, and verifies these three capabilities.

---

## 1. Ubiquitous language

Canonical business terms first, technical alias second. Every rule and scenario
below uses these terms verbatim.

| Term | Definition | Also known as | Notes / source |
|------|------------|---------------|----------------|
| Frame | The first pipeline phase: read the four context dimensions, then run `compass route evaluate --write` to compute and record the route. Never skipped for work that changes artifacts. | the Needle, `/compass:frame` | `CLAUDE.md`; referenced throughout `comparison.md`. |
| Route | The per-task process computed at Frame — which phases run full-weight, collapse, or are skipped. | — | `comparison.md:9-11`, `:22-25`. |
| Reading | One of the four context dimensions judged by a human at Frame: **blast radius**, **terrain**, **magnitude**, **intent & role**. | the four readings, context dimensions | `comparison.md:22-25`, `:26-30`. |
| Blast radius | The reversibility/impact reading; large blast radius is what can *earn* heavier ceremony or promote a check to a gate. | — | `comparison.md:23`, `:84-85`. |
| Determinism boundary | The line between **judgement** (the four readings — human) and **mechanism** (route composition, floors/caps, guardrail checks — CLI). Same readings + same policy ⇒ same route. | — | `comparison.md:26-30`. |
| Routing policy | The deterministic machine-readable policy (`governance/routing-policy.yml`) the CLI applies to readings to compose a route. | — | `CLAUDE.md`; `comparison.md:28-29`. |
| Guardrail | A constraint that is few, hard, checkable, and **blocking**. No route or convenience crosses one (G1–G5). | hard line | `comparison.md:31-35`; `CLAUDE.md`. |
| Strategy | A directional practice that is many, soft, and **assessed, not blocking**. BDD and TDD are the shipped default strategies. | — | `comparison.md:31-35`. |
| Gate | A checkpoint that blocks a phase transition until its checklist is satisfied — the Definition of Ready (Clarify→Plan) and Definition of Done (Verify→Land). | DoR, DoD | `CLAUDE.md`; `comparison.md:84-85`. |
| Spike | A route for genuinely exploratory work; the TDD strategy is suspended on it. | — | `comparison.md:140-142`; `CLAUDE.md`. |
| Land | The final pipeline phase, where a route's work integrates. The proposed living system spec is a *product* of this phase. | — | `comparison.md:103-112`, `:150-155`. |
| Lens | A role's perspective on the **one shared spec**. Compass has five roles as lenses, not as separate agents/characters. | role | `comparison.md:65-68`. |
| Scenario | A Given/When/Then behaviour statement; the shared artifact every role reads. Proposed substrate for the living system spec. | spec.feature.md | `comparison.md:108-112`. |
| task.yml | The machine-readable task spine the CLI reads and writes; holds readings, route, scenarios, changed files. | — | `CLAUDE.md`; `comparison.md:60-63`, `:81-84`. |
| route.md | The human-readable Frame output describing the computed route. | — | `comparison.md:81-84`. |
| `compass check` | The existing CLI verb that proves gate evidence *exists*, is valid, and *traces*. | — | `comparison.md:80-84`. |
| `compass analyze` | **(Candidate 1)** A proposed CLI verb: a mechanical, deterministic *coherence* check across `brief.md`, scenarios, `route.md`, and `task.yml`. Advisory by default; a gate only where the route earns it. | cross-artifact consistency check | `comparison.md:79-87`, `:150-152`. |
| Living system spec | **(Candidate 2)** A proposed durable, accreted description of the system, derived from scenarios as routes land — a product of the pipeline, not hand-maintained. | living-spec corpus, spec-evolution outcome | `comparison.md:103-112`, `:153-155`. |
| `compass next` | **(Candidate 3a)** A proposed one-line CLI verb that reads `task.yml` and the route and says which phase and gate come next and what is optional on *this* route. | — | `comparison.md:58-63`, `:156-158`. |
| Invisible triggering | **(Candidate 3b)** The ergonomic property that skills (and Frame) fire when relevant without the user reciting incantations. Presentation/ergonomics only. | ergonomics of invisibility | `comparison.md:129-138`, `:156-158`. |
| Five-minute legibility | The cross-cutting USP that the conceptual model must be graspable in ~5 minutes; every addition is weighed against the surface area it adds. | — | `comparison.md:40-44`. |
| USP | Unique selling proposition — here, one of the invariants on the hard line that must not be compromised. | — | `comparison.md:15-44`. |

---

## 2. Business rules

The hard line is a set of constraint rules every candidate must satisfy; the
guards are per-candidate constraints; the refusals are negative constraints
(what must not be built). All are implementation-independent policy — the
behaviour that honours them lives in §3–§4.

### The hard line — invariants

#### BR-001 — Process intensity is computed per task, not selected from a ladder
- **Type:** Constraint
- **Statement:** A task's process intensity must be *computed* from the four
  continuous readings, never selected from a fixed menu of tiers/levels.
- **Source:** `comparison.md:22-25`.
- **Rationale:** A fixed tier menu collapses Compass into "BMAD with fewer agents";
  per-task routing is the primary USP.
- **Related terms:** Route, Reading, Routing policy.
- **Edge cases:** Floors and caps may bound a route (`comparison.md:28-29`) — that
  is still computation, not a tier menu.
- **Status:** As-is (invariant).

#### BR-002 — The determinism boundary is real
- **Type:** Constraint
- **Statement:** Judgement (the four readings) is human; everything after — route
  composition, floors/caps, guardrail checks — is mechanism. The same readings
  applied to the same policy must yield the same route. No feature may move
  post-reading work back to "the agent decides at runtime".
- **Source:** `comparison.md:26-30`.
- **Rationale:** Determinism after the boundary is the core verifiable claim.
- **Related terms:** Determinism boundary, Routing policy, Route.
- **Edge cases:** A runtime LLM decision anywhere past the readings violates this,
  regardless of how helpful it is.
- **Status:** As-is (invariant).

#### BR-003 — Guardrails are hard; strategies are soft; TDD/BDD are strategies
- **Type:** Constraint
- **Statement:** Guardrails (few, hard, blocking) constrain outcomes; strategies
  (many, soft, assessed) bias method. TDD and BDD are strategies, not guardrails:
  the *outcome* (tested before it lands, acceptance defined) is hard, the *ritual*
  is negotiable and route-aware.
- **Source:** `comparison.md:31-35`.
- **Rationale:** This split is what lets a typo fix and a payments rewrite share one
  vocabulary; it is the exact inverse of a uniform-TDD framework.
- **Related terms:** Guardrail, Strategy, Spike.
- **Edge cases:** On a Spike route the TDD strategy is suspended; the tested-before-
  land *outcome* still governs anything that lands.
- **Status:** As-is (invariant).

#### BR-004 — Governance is a gradient from zero
- **Type:** Constraint / default
- **Statement:** Frame must work on day one with no project setup; teams accrete
  strategy as they form opinions. No feature may reintroduce an upfront
  configuration tax.
- **Source:** `comparison.md:36-38`.
- **Rationale:** A setup tax breaks the on-ramp.
- **Related terms:** Frame, Routing policy.
- **Edge cases:** Shipped defaults stand in for any absent project config.
- **Status:** As-is (invariant).

#### BR-005 — Every addition is weighed against five-minute legibility
- **Type:** Constraint
- **Statement:** Each new capability is weighed against the surface area it adds;
  when in doubt the framework must get *lighter* to learn, not heavier. The wedge
  (adaptive *and* enforced, ritual demoted to strategy) must stay graspable in ~5
  minutes.
- **Source:** `comparison.md:40-44`, `:171-174`.
- **Rationale:** The conceptual model is the richest asset and the heaviest
  adoption cost; the field competes on legibility.
- **Related terms:** Five-minute legibility, USP.
- **Edge cases:** A feature that is net-new *concept* (not just a verb) is suspect
  even if individually useful.
- **Status:** As-is (invariant).

### Guards on the shortlist candidates

#### BR-006 — `compass analyze` stays on the mechanism side of the boundary
- **Type:** Constraint
- **Statement:** `compass analyze` must be a mechanical, deterministic coherence
  check; it must not introduce runtime agent judgement.
- **Source:** `comparison.md:84-85`, `:150-152`.
- **Rationale:** Protects BR-002.
- **Related terms:** `compass analyze`, Determinism boundary.
- **Edge cases:** See BR-002 edge cases.
- **Status:** Proposed.

#### BR-007 — `compass analyze` is advisory by default, a gate only by route
- **Type:** Constraint / action-enabler
- **Statement:** `compass analyze` is advisory by default; it is promoted to a
  blocking gate only on routes whose blast radius earns it, never globally.
- **Source:** `comparison.md:84-85`, `:150-152`.
- **Rationale:** Promoting it globally would impose ceremony irrespective of route,
  violating BR-001.
- **Related terms:** `compass analyze`, Blast radius, Gate, Route.
- **Edge cases:** The blast-radius threshold for promotion is policy-driven and
  currently unspecified — see OQ-2.
- **Status:** Proposed.

#### BR-008 — The living system spec is derived, not hand-maintained
- **Type:** Constraint
- **Statement:** The living system spec must be an accreted, mostly-derived artifact
  produced *at Land* from the scenarios — not a document a person maintains by hand.
- **Source:** `comparison.md:108-112`, `:153-155`.
- **Rationale:** Hand-maintenance adds ceremony and rots; derivation keeps it
  current without effort.
- **Related terms:** Living system spec, Land, Scenario.
- **Edge cases:** A task that lands no behaviour change (e.g. a pure Spike)
  contributes nothing to the spec.
- **Status:** Proposed.

#### BR-009 — The living system spec adds no upfront tax and no new ceremony
- **Type:** Constraint
- **Statement:** Introducing the living system spec must add no upfront setup and no
  new phase or gate to the pipeline.
- **Source:** `comparison.md:110-112`, `:153-155`.
- **Rationale:** Protects BR-004 (gradient from zero) and BR-005 (legibility).
- **Related terms:** Living system spec, Gate, Frame.
- **Edge cases:** A greenfield project with zero setup must still Land normally with
  no pre-existing system spec.
- **Status:** Proposed.

#### BR-010 — `compass next` is a derived, one-line read of existing state
- **Type:** Derivation
- **Statement:** `compass next` must derive its answer from `task.yml` and the route
  already on disk and report, in one line, the next phase and gate and what is
  optional on *this* route. It introduces no new state.
- **Source:** `comparison.md:58-63`, `:156-158`.
- **Rationale:** It teaches the model by using it, at zero conceptual cost.
- **Related terms:** `compass next`, task.yml, Route, Gate.
- **Edge cases:** On a completed task it reports that nothing remains (see scenarios).
- **Status:** Proposed.

#### BR-011 — Candidate 3 is presentation/ergonomics only
- **Type:** Constraint
- **Statement:** Invisible triggering and `compass next` must add no new concept, no
  new agent, and no new surface area; they change *how* existing capabilities are
  reached, not *what* exists.
- **Source:** `comparison.md:133-135`, `:156-158`.
- **Rationale:** Pure USP-protection: lowers activation energy without touching the
  model (BR-005).
- **Related terms:** Invisible triggering, `compass next`, Lens.
- **Edge cases:** Explicit invocation of commands must still work — invisibility is
  additive, not a replacement.
- **Status:** Proposed.

### Refused ideas — negative constraints

These record what must **not** be built, so the candidates cannot drift into them.

#### BR-012 — No tier/level ladder for process intensity
- **Type:** Constraint (prohibition)
- **Statement:** Compass must not ship a fixed menu of process tiers/levels.
- **Source:** `comparison.md:24-25`, `:160-161`.
- **Related terms:** Route, BR-001.

#### BR-013 — No persona zoo or module ecosystem of agents
- **Type:** Constraint (prohibition)
- **Statement:** Compass must not multiply agents into a cast of expert personas or
  a module ecosystem; the five roles remain lenses on one shared spec.
- **Source:** `comparison.md:65-68`, `:160-161`.
- **Related terms:** Lens, BR-005.

#### BR-014 — No flat, fixed-depth pipeline
- **Type:** Constraint (prohibition)
- **Statement:** Compass must not adopt a one-size, fixed-depth pipeline; the phases
  must keep flexing by route.
- **Source:** `comparison.md:93-94`, `:160-161`.
- **Related terms:** Route, BR-001.

#### BR-015 — No fluid, no-gate mode
- **Type:** Constraint (prohibition)
- **Statement:** Compass must not make phases and gates optional/unstructured; the
  enforced pipeline and the gates are the product.
- **Source:** `comparison.md:114-117`, `:160-161`.
- **Related terms:** Gate, BR-003.

#### BR-016 — No mandatory universal TDD
- **Type:** Constraint (prohibition)
- **Statement:** Compass must not make red/green TDD mandatory for every task; TDD
  remains the strong default strategy that the Spike route can suspend.
- **Source:** `comparison.md:140-142`, `:160-161`.
- **Related terms:** Strategy, Spike, BR-003.

### Conflicts, gaps, and tensions

- **Managed tension (not a defect):** BR-005 says the framework should get *lighter*,
  yet the shortlist adds two new CLI verbs (`analyze`, `next`) and one new artifact
  (living spec). The proposal manages this by constraining Candidate 3 to
  presentation-only (BR-011) and the living spec to derived/no-ceremony (BR-008/9).
  Flagged so the legibility budget is tracked, not assumed.
- **Gap (OQ-2):** the blast-radius threshold at which `compass analyze` is promoted
  from advisory to gate (BR-007) is unspecified.
- **Gap (OQ-3):** how the living system spec reconciles superseded/conflicting
  scenarios across tasks (archive vs merge) is unspecified.
- **Overlap to pin down (OQ-1):** `compass analyze` (coherence) vs `compass check`
  (evidence exists/valid/traces) must have a clean, non-duplicating boundary.

---

## 3. Functional requirements (BDD)

Scenarios are declarative and in the ubiquitous language. Each candidate's
behaviour is grouped under the business rule it honours; every rule carries at
least one positive and one negative/exception scenario.

### Feature 1 — `compass analyze`: cross-artifact coherence

```gherkin
Feature: compass analyze — cross-artifact coherence check
  As a Compass user closing out a phase
  I want a deterministic check that brief.md, the scenarios, route.md and task.yml agree
  So that drift between the artifacts is caught before it lands

  Rule: analyze reports coherence across the task's artifacts (BR-006)

    Background:
      Given a framed task with brief.md, scenarios, route.md and task.yml on disk

    Scenario: Coherent artifacts pass cleanly
      Given every scenario traces to an intent stated in brief.md
      And route.md and task.yml describe the same route
      When compass analyze runs for the task
      Then it reports no incoherence

    Scenario: A scenario with no upstream intent is flagged
      Given a scenario that traces to no intent in brief.md
      When compass analyze runs for the task
      Then it reports the scenario as incoherent
      And it names the orphaned scenario

    Scenario: Route disagreement between route.md and task.yml is flagged
      Given route.md lists a phase that task.yml records as skipped
      When compass analyze runs for the task
      Then it reports the route as incoherent
      And it names the disagreeing phase

  Rule: analyze is deterministic and stays on the mechanism side (BR-006, BR-002)

    Scenario: Same artifacts and policy give the same verdict
      Given an unchanged set of task artifacts
      And an unchanged routing policy
      When compass analyze runs twice
      Then both runs return an identical verdict

    Scenario: analyze reaches no verdict by runtime agent judgement
      When compass analyze runs for the task
      Then it makes no runtime model call to decide coherence
      And its verdict is reproducible from the artifacts and policy alone

  Rule: analyze is advisory by default and a gate only by route (BR-007)

    Scenario: Incoherence on a low-blast-radius route warns but does not block
      Given a route whose blast radius does not earn an analyze gate
      And compass analyze reports incoherence
      When the task proceeds to Land
      Then Land is not blocked by analyze
      And the incoherence is surfaced as advice

    Scenario: Incoherence on a high-blast-radius route blocks Land
      Given a route whose blast radius earns an analyze gate
      And compass analyze reports incoherence
      When the task attempts to Land
      Then Land is blocked until the incoherence is resolved

    Scenario: analyze is never promoted to a gate globally
      Given two tasks on routes that do not earn an analyze gate
      When compass analyze reports incoherence on both
      Then neither Land is blocked

  Rule: analyze is route-aware about absent-by-design artifacts (BR-007)

    Scenario: An artifact a route legitimately omits is not flagged
      Given a route on which the brief is collapsed by construction
      And no brief.md exists for the task
      When compass analyze runs
      Then it does not report the missing brief as incoherence

    Scenario: analyze does not duplicate evidence checks
      Given a task missing gate evidence that compass check would catch
      When compass analyze runs
      Then it reports only coherence findings
      And it does not assert whether gate evidence exists
```

### Feature 2 — Living system spec accreted on Land

```gherkin
Feature: Living system spec derived at Land
  As a team that has run many tasks
  I want a durable, current description of the system derived from scenarios as they land
  So that Compass leaves behind an evolving spec, not a pile of task directories

  Rule: landing a route folds its scenarios into a derived system spec (BR-008)

    Scenario: A landed behaviour change accretes into the system spec
      Given a task whose scenarios describe a new behaviour
      When the task Lands
      Then the living system spec includes those scenarios

    Scenario: A pure Spike contributes nothing to the system spec
      Given a Spike route that lands no behaviour change
      When the task Lands
      Then the living system spec is unchanged

  Rule: the spec is derived, not hand-maintained (BR-008)

    Scenario: Re-deriving from unchanged scenarios produces no diff
      Given a living system spec already derived from the current scenarios
      When the derivation runs again with no scenario change
      Then the living system spec is byte-identical

    Scenario: A superseding change updates the prior behaviour
      Given the living system spec describes an existing behaviour
      And a task lands scenarios that supersede that behaviour
      When the task Lands
      Then the superseded behaviour is no longer presented as current
      # How supersession is reconciled (archive vs merge) is OQ-3

  Rule: the spec adds no upfront tax and no new ceremony (BR-009)

    Scenario: A greenfield project lands with no pre-existing system spec
      Given a brand-new project with no setup and no living system spec
      When its first task Lands
      Then Land succeeds
      And the living system spec is created as a product of that Land

    Scenario: Introducing the living spec adds no new phase or gate
      Given the pipeline Frame → … → Land
      When the living system spec capability is enabled
      Then the set of phases is unchanged
      And the set of gates is unchanged
```

### Feature 3 — Invisible triggering and `compass next`

```gherkin
Feature: Frictionless orientation and skill activation
  As a newcomer inside a large process
  I want skills to fire when relevant and one-line guidance on what comes next
  So that I stay oriented without reciting commands

  Rule: skills and Frame trigger without the user reciting incantations (BR-011)

    Scenario: Asking to build something triggers Frame
      Given a session with no active framed task
      When the user asks the agent to build a change
      Then Frame runs before any artifact-changing work
      And the user did not have to name the Frame command

    Scenario: Explicit invocation still works
      Given a user who names a Compass command directly
      When they invoke it
      Then it runs as invoked
      # invisibility is additive, not a replacement (BR-011 edge case)

    Scenario: An exploratory request still gets framed
      Given a request too vague to deliver as specified
      When the agent picks up the request
      Then Frame still runs
      And it routes the work as a Spike rather than skipping Frame

  Rule: compass next derives one-line guidance from existing state (BR-010)

    Background:
      Given a framed task with task.yml and route.md on disk

    Scenario: next reports the upcoming phase and gate
      Given the task has completed Specify
      When the user runs compass next
      Then it reports, in one line, the next phase and its gate

    Scenario: next states what is optional on this route
      Given a route on which Clarify collapses
      When the user runs compass next at that point
      Then its one-line answer marks Clarify as optional on this route

    Scenario: next on a completed task reports nothing remains
      Given a task that has Landed
      When the user runs compass next
      Then it reports that no phase remains

    Scenario: next introduces no new state
      When compass next runs
      Then it writes no new task state
      And its answer is derived only from task.yml and the route
```

---

## 4. Non-functional requirements

These carry the cross-cutting USPs as measurable targets. Where a target has no
source in `comparison.md` it is marked as an assumption to confirm (see §5).

### NFR-LEG-001 — Five-minute legibility preserved
- **Category:** Usability / maintainability
- **Requirement:** The three candidates together introduce **zero net-new
  top-level concepts** and at most the two new CLI verbs already named
  (`analyze`, `next`) plus one derived artifact. A newcomer can still state the
  wedge — "adaptive *and* enforced, ritual demoted to strategy" — within ~5
  minutes of first contact.
- **Metric / measurement:** Count of new concepts in the glossary attributable to
  each candidate (target: 0 concepts; verbs/artifacts as above). Time-to-articulate
  measured by a short onboarding check with new users.
- **Priority:** Must
- **Source / rationale:** `comparison.md:40-44`, `:133-135`, `:171-174` (BR-005, BR-011).
- **Fitness function:** A docs/legibility check asserting the candidates add no
  new top-level concept headings; periodic onboarding comprehension test.

### NFR-DET-001 — Route determinism
- **Category:** Reliability (correctness)
- **Requirement:** The same four readings applied to the same routing policy
  produce a byte-identical route, with no runtime agent judgement after the
  determinism boundary.
- **Metric / measurement:** Golden-route test: fixed readings + fixed policy ⇒
  fixed `route.md`/`task.yml` route fields, across repeated runs.
- **Priority:** Must
- **Source / rationale:** `comparison.md:26-30` (BR-002).
- **Fitness function:** CI golden test that fails on any non-deterministic route
  output.

### NFR-DET-002 — `compass analyze` determinism and offline operation
- **Category:** Reliability (correctness)
- **Requirement:** `compass analyze` produces an identical verdict for identical
  artifacts + policy and makes no network or model call on its decision path.
- **Metric / measurement:** Repeat-run equality test; network/model-call assertion
  on the analyze path (expected count: 0).
- **Priority:** Must
- **Source / rationale:** `comparison.md:84-85`, `:150-152` (BR-006).
- **Fitness function:** A test that runs analyze twice on a fixture and asserts
  identical output; a guard that fails if the analyze path opens a socket or model
  client.

### NFR-ONR-001 — Zero-setup on-ramp preserved
- **Category:** Operability / usability
- **Requirement:** Frame, `compass analyze`, `compass next`, and the living-spec
  derivation all function on a repository with no `/compass:init` and no project
  `governance/` overrides, falling back to shipped defaults.
- **Metric / measurement:** Integration test on a bare repo exercising each
  capability with no project config present (expected: all succeed).
- **Priority:** Must
- **Source / rationale:** `comparison.md:36-38`, `:110-112` (BR-004, BR-009).
- **Fitness function:** A bare-repo integration test in CI.

### NFR-MNT-001 — Living system spec is idempotent and derived
- **Category:** Maintainability
- **Requirement:** Re-running the living-spec derivation against unchanged scenarios
  yields no diff; the artifact is reproducible from the scenarios on disk and is
  never the sole source of truth.
- **Metric / measurement:** Idempotency test (derive → derive ⇒ empty diff); a
  provenance check that every spec entry traces to a landed scenario.
- **Priority:** Must
- **Source / rationale:** `comparison.md:108-112`, `:153-155` (BR-008).
- **Fitness function:** Idempotency test in CI; trace-back assertion from spec
  entries to scenarios.

### NFR-PERF-001 — Orientation commands are fast *(assumption — target to confirm)*
- **Category:** Performance
- **Requirement:** `compass next` returns in well under a second and `compass
  analyze` completes within a few seconds on a typical task, since both sit on
  interactive paths.
- **Metric / measurement:** Wall-clock at p95 on a representative task fixture.
  **Provisional targets** (no source in `comparison.md`, see OQ-4): `next` < 200 ms
  p95; `analyze` < 3 s p95.
- **Priority:** Should
- **Source / rationale:** Inferred from the interactive, "one-line"/advisory framing
  (`comparison.md:58-63`, `:84-85`); targets are an assumption.
- **Fitness function:** A latency check in CI against the fixture.

---

## 5. Assumptions, open questions, and tensions

**Assumptions (A)**
- **A-1:** The three candidates are at *proposal* granularity. Exact CLI flags, the
  on-disk location/format of the living system spec, and the precise coherence
  checks `compass analyze` performs are not yet designed; this document specs
  *behaviour and constraints*, not the implementation.
- **A-2:** "Scenarios" (the shared `spec.feature.md` artifact) are the substrate of
  the living system spec, per `comparison.md:108-112`.
- **A-3:** Performance targets in NFR-PERF-001 are inferred, not sourced.

**Open questions (OQ) — tagged with who can likely answer**
- **OQ-1 (framework owner):** Where exactly is the boundary between `compass
  analyze` (coherence) and `compass check` (evidence exists/valid/traces) so they
  do not duplicate? (BR-006, Feature 1 final scenario.)
- **OQ-2 (routing-policy owner):** At what blast-radius / route conditions is
  `compass analyze` promoted from advisory to a gate, and where is that encoded in
  `governance/routing-policy.yml`? (BR-007.)
- **OQ-3 (spec/methodology owner):** How does the living system spec reconcile
  superseded or conflicting scenarios across tasks — archive (OpenSpec-style) or
  merge? (BR-008, Feature 2 supersession scenario.)
- **OQ-4 (framework owner):** What are the real latency budgets for `compass next`
  and `compass analyze`? (NFR-PERF-001.)

**Tensions to keep visible**
- **T-1:** The legibility budget (BR-005) versus the surface added by two verbs and
  one artifact. The proposal's mitigations (BR-008, BR-009, BR-011) are the controls;
  NFR-LEG-001 is how we keep them honest. Track the concept count as these land.

---

*Traceability note: every BR cites a `comparison.md` line range; every Feature
groups scenarios under the BR(s) they verify; every NFR cites its source BR.
Glossary terms are used verbatim throughout.*
