<p align="center">
  <img src="assets/compass-icon.png" alt="Compass Framework Icon" width="320" max-width="100%">
</p>

# Compass - Adaptive Spec-Driven Development

**Read the terrain. Then route.**

Compass is a spec-driven development framework that refuses to treat a typo fix
and a payments rewrite the same way. It reads the context of each task - how
risky, how big, new code or old, who's asking - and computes the right amount
of process for *that* change. Heavy when it needs to be. Out of the way when it
doesn't.

Built for Claude Code. The methodology and kit layers are tool-agnostic, so it
ports - only the thin adapter layer is Claude-Code-specific.

> Working name. "Compass" and "the Needle" are placeholders - rename freely.

---

## The problem

Every spec-driven framework eventually picks a ceremony and applies it to
everything. Then one of two things happens:

- The process costs more than the change, so people route around it. It gets
  used for the demo and abandoned for the real work.
- The same flat process that's too heavy for a typo is too *light* for a
  schema migration. You can't calibrate one fixed pipeline for both ends.

The usual fix is *levels* - a fixed ladder of five or six tiers. Better, but a
ladder is a one-dimensional answer to a multi-dimensional question. "How risky"
and "how big" and "is this greenfield" and "who's invoking" are different axes.
A migration that touches one file is small but not safe. A prototype is large
but low-risk.

## The idea

Compass computes process intensity per task instead of selecting it from a
menu. Every task starts with **Frame** - a triage step where the **Needle**
reads four dimensions:

| Dimension | Question |
|---|---|
| **Blast radius** | If this goes wrong, how bad and how wide? |
| **Terrain** | New code or existing code - and how well is it mapped? |
| **Magnitude** | How much work is this actually? |
| **Intent & role** | Who's invoking, and what outcome are they really after? |

The Needle writes `route.md`: what it assessed, the route it chose, the gates
that apply, and **exactly what it's skipping and why that's safe**. De-scoping
is a written, auditable decision - never an accident.

## One pipeline, adaptive depth

Every route runs the same eight phases. What changes is how much each one
costs.

```
Frame → Specify → Clarify → Plan → Distribute → Build → Verify → Land
```

On the **Express** route, Clarify/Plan/Distribute collapse to almost nothing.
On **Expedition**, Plan produces a distribution map and Distribute spins up a
swarm of agents across git worktrees. Same vocabulary, different weight - so
anyone who's run one Compass task can read the artifacts of any other.

## Governance - guardrails and strategies

Compass is governed by two kinds of thing, kept deliberately separate:

- **Guardrails** - few, hard, checkable, blocking. The things that must never
  happen. The Needle adapts ceremony *around* them; it never crosses one.
- **Strategies** - many, soft, directional, assessed. How the team tends to
  work. A strategy biases a decision; it doesn't block one.

The framework ships five **default guardrails**: (G1) tested before it lands,
(G2) acceptance defined before it's built, (G3) traceability holds, (G4)
evidence not assertion, (G5) a human signs off on the irreversible.

The move that keeps Compass from being a sledgehammer: **BDD and TDD are
default *strategies*, not guardrails.** The hard line is the *outcome* - code
is tested, acceptance is checkable. Given/When/Then and red-green-refactor are
the strong, shipped-on *way* to get there - and the Spike route can suspend
them. A one-line typo fix still has to be tested before it lands; it doesn't
have to perform the full ritual to do so.

And governance is a **gradient, not a threshold**: the defaults ship active,
so `/compass:init` is optional and `/compass:frame` works on day one. A team
*accretes* its own strategies as it forms opinions. See `governance/`.

### Fitness functions and intermittent-test integrity

Two related v1.1.0 capabilities extend the governance story without adding to
the hard guardrail count:

- **Fitness functions as project guardrails.** A project declares a fitness
  function as a guardrail in `governance/guardrails.yml` with
  `check: command-passes` plus the command to run; `compass check` runs the
  command at Verify and refuses to clear the gate if it does not exit 0. This
  lets a team encode "the build is under N MB", "the API never returns 500 in
  the smoke suite", "performance does not regress past P95 = X ms" *as
  guardrails* - checkable, blocking, evidence-backed - without having to
  invent new check types in the framework. See `architecture/decisions/ADR-009`.
