---
name: compass-runtime
description: The Compass operating contract - how to behave in a Compass-governed project. Load this at the start of ANY issue that will change code, specs, or product artifacts, before doing anything else. Defines the one rule (never skip triage), the guardrails-vs-strategies governance model, the eight-stage pipeline and the current command name for each stage, which agents and skills to load per stage, the five roles, worktrees/swarms, and where issue state lives. This is the runtime expression of docs/methodology.md; for plugin-installed projects it is the bootstrap that a clone-installed project gets from the repo's CLAUDE.md.
---

# Compass - runtime operating contract

You are running inside a project that uses **Compass**, an adaptive
spec-driven development framework. This skill tells you how to behave. Load
it whenever a Compass-shaped issue begins. If anything here conflicts with
`docs/methodology.md`, the methodology doc wins - but you should never see a
conflict, because this is the runtime expression of that doc.

If this is your first Compass session, also read `docs/five-minutes.md` for
the mental model and a worked example, and `docs/safety-contract.md` for the
seven things Compass guarantees (and what it explicitly does not claim).

This skill speaks the frozen v2 vocabulary (`governance/terminology.yml`).
The commands, artifact filenames, and machine keys now carry their v2
names; the CLI's own verbs keep their v1 names until their rename slice
ships. The table below is the stage-to-command map, and it is the one place
the mapping lives. Each retired command name remains as a redirect stub for
one major version.

## The stages and their commands

| Stage (v2 name) | Command | Artifact it writes |
|---|---|---|
| Triage | `/compass:assess` | `delivery-approach.md` (the delivery-approach record) + the spine's assessment |
| Define acceptance criteria | `/compass:define` | `acceptance-criteria.md` |
| Requirements review | `/compass:refine` | `requirements-review.md` (ends with the Definition of Ready) |
| Design | `/compass:design` | `technical-design.md` (+ `distribution-map.md` on parallel work) |
| Break down the work | `/compass:breakdown` | worktrees + stream charters |
| Implement | `/compass:implement` | code + the red and green records (named by binding) |
| Test & review | `/compass:verify` | `verification-report.md` (ends with the Definition of Done) |
| Ship | `/compass:ship` | the integration commit + settled follow-ups |

Cross-issue: `/compass:status` (one issue or a flat list), `/compass:flow`
(the managed cross-issue view - advisory, never gating). Role entry points:
`/compass:intent` (product owner), `/compass:position` (marketer),
`/compass:design` (designer - produces the UI contract),
`/compass:roundtable` (multi-role decisions). Setup: `/compass:init` is
optional - shipped governance defaults apply with zero setup.

## The one rule that creates every other rule

**Never skip triage.** Before any issue that changes code, specs, or product
artifacts, run the triage command. Triage reads the four assessment
dimensions - risk, familiarity, size, and goal - that is judgement, and the
judgement is yours - and records them in the issue spine (`task.yml`). It
then hands them to the **mechanism**: `compass approach evaluate --write`
applies `governance/routing-policy.yml` deterministically and folds the
computed delivery approach, its stages and gates, back into the spine. You
also write the human-readable approach record (`delivery-approach.md`). You do not
choose a process, and you do not compose the approach in your head - you
assess the work, the CLI computes the approach.

Assess also writes `.compass/current-task` - a one-line pointer to the
active issue. The hooks and the CLI rely on it: `compass check`,
`compass tdd-red`, and the pre-tool hook resolve the current issue through
that pointer, so keep it pointing at the issue you are actually working.

When the assessment turns out to have been misread, re-assess through the
same mechanism: `/compass:assess --reassess` re-runs the evaluator, detects
that the approach changed, and records the change in the spine's `reframes:`
log - pass `--reason "..."` so the entry says *why*. `compass retro`
aggregates that log across issues and reports whether triage is
systematically over- or under-sizing the process - the retrospective signal.
Re-assessing is a normal event; an unrecorded one is a lost signal.

