---
id: ADR-020
title: The archive is migrated, not frozen
status: accepted
date: 2026-08-25
supersedes: 'ADR-014'
superseded_by: ''
---

## Context

ADR-014 decided that the framework's own issue archive is never edited:

> **Kept: the archive as written.** `.compass/work/` is historical record. If a
> tightened scan trips on it, the archive is exempted, never edited. A project
> whose selling point is an audit trail cannot rewrite its own audit trail to
> make a check pass.

The reasoning is sound and the conclusion does not follow from it, because
**the archive has already been edited, and that clause was written after it
happened.** The v2 vocabulary freeze ran the migrator over `.compass/work/`:
`spec.feature.md` became `acceptance-criteria.md`, `route.md` became
`delivery-approach.md`, `brief.md` became `intent.md`, in every issue
directory. The records were rewritten. The clause describes an intention, not
the tree.

What the freeze did not do was fix what pointed at those records. Measured
before this decision was taken:

```
unopenable citations on shipped surfaces : 26
of which spec.feature.md                 : 22
```

Twenty-two test modules open with a provenance line reading

```
Spec: .compass/work/<slug>/spec.feature.md (TRC-A1..A3, ...)
```

and not one of them resolves. Nothing noticed, because nothing checked. That
is the actual cost of the freeze's migration - not a rewritten record, which
is auditable in git, but a **pointer that still looks right and no longer
opens**, which is not.

So the choice is not "edit the archive or leave it honest". It is: migrate it
deliberately with the pointers repaired and checked, or leave it half-migrated
with the pointers rotting and no measurement of how many.

## Decision

**The framework's own `.compass/work/` is migrated by `compass migrate
--apply`, like any other tree, and every citation into it must resolve.**

Three parts, and the third is what makes the first safe:

1. **The migration is mechanical.** `compass migrate` performs it - the same
   verb an adopter runs, over the same map. Nothing is hand-edited, so the
   change is reviewable as a diff and reproducible by re-running the tool.
   Prose inside a record is not touched: a devlog entry that says "we called
   it Frame then" still says it, because that is the record.
2. **The record of what changed is git**, which is a stronger audit trail than
   a filename. ADR-014's worry - "a project whose selling point is an audit
   trail cannot rewrite its own audit trail" - is answered by the rewrite
   being in the history rather than by the file never moving.
3. **Every citation into the archive must open**, enforced by
   `tests/test_archive_citations_resolve.py`. This is the condition, not a
   nicety: a migration that leaves a pointer dangling has converted a readable
   record into one that reads as readable and is not, and the freeze proved
   that happens silently.

## Consequences

**Good.** The tree stops carrying two vocabularies. `_flat_names` and
`normalize_spine` remain, and remain necessary - they exist for an adopter's
tree, not for this one - but they stop being load-bearing for the framework's
own records, so a defect in them is no longer invisible here.

**Good.** 26 broken citations are repaired, and the guard means the count
cannot climb again without a test failing. Before this, the only way to learn
the number was to go and measure it, which is how it reached 26.

**Good.** `compass migrate` is exercised on a real 110-directory tree rather
than only on fixtures. TRC-C4 - a migration that stops partway - was written
because the archive is large enough for a partial run to be a real outcome.

**Cost, accepted.** Filenames in the archive change, so a link from outside
this repository to a file by its old name breaks. `.compass/work/` is
gitignored and has never been published, so that population is empty - and
unlike ADR-014's version of this argument, it stays empty, because nothing
publishes it.

**Cost, accepted.** A record's prose may now name a file whose name has
changed - a devlog saying "written to plan.md". That is left alone
deliberately: it is what the author wrote at the time, and the citation guard
only requires paths to resolve, not prose to be retrofitted.

## Alternatives considered

**Leave the archive frozen, as ADR-014 said.** Rejected: it is not frozen, and
saying so does not make it so. Freezing it *from here* would preserve the 26
broken citations permanently and leave the tree speaking two vocabularies with
no plan to stop.

**Migrate the archive and skip the citation guard.** Rejected. That is exactly
what the v2 freeze did, and the result is the 26 citations this ADR opens
with. The guard is the difference between this decision and repeating that
one.

**Repair the 26 citations without migrating.** Tempting - it fixes the visible
harm at no risk. Rejected because it leaves 36 directories holding `design.md`
and 7 holding `prd.md`, so the next rename inherits the same split archive and
the same choice, one cycle staler.

## References

- ADR-006 - backward compatibility within a major version. Unaffected: the
  read-side compatibility path is kept and still tested, because it exists for
  adopters rather than for this repository.
- ADR-014 - superseded in this respect by this ADR and in the redirect respect
  by ADR-019. Its removals stand.
- ADR-019 - retired names carry redirects once there are adopters. Same shape
  of correction: an ADR-014 clause whose stated condition had stopped holding.
- `governance/strategies.md` `S11` - measure before arguing. The 26 was counted
  before this decision was made, and it is the reason it went this way.
