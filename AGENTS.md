# Compass - Runtime-Neutral Agent Instructions

This file is the portable expression of Compass. `CLAUDE.md` is the Claude
Code adapter; this file is the same intent without runtime-specific syntax,
for any other agent runtime (Codex, Amp, Cursor, OpenCode, a custom harness).

It speaks the frozen v2 vocabulary (`governance/terminology.yml`). The
commands, filenames and machine keys carry their v2 names - the rename slices
have shipped - and where a name still reads oddly it appears as code, exactly
as the machinery spells it.

Compass is built in three layers. The **methodology layer** - `docs/`,
`governance/` `.md` files, the delivery-approach reference docs, `templates/`
- *is* the framework, in plain markdown. The **kit layer** - `cli/compass`,
`governance/*.yml`, `schemas/` (executable JSON Schema, draft-07, validated
against when the optional `jsonschema` library is installed), the `manifest.yml`
issue manifest - is the deterministic mechanism: a plain CLI that bundles the
one third-party library it needs (PyYAML, at `cli/vendor/yaml/` - see
`THIRD-PARTY-NOTICES.md`), **not** runtime-specific. The **adapter layer** wires
both into one runtime. Porting Compass means satisfying the contract below by
rewriting *only the adapter layer* - the methodology and kit layers are
already runtime-neutral, and a portable adapter should *shell out to the
kit-layer CLI* for the deterministic parts rather than reimplement them. See
`docs/portability.md` for the full contract.

---

## What any Compass runtime must do

**1. Assess before changing anything.** Before an issue modifies code, specs,
or product artifacts, run triage: read the four assessment dimensions - risk,
familiarity, size, and goal - that is judgement, and judgement is the
adaptivity, so the runtime must produce it. Composing the delivery approach
*from* that assessment is mechanism, not judgement: a portable runtime should
shell out to `compass approach evaluate` (the kit-layer CLI) rather than
reimplement the composition, so that the same assessment plus the same policy
yield the same approach on every runtime. The runtime records the assessment
in the manifest (`manifest.yml`), runs the evaluator, and writes the
human-readable approach record (`delivery-approach.md`). The approach is computed from
context, not chosen from a menu. Genuinely exploratory work is not exempt
from triage - it composes a **spike**.

**Trigger triage on intent, not just on the literal command.** When the user
describes intent to build, change, or fix code - even when they do not type
the adapter's triage command - the adapter must run triage before any
artifact-changing tool call. Explicit invocation always works regardless. If
`.compass/current-task` already points at a triaged issue, do not re-triage -
proceed with the issue's recorded delivery approach. This intent-recognition
is an adapter responsibility (it is *when* to trigger triage, not what triage
does); methodology describes the stage, this rule describes the trigger.

**2. Walk the eight-stage pipeline.** Assess, define acceptance criteria,
requirements review, design, break down the work, implement, test & review,
ship. The delivery approach says which stages are full-weight, which
collapse, and which are skipped - and why. Each stage emits its artifact
(templates in `templates/`) to the issue's working directory.

**3. Enforce the guardrails - few, hard, never crossed:**
   - **Tested before it ships:** no code reaches `main` without a passing
     test it traces to.
   - **Acceptance defined before it is built:** no code without a stated,
     checkable acceptance criterion.
   - **Traceability:** code → criterion → intent, and claim → criterion.
   - **Evidence, not assertion:** guardrails clear with command output, not
     claims. The Definition of Done is itself a typed gate - every unchecked
     item must reference typed inline evidence as `(evidence: EV-<id>)` or a
     filed follow-up as `(follow-up: BF-<id>)`, or be ticked `[x]` if a human
     has actually done the work. Bare unchecked items fail `compass check`'s
     `dod-evidence-typed` rule. An adapter that emits Definition of Done
     output is responsible for emitting it in this form.
   - **Human sign-off on the irreversible:** data, money, auth, privacy get a
     human checkpoint.

   **BDD and TDD are default *strategies*, not guardrails** - the strong,
   shipped-on way to satisfy the first two guardrails. A runtime should
   enforce the red-before-green strategy *mechanically* if it can (Claude
   Code uses a pre-tool hook that is aware of the delivery approach and does
   not block on a spike); if it cannot, it enforces it procedurally. But the
   hard line a runtime must never let slip is the guardrail *outcome*
   (tested before it ships), not the ritual.

   The guardrail *checks* are mechanism, not judgement - so a portable
   runtime should run them via the kit-layer CLI rather than reimplement
   them: `compass check` runs the `governance/guardrails.yml` checks against
   the issue's manifest and `evidence/`, and `compass tdd-red` /
   `compass tdd-green` run a test, assert fail/pass, and write the evidence
   records the checks read. Gate evidence in the manifest is **typed** - a
   `{type, path}` record, not a bare path - and `guardrails.yml` declares
   which evidence types each gate accepts, so a mechanical gate cannot be
   cleared with a written note; `compass check` enforces that. The runtime's
   job is to *call* these at the right stages, not to re-derive what they do.
   Governance is a gradient: the shipped default guardrails and strategies
   apply with zero project setup; project-specific governance is accreted,
   not required up front.

   **Artifacts are written for a cold reader.** Every artifact a runtime
   emits is read later by someone who was not in the conversation, so it
   states its context before its detail, resolves its own references rather
   than pointing at a discussion, and stops when it has said the thing.
   Commit messages and pull-request bodies the runtime generates carry no
   agent co-author trailer and no "Generated with" footer; `devlog.md` and
   the manifest already record provenance in a form the framework can read.
   Like every strategy this is assessed at review, never gating.

