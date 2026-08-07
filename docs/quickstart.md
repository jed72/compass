# Compass - Quickstart

This walks you from an empty machine to a finished first task. It is
deliberately concrete: real commands, in order, with the artifact each one
leaves on disk and what the gates feel like when you hit them. There are three
walkthroughs - an engineer, a product owner, a marketer - because Compass has
five roles and the entry point you use shapes the route the Needle composes.

This document uses Compass's vocabulary: the eight-phase pipeline, the four
dimensions, the default guardrails, the Needle. Each term is introduced as it
comes up, so you can work through this page first and read
`docs/methodology.md` afterwards for the design reasoning behind any of them.

---

## 1. Install

There are two ways in. Pick one.

**The plugin marketplace is the fastest.** No clone, no install script:

```bash
# In Claude Code:
/plugin marketplace add jed72/compass
/plugin install compass@compass
pip install pyyaml      # the CLI's one dependency
```

Enabling the plugin namespaces the commands as `/compass:…`, registers the
hooks, and puts the `compass` CLI on your PATH. Skip to step 2.

**Install from source** if you want to read or edit the framework as you go.
`scripts/install.sh` wires everything in by symlink, so edits to your clone are
picked up live:

```bash
git clone https://github.com/jed72/compass.git
cd compass
pip install pyyaml                    # the CLI's one hard dependency
pip install jsonschema                # optional - turns on full JSON Schema lint
bash scripts/install.sh --global      # or: bash scripts/install.sh  (project-local)
```

`install.sh` symlinks `commands/`, `agents/`, and `skills/` into your Claude
Code config as a `compass` subdirectory (so nothing collides with your own
files) and registers the three hooks - `pre-tool.sh`, `post-tool.sh`,
`stop.sh` - in `settings.json`. It is idempotent: re-running refreshes the
links and never clobbers a file Compass did not create. `--global` makes the
`/compass:*` commands available in every project; `--copy` installs copies
instead of symlinks if you prefer. The CLI's only *hard* dependency is PyYAML -
if it is missing, `compass` says so and exits; `jsonschema` is optional and
turns on full JSON Schema validation in `compass policy lint` and
`compass task lint` (without it the built-in linter still runs - see
`schemas/README.md`).

Unlike the plugin, `install.sh` does **not** modify your PATH. If you want to
call `compass` directly from your shell, add `$COMPASS_HOME/bin` to your
`PATH` (or invoke the CLI as `python3 $COMPASS_HOME/cli/compass`). The slash
commands run the CLI on your behalf, so this only matters when you call it
directly.

Either way, what you have installed is three layers: the **methodology** (the
markdown in `docs/`, `governance/*.md`, `routes/` and `templates/`, read in
place and never copied), the **kit** (`cli/compass`, `governance/*.yml`,
`schemas/` and the `task.yml` spine, which is the deterministic mechanism), and
the **Claude Code adapter** (`commands/`, `agents/`, `skills/`, `hooks/`),
whose commands call the kit underneath. `docs/methodology.md` §9 and
`docs/portability.md` have the full picture; you do not need it to continue.

One thing to know going in: the `pre-tool.sh` hook enforces the red-before-green
TDD strategy. Once Compass is installed, an attempt to edit a recognised code
file with no failing test on record for the current task is **blocked** - exit
code 2, edit denied. That is not a bug to work around; it is the S2 strategy in
service of guardrail G1 (tested before it lands), made physical. The hook is
route-aware: on a **Spike** route the TDD strategy is suspended and the hook
does not block. The rest of this document is, in part, how to work with the
hook rather than against it.

## 2. Frame-and-go - `/compass:init` is optional

There is no required setup step between installing Compass and running your
first task. The **five default guardrails** and the **default method
strategies** ship active with the framework, so `/compass:frame` works against
the shipped `governance/` defaults on day one. Governance is a *gradient, not a
threshold*: "the shipped defaults and nothing project-specific yet" is a valid,
complete governance state - see `governance/README.md`.

`/compass:init` is how a project *accretes* its own governance later, not a
prerequisite. When you have opinions to encode, run it once from the project
root:

```
/compass:init
```

`init` is exempt from Frame - it changes no application code. It:

