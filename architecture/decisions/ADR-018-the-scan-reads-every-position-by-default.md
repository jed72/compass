---
id: ADR-018
title: The vocabulary scan reads every position by default; an exclusion must be declared and reasoned
status: accepted
date: 2026-08-14
supersedes: ADR-015
superseded_by: ''
---

## Context

The vocabulary scan has been narrowed three times, in three different
positions, and each narrowing was justified with the same sentence.

| Position | Excluded because | Found wrong when |
|---|---|---|
| Markdown fenced blocks | "a backticked name is code, not prose" | a retired name shipped inside a worked example |
| Python string literals with no whitespace | "a single token is a machine identifier" | three defects hid in `cli/compass_pkg/`, printing placeholders for months past a green scan |
| YAML values | "in a machine file only the comments are prose" | `rationale:` values are printed verbatim by `compass approach evaluate`, so *"checked before Land"* reached a screen |

ADR-015 corrected the first two and framed the lesson narrowly: *"an exclusion
written for a good reason becomes wrong when the surface it applies to
changes."* That framing invited a fourth patch, and a fourth arrived.

The unifying fact is simpler and was visible each time: **a string that gets
printed is prose wherever it lives.** The position it occupies in a file says
nothing about whether a user will read it. A `rationale:` value, a `help=`
literal and a fenced transcript are all read by people; a comment is not.
"Machine identifier" was never the right question.

### The same shape, outside the scan

This is not only a scanning defect. Inside the session that produced this
record, `compass ship-commit` rejected `-F`, a shell fallback printed
"committed", and `HEAD` had not moved. The commit was reported as done and was
not done.

A **check that reports success while checking nothing** and a **command that
reports success while doing nothing** are the same defect wearing different
clothes: an output that asserts an outcome it never established. Four
instances of the first were found in one release; this is the first recorded
instance of the second. Naming the class is what stops the fifth.

The tell is the same in both: the success path is reached without the work
being observed. The remedy is the same too - make the success path depend on
an observation, as `compass tdd-red` does when it refuses to record a red for
a test that never ran.

## Decision

**The scan reads every position by default.** A file on a scanned surface
contributes all of its text unless something says otherwise.

**An exclusion must be declared, must name the positions it covers, and must
state why a string in that position cannot reach a user.** Exclusions live in
`governance/terminology.yml` under `scan.position_exemptions`, carry a `PX-`
id, and are enforced: a test fails if any entry lacks a real reason.

Two exemptions exist:

- **`PX-1` - source comments and Python docstrings.** The parser discards
  them; there is no path from a comment to a user. They are also where the
  history lives - a comment explaining that a key used to be called something
  else *is* the record, and banning the old name there would delete the
  explanation.
- **`PX-2` - YAML keys, JSON keys, JSON enum values.** These are the machine
  contract. A spine on disk, a policy file and a schema all agree on them, so
  a rename is a migration with a back-compat shim rather than a text sweep.
  The prose beside them - `description:`, `title:`, `rationale:` - is scanned.

The test is the question to ask of any future exclusion: **can a string in
this position reach a user?** Not "is this a machine identifier".

## Consequences

**Good.** A position that nobody has thought about is now scanned rather than
missed. The default was the actual defect: three separate authors each reached
the same wrong conclusion because the structure invited it.

**Good.** Where a genuine machine value must keep a retired name - the
`full-plus-backfill` stage weight, which every spine on disk reads - the
resolution is a per-line marker carrying its reason, visible to anyone reading
the file.

**Cost, measured not estimated.** Scanning every position across all 30
surfaces produces 1004 hits. Of those, 752 are in source comments and
docstrings, which `PX-1` exempts, and **26** are in the YAML value positions
this decision is really about. Sixteen of the 26 were genuine retired
vocabulary in prose users read, and were fixed; the rest were machine keys
now covered by `PX-2`.

The 752 were **not** individually reviewed, and this record does not claim
they were. They are covered by one categorical exemption whose reason is
stated and checkable.

**Cost, accepted.** Inverting the default broke the allow-marker mechanism for
YAML - markers live in comments, and comments stopped being emitted - so a
marker had to be made visible to the scanner explicitly. Recorded because it
is the kind of second-order breakage an inversion causes, and it was caught by
a guard rather than by review.

**Known limit, stated.** The prose ban patterns are capitalisation-scoped on
purpose: *"before critical changes land"* is correct English and must not
fire. So a lowercase machine value such as `expedition` sitting in a YAML
value is **not** caught by this scan. It is caught downstream, by the
printed-output guard on the evaluator, which is stricter because everything it
sees is going to a screen. Two guards with different thresholds, deliberately.

## Alternatives considered

**Patch the YAML rule and leave the default.** The obvious fourth patch. It
fixes the instance and leaves the structure that produced three of them.

**Scan every position with no exemptions at all.** Rejected on measurement:
752 hits in comments, most of them comments that exist precisely to explain a
historical name. It would delete the repository's own account of its rename.

**Infer "is this printed" automatically** - trace string literals to output
calls. Rejected as far more machinery than the problem needs, and it cannot
work for data files at all: whether a `rationale:` value is printed depends on
the consumer, not the file.

## References

- ADR-015 - superseded. Its two corrections stand; its framing ("name the
  surface an exclusion was reasoned about") is replaced by the inverted
  default, which does not rely on anyone remembering to ask.
- ADR-012 - the v2 vocabulary freeze, which this enforcement serves.
- ADR-014 - retired names removed at the major version, which is what made
  scanning code positions possible at all.
- `governance/strategies.md` `S10` - mutation proof. The widened scan is
  broken on purpose in the newly covered position, with a control proving it
  stays quiet in the exempt one.
- `governance/strategies.md` `S11` - measure before arguing. The 1004 / 752 /
  26 split was produced before this decision was taken, and it is what made
  the shape of the exemptions obvious.

## Postscript - the class appeared inside the issue that named it

A test written for this issue asserted `stream_ceiling > 1` and passed because
of an invented value (`swarm: 8`) that nothing in the policy supported - an
assertion passing for the wrong reason, written after the document explaining
that outputs assert outcomes they never established.

Recorded here because it is the strongest evidence in this record and it
arrived after the record was written. It means this is not legacy debt being
cleaned up: it is a live tendency that reproduces under someone actively
thinking about it, which is why the remedy is a standing habit - ask what
would have to be true for this assertion to fail - rather than a sweep.
