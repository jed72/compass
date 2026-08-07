# Compass - Methodology

This is the canonical design document for Compass. Every other file in the
repository is downstream of this one. If a command, agent, skill, or template
ever contradicts this document, this document wins.

---

## 1. The problem with one-size-fits-all SDD

Spec-driven development frameworks tend to pick a ceremony and apply it to
everything. A typo fix in a help string goes through the same specify →
clarify → plan → issues → implement → review pipeline as a new billing system.
Two failure modes follow:

- **Ceremony fatigue.** When the process costs more than the change, people
  route around it. The framework gets used for the demo and abandoned for the
  actual work.
- **Under-protection.** The same fixed pipeline that is too heavy for a typo
  is often too light for a database migration. A flat process cannot be
  correctly calibrated for both ends at once.

The frameworks that try to fix this usually add *levels* - a fixed ladder of
five or six tiers. That helps, but a ladder is still a one-dimensional answer
to a multi-dimensional question. "How risky" and "how big" and "is this new
code or old code" and "who is asking" are different axes. A migration that
touches one file is small but not safe. A greenfield prototype is large but
low-risk. A marketing claim and an engineering issue enter the same product
from completely different doors.

Compass treats process intensity as something to **compute per issue**, not
select from a menu.

---

## 2. The core idea: read the familiarity, then route

Every Compass issue begins with **Frame** - a triage step that reads four
context dimensions and produces a **Route**: a tailored pipeline with the
right ceremony, the right gates, the right agent topology, and the right
artifacts for *this* change. The component that does this is the **Needle**.

The four dimensions triage reads:

| Dimension | Question | Range |
|---|---|---|
| **risk** | If this goes wrong, how bad and how wide? | trivial · contained · cross-cutting · critical |
| **Familiarity** | Is this new code or existing code, and how well is it mapped? | greenfield · brownfield-mapped · brownfield-unmapped |
| **Magnitude** | How much work is this? | atomic · small · standard · large · product |
| **Intent & role** | Who is invoking, and what outcome are they really after? | engineer · product owner/manager · product marketer · designer · QA |

Triage does not just classify - it explains. Its output, `delivery-approach.md`, is an
auditable record: here is what I assessed, here is the route I chose, here is
what ceremony applies, **here is what I am skipping and the explicit reason it
is safe to skip.** De-scoping is a first-class, written decision, not an
accident.

Routing is **advisory until confirmed**. The human can override triage,
and a routing guardrail can override the human (changing a routing guardrail
means amending `governance/routing-policy.md`, not overriding a route). What
routing is *not* allowed to do is silently cross a guardrail - see §4.

---

## 3. The pipeline: universal vocabulary, adaptive depth

Every route is the same eight phases in the same order. What changes between
routes is how much each phase costs, which gates are enforced, and whether a
phase collapses to a single sentence or expands into a swarm.

```
Frame → Specify → Clarify → Plan → Distribute → Build → Verify → Land
```

| Phase | What happens | What adapts |
|---|---|---|
| **Frame** | Triage reads the four dimensions and writes `delivery-approach.md`. Roles in play are identified. | Always runs. Cost: ~minutes even on the heaviest route. |
| **Specify** | Behaviour is captured as BDD scenarios (Given/When/Then). Greenfield: discovery. Brownfield: *blueprint distillation* - reverse-engineer current behaviour into scenarios before changing it. | One scenario vs. a full feature set. Discovery depth. |
| **Clarify** | Ambiguities resolved. The spec is QA'd against itself and against governance. | Skipped on quick fix when the spec is a single unambiguous scenario; skipped on Spike entirely. |
| **Plan** | Technical plan. Governance check. Independent work units identified; worktree/swarm topology decided. | Collapses to "edit this file" on quick fix; expands to a distribution map on initiative. |
| **Distribute** | Git worktrees created; agent swarm assigned, one stream per independent unit. | Skipped entirely on solo work. |
| **Build** | TDD red → green → refactor (the default strategy). Each agent owns its scenarios. | Test surface scales with risk; the red-before-green strategy is suspended on Spike. |
| **Verify** | BDD scenarios run as acceptance tests; TDD suite runs; review dimensions applied; gates checked. | Number of review dimensions and gates scales with the route. |
| **Land** | Worktrees integrated, regression run, living docs updated, any de-scoped artifact backfilled. | Integration is trivial for solo, a coordinated merge for swarms. |

