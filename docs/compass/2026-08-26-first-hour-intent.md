# Brief - first-hour

> **Author:** jed72 · **Date:** 2026-08-26
> **Governance owner check:** consistent with `governance/strategies.md`.
> This brief is the parent of six issues. Each issue's `task.yml` names the
> INT ids it traces to. It lives here, not under `.compass/work/`, because it
> is the first human-facing artefact under the `docs/compass/` convention
> that INT-3 introduces.

---

## Problem

A Claude Code user's first hour with Compass is worse than their first hour
with Superpowers, even though Compass has the stronger engine underneath.
The plugin hook refuses code edits in repos that have never opted in; nothing
loads the operating contract into a session; a feature run reads roughly
three times the instruction prose; and the docs carry visible rename debt.
Reviewers also have nowhere obvious to read an issue's spec, design and
verification report - they are buried in `.compass/work/` next to machine
state.

## Desired outcome

Someone who installs Compass from the marketplace gets the same
frictionless first hour they would get from Superpowers, and finds the
engine (routing, evidence, traceability, CI) already working underneath it.
Human-facing artefacts are where a reviewer would look for them.

## Success signals

- INT-1 A repo without `.compass/` is never blocked by the hook; the user
  sees nothing until they opt in.
- INT-2 The operating contract is present after every session start, clear
  and compact, without the model having to choose to load it; every command
  resolves its templates and governance from the plugin root.
- INT-3 Every artefact a human reviews (intent, acceptance criteria,
  technical design, distribution map, threat model, rollback plan,
  verification report, ADRs) lives under `docs/compass/`; `.compass/work/`
  holds only the spine, evidence and markers.
- INT-4 A quick-fix issue reads one command and one skill and produces the
  spine plus red/green evidence and nothing else; resident per-turn cost is
  at or under Superpowers' (about 1k tokens).
- INT-5 A green cannot be recorded without a red on record for the same
  scenario; the hook checks a digested red record rather than an empty
  marker; fail-closed behaviour is the same for every python failure mode.
- INT-6 The public surface carries no retired vocabulary, no dead links, and
  no claim that contradicts the routing policy.
- INT-7 A written recommendation exists on which parts of Superpowers' SDD
  controller loop transfer to the orchestrator/builder protocol.

## Constraints

- The routing engine, typed evidence and check semantics do not change
  shape; this is a product layer fix, not an engine rewrite.
- Backward compatibility with 2.0 spines holds (ADR-006).
- `.compass/work/` stays as the machine record; nothing that `compass check`
  reads moves out of it.
- Claude Code only. No cross-LLM work in this cycle.

## Non-goals

- Codex or any other runtime.
- New guardrail checks or gates (the ceiling stands).
- A third vocabulary rename. The vocabulary is frozen by ADR before INT-6
  starts, and INT-6 pays the existing debt once.

## Internal FAQ

**Why now?**
The comparison against Superpowers 6.3.0 on 26 Aug 2026 found Compass ahead
on mechanism and behind on the first hour. The blockers are small relative
to the engine and every week they stand costs adopters.

**What is in v1, and what is explicitly later?**
v1 is INT-1 to INT-6. INT-7 is a spike whose conclusion decides whether a
seventh issue exists. Merging skills beyond what INT-4 needs is later.

**How will we know it worked?**
A fresh marketplace install, in an unrelated repo, edits a file without
being blocked (INT-1). A quick fix in a Compass project completes with one
command read and under 10k tokens of framework prose (INT-4). A reviewer
opens `docs/compass/<issue>/` and finds everything they need (INT-3).

**What could make this fail?**
INT-3 is the one with the blast radius: two locations for one issue means
the spine must carry artefact paths and every reader (check, next, analyze,
receipt, ship-commit, the hook's exemptions, the examples, CI fixtures) must
follow them. Doing INT-6 before INT-3 pays the debt twice. Doing INT-5 before
INT-3 writes the red-record check against paths that are about to move.

## Affected roles

- engineer - all issues.
- product-owner - INT-3, because the placement of human artefacts is a
  product decision, and the intent-fidelity check applies before Plan.

---

## Intent-fidelity check (filled at the pre-Plan gate)

- [ ] Every success signal above maps to at least one scenario in each
  issue's `acceptance-criteria.md`.
- [ ] No scenario contradicts a constraint, pursues a non-goal, or runs
  against a product strategy.
- [ ] Checked by: {{NAME}} on {{DATE}}.
