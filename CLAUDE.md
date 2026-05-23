# Compass — Operating Instructions for Claude Code

You are running inside a project that uses **Compass**, an adaptive
spec-driven development framework. This file tells you how to behave. It is
loaded on every session.

If anything here conflicts with `docs/methodology.md`, the methodology doc
wins — but you should never see a conflict, because this file is the runtime
expression of that doc.

If this is your first Compass session, also read `docs/five-minutes.md` for
the mental model and a worked end-to-end example, and `docs/safety-contract.md`
for the seven things Compass 1.0 guarantees (and the things it explicitly does
not claim). They are short, and they ground everything below.

---

## The one rule that creates every other rule

**Never skip Frame.** Before any task that changes code, specs, or product
artifacts, run the Needle (`/compass:frame`). The Needle reads the four
context dimensions — that is judgement, and the judgement is yours — and
records them in `.compass/work/<task>/task.yml`. It then hands them to the
**mechanism**: `/compass:frame` runs `compass route evaluate --write`, which
applies `governance/routing-policy.yml` deterministically and folds the route,
phases, and gates back into `task.yml`. You also write the human-readable
`route.md`. You do not choose a process, and you do not compose the route in
your head — you read the terrain, the CLI computes the route.

`/compass:frame` also writes `.compass/current-task` — a one-line pointer to
the active task slug. The hooks and the CLI both rely on it: `compass check`,
`compass tdd-red`, and the pre-tool hook resolve "the current task" through
that pointer, so keep it pointing at the task you are actually working.

When the terrain turns out to have been misread, re-frame through the same
mechanism: `/compass:frame --reframe` re-runs `compass route evaluate --write`,
which detects that the route changed and records the re-frame in `task.yml`'s
`reframes` log — pass `--reason "..."` so the entry says *why*. That log is the
framework's feedback signal: `compass calibration` aggregates it across every
task and reports whether the Needle is systematically over- or under-sizing
routes. A re-frame is a normal event; an unrecorded one is a lost signal.

The only work exempt from Frame is conversation — answering a question,
explaining code, reading to understand. The moment a tool call would change a
file, Frame must already have run for the current task. If the work is
genuinely exploratory — you cannot frame it well enough to deliver it yet —
that is not an exemption; that is a **Spike** route, and Frame still runs.

`/compass:init` is **optional**. The default guardrails and default strategies
ship active with the framework, so `/compass:frame` works with zero project
setup. Init is how a project *accretes* its own governance later — not a
prerequisite for the first task.

## Governance — guardrails and strategies

Compass is governed by two kinds of thing, and you must keep them straight.

- **Guardrails** are few, hard, checkable, blocking. Routes adapt ceremony
  *around* them; no route, agent, or convenience crosses one. If a route
  appears to ask you to cross a guardrail, stop — the route definition has a
  bug. The five shipped default guardrails:
  1. **G1 — Tested before it lands.** No code reaches `main` without a passing
     automated test it traces to. Checked at Verify and Land, with evidence.
  2. **G2 — Acceptance defined before it is built.** No code is written that
     no stated, checkable acceptance criterion describes.
  3. **G3 — Traceability holds.** code → acceptance criterion → intent, and
     claim → criterion. Maintain it as you go, not at the end.
  4. **G4 — Evidence, not assertion.** Clear a guardrail with pasted command
     output and artifacts. "The tests pass" without the run clears nothing.
  5. **G5 — A human signs off on the irreversible.** Data loss, money, auth,
     privacy — these get an explicit human checkpoint before they land.
- **Strategies** are many, soft, directional, assessed. They bias your work;
  they do not block it. **BDD** (Given/When/Then scenarios as spec and
  acceptance check) and **TDD** (red-green-refactor) are the shipped default
  *strategies* — strong, on by default, the way you satisfy G1 and G2. They
  are not guardrails: the *outcome* is hard, the *ritual* is the default
  method. `hooks/pre-tool.sh` enforces red-before-green and is **route-aware**
  — it does not block on a **Spike** route, where the TDD strategy is
  suspended. Do not work around the hook on the routes where it does apply.

The conflict rule: a guardrail beats a strategy; strategy-vs-strategy is the
Needle's call (by route) or a human's. Read `governance/` at the start of a
task — `guardrails.md`, `strategies.md`, `routing-policy.md` for the why;
`routing-policy.yml` and `guardrails.yml` are the machine-readable companions
the CLI runs. The guardrail *checks* are mechanical: `compass check` runs the
`guardrails.yml` checks against the task's `task.yml` and `evidence/`, and
`/compass:verify` calls it. Clear a guardrail with evidence on disk, not a
claim — the check looks for the evidence record, not your word for it. Gate
evidence in `task.yml` is **typed** — a `{type, path}` record (`test-run`,
`command-output`, `human-approval`, `artifact`), not a bare path — and
`guardrails.yml`'s `gate_evidence_requirements` say which types each gate
accepts. A mechanical gate cannot be cleared with a written note; the type
is checked, not just the file's existence.

## The pipeline

```
Frame → Specify → Clarify → Plan → Distribute → Build → Verify → Land
```

Each phase has a slash command in `commands/`. Run them in order. The
route in `route.md` tells you which phases are full-weight, which collapse,
and which are skipped — and the route always states *why* a phase is skipped.
Honour that; do not silently re-skip or re-add phases.

After each phase, write its artifact to `.compass/work/<task>/` using the
matching template in `templates/`. Persistence over conversation: if it isn't
on disk, it didn't happen. Each phase also fills its section of `task.yml` —
the machine-readable task spine — as a by-product: Frame writes `readings`,
Specify adds `scenarios`, Build adds `changed_files`. It is not extra ceremony;
the CLI reads and writes it for you.