The vocabulary never changes, so a person who has run one Compass issue can
read the artifacts of any other. The *weight* changes.

Two of the phase transitions carry an explicit checklist gate, so "ready" and
"done" are never a judgement call. **Clarify → Plan** is guarded by a
**Definition of Ready** - the spec traces to intent, behaviour is
Given/When/Then, traceability ids are assigned, no open ambiguities, the route
still fits. **Verify → Land** is guarded by a **Definition of Done** - every
scenario passes, the suite is green, coverage meets the guardrail floor, no
lint errors, traceability intact. The checklists live at the foot of
`requirements-review.md` and `verification-report.md` respectively; on routes where
Clarify collapses, the Definition of Ready is satisfied by construction.

**The Definition of Done is a typed gate, not a narrative.** Every unchecked
DoD item must carry a typed inline tag pointing at the evidence that would
clear it - `(evidence: EV-<id>)` referencing an entry in the issue's typed
evidence registry, or `(backfill: BF-<id>)` referencing an owed follow-up - or
be ticked `[x]` when a human has actually done the work. Bare unchecked items
fail `compass check`'s `dod-evidence-typed` rule. This is G4 (evidence, not
assertion) expressed at the checklist level: a written note in a devlog is
not evidence, and the typed-tag form is what makes the DoD mechanically
checkable rather than aspirational.

---

## 4. Governance: guardrails and strategies

Compass is governed by two kinds of thing, and keeping them separate is what
lets the framework be rigorous *and* adaptive *and* light at the same time.

- **Guardrails** are few, hard, checkable, and blocking. The things that must
  never happen. A guardrail is cleared only with evidence, and a failed
  guardrail stops the work. Triage adapts ceremony around guardrails; it
  never crosses one.
- **Strategies** are many, soft, directional, and assessed. How the team tends
  to work and what it prefers. A strategy *biases* a decision - it does not
  block one. Triage, a route, or a human can depart from a strategy for a
  given issue; the departure is recorded, not punished.

The full set lives in `governance/`. This section is the why; that directory
is the what.

**The five default guardrails.** These ship active with the framework - they
are the floor under every route, including the lightest and the most
exploratory:

1. **G1 - Tested before it lands.** No code reaches `main` without a passing
   automated test it traces to.
2. **G2 - Acceptance defined before it is built.** No code is written that no
   stated, checkable acceptance criterion describes.
3. **G3 - Traceability holds.** code → acceptance criterion → intent, and
   public claim → backing criterion, maintained continuously.
4. **G4 - Evidence, not assertion.** A guardrail is cleared with artifacts and
   command output, never a claim.
5. **G5 - A human signs off on the irreversible.** Changes that can lose data,
   move money, or breach auth or privacy get an explicit human checkpoint.

**BDD and TDD are default *strategies*, not guardrails - and this is the
deliberate move that keeps Compass from being a sledgehammer.** The hard line
is the *outcome*: code is tested (G1), acceptance is stated and checkable
(G2). The *form* - Given/When/Then scenarios, red-green-refactor - is the
shipped-on, strong default *way* to reach that outcome. The distinction has
teeth: a one-character typo fix still has to satisfy G1 (tested before it
lands), but it does not have to perform the full red-before-green ritual to do
so; and the **spike** suspends the TDD strategy entirely so exploration
is not throttled - while G1 still applies to anything a spike graduates into
production. Old frameworks made the ritual itself non-negotiable; Compass makes
the *outcome* non-negotiable and the ritual a strong, suspendable default.

**The conflict rule.** A guardrail always beats a strategy. Guardrail-vs-
guardrail should not happen - if it does, the guardrail set has a bug.
Strategy-vs-strategy is resolved by context: triage picks based on the
route, or a human picks. This replaces the older idea of a single supreme
"constitution": there is no supreme document, there is a small hard set that
wins and a larger soft set that guides.