1. **Copies `governance/`** into the project - `guardrails.md`,
   `strategies.md`, `routing-policy.md` - so the team can extend the shipped
   defaults. It does not make you author anything: the defaults are real,
   in-force content from the moment they land. Adding project guardrails and
   strategies is accretion, done whenever the team is ready.
2. **Creates `.compass/config.yml`** - route defaults, swarm thresholds,
   worktree ceilings. The defaults are sane; `init` confirms them with you.
3. **Creates `.compass/work/`** - where every task's state will live. Note
   that `.compass/work/` **is committed**. It is the audit trail, not scratch.

Until `init` is run, the framework's shipped `governance/` defaults apply
as-is. Init is accretion, not a gate.

---

## 3. First task - the engineer

You are an engineer. A task: add rate limiting to the public API. You start
where every engineer starts - at Frame.

### Frame

```
/compass:frame "Add rate limiting to the public API"
```

The Needle reads four dimensions - that part is judgement - and records them
in `.compass/work/add-rate-limiting/task.yml`. For this task it scores
something like: magnitude `standard` (several files, one or two design
decisions), blast radius `cross-cutting` (a misconfigured limiter degrades
something every API consumer touches), terrain `brownfield-mapped`, role
`engineer`. It tags `touches: [public-api]`.

Then the mechanism takes over. `/compass:frame` shells out to
`compass route evaluate --write`, which applies `governance/routing-policy.yml`
deterministically - composing the candidate route, applying the floors and
caps, assembling the gate set - and folds `route`, `phases`, and `gates` back
into `task.yml`. For this task it lands on **Standard, with the `security`
review dimension turned on because blast radius is cross-cutting**; no routing
guardrail forces a heavier route. The Needle then writes the human-readable
`delivery-approach.md` alongside it. Same readings + same policy would produce this exact
route on any machine - the route is no longer something an agent composes in
its head. `/compass:frame` also drops a `.compass/current-task` pointer so the
CLI and the hooks know which task is live.

It then **presents the route and waits**. Routing is advisory until confirmed.
You read the four readings, you read the de-scope ledger - Standard collapses
nothing major, so the ledger is short - and you confirm, or you override a
reading and the override is recorded in `delivery-approach.md` with your name and reason.

What the gate feels like: it is not a wall. It is the Needle showing its work
and asking you to agree the terrain was read correctly. Confirming takes a
moment. The point is that the process for this task is now *written down* -
any later session can read `delivery-approach.md` and know exactly what shape the pipeline
takes.

### Specify

```
/compass:specify
```

The `spec-author` agent reads `delivery-approach.md`, sees "small feature set," and writes
`acceptance-criteria.md` - Given/When/Then scenarios for the rate limiter: the happy
path (a client under the limit is served), the realistic edges (a client at
exactly the limit; the limit window rolling over), the failure modes that
matter (a client over the limit gets a clean 429, not a dropped connection).
Each scenario carries a traceability id and links back to an intent.

This file is the one every role would read if they were involved - but on a
solo engineering task, you are reading it for tests. The scenarios here become
your acceptance suite and seed your TDD cycle.

### Clarify

```
/compass:clarify
```

On Standard, Clarify is a light-to-full pass - never skipped. The `spec-author`
QAs the spec against itself (is "the limit" defined? per-client or global? what
about unauthenticated traffic?) and against governance. Each ambiguity is
resolved into `acceptance-criteria.md` or recorded in `requirements-review.md` with an
owner. An unresolved ambiguity is not allowed to pass silently into Plan.

### Plan

```
/compass:plan
```

The `planner` agent writes a real `design.md`: the technical approach, each
design decision recorded ADR-style (token bucket vs. sliding window - what was
chosen, what was rejected, why), and a governance check run against all of
`governance/` - guardrails, strategies, and the routing policy. The work here
is one or two streams, not four, so the distribution map is a short list, not a
full `distribution-map.md`. The gate: the governance check passed - every
guardrail cleared with evidence - and you paste its result.

### Build

```
/compass:build
```

This is where the hook earns its keep. The `builder` agent works one scenario
at a time, driving the cycle through the CLI:

