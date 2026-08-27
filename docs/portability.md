# Portability

Compass runs on Claude Code today, but most of Compass is deliberately runtime
neutral. A port should replace the adapter, not fork the methodology or
reimplement the policy engine.

## The three-layer boundary

| Layer | Responsibility | Representative files | Porting rule |
|---|---|---|---|
| Methodology | Defines the flow, roles, artefacts, guardrails and strategies. | `docs/`, `approaches/`, templates, governance Markdown | Reuse. |
| Kit | Computes routes, validates state and writes mechanical evidence. | `cli/`, governance YAML, schemas, `manifest.yml` | Invoke. |
| Adapter | Maps Compass into a particular agent runtime. | commands, agents, skills, hooks, runtime instructions and install wiring | Rebuild. |

The boundary follows the determinism model:

- the adapter produces an assessment because assessment requires judgement;
- the kit computes the delivery approach because that must be deterministic; and
- the adapter orchestrates the resulting flow while calling the kit for
  checks and state mutations.

A port that independently implements routing or guardrails may resemble
Compass, but it will drift from Compass policy.

## Runtime adapter contract

### The Claude Code adapter layer

The shipped adapter is Claude Code: `commands/` are the stage interface,
`agents/` the distinct contexts, `skills/` the loadable procedures, `hooks/`
the pre-action enforcement, and `.claude-plugin/` the install wiring. A port
rebuilds that layer and reuses everything under it.

```
commands/        the stage interface (the /compass: namespace)
agents/          router, spec-author, planner, orchestrator, builder,
                 verifier, reviewer, product-owner, product-marketer,
                 architect
skills/          adaptive-routing, bdd-specification, tdd-discipline,
                 intent-interview, worktree-multiagent, governance-check,
                 traceability, evidence-gates, role-translation
hooks/           pre-tool.sh, post-tool.sh, stop.sh, session-start.sh
bin/compass      the shim that puts the kit on PATH
.claude-plugin/  the plugin manifest and marketplace entry
```

`architect` is the one to watch when porting: it is an advisory
perspective over the pipeline rather than a sixth entry-point role, so a port
that maps roles one-to-one will either lose architect or promote it into
a role it was deliberately not made.

A conforming adapter must satisfy the following requirements.

### 1. Assess before changing delivery artefacts

The runtime must recognise intent to build, change or fix files, even when the
user does not type an explicit Compass command.

Before the first delivery change it must:

1. assess risk, familiarity, size, intent and role;
2. record the assessment in the manifest;
3. call `compass approach evaluate --write`; and
4. present the human-readable approach for approval.

Conversation and read-only exploration do not require an issue. A delivery
change does.

### 2. Expose the delivery flow

The adapter must expose the eight methodological stages, whether as six user
commands or an equivalent interface:

```text
triage → define → refine → design → breakdown → implement → verify → ship
```

It must honour the stage weights and omissions computed by the route, and
write the selected artefacts using Compass templates.

### 3. Call the kit

The adapter must invoke, rather than reproduce, the kit's deterministic
operations. At minimum:

| Need | Kit command |
|---|---|
| Compute or update a route | `compass approach evaluate` |
| Validate an issue | `compass check` |
| Record red and green tests | `compass tdd-red`, `compass tdd-green` |
| Validate governance and issue schemas | `compass policy lint`, `compass issue lint` |
| Check cross-artefact coherence | `compass analyze` |
| Run the CI lane | `compass ci` |
| Surface calibration signals | `compass retro`, `compass rework-scan`, `compass flow` |

Schema-owning state changes should also use kit commands where one exists,
rather than editing `manifest.yml` ad hoc.

### 4. Preserve the safety contract

The adapter must call `compass check` at verify and before ship, honour its
exit code and preserve required human approvals.

**Getting the contract into a session.** Compass's rules of behaviour live in
`compass-contract.md`, and on Claude Code a `SessionStart` hook injects it at
startup, on clear and on compact, so the model has it without choosing to load
anything. That is an adapter feature, not a portable one: a runtime with no
session-start event has to reach the same outcome another way - a system
prompt, an always-loaded instruction file, or the equivalent of `CLAUDE.md`.
What must not change is that the contract exists once. Restating it per
runtime is how the Claude Code adapter ended up with two copies that drifted
until one named nine agents and the other ten.

BDD and TDD are default strategies. When the runtime supports pre-action hooks,
the adapter should enforce red-before-green mechanically and make the hook
route-aware so it does not block spikes. Without hooks, the adapter must make
the check an explicit implementation step.