**Governance is a gradient, not a threshold.** A valid, complete governance
state is "the shipped default guardrails, the shipped default strategies, and
nothing project-specific yet." A team starts there - `/compass:init` is
*optional*, and `/compass:frame` works on day one against the shipped defaults -
and *accretes* project strategies as it forms opinions, adding a guardrail
only when it hits something that must never recur. That gradient is what makes
the lightweight path real rather than a bolted-on exception.

If a route ever appears to require crossing a guardrail, that is a bug in the
route definition, not a license.

**Fitness functions and intermittent-test integrity.** Two v1.1.0 additions
extend the governance discipline without adding to the hard guardrail count.
*Fitness functions as project guardrails* - codified in
`architecture/decisions/ADR-009` - let a project declare a check in
`governance/guardrails.yml` with `check: command-passes` plus the command to
run; `compass check` runs the command at Verify and refuses to clear the gate
on non-zero exit. This is how a team encodes project-specific invariants ("the
build is under N MB", "no API endpoint regresses past P95 = X ms") *as
guardrails*, not as advisory strategies. *Intermittent-test integrity* -
detailed in `governance/strategies.md` §6 and operationalised through
`governance/quarantine.yml` - pairs with G4 (evidence, not assertion): the
`no-trusted-rerun` rule refuses to clear a test-run when a rerun was needed
unless the root cause is fixed or the test is explicitly quarantined with a
tracking issue. A test that reruns to green is the classic way a guardrail
becomes silently advisory; the rule closes that drift surface.

*Writing for a cold reader* - strategy S7 - extends persistence over
conversation (S4) by one step. S4 says put the decision on disk. S7 says put
enough on disk that the next reader does not need the conversation you had
while writing it: context before detail, no reference the reader cannot
resolve, and no length that stops them finishing. It is the strategy that
makes the rest of the framework's artifacts worth persisting, and it applies
to commit messages and pull-request bodies as much as to a spec. Like every
strategy it is assessed, not checked: the reviewer raises it at Verify under
the `clarity` dimension, and it fails nothing.

---

## 5. One spec, many roles: roles as full citizens

Compass is not an engineering framework with hooks for other people bolted on.
The four non-engineering roles are full participants with their own entry
points, their own vocabulary, and their own artifacts that plug into the
*same* pipeline.

The mechanism that makes this work is the **shared scenario file**. The BDD
spec is the one artifact every role reads - each through their own perspective:

- The **product owner / manager** reads it for *intent fidelity*: do these
  scenarios actually deliver the outcome in the brief?
- The **product marketer** reads it for *claims*: every line of launch copy
  must point at a scenario that backs it.
- The **engineer** reads it for *tests*: scenarios become the acceptance
  suite and seed the TDD cycle.
- **QA** reads it for *coverage*: which scenarios are exercised, which edges
  are not.

Role entry points:

| Role | Entry point | Primary artifact | Where they gate |
|---|---|---|---|
| Product owner / manager | `/compass:intent` | `prd.md` (problem, outcome, success signals, constraints) | Reviews the spec for intent fidelity before Plan. Curates the product strategies in `governance/strategies.md`. |
| Product marketer | `/compass:position` | `positioning.md`, `launch-readiness.md` | Gates Land: no launch claim ships without a passing scenario behind it. Curates the voice & positioning strategies. |
| Designer | `/compass:design` | `ui-contract.md` | UI contracts are written as scenarios and flow into the define stage. |
| Engineer | `/compass:frame` and the pipeline | `delivery-approach.md`, `design.md`, code | Owns Build. Curates the engineering strategies. |
| QA | participates in `/compass:verify` | `verification-report.md` | Owns the Verify gate. |

The product owner enters *upstream* of the spec; the marketer works *parallel*
to it; the designer feeds *into* it. None of them are downstream consumers of
a finished engineering process. They are in the pipeline.

A worked example of the same scenario seen four ways lives in
`docs/roles-guide.md`.

---

## 6. Governance governs the router

The genuinely novel move in Compass is that governance does not just shape the
*code* - it shapes the *router*. `governance/routing-policy.md` applies the
same guardrails-and-strategies split to triage itself:

- **Routing guardrails** *bound* what triage may do. A routing guardrail
  can force a route to be at least a certain weight ("anything touching auth
  or payments is floored to initiative regardless of size"), cap how far
  it may scale up ("never swarm a critical-risk change"), or staple on
  a gate no route may remove. Triage cannot route around these, and a
  human cannot override them per-issue - changing one means amending the file.
- **Routing strategies** *bias* what triage does by default - the route
  shapes it reaches for, how it breaks ties ("when size is unclear,
  estimate up"; "prefer the lightest route that still clears the guardrails").
  Triage starts here and tunes; a departure is recorded in `delivery-approach.md`.

This is the answer to the obvious objection to any adaptive framework - *"if
the process can flex, what stops it flexing to nothing?"* The routing
guardrails are what stop it. The flex is real and bounded, and any `delivery-approach.md`
shows not just the route chosen but which routing guardrails fired and why. An
adaptive framework gives up the simple integrity story of a fixed pipeline;
this file is where Compass buys that integrity back.

### The determinism boundary - judgement vs mechanism

There is a line running through Compass, and naming it precisely is what keeps
"adaptive" from meaning "inconsistent." On one side of the line is
**judgement**: triage reading the four context dimensions - how risky is
this, how big, new code or old, what outcome is really wanted. That cannot be
mechanized, and it must not be: that judgement *is* the adaptivity. A framework
that reduced it to a deterministic classifier would just be a fixed tiered
ladder wearing a costume.

On the other side of the line is **mechanism**: everything that happens once
the assessment exist. Composing the candidate route, applying the floors and
caps, stapling the immovable gates, assembling the gate set - that is pure
function. Same assessment plus same policy produce the same route, every time,
for every agent and every human. And the checkable guardrails - is every
scenario tested, does every changed file trace to a criterion, does every gate
have evidence - are mechanism too.

Compass puts the mechanism in a CLI (`cli/compass`) so it is *actually*
deterministic, not deterministic-in-principle: `compass approach evaluate` runs
`routing-policy.yml` against an issue's assessment; `compass check` runs the
`guardrails.yml` checks against the issue's `task.yml` and evidence. Triage
still produces the assessment - judgement stays judgement - but it no longer
*also* composes the route in its head, where two agents could reason to two
different answers. It hands the assessment to the mechanism. The machine-readable
files (`routing-policy.yml`, `guardrails.yml`, the `task.yml` spine) exist
precisely so the mechanism *can* be mechanical. This is the boundary the "kit"
is built around - see §9.

### The feedback loop - the framework checks its own calibration

A framework whose central claim is *right-sizing the process* owes an answer
to the obvious follow-up: **is the right-sizing any good?** Judgement that is
never checked against outcomes is just assertion with extra steps. So the
Needle has a feedback loop.

The mechanism is small. When the familiarity reading turns out wrong, the honest
response is a **re-assess** - re-score the four dimensions mid-issue - and every
re-assess is *recorded*: `compass approach evaluate --write` detects that the route
changed and appends an entry to `task.yml`'s `reframes` log, with the reason
(`--reason "..."`). One re-assess is an anecdote. The log across every issue is
data: `compass retro` aggregates it and reports the pattern - are
re-frames mostly *up* (triage reads size and risk low - it is
under-sizing) or *down* (it reads risk high - it is over-sizing)? That is the
framework holding a mirror to its own judgement layer. It does not gate
anything; it tells the team whether `routing-policy.yml` or the Frame rubric in
`approaches/rubric.md` needs tuning. The adaptivity is judgement (§6's first half),
and this is how judgement stays honest over time - measured, not assumed.

---

## 7. Agent swarms and worktrees

Parallelism in Compass is decided in **Plan** and executed in **Distribute**.

The Plan phase produces a **distribution map**: the set of work units, which
are independent, and which share surface area. Independence is determined from
the scenario file and the technical plan - units that touch disjoint code and
satisfy disjoint scenarios can run in parallel.

Distribute then sets up the topology:

- **Solo** (1 stream) - quick fix and most Standard routes. No worktree; work
  happens on the current branch. Distribute is a no-op.
- **Pair** (2–3 streams) - larger Standard routes. One worktree per stream.
- **Swarm** (4+ streams) - initiative. One git worktree per stream, one
  subagent per worktree, plus an **orchestrator** agent that does not write
  feature code - it monitors progress, detects when two streams are about to
  collide, and owns the integration at ship time.

Each worktree is an isolated checkout, so a swarm agent can run a full TDD
cycle - including a failing test suite - without destabilising siblings. The
orchestrator integrates at ship time, runs regression across the combined result,
and is the only agent allowed to resolve cross-stream conflicts.

Swarm topology is itself a routed decision: triage's size and blast
radius assessment set the default, the distribution map sets the count, and a
routing guardrail can cap it (e.g. "never swarm a critical-risk change -
the coordination risk outweighs the speed").

Scripts: `scripts/swarm.sh` creates the worktrees and launches agents;
`scripts/integrate.sh` lands them.

---

## 8. The five reference shapes

Routes are *composed* from the dimension assessment, but in practice most issues
land near one of five reference shapes. These are starting points triage
tunes, not a fixed ladder.

| Route | Typical reading | Pipeline shape |
|---|---|---|
| **quick fix** | atomic/small · trivial/contained · brownfield-mapped | Frame → Specify (1 scenario) → Build → Verify. Clarify, Plan, Distribute collapse. Still tested before it lands (G1); the red-before-green TDD strategy still applies. One gate. |
| **Standard** | standard · contained · either familiarity | Full pipeline, solo or pair. Spec is a small feature set. Governance check in Plan. Two gates. |
| **initiative** | large/product · cross-cutting · greenfield/unmapped | Full pipeline at full weight. Governance check, full BDD discovery, distribution map, agent swarm across worktrees. All gates. |
| **Hotfix** | critical · atomic/small · brownfield | Reproduce-first: a failing regression test *is* the spec. Expedited Build, but a mandatory post-incident follow-up of `delivery-approach.md` and a real scenario before the issue is closed. All Verify gates, no exceptions. |
| **Spike** | intent is exploration - "I cannot frame this well enough yet" | Frame (light) → Explore (TDD strategy suspended; the hook does not block) → Conclude → graduate or discard. **Nothing lands from a Spike** - the only exit that keeps code is graduating, which is re-framing into a real route where the guardrails apply in full. |

Full definitions, including exact gate sets, live in `approaches/`. Spike is the
escape hatch that keeps the lightweight path honest: it exists so exploratory
work is not forced through a delivery-shaped pipeline, and it is safe because
its de-scopes are all backed by the same fact - nothing lands from it.

---

## 9. The three layers: methodology, kit, adapter

Compass is built in three layers, deliberately separated.

- **The methodology layer** - `docs/`, `governance/` (the `.md` files),
  `approaches/`, `templates/`, and `architecture/` (the project's cross-issue
  architectural artifacts - `system-context.md`, `relations.md`,
  `ownership.md`, and ADRs in `decisions/`; Compass ships its own as a
  worked example for adopters). Plain markdown. No tool-specific syntax, no
  code. This layer *is* the framework; it would be valid if neither a CLI
  nor Claude Code existed. It is what you read to *understand* Compass.

- **The kit layer** - `cli/compass`, the machine-readable governance files
  (`governance/routing-policy.yml`, `governance/guardrails.yml`), `schemas/`,
  and the `task.yml` issue spine. This is the *mechanism* side of the
  determinism boundary (§6) made into software: it composes routes, applies
  the routing guardrails, and runs the guardrail checks - deterministically
  and reproducibly. `schemas/` ships executable JSON Schema (draft-07
  `*.schema.json`, with human-readable `*.reference.yml` companions), which
  `compass policy lint` and `compass issue lint` validate against when the
  optional `jsonschema` library is installed - the built-in linter is the
  no-dependency floor and always runs. Gate evidence in `task.yml` is *typed* -
  a `{type, path}` record, not a bare path - so the checks can refuse to clear
  a mechanical gate with a written note. It depends only on Python 3 and PyYAML
  (`jsonschema` is optional); it is **not** Claude-Code-specific, and it is the
  part that makes the framework's checks real rather than aspirational.

- **The Claude Code adapter layer** - `commands/`, `agents/`, `skills/`,
  `hooks/`, `CLAUDE.md`, plus the runtime-specific install surface:
  `bin/compass` (a thin shim that execs the kit-layer `cli/compass`; Claude
  Code adds the plugin's `bin/` to PATH automatically) and `.claude-plugin/`
  (the plugin and marketplace manifests for the `/plugin install` path).
  This wires the methodology and the kit into one specific runtime: slash
  commands invoke phases, subagents are the swarm, skills carry the
  procedural knowledge, hooks enforce the guardrails and the
  red-before-green strategy, and the commands and agents *call the kit* -
  `/compass:frame` runs `compass approach evaluate`, `/compass:verify` runs
  `compass check`. `bin/compass` and `.claude-plugin/` are the
  runtime-specific install wiring; another runtime's adapter would replace
  them with its own equivalent (a shell PATH addition, a different plugin
  manifest, or whatever the new runtime exposes).

Porting Compass to another agent runtime means rewriting only the **adapter
layer** - the methodology layer is already runtime-neutral, and the kit layer
is a plain CLI any runtime can shell out to. `AGENTS.md` is the first step of a
port: a runtime-neutral instruction file. `docs/portability.md` describes the
contract the adapter layer must satisfy and what each layer guarantees.

---

## 10. The flow layer: managing across issues

Everything above is *task-centric* - and that is the right default. Each issue
carries its own route, its own artifacts, its own gates; the pipeline
guarantees a single issue is well-run. But a team runs many issues at once, and
the per-issue pipeline has a structural blind spot: each issue only sees itself.
Nothing inside an issue answers "what is the state of *everything*, and what
needs a human first?"

The **flow layer** fills that gap. It is the delivery-management function -
triage, blockers, status across the board, the periodic digest - expressed as
a **capability**, not a role. Compass deliberately does not add a "delivery
manager" persona with turf and an inbox; it adds `/compass:flow`, a command
anyone can run, backed by the `flow-management` skill.

The distinction matters because of how Compass stores state. Issue state is not
a label a manager sets - it is *inferred from the artifacts on disk* (`design.md`
exists and `verification-report.md` does not ⇒ the issue is in Build). So flow
management has nothing to "own" and nothing to "move." Its whole job is to read
the artifacts, notice what the per-issue pipeline cannot, and surface the right
thing first: guardrail violations (an issue with no `delivery-approach.md`), routes quietly
outgrown, stalls, and owed follow-ups aggregated across every issue. It advises;
it never gates. The gates stay in the per-issue pipeline, next to the evidence.

`/compass:status` looks *down* into one issue. `/compass:flow` looks *across*
all of them. `/compass:flow --digest` writes a dated, append-only digest - the
artifact a team reviews on a cadence, and a natural fit for a scheduled run.

Flow also carries the framework's **calibration signal**. Every re-assess is
recorded in `task.yml`'s `reframes` log (§6's feedback loop), and `compass
calibration` aggregates that log across every issue - is triage
systematically over- or under-sizing routes? Flow surfaces that read alongside
the board and folds it into the digest, because "are we right-sizing process?"
is exactly the cross-issue question no single issue can answer.

## 11. Loading project architecture

Every Compass issue begins with Frame.  As part of Frame, the CLI's internal
`frame_load_architecture` helper scans the project's `architecture/` directory
(when present) and writes a structured record of what it found to
`.compass/work/<task>/architecture-loaded.yml`.

**Why a separate file, not a `task.yml` field?**  `task.yml.readings` is the
*judgement* block - triage's assessment of the four dimensions.  Mechanism-
produced state (what files exist on disk, their hashes) does not belong there.
`architecture-loaded.yml` is the mechanism's output; `readings` is the human's.
Keeping them separate preserves the determinism boundary: same inputs to the
mechanism always produce the same record, independent of triage's
judgement.

**What the record contains:**

```yaml
schema_version: "1.0"
loaded_at: <ISO timestamp>
artifacts:
  - path: architecture/system-context.md
    sha256: <hex>
    type: narrative
  - path: architecture/invariants.yml
    sha256: <hex>
    type: structured
    parsed: <inline YAML content>   # structured artifacts only
adrs:
  - id: ADR-001
    path: architecture/decisions/ADR-001-<slug>.md
    title: <title from frontmatter>
    status: proposed | accepted | superseded
```

The `sha256` per artifact lets downstream agents detect mid-issue drift: if an
architecture file changes after Frame loaded it, the hash will not match, and
the agent knows to ask Frame to reload.  The `parsed` field for structured
files means downstream agents do not need to re-read the file from disk.

**Backward compatibility:** if `architecture/` does not exist the helper
writes the record with empty `artifacts: []` and `adrs: []` and returns
without error.  Every existing project that has not yet adopted the
`architecture/` convention continues to work unchanged.

**Malformed structured files fail loudly:** if `architecture/invariants.yml`
exists but is not valid YAML, Frame raises an error that names the file and
the parse error.  A malformed structured artifact is never silently swallowed -
it would produce incorrect architectural context for every downstream agent in
this issue.

**Downstream agents:** spec-author, planner, and the architect-lens all read
`architecture-loaded.yml` to get persistent architectural context.  The file
survives session boundaries and context compaction - which is the core problem
it solves.  An agent that needs to know whether the project has a stable
service boundary, who owns a given surface, or which decisions are already
recorded reads this file, not the raw `architecture/` tree.
## 12. Cross-issue rework

Each Compass issue owns its own `changed_files` record - a list of paths and
their actions (`added`, `modified`, `deleted`). These records are the code-half
of traceability (G3), but they also carry a cross-issue signal: if issue B deletes
a file that issue A added within a short window, that is rework - issue A's effort
was undone before it delivered lasting value.

`compass rework-scan` reads every `task.yml.changed_files` under a configured
root and detects:

- **Add-then-delete pairs.** File added in issue A, deleted by issue B within the
  configured `window_days` (default 14, from `governance/signals.yml`).
- **Public-surface churn.** Files matching `rework_scan.public_surface_patterns`
  (API routes, proto symbols, etc.) that follow the add-then-delete pattern.
- **Migration pairs.** A migration file matching `rework_scan.migration_paths`
  added by issue A, paired with a semantically related drop migration added by
  issue B in the same window.

**Exit code is always 0.** The scan is a signal, not a gate (Inv-4: Flow
advises, never gates). Detection of rework does not block delivery. The output
surfaces in `/compass:flow --digest` as the "Rework scan" section and is
also written to its own dated artifact at `.compass/flow/rework-<date>.md`
(an append-only record the team reviews on a cadence to decide whether to
act - spawning a sibling issue, filing an ADR, or accepting the churn as
intentional).

Configuration lives in `governance/signals.yml` and is loaded at runtime;
patterns are never hardcoded in the CLI. Projects override by editing their own
`governance/signals.yml` using the same convention as `guardrails.yml` and
`routing-policy.yml`.

## 13. Reframes - feedback signal

A **re-assess** is what happens when triage (or a human) re-reads the
familiarity mid-issue and concludes that the initial route was wrong. Re-framing is
normal and expected - it is the mechanism that keeps process proportionate when
reality turns out to differ from first impressions. What is *not* normal is
absorbing a scope change silently, without filing the re-assess.

### Why absorbed mis-frames matter

When a builder discovers during Build that the issue is larger, narrower, or
differently shaped than Plan described, and works around it without filing a
re-assess, two things happen:

1. **The calibration signal is lost.** `compass retro` reads the
   `reframes:` log across all issues and reports whether triage is
   systematically over- or under-sizing. An absorbed mis-frame - a real scope
   change that was not recorded - makes calibration less accurate. The pattern
   repeats; triage never learns.
2. **The audit trail has a gap.** The issue's `task.yml` says it was a
   `standard` issue; the devlog says scope ballooned. Anyone reading the history
   cannot reconstruct why the issue took longer than Plan said.

### The stop-hook nudge

`hooks/stop.sh` reads `governance/signals.yml`'s `scope_bloat_phrases` list at
runtime and checks each active issue's `devlog.md` against those patterns at
session end. If a scope-bloat phrase appears as a top-level statement in the
devlog (not nested in quotes or indentation) AND no reassess has been filed
after it, the hook emits a nudge to stderr suggesting:

```
/compass:frame --reframe --reason "<what changed and why>"
```

The hook is **non-blocking** - it exits 0 regardless. It nudges; the human
decides.

### compass retro --reassess-debt

`compass retro` includes a **Reframe debt** section in its output when it
finds issues that have scope-bloat devlog signals and no corresponding reassess.
These are listed as "absorbed mis-frames, signal lost" - advisory only. The
command is read-only: it never writes to `task.yml` or any other file (this
is a hard architectural invariant, not a convention).

### The roundtable trigger

Any roundtable outcome that changes a service boundary or migration scope must
end with a re-assess. See `commands/roundtable.md` §"Reframe trigger" for the
exact procedure and example invocation.

### What counts as a filed reassess

A re-assess is filed when `compass approach evaluate --write --reason "..."` runs
and the computed approach differs from the previously recorded one. This appends
an entry to `task.yml.reframes` with `from_route`, `to_route`, `reason`, and
`date`. The stop-hook and calibration both check this field to decide whether
a nudge is appropriate.

**The rule:** if scope grew, file the re-assess. The re-assess is not a failure;
it is the calibration signal working as intended.

### The friction signal - calibrating the ceremony itself

The `reframes:` log answers "did triage mis-*size* the route?" The
**friction signal** answers a different question on the same axis: "did
Compass's own ceremony cost more than it returned on this issue?" - a phase that
fought the work, a gate that demanded ceremony the issue didn't warrant, a
routing default that routed badly, a missing strategy that would have caught a
defect earlier.

It is captured at **Land**, when the gap between what Frame promised and what
Build/Verify actually cost is freshest. `compass _friction-capture` (called by
the Land procedure) assembles a draft `friction:` list in `task.yml` from
signals the CLI already computes - recorded `reframes` and absorbed
reassess-debt become `source: derived` entries - and the author may add one
optional `source: human` line. **Recording nothing is a valid, common
outcome.** Each entry carries a `category` (over-ceremony, under-ceremony,
mis-route, missing-strategy, tooling, docs, other) and, for human entries, a
`proposed_change` describing how the framework could have been configured to
avoid the friction.

`compass retro --friction` aggregates these across every issue, groups
recurring `proposed_change` targets (exact-normalised, never semantic), and
surfaces only those that recur at or above `signals.yml`'s
`friction.recurrence_threshold` (default 2) - a one-off is noise, not a trend.
The output (`--format json` for machine consumers) is what Claude or a human
reads to **draft** a targeted change to `governance/` or the routes.

Three properties keep this on the right side of every Compass line:

1. **It never gates.** Friction is a strategy-class signal, not a guardrail
   (ADR-002 keeps the guardrail count at five). An issue with no friction record
   Lands exactly as one with. `compass retro --friction` is read-only and
   exits 0 always - like `rework-scan` and `flow`.
2. **It never auto-tunes.** The loop produces drafts; a human edits governance.
   Telemetry advises, judgement stays human-side (ADR-001, the determinism
   boundary).
3. **It no-ops cleanly.** Absent a `friction:` block, every command behaves
   exactly as before - a 1.x `task.yml` without the field is valid (ADR-006).

## 14. Design principles (the short version)

1. **Compute the process, don't select it.** Intensity is a function of the
   familiarity, not a menu choice.
2. **Adapt the ceremony and the strategy - never the guardrail.** A few hard,
   checkable limits never flex; the form of how you meet them does.
3. **Outcome is the guardrail; ritual is a strategy.** "Tested before it
   lands" is hard. Red-before-green is the strong default way to get there -
   and Spike can suspend it. That is how rigour stays proportionate.
4. **Governance is a gradient, not a threshold.** Ship the defaults; accrete
   the rest. There is a valid, complete *light* state - `/compass:init` is
   optional.
5. **One spec, many roles.** The scenario file is the shared substrate for
   every role.
6. **De-scoping is a written decision.** If a route skips something, the
   reason is in `delivery-approach.md`.
7. **Governance governs the router.** Routing guardrails bound triage;
   routing strategies bias it. Flexibility is real and bounded.
8. **Evidence over assertion, persistence over conversation.** Artifacts on
   disk, not claims in chat.
