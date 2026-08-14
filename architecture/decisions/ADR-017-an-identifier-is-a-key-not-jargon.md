---
id: ADR-017
title: An identifier is a key, not jargon - attach its meaning, never delete the id
status: accepted
date: 2026-08-14
supersedes: ''
superseded_by: ''
---

## Context

A maintainer ran Compass the way a first-time user would. An agent told them
"the G5 guard kicked in". They had no idea what a G5 guard was, and were
annoyed.

Nothing had taught the agent that phrasing. `governance/guardrails.yml` uses
the id as each guardrail's primary key, so an agent reading the file and using
the key as the name is doing the obvious thing. Measured across the shipped
surfaces: bare `G1`-`G5` appears **zero** times in `skills/`, `commands/` and
`agents/`, and **nineteen** times in `governance/`. The phrasing came from the
data, not from any instruction.

`governance/terminology.yml` had governed this since the v2 freeze, and its
entry was wrong:

```
term:        "G1..G5 / S1..S7 codes"
replacement: "the plain statement of the rule"
context:     "In human-facing output. Codes may live in governance config."
```

It says **replace** the code with its statement - delete the id. That is the
opposite of what the codes are for: `TRC-`, `EV-`, `INT-` and the guardrail
ids are the join keys of the traceability chain, and `compass check`,
`compass analyze` and the DoD tag parser all read them. A writer who followed
the entry literally would break the machine checks to improve a sentence.

It also contradicted the CLI. `compass check` has always printed
`G5 A human signs off on the irreversible` - the id and its meaning together.
The correct standard already shipped, in code, and the vocabulary told writers
to do something else.

Two things about how this was found are worth recording, because they are the
reason the amendment is defensible rather than a preference:

- **The entry was wrong from the freeze**, not broken by a later change. It
  passed every review the freeze had, and the scan that enforces it never
  fired, because no surface it covered contained a bare code.
- **It surfaced through irritation, not analysis.** A first-time user hit it
  and said so. No amount of re-reading the vocabulary would have produced the
  finding, because everyone re-reading it already knew what G5 meant.

## Decision

**An identifier is a key, not jargon.** The fix for an unexplained id is to
attach its meaning; it is never to delete the id.

Stated as the rule writers and agents follow: **an identifier appears with its
plain statement on first use in any one piece of output, and as the bare id
every time after that.** Both halves are load-bearing. Expanding on every
mention is its own readability defect, and the bare id after the first use is
shorter and reads better once the meaning is known.

This governs **agent speech**, **printed output** and **generated artifacts** -
anything a human reads. `governance/strategies.md` `S7`, the cold-reader
strategy, carries it, because that is where the guidance shaping an agent's
prose already lives.

`compass check` is named as the shipped example rather than a new convention
being invented beside it.

**The stale `S1..S7` range is corrected to `S1..S12` as a plain correction.**
It needs no decision record: nothing was decided, a range simply fell behind
the strategies it names.

## Consequences

**Good.** The vocabulary and the CLI now say the same thing, and the thing
they say is the one that keeps the traceability chain intact.

**Good, and general.** The principle extends past guardrail codes to every
prefix ADR-016 defines. A reader meeting `TRC-A1` or `RP-FLOOR-002` gets the
same treatment, and the receipt was changed in the same slice to print a
scenario's title beside its id.

**Cost, accepted.** First use is a judgement about scope - "this piece of
output" is a message, a file, or a command's output, and nobody can check it
mechanically. This is a strategy, assessed by a reviewer, not a guardrail. A
test asserts the *guidance exists and says the right thing*; no test can
observe what an agent says in a session, and claiming otherwise would be the
defect class this cycle is named after.

**Cost, accepted.** Amending a frozen entry's meaning is a heavier act than
adding a term, which is why this record exists. The entry count did not
change; what it means did.

## Alternatives considered

**Add a new term instead of amending.** Rejected: it would leave two entries
disagreeing, and the older one is the machine-readable one the scan reads.

**State the rule only in `S7`.** Rejected: `terminology.yml` would still tell
a writer to delete the code, and it is the file the enforcement reads.

**Drop the codes from user-facing output entirely**, as the original entry
said. Rejected on the mechanism: `compass check`, `compass analyze` and the
Definition-of-Done tag parser all resolve work by these ids. Removing them
from what a human reads would leave the human unable to cite what the machine
just told them.

## References

- ADR-012 - the v2 vocabulary freeze. This amends one of its `banned:`
  entries; the freeze is why that takes a decision record.
- ADR-016 - id prefixes are part of the frozen vocabulary. This states the
  rule for *using* the prefixes that record defines.
- `governance/strategies.md` `S7` - the cold reader, which now carries the
  rule.
- `mission.md` - names the vocabulary as frozen, which is what makes changing
  the meaning of an entry an architectural decision rather than an edit.
