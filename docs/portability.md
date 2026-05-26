# Compass — Portability

Compass runs on Claude Code today. It is built so that "today" is not "only."
The framework is deliberately split into three layers, and the split is the
whole portability story: two layers are tool-agnostic — the framework itself
and the deterministic mechanism that runs its checks — and only the third
wires those into one specific runtime. A port rewrites only the third.

This document describes the three layers, the contract a new runtime adapter
must satisfy, and a concrete sketch of what porting to another agent runtime
actually involves — which files you keep untouched, which you rewrite.
`docs/methodology.md` §9 introduces the three layers; this is the portability
consequence of that split worked out in full.

---

## The three layers

### The methodology layer — tool-agnostic

```
docs/            methodology.md (canonical), quickstart, routing-deep-dive,
                 roles-guide, this file
governance/      README.md, guardrails.md, strategies.md, routing-policy.md
routes/          router.md, README.md,
                 express/standard/expedition/hotfix/spike.md
templates/       route.md, task.yml, brief.md, spec.feature.md,
                 clarifications.md, plan.md, distribution-map.md,
                 positioning.md, launch-readiness.md, ui-contract.md,
                 verification-report.md, devlog.md
```

This layer is plain markdown (the `.md` files of `governance/`, not the
`.yml`). No slash-command syntax, no hook scripts, no runtime-specific
anything. It is the framework: the eight-phase pipeline, the four routing
dimensions, the guardrails and strategies, the routing policy, the artifact
shapes, the role model. It would be a valid, complete description of Compass if
neither a CLI nor Claude Code existed. `docs/methodology.md` is the canonical
design document; every other file in the repository is downstream of it.

A port does not touch this layer. That is the point of it existing.

### The kit layer — tool-agnostic, but executable

```
cli/             compass — the deterministic CLI
governance/      routing-policy.yml, guardrails.yml — machine-readable governance
schemas/         *.schema.json — executable JSON Schema (draft-07);
                 *.reference.yml — human-readable companions
ci/              github-actions.yml + README — the CI integration contract
templates/       task.yml — the machine-readable task spine
```

The kit layer is the *mechanism* side of the determinism boundary
(`docs/methodology.md` §6) made into software. The Needle's four-dimension
*readings* are judgement and stay judgement; everything downstream — composing
the route, applying the floors and caps, stapling the immovable gates, running
the guardrail checks — is pure function, and this layer is that function.
`compass route evaluate` applies `routing-policy.yml` to a task's readings;
`compass check` runs the `guardrails.yml` checks against `task.yml` and
`evidence/` (gate evidence is *typed* — a `{type, path}` record — so a
mechanical gate cannot be cleared with a written note); `compass tdd-red` /
`tdd-green` run a test and write the evidence records; `compass policy lint` /
`task lint` validate the YAML against the executable JSON Schema in `schemas/`
when the optional `jsonschema` library is present, and against the built-in
linter always; `compass ci` aggregates the lot for CI; `compass calibration`
reads the re-frame log across all tasks and reports whether routing is
well-sized. Same readings + same policy => the same route, every time, on every
runtime.

This layer is tool-agnostic — its only hard dependency is Python 3 and PyYAML
(`jsonschema` is optional), and nothing in it knows what Claude Code is — but
unlike the methodology layer it is *executable*. A port does not rewrite it
either. It *calls* it. That is the distinction that matters for porting: the
kit is the part a new runtime should shell out to rather than reimplement, so
that route composition and guardrail checking are provably identical across
runtimes instead of two independent re-derivations that might drift.

### The Claude Code adapter layer — runtime-specific

```
commands/        slash commands — the eight pipeline phases plus the role
                 entry points (all under the /compass: namespace)
agents/          subagent definitions — navigator, spec-author, planner,
                 orchestrator, builder, verifier, reviewer, product-lens,
                 marketing-lens
skills/          procedural-knowledge modules — adaptive-routing,
                 bdd-specification, tdd-discipline, blueprint-distillation,
                 worktree-swarm, governance-check, traceability,
                 evidence-gates, role-translation
hooks/           pre-tool.sh, post-tool.sh, stop.sh — mechanical guardrail
                 enforcement
CLAUDE.md        the operating instructions loaded every Claude Code session
bin/             compass — plugin CLI shim that execs cli/compass. Claude
                 Code adds the plugin's bin/ to PATH automatically when the
                 plugin is enabled
.claude-plugin/  plugin.json + marketplace.json — the Claude Code plugin
                 and marketplace manifests; the install path used by
                 `/plugin install`, parallel to scripts/install.sh
scripts/         install.sh, swarm.sh, integrate.sh, validate.sh
```