**4. Support five roles as full citizens.** Engineer, product owner/manager,
product marketer, designer, QA. Each has an entry point and artifacts that
plug into the same pipeline. The acceptance-criteria file is the shared
substrate read through five role perspectives - do not reduce it to an
engineering-only artifact.

**5. Support solo / pair / multiagent orchestrations.** On larger delivery
approaches, design produces a distribution map and the breakdown stage
parallelises across isolated workspaces (git worktrees in the reference
implementation), one agent per subtask, with a coordinating orchestrator that
owns integration at ship time. A runtime without worktrees must provide
equivalent isolation or cap itself at solo/pair.

**6. Shell out for CI and the feedback loop too.** Two cross-issue kit
commands round out the contract, and a portable runtime should call them
rather than reinvent them. `compass ci` runs the full mechanical gate suite
(`policy lint` + `issue lint` + `check` for every issue) and aggregates exit
codes - the CI integration is "run `compass ci`, honour the exit code" (see
`ci/README.md`). `compass retro` aggregates the `reframes` log across
issues and reports whether triage is systematically over- or under-sizing
the process - the framework's own retrospective signal. The adapter wires
these into the runtime's CI and reporting surfaces; it does not re-derive
them.

## What a runtime adapter must provide

| Methodology concept | Adapter must map it to… |
|---|---|
| The eight stages | Invocable commands or equivalent |
| Assess | A routine that produces the assessment, then *calls the kit* (`compass approach evaluate`) to compose the delivery approach |
| The kit-layer CLI | A shell-out, not a reimplementation - the adapter runs `compass approach evaluate`, `compass check`, `compass tdd-red/green`, and `compass analyze` (cross-artifact coherence) for the deterministic parts |
| CI and the feedback loop | A shell-out to `compass ci` (honour the exit code), `compass retro` (the retrospective signal), `compass rework-scan` (cross-issue rework signal), and `compass flow` (cross-issue view; `--digest` writes a dated digest combining rework-scan and calibration) |
| Subagents (`router`, `spec-author`, `planner`, `orchestrator`, `builder`, `verifier`, `reviewer`, `product-owner`, `product-marketer`, `architect`) | Distinct agent contexts or personas. The 10th - `architect` - applies the architect perspective (not an entry-point role): reads the project's `architecture/` artifacts (system-context, relations, ownership, decision records) at triage and annotates the design via `architecture-notes.md`. Consulted by `spec-author` and `planner`; never writes feature code |
| Skills | Loadable procedural-knowledge modules |
| Guardrail enforcement | `compass check` for the mechanical checks; hooks if available for red-before-green, procedural checks otherwise |
| Role entry points | Distinct session-start modes |
| Per-issue next-step + follow-up management | The adapter wires `compass next` (surface the next action on the current issue) and `compass follow-up resolve` (mark an owed follow-up as settled) into its issue-resumption and shipping flows |
| Decision-record creation | `compass adr new` (creates a numbered decision record under `architecture/decisions/`) - the adapter exposes this in whatever shape its agents use for recording architectural decisions |

The kit layer (`cli/compass`, `governance/*.yml`, `schemas/`, `manifest.yml`) is
itself runtime-neutral - an adapter does not rewrite it, it invokes it. The
only thing the adapter owes the kit is a `.compass/current-task` pointer (or
an explicit `--issue` slug) so the CLI can resolve which issue it is acting
on.

## Writing voice

Every artifact a runtime writes is prose someone reads later, and prose that
narrates the pipeline instead of communicating a decision teaches nothing.
`skills/compass-runtime/writing-voice.md` states the rule in one line,
carries real before/after pairs harvested from this project's own archive,
and names the tells that mark the narrating kind. A runtime's session-facing
output - devlog entries, requirements reviews, replies to the person driving
it - should read the way that reference asks: what happened, what is
needed, never which stage is running.

### Reporting to the person driving the runtime

Read a report back for terms of art before sending it; afterwards is too late,
because a sentence in conversation lands once. Give it four parts: what I did,
outstanding questions numbered when there is more than one, what I need from
you, and what I intend to do next. Sections stay short, a snippet sits under the
point it belongs to, and a large change may run long - cut the account of how
the work went, never the substance. Each heading answers a question the reader
already has, which is what leaves jargon nowhere to hide.

## State on disk

All issue state is files, not conversation. `governance/` at the project
root - the `.md` files and the `.yml` files the CLI runs - or the framework's
shipped defaults if a project has not run init; per-issue artifacts in a
`.compass/work/<issue-slug>/` directory, including `manifest.yml` (the
manifest), `evidence/` (the CLI's test and gate records),
and - when the project ships an `architecture/` directory - two derived
files triage writes when present: `architecture-loaded.yml` (the per-issue
snapshot of which cross-issue architectural state was loaded) and
`architecture-notes.md` (annotations the architect perspective writes on the
design, *not* a parallel spec); a `.compass/current-task` pointer so the CLI
and any hooks resolve the current issue unambiguously. A different session,
agent, or runtime must be able to resume an issue by reading the approach
record (`delivery-approach.md`), the manifest, and the artifacts - nothing essential lives
only in context.
