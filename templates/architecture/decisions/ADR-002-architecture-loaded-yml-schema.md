---
id: ADR-002
title: Architecture-Loaded Yml Schema
status: accepted
date: 2026-05-23
supersedes: ''
superseded_by: ''
---

## Context

When Frame loads the project's `architecture/` artifacts, it needs to expose
the result to downstream agents (spec-author, planner, architect-lens) in a
structured, persistent form.  The first design placed this data in
`manifest.yml.readings` - the existing machine-readable task manifest.  However,
`readings` is the *judgement* block, where the Needle records its four-dimension
assessment.  Mixing mechanism-produced load state into the judgement block
violates the invariant that `readings` is the only judgement field.

## Decision

Frame writes a separate file: `.compass/work/<task>/architecture-loaded.yml`.

Schema (version 1.0):

```yaml
schema_version: "1.0"
loaded_at: <ISO timestamp>
artifacts:
  - path: <relative to project root>
    sha256: <hex digest>
    type: narrative | structured
    parsed: <inline YAML>   # structured artifacts only
adrs:
  - id: "ADR-NNN"
    path: <relative path>
    title: <string>
    status: proposed | accepted | superseded
```

The `sha256` field lets downstream agents detect whether an artifact changed
between Frame time and when they read the loaded record.

## Alternatives considered

| Alternative | Why considered | Why rejected |
|---|---|---|
| `manifest.yml.readings.loaded_artifacts` | Single file, no extra artifact | Violates the invariant that `readings` is the judgement block only |
| Inline in `route.md` prose | Humans can read it without a separate file | Agents need structured access; prose is not machine-parseable |
| Separate JSON sidecar | Already common in many tools | YAML is the project's standard; keeping it consistent reduces tooling friction |

## Consequences

**Positive:**
- `readings` stays clean: only judgement, no mechanism state.
- `sha256` enables mid-task drift detection.
- `parsed` on structured files means downstream agents do not re-read disk.

**Negative:**
- One extra file per task in `.compass/work/<task>/`.

**Neutral / follow-on:**
- The schema is versioned (`schema_version`); future additions are additive.

## References

- The invariant that `manifest.yml.readings` holds judgement only, and nothing a mechanism produced
- The boundary rule that a builder never writes loaded architecture content into `readings`
- The task's `clarifications.md`, where the shape of this file was settled
