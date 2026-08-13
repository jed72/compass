---
id: ADR-014
title: Retired names are removed at the major version rather than carried as redirects
status: accepted
date: 2026-08-13
supersedes: ''
superseded_by: ''
---

## Context

The v2 vocabulary freeze (ADR-012) renamed the pipeline's commands, verbs and
flags to industry words. Each rename left a redirect behind: seven slash
commands whose whole body says "retired name - this command is now X", a CLI
pointer that exits 2 with a line naming the replacement verb, and two flag
spellings tolerated alongside their replacements. The stated window was one
major version.

The window was written for adopters. **There are none.** Nobody outside this
repository has installed Compass, so every redirect is a promise kept to
nobody - and the window closes the moment someone installs from the
marketplace, at which point removing them stops being free.

This sits against **Inv-8**: every new mechanism no-ops on projects that have
not adopted it. Inv-8 is about not breaking people. ADR-006 already states
the condition under which a break is allowed - it is paid once, behind a
major version - and ADR-012 relied on exactly that when it froze the
vocabulary.

## Decision

**Delete the retired names outright, at a major version, while the cost of
doing so is zero.**

Removed: the seven retired slash-command files; the retired-verb and
retired-subverb pointer, and the `verbs:`/`subverbs:` data that fed it; the
retired flag spellings `--task` and `--reading`, and their call sites.

**Kept: the migrator's v1-to-v2 mapping.** `migrate-map.yml`'s `values:`,
`shape_display:` and `artifacts:` sections stay, because `compass migrate`
reads archives written under the old vocabulary and a translation table is
not a redirect. A stub answers a caller who used the old name; a mapping
reads a file that used it. Deleting the second would strand exactly the
historical records Compass tells people to keep.

**Kept: the archive as written.** `.compass/work/` is historical record. If a
tightened scan trips on it, the archive is exempted, never edited. A project
whose selling point is an audit trail cannot rewrite its own audit trail to
make a check pass.

The release is **3.0.0**. Removing a name a caller could call is a breaking
change; the version number describes the compatibility promise, not the size
of the diff. "No adopters yet" is why the removal is cheap, not why it is
minor - and calling it minor would be the first false statement in a
changelog whose entire argument is that its claims are checkable.

## Consequences

**Good.** The vocabulary becomes single-valued: there is one name for each
thing, and no live surface teaching the old one. That is what makes ADR-015's
scan tightening possible at all - a scan cannot ban a name the machinery
still answers to.

**Good.** The redirect layer stops being a place for bugs to hide. Three of
the six defects this issue fixes were the *absence* of a rename in a code
position; carrying a half-renamed surface indefinitely is what let them sit
undetected.

**Cost, accepted.** Anyone who installed a 2.x plugin and typed a v1 command
gets an unrecognised-command error rather than a helpful pointer. With no
adopters, that population is empty today and grows the longer this waits -
which is the argument for doing it now rather than the argument against.

**Cost, accepted.** 337 call sites change spelling in one sweep. Mechanical,
and verified by count rather than by reading: the replacement spellings
already worked before the old ones were removed, so no behaviour changes with
them.

## Alternatives considered

**Carry the redirects to 4.0.0.** Costs nothing today and everything later:
by then the population of affected users is non-empty, and the redirect layer
has had another major version to accumulate half-renamed code behind it.

**Delete the commands, keep the flag aliases.** The author's recommendation,
overturned by the maintainer after the call sites were counted. The argument
for keeping them was that the sweep would sprawl; 268 and 69 occurrences
across ~70 files, all mechanical, is not sprawl. Recorded because the
measurement is the reason the decision went the other way (`S11`).

**Deprecation warnings instead of removal.** A warning is a redirect that
also prints. It keeps the old name live, so it blocks ADR-015 for the same
reason a silent redirect does.

## References

- ADR-006 - backward compat is non-negotiable; a break is paid once, behind a
  major version. This decision is that clause being exercised, not an
  exception to it.
- ADR-012 - the v2 vocabulary freeze, which created the retired names and set
  the one-major-version window this closes.
- ADR-015 - the vocabulary scan covers code positions. It depends on this
  decision: a scan cannot ban a name the machinery still answers to.
- `governance/strategies.md` `S11` - measure before arguing. The flag-alias
  half of this decision reversed the author's recommendation once the call
  sites were counted.
