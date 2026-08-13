# Glossary

Every word and every id prefix Compass uses, with what it means.

**This page is generated** from `governance/terminology.yml`. Edit that
file, not this one - a drift guard fails the build if the two disagree.

## Codes

The short ids that appear in artifacts. If you have met one in a spec or
a pull request and wondered what it was, it is here.

### `ADR-`

Architecture decision record. A DD- promoted to a standing decision about the system rather than about one issue - it outlives the issue and constrains later ones.

**Refers to:** One numbered file under architecture/decisions/.

**Appears in:** `architecture/decisions/`

**Related:** `DD`

### `BF-`

The retired spelling of FU-. Still read by the Definition-of-Done tag parser so archived verification reports keep resolving.

**Refers to:** A follow-up. Same referent as FU-.

**Appears in:** `.compass/work/ (archive)`

**Related:** `FU`

### `CLM-`

Claim id. A public statement the product marketer intends to make. Every claim must trace to a passing scenario before the issue ships; the claims gate blocks on it.

**Refers to:** One planned public claim.

**Appears in:** `positioning.md`, `launch-readiness.md`, `task.yml claims[].id`

**Related:** `TRC`, `launch-readiness`

### `DD-`

Design decision. Numbered within one design.md: what was chosen, what was rejected, and why. A decision with no alternative recorded is not yet a decision.

**Refers to:** One decision inside a single issue's design.

**Appears in:** `design.md`

**Related:** `ADR`, `design`

### `EV-`

Evidence id. Identifies one typed record in the issue's evidence registry that clears a quality gate. One record can clear several gates. The accepted types are fixed by guardrails.yml; a gate that requires a mechanical type cannot be cleared with a written note.

**Refers to:** One typed evidence record.

**Appears in:** `task.yml evidence[].id`, `gates[].evidence`, `verification-report.md`

**Related:** `quality-gate`, `evidence`

### `FU-`

Follow-up id. Ceremony this issue owes after an expedited ship - the hotfix's promoted scenario, a de-scoped artifact. Not "any outstanding work": a newly found defect gets its own issue named by slug. A follow-up may carry target_task, naming the issue whose ship it blocks.

**Refers to:** One outstanding piece of ceremony this issue owes.

**Appears in:** `task.yml follow_ups[].id`, `verification-report.md`

**Related:** `follow-up`, `definition-of-done`

### `INT-`

Intent id. The "why" end of the traceability chain - the outcome the work is meant to produce, sourced from the PRD's desired outcome, the UI contract, or the issue description. A goal, not a requirement; the requirement is the scenario.

**Refers to:** A stated desired outcome.

**Appears in:** `prd.md`, `acceptance-criteria.md`, `task.yml scenarios[].intent`

**Related:** `TRC`, `prd`

### `RG-`

The retired spelling of RP-. Kept in archived records, which keep the id that fired.

**Refers to:** A routing policy rule. Same referent as RP-.

**Appears in:** `.compass/work/ (archive)`

**Related:** `RP`

### `RP-`

Routing policy rule. One rule in routing-policy.yml that biases or constrains the computed delivery approach. RP-SHAPE and RP-ADV are soft - they bias the candidate. RP-FLOOR, RP-CAP, RP-GATE and RP-ROLE are hard - they constrain the result. RP-REQUIRE attaches a gate without raising a minimum.

**Not:** A guardrail. `guardrail` means one of the five hard rules cleared with evidence; a routing rule constrains which delivery approach you end up with. The prefix said RG- until 3.0.0, which is why this distinction needs stating.

**Refers to:** One rule in the routing policy.

**Appears in:** `routing-policy.yml`, `delivery-approach.md`, `task.yml policy_rules_fired[].id`

**Related:** `routing-policy`, `delivery-approach`, `guardrail`

### `RS-`

The retired spelling of RP- for the soft rules. Same replacement, same reason.

**Refers to:** A routing policy rule. Same referent as RP-.

**Appears in:** `.compass/work/ (archive)`

**Related:** `RP`

### `SCN-`

The retired spelling of TRC-. Still present in shipped examples and read wherever TRC- is. TRC- is canonical because the parser's anchor is the literal keyword `traceability id:`, and because SCN- presumes every traced item is a Given/When/Then - a non-functional requirement can be traceable and testable without being a scenario.