An adapter limitation may reduce convenience or parallelism. It must not
silently weaken a guardrail.

### 5. Support the five entry-point roles

The runtime needs distinct entry paths for product, design, engineering,
marketing and QA. All five contribute to the same acceptance specification and
produce their normal Compass artefacts.

The adapter must preserve role-dependent gates such as intent fidelity and
claim traceability. Otherwise the role is decorative rather than operational.

### 6. Persist state on disk

Nothing essential may live only in conversation. The adapter must maintain:

```text
.compass/current-task
.compass/work/<issue>/README.md
.compass/work/<issue>/manifest.yml
.compass/work/<issue>/delivery-approach.md
.compass/work/<issue>/evidence/
```

It adds the route-selected product, requirements, design, delivery, quality and
launch artefacts alongside them.

A different session or runtime should be able to resume by reading this state.

### 7. Provide safe delivery orchestration

The adapter must support solo delivery. Pair and multiagent approaches require
isolated workspaces plus a single integration owner.

The reference adapter uses Git worktrees. A runtime may use another mechanism,
but each subtask must be able to run a failing test cycle without destabilising
the others. If equivalent isolation is unavailable, cap the orchestration and state
the limitation.

## Conformance mapping

### The mapping table

A port should document this table before implementation. The cross-issue kit
calls are listed with it, because an adapter that routes only the per-issue
verbs will look complete and lose the view across work in flight:

| Kit call | What a port loses without it |
|---|---|
| `compass analyze` | nothing reports where an issue's own artifacts disagree |
| `compass flow` | no view of blockers or owed follow-ups across issues |
| `compass next` | the session guesses which stage comes next |
| `compass retro` | no signal that triage is systematically mis-sizing work |
| `compass rework-scan` | add-then-delete churn stays invisible |
| `compass follow-up` | an owed follow-up can never be settled, so shipping stays blocked |
| `compass adr` | decision records are hand-numbered, and numbers get reused |


| Compass capability | Target runtime mechanism | Status or limitation |
|---|---|---|
| Always-loaded operating instructions |  |  |
| Intent-triggered assessment |  |  |
| User commands or stage interface |  |  |
| Kit CLI invocation |  |  |
| Pre-action enforcement |  |  |
| Post-action issue logging |  |  |
| Session-end status check |  |  |
| Role entry points |  |  |
| Distinct agent contexts |  |  |
| Isolated parallel workspaces |  |  |
| CI integration |  |  |
| Install surface (`bin/compass`, `.claude-plugin/`) |  |  |

An empty cell is a design question, not evidence of equivalence.

## What to reuse

A port should normally keep these unchanged:

- methodology and conceptual documentation;
- governance prose and machine-readable policy;
- approach definitions and rubric;
- artefact templates;
- CLI, schemas and vendored dependencies;
- issue directory layout; and
- CI's `compass ci` contract.

Runtime-specific quick-start instructions may be added without changing the
shared methodology.

## What to implement

The adapter normally supplies:

- the target runtime's commands or modes;
- agent or persona definitions;
- skill-loading or equivalent procedural context;
- pre-action, post-action and stop behaviour where supported;
- the always-loaded runtime instruction file;
- plugin or configuration manifests;
- installation and upgrade wiring; and
- isolated parallel execution where supported.

`AGENTS.md` is the runtime-neutral starting point. The Claude Code adapter's
`CLAUDE.md`, commands and hooks are a reference implementation, not the
portable contract itself.

## Conformance test

A port is conforming when the same assessed issue and policy produce:

- the same computed approach;
- a schema-compatible `manifest.yml`;
- the same required artefact and gate set;
- equivalent typed evidence and approval records;
- the same `compass check` verdict; and
- an issue that another Compass runtime can resume without translation.

Test this in both directions: start an issue in each runtime and resume it in
the other. Differences in terminal presentation are acceptable. Differences
in policy outcome or persisted meaning are not.

## Porting sequence

1. Complete the conformance mapping.
2. Wire the target runtime to the unchanged kit CLI.
3. Implement assessment and the six user-facing flow commands.
4. Add role entry points.
5. Add persistence and resumption.
6. Add the strongest enforcement the runtime supports.
7. Add safe parallelism, or declare a orchestration cap.
8. Run cross-runtime conformance tests.
9. Document install, security and known limitations.

The methodology is the long-lived asset, the kit is its deterministic
mechanism, and the adapter is how a particular runtime reaches both.