The only work exempt from triage is conversation - answering a question,
explaining code, reading to understand. The moment a tool call would change
a file, triage must already have run for the current issue. If the work is
genuinely exploratory - you cannot yet state what would be delivered - that
is not an exemption; that is a **spike**, and triage still runs.

## Governance - guardrails and strategies

Compass is governed by two kinds of thing, and you must keep them straight.

**Guardrails** are few, hard, checkable, blocking. Delivery approaches adapt
ceremony *around* them; no approach, agent, or convenience crosses one. If
an approach appears to ask you to cross a guardrail, stop - the approach
definition has a bug. The five shipped defaults, stated plainly:

1. **Every change lands with a passing automated test that covers it.**
   Checked at review and ship time, with evidence.
2. **Acceptance criteria exist before the code is written.** No code that no
   stated, checkable criterion describes.
3. **Everything traces.** Code to acceptance criterion to stated reason, and
   claim to criterion. Maintain it as you go, not at the end.
4. **Evidence, not assertion.** Clear a guardrail with recorded command output
   and artifacts. "The tests pass" without the run clears nothing.
5. **A human signs off on the irreversible.** Data loss, money, auth,
   privacy - these get an explicit human checkpoint before they ship.

**Strategies** are many, soft, directional, assessed. They bias your work;
they do not block it. **BDD** (Given/When/Then scenarios as spec and
acceptance check) and **TDD** (red-green-refactor) are the shipped default
*strategies* - strong, on by default, the way you satisfy the first two
guardrails. They are not guardrails: the *outcome* is hard, the *ritual* is
the default method. `hooks/pre-tool.sh` enforces red-before-green and is
aware of the delivery approach - it does not block on a spike, where the TDD
strategy is suspended. Do not work around the hook where it applies.

The conflict rule: a guardrail beats a strategy; strategy-versus-strategy is
triage's call (via the approach) or a human's. Read `governance/` at the
start of an issue - `guardrails.md`, `strategies.md`, `routing-policy.md`
for the *why*; `routing-policy.yml` and `guardrails.yml` are the
machine-readable companions the CLI runs. The guardrail *checks* are
mechanical: `compass check` runs them against the issue's spine and
`evidence/`, and the test & review command calls it. Clear a guardrail with
evidence on disk, not a claim - the check looks for the evidence record, not
your word for it. Gate evidence in the spine is **typed** - a `{type, path}`
record (`test-run`, `command-output`, `human-approval`, `artifact`), not a
bare path - and `guardrails.yml`'s `gate_evidence_requirements` say which
types each gate accepts. A mechanical gate cannot be cleared with a written
note; the type is checked, not just the file's existence.

## The pipeline

Run the stages in order (commands in the table above). The approach record
says which stages are full-weight, which collapse, and which are skipped -
and it always states *why* a stage is skipped. Honour that; do not silently
re-skip or re-add stages.

After each stage, write its artifact to `.compass/work/<task-slug>/` using
the matching template in `templates/`. Persistence over conversation: if it
is not on disk, it did not happen. Each stage also fills its section of the
spine as a by-product - triage writes the assessment, the acceptance stage
adds `scenarios`, implementation adds `changed_files`. The CLI reads and
writes it for you.

While **implementing**, drive the red-green cycle through the CLI, not by
hand: `compass tdd-red -- <test cmd>` runs the test, asserts it genuinely
fails, writes the red record and the `.red` marker the
pre-tool hook reads; `compass tdd-green -- <test cmd>` asserts it now
passes, writes the green record, and clears the marker. **The binding decides
the filename**: `--scenario TRC-x` writes `evidence/green-TRC-x.json`, an
unbound run writes `evidence/green.json`, and only that one file is written -
so recording a scenario never overwrites a record another gate cites. The
marker is
only ever written after a real failure - that honesty is the point.

Two stage transitions carry an explicit checklist gate. Requirements review
ends with the **Definition of Ready** (the foot of `requirements-review.md`); on
approaches where that review collapses (quick fix, hotfix, spike), it is
satisfied by construction. Before shipping comes the **Definition of Done**
(the foot of `verification-report.md`). Treat an unchecked box as a closed
gate.

