---
id: ADR-019
title: Retired names carry redirects once there are adopters
status: superseded
date: 2026-08-25
supersedes: 'ADR-014'
superseded_by: 'ADR-024'
---

## Context

ADR-014 decided that a retired name is deleted outright at the major version
rather than carried as a redirect. Its argument rested on one fact, stated
plainly in its own Consequences section:

> Anyone who installed a 2.x plugin and typed a v1 command gets an
> unrecognised-command error rather than a helpful pointer. With no adopters,
> that population is empty today and grows the longer this waits.

**That population is no longer empty.** Compass is published to the plugin
marketplace and released at 3.3.0. Someone can install it, learn
`/compass:triage` and `compass design lint`, write them into a script or a
project's own instructions, and upgrade.

The vocabulary rename of 2026-08-25 is the first rename to land in that world.
It moves four names: `triage` to `assess`, the engineering `design` command to
`plan`, `wireframe` back to `design`, and the CLI verb `design lint` to
`plan lint`. Under ADR-014 as written, all four would break on upgrade inside
major version 3 - which ADR-006 forbids.

So ADR-014 and ADR-006 now disagree, where before they agreed. ADR-014 was
ADR-006's "a break is paid once, behind a major version" clause being
exercised at a moment when the break cost nothing. It costs something now, and
the major version has not turned.

## Decision

**A name retired inside a major version keeps working until the next one. A
name retired AT a major version is deleted, as ADR-014 said.**

The rule ADR-014 got right was "a break is paid at a major version". The rule
it got wrong was inferring from a zero-cost moment that redirects are never
worth carrying. Both halves are kept:

- **Slash commands** retire to a stub: a file under 40 lines whose whole body
  names the replacement and tells the session to stop. It does not do the
  work. `commands/triage.md` and `commands/wireframe.md` are this cycle's two.
- **CLI verbs** retire to a working alias, not a pointer. A slash command is
  read by a session that can be redirected; a CLI verb is called by scripts
  and CI, where failing with advice is still failing. `compass design lint`
  runs, and says once on stderr what to call it now.
- **A retired name is never advertised.** The stub carries `retired` in its
  own description; the aliased verb is hidden from `compass --help`, so no
  teaching surface documents a name a reader should not use. This is what
  keeps ADR-015's scan possible: the scan bans the name everywhere a reader
  learns it, and the machinery answering to it is not a teaching surface.
- **Every retired name is named individually**, in `CURRENT_STUBS`
  (`tests/test_no_deprecation_stubs.py`) and in the `hidden` set in
  `cli/compass`. A third stub is a deliberate addition, not a silent one.
- **They go at the next major version.** The same removal ADR-014 performed at
  3.0.0, one cycle later, for this cycle's names.

## Consequences

**Good.** An adopter who upgrades inside major version 3 keeps working. That
is what ADR-006 promises, and it is the promise a published framework is
judged on.

**Good.** The removal is scheduled rather than open-ended. ADR-014's real
target was an indefinite redirect layer that "accumulates half-renamed code
behind it", and naming each stub individually with a removal version is what
stops that, rather than never having one.

**Cost, accepted.** The vocabulary is two-valued for one major version, in
exactly two places: two command files and one hidden CLI verb. ADR-015's scan
still bans the retired names on every scanned surface; the stubs are exempted
by name, with a reason, not by a path pattern.

**Cost, accepted.** A whole-file scan exemption on a stub means that file is
unscanned for every banned term, not only its own. Two files, each under 40
lines, each of which is a pointer and nothing else.

**Consequence of the supersession.** ADR-014's *actions* stand: the seven v1
slash commands, the retired-verb pointer, and the `--task` and `--reading`
flag spellings are gone and stay gone. They were removed at a major version
with the population empty. This ADR changes the rule going forward, not that
removal.

## Alternatives considered

**Leave ADR-014 as written and break the four names.** Rejected: it breaks
ADR-006 inside a major version, on a released and published framework, to
honour a decision whose own stated condition ("there are no adopters") has
stopped holding.

**Hold the rename until 4.0.0.** Rejected. The rename fixes names that are
actively wrong today - a command called `triage` writing an `assessment:`
block, a `design` command whose machine key says `plan`, and `/compass:intent`
writing `prd.md`. Holding a correction for a version boundary means teaching
the wrong word for longer, to more people.

**Make the CLI verb a pointer that exits 2, matching the slash-command stub.**
Rejected after separating the two cases. A session that reads a stub can act
on it; a CI job that gets exit 2 has already failed. The two surfaces have
different callers, so they get different treatment, and this ADR says why
rather than leaving the inconsistency to be read as an oversight.

## References

- ADR-006 - backward compatibility is non-negotiable within a major version.
  This ADR restores that clause where ADR-014 had come to contradict it.
- ADR-014 - superseded by this one. Its removals stand; its rule does not.
- ADR-015 - the vocabulary scan covers code positions. It required that no
  live surface teach a retired name; "not advertised" above is how that holds
  with the machinery still answering to one.
- `governance/strategies.md` `S11` - measure before arguing. The fact that
  changed is the adopter count, and it is the reason the decision moved.