**Refers to:** The traced item. Same referent as TRC-.

**Appears in:** `examples/`

**Related:** `TRC`

### `TRC-`

Traceability id. The join key of the traceability chain: code traces to a TRC- id, which traces to an INT- id. It names the chain, not one node on it - changed_files, claims, evidence records and Definition-of-Done tags all point at it.

**Refers to:** The traced item, normally a scenario.

**Appears in:** `acceptance-criteria.md`, `task.yml scenarios[].id`

**Related:** `INT`, `EV`, `SCN`

## Terms

### acceptance-criteria

The collective term: the set of scenarios for an issue. Executable where a BDD runner is configured.

**Related:** `scenario`, `definition-of-done`

### adr

Architecture decision record: one real decision, the alternatives considered, the consequences. Only written when there was a decision.

**Related:** `design-doc`

### assessment

The four-dimension judgement triage produces - risk, familiarity, size and goal, plus the domain labels. It is the only judgement field in the issue spine; everything below it is computed from it deterministically.

**Not:** A choice of process. The assessment is read; the delivery approach is computed from it by `compass approach evaluate`.

**Related:** `triage`, `delivery-approach`, `navigator`

### backlog

Two senses, both standard: the workflow state an issue starts in, and the list of deferred slices and follow-ups. Context disambiguates, as it does on every real team.

**Related:** `workflow-state`, `follow-up`

### blocked

A flag, not a state - an issue is blocked while in-progress or in-review. Carries a reason.

**Related:** `workflow-state`

### board-column

A user-defined view column (Design, UAT, Staging...). Maps to exactly one workflow state so gates keep firing regardless of board shape.

**GitHub:** Project column / status field

**Related:** `workflow-state`

### bug-fix

A defect in existing behaviour, not live-urgent. Starts from a bug report; the failing reproduction test is written before the fix.

**Related:** `bug-report`, `issue-type`

### bug-report

The intake for a bug fix: observed behaviour, expected behaviour, reproduction steps.

**Related:** `bug-fix`

### canary

Releasing to a small slice of traffic/users first, watching SLIs.

**Related:** `rollout-plan`, `sli`

### definition-of-done

The gate before shipping: acceptance criteria pass, applicable guardrails clear, every box backed by evidence.

**Also:** DoD

**Related:** `quality-gate`, `evidence`

### definition-of-ready

The gate between requirements and design/build: acceptance criteria exist, ambiguities resolved, PRD reviewed where one exists. Trivially satisfied for a quick fix.

**Also:** DoR

**Related:** `quality-gate`, `workflow-state`

### delivery-approach

The chosen shape for an issue: which artifacts exist, which gates apply, solo or parallel. Deterministic - same triage plus same policy always gives the same approach.

**Related:** `triage`, `quality-gate`

### design-doc

The high-level design (HLD): approach, system context, components, interfaces, data model, cross-cutting concerns - with sequence diagrams, named design patterns, and illustrative code where they add clarity.

**Also:** HLD

**Related:** `lld`, `adr`, `operability`

### dora-metrics

Lead time, deployment frequency, change failure rate, MTTR - what the process-impact telemetry measures to ask whether the process itself pays off.

**Related:** `retrospective-signal`

### error-budget

The unreliability an SLO allows. Paces rollout speed on initiatives: budget spent means slow down.

**Related:** `slo`, `rollout-plan`

### evidence

A recorded, typed artifact that clears a gate: a test run, a review, a sign-off. A claim without evidence clears nothing.

**Related:** `guardrail`, `definition-of-done`

### feature

A self-contained change with its own acceptance criteria that does not warrant a full PRD. Unqualified "feature" always means this issue type.

**Not:** A feature file (the Gherkin artifact) - always say 'feature file'.

**Related:** `issue-type`, `feature-file`

### feature-file

A Gherkin file grouping the scenarios for one capability (the `Feature:` keyword). The extraction target for executable acceptance criteria.

**Not:** The feature issue type - unqualified 'feature' means the issue type.

**Related:** `scenario`, `step`, `acceptance-criteria`

### feature-flag

A runtime switch decoupling deploy from release.

**Related:** `rollout-plan`

### first-slice

The 80/20 cut recorded in a PRD: the slice of an initiative that ships first because it delivers most of the value, with what deliberately waits stated beside it. Design and work breakdown follow the first slice, not the whole PRD.