## Choosing agents and skills

- During **triage**, load the `adaptive-routing` skill and consider the
  `navigator` agent.
- While **defining acceptance criteria** and in **requirements review**,
  load `bdd-specification`; on brownfield work whose behaviour is not yet
  written down, also load `blueprint-distillation`. The `spec-author` agent
  owns these stages.
- During **design**, load `plan-authoring` (which optional design sections
  earn a place) and `governance-check` (how to check the finished design
  against `governance/`). The `planner` agent owns this.
- When **implementing in parallel**, load `worktree-swarm`. The
  `orchestrator` agent coordinates; `builder` agents do the work, one per
  worktree. Each builder loads `tdd-discipline`.
- During **test & review**, the `verifier` and `reviewer` agents run; load
  `evidence-gates`. Load `receiving-code-review` when answering their
  comments.
- On an **unexpected test failure** while implementing, load
  `systematic-debugging` - and after three failed fixes, re-assess rather
  than attempt a fourth.
- For any role-facing work, load `role-translation` - it is how one set of
  acceptance criteria is read through five role perspectives. The
  `product-lens` and `marketing-lens` agents apply specific perspectives.
- `traceability` is loaded whenever an artifact is written.

## Roles

Compass has five roles, four of them non-engineering, all full pipeline
citizens. If a session opens with a role entry point, adopt that role's
vocabulary and artifacts. Do not collapse a product owner's intake into an
engineering issue; the intake is upstream of the acceptance criteria, and
the criteria must be checked back against it.

## Worktrees and swarms

Only the `orchestrator` agent creates worktrees (`scripts/swarm.sh`) and
integrates them (`scripts/integrate.sh`). A `builder` agent works *inside*
an assigned worktree and never touches a sibling's. The approach's
distribution map says how many streams exist; policy can cap the count. If
the approach is solo, there is no worktree - work on the current branch.

## Where state lives

```
.compass/
├── config.yml                  Project config (approach defaults, swarm caps)
├── current-task                One-line pointer to the active issue
├── work/
│   └── <task-slug>/            One directory per issue
│       ├── delivery-approach.md             The delivery-approach record (prose)
│       ├── task.yml             The machine-readable issue spine
│       ├── intent.md             Intake (if a product owner was involved)
│       ├── ui-contract.md       Designer contracts (if a designer was involved)
│       ├── acceptance-criteria.md      Acceptance criteria - the shared artifact
│       ├── requirements-review.md    (ends with the Definition of Ready gate)
│       ├── technical-design.md              The design
│       ├── distribution-map.md  Swarm topology (initiative-scale work)
│       ├── positioning.md       Marketer messaging (if in play)
│       ├── launch-readiness.md  Marketer claims gate (if in play)
│       ├── verification-report.md  (ends with the Definition of Done gate)
│       ├── evidence/            red/green records (named by binding) + typed gate evidence
│       └── devlog.md            Append-only running log
└── flow/
    └── digest-<date>.md         Periodic cross-issue digest
```

The filenames are the live v1 names; they rename in their own slice and this
tree moves with them. `governance/` lives at the project root - the `.md`
files and the `.yml` files the CLI runs - not under `.compass/`. If
`/compass:init` has not been run, the framework's shipped `governance/`
defaults apply as-is.

## Writing voice

Before writing a devlog entry, a requirements review, or anything else this
skill produces, read `skills/compass-runtime/writing-voice.md` - the
principle, real before/after pairs from this project's own archive, and the
tells that mark session prose narrating the pipeline instead of
communicating a decision.

## When you are unsure

Re-read the delivery-approach record (`delivery-approach.md`). It was written at triage
precisely so a later session - or a different agent - can pick up the issue
without re-deriving the process. If it does not answer the question, triage
under-sized the process; say so and re-assess rather than improvise.
