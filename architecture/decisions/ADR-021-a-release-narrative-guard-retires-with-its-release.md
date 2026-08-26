---
id: ADR-021
title: A release narrative guard retires with its release
status: accepted
date: 2026-08-26
supersedes: ''
superseded_by: ''
---

## Context

`tests/test_v1_2_narrative.py` was written when v1.2.0 shipped. Its 13 checks
proved that release's new surface had reached the public documents: the
`architect-lens` agent, the `architecture/` directory, `signals.yml`,
`quarantine.yml` and the fitness functions, the trigger-on-intent rule, and the
typed inline Definition of Done tags. Each check named a heading, a table row or
a paragraph and asserted the words were still there.

That was the right guard at the time. Three releases later it had turned into a
different claim: that every capability ever shipped stays named in the front
page prose forever, in the shape it was first written. A documentation slimming
pass in 3.4.0 cut eight documents from 4,134 lines to 1,394, and seven of the
13 checks failed - not because a capability had been lost, but because the
paragraph naming it had been rewritten or moved.

The wrong answer is to relax the seven failing checks so the build goes green.
That leaves a guard whose remaining checks nobody has re-justified, and it is
the sentence a project says just before it loses coverage it needed. So the
question is asked once, for the whole file.

## Decision

Retire `tests/test_v1_2_narrative.py`. A guard that exists to prove a specific
release was documented retires when that release stops being the current story,
and this ADR is the record.

**What stopped being covered.** All 13 checks go, not only the seven that
failed. Six were still passing against live facts:

| Check | What it asserted |
|---|---|
| `trc_a1` | `AGENTS.md`'s adapter mapping table names `architect-lens` |
| `trc_a2` | all three subagent listings in `docs/portability.md` include it |
| `trc_a3` | `AGENTS.md` names `architecture-loaded.yml` and `architecture-notes.md` |
| `trc_a4` | `AGENTS.md` carries the trigger-on-intent rule |
| `trc_b2` | the README directory tree lists `architecture/` |
| `trc_d1` | `governance/README.md`'s file table lists `signals.yml` and `quarantine.yml` |

Those six facts are now unguarded in the documents. Deleting a paragraph naming
`signals.yml` from `governance/README.md` will not redden the build.

**What is still covered elsewhere**, so it is not lost with the file:

- `tests/test_architect_lens.py` proves the agent exists, has valid
  frontmatter, and is invocable from `/compass:roundtable`. The agent itself is
  guarded; only its mentions in prose are not.
- `tests/cross_cutting/test_stream_d_invariants.py` requires
  `agents/architect-lens.md` to be present in the shipped agent set.
- `tests/test_cli_surface_drift.py` guards the CLI verb listings in `README.md`
  and `docs/five-minutes.md` against `compass --help`, which is the anti-drift
  check `trc_f1` was modelled on and is not release-specific.

## Alternatives considered

**Move the content and repoint the guard.** Satisfy each failing check by
relocating the paragraph it wants from `README.md` into `docs/`, and edit the
check to read the new location. This keeps the coverage, and it also keeps the
premise: that the v1.2.0 feature list is permanently load-bearing in the
documents. Every future slimming pass pays the same cost again.

**Relax only the seven failing checks.** Rejected in the context above. It
answers the cheap half of the question and leaves the expensive half unasked.

**Write a general guard instead**, asserting that every capability named in
`CLAUDE.md` appears in `AGENTS.md` or `docs/methodology.md`. This is what
`trc_f1` did for one hand-listed set of v1.2.0 terms. Doing it generally needs a
definition of "capability" that a regular expression can find, and the honest
answer is that we do not have one yet. Recorded here as the shape a replacement
would take, not as work this decision commits to.

## Consequences

- The suite loses 13 checks and the six live facts listed above.
- Documentation passes stop being blocked by the wording choices of a release
  three versions back.
- The next release's own narrative guard, if one is written, should carry an
  expiry in its docstring saying which release it proves and when that stops
  mattering. This ADR exists because the first one did not.

## References

- `tests/test_v1_2_narrative.py`, deleted by this decision. Its content is in
  the history at the commit that references this ADR.
- `.compass/work/docs-slimming-pass/bug-report.md` states the question this
  decision answers, with the full list of 49 failing drift guards.
- `governance/strategies.md` `S10` - a guard is accepted on a demonstrated
  failure. The mirror of that rule is that retiring one needs a demonstrated
  reason, which is what this record is.
