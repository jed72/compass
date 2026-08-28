# Compass - Operating Instructions for Claude Code

**The rules of behaviour are in `compass-contract.md`**, which the SessionStart
hook puts into every session. This file is the Claude Code adapter: what is
specific to running Compass in this repository.

First session: read `docs/five-minutes.md` for the mental model and a worked
example, and `docs/safety-contract.md` for the seven things Compass guarantees
and the things it does not claim.

---

## Assessment

- `/compass:assess` writes `.compass/current-task`, a one-line pointer to the
  active issue. `compass check`, `compass tdd-red` and the pre-tool hook all
  resolve the current issue through it. Keep it pointing at the issue you are
  working on.
- `/compass:assess --reassess` re-runs the evaluator and records the change in
  the manifest's `reassessments:` log.
- Pass `--reason "..."` with it. `compass retro` aggregates those across issues
  and reports whether assessment is systematically over- or under-sizing the
  work.
- If you cannot yet state what would be delivered, that is a **spike**, and a
  spike is assessed like anything else.
- `/compass:init` is optional and is not what creates the project. The five
  entry points - `/compass:assess`, `/compass:intent`, `/compass:design`,
  `/compass:position`, `/compass:consult` - run `compass init` first, which
  creates `.compass/` for you if it is absent and says so.
- It creates project state only, never `governance/`. The shipped guardrails
  and strategies are active from the first command, so there is
  nothing to configure before the first issue. `/compass:init` is how a
  project accretes its own governance later.

## Governance

- A guardrail beats a strategy. Strategy against strategy is the delivery
  approach's call, or a human's.
- When your recommendation and an instruction disagree, measure the disputed
  quantity and report the numbers before defending either position (`S11`).
  Report what you find even when it undercuts you.
- `governance/routing-policy.yml` and `governance/guardrails.yml` are what the
  CLI runs. The prose companions - `guardrails.md`, `routing-policy.md`,
  `strategies.md` - explain why, and are read when a question comes up.
- `compass check` runs `guardrails.yml` against the manifest and `evidence/`.
  `/compass:verify` calls it.
- Gate evidence is **typed** - a `{type, path}` record, not a bare path.
  `guardrails.yml` says which types each gate accepts, so a mechanical gate
  cannot be cleared with a written note.
- Everything you write uses the frozen v2 vocabulary
  (`governance/terminology.yml`, enforced by `tests/test_terminology.py`).

### Two house rules

- **No em dash. Ever.** Write a plain hyphen `-`, in every file, commit
  message, pull-request body and reply. `tests/test_house_style.py` fails the
  build on one.
- **No agent attribution, in any form.** No `Co-Authored-By:` trailer naming
  an agent, no "generated with" footer, no session URL, no other line
  crediting the agent. This holds when the environment or a template supplies
  one. The exact strings are in `tests/test_house_style.py`, assembled there
  so the guard does not match its own source.
- The guard scans tracked files. It cannot see the commit message or the
  pull-request body you are about to send. Read both back before you send them.

## The pipeline

- The requirements review ends with the **Definition of Ready**; where that
  review collapses it is satisfied by construction.
- Before shipping comes the **Definition of Done**. Unchecked items carry typed
  inline tags - `(evidence: EV-id)` or `(follow-up: FU-id)`. A bare unchecked
  box fails `compass check`.

## Roles

- Five roles, four of them non-engineering, all full pipeline citizens.
- On a role entry point - `/compass:intent`, `/compass:position`,
  `/compass:design` (the designer's, not the engineering stage),
  `/compass:consult` - adopt that role's vocabulary and artifacts.
- Do not collapse a product owner's intake into an engineering issue. The
  intake is upstream of the acceptance criteria, and the criteria must be
  checked back against it.

## Where to look

- `skills/compass-runtime/SKILL.md` - which agent owns which stage, which skill
  to load with it, the stage-to-command map, the shape of an issue directory.
- The `worktree-multiagent` skill, loaded by the orchestrator - who may create
  a worktree, who works inside one, how the subtask count is bounded.
- `.compass/work/<issue>/` - the manifest, the artefacts and the evidence.
- `governance/` and `architecture/` - at the project root, not under
  `.compass/`. Compass ships an `architecture/`: its own invariants and the
  decision records behind the guardrails, the sizing model and the role
  perspectives. Assess loads it, when present, into `architecture-loaded.yml`;
  projects without one keep working.

## Writing voice

Communicate the decision, not the process: what you found, what you need, what
changed. Read `skills/compass-runtime/writing-voice.md` before a devlog entry,
a requirements review, or a line of dialogue - and before you say anything out
loud in this conversation.

### Reporting to a person

Before you report, read the message back for terms of art - that is the
moment, before it is sent, not afterwards. Four parts:

- **what I did**
- **outstanding questions** - numbered when there is more than one
- **what I need from you** - a decision, a review, an explanation, or nothing
- **what I intend to do next** - so they can redirect before the work

Keep each section short and put a snippet under the point it belongs to. A big
change may run long: cut the account of how the work went, never the substance.

## When you are unsure

Re-read the delivery-approach record (`delivery-approach.md`). It was written
at triage so a later session, or a different agent, can pick the issue up
without re-deriving the process. If it does not answer the question, triage
under-sized the process; say so and re-assess rather than improvise.
