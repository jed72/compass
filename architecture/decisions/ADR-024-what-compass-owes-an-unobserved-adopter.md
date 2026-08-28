---
id: ADR-024
title: What Compass owes an unobserved adopter
status: accepted
date: 2026-08-28
supersedes: 'ADR-019'
superseded_by: ''
---

## Context

ADR-019 reversed ADR-014 and brought back redirect stubs, a hidden CLI verb
alias, and the read-side rename tables. It rested on one stated fact, quoted
from its own Context:

> **That population is no longer empty.** Compass is published to the plugin
> marketplace and released at 3.3.0.

**Publication is not adoption.** Nothing here counts installs, so the adopter
population is not empty and not non-empty - it is *unknown*. ADR-019 read
publication as evidence of a non-empty population. ADR-014 before it read
pre-publication as evidence of an empty one. Both inferred a quantity from a
proxy that does not measure it, then argued confidently from the inference.
The two records disagree about a number neither of them had.

That is the failure `S11` names: the disagreement was about a quantity
somebody had guessed, and the guess was doing the arguing.

The cost was not theoretical. Each retired name carried a command file, an
entry in a vocabulary that then held two values for one concept, and a
whole-file scan exemption - so those files went unscanned for *every* banned
term, not only their own. The hidden verb alias carried a second parser branch
and a `hidden` set whose stale entries are invisible, because the set is only
ever subtracted from the advertised list.

## Decision

**4.0.0 removes the retired names.** `/compass:triage`, `/compass:wireframe`,
`/compass:roundtable` and the `compass design` verb alias are gone, at the
major-version boundary ADR-019 already authorised removal at. ADR-006 is
untouched: a break inside a major version stays forbidden, and this is not one.

**Redirects are not carried on the strength of an inferred population.** The
quantity the rule turns on is the number of adopters who would be broken by a
removal. It is observed the only way this project can observe it: someone says
so - an issue, a bug report, a pull request, a message. Until that happens the
population is unknown, and an unknown population does not justify machinery
paid for every cycle.

**What Compass owes an unobserved adopter is a migration path, not a
redirect.** `compass migrate` brings an issue directory written under an older
vocabulary forward, and the read-side rename tables it depends on stay. Those
tables are kept because **ADR-020** requires them - the archive is migrated,
not frozen - and not because of any promise to adopters. That distinction is
the point of this record: the same code serves two populations, and only one
of them was ever in dispute.

**If the population is observed, redirects come back.** Once a real adopter is
known to exist, a retired name gets a redirect through the following major
version, and this decision is revisited with a number in hand rather than a
proxy.

## Consequences

- A session or script calling a removed name gets an unknown-command error.
  `docs/releasing.md` lists every removal beside its replacement.
- The vocabulary holds one value per concept again, and no file is exempted
  from the scan for being a stub.
- `Inv-8` is untouched and stays where it is defined, on ADR-006. Its promise
  is that **a new mechanism does nothing to a project that has not adopted
  it** - a no-op on absent prerequisites. That is not the same claim as "a
  retired name keeps working". ADR-019's framing ran the two promises
  together, which is how the first was used to justify the second. They are
  two different claims and this record separates them: the no-op promise
  continues unchanged and is not weakened here.
- There is no install telemetry and this record does not add any. Building it
  is out of scope. The observation named above is one nobody performs today
  because nothing collects it - it is unperformed, not impossible, and saying
  which matters more than naming it.
- Anyone reading ADR-019 now arrives here.

## Alternatives considered

**Schedule 4.0.0 and write nothing.** The cheapest option, and most of what
this record does is already authorised by ADR-019. Rejected because a release
removes *these* names and touches nothing else. ADR-019 decided the rule for
renames **inside a major version**, and decided it on the wrong inference. Left
standing, the first future rename inside 4.x rebuilds the stubs, the alias and
the two-valued vocabulary on the same reasoning, and the release will have
bought one cycle. What this record adds beyond the schedule is exactly that
rule, and nothing else.

**Remove the names inside 3.x.** Faster, and rejected outright: it needs
ADR-006 superseded, which is a far larger decision than this one, for a saving
of one release.

**Keep the redirects until someone complains.** This is ADR-019 restated with
a softer trigger. Rejected because it inverts the cost: the machinery is paid
every cycle by the project, and the benefit is owed to a population nobody has
been shown to be collecting. The condition above puts the trigger before the
machinery rather than after it.

**Delete the read-side rename tables too.** The intake for this work counted
them as compat cost. Rejected on the facts: they are what lets an archived
manifest load, so removing them breaks ADR-020's promise about the archive
whatever is decided about adopters.

## References

- `.compass/work/what-compass-owes-an-unobserved-adopter/` - the issue, its
  acceptance criteria and its verification.
- ADR-006 - backward compatibility is non-negotiable within a major version.
  Untouched; this record supersedes the interpretation, not the principle.
- ADR-014 - retired names are removed at the major version. Its reasoning made
  the mirror-image error to ADR-019's, in the other direction.
- ADR-019 - the record this supersedes.
- ADR-020 - the archive is migrated, not frozen. The reason the read-side
  rename tables stay.
- `docs/releasing.md` - what 4.0.0 removed, and what to call each thing now.
- `governance/strategies.md` `S11` (measure before arguing) - the strategy that
  names the failure both earlier records made.
