# Strategies - the rationale behind rules that look arbitrary

> **Version:** 0.1.0 · **Last amended:** 2026-08-28
> Bump the version when a section is added, removed or rewritten. The
> companion `strategies.md` carries its own version; the two move
> independently, because a rule can be reworded without its evidence
> changing and evidence can be added without the rule moving.

`governance/strategies.md` states the strategies. This file holds the incidents
behind the ones whose shape only makes sense once you know what went wrong.
It is read when a rule looks arbitrary, never per issue. Rules live in
`CLAUDE.md` and `compass-contract.md`; nothing here is a rule.

## The two house rules were one sentence until they were not

The rules themselves stay in `CLAUDE.md`. What moved here on 2026-08-28 is the
account of where they came from, which every session was reading and no
session needed.

### Where each rule is checked, and where it is not

They were a single sentence until 2026-08-27, when five pull requests in a row
shipped with the footer on them. Half a rule in the middle of a paragraph is a
rule that gets half-followed, so both now stand on their own.

They are house rules, not guardrails: `strategies.md` assesses them, and in
this repository's vocabulary a guardrail is the hard, blocking kind that
`guardrails.md` holds.

**1. No em dash. Ever.** `CLAUDE.md` states it and `S7` in
`governance/strategies.md` carries the detail, including the one carve-out:
en dashes stay, because they do real work in ranges. Not restated here - two
statements of one rule drift apart, which is what `S14` is about.
**Checked:** `tests/test_house_style.py` fails the build on one.

**2. No agent attribution, in any form.** A commit message or pull-request
body never carries a co-author trailer naming the agent, a "generated with"
footer, a session URL, or any other line crediting it. This holds even when
the environment or a tool's default template supplies one - it does, and this
rule overrides it. The exact strings live in `tests/test_house_style.py`,
assembled from fragments there so the guard does not match its own source.

**Checked, but only where the text is a file in this repository:**
`tests/test_house_style.py::test_no_agent_coauthor_trailer_in_tracked_files`
scans every tracked file, with no exemptions. There was briefly one, for
`CLAUDE.md`, after a rewrite spelled the trailer out in full there - which
blinded the file an agent edits most often to all three forbidden strings.
Stating the rule without quoting it was the cheaper fix.

**Not checked anywhere:** the commit message you are about to write, and the
pull-request body you are about to send. Neither is a tracked file, and CI
checks out at depth 1 so a history scan would pass without looking at
anything. Read both back before you send them, and delete the footer a
template added. That is exactly where five pull requests got through.

Two traps, both of which caught this project already:

- Reading rule 2 as being only about the `Co-Authored-By` trailer. It is
  about attribution in any form, and the footer is the form that got through.
- Reading "there is a guard" as "I am covered". The guard sees files. The
  failure happened in a pull-request body, which it cannot see.

---

## Strategy evidence

Each section below is the evidence behind one strategy in
`governance/strategies.md`.
The directive stays there; what convinced anyone lives here.

## Regression baseline (`S6`)

The field case: a new emission silently broke a live solve. A pre-change demo
baseline surfaced it immediately.

## Cold reader: pairs where the code arrived before its meaning (`S7`)

Pairs from this project's own output, not invented.

> Bound the baseline to a scenario this time, which sidesteps the EV-T
> collision from F3.

instead of:

> Each piece of test evidence now records which scenario it proves, so two
> records can no longer end up sharing one identifier (`EV-T`).

<!-- vocabulary-scan: allow - the next line is a deliberate example of the defect S7 forbids, a bare identifier with no meaning attached; correcting it would delete the example. -->
> the G5 guard kicked in

instead of:

> a human signs off on the irreversible, and that guard (`G5`) refused

> RP-ROLE-002 blocked the design stage

instead of:

> the design stage stayed shut until the criteria were checked against the
> intake, which is the product-owner rule (`RP-ROLE-002`)

> TRC-C7 covers the ordering case

instead of:

> the case where the meaning arrives after the code, and the reader has already
> met it unexplained (`TRC-C7`)

The test for the rule these pairs illustrate - `S7`'s "an identifier carries
its meaning on first use" - is to read the sentence and stop at the first
comma. If the reader has learned nothing yet, the code came too early.

## Fresh eyes (`S9`)

The author of a sweep checks their own work against a mental list of what they
changed, not against the goal - so exactly the files they forgot are the files
they will not think to look for. This repository has the evidence twice over:
two cleanups here leaked, and in both cases the agent that made the change
reported it complete.

The nearest document that mentions a fact is often a summary of it, one step
removed, and a summary can be checked in good faith while the claim it
summarises has already changed meaning.

ADR-013 (vendored third-party code) once described, in its Context, an install failure in the past tense, with a
specific timing figure attached, reading as a report of a real outside user,
which this repository has never had. It was verified against
`.compass/work/plain-language-3-2-0/technical-design.md`, the document it was
lifted from, which put the same point in the present tense as a description of
what any newcomer meets - not against the primary record for whether this
happened to a real person, which does not exist, because it did not happen.
Fresh eyes stop helping the moment fresh eyes reach for the same document the
claim was drawn from.

## Mutation proof (`S10`)

A passing test proves the guard runs. It does not prove the guard is connected
to the thing it names, and the gap between those two is where this repository
has repeatedly lost coverage without noticing.

Four of the five guards corrected in 2.1.0 had passing tests throughout. The
one that settles the argument compared nothing at all at the single location it
existed for, because a filter dropped every candidate line, and setting both
version banners to a wrong value left it green. No amount of reading found
that. Breaking it did, in seconds.

