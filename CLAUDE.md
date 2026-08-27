# Compass - Operating Instructions for Claude Code

**The rules of behaviour are in `compass-contract.md`**, which the SessionStart
hook puts into every session in a Compass project. This file is the Claude Code
adapter: what is specific to running Compass in this repository, on top of that
contract. Where the two would say the same thing, this file points instead.


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

A note on names: this file speaks the frozen v2 vocabulary
(`governance/terminology.yml` - the build enforces it). The commands, the CLI's
verbs, the artifact filenames and the machine keys all carry their v2 names;
the rename slices have shipped. Where a name still reads oddly it appears as
code, exactly as the machinery spells it. The `compass-runtime` skill carries
the mapping from each pipeline stage to its command, and each retired name
remains as a redirect stub for one major version.

---

## Assessment, and what this adapter adds to it

The rule itself - assess before you change anything, trigger on intent rather
than on the literal command - is in `compass-contract.md`, which the
SessionStart hook has already put in this session. What follows is what is
specific to running Compass here.

`/compass:assess` writes `.compass/current-task`, a one-line pointer to the
active issue. `compass check`, `compass tdd-red` and the pre-tool hook all
resolve the current issue through it, so keep it pointing at the issue you are
actually working on.

**Re-assessing is a normal event; an unrecorded one is a lost signal.**
`/compass:assess --reassess` re-runs the evaluator, notices the approach
changed, and records it in the spine's `reassessments:` log. Pass
`--reason "..."` so the entry says why - `compass retro` aggregates those
across issues and reports whether assessment is systematically over- or
under-sizing the work.

Exploratory work is not exempt. If you cannot yet state what would be
delivered, that is a **spike**, and a spike is assessed like anything else.

`/compass:init` is optional and is not what creates the project: the five
entry points - `/compass:assess`, `/compass:intent`, `/compass:design`,
`/compass:position`, `/compass:roundtable` - run `compass init` first, which
creates `.compass/` if it is absent and says so. It creates project state
only, never `governance/`. The shipped guardrails and strategies are active
from the first command, so there is nothing to configure and no gate to clear
before the first issue; `/compass:init` is how a project accretes its own
governance later.

## Governance - guardrails and strategies

The five guardrails and the guardrails-versus-strategies split are in
`compass-contract.md`. Two things this adapter adds:

**The conflict rule.** A guardrail beats a strategy. Strategy against strategy
is the delivery approach's call, or a human's. And when your recommendation
and an instruction disagree, **measure the disputed quantity and report the
numbers before defending either position** (`S11`) - the disagreement is nearly
always about a quantity someone has guessed, and the guess is doing the
arguing. Report what you find even when it undercuts you.

**Where the rules actually live.** `governance/routing-policy.yml` and
`governance/guardrails.yml` are what the CLI runs; read those when you need to
know what will be enforced. The prose companions - `guardrails.md`,
`routing-policy.md`, `strategies.md` - explain why, and are read when a
question comes up rather than at the start of every issue.
`strategies.md` is 7,000 words: it is the reviewer's reference and the place a
strategy is defined, not a per-issue read.

The checks are mechanical. `compass check` runs `guardrails.yml` against the
spine and `evidence/`, and `/compass:verify` calls it. Gate evidence is
**typed** - a `{type, path}` record, not a bare path - and `guardrails.yml`
says which types each gate accepts, so a mechanical gate cannot be cleared
with a written note.

**How you write is governed too.** Assume the reader has zero context: give
the why before the detail, never leave a dangling reference, say what a linked
issue or pull request actually changed rather than only citing it, and stop
once you have said it. Commit messages and pull-request bodies never carry an
agent co-author trailer or a "Generated with" footer. This repository writes a
plain hyphen where an em dash would go (`tests/test_house_style.py` enforces
it), and everything you write uses the frozen v2 vocabulary
(`governance/terminology.yml`, enforced by `tests/test_terminology.py`).

## The pipeline

Eight stages, in order: assess, define acceptance criteria, refine, plan,
break down, implement, verify, ship. The stage-to-command map, what each
stage writes, and which agent owns it are in the `compass-runtime` skill.

The delivery approach written at assessment says which stages run at what
weight and why any was skipped. Honour it: do not silently re-skip a stage
it kept, or re-add one it skipped.

Two transitions carry a checklist. The requirements review ends with the
**Definition of Ready**; on approaches where that review collapses it is
satisfied by construction. Before shipping comes the **Definition of
Done**, whose unchecked items carry typed inline tags - `(evidence: EV-id)`
or `(follow-up: FU-id)`. A bare unchecked box fails `compass check`.

## Choosing agents and skills

Which agent owns which stage, and which skill to load with it, is the
`compass-runtime` skill's table - `skills/compass-runtime/SKILL.md`. It also
carries the stage-to-command map and the shape of an issue directory on disk.
Read it there rather than here: this file used to restate it, and the two
drifted until one of them was naming nine agents where the other named ten.

## Roles

Compass has five roles, four of them non-engineering, all full pipeline
citizens. If a session opens with a role entry point - `/compass:intent`,
`/compass:position`, `/compass:design`, `/compass:roundtable` - adopt that
role's vocabulary and artifacts. Do not collapse a product owner's intake
into an engineering issue; the intake is upstream of the acceptance
criteria, and the criteria must be checked back against it.

## Worktrees and swarms

Worktree rules - who may create one, who works inside one, and how the stream
count is bounded - are in the `compass-runtime` skill and in the
`worktree-swarm` skill that the orchestrator loads.

## Where state lives

`.compass/work/<issue>/` holds the spine, the artefacts and the evidence;
the `compass-runtime` skill has the tree and what each file is for.

`governance/` and `architecture/` live at the project root, not under
`.compass/`. **Compass ships an `architecture/`** - read it for the
framework's own invariants and the decision records behind the guardrails,
the sizing model and the role perspectives. Assess loads it, when present,
into `architecture-loaded.yml` in the issue directory; projects without one
keep working.

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

### Reporting to a person

Before you report, read the message back for terms of art - that is the moment,
before it is sent, not afterwards. A sentence in conversation lands once.

Four parts:

- **what I did**
- **outstanding questions** - numbered when there is more than one
- **what I need from you** - a decision, a review, an explanation, or nothing
- **what I intend to do next** - so they can redirect before the work, not after

Keep each section short and put a snippet under the point it belongs to. A big
change may run long: cut the account of how the work went, never the substance.

Each heading answers a question the reader already has, which is what stops
jargon hiding - "what I need from you" cannot be answered in terms of art.

## When you are unsure

Re-read the delivery-approach record (`delivery-approach.md`). It was written at triage
precisely so that a later session - or a different agent - can pick up the
issue without re-deriving the process. If it does not answer the question,
triage under-sized the process; say so and re-assess rather than improvise.