This is the methodology and kit layers expressed in one runtime's vocabulary.
Slash commands invoke the phases — and *call the kit* for the deterministic
parts: `/compass:frame` runs `compass route evaluate`, `/compass:verify` runs
`compass check`, the `builder` agent runs `compass tdd-red` / `tdd-green`.
Subagents are the swarm and the role lenses. Skills carry the procedural
knowledge a phase needs. Hooks enforce the guardrails mechanically where they
can — `pre-tool.sh` enforces the red-before-green TDD strategy in service of
guardrail G1 (and is route-aware: it does not block on a Spike); `post-tool.sh`
appends to the devlog and clears the red marker; `stop.sh` makes a
half-finished task loud at session end. `CLAUDE.md` is the runtime expression
of `docs/methodology.md` — and where the two ever appear to conflict, the
methodology doc wins.

A port rewrites this layer, and only this layer — the methodology layer it
reads unchanged, the kit layer it invokes unchanged.

### What the boundary looks like in practice

`scripts/install.sh` is itself evidence of the boundary. It installs *only*
the adapter layer — it symlinks `commands/`, `agents/`, and `skills/` into
Claude Code's config, registers the hooks in `settings.json`, and puts the
`compass` CLI on the path. The methodology and kit layers are "NOT installed
anywhere — read and run in place from this repo." Uninstalling removes the
adapter wiring and leaves methodology and kit untouched. The installer treats
the layers as exactly the separable things this document claims they are: the
adapter is the thin part it wires in, the kit is a CLI it merely exposes, the
methodology is read where it sits.

---

## The contract a runtime adapter must satisfy

`AGENTS.md` at the repository root is the runtime-neutral statement of this
contract — the same intent as `CLAUDE.md` without Claude Code's syntax, for
any other runtime. What follows expands it into the full contract. A correct
Compass adapter must provide all five of the following — and the rule that
runs through all of them: **call the kit, do not reimplement it.** The
deterministic parts — route composition, guardrail checks, the TDD red/green
records — already exist as a runtime-neutral CLI. An adapter that re-derives
them in its own code has not ported Compass; it has forked it, and the fork
will drift.

The adapter's job, ultimately, is to preserve the **Compass 1.0 safety
contract** (`docs/safety-contract.md`) on the new runtime — the seven
guarantees that make "Compass is in use" mean something. Methodology gives
the contract its language; the kit makes most of it mechanical; the adapter
is what makes a runtime able to honour it. A port that preserves the
methodology and kit but breaks the contract — say, by skipping the kit's
guardrail checks and "doing them locally" — has shipped a fork wearing
Compass's name. The five requirements below are how an adapter holds up its
end of the contract.

### 1. Frame before changing anything

Before a task modifies code, specs, or product artifacts, the runtime must run
the Needle: read the four context dimensions (blast radius, terrain,
magnitude, intent & role) — that part is judgement, and the runtime must
produce it. *Composing* the route from those readings is mechanism, and the
adapter should shell out to `compass route evaluate` rather than reimplement
it: the CLI applies `governance/routing-policy.yml` and records the route,
phases, and gates into `task.yml`. The runtime records the readings (in
`task.yml`) and writes the human-readable `route.md`. The route is *computed*
from context, not chosen from a menu, and — because the composition is the
kit's pure function — the same readings produce the same route on every
runtime. The only work exempt from Frame is conversation — answering,
explaining, exploring. The moment an operation would change a file, Frame must
already have run for the current task.

The reference adapter enforces this two ways: `CLAUDE.md` states "Never skip
Frame" as the one rule that creates every other rule, and `pre-tool.sh` blocks
a code edit when no `route.md` exists for the current task. A port must achieve
the same outcome — mechanically if it can, procedurally if it cannot.

### 2. Walk the eight-phase pipeline

`Frame → Specify → Clarify → Plan → Distribute → Build → Verify → Land`. The
adapter must make each phase an invocable unit — a command, a mode, a routine,
whatever the runtime offers — run in order. The route in `route.md` says which
phases are full-weight, which collapse, and which are skipped, and always says
*why* a phase is skipped. The adapter must honour that: not silently re-skip a
phase the route kept, not silently re-add one it skipped. After each phase, the
adapter writes that phase's artifact to the task's working directory using the
matching template from `templates/`.