1. **Red.** Write the failing test for the scenario. Then run
   `compass tdd-red -- <test cmd>`: the CLI runs the test, *asserts it actually
   fails*, writes the `evidence/red.json` record, and only then writes the
   `.red` marker. If the test passes, `tdd-red` refuses - there is no red to
   record. The marker is honest by construction.
2. **Green.** Now edit the production code. The `pre-tool.sh` hook sees the
   `.red` marker and allows the edit. Write the smallest correct change, then
   run `compass tdd-green -- <test cmd>`: the CLI asserts the test now passes,
   writes `evidence/green.json`, and clears the `.red` marker.
3. **Refactor** under a green suite - the marker is already cleared, which is
   the detectable hand-off to Verify.

If you skip red, the hook blocks you with a message telling you exactly what to
do. The fix is always the same: go write the test, then `compass tdd-red`.

### Verify

```
/compass:verify
```

The `verifier` runs the scenarios as the acceptance suite and runs the full
TDD suite, pasting the actual command output - "the tests pass" is the run,
not the sentence. It also runs `compass check`, which executes the
`governance/guardrails.yml` checks against `task.yml` and `evidence/` - every
scenario lists a test, the recorded suite passed, every changed file traces to
a scenario, every `pass` gate has resolving evidence. The `reviewer` then
applies the route's review dimensions: `correctness`, `governance`,
`traceability` always, plus `regression`, `clarity`, and `security` scaled to
the cross-cutting blast radius. The result is `verification-report.md`. A gate
passes only with evidence attached, and that evidence is **typed** - a
`{type, path}` record (`test-run`, `command-output`, `human-approval`,
`artifact`), and `guardrails.yml` says which types each gate accepts, so a
mechanical gate cannot be cleared with a written note. `compass check` fails an
empty or wrongly-typed evidence block automatically. If anything fails, the
task does not advance - you fix it, or it goes back.

### Land

```
/compass:land
```

Solo route, so Land commits on the current branch, runs regression across the
result, updates any living docs the change touched, and checks the de-scope
ledger for owed backfills (Standard owed none here). A final `devlog.md` entry
records what landed and how it was verified. The task is closed.

That is the full Standard route, walked end to end. Seven artifacts on disk,
each one readable by anyone who picks the task up later.

---

## 4. First task - the product owner

You are a product owner. You do not start at Frame - you start *upstream* of
the spec, with intent.

### Intent

```
/compass:intent "Let finance pull their month-end numbers without filing a data request"
```

The `product-lens` agent adopts the product owner's vocabulary - outcomes and
users, not files and functions - and writes `prd.md`: the **problem**
(finance cannot self-serve; every month-end is a data request and a wait), the
**outcome** (finance gets their numbers directly), the **success signals**
(finance pulls month-end numbers without filing a request; the data team's
month-end ticket volume drops), the **constraints**, and the **non-goals** (we
are *not* building a full reporting suite). It checks the brief against the
product strategies in `governance/strategies.md` - the ones the product owner
curates - and names any tension rather than passing it downstream silently.

Notice what the brief is *not*: it is not "add a CSV export button." That is a
solution. The brief states the outcome, and the difference matters - see the
routing deep dive for how the same literal request routes differently
depending on the brief behind it.

### Frame - now with a brief

```
/compass:frame "CSV export for finance month-end numbers"
```

The Needle reads `prd.md` as part of the intent & role dimension - intent is
the *actual outcome wanted*, not the literal request. The `product-owner`
reading does two things to the route: it adds `prd.md` as a required
artifact, and it inserts the **intent-fidelity gate** before Plan. The route
comes out heavier than a bare engineering "add an export" would - that extra
weight is the framework working, not overhead.

### Specify and Clarify

`/compass:specify` writes `acceptance-criteria.md` against the brief - every success
signal in the brief should have a scenario that delivers it. At
`/compass:clarify`, the `product-lens` agent reviews: it walks every success
signal and finds the scenario behind it, flagging **drift** (a scenario that
solves the literal request but misses the outcome), **gaps** (a signal with no
scenario), and **scope creep** (scenarios beyond the brief with no recorded
decision).

### The intent-fidelity gate at Plan

```
/compass:plan
```

