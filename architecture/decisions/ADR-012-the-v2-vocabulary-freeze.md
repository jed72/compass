---
id: ADR-012
title: The v2 vocabulary is frozen - industry words only, enforced by the build
status: accepted
date: 2026-08-07
supersedes: ''
superseded_by: ''
---

## Context

Compass v1 wrapped its two load-bearing ideas - process sized to the change,
and hard rules enforced with evidence - in a private vocabulary: Frame, the
Needle, readings, routes, lenses, Express, Expedition, Specify, Clarify,
Distribute, Land, G1-G5 and S1-S7 as user-facing codes. Every one of those is
a word an engineer must learn before Compass makes sense, and none of them
needed inventing: the industry already has triage, assessment, delivery
approach, quick fix, initiative, acceptance criteria, requirements review,
ship. The v2 redesign's first observable target is that a colleague with no
Compass exposure reads a full session transcript and never asks what a word
means.

v2 is a deliberate breaking release - the one moment a clean vocabulary break
is affordable, while the user base is small. That card is spent exactly once:
a v3 rename is not available for years. So the v2 vocabulary is not a style
preference to drift around; it has to be frozen, and the freeze has to be
mechanical.

The mechanism landed first (2026-08-06; it reached `origin/v2` inside the
squash commit 2d45d84, and the issue's full evidence trail lives in the
repository's work archive under `v2-terminology-freeze`):

- `governance/terminology.yml` - every v2 term with its exact meaning, the
  banned v1 vocabulary, and the scan config naming the user-facing surfaces.
- `tests/test_terminology.py` - well-formedness checks, per-ban patterns
  proven against a fixture pair (each ban must catch its banned sense and
  tolerate the same words in ordinary English), and a shrink-only
  `pending_surfaces` ratchet that keeps CI green while the rename proceeds
  surface by surface: a pending surface may still carry v1 terms, a surface
  removed from pending must stay clean forever, and the pending list can
  only shrink against a baseline committed in the test.

One numbering correction: the v2 planning notes (local working papers under
`docs/proposals/`, untracked by design) assigned this decision "ADR-010"
before ADR-010 and ADR-011 landed with other decisions. This record is
ADR-012; the planning notes are the stale reference, not this file.

## Decision

**The v2 vocabulary defined in `governance/terminology.yml` is frozen, and
changing it carries decision-record ceremony.**

1. **Industry words only.** A term that is not in common use across the
   industry does not ship. If the industry has no word for a concept, the
   concept is questioned before a word is coined. One word per concept:
   "epic" is dropped for initiative, "task" survives only as machine state
   during the transition, never in prose.
2. **The banned list is enforced, pattern-plus-context, never bare words.**
   `tests/test_terminology.py` owns the executable patterns; the vocabulary
   file's context notes are the intent; the fixture pair is the proof the
   two agree. Ordinary English reuse of a banned word ("frame the problem",
   "order of magnitude") stays legal by test.
3. **The ratchet only tightens.** Surfaces leave `pending_surfaces` as their
   rename slice ships and never return. Growing the pending list, or
   re-introducing a banned term on a clean surface, is a build failure.
4. **Post-freeze vocabulary changes are recorded decisions.** Any change to
   a term's meaning, any new ban, any un-banning, and any growth of the
   scanned or pending surface sets requires: an amendment to
   `governance/terminology.yml` with its version bumped, in the same diff as
   the change it describes, plus either a decision record superseding or
   extending this one, or - for additive gap-filling that changes no meaning
   and no ban - a written maintainer instruction recorded in the issue's log
   (the 2.0.0-pre2 bump that defined three already-referenced terms is the
   precedent for that lighter path).
5. **Command names clear the same bar.** Every command is an industry verb;
   the command table is proposed against this rule and lands with a
   vocabulary version bump in the same diff.

## Consequences

- The entire v2 rename becomes a red-to-green migration: the house test
  fails wherever v1 vocabulary survives on a cleaned surface, so drift is a
  CI failure rather than a review nit. The pending list burning down to
  empty is, by definition, the rename being done.
- Adopters relearn once. v2.0.0 is a breaking release with a migration tool;
  no long-lived aliases, because two names per concept is the private-
  vocabulary problem doubled.
- The freeze binds this repository's own prose first: every v2 session
  writes test names, comments, commit messages, and artifacts in the frozen
  vocabulary, and the framework's own surfaces are the scanned surfaces.
- Future flexibility is deliberately reduced. A genuinely better word found
  in 2027 costs a decision record and a migration note, not a quiet edit.
  That is the point: the target state is that two years out the words are
  still the industry's words, and the terminology command still answers
  vocabulary questions from the same file the build enforces.

## Alternatives considered

- **Keep the v1 vocabulary.** Rejected: the cold-transcript test is
  unreachable while the framework speaks words it invented, and the
  vocabulary tax lands on every new user forever.
- **Long-lived aliases (v1 and v2 names both valid).** Rejected: every
  concept then has two names, documentation must teach both, and the scanner
  cannot distinguish a legacy alias from drift.
- **Gradual rename across ordinary releases, no freeze.** Rejected: each
  release would relearn some vocabulary, adopters would chase a moving
  target, and without a frozen file plus enforcement there is nothing to
  stop later sessions drifting back - which was the predictable failure the
  freeze was built against.
- **Freeze by convention, without the house test.** Rejected: a freeze that
  is only prose is an opinion. The evidence-not-assertion guardrail applies
  to the framework's own promises.

## References

- `governance/terminology.yml` - the frozen vocabulary this decision
  protects; its version history is the freeze's amendment log.
- `tests/test_terminology.py` and `tests/fixtures/terminology/` - the
  enforcement: patterns, fixtures, and the shrink-only ratchet.
- The `v2-terminology-freeze` issue in the repository's work archive - the
  freeze landing's full evidence trail under the framework's own
  governance (its original per-slice commits were squashed into 2d45d84
  when the branch first reached `origin/v2`).
- **ADR-002** (the framework grows by adding artifacts, not rules) - the
  freeze adds no guardrail; it is enforced as house invariants of this
  repository, the same class as the writing-style tests.
- **ADR-006** (backward compatibility is non-negotiable) - why the break is
  paid once, behind a major version with a migration tool, rather than
  spread across minor releases.
