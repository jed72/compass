---
STATUS: ACCEPTED
date: 2026-05-24
---

# Compass - System Context

<!-- triage reads this file at the start of every issue and includes it (with
     its SHA-256 fingerprint) in .compass/work/<task>/architecture-loaded.yml.
     Downstream agents - spec-author, planner, and the architect-lens - read
     architecture-loaded.yml to get persistent architectural context that
     survives session boundaries and context compaction.

     Keep this file factual and concise. It is machine-read as well as
     human-read. -->

## Purpose

Compass is an adaptive spec-driven development framework that runs inside
Claude Code. Its primary purpose is to reduce the cost of doing things right:
writing testable acceptance criteria before building, routing issues to the
appropriate level of ceremony, and producing an auditable evidence trail that
proves work landed safely.

Compass governs its own development using the same mechanisms it supplies to
adopters. This `architecture/` tree is the self-application of that governance.

## Components

The framework has five logical surfaces. Each maps to artefacts on disk and
to agent roles that own them.

### Pipeline

The pipeline is the ordered sequence of stages every delivery issue passes
through: triage → define → refine → design → breakdown → implement → verify → ship.
Phase weights (full / light / skipped) are determined at triage by the router.
The pipeline is implemented through the slash commands in `commands/` and the
CLI subcommands in `cli/compass`.

Logical surface: **pipeline**

### Router

The router reads the four context dimensions (risk, familiarity, size,
intent + role) recorded in `task.yml.assessment` and deterministically selects a
route, phase weights, and gate set by running `governance/routing-policy.yml`
through `compass approach evaluate`. No human judgement enters after the assessment
are recorded; the route is a pure function of the assessment.

Logical surface: **router**

### Guardrails

Guardrails are the five hard, checkable, blocking rules that no route, agent,
or convenience can cross: G1 (tested before it lands), G2 (acceptance defined
before built), G3 (traceability holds), G4 (evidence not assertion), G5 (human
signs off on the irreversible). They are encoded in `governance/guardrails.yml`
and checked mechanically by `compass check`.

Logical surface: **guardrails**

### Strategies

Strategies are directional biases that are on by default but are not blocking:
BDD (Given/When/Then scenarios as spec), TDD (red-green-refactor), simplest
correct implementation, and persistence over conversation. They are encoded in
`governance/strategies.md`. The TDD strategy enforcement is implemented in
`hooks/pre-tool.sh` (the `.red` marker gate).

Logical surface: **strategies**

### Role Pipeline

Compass has five roles - engineer, product owner, designer, marketer, QA - all
of whom are full pipeline citizens. Each role has entry-point slash commands
(`/compass:intent`, `/compass:position`, `/compass:design`,
`/compass:roundtable`) and dedicated agent files in `agents/`. The architect
lens (`agents/architect-lens.md`) is an advisory lens over the role pipeline,
not a sixth full role.

Logical surface: **role pipeline**

## External dependencies

| Dependency | What Compass reads / writes | Criticality |
|---|---|---|
| `governance/routing-policy.yml` | The evaluator reads this at triage to compute the delivery approach | high |
| `governance/guardrails.yml` | `compass check` reads this to run gate assertions | high |
| `governance/strategies.md` | Consulted by agents when deciding TDD/BDD application | medium |
| `governance/signals.yml` | `hooks/stop.sh` and `compass rework-scan` read this | medium |
| `.compass/work/<issue>/task.yml` | The machine-readable issue spine; written by triage, read by every stage | high |
| `.compass/work/<task>/*.md` | Phase artefacts (spec, plan, clarifications, etc.) | high |
| `.compass/current-task` | One-line pointer resolved by CLI and hooks | high |
| `architecture/` (this tree) | Assess loads into `architecture-loaded.yml`; architect-lens reads | medium |
| `templates/` | Worked examples and starting shapes for adopter artefacts | low |
| Claude Code session | The execution environment; not a file dependency | n/a |

## Boundary conditions

1. **Assess is always first.** No code-changing tool call may precede an assessment
   invocation for the active issue. The pre-tool hook (`hooks/pre-tool.sh`)
   enforces the `.red` marker contract; it cannot enforce triage itself, but the
   methodology makes triage mandatory.

2. **The assessment is the only judgement field in `task.yml`.** Everything else in
   `task.yml` is mechanism-produced: route, phases, gates, scenarios,
   changed_files, evidence, follow-ups, reframes. No mechanism may write into
   `task.yml.assessment`.

3. **Guardrails are not configurable.** Projects may add their own governance
   checks, but they cannot remove or soften G1–G5. Adopters declare
   architectural fitness functions as project guardrails using the generic
   `command-passes` check (see ADR-009); the `verify.fitness` gate is promoted
   to blocking by routing floors `RP-REQUIRE-003/007` when the issue's blast
   radius or domain tags warrant it.

4. **The router is not extensible in-line.** Adding a new route shape or
   reading dimension requires a deliberate framework change with its own
   issue and ADR; it is not a per-project configuration option.

5. **The `architecture/` tree is advisory.** A project may operate Compass
   without an `architecture/` directory. Assess degrades gracefully to an
   empty load record. The architect-lens degrades gracefully to heuristic
   analysis with a `WARNING:` prefix. Neither absence causes a phase to fail.

## Open questions

- None open at time of authoring (2026-05-24). Opened questions will be
  recorded here with a date and a link to the issue that raised them.