### 3. Enforce the guardrails — five defaults, never adapted

- **G1 — Tested before it lands** — no code reaches `main` without a passing
  automated test it traces to.
- **G2 — Acceptance defined before it is built** — no code is written that no
  stated, checkable acceptance criterion describes.
- **G3 — Traceability holds** — code → acceptance criterion → intent, and
  public claim → backing criterion.
- **G4 — Evidence, not assertion** — guardrails clear with command output and
  artifacts, not claims.
- **G5 — A human signs off on the irreversible** — data loss, money, auth,
  privacy get an explicit human checkpoint.

The guardrail *checks* are mechanism, and the kit layer already implements
them: `compass check` runs the `governance/guardrails.yml` checks against the
task's `task.yml` and `evidence/`. The adapter's job is to *call* `compass
check` at Verify and Land — not to write its own scenario-has-a-test or
gate-has-evidence logic. Re-deriving the checks is exactly the drift the kit
layer exists to prevent.

BDD (Given/When/Then) and TDD (red-green-refactor) are the shipped default
*strategies* — the strong, on-by-default way to satisfy G2 and G1 — not
guardrails themselves. The hard line is the outcome; the form is a suspendable
strategy (the Spike route suspends TDD). The adapter must enforce the
red-before-green strategy **mechanically if the runtime can** — the reference
adapter uses `pre-tool.sh` as a `PreToolUse` hook with a `.red` marker
convention, and makes it route-aware so it does not block on a Spike. The
red/green *records* themselves come from the kit: `compass tdd-red` runs a
test, asserts it fails, and writes the `.red` marker and `evidence/red.json`;
`compass tdd-green` asserts it passes and clears the marker. An adapter wires
its hook to that marker; it does not need to reproduce the test-running and
evidence-writing. If the runtime has no hook mechanism, the adapter must
enforce the strategy *procedurally* — but it still calls `compass tdd-red` /
`tdd-green` for the records, and refuses to proceed without a failing test on
record. The real G1 check is at Verify and Land, with evidence. "We could not
enforce it mechanically" is an acceptable adapter limitation; "so we did not
enforce G1" is not — that is crossing a guardrail.

### 4. Support five roles as full citizens

Engineer, product owner / manager, product marketer, designer, QA. Each needs
a distinct entry point — a session-start mode the runtime can express — and
each has artifacts that plug into the same pipeline (`brief.md`,
`positioning.md`, `launch-readiness.md`, `ui-contract.md`,
`verification-report.md`). The BDD scenario file is the shared substrate read
through five lenses; the adapter must not reduce it to an engineering-only
artifact. The role rules in `governance/routing-policy.md` — the intent-fidelity
gate, the claims gate — must be enforced, because an unenforced role is a
decorative one.

### 5. Support solo / pair / swarm topologies

On larger routes, Plan produces a distribution map and Distribute parallelises
across isolated workspaces — git worktrees in the reference implementation,
one agent per stream, with a coordinating orchestrator that owns integration
at Land. A runtime without worktrees must provide *equivalent isolation* — a
mechanism where one stream can run a full red→green cycle, including a failing
suite, without destabilising siblings. If it genuinely cannot, the adapter
must cap itself at solo/pair and say so. It must not pretend to swarm without
the isolation that makes a swarm safe.

### 6. Shell out for CI and the feedback loop

Two kit commands operate across the whole board, and the adapter wires them
into the runtime's surfaces rather than reimplementing them. `compass ci` runs
the full mechanical gate suite — `policy lint`, then `task lint` and `check`
for every task — and aggregates exit codes; the CI integration is "run
`compass ci`, honour the exit code" (`ci/README.md` is the contract, and
`ci/github-actions.yml` the reference workflow). `compass calibration`
aggregates the `reframes` log across all tasks and reports whether the Needle
is systematically over- or under-sizing routes — the framework's own feedback
loop, a natural fit for the runtime's cross-task / flow surface. Neither gates;
both are mechanism the adapter calls.

### The mapping table

`AGENTS.md` states the mapping a runtime adapter must provide. Expanded:

