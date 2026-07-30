# Compass - Runtime-Neutral Agent Instructions

This file is the portable expression of Compass. `CLAUDE.md` is the Claude
Code adapter; this file is the same intent without runtime-specific syntax,
for any other agent runtime (Codex, Amp, Cursor, OpenCode, a custom harness).

Compass is built in three layers. The **methodology layer** - `docs/`,
`governance/` `.md` files, `routes/`, `templates/` - *is* the framework, in
plain markdown. The **kit layer** - `cli/compass`, `governance/*.yml`,
`schemas/` (executable JSON Schema, draft-07, validated against when the
optional `jsonschema` library is installed), the `task.yml` spine - is the
deterministic mechanism: a plain CLI whose only hard dependency is PyYAML,
**not** runtime-specific. The **adapter layer** wires both into one runtime.
Porting Compass means satisfying the contract below by rewriting *only the
adapter layer* - the methodology and kit layers are already runtime-neutral,
and a portable adapter should *shell out to the kit-layer CLI* for the
deterministic parts rather than reimplement them. See `docs/portability.md` for
the full contract.

---

## What any Compass runtime must do

**1. Frame before changing anything.** Before a task modifies code, specs, or
product artifacts, run the Needle: read the four context dimensions (blast
radius, terrain, magnitude, intent & role) - that is judgement, and judgement
is the adaptivity, so the runtime must produce it. Composing the route *from*
those readings is mechanism, not judgement: a portable runtime should shell out
to `compass route evaluate` (the kit-layer CLI) rather than reimplement route
composition, so that the same readings plus the same policy yield the same
route on every runtime. The runtime records the readings in `task.yml`, runs
the evaluator, and writes the human-readable `route.md`. The route is computed
from context, not chosen from a menu. Genuinely exploratory work is not exempt
from Frame - it composes a **Spike** route.

