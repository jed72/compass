---
id: ADR-015
title: The vocabulary scan covers code positions, not only prose
status: accepted
date: 2026-08-13
supersedes: ''
superseded_by: ''
---

## Context

`tests/test_terminology.py` enforces the v2 vocabulary freeze (ADR-012)
surface by surface. It deliberately scanned less than the full text of two
file types, and the reasoning was written down at the time:

- **In markdown**, fenced blocks (the triple-backtick kind) and inline code
  spans (the single-backtick kind) were skipped, because "a backticked
  `/compass:frame` names a command that really is still called that during
  the transition - so markdown contributes prose only."
- **In Python**, docstrings and *string literals with no whitespace* were
  skipped, because "a single token is a machine identifier (a spine key, a
  filename, a flag), not prose."

Both were reasonable when written, and the second is the more interesting
one. It is not a slip - it is a heuristic that was **true of the surface it
was written for and false of the surface it was applied to**. A whitespace-free
literal is very often a machine identifier. It is also exactly the shape of:

```python
task.get('route', '?')                     # a retired spine key
os.path.join(task_dir, "plan.md")          # a retired artifact filename
```

Three of the six defects in this cycle hid in precisely that shape, inside
`cli/compass_pkg/` - a surface the scan already covered. The guard reported
success on files containing the exact names it existed to ban. `compass
check`'s header printed a placeholder on every run and the cross-issue board
printed one on every row, for months, past a green scan.

The exclusions could not be removed while ADR-014's retired names were still
live: banning a spelling the machinery still answers to would fail on the
machinery itself.

## Decision

**With the retired names gone (ADR-014), the scan reads code positions too.**

- **Markdown:** inline code spans *and* fenced blocks are scanned.
- **Python:** string literals are scanned regardless of whether they contain
  whitespace. Docstrings remain excluded - they teach the developer reading
  the source, not the user at the terminal, and the scan measures what the
  CLI says.
- **`hooks/` becomes a scanned surface.** It was never on the list, which is
  how a hook telling users "Frame has not run" survived the entire v2 rename.

**Deliberate back-compat spellings move into data.** A few reads must still
name a v1 key to load an old archive - `task.get("phases")`, `route.md`.
Those move into `cli/migrate-map.yml`, which is scan-exempt *as data*, and
are read from there. This is not a loophole: it is the same mechanism the
retired-verb pointer already used, and it has the property that every
remaining v1 spelling in the codebase lives in one file that a reader can
enumerate.

**Where a fenced block must legitimately quote a historical name** - a
changelog entry, a worked example about the rename itself - the resolution is
a named exemption with a stated reason, never a quiet loosening of the scan.

**The archive is exempt and never edited** (ADR-014).

## Consequences

**Good.** The guard can now fail in the position where it actually failed.
`RCD-G5` requires that to be demonstrated rather than assumed - the tightened
scan is broken on purpose in each newly-covered position before it is
accepted, per `S10`.

**Cost, measured not estimated.** Tightening produces **200 hits across 38
files**. That number was produced by running the tightened rules against the
real tree before the decision was taken, and it is the reason the decision
was taken: the objection to tightening was that it would sprawl, and 200
mechanical hits is not sprawl. A large share are the `--task` spelling that
ADR-014 removes anyway.

**Cost, accepted.** Scanning fenced blocks means a future example that quotes
old output needs an explicit exemption. That is a small tax on writing, and
the thing it buys is that no v1 name can enter the repository unnoticed
inside a code fence.

**A general lesson, recorded because it will recur.** An exclusion written
for a good reason becomes wrong when the surface it applies to changes, and
it does so *silently* - the scan keeps passing, which reads as coverage. Any
future narrowing of a scan should name the surface it was reasoned about, so
the next person can tell whether that reasoning still holds.

## Alternatives considered

**Fix the four call sites, leave the scan as it was.** The author's initial
recommendation. It repairs the symptom and leaves the guard unable to catch
the next occurrence - the defect class, not the defect.

**Tighten markdown only**, as originally scoped. Would have left the Python
exclusion in place: the surface where three of the six defects actually hid.

**Scan inline spans but not fenced blocks.** The author's recommendation,
overturned by the maintainer. The objection was that fenced blocks hold
terminal transcripts where quoting a historical name is the point; the
measurement showed the real cost was small and bounded, and the exemption
mechanism handles the genuine cases. Recorded because the numbers, not the
argument, decided it (`S11`).

## References

- ADR-012 - the v2 vocabulary freeze. `tests/test_terminology.py` is its
  enforcement, and this decision widens what that enforcement can see.
- ADR-014 - retired names are removed at the major version. This decision is
  only safe once that one has landed.
- `governance/strategies.md` `S10` - mutation proof. `RCD-G5` requires the
  tightened scan to be broken on purpose in each newly-covered position
  before it counts as a guard.
- `governance/strategies.md` `S11` - measure before arguing. The 200-hits
  measurement, not the argument, settled how far the tightening should reach.