**Related:** `prd`, `slice`, `initiative`

### follow-up

Work owed after an expedited ship (the hotfix's promoted scenario, the optional postmortem). Tracked with a state pair: outstanding (not yet discharged) and resolved. An issue with an outstanding follow-up does not fully close; `compass follow-up resolve` discharges one.

**Not:** v1 called this a 'backfill', with states 'owed' and 'paid'.

**Related:** `hotfix`, `backlog`

### guardrail

A hard rule cleared with evidence; a failed guardrail stops the work. Few by design. Plain statement of the five: every change lands with a passing test that covers it; acceptance criteria exist before the code is written; every change traces to a stated reason; claims need evidence; a human signs off on the irreversible.

**Related:** `strategy`, `quality-gate`, `evidence`

### hotfix

A live-incident fix, expedited: reproduce, fix, ship, then pay the follow-up (promote the reproduction into proper acceptance criteria; optional postmortem).

**Related:** `incident`, `follow-up`, `postmortem`

### incident

The intake that triggers a hotfix: what broke in production, impact, severity. SRE sense of the word.

**Related:** `hotfix`, `postmortem`

### initiative

A body of work significant enough to need a PRD, delivered across multiple milestones. Owns the PRD, the design, the first-slice (80/20) decision, and the rollout strategy.

**Not:** An epic - that word is dropped; one word per concept.

**GitHub:** Project

**Related:** `milestone`, `prd`, `slice`

### intent

The outcome a change is meant to produce - the "why" end of the traceability chain, sourced from the PRD's desired outcome, the UI contract, or the issue description. A goal, not a requirement: the functional requirement is the scenario.

**Not:** A restatement of the request. "Add a CSV export" is a request; "let finance self-serve" is the intent, and it may need filters and permissions the request never mentioned.

**Also:** The product owner's entry point, `/compass:intent`, captures it.

**Related:** `prd`, `scenario`, `traceability`

### issue

The atomic tracked unit of work: one triaged piece of work, one delivery approach, shipping as one PR or a small PR series. Carries a type, labels, and a workflow state.

**Not:** A 'task' - that word survives only as machine state, never prose.

**GitHub:** Issue

**Related:** `sub-issue`, `issue-type`, `label`, `workflow-state`

### issue-type

The classification triage assigns to an issue: quick fix, bug fix, hotfix, feature, or spike. Together with labels it determines the delivery approach - which artifacts exist and which gates apply.

**GitHub:** Issue type

**Related:** `issue`, `triage`, `delivery-approach`, `label`

### label

A plain-word tag on an issue carrying classification and risk surface. Local-first (strings in the issue file); synced 1:1 with GitHub labels when connected. Labels never track workflow state.

**GitHub:** Label

**Related:** `label-rule`, `issue`

### label-rule

The deterministic consequence of a label, declared in policy: security/payments/personal-data/migration require a security review; user-facing requires a rollout plan; breaking-change requires human sign-off; ops-surface requires the operability section. Triage suggests labels, the human confirms; the rules then apply mechanically.

**Related:** `label`, `quality-gate`

### lld

Low-level design: optional per-component detail on initiative-scale work only. Empty is a valid state.

**Related:** `design-doc`

### milestone

A shippable checkpoint within an initiative: a coherent bundle of delivered issues with a review point. Every milestone leaves the system releasable.

**GitHub:** Milestone

**Related:** `initiative`, `issue`

### navigator

The agent that runs triage: reads the four assessment dimensions, hands them to the CLI, and writes the delivery-approach record. It assesses; it does not choose a process.

**Not:** A decision-maker about ceremony. The approach is computed from the assessment by `compass approach evaluate`, which is the determinism boundary.

**Related:** `triage`, `assessment`, `delivery-approach`

### operability

The design section answering "what tells us this works in production?": the SLIs/SLOs the change affects, the alerts that watch them, runbook updates where the ops surface changes. Required by the ops-surface label rule; always present on initiatives.

**Related:** `sli`, `slo`, `runbook`

### postmortem

Blameless incident review - an optional follow-up artifact on a hotfix.

**Related:** `incident`, `follow-up`

### pr

The unit of landing code. Small, trunk-based PRs preferred.

**GitHub:** Pull request

**Related:** `issue`, `ship`

### prd

Product requirements document: problem, users, goals, non-goals, success metrics, constraints, open questions, and the first slice (the 80/20 cut). Iterated through review before design begins. User stories are welcome inside it as a format; acceptance criteria are derived from them.

**Related:** `initiative`, `first-slice`, `requirements-review`

### quality-gate

A check that must pass before an issue moves state. Which gates apply depends on the issue type and labels.

**Related:** `workflow-state`, `definition-of-ready`, `definition-of-done`

### quick-fix

A small, low-risk change on familiar ground. Produces a test and a PR - nothing else exists for it.

**Related:** `issue-type`

### receipt

The per-issue proof summary rendered from the spine and the evidence registry: the assessment, the delivery approach, the gates and what cleared them - one screen, shareable as-is.

**Not:** Evidence - evidence is the typed records that clear gates; the receipt is the read-only summary that cites them.

**Related:** `evidence`, `quality-gate`

### requirements-review

The review pass that hardens requirements before design or build: ambiguities resolved into recorded decisions, contradictions and gaps closed, the PRD reviewed where one exists. Satisfying it is what makes an issue ready. v1 called this "Clarify".

**Related:** `prd`, `definition-of-ready`, `acceptance-criteria`

### retrospective-signal

Compass's cross-issue self-check: is triage consistently over- or under-sizing the process? Advisory, surfaced in retro language. v1 called this "calibration".

**Related:** `dora-metrics`, `triage`

### rollback-plan

The recorded way back if the change misbehaves in production.

**Related:** `rollout-plan`

### rollout-plan

How the change reaches users safely: feature flags, canary or incremental rollout, and the rollback plan. Required by label rule on user-facing work; always present on initiatives.

**Related:** `feature-flag`, `canary`, `rollback-plan`

### runbook

Operational how-to for the service. Updated as an initiative-scale output when the ops surface changes.

**Related:** `operability`

### scenario

The atomic unit of acceptance: one behaviour, one Given/When/Then, one executable test. Everything traces to scenarios.

**Related:** `feature-file`, `step`, `acceptance-criteria`

### ship

Merging and releasing the change: the PR lands, follow-ups are recorded, the derived system spec accretes. v1 called this "Land".

**Related:** `pr`, `rollout-plan`

### sli

Service level indicator - a measured signal of service health (latency, error rate, availability).

**Related:** `slo`, `operability`

### slice

An independently shippable vertical cut of a feature or initiative, with its own acceptance criteria and its own PR. The bar: every slice leaves the system releasable.

**Related:** `sub-issue`, `milestone`

### slo

Service level objective - the target an SLI must meet. Implies an error budget.

**Related:** `sli`, `error-budget`

### spike

Time-boxed exploration whose output is knowledge, not shipped code. Records the question, the timebox, and a conclusion: discard, graduate (a fresh issue owns any real work), or defer. Nothing ships from a spike.

**Related:** `issue-type`

### step

A single Given/When/Then line, bound to a step definition in the project's codebase.

**Related:** `scenario`

### strategy

A strong default you can step off with a recorded reason. Assessed by a reviewer, never mechanically blocking. TDD and BDD are strategies; the outcomes they serve are guardrails.

**Related:** `guardrail`

### sub-issue

The breakdown unit within an issue or initiative. A slice is tracked as a sub-issue.

**GitHub:** Sub-issue

**Related:** `issue`, `slice`

### traceability

The chain that makes a change accountable: code traces to a TRC- id, which traces to an INT- id. Maintained as the work happens, not reconstructed at the end. It is one of the five guardrails, and the thing the `TRC-` prefix is named after.

**Not:** A report produced at the end. A chain assembled after the fact records what someone remembered, not what happened.

**Related:** `scenario`, `intent`, `acceptance-criteria`

### triage

Sizing up incoming work: risk, size, familiarity, urgency - producing an issue type, labels, and a delivery approach. The human judgement step; everything after it is mechanism.

**Related:** `delivery-approach`, `label`, `issue-type`

### workflow-state

The fixed semantic lifecycle Compass owns: backlog, ready, in-progress, in-review, done. Gates attach to the transitions; transitions are earned (evidence), not dragged. Board columns are a user-defined projection - every custom column maps to exactly one state.

**Related:** `quality-gate`, `board-column`, `blocked`