**Trigger Frame on intent, not just on the literal command.** When the user
describes intent to build, change, or fix code - even when they do not type
`/compass:frame` (or the adapter's equivalent) - the adapter must invoke Frame
before any artifact-changing tool call. Explicit invocation always works
regardless. If `.compass/current-task` already points at a framed task, do not
re-Frame - proceed in the task's recorded route. This intent-recognition is an
adapter responsibility (it is *when* to invoke Frame, not what Frame does);
methodology describes Frame as a phase, this rule describes the trigger.

**2. Walk the eight-phase pipeline.** `Frame → Specify → Clarify → Plan →
Distribute → Build → Verify → Land`. The route says which phases are
full-weight, which collapse, and which are skipped - and why. Each phase emits
its artifact (templates in `templates/`) to the task's working directory.

**3. Enforce the guardrails - few, hard, never crossed:**
   - **G1 Tested before it lands:** no code reaches `main` without a passing
     test it traces to.
   - **G2 Acceptance defined before it is built:** no code without a stated,
     checkable acceptance criterion.
   - **G3 Traceability:** code → criterion → intent, and claim → criterion.
   - **G4 Evidence, not assertion:** guardrails clear with command output, not
     claims. The Definition of Done is itself a typed gate - every unchecked
     DoD item must reference typed inline evidence as `(evidence: EV-<id>)` or
     a filed backfill as `(backfill: BF-<id>)`, or be ticked `[x]` if a human
     has actually done the work. Bare unchecked items fail `compass check`'s
     `dod-evidence-typed` rule. An adapter that emits DoD output is
     responsible for emitting it in this form.
   - **G5 Human sign-off on the irreversible:** data, money, auth, privacy get
     a human checkpoint.

   **BDD and TDD are default *strategies*, not guardrails** - the strong,
   shipped-on way to satisfy G1 and G2. A runtime should enforce the
   red-before-green strategy *mechanically* if it can (Claude Code uses a
   route-aware pre-tool hook that does not block on Spike); if it cannot, it
   enforces it procedurally. But the hard line a runtime must never let slip
   is the guardrail *outcome* (G1: tested before it lands), not the ritual.

   The guardrail *checks* are mechanism, not judgement - so a portable runtime
   should run them via the kit-layer CLI rather than reimplement them:
   `compass check` runs the `governance/guardrails.yml` checks against the
   task's `task.yml` and `evidence/`, and `compass tdd-red` / `compass
   tdd-green` run a test, assert fail/pass, and write the evidence records the
   checks read. Gate evidence in `task.yml` is **typed** - a `{type, path}`
   record, not a bare path - and `guardrails.yml` declares which evidence types
   each gate accepts, so a mechanical gate cannot be cleared with a written
   note; `compass check` enforces that. The runtime's job is to *call* these at
   the right phases, not to re-derive what they do. Governance is a gradient:
   the shipped default guardrails and strategies apply with zero project setup;
   project-specific governance is accreted, not required up front.

   **Artifacts are written for a cold reader** (strategy S7). Every artifact a
   runtime emits is read later by someone who was not in the conversation, so
   it states its context before its detail, resolves its own references rather
   than pointing at a discussion ("Option 2", "per the review"), and stops when
   it has said the thing. Commit messages and pull-request bodies the runtime
   generates carry no agent co-author trailer and no "Generated with" footer;
   `devlog.md` and `task.yml` already record provenance in a form the framework
   can read. Like every strategy this is assessed at Verify, never gating.

**4. Support five roles as full citizens.** Engineer, product owner/manager,
product marketer, designer, QA. Each has an entry point and artifacts that
plug into the same pipeline. The BDD scenario file is the shared substrate
read through five lenses - do not reduce it to an engineering-only artifact.

**5. Support solo / pair / swarm topologies.** On larger routes, Plan produces
a distribution map and Distribute parallelises across isolated workspaces
(git worktrees in the reference implementation), one agent per stream, with a
coordinating orchestrator that owns integration at Land. A runtime without
worktrees must provide equivalent isolation or cap itself at solo/pair.

**6. Shell out for CI and the feedback loop too.** Two cross-task kit commands
round out the contract, and a portable runtime should call them rather than
reinvent them. `compass ci` runs the full mechanical gate suite (`policy lint`
+ `task lint` + `check` for every task) and aggregates exit codes - the CI
integration is "run `compass ci`, honour the exit code" (see `ci/README.md`).
`compass calibration` aggregates the `reframes` log across all tasks and
reports whether the Needle is systematically over- or under-sizing routes - the
framework's own feedback loop. The adapter wires these into the runtime's CI
and reporting surfaces; it does not re-derive them.

## What a runtime adapter must provide

| Methodology concept | Adapter must map it to… |
|---|---|
| The eight phases | Invocable commands or equivalent |
| The Needle | A triage routine that produces the readings, then *calls the kit* (`compass route evaluate`) to compose the route |
| The kit-layer CLI | A shell-out, not a reimplementation - the adapter runs `compass route evaluate`, `compass check`, `compass tdd-red/green`, and `compass analyze` (cross-artifact coherence) for the deterministic parts |
| CI and the feedback loop | A shell-out to `compass ci` (honour the exit code), `compass calibration` (the re-frame feedback loop), `compass rework-scan` (cross-task rework signal), and `compass flow` (cross-task view; `--digest` writes a dated digest combining rework-scan and calibration) |
| Subagents (navigator, spec-author, planner, orchestrator, builder, verifier, reviewer, product-lens, marketing-lens, architect-lens) | Distinct agent contexts or personas. The 10th - architect-lens - applies a lens (not an entry-point role): reads the project's `architecture/` artifacts (system-context, relations, ownership, ADRs) at Frame and annotates `plan.md` via `architecture-notes.md` at Plan. Consulted by `spec-author` and `planner`; never writes feature code |
| Skills | Loadable procedural-knowledge modules |
| Guardrail enforcement | `compass check` for the mechanical checks; hooks if available for red-before-green, procedural checks otherwise |
| Role entry points | Distinct session-start modes |
| Per-task next-step + backfill management | The adapter wires `compass next` (surface the next action on the current task) and `compass backfill pay` (mark an owed backfill as paid) into its task-resumption and Land flows |
| ADR creation | `compass adr new` (creates a numbered ADR file under `architecture/decisions/`) - the adapter exposes this in whatever shape its agents use for recording architectural decisions |

The kit layer (`cli/compass`, `governance/*.yml`, `schemas/`, `task.yml`) is
itself runtime-neutral - an adapter does not rewrite it, it invokes it. The
only thing the adapter owes the kit is a `.compass/current-task` pointer (or an
explicit `--task` slug) so the CLI can resolve which task it is acting on.

## State on disk

All task state is files, not conversation. `governance/` at the project root -
the `.md` files and the `.yml` files the CLI runs - or the framework's shipped
defaults if a project has not run init; per-task artifacts in a
`.compass/work/<task-slug>/` directory, including `task.yml` (the
machine-readable task spine), `evidence/` (the CLI's test and gate records),
and - when the project ships an `architecture/` directory - two derived
files Frame writes when present: `architecture-loaded.yml` (the per-task
snapshot of which cross-task architectural state was loaded) and
`architecture-notes.md` (annotations the architect-lens writes on
`plan.md`, *not* a parallel spec); a `.compass/current-task` pointer so the
CLI and any hooks resolve "the current task" unambiguously. A different
session, agent, or runtime must be able to resume a task by reading
`route.md`, `task.yml`, and the artifacts - nothing essential lives only in
context.
