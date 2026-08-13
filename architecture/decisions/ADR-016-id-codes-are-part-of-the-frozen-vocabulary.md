---
id: ADR-016
title: Id prefixes are part of the frozen vocabulary, and routing rule ids say routing policy rather than guardrail
status: accepted
date: 2026-08-13
supersedes: ''
superseded_by: ''
---

## Context

Compass artifacts are dense with short codes. A single issue directory can
carry `TRC-A1`, `INT-1`, `EV-003`, `DD-2`, `BF-1` and `RG-FLOOR-006`, and a
reader meeting any of them has nowhere to look it up. Measured across the
shipped surfaces: `TRC-` 639 occurrences, `INT-` 542, `ADR-` 118, `DD-` 59,
`EV-` 43, `SCN-` 41, `RG-` 30, `BF-` 22, `RS-` 11, `CLM-` 5.

`governance/terminology.yml` is the only glossary that exists. ADR-012 froze
it, and it defines 53 terms - initiative, issue, slice, delivery approach -
without mentioning a single code. The gap was found by asking "where do I look
up `TRC-`?" and getting no answer.

Investigating it turned up a second problem. Some prefixes encode words the v2
freeze banned, and they survived because ids are not prose: the vocabulary
scan reads what a surface teaches, and a code is a machine identifier that
happens to be made of letters.

## Decision

**Id prefixes are vocabulary, and they live in the frozen file.** A `codes:`
section sits beside `terms:`, each entry stating what the code means, what it
refers to, and where it appears. `docs/glossary.md` is derived from it;
`compass terminology` renders codes as well as terms.

**The set of codes is derived from use, not maintained by hand.** The guard
scans shipped artifacts for prefix patterns and requires a definition for each
one it finds. A hand-kept list would be the version-location table again: a
list somebody must remember to extend, which reads as complete whatever it
omits.

**Routing rule ids become `RP-` - routing policy.** `RG-` was wrong because of
the `G`. `guardrail` is a frozen term meaning one of the five hard rules
cleared with evidence; `RG-FLOOR-001` is not one of them. Compass already made
this correction once, renaming the spine key `fired_guardrails` to
`policy_rules_fired` for exactly this reason, and the id never followed.
`RS-` was already correct - `routing_strategies:` is the literal key - but
`RP-` unifies both into one namespace with one thing to document.

The `R` survives deliberately. `route` is banned as *the computed process
shape*; `routing` was never banned and is thoroughly alive. The sentence that
holds is: the navigator does the routing and produces a delivery approach.

**Floors and gate-adders are distinguished.** A floor is a lower bound on
process weight. Only three of the seven entries in the `floors:` block do
that; the other four attach a gate when a condition matches and raise no
minimum at all. They become `RP-REQUIRE-*` while remaining physically in the
`floors:` list, with a comment saying the block name follows in the
machine-key slice.

## Consequences

**Good.** The glossary can define `RP-FLOOR` and `RP-REQUIRE` honestly. Keeping
all seven under one id would have forced the definition "either a minimum
weight or an added gate" - the vague definition this work exists to eliminate,
which would make the deliverable self-defeating.

**Good.** A new prefix cannot enter the repository undefined. The guard derives
its set from what is in use, so the failure arrives with the prefix rather than
years later when someone asks what it means.

**Cost, accepted.** For one release the `floors:` block contains entries whose
ids say `REQUIRE`. Cosmetically odd, and honest: the block name is the thing
that is wrong, and moving it is a structural change to a file the evaluator
iterates and the schema validates. That is filed as its own issue with a
back-compat shim.

**Cost, accepted.** The rename is not purely opaque data. The schema does not
constrain the id, and the evaluator only copies it into `policy_rules_fired` -
but one test asserts two of these ids by literal value, and it moves in the
same commit. Checked before the assessment rather than discovered during
implementation.

**The archive keeps the ids that fired.** `.compass/work/` holds live
`RG-FLOOR-006` records, including the spine of the issue that made this
decision. Historical records keep the id that actually fired, and a scenario
asserts no archived file is modified.

## Alternatives considered

**A hand-written glossary page.** Correct on the day it is written. This
repository has produced three separate documents this cycle that restated a
machine-readable source and drifted: a version table that said six while there
were seven, a transcript promising to be reproducible verbatim that no longer
matched, and a routing policy documenting its own conditions in retired names.

**Only the CLI, no page.** `compass terminology TRC` serves an agent with a
shell. A person meeting `TRC-A1` in a pull request wants a URL.

**Defining `EV-` as "evidence the Definition of Done was met".** Rejected on
the mechanism: `guardrails.yml` states a gate's evidence is a list of ids into
a shared registry and that multiple gates can share one entry. The DoD is one
consumer among several, so the definition anchors on the quality gate instead.

**Renaming `SCN-` to be canonical instead of `TRC-`.** The parser's anchor is
the literal keyword `traceability id:`, so `TRC-` keeps keyword and prefix in
agreement; and `SCN-` presumes every traced thing is a Given/When/Then, which
a non-functional requirement is not.

## References

- ADR-012 - the v2 vocabulary freeze, which this extends from terms to codes.
- ADR-015 - the vocabulary scan covers code positions. Ids are the case that
  motivated asking what else the scan cannot see.
- ADR-006 - backward compatibility. The read side stays tolerant: retired tag
  spellings still parse and archived ids are never rewritten.
- `governance/strategies.md` `S10` - the drift guard is proved able to fail
  before it counts.
