# Compass - Operating Instructions for Claude Code

You are running inside a project that uses **Compass**, an adaptive
spec-driven development framework. This file tells you how to behave. It is
loaded on every session.

If anything here conflicts with `docs/methodology.md`, the methodology doc
wins - but you should never see a conflict, because this file is the runtime
expression of that doc.

If this is your first Compass session, also read `docs/five-minutes.md` for
the mental model and a worked end-to-end example, and
`docs/safety-contract.md` for the seven things Compass guarantees (and the
things it explicitly does not claim). They are short, and they ground
everything below.

A note on names while v2 is in flight: this file speaks the frozen v2
vocabulary (`governance/terminology.yml` - the build enforces it). The
commands, artifact filenames, and machine keys now carry their v2 names;
the CLI's own verbs keep their v1 names until their rename slice ships.
Wherever a live v1 name is unavoidable it appears as code, exactly as the
machinery spells it today. The `compass-runtime` skill carries the full
mapping from each pipeline stage to its current command, and each retired
command name remains as a redirect stub for one major version.

---

## The one rule that creates every other rule

**Never skip triage.** Before any issue that changes code, specs, or product
artifacts, triage it: run `/compass:triage`. Triage reads the four assessment
dimensions - risk, familiarity, size, and goal - that is judgement, and the
judgement is yours - and records them in the issue spine (`task.yml`, under
`.compass/work/<task-slug>/`, in the spine's own key names). It then hands
them to the **mechanism**: the command runs `compass approach evaluate --write`,
which applies `governance/routing-policy.yml` deterministically and folds the
computed delivery approach - its stages and its gates - back into the spine.
You also write the human-readable record of the approach (`delivery-approach.md`). You do
not choose a process, and you do not compose the delivery approach in your
head - you assess the work, the CLI computes the approach.

`/compass:triage` also writes `.compass/current-task` - a one-line pointer to
the active issue. The hooks and the CLI both rely on it: `compass check`,
`compass tdd-red`, and the pre-tool hook resolve the current issue through
that pointer, so keep it pointing at the issue you are actually working.

When the assessment turns out to have been misread, re-assess through the
same mechanism: `/compass:triage --reassess` re-runs the evaluator, detects
that the approach changed, and records the change in the spine's `reframes:`
log - pass `--reason "..."` so the entry says *why*. That log is the
framework's retrospective signal: `compass retro` aggregates it across
issues and reports whether triage is systematically over- or under-sizing
the process. Re-assessing is a normal event; an unrecorded one is a lost
signal.

The only work exempt from triage is conversation - answering a question,
explaining code, reading to understand. The moment a tool call would change
a file, triage must already have run for the current issue. If the work is
genuinely exploratory - you cannot yet state what would be delivered - that
is not an exemption; that is a **spike**, and triage still runs.

**Trigger triage on intent, not just the literal command.** When the user describes intent to build, change, or fix code - even if they do not type `/compass:triage` - invoke `/compass:triage` before any artifact-changing tool call. The pre-tool hook still enforces the `.red` marker; this rule adds the upstream trigger from intent recognition. Explicit invocation of any Compass command always works regardless. If `.compass/current-task` already points at a triaged issue, do not re-run triage - proceed with the issue's recorded delivery approach.

`/compass:init` is **optional**. The default guardrails and default
strategies ship active with the framework, so triage works with zero project
setup. Init is how a project *accretes* its own governance later - not a
prerequisite for the first issue.

## Governance - guardrails and strategies

Compass is governed by two kinds of thing, and you must keep them straight.

- **Guardrails** are few, hard, checkable, blocking. Delivery approaches
  adapt ceremony *around* them; no approach, agent, or convenience crosses
  one. If an approach appears to ask you to cross a guardrail, stop - the
  approach definition has a bug. The five shipped defaults, stated plainly:
  1. **Every change lands with a passing automated test that covers it.**
     Checked before shipping, with evidence.
  2. **Acceptance criteria exist before the code is written.** No code that
     no stated, checkable criterion describes.
  3. **Everything traces.** Code to acceptance criterion to stated reason,
     and claim to criterion. Maintain it as you go, not at the end.
  4. **Evidence, not assertion.** Clear a guardrail with pasted command
     output and artifacts. "The tests pass" without the run clears nothing.
  5. **A human signs off on the irreversible.** Data loss, money, auth,
     privacy - these get an explicit human checkpoint before they ship.
- **Strategies** are many, soft, directional, assessed. They bias your work;
  they do not block it. **BDD** (Given/When/Then scenarios as spec and
  acceptance check) and **TDD** (red-green-refactor) are the shipped default
  *strategies* - strong, on by default, the way you satisfy the first two
  guardrails. They are not guardrails: the *outcome* is hard, the *ritual*
  is the default method. `hooks/pre-tool.sh` enforces red-before-green and
  is aware of the delivery approach - it does not block on a spike, where
  the TDD strategy is suspended. Do not work around the hook where it does
  apply.

The conflict rule: a guardrail beats a strategy; strategy-versus-strategy is
triage's call (via the delivery approach) or a human's. **When your
recommendation and an instruction disagree, measure the disputed quantity
and report the numbers before defending either position** (`S11`) - the
disagreement is nearly always about a quantity someone has guessed, and the
guess is doing the arguing. Report what you find even when it undercuts you.
Read `governance/`
at the start of an issue - `guardrails.md`, `strategies.md`, and
`routing-policy.md` for the why; `routing-policy.yml` and `guardrails.yml`
are the machine-readable companions the CLI runs. The guardrail *checks* are
mechanical: `compass check` runs them against the issue spine and
`evidence/`, and `/compass:verify` calls it. Clear a guardrail with evidence
on disk, not a claim - the check looks for the evidence record, not your
word for it. Gate evidence in the spine is **typed** - a `{type, path}`
record (`test-run`, `command-output`, `human-approval`, `artifact`), not a
bare path - and `guardrails.yml` says which types each gate accepts. A
mechanical gate cannot be cleared with a written note; the type is checked,
not just the file's existence.

**How you write is governed too.** Assume the reader has zero context: give
the why before the detail, never leave a dangling reference, say what a
linked issue or pull request actually changed rather than only citing it,
and stop once you have said it. Commit messages and pull-request bodies
never carry an agent co-author trailer and never a "Generated with" footer.
A comment or docstring you are editing for any other reason gets its
retired vocabulary corrected on the way past. Comments are exempt from the
scan - nothing in them reaches a user - but they are what the next
user-facing string is copied from, so they decay rather than being swept.
This repository writes a plain hyphen where an em dash would go
(`tests/test_house_style.py` enforces that). And everything you write -
test names, comments, commit messages, artifacts - uses the frozen v2
vocabulary: `governance/terminology.yml` defines it and
`tests/test_terminology.py` enforces it, surface by surface, as the rename
proceeds.

## The pipeline

```
triage → define acceptance criteria → requirements review → design →
break down the work → implement → test & review → ship
```

Each stage has a slash command in `commands/` (current names in the
`compass-runtime` skill); run them in order. The delivery-approach record
says which stages are full-weight, which collapse, and which are skipped -
and it always states *why* a stage is skipped. Honour that; do not silently
re-skip or re-add stages.

After each stage, write its artifact to the issue's directory using the
matching template in `templates/`. Persistence over conversation: if it is
not on disk, it did not happen. Each stage also fills its section of the
spine as a by-product - triage writes the assessment, the acceptance stage
adds `scenarios`, implementation adds `changed_files`. The CLI reads and
writes it for you.

While **implementing**, drive the red-green cycle through the CLI, not by
hand: `compass tdd-red -- <test cmd>` runs the test, asserts it genuinely
fails, writes the `evidence/red.json` record and the `.red` marker the
pre-tool hook reads; `compass tdd-green -- <test cmd>` asserts it now
passes, writes `evidence/green.json`, and clears the marker. The marker is
only ever written after a real failure - that honesty is the point.

Two stage transitions carry an explicit checklist gate. Requirements review
ends with the **Definition of Ready** (the foot of `requirements-review.md`); on
delivery approaches where that review collapses (quick fix, hotfix, spike),
it is satisfied by construction. Before shipping comes the **Definition of
Done** (the foot of `verification-report.md`); its unchecked items carry
typed inline evidence tags - `(evidence: EV-id)` or `(follow-up: FU-id)` -
and a bare unchecked item fails `compass check`. Treat an unchecked box as a
closed gate.

Beyond the per-issue pipeline, two commands look across issues:
`/compass:status` reports one issue or a flat list; `/compass:flow` is the
managed cross-issue view - blockers, owed follow-ups, and a periodic digest.
Flow advises; it never gates, and it never sets issue state (state is always
inferred from artifacts on disk).

## Choosing agents and skills

- During **triage**, load the `adaptive-routing` skill and consider the
  `navigator` agent.
- While **defining acceptance criteria** and in **requirements review**,
  load `bdd-specification`; on brownfield work whose behaviour is not yet
  written down, also load `blueprint-distillation`. The `spec-author` agent
  owns these stages.
- During **design**, load `plan-authoring` (which optional design sections
  earn a place, and how they scale) and `governance-check` (how to check
  the finished design against `governance/`). The `planner` agent owns this.
- When **breaking down and implementing in parallel**, load
  `worktree-swarm`. The `orchestrator` agent coordinates; `builder` agents
  do the work, one per worktree. Each builder loads `tdd-discipline`.
- During **test & review**, the `verifier` and `reviewer` agents run; load
  `evidence-gates`. Load `receiving-code-review` when answering their
  comments.
- On an **unexpected test failure** while implementing, load
  `systematic-debugging` - and after three failed fixes, re-assess rather
  than attempt a fourth.
- For any role-facing work, load `role-translation` - it is how one set of
  acceptance criteria is read through five role perspectives. The
  `product-lens`, `marketing-lens`, and `architect-lens` agents apply
  specific perspectives. The `architect-lens` reads the project's
  `architecture/` artifacts and writes `architecture-notes.md` in the issue
  directory; `spec-author` and `planner` consult those notes rather than
  re-invoking it.
- `traceability` is loaded whenever an artifact is written.

## Roles

Compass has five roles, four of them non-engineering, all full pipeline
citizens. If a session opens with a role entry point - `/compass:intent`,
`/compass:position`, `/compass:wireframe`, `/compass:roundtable` - adopt that
role's vocabulary and artifacts. Do not collapse a product owner's intake
into an engineering issue; the intake is upstream of the acceptance
criteria, and the criteria must be checked back against it.

## Worktrees and swarms

Only the `orchestrator` agent creates worktrees (`scripts/swarm.sh`) and
integrates them (`scripts/integrate.sh`). A `builder` agent works *inside*
an assigned worktree and never touches a sibling's. The delivery approach's
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
│       ├── prd.md             Intake (if a product owner was involved)
│       ├── ui-contract.md       Designer contracts (if a designer was involved)
│       ├── acceptance-criteria.md      Acceptance criteria - the shared artifact
│       ├── requirements-review.md    (ends with the Definition of Ready gate)
│       ├── design.md              The design
│       ├── distribution-map.md  Swarm topology (initiative-scale work)
│       ├── positioning.md       Marketer messaging (if in play)
│       ├── launch-readiness.md  Marketer claims gate (if in play)
│       ├── verification-report.md  (ends with the Definition of Done gate)
│       ├── architecture-loaded.yml (what cross-issue architectural state was loaded)
│       ├── architecture-notes.md   (the architect perspective's annotations)
│       ├── evidence/            red.json/green.json + typed gate evidence
│       └── devlog.md            Append-only running log
└── flow/
    └── digest-<date>.md         Periodic cross-issue digest
```

The artifact filenames above are the live v1 names; they rename in their own
slice, and the tree here moves with them. `governance/` lives at the project
root - the `.md` prose and the `.yml` files the CLI runs - not under
`.compass/`. If `/compass:init` has not been run, the framework's shipped
`governance/` defaults apply as-is.

`architecture/` also lives at the project root, sibling to `governance/`.
**Compass itself ships one** - read it for the framework's own invariants,
ownership rules, and the decision records that codify the principles behind
the guardrails, the sizing model, and the role perspectives. It also doubles
as a worked example for adopters. Triage loads it (when present) into
`architecture-loaded.yml` in the issue directory; projects without
`architecture/` continue to work.

## Writing voice

A session narrates the framework when it announces the stage it is entering
or the step it is about to take - you can already see the pipeline; naming
it tells you nothing. Communicate the decision instead: what you found, what
you need, what changed. `skills/compass-runtime/writing-voice.md` carries
the principle in one line, real before/after pairs pulled from this
project's own archive, and the tells to watch for. Read it before you write
a devlog entry, a requirements review, or a line of dialogue with the person
you are working with - and before you say anything out loud in this
conversation.

## When you are unsure

Re-read the delivery-approach record (`delivery-approach.md`). It was written at triage
precisely so that a later session - or a different agent - can pick up the
issue without re-deriving the process. If it does not answer the question,
triage under-sized the process; say so and re-assess rather than improvise.
