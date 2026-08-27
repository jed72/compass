---
name: compass-runtime
description: "The stage-to-command map: which command runs each pipeline stage, what it writes, which agent owns it, and where issue state lives on disk. Load when a Compass issue begins."
---

# Compass - the stage map

The rules of behaviour are in `compass-contract.md`, and the SessionStart hook
puts them in every session before you read this. They are not repeated here:
they used to be, and the two copies drifted until this skill was naming nine
agents where the contract named ten.

What this file carries is the mapping a session needs once it is already
following the contract - which command runs which stage, what each writes,
which agent owns it, and where the result lands on disk.

If anything here conflicts with `docs/methodology.md`, the methodology doc
wins. First Compass session? `docs/five-minutes.md` has the mental model and a
worked example; `docs/safety-contract.md` says what Compass guarantees and
what it explicitly does not.

## The stages and their commands

| Stage | Command | Artifact it writes |
|---|---|---|
| Assess | `/compass:assess` | `delivery-approach.md` + the manifest's assessment |
| Define acceptance criteria | `/compass:define` | `acceptance-criteria.md` |
| Requirements review | `/compass:refine` | `requirements-review.md` (ends with the Definition of Ready) |
| Plan | `/compass:plan` | `technical-design.md` (+ `distribution-map.md` on parallel work) |
| Break down the work | `/compass:breakdown` | worktrees + subtask assignments |
| Implement | `/compass:implement` | code + the red and green records (named by binding) |
| Test & review | `/compass:verify` | `verification-report.md` (ends with the Definition of Done) |
| Ship | `/compass:ship` | the integration commit + settled follow-ups |

Cross-issue: `/compass:status` (one issue or a flat list), `/compass:flow`
(the managed cross-issue view - advisory, never gating). Role entry points:
`/compass:intent` (product owner), `/compass:position` (marketer),
`/compass:design` (designer - produces the UI contract), `/compass:consult`
(multi-role decisions). `/compass:init` is optional, and it is not what
creates the project: the entry points above run `compass init` for you.

Each retired command name remains as a redirect stub for one major version.

**The binding decides the filename.** `compass tdd-red --scenario TRC-x` and
`compass tdd-green --scenario TRC-x` write `evidence/red-TRC-x.json` and
`evidence/green-TRC-x.json`; a run with no `--scenario` writes
`evidence/red.json` and `evidence/green.json`. Nothing else is touched, so
recording one scenario cannot overwrite the record another gate is citing -
and a reader knows where their evidence went without guessing.

## Which agent and which skill, per stage

- **Assess** - load the `adaptive-routing` skill; consider the `router`
  agent.
- **Define and refine** - load `bdd-specification`; on brownfield work whose
  behaviour is not yet written down, also load `behaviour-mapping`. The
  `spec-author` agent owns both stages.
- **Plan** - load `plan-authoring` (which optional design sections earn a
  place) and `governance-check` (how to check the design against the
  governance in force). The `planner` agent owns it.
- **Implementing in parallel** - load `worktree-multiagent`. The `orchestrator`
  agent coordinates; `builder` agents work, one per worktree, each loading
  `tdd-discipline`.
- **Test & review** - the `verifier` and `reviewer` agents run; load
  `evidence-gates`. Load `receiving-code-review` when answering their
  comments.
- **An unexpected test failure while implementing** - load
  `systematic-debugging`, and after three failed fixes re-assess rather than
  attempt a fourth.
- **Role-facing work** - load `role-translation`, which is how one set of
  acceptance criteria is read through five role perspectives. The
  `product-owner`, `product-marketer` and `architect` agents apply specific
  ones.
- `traceability` is loaded whenever an artifact is written.

The full set is in `agents/`. Read there rather than trusting a list in prose:
this one has been wrong before.

## Worktrees and multiagent

Only the `orchestrator` agent creates worktrees (`scripts/multiagent.sh`) and
integrates them (`scripts/integrate.sh`). A `builder` works *inside* its
assigned worktree and never touches a sibling's. The approach's distribution
map says how many subtasks exist; policy can cap the count. On solo work there
is no worktree - work on the current branch.

## Where state lives

```
.compass/
├── config.yml                  Project config, and what initialised the project
├── current-task                One-line pointer to the active issue
├── work/
│   └── <issue-slug>/            One directory per issue
│       ├── delivery-approach.md The delivery-approach record (prose)
│       ├── manifest.yml             The manifest
│       ├── intent.md            Intake (if a product owner was involved)
│       ├── ui-contract.md       Designer contracts (if a designer was involved)
│       ├── acceptance-criteria.md  The shared artifact every role reads
│       ├── requirements-review.md  (ends with the Definition of Ready gate)
│       ├── technical-design.md  The design
│       ├── distribution-map.md  Multiagent orchestration (initiative-scale work)
│       ├── positioning.md       Marketer messaging (if in play)
│       ├── launch-readiness.md  Marketer claims gate (if in play)
│       ├── verification-report.md  (ends with the Definition of Done gate)
│       ├── evidence/            red/green records + typed gate evidence
│       └── devlog.md            Append-only running log
└── flow/
    └── digest-<date>.md         Periodic cross-issue digest
```

`governance/` lives at the project root, not under `.compass/`. The CLI reads
whichever is in force: the project's own if `/compass:init` copied one in, the
framework's shipped defaults otherwise.

## Writing voice

Before writing a devlog entry, a requirements review, or anything else this
skill produces, read `skills/compass-runtime/writing-voice.md` - the
principle and the tells that mark prose narrating the pipeline instead of
communicating a decision. `writing-voice-worked-example.md` beside it carries
the before-and-after pairs from this project's own archive, for when the
principle alone does not settle a sentence.

## When you are unsure

Re-read `delivery-approach.md`. It was written at assessment precisely so a
later session, or a different agent, can pick the issue up without re-deriving
the process. If it does not answer the question, the assessment under-sized
the work: say so and re-assess rather than improvise.