| Methodology / kit concept | Adapter must map it to… | Reference (Claude Code) |
|---|---|---|
| The eight phases | Invocable commands or equivalent units | `commands/*.md` slash commands |
| The Needle | A triage routine that produces the *readings*, then calls the kit to compose the route | `/compass:frame` + the `navigator` agent + the `adaptive-routing` skill, calling `compass route evaluate` |
| The kit-layer CLI | A shell-out from the adapter — never a reimplementation | `commands`/`agents` invoke `compass route evaluate`, `compass check`, `compass tdd-red/green` |
| CI and the feedback loop | A shell-out to `compass ci` (honour the exit code) and `compass calibration` (the re-frame feedback loop) | `ci/github-actions.yml` runs `compass ci`; `/compass:flow` surfaces `compass calibration` |
| Subagents (navigator, spec-author, planner, orchestrator, builder, verifier, reviewer, product-lens, marketing-lens) | Distinct agent contexts or personas | `agents/*.md` |
| Skills | Loadable procedural-knowledge modules | `skills/*/SKILL.md` |
| Guardrail enforcement | `compass check` for the mechanical checks; hooks if available for red-before-green, procedural checks otherwise | `compass check` + `hooks/pre-tool.sh`, `post-tool.sh`, `stop.sh` |
| Role entry points | Distinct session-start modes | `/compass:intent`, `/compass:position`, `/compass:design`, `/compass:roundtable` |
| The operating instructions | The runtime's always-loaded instruction file | `CLAUDE.md` (neutral form: `AGENTS.md`) |
| Install surface | Whatever the runtime exposes for wiring the adapter in — a plugin manifest, a config-file edit, a PATH addition, an install script | `bin/compass` (plugin CLI shim) + `.claude-plugin/plugin.json` (plugin path used by `/plugin install`); `scripts/install.sh` (clone path, symlinks the adapter into `~/.claude/`) |

### State on disk — the non-negotiable substrate