- **Intermittent-test integrity.** Tests that rerun to green are the classic
  way a guardrail becomes silently advisory. The `no-trusted-rerun` rule on
  G4 (evidence, not assertion) refuses to clear a test-run when a rerun was
  needed unless either the root cause is fixed *or* the test is explicitly
  quarantined in `governance/quarantine.yml` with a tracking task. The detail
  lives in `governance/strategies.md` §6; the discipline is part of how
  Compass takes G4 seriously.

## Roles are full citizens - one spec, many lenses

Compass isn't an engineering framework with bolted-on hooks for everyone else.
The non-engineering roles have their own entry points and artifacts that plug
into the *same* pipeline. The shared BDD scenario file is what makes it work -
every role reads it through their own lens:

| Role | Entry point | Reads the spec for… |
|---|---|---|
| Product owner / manager | `/compass:intent` | intent fidelity - do these scenarios deliver the brief? |
| Product marketer | `/compass:position` | claims - every line of launch copy points at a backing scenario |
| Designer | `/compass:design` | UI contracts, written as scenarios that flow into Specify |
| Engineer | `/compass:frame` → pipeline | tests - scenarios become the acceptance suite |
| QA | `/compass:verify` | coverage - which scenarios are exercised, which edges aren't |

The product owner enters *upstream* of the spec. The marketer works *parallel*
to it. The designer feeds *into* it. Nobody is just a downstream consumer of a
finished engineering process.

**A lens does not always have an entry point.** The table above lists five
**entry-point roles** - each starts a Compass task with its own `/compass:…`
command. The framework ships ten agents though, not five, because some lenses
apply *during* the pipeline rather than starting it. The 10th - the
**architect-lens** - reads the project's `architecture/` artifacts at Frame
and annotates `plan.md` via `architecture-notes.md` at Plan; it is consulted
by `spec-author` and `planner`, not invoked as its own entry point. See
[`docs/roles-guide.md`](docs/roles-guide.md) for the full lens treatment.

## The five reference routes

Routes are *composed* from the dimension readings - these five are starting
shapes the Needle tunes, not a fixed ladder.

| Route | Typical reading | Shape |
|---|---|---|
| **Express** | atomic · contained · mapped | Frame → Specify (1 scenario) → Build → Verify. Still tested before it lands. One gate. |
| **Standard** | standard · contained | Full pipeline, solo or pair. Two gates. |
| **Expedition** | large · cross-cutting · greenfield | Full weight. Governance check, BDD discovery, distribution map, agent swarm across worktrees. All gates. |
| **Hotfix** | critical · small · brownfield | Reproduce-first - a failing regression test is the spec. Expedited Build, mandatory post-incident backfill. All Verify gates. |
| **Spike** | intent is exploration | Explore freely - the TDD strategy is suspended, the hook doesn't block. Then graduate (re-frame into a real route) or discard. **Nothing lands from a Spike.** |

## The determinism boundary - and the CLI

An adaptive framework owes an answer to the obvious objection: *if the process
can flex, what stops it flexing to nothing?* Part of that answer is the routing
policy (above). The other part is now **mechanical**.

There is a line through Compass. On one side is **judgement** - the Needle
reading the four dimensions. That cannot be mechanized; that judgement *is* the
adaptivity. On the other side is **mechanism** - everything that happens once
the readings exist: composing the route, applying the floors and caps, running
the guardrail checks. Same readings + same policy => the same route, every
time. Compass puts that mechanism in a CLI, `cli/compass`, so it is *actually*
deterministic, not deterministic-in-principle. See `docs/methodology.md` §6.

