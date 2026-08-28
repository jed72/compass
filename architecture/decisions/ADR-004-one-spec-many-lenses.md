---
id: ADR-004
title: One spec, many lenses; the lens annotates, never forks
status: accepted
date: 2026-05-24
supersedes: ''
superseded_by: ''
---

> **Vocabulary note (ADR-023, 2026-08-27):** the concept this record calls a
> *lens* is now called a **role**, and the three agents it describes are named
> after their roles: `product-owner`, `product-marketer`, `architect`. The
> record keeps the word it was decided in; only the name has moved.


## Context

Compass has five roles - engineer, product owner, designer, marketer, QA -
plus an architect lens. Each role reads the task's specification with different
concerns. A product owner reads for user outcomes; an engineer reads for test
coverage; a marketer reads for claims that need evidence.

There was an early impulse to give each role its own specification artifact:
an "engineering spec" with Given/When/Then scenarios, a "product spec" with
user story format, a "QA spec" with risk matrices. Many teams work this way in
practice, and the tooling supports it (distinct templates for each role).

The question Compass had to answer was: when the engineering spec and the
product spec diverge (as they inevitably do in long-lived projects), which one
is authoritative?

## Decision

There is one specification artifact: `spec.feature.md`. Every role reads it.
No role forks it into a parallel specification.

Role-specific concerns are expressed as annotations: the architect-lens writes
`architecture-notes.md`; the product lens writes a `brief.md` that feeds into
the spec; the marketer works from `positioning.md`. These are upstream inputs
to the spec (brief, positioning) or downstream annotations on the spec
(architecture-notes). None of them is a parallel specification.

The lens pattern is the canonical form for role-specific annotations: a lens
agent reads `spec.feature.md` and produces an annotation artifact. The lens
never writes scenarios into its output. It may flag that a scenario is
missing or underspecified, but the fix happens in `spec.feature.md`, not in a
parallel file.

The architect-lens hard boundary encodes this: "You never write
Given/When/Then scenarios into `architecture-notes.md`. Your output is
annotations, candidate ADR titles, and boundary-risk flags."

## Alternatives considered

| Alternative | Why considered | Why rejected |
|---|---|---|
| Let each role maintain its own spec format (engineering: Gherkin; product: user stories; QA: risk register) | Matches many teams' existing practice; roles feel less constrained | When specs diverge, there is no single acceptance criterion. "Does this feature pass?" becomes unanswerable without reconciling multiple documents. Compass is designed to make that question have one answer. |
| Keep one spec file but allow lenses to append scenarios to it | Ensures scenarios stay in one file; lenses can add missing coverage | A lens that writes scenarios becomes a parallel spec author. The lens's scenarios may not be reviewed to the same standard as the spec-author's. Traceability (G3) requires knowing who wrote each scenario and why - a mixed-authorship file defeats this. |

## Consequences

**Positive:**
- There is one file that answers "what are the acceptance criteria for this
  task?" - `spec.feature.md`. Reviewers, verifiers, and the build agent all
  read the same file.
- Traceability is clean: every scenario in `spec.feature.md` traces to an
  intent; every changed file in `task.yml.changed_files` traces to a scenario.
  No scenario lives outside this file.
- The architect-lens can annotate without risk of polluting the spec.

**Negative:**
- A lens that finds a genuinely missing scenario cannot fix it directly - it
  must flag the gap and wait for the spec-author to update `spec.feature.md`.
  This is a workflow friction point, especially when the lens is invoked late
  in the pipeline.

**Neutral / follow-on:**
- Role-specific views of the spec (for a marketer, a product owner) are
  addressed by the `role-translation` skill, which reads `spec.feature.md` and
  produces a role-appropriate summary. The summary is never stored as a
  canonical artifact - it is transient output for the role's consumption.

## References

- Invariant Inv-5 (one spec, many lenses; lenses annotate, never fork), defined in `architecture/decisions/README.md`
- Boundary rule: a lens never emits Given/When/Then scenarios; those live only in `spec.feature.md` (`architecture/ownership.md`)
- `agents/architect-lens.md` §"What you do NOT do"
- `docs/methodology.md` §"Roles"
- `CLAUDE.md` §"Roles"
