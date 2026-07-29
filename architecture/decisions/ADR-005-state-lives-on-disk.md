---
id: ADR-005
title: State lives on disk; conversation reconstructs from artifacts
status: accepted
date: 2026-05-24
supersedes: ''
superseded_by: ''
---

## Context

Claude Code sessions do not have persistent memory across invocations. A task
that spans multiple sessions - a Standard route task with a two-day Build
phase, for example - must be resumable by a new session (or a different agent)
without loss of context.

There are two design choices for how to handle this: (a) keep the important
state in the conversation history and expect future sessions to re-read the
earlier messages, or (b) write every output of every phase to a named file on
disk, from which a new session can reconstruct the full task context.

The conversation-as-state approach is the default in most LLM-based tools. It
is convenient for short tasks but breaks down over long tasks and across
session boundaries, where context compaction discards earlier messages.

## Decision

Every output of every Compass phase is a file on disk in a deterministic
location. Conversation is ephemeral; the file is the record.

Phase artifacts live under `.compass/work/<task>/`: `route.md`, `task.yml`,
`spec.feature.md`, `clarifications.md`, `plan.md`, `evidence/*.json`,
`devlog.md`, `verification-report.md`. Each is written by the corresponding
phase and read by downstream phases.

Mechanism-produced state (evidence, load records, scan reports) also lives on
disk in deterministic locations: `architecture-loaded.yml` in the task
directory, `evidence/red.json` / `evidence/green.json` in the task directory,
`.compass/flow/rework-<date>.md` in the flow directory.

No Compass mechanism produces only-in-chat output. If a mechanism's output is
not a named file, it did not happen.

CLAUDE.md states this as the operative rule: "Persistence over conversation:
if it isn't on disk, it didn't happen."

## Alternatives considered

| Alternative | Why considered | Why rejected |
|---|---|---|
| Use a database (SQLite) as the task state store | Richer query interface; atomic updates; easier to check "has the spec been approved?" | Adds a runtime dependency; breaks the "file is the record" inspection model; harder to diff, review, and audit in a standard code review; not version-controlled alongside the code |
| Rely on Claude Code's project memory (`/memory`) | Native to the tool; no separate file management needed | Project memory is not version-controlled, not inspectable by other tools, not portable across Claude Code instances, and not part of the git diff that a reviewer sees. It is invisible to the framework's mechanical checks. |

## Consequences

**Positive:**
- Any session (or agent) can pick up a task by reading the files in
  `.compass/work/<task>/`. There is no "warm session" requirement.
- The task's entire history is in git: phase artifacts, evidence files,
  devlog. A PR reviewer sees the whole pipeline output, not just the diff.
- `compass check` and `/compass:verify` are mechanical: they check file
  existence and content on disk. No session state is needed.

**Negative:**
- Every agent invocation must read multiple files to reconstruct context.
  On a long task with many phase artifacts, the context budget is consumed
  partly by re-reading artifacts. Compression artefacts (`/compress`) help
  but do not eliminate this cost.
- The `.compass/work/` directory accumulates files across tasks. Teams that
  do not prune it will accumulate a large history tree. There is no
  automated expiry mechanism.

**Neutral / follow-on:**
- The `architecture-loaded.yml` convention (Frame writes a load record that
  downstream agents read) is a direct application of this decision: rather
  than have each agent re-parse `architecture/`, Frame parses it once and
  writes the result to a file that all downstream agents can read cheaply.

## References

- Prior task's `architecture-notes.md` §2 Inv-6 (persistence over conversation)
- `CLAUDE.md` §"The pipeline" ("if it isn't on disk, it didn't happen")
- `docs/methodology.md` §"Where state lives"
- `CLAUDE.md` §"Where state lives"