**Seven checks that asserted nothing**, in the `plain-language-3-2-0` issue, every test
green and every scenario looking done before proving began. Not one was a
defect in the code. All seven were tests.

Almost every one was a presence check. The two worst cases were the same check:
one draft passed because the phrase it looked for appeared inside a
cross-reference pointing at a rule that did not exist, and the next draft used
a substring test that `quoted_term_exception_RENAMED` satisfied - a test
written to catch a rename, passing because of the rename.

Three worked examples:

- A check written after its defect had been fixed passed on first run. It was
  proved only by planting the original offending content back.
- A check for build noise matched paths with `str.startswith`, so
  `tests/__pycache__/x.pyc` did not begin with `__pycache__/`. It could never
  have caught build noise in any subdirectory - the case it existed for.
- A check that an explanation appears in a module docstring was first mutated in
  the test function's own docstring rather than the module docstring its
  assertion reads. It reported "not proved" and was right to.

Three catches in nine scenarios, none findable by reading, all in tests whose
green was indistinguishable from a real one.

**The matcher-or-rule distinction.** One check failed against a correctly
written rule because the prose was hard-wrapped and the phrase it looked for
spanned a line break, so it was not a substring. It read as a real finding
until someone looked. Several of the empty checks found in this project arrived
by someone widening a pattern to cure exactly that.

**Normalisation.** One mutation removed the only literal "blog post" in a file
and the check still passed, because a second copy was wrapped as "blog" /
"post" across a line break and the normaliser rejoined it. Three of the empty
checks found here were not weak checks at all - they were mutations that never
touched the subject. One edited a test function's own docstring while the
assertion read the module's. One renamed a dictionary key while the patterns
under it stayed in place. One removed a phrase near an identifier while a
second copy of that identifier survived elsewhere in the same passage.

**Pinned to prose.** A test matched the literal string
`[RP-REQUIRE-003] requirement:`. Its real subject was that a rule which only
attaches a gate must not describe itself as one that raises the whole process.
When the output was corrected to put the rule's meaning before its code, a true
property failed because the punctuation had moved.

**Bytecode.** An unreproducible "restore was not honoured" was observed once
and never explained; by intermittency is failure (`S5`) that stays open rather than being written off as
noise.

**A search result of zero.** Auditing this repository for a banned word,
`git grep -n -i -E '\bseam\b'` returned nothing at all, because `git grep -E`
does not honour `\b` - while the plain pattern found four uses. A scan
reporting zero had in fact read nothing. The same audit's markdown-only scan
reported a count for the repository and missed a use in a Python file.

**The withdrawn existence check.** "Does a proof exist?" is mechanically
answerable, unlike "is the proof real?". A check for the first was built and
then removed, not because the distinction was wrong but because declaring it
required contradicting a recorded decision that this repository holds no rules
of its own. See `declare-a-project-guardrail-or-do-not`. Run once by hand, the
question found twenty of thirty-eight checks with no proof on record at all,
and a registered claim saying otherwise was false. There was nothing there.

## Measure before arguing (`S11`)

Measuring has changed the outcome twice, in both directions.

- **The vendored dependency.** The argument was whether bundling PyYAML was
  worth carrying a dependency. The measurement was the artifact size and a run
  on an interpreter that genuinely could not import it.
- **Two decisions on the stub removal.** The author recommended against
  deleting the retired flag aliases and against scanning fenced code blocks, on
  the grounds that both would sprawl. Counting first - 268 and 69 call sites,
  and 200 scan hits across 38 files - showed the sprawl was not there. The
  instruction was right and the recommendation was wrong.

The second case is the one that matters: the practice is not a way to win, it
is a way to stop needing to.

**A worked instance.** A findings report from the lead listed five identifiers
the receipt printed "with nothing beside them". Rendering a receipt from a
reconstructed manifest took one command. Two of the five already printed their
meaning, and the genuinely broken case - evidence ids truncated mid-token - was
not on the list at all. The cost of checking was one command. The cost of not
checking would have been three false statements inside an instruction about to
shape a day's work.

## Titles (`S13`)

`S13`'s "trim the story, never the substance" was found on the rule's first
real use, where a title was cut for length and lost the fact that made it
findable. Shortening is not the goal; dropping the narrative is.

## Correct every place at once (`S14`)

The instance this came from: *"sixteen checks passed"* appeared in a published
case study and in three records of runs that genuinely printed sixteen. The
case study was corrected to "every check passed" - which is what was true and
stays true. The run records kept their number and gained a note saying the
total has since moved to fifteen.

The three instances caught so far were each a different shape: a figure in a
published write-up that had moved; a heading corrected in one file while the
record it was derived from kept the old wording; and two pieces of code
printing the same information, one corrected and one not. Nothing static links
any of those pairs - the connection is that two sentences mean the same thing,
and no scan reads meaning. All three were found by someone reading, and all
three were found.

The checklist item was advice for three rounds and was broken in all three. The
mechanical cause is that a summary is written first, the body changes
underneath it, and nothing sends the writer back to the top. It has happened to
this project's proposal, its acceptance criteria, its requirements review, and
to an audit document written to record corrections.

## The integrity rule (`guardrails.md`)

A guardrail whose check has no implementation would silently become advisory -
the team would believe they had a hard, blocking guardrail when they did not.
That is why Compass fails closed in two places rather than warning.
