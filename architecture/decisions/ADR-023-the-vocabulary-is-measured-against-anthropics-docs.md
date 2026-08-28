---
id: ADR-023
title: The vocabulary is measured against Anthropic's platform docs
status: accepted
date: 2026-08-27
supersedes: ''
superseded_by: ''
---

## Context

ADR-012 froze the v2 vocabulary on one rule: **if a term is not in common use
across the industry, it does not ship.** That rule has no reference text. "In
common use" was settled per term, by argument, at the moment each was named.

Compass runs inside Claude Code and is read by people who read Anthropic's
platform documentation. That documentation is a reference text, and measuring
against it turns the rule from a judgement into a check someone else can repeat.

Measured across the 146 user-facing `.md` and `.yml` files, against
`docs/glossary.md`, which opens with the claim that it holds "every word and
every id prefix Compass uses":

| Term | Hits | Files | Glossary entry |
|---|---|---|---|
| `stream` | 192 | 66 | none |
| `swarm` | 105 | 40 | none |
| `topology` | 73 | 40 | none, and it is a key in two schemas |
| `ceremony` | 49 | 28 | none |
| `distillation` | 39 | 18 | none |
| `coherence check` | 29 | 13 | none |
| `fitness function` | 28 | - | none |
| `charter` | 7 | 4 | none |

The glossary defines 62 terms and 12 id prefixes. **None of the eight is one of
them.** They were not exceptions granted after argument; they were never
examined, because nothing measured them.

Two of them are worse than unfamiliar. They are words the reader already knows,
meaning something else:

- **`distillation`.** In any AI-adjacent codebase this means training a smaller
  model from a larger one. Compass means reverse-engineering existing behaviour
  into scenarios. The skill is called `blueprint-distillation`, so the wrong
  reading arrives first.
- **`ceremony`.** Agile teams own this word: a ceremony is a meeting. Compass
  means process weight, as in "pay back the ceremony borrowed for speed".

A third is a competitor's product name: **`swarm`** is the name of OpenAI's
experimental multi-agent framework.

`lens` is the counter-example that shows the machinery works when it is pointed
at something. It was banned with replacement `role`, and bare concept uses are
now at **zero**. The 124 remaining hits are the hyphenated agent identifiers
(`product-lens`, `marketing-lens`, `architect-lens`), which the ban pattern
carves out on purpose until those agents are renamed. The ban worked; the rename
it was waiting for is in this change.

`terminology.yml` states that the vocabulary is frozen and that changing it
carries the same weight as a decision record. This is that record. It amends
ADR-012 rather than replacing it: the freeze stands, and so does the rule. What
changes is that the rule now names where "common use" is read from.

## Decision

**Where a term has a counterpart in Anthropic's platform documentation, Compass
uses their word with their meaning. Where it does not, Compass uses plain
English with no competing meaning.**

| Retired | Replacement | Source |
|---|---|---|
| `swarm` | `multiagent` | "Multiagent orchestration" |
| `topology` (key) | `orchestration` | single agent versus multiagent |
| `stream` (unit of work) | `subtask` | "Fan out independent subtasks" |
| `stream_ceiling` | `subtask_ceiling` | consequential |
| `navigator` (agent) | `router` | the "Routing" workflow pattern |
| `-lens` (agent identifiers) | `product-owner`, `product-marketer`, `architect` | the Specialization pattern: "agents with domain-focused system prompts" |
| `roundtable` (command) | `consult` | an advisor is "consulted mid-turn" |
| `intent-elicitation` (skill) | `intent-interview` | the onboarding "interview" |
| `charter` | `assignment` | plain English |
| `fitness function` | `architecture check` | plain English, and see below |
| `verify.fitness` (gate id) | `verify.architecture` | consequential |
| `coherence check` | `consistency check` | plain English |
| `distillation` | `behaviour mapping` | plain English |
| `ceremony` | `process weight` | plain English |

**`ratchet` is deliberately kept.** Maintainer's ruling, 2026-08-27. It was on
the candidate list and was taken off it.

**The rule cuts both ways, and the clearest evidence is a term it rejected.**
`fitness function` was first mapped to **`eval`**, which is Anthropic's word and
appears throughout their docs. It was dropped on inspection: an eval measures
model output against success criteria, and a Compass fitness function is an
architectural rule about code structure. Borrowing the word would have imported
a meaning it does not have here, which is the precise defect this record exists
to prevent. Matching Anthropic's spelling is not the test; matching their
meaning is.

## Alternatives considered

**Leave the eight terms and add glossary entries for them.** Cheaper, and it
answers the lookup problem without touching a schema. Rejected because it does
nothing for the two collisions: a reader who thinks `distillation` means model
distillation does not consult a glossary, because they do not know they have
misread anything.

**Rename the prose and leave the machine keys.** This was the maintainer's
explicit instruction to reject. It also repeats the defect ADR-015 records for
`compass check`'s placeholder header: a retired name survives in printed output
past a green scan, because the scan was not reading what the tool prints.
`topology` is a key in `manifest.schema.json`, and `verify.fitness` is a gate id
`compass check` prints on every run. Both are teaching surfaces.

**Keep a third orchestration value so `pair` survives.** Rejected. `pair` in
engineering means two people on one thing; Compass meant two agents on two
separate things. A vocabulary that says `single` and `multiagent` and then needs
a third word meaning "multiagent but small" has not simplified anything.

## Consequences

**Backward compatibility holds and is not assumed** (ADR-006). Machine keys
migrate read-side through `cli/migrate-map.yml`, the way `task.yml` did
(ADR-022). Nothing under `.compass/work/` is rewritten: the archive is migrated
on read, and an archived manifest keeps saying what it said. Retired command
names get redirect stubs for one major version (ADR-019).

**The routing policy gets simpler, not just renamed.** Route shapes declared a
`topology:` word that `routing.py` immediately converted to a ceiling number
through a lookup table. Since the words retire anyway, the shapes declare the
number directly and the conversion goes. The lookup survives in
`cli/compass_pkg/core.py`, where it is still needed to read archived manifests.

**Accepted decision records keep their words.** The terms appear in ADR bodies
`lens` 62 times across 9 files, `fitness` 32 across 5, `stream` 14 across 7,
`ceremony` 5 across 5. None is edited. Each retired term instead lists the
specific record paths that name it, by full path, in the per-term exemption
table - the same form `spine / issue spine` already takes for ADR-022, and for
the same stated reason: the record has to say what it renamed and why. The broad
`"lens": ("architecture/",)` prefix is replaced by those specific paths, which
tightens the guard.

**This record is itself exempt**, for every term it retires, on that same
ground. It cannot state a rename without naming both spellings.

**The freeze is not weakened by being amended twice.** ADR-012 froze the
vocabulary "for years" and a rename landed three weeks later; ADR-022 named that
pattern. The honest reading is that a freeze without a reference text can only
be reopened by argument, and argument is always available. Naming the reference
text is what makes the next reopening harder than this one.

## References

- `.compass/work/anthropic-aligned-vocabulary/` - the issue, its measurements
  and its verification.
- ADR-006 - backward compatibility within a major version.
- ADR-012 - the vocabulary freeze this record amends.
- ADR-015 - a retired name in printed output survives a green scan.
- ADR-019 - retired names carry redirects once there are adopters.
- ADR-020 - the archive is migrated, not frozen.
- ADR-022 - the issue record is a manifest; the precedent for a decision record
  keeping the words it was decided in.