One requirement cuts across all five: **all task state is files, not
conversation.** `governance/` at the project root — the `.md` files
(`guardrails.md`, `strategies.md`, `routing-policy.md`) and the kit-layer
`.yml` files the CLI runs (`routing-policy.yml`, `guardrails.yml`); per-task
artifacts in a `.compass/work/<task-slug>/` directory holding `route.md`,
`task.yml` (the machine-readable task spine), `brief.md`, `spec.feature.md`,
`clarifications.md`, `plan.md`, `distribution-map.md`, `positioning.md`,
`launch-readiness.md`, `ui-contract.md`, `verification-report.md`, an
`evidence/` directory (the CLI's red/green and gate records), an append-only
`devlog.md`, and — on a Spike route — a `.spike` marker file; plus a
`.compass/current-task` pointer the CLI and hooks resolve "the current task"
through. A different session, a different agent, or a different runtime must be
able to resume a task by reading `route.md`, `task.yml`, and the artifacts —
nothing essential may live only in context. This is what makes the framework
portable *across sessions* in the first place; portability across runtimes is
the same property extended.

---

## A concrete port — what it would actually involve

Suppose you are porting Compass to another agent runtime — call it a generic
harness with a different command system, a different (or absent) hook
mechanism, and its own notion of subagents. Here is the shape of the work.

### What you keep, untouched

The entire methodology layer *and* the entire kit layer:

- `docs/` — `methodology.md` is still the canonical design doc; the other docs
  still describe the framework. (You would add a runtime-specific quickstart
  section, but the conceptual docs are unchanged.)
- `governance/` — `guardrails.md`, `strategies.md`, and `routing-policy.md` are
  pure methodology; `routing-policy.yml` and `guardrails.yml` are the kit
  layer's machine-readable governance. The new runtime's Needle reads the prose
  exactly as Claude Code's does, and the new adapter runs the YAML through the
  same CLI.
- `routes/` — `router.md` is the routing rubric regardless of runtime; the
  five reference route files describe pipeline *shapes*, not runtime calls.
- `templates/` — every artifact template is plain markdown, including
  `task.yml`, the machine-readable task spine. `route.md`, `spec.feature.md`,
  and the rest are written the same way by any runtime.
- `cli/`, `schemas/`, and `ci/` — the kit layer. `cli/compass` is a plain
  Python+PyYAML CLI with no Claude Code dependency; the new adapter *calls* it
  for route composition, guardrail checks, CI (`compass ci`), and the re-frame
  feedback loop (`compass calibration`). `schemas/` holds the executable JSON
  Schema the lint commands validate against; `ci/` holds the CI integration
  contract. You do not rewrite any of it — and if you find yourself wanting to,
  that is the strongest possible sign something has leaked across the boundary.

This is most of the repository, and a port does not edit a line of it. If you
find yourself wanting to, something has leaked across the boundary — fix the
leak, do not edit the methodology or the kit.

### What you rewrite

The adapter layer, against the contract above:

- **`commands/`** → the new runtime's equivalent of invocable phase units. The
  *content* of each — what `/compass:frame` does, the procedure it follows —
  is dictated by the methodology layer (`frame.md`'s procedure "follows
  `routes/router.md` exactly"). You are re-expressing known procedures in a
  new command syntax, not redesigning them — and where a procedure has a
  deterministic step, it *calls the kit*: the new Frame command shells out to
  `compass route evaluate`, the new Verify command to `compass check`, the new
  Build procedure to `compass tdd-red` / `tdd-green`. Re-expressing the
  procedure does not mean re-implementing the mechanism it invokes.
- **`agents/`** → the new runtime's notion of distinct agent contexts. The
  nine agents and their boundaries (the navigator owns Frame and only Frame;
  the orchestrator writes no feature code; a builder never touches a sibling
  worktree) are methodology; the wrapper is runtime.
- **`skills/`** → loadable procedural-knowledge modules in whatever form the
  runtime supports. If the runtime has no skill mechanism, the procedural
  knowledge has to be delivered another way — inlined into the command
  procedures, or loaded as reference docs — but it must reach the agent that
  needs it.
- **`hooks/`** → this is the hardest part and where runtimes differ most. The
  reference hooks are bash scripts wired into Claude Code's
  `PreToolUse` / `PostToolUse` / `Stop` events. A new runtime with an
  equivalent event system gets a near-direct rewrite. A runtime *without*
  hooks must move guardrail enforcement into the procedural layer — the
  red-before-green TDD-strategy check becomes a mandatory step in the build
  command that refuses to proceed without a recorded red (and is suspended on a
  Spike route), the devlog append becomes an explicit instruction, the
  session-end warning becomes a `/compass:status`-style check the runtime is
  told to run. Note that even here the kit does the heavy lifting: the recorded
  red is `compass tdd-red`'s `.red` marker and `evidence/red.json`, and the
  guardrail checks are `compass check` — the procedural layer's job is to
  *invoke* them at the right moment, not to reproduce them. The `.red` marker
  convention is deliberately a plain file precisely so it survives this
  translation: it is inspectable and auditable whether a hook maintains it or a
  procedure does, and the CLI writes it the same way regardless. The `.spike`
  marker is the same — a plain file the procedural layer can check just as a
  hook can.
- **`CLAUDE.md`** → the new runtime's always-loaded instruction file.
  `AGENTS.md` is your starting point — it is already the runtime-neutral
  version; you specialise it to the new runtime's mechanics the way `CLAUDE.md`
  specialises it to Claude Code's.
- **`scripts/`** → `install.sh` is rewritten to wire the new adapter into the
  new runtime's config locations. `swarm.sh` and `integrate.sh` are git
  operations and largely portable as-is *if* the new runtime's isolation
  mechanism is git worktrees; if it is something else, they are rewritten
  against that mechanism. `validate.sh` checks repo coherence and is mostly
  portable.

### The test of a correct port

A port is correct when a task framed under the new runtime produces the same
`route.md`, the same `task.yml`, the same artifacts in the same
`.compass/work/<task-slug>/` layout, and obeys the same guardrails — such that
a Claude Code session could `/compass:resume` a task the other runtime
started, and vice versa. The methodology layer is the shared *contract*; the
kit layer is the shared *mechanism* — and because both adapters call the same
kit rather than each implementing route composition and guardrail checking
themselves, the deterministic parts are not merely *equivalent* across
runtimes, they are *identical*. That is a stronger guarantee than the two-layer
design could offer, and it is why the kit was split out as its own layer.

---

## Why it is built this way

Adaptive frameworks have a credibility problem and a longevity problem.
Compass answers the credibility problem two ways: the routing policy bounds the
flex with routing guardrails the team owns, and the kit layer makes the
bounded parts *mechanically* deterministic — same readings, same route, every
runtime. It answers the longevity problem here: by keeping both the framework
itself (the methodology layer) and its mechanism (the kit layer) free of any
one runtime's syntax, so that when the runtime landscape shifts — and it will
— Compass is a rewrite of the adapter, not a rewrite of the framework or the
CLI. The methodology is the asset and the kit is its working machinery; the
adapter is just how this year's tool reaches them.