```
compass route evaluate   apply routing-policy.yml to a task's readings → the route
compass check            run the guardrails.yml checks against task.yml + evidence/
compass tdd-red   -- CMD run a test, assert it FAILS, record the red
compass tdd-green -- CMD run a test, assert it PASSES, clear the red marker
compass policy lint      structurally validate the governance YAML
compass task lint        structurally validate a task.yml
compass task receipt     render a one-screen receipt for a landed task -
                         readings → route → typed evidence → gate verdicts
compass gate pass        flip a gate to pass; validates evidence type at write time (R6)
compass scenario add     append a scenario to task.yml (schema-owning mutator, R9)
compass changed-file add trace a changed production file to a scenario (R9)
compass evidence add     append a typed evidence entry to the registry (R9)
compass analyze          cross-artifact coherence check: orphaned scenarios,
                         route disagreements, orphan claims (advisory or
                         gate-clearing if verify.analyze is in the route)
compass adr new          create a new numbered ADR in architecture/decisions/
compass rework-scan      scan tasks for rework patterns (window from signals.yml)
compass flow [--digest]  cross-task flow view; --digest writes a dated digest
                         with the rework-scan section and calibration signal
compass next             surface the next action on the current task
compass backfill pay     mark a backfill as paid in a task's task.yml
compass land-commit -m   commit staged artifacts robustly - survives auto-fixing
                         pre-commit hooks and verifies HEAD advanced (R5)
compass calibration      aggregate the re-frame log - is routing well-sized?
compass ci               the full mechanical gate suite, for CI - honour the exit code
```

Its only hard dependency is PyYAML (`jsonschema` is optional - it turns on
full JSON Schema validation in the lint commands). The slash commands call the
CLI under the hood - `/compass:frame` runs `compass route evaluate`,
`/compass:verify` runs `compass check` - so you rarely invoke it directly, but
it is there, and it is the part that makes the framework's checks real rather
than aspirational. Gate evidence in `task.yml` is **typed** - a `{type, path}`
record, not a bare path - so a mechanical gate cannot be cleared with a written
note. And `compass calibration` is the framework's own feedback loop: it reads
the re-frame log across every task and reports whether the Needle is
systematically over- or under-sizing routes.

## Compass CI vs project CI

> Compass CI does not replace your normal project CI. It does not re-run
> your full test suite unless you explicitly configure your pipeline to do
> so. Compass checks whether required evidence exists, is valid, and is
> traceable to the task route. Your application pipeline should still run
> tests, linting, type checks, security scans, build validation, and
> deployment checks.

The two are complementary: project CI proves the *code* is correct;
Compass CI proves the *process* - that the route was framed, scenarios
have tests, changed files trace to scenarios, gates carry evidence of the
right type, approvals are recorded where they must be. Run them as
separate jobs in the same workflow, with `compass-ci` gated on
`project-ci` so a failing test suite stops the pipeline before Compass
even runs:

```yaml
# .github/workflows/ci.yml
name: CI

on:
  pull_request:
  push:
    branches: [main]

jobs:
  project-ci:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      # your normal pipeline: tests, lint, type-check, security scans,
      # build validation, deploy checks - whatever your project requires.
      - run: make test
      - run: make lint

  compass-ci:
    runs-on: ubuntu-latest
    needs: project-ci             # only run Compass once the code is green
    env:
      COMPASS_CLI: cli/compass    # adjust to wherever Compass lives in your repo
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install pyyaml jsonschema
      - run: python3 "$COMPASS_CLI" ci
```

`ci/github-actions.yml` is the reference workflow for just the
`compass-ci` job; `ci/README.md` is the full contract. Pin
`COMPASS_CLI` to a specific commit SHA - see `docs/security.md` for the
supply-chain stance. When you are first piloting Compass and do not
want it blocking PRs yet, set `mode: advisory` in `.compass/config.yml`
and `compass ci` will report failures without exiting non-zero. Flip to
`mode: enforced` when the team is ready.

## Quick start

The fastest path is the plugin marketplace - no clone, no install script:

```bash
# In Claude Code:
/plugin marketplace add jed72/compass
/plugin install compass@compass
pip install pyyaml      # the CLI's one dependency
```

Enabling the plugin namespaces the commands as `/compass:…`, registers the
hooks, and puts the `compass` CLI on your PATH (Claude Code adds the plugin's
`bin/` to PATH automatically - that is the plugin-path-only convenience).

Or install from source - `install.sh` wires the slash commands, agents,
skills, and hooks in by symlink, so edits to your clone are picked up live:

```bash
git clone https://github.com/jed72/compass.git
cd compass && bash scripts/install.sh --global
pip install pyyaml
```

`install.sh` does **not** modify your PATH - the source install does not have
the plugin runtime to do it for you. To make `compass` invokable from your
shell, add `$PWD/bin` to your `PATH` (or invoke the CLI as
`python3 $COMPASS_HOME/cli/compass`). The slash commands run the CLI on your
behalf, so this only matters when you call it directly.