In **Build**, drive the red-green cycle through the CLI, not by hand: `compass
tdd-red -- <test cmd>` runs the test, asserts it genuinely fails, writes the
`evidence/red.json` record and the `.red` marker the pre-tool hook reads;
`compass tdd-green -- <test cmd>` asserts it now passes, writes
`evidence/green.json`, and clears the marker. The marker is only ever written
after a real failure — that honesty is the point.

Two phase transitions carry an explicit checklist gate. **Clarify → Plan** is
guarded by a **Definition of Ready** (the foot of `clarifications.md`); on
routes where Clarify collapses (Express, Hotfix, Spike), the DoR is satisfied
by construction. **Verify → Land** is guarded by a **Definition of Done** (the
foot of `verification-report.md`). Treat an unchecked box as a closed gate.

Beyond the per-task pipeline, two commands look across tasks: `/compass:status`
reports one task or a flat list; `/compass:flow` is the managed cross-task view
— triage, blockers, owed-backfill aggregation, and a periodic digest. Flow is a
capability, not a role: it advises, it never gates, and it never sets task
state (state is always inferred from artifacts on disk).

## Choosing agents and skills

- During **Frame**, load the `adaptive-routing` skill and consider the
  `navigator` agent.
- During **Specify/Clarify**, load `bdd-specification`; on brownfield terrain
  also load `blueprint-distillation`. The `spec-author` agent owns this.
- During **Plan**, load `governance-check`; the `planner` agent owns this.
- During **Distribute/Build** on a swarm route, load `worktree-swarm`. The
  `orchestrator` agent coordinates; `builder` agents do the work, one per
  worktree. Each builder loads `tdd-discipline`.
- During **Verify**, the `verifier` and `reviewer` agents run; load
  `evidence-gates`.
- For any role-facing work, load `role-translation` — it is how one spec is
  read through five lenses. The `product-lens`, `marketing-lens`, and
  `architect-lens` agents apply specific role perspectives. The architect-lens
  reads the project's `architecture/` artifacts and writes `architecture-notes.md`
  in the task dir; spec-author and planner consult those notes rather than
  re-invoking the lens.
- `traceability` is loaded whenever an artifact is written.

## Roles

Compass has five roles, four of them non-engineering, all full pipeline
citizens. If a session opens with a role entry point —`/compass:intent`,
`/compass:position`, `/compass:design`, `/compass:roundtable`— adopt that
role's vocabulary and artifacts. Do not collapse a product owner's brief into
an engineering task; the brief is upstream of the spec and the spec must be
checked back against it.

## Worktrees and swarms

Only the `orchestrator` agent creates worktrees (`scripts/swarm.sh`) and lands
them (`scripts/integrate.sh`). A `builder` agent works *inside* an assigned
worktree and never touches a sibling's. The route's distribution map says how
many streams exist; a routing guardrail can cap the count. If the route is
solo, there is no worktree — work on the current branch.

## Where state lives

```
.compass/
├── config.yml                  Project config (route defaults, swarm caps)
├── current-task                One-line pointer to the active task slug
├── work/
│   └── <task-slug>/
│       ├── route.md             Frame output — the computed route (prose)
│       ├── task.yml             The machine-readable task spine — the CLI reads/writes it
│       ├── brief.md             Intent (if a product owner was involved)
│       ├── ui-contract.md       Designer contracts (if a designer was involved)
│       ├── spec.feature.md      BDD scenarios — the shared artifact
│       ├── clarifications.md    (ends with the Definition of Ready gate)
│       ├── plan.md
│       ├── distribution-map.md  Swarm topology (Expedition / larger routes)
│       ├── positioning.md       Marketer messaging + PRFAQ (if in play)
│       ├── launch-readiness.md  Marketer claims gate (if in play)
│       ├── verification-report.md  (ends with the Definition of Done gate;
│       │                            DoD lines use the typed inline tags
│       │                            `(evidence: EV-id)` or `(backfill: BF-id)`
│       │                            — bare unchecked items fail compass check)
│       ├── architecture-loaded.yml (written at Frame if architecture/ is
│       │                            present; the per-task snapshot of what
│       │                            cross-task architectural state was loaded)
│       ├── architecture-notes.md   (written by the architect-lens — annotations
│       │                            on plan.md; not a parallel spec)
│       ├── evidence/            red.json/green.json + gate evidence the CLI records
│       └── devlog.md            Append-only running log
└── flow/
    ├── digest-<date>.md         Periodic cross-task digest (/compass:flow --digest)
    └── rework-<date>.md         Cross-task rework scan (compass rework-scan)
```

`governance/` lives at the project root — the `.md` files (`guardrails.md`,
`strategies.md`, `routing-policy.md`) and the `.yml` files the CLI runs
(`routing-policy.yml`, `guardrails.yml`, `signals.yml`) — not under
`.compass/`. `signals.yml` holds advisory patterns (scope-bloat phrases the
stop-hook nudges on, rework-scan window + public-surface patterns); soft
signals, not guardrails. If `/compass:init` has not been run, the framework's
shipped `governance/` defaults apply as-is; the CLI falls back to them the
same way.

`architecture/` also lives at the project root, sibling to `governance/`,
when adopted. It holds the cross-task architectural contract —
`system-context.md`, `relations.md`, `ownership.md`, and `decisions/ADR-*.md`
— so the design that should not silently drift survives across tasks. Frame
loads it (when present) into `architecture-loaded.yml` in the task dir; the
architect-lens reads it. Projects without `architecture/` continue to work;
the load no-ops cleanly.

## When you are unsure

Re-read `route.md`. It was written at Frame precisely so that a later session
— or a different agent — can pick up the task without re-deriving the
process. If `route.md` does not answer the question, the Needle under-framed;
say so and re-run Frame rather than improvising.
