---
STATUS: ACCEPTED
date: 2026-05-24
---

# Compass - Component Relations

<!-- Frame reads this file and includes it in architecture-loaded.yml as a
     narrative artifact. The architect-lens reads it to determine which
     `touches:` tags in task.yml.readings map to known component names, so
     it knows when to fire automatically at Specify time.

     Format: keep component names consistent with the tags used in
     task.yml.readings.touches so the lens can match them.

     Direction: A -> B means A reads or calls B (A is the caller/reader,
     B is the callee/source). -->

## Call graph and read graph

The following table enumerates every non-trivial relation between Compass
components. Relations are ordered by the calling component.

| From | To | Transport | Purpose | Criticality |
|---|---|---|---|---|
| `cli/compass` | `governance/routing-policy.yml` | file read | `compass route evaluate` applies routing policy at Frame | high |
| `cli/compass` | `governance/guardrails.yml` | file read | `compass check` runs gate assertions against this schema | high |
| `cli/compass` | `governance/strategies.md` | file read | strategy documentation consulted by CLI subcommands | medium |
| `cli/compass` | `governance/signals.yml` | file read | `compass rework-scan` and `compass calibration` read signal patterns | medium |
| `cli/compass` | `architecture/` | file read | `frame_load_architecture` reads all `*.md` files and `decisions/ADR-*.md` into `architecture-loaded.yml` | medium |
| `cli/compass` | `.compass/work/` | file read/write | every subcommand (frame, check, tdd-red, tdd-green, rework-scan, calibration) reads and writes task spines under this directory | high |
| `cli/compass` | `.compass/current-task` | file read | resolves the active task slug for hooks and subcommands that don't receive `--task` explicitly | high |
| `hooks/pre-tool.sh` | `.compass/work/<task>/.red` | file read | the hook checks for the `.red` marker before allowing code-editing tool calls; absent marker → edit blocked | high |
| `hooks/pre-tool.sh` | `.compass/current-task` | file read | resolves which task's `.red` marker to check | high |
| `hooks/stop.sh` | `governance/signals.yml` | file read | reads scope-bloat and rework signal patterns at session end | medium |
| `hooks/stop.sh` | `.compass/work/<task>/devlog.md` | file read | scans the session's devlog for rework signals before the session closes | medium |
| `hooks/stop.sh` | `.compass/current-task` | file read | resolves active task for devlog location | medium |
| `architect-lens` (agent) | `architecture/` | file read | reads `system-context.md`, `relations.md`, `ownership.md`, `invariants.yml` (if present), and all `decisions/ADR-*.md` to build its consultation context | medium |
| `architect-lens` (agent) | `.compass/work/<task>/spec.feature.md` | file read | reads scenarios the task must satisfy | medium |
| `architect-lens` (agent) | `.compass/work/<task>/plan.md` | file read | reads the technical approach to annotate | medium |
| `architect-lens` (agent) | `.compass/work/<task>/architecture-loaded.yml` | file read | reads Frame's load record if present | medium |
| `architect-lens` (agent) | `.compass/work/<task>/architecture-notes.md` | file write | writes its output (annotations, boundary risks, candidate ADR titles) | medium |
| `agents/spec-author.md` | `architecture/decisions/ADR-*.md` | via `architecture-loaded.yml` | reads ADR summaries (id, title, status) to avoid re-litigating closed decisions | low |
| `agents/planner.md` | `.compass/work/<task>/architecture-notes.md` | file read | planner reads architect-lens output to compose `plan.md §2` design decisions | medium |
| `templates/architecture/` | n/a | reference only | templates are never read by the CLI; they are human-referenced when an adopter bootstraps their own `architecture/` tree | n/a |

## Prohibited relations

The following relations must never be created. They would violate invariants
or cross boundary rules encoded in the ADRs.

- **`architect-lens` must not read any directory other than `architecture/`** -
  the lens reads exactly `architecture/` at the project root. Reading any
  sibling or adjacent directory that might contain draft or provisional content
  would introduce undeclared dependencies. The lens reads `architecture/` only.
  (Cited source: TRC-D2 and the `architect-lens` agent's hard boundaries.)

- **Any mechanism must not write into `task.yml.readings`** - readings are the
  human's judgement field; mechanism-produced state lives in `architecture-loaded.yml`
  and elsewhere in `task.yml`. (See ADR-001.)

- **`hooks/stop.sh` and `compass rework-scan` must not mutate `task.yml`** -
  both are read-only over the task spine. Detection is advisory; blocking on
  detection would violate ADR-003 (Flow advises, never gates) and the
  invariant behind it, Inv-4.

- **`compass calibration` must not mutate `task.yml`** - calibration aggregates
  reframe data read-only; it never writes back to individual task spines
  (Inv-4: Flow advises, never gates).

## Known interface contracts

| Contract | Location | Notes |
|---|---|---|
| Task spine schema (`task.yml`) | `cli/compass` (validated inline) | `schema_version: '1.0'`; fields: readings, route, topology, phases, evidence, gates, scenarios, changed_files, claims, backfills, reframes |
| Architecture load record | `cli/compass` (`frame_load_architecture`) | `schema_version: '1.0'`; fields: artifacts (path, sha256, type), adrs (id, path, title, status), loaded_at |
| ADR frontmatter | `architecture/decisions/ADR-*.md` | Required fields: id, title, status, date, supersedes, superseded_by. Status: accepted \| proposed \| superseded. |
| Routing policy schema | `governance/routing-policy.yml` | Consumed by `compass route evaluate`; schema validated by `tests/test_policy_integrity.py` |
| Guardrails schema | `governance/guardrails.yml` | Consumed by `compass check`; validates gate evidence types |
