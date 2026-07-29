---
id: ADR-001
title: Judgement and mechanism are separated
status: accepted
date: 2026-05-24
supersedes: ''
superseded_by: ''
---

## Context

Early in Compass's design, the framing step produced both the context
readings (blast radius, terrain, magnitude, intent) and the computed route in
a single pass. There was no clear boundary between the human's input and the
system's output.

This created two problems. First, it was difficult to audit: if the route
seemed wrong, you could not tell whether the human had misread the terrain or
whether the routing logic had applied a policy incorrectly. Second, it made
the mechanism fragile: if you wanted to change the routing policy, you had to
be careful not to accidentally also change what constituted a "reading" - the
two concerns were entangled.

The framework needed a design decision: should judgement and mechanism be
co-located for simplicity, or separated for auditability and correctness?

## Decision

We separate human judgement from framework mechanism at a hard boundary.

`task.yml.readings` is the only field a human fills in. It records exactly
four context dimensions: blast radius, terrain, magnitude, and intent + role.
These are the human's assessment of the task's character. No mechanism writes
into `task.yml.readings`; no mechanism reads from it except to pass it as
input to the routing computation.

Everything else is mechanism-produced: the route, phase weights, gate set,
scenarios, changed_files, evidence, backfills, reframes, and the
`architecture-loaded.yml` record. These live in named files and fields outside
`task.yml.readings`. They are recomputable given the readings; the readings
are not recomputable from them.

The routing computation (`compass route evaluate`) is a pure function of the
readings and `governance/routing-policy.yml`. Run it twice with the same
inputs: same output.

## Alternatives considered

| Alternative | Why considered | Why rejected |
|---|---|---|
| Co-locate readings and route in a single `framing:` block in `task.yml` | Simpler schema - one block for everything Frame produces | The human's judgement becomes indistinguishable from the computed result; audits cannot determine which changed when a re-frame occurs |
| Let the mechanism propose initial readings (pre-filling blast radius, terrain) and have the human confirm | Reduces human effort at Frame | Pre-filled values become anchors; the human loses calibration discipline; the feedback loop that makes the Needle improve over time (via `/compass:calibration`) breaks |
| Store readings in a separate `readings.yml` file outside `task.yml` | Clean separation at the file level, not just the field level | Creates a two-file coordination problem; `task.yml` is the task spine - splitting it creates surface for inconsistency |

## Consequences

**Positive:**
- Audits are unambiguous: a wrong route means either wrong readings (human
  error, feedbacks into calibration) or wrong policy (policy bug, fixes the
  YAML). The two failure modes are distinguishable.
- Re-frames are first-class: `task.yml.reframes` records every time a human
  changed the readings, with a `--reason`. The history is inspectable.
- Deterministic mechanism: tests can assert that given fixed readings and a
  fixed policy, the route is always the same. `tests/test_route_selection.py`
  and `tests/fixtures/route-baseline.yml` hold the mechanism to this contract.

**Negative:**
- Every framework task now requires a human to fill in four dimensions before
  any code-changing tool call. This is friction. On small or obvious tasks, it
  can feel like ceremony. The framework accepts this cost deliberately - the
  calibration signal is worth more than the saved seconds per task.
- Mechanism-produced state living outside `task.yml.readings` means the schema
  has multiple sections with different write-authorities. New contributors
  sometimes misplace state into `readings` by accident, which is why
  `architecture/ownership.md` states it as a boundary rule. The `compass check`
  validation catches this, but the rule needs to be taught.

**Neutral / follow-on:**
- This decision implies that a tool that proposes readings ("I think this is
  `magnitude: standard` because...") is an advisor, not an automator - the
  human must confirm before the reading is written. This is the Needle's
  design intent; it is not an exception to this ADR.

## References

- Compass methodology: `docs/methodology.md` §"The one rule that creates every other rule"
- Invariant Inv-1 (Frame is mandatory; `readings` is the only judgement field), defined in `architecture/decisions/README.md`
- Boundary rule: no mechanism may write loaded architecture content into `task.yml.readings` (`architecture/ownership.md`)
- `governance/routing-policy.yml` (the policy the mechanism runs)
- `tests/fixtures/route-baseline.yml` (the regression fixture for determinism)