Per the routing policy's `role_rules`, when a product owner is in play the
spec **must be checked against `prd.md` before Plan completes**. The
`product-lens` agent runs that check. If the spec drifts from the brief -
well-formed scenarios that nonetheless miss the outcome - Plan does not
proceed; the spec goes back. Well-formed and faithful are different tests, and
this gate is where the difference is enforced.

From here the pipeline continues as the route specifies - Build, Verify, Land -
with the engineer carrying it. The product owner's involvement did not bolt a
review onto the end; it changed the route from the start and put a gate before
Plan.

---

## 5. First task - the product marketer

You are a product marketer. You work *parallel* to the spec - not downstream
of a finished engineering process.

### Position

```
/compass:position "The finance self-serve export"
```

The `marketing-lens` agent adopts the marketer's vocabulary - claims, voice,
audience - reads the voice & positioning strategies in
`governance/strategies.md` (the ones the marketer curates), reads
`acceptance-criteria.md` if it exists yet, and writes two artifacts:

- **`positioning.md`** - the audience, the value proposition, and the claim
  set. For **every claim**, it names the scenario in `acceptance-criteria.md` that
  backs it. A claim with no backing scenario is not yet a claim: it is either
  a scenario that needs writing (raised with `spec-author` at Specify) or a
  claim that has to be cut. The template leaves the backing-scenario slot
  blank when there is nothing behind the claim yet - an empty slot is a
  visible debt, which is the point.
- **`launch-readiness.md`** - the claims ledger: every claim, its backing
  scenario, and that scenario's verification status.

### How this shapes the route, and the gate at Land

The `product-marketer` reading turns on the `claims` review dimension and -
per the `role_rules` - **blocks Land until every claim in `positioning.md`
traces to a passing scenario**. `verify.claims` is an immovable gate; no route
removes it.

So the marketer's gate is felt at the very end. At `/compass:land`, the
`marketing-lens` agent walks `launch-readiness.md`. Every row must be green: a
claim, a backing scenario, that scenario passing at Verify. A red row - a
claim whose scenario is missing, failing, or skipped - and Land refuses to
close the task. The marketer's only moves at that point are to soften the
claim, cut it, or file the missing scenario. What cannot happen is a launch
claim shipping on a scenario that does not back it.

---

## When you cannot frame it yet - the Spike route

Some work is not a known change - it is a question. Root-causing a mysterious
defect, evaluating whether an approach is even viable, learning an unfamiliar
API. You cannot state acceptance criteria for it because the behaviour is the
unknown. That is not an exemption from Frame; it is the **Spike** route. Frame
still runs (`delivery-approach.md` records the question and a timebox), but Specify
collapses to the question, Clarify is skipped, and Build becomes Explore - the
TDD strategy is suspended and the hook does not block, because red-before-green
is the wrong discipline for code you are writing to learn something and may
throw away. The catch that keeps it honest: **nothing lands from a Spike**. The
only exit that keeps code is *graduating* - re-framing into a real route where
the guardrails apply in full - or discarding it with the finding recorded. See
`routes/spike.md`.

## Where to go next

- **`docs/routing-deep-dive.md`** - how the Needle actually composes a route,
  with worked examples, including the same literal request routing four
  different ways, and a Spike route worked through end to end.
- **`docs/roles-guide.md`** - one concrete scenario read through all five
  lenses, and what each role owns.
- **`docs/portability.md`** - the three layers (methodology / kit / adapter),
  and what porting Compass to another runtime involves: rewrite the adapter,
  keep the methodology and the kit untouched.

When a session leaves a task half-finished, `/compass:status` reports where
every task stands, and `/compass:resume <task-slug>` picks one up from disk -
the artifacts were written precisely so the process never has to be
re-derived. Once you are running more than one task at a time, `/compass:flow`
is the view across all of them - triage, blockers, and a periodic digest;
`docs/methodology.md` §10 explains why it is a capability rather than a role.

Two more CLI commands work across the whole board. `compass ci` runs the full
mechanical gate suite - `policy lint`, then `task lint` and `check` for every
task - and exits non-zero if anything fails; wiring Compass into CI is just
"run `compass ci`, honour the exit code" (see `ci/README.md`). And `compass
calibration` reads the re-frame log across every task and reports whether the
Needle is systematically over- or under-sizing routes - the framework's own
feedback loop, the way you find out if the routing policy needs tuning.