Either way, start a task right away - the default guardrails ship active, so
the Needle frames it and picks the route with zero setup:

```bash
/compass:frame "Add rate limiting to the public API"

# Walk the pipeline (or let the route auto-advance). The slash commands
# call the `compass` CLI under the hood for the deterministic parts -
# route evaluation, the TDD red/green records, the guardrail checks.
/compass:specify
/compass:plan
/compass:build
/compass:verify
/compass:land

# Optional, whenever you have opinions to encode - not a prerequisite:
/compass:init   # adopt project guardrails and strategies into governance/
```

A product owner would instead start with `/compass:intent`, a marketer with
`/compass:position`. To see across every task in flight - triage, blockers,
the periodic digest - run `/compass:flow`. See `docs/quickstart.md`.

## What's in the box

Compass is built in **three layers** - see `docs/methodology.md` §9. The
methodology layer *is* the framework (plain markdown). The kit layer is the
deterministic mechanism (a plain CLI, PyYAML its one dependency, not
Claude-Code-specific). The adapter layer wires both into Claude Code.

```
compass/
├── governance/        Guardrails + strategies + routing policy - .md (prose)
│                      AND .yml (the machine-readable governance the CLI runs;
│                      including signals.yml and quarantine.yml)
├── architecture/      The project's cross-task architectural artifacts:
│                      system-context.md, relations.md, ownership.md, and
│                      ADRs in decisions/. Compass ships its own (the
│                      framework's founding ADRs) as a worked example for
│                      adopters; another project drops its own here
├── routes/            The Needle (router.md) + the 5 reference routes
├── schemas/           Executable JSON Schema (.schema.json) for the .yml +
│                      task.yml, with human-readable .reference.yml companions
├── cli/               compass - the deterministic CLI (route evaluate, check,
│                      tdd-red/green, lint, calibration, ci); the kit's mechanism
├── bin/               compass - plugin CLI shim that execs cli/compass.
│                      Claude Code adds the plugin's bin/ to PATH when the
│                      plugin is enabled, so `compass <subcommand>` resolves
│                      without a manual symlink or alias
├── ci/                CI integration: the reference workflow + the contract
│                      ("run compass ci, honour the exit code")
├── commands/          Slash commands: the pipeline + role entry points
├── agents/            Subagent definitions, including the swarm orchestrator
├── skills/            Procedural knowledge: routing, BDD, TDD, worktrees…
├── hooks/             Mechanical enforcement of the guardrails + TDD strategy
├── templates/         Artifact templates for every phase and role -
│                      including task.yml, the machine-readable task spine
├── scripts/           install, swarm, integrate, validate
├── .claude-plugin/    Claude Code plugin manifest (plugin.json) +
│                      marketplace manifest - the install path used by
│                      `/plugin install`, parallel to scripts/install.sh
└── docs/              methodology.md is the canonical design doc - start there
```

The methodology layer is `docs/`, `governance/*.md`, `routes/`, `templates/`.
The kit layer is `cli/`, `governance/*.yml`, `schemas/`, and the `task.yml`
spine. The Claude Code adapter layer is `commands/`, `agents/`, `skills/`,
`hooks/`, `CLAUDE.md` - and the commands and agents *call the kit*.

## Read next

- **`docs/five-minutes.md`** - the shortest path from "what is this" to
  "I've shipped a task with it." Start here.
- **`docs/safety-contract.md`** - the seven things Compass 1.0
  guarantees, and what it explicitly does *not* claim.
- **`docs/methodology.md`** - the canonical design doc. Everything else
  is downstream of it.
- `docs/quickstart.md` - your first task, per role.
- `docs/install-smoke-test.md` - manual install verification checklist.
- `docs/security.md` - hook surface, dependencies, supply-chain stance.
- `docs/routing-deep-dive.md` - how the Needle actually decides.
- `docs/roles-guide.md` - one scenario, seen four ways.
- `docs/portability.md` - the three layers, and what porting Compass to
  another runtime involves (rewrite the adapter; keep methodology and kit).
- `schemas/README.md` - the shape of the machine-readable files the CLI reads.

## License

Apache 2.0. See `LICENSE`.
