# Strategies

Strategies are the many soft things. They are **directional** (they say how
the team tends to work, and what it prefers), **assessed** not checked (a
reviewer judges whether a strategy was followed - there is no pass/fail
artifact), and **accretive** (cheap to add, expected to evolve, fine to drop).
A strategy *biases* a decision. It does not block one. A guardrail always
beats a strategy.

This file ships with a small set of **default method strategies** - the way
Compass works out of the box. Below them is a **project strategies** section
that starts empty and grows as the team forms opinions. An empty project
section is a valid, complete state - see `README.md` on gradient-not-threshold.

> **Version:** 0.10.0 · **Last amended:** 2026-08-16

---

## Default method strategies

These ship on. They are how Compass satisfies the guardrails by default -
strong, shipped-on, and you would need a deliberate, recorded reason to
deviate. They are still *strategies*: a spike can suspend the first
two, and a project can refine any of them.

### BDD: behaviour as Given/When/Then (`S1`)

Acceptance criteria are expressed as Given/When/Then scenarios, and those same
scenarios are the acceptance check at Verify. This is the shipped-on way to
satisfy **the acceptance-before-code guardrail** ("acceptance defined before it is built"). The
scenario file is also the shared artifact every role reads - see
`docs/roles-guide.md`.

*Why a strategy and not a guardrail:* acceptance-before-code - that acceptance is *stated and
checkable* - is the hard line. Given/When/Then is the *form*. The form is
strong and shipped-on; a context where it genuinely does not fit is a strategy
deviation, not a framework violation.

### TDD: red, green, refactor (`S2`)

Code is built by writing the failing test first, watching it fail for the
right reason, writing the minimal code to pass, then refactoring. This is the
shipped-on way to satisfy **the tested-before-ship guardrail**. The
pre-tool hook enforces red-before-green by default.

TDD serves **two purposes**, not one. The first is governance: red-before-green
is the mechanism that makes tested-before-ship checkable - it ensures there is a test, and that
the test was there first. The second is **design feedback**: a hard-to-write
test is the design speaking. TDD is less about testing and more about good
design. A test that is painful to set up, or that needs elaborate mocking to
run, is not a test problem - it is a design problem. The red-green-refactor
loop is the design-feedback loop: listen to the test, and reshape the design.

*Why a strategy and not a guardrail:* tested-before-ship - that code is *tested before it
lands* - is the hard line, checked at verify and at ship time.
Red-before-green is the
*discipline* that gets you there reliably. It is the strong default on every
route except **Spike**, where it is suspended so exploration is not throttled.
A one-character typo fix still satisfies tested-before-ship; it does not need to perform the
full ritual to do so. This is the distinction that keeps Compass from being a
sledgehammer on small changes.

### Simplest thing that satisfies the guardrail (`S3`)

Prefer the simplest change that clears the guardrails and the route's gates.
Not the cleverest, not the most general, not the most future-proof - the
simplest that is actually correct. Complexity is added in response to a
demonstrated need, not in anticipation of one.

### Persistence over conversation (`S4`)

Decisions, specs, routes, and rationale live in files (`.compass/work/<task>/`,
`governance/`, `docs/`), not only in a chat transcript. A later session - or a
different agent - should be able to resume from disk. If it is not written
down, it did not happen.

### Intermittency is failure (`S5`).

A test that fails then passes without an intervening source change is not a
clean green - it is the loss of the most useful signal a test suite produces.
A rerun-to-green hides a real failure behind timing, environment state, or
shared mutable setup. It is never trusted as a pass.

When a test reruns to green: either fix the root cause or quarantine the test
in `governance/quarantine.yml` with a tracking issue. Silence is not evidence
(the evidence-not-assertion guardrail). The `no-trusted-rerun` check attached to evidence-not-assertion reads the
`attempts` and `rerun_without_change` fields from evidence records and refuses
to clear silently when a rerun is unaccounted for.

*Cross-reference: evidence-not-assertion (evidence, not assertion). See also `governance/quarantine.yml`.*

---

### Regression baseline: green before, re-run after, on shared surface (`S6`)

**Soft, assessed - not a guardrail.** When a change touches shared or critical
surface (`risk` cross-cutting or critical), the highest-value evidence
is a *baseline*: run a designated existing end-to-end / regression suite green
**before** the change, keep the change additive / guarded, and re-run it
**after**. Record both as `test-run` evidence on `verify.regression`.

This is tested-before-ship's spirit applied to the *non-regression of untouched behaviour* - it
catches a high-consequence break in code you did not mean to change (the field
case: a new emission silently broke a live solve; a pre-change demo baseline
surfaced it immediately). The designated suite is a project knob
(`project.regression_baseline_suite` in `.compass/config.yml`; falls back to
`project.test_command`). Build prompts for the baseline **up front**, not as an
afterthought; `compass approach evaluate` surfaces it under
`applicable_strategies` when the assessment match (`RP-ADV-001`).

It adds **no guardrail and no new gate**, and it **does not block shipping** when
absent - it reuses the existing `verify.regression` gate and is assessed as
reviewer judgement (a strategy note), never a mechanical failure. The framework
grows by adding artifacts, not rules (ADR-002, ADR-006).

*Cross-reference: tested-before-ship (tested before it lands), applied to non-regression;
`verify.regression`; `routing-policy.yml` `advisory_strategies` RP-ADV-001.*

---

### Cold reader: write so a stranger can follow it without asking (`S7`)

**Soft, assessed - not a guardrail.** Assume the reader has zero prior
context. They were not in the conversation, they have not read the review, and
they cannot ask a follow-up question.

**The surfaces this governs**, stated plainly because the coverage was
invisible until someone went looking for it and did not find it:

- **Artifacts** - the intake, the acceptance criteria, the delivery-approach
  record, the design, the devlog, the verification report.
- **Code comments.**
- **Commit messages.**
- **Pull-request bodies and review comments.**

Anything on that list is written to stand on its own.

This is persistence over conversation carried one step further. Persistence
over conversation says put it on disk. The cold reader says put enough on disk
that the next reader does not need the conversation you had while writing it.

**Context before detail.** Say what the thing is and why it matters before you
say how it works. A reader who does not yet know why should not have to reach
the last paragraph to find out.

**No dangling references.** Never write "Option 2", "Finding 1/3", "per the
review", "as discussed", or an internal review number. Each of those points at
a conversation the reader does not have, and the pointer rots the moment that
conversation ends. Name the thing instead. When you link an issue or a pull
request, say in the same sentence what it actually is - "#412, which moved rate
limiting into the gateway" - so the sentence still works when the link is dead.

**An identifier carries its meaning on first use.** Compass is dense with
short codes, and a reader meeting one has nowhere to look it up mid-sentence.
So the first time a code appears in any one piece of output, it appears with
its plain statement beside it; every mention after that is the bare code,
which is shorter and reads better once the meaning is known. This governs
**agent speech**, **printed output**, and **generated artifacts** alike -
<!-- vocabulary-scan: allow - the next line quotes the WRONG form on purpose; backticking it would turn the bad example into a good one. -->
saying "the G5 guard kicked in" to someone who has never read
`guardrails.yml` communicates nothing.

`compass check` is the shipped example: it prints `G5 A human signs off on
the irreversible`, the identifier and its meaning together. Match it rather
than inventing a second convention. Never solve this by dropping the code -
the codes carry the traceability, and the machine checks read them.

**The plain words come first; the code follows in brackets.** An identifier
carrying its meaning is the rule above. This is the order, which that rule never
settled. A code placed first makes the reader hold an unresolved symbol while
they wait to find out what it meant - and if they stop reading at the comma,
they never do. Put the meaning where they already are, and the code where they
can search for it.

Pairs from this project's own output, not invented:

> Bound the baseline to a scenario this time, which sidesteps the EV-T
> collision from F3.

instead of:

> Each piece of test evidence now records which scenario it proves, so two
> records can no longer end up sharing one identifier (`EV-T`).

<!-- vocabulary-scan: allow - the next line is a deliberate example of the defect this rule forbids; correcting it would delete the example. -->
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

The test: read the sentence and stop at the first comma. If the reader has
learned nothing yet, the code came too early.

Never solve this by removing the code. The codes carry the traceability and the
machine checks read them - deleting one trades a reader's small confusion for a
broken chain. `tests/test_plain_language.py` counts the ones that arrive
unexplained and reports the number against a recorded baseline; it never fails a
build, because a number that can fail a build becomes a number people write
around.

**Correct a retired name in a comment you were touching anyway.** The
vocabulary scan does not read comments or docstrings - the parser discards
them, so nothing there reaches a user. That exclusion is recorded as position
exemption `PX-1` in `terminology.yml`, which is the list of places the scan
deliberately does not read and the reason for each. But the
752 retired names sitting in them are the reservoir the next user-facing
string gets copied from, which is close to how the v1 vocabulary spread in
the first place. So: no sweep, and no obligation to go looking - but a
comment you are editing for another reason gets its retired name fixed on the
way past. It drains without a big bang.

**Self-contained, and short.** Say it once, plainly, then stop. Length is not
thoroughness: an artifact nobody finishes has communicated nothing. Cut every
sentence that only restates the one before it.

**No agent co-author trailer.** Commit messages and pull-request bodies never
carry a `Co-Authored-By:` line naming an agent, and never a "Generated with"
footer. The human author owns the change; what typed it is not part of the
permanent record. `devlog.md` and `task.yml` already hold the provenance that
matters, in a form the framework can read.

*Why a strategy and not a guardrail:* clarity is judgement. No mechanical check
tells you whether a stranger would understand a paragraph, and inventing one
would produce a rule you could satisfy while still writing badly. The
`reviewer` agent assesses this at Verify under the `clarity` review dimension;
nothing here fails `compass check`.

*Cross-reference: persistence over conversation (persistence over conversation), which this extends; traceability
(traceability) - a reference the reader cannot resolve is not traceability.
Assessed under the `clarity` review dimension; restated at the point of use in
`commands/ship.md` (commit messages).*

---

### A title is a summary, not a headline (`S13`)

**Soft, assessed - not a guardrail.** A pull-request or commit title is read by
someone scanning a list of thirty, and read again in six months by someone
searching for the change. Both want the same thing: what the change does, in the
words they would search for.

**Say what it does.** "Add rate limiting to the search endpoint". "Fix the
timeout error message to name the size limit". "Remove retired CLI flags; add
glossary; fix six defects" when it genuinely does several things - name the main
one and leave the rest to the body.

**Four shapes it refuses**, each named because each is a different temptation:

- a **slogan** - "Make the record trustworthy again"
- a **theme** - "Clarity week: part two"
- a **play on words** - "Guarding the guards"
- a **"the X that Y" construction** - "The check that could not fail"

**The test:** if the title would work as a blog post title, it is wrong. A blog
post title is written to make you click; a pull-request title is written to save
you opening it.

**Body prose is different, and the distinction matters.** A neat formulation is
allowed and is often the clearest thing to write in a paragraph - "a number
reported without saying what it counts is as hard to act on as a code reported
without saying what it means" earns its place in prose. The same sentence as a
**heading** does not. A heading is a label; a label that has to be decoded is a
worse label than a plain one.

**Scope: pull-request titles and commit titles. Deliberately NOT ADR titles.**
Stating a decision as an assertion is ordinary practice in an architecture
decision record and it earns its keep - a reader learns the decision from
`an-identifier-is-a-key-not-jargon` without opening the file, and learns nothing
from `identifier-naming-policy`. This note exists so nobody applies the rule by
analogy and starts flattening them.

**Commit titles follow the same rule.** Not a second rule that says the same
thing: the pull-request title rule above, applied unchanged. Two statements of
one rule drift apart, and then a contributor has to work out which is current.

**The body is a description, not a narrative.** `templates/pull-request-body.md`
is the shape: what changed, what breaks, how to check it, where to look.
Sections and lists rather than paragraphs. Leave out the story of how the work
went - what was tried, what was discovered, what it taught you. A reviewer wants
the state of the code, not the journey to it, and the journey is the most common
reason a body gets too long to read.

**This forbids narrative, not length.** Read as one rule the two run together,
and it then fights real substance: a change with a lot in it is allowed to be
long, and four sections of genuine content running to a page is a large change
honestly described. Trim the story, never the substance. Found on this rule's
first real use, where it pushed against a description that needed the room.

*Why a strategy and not a guardrail:* no mechanical check can tell a summary
from a slogan. `tests/test_plain_language.py` checks that the rule is stated and
that the template has its sections; whether a given title obeys it is the
reviewer's judgement under the `clarity` dimension.

### Correct every place at once, or you have made it worse (`S14`)

**Soft, assessed - not a guardrail.** When a figure, a decision or a claim is
corrected, every place stating the superseded version is corrected in the same
change.

**A correction that leaves the record contradicting itself is worse than the
original error**, because the next reader now has two answers and no way to tell
which is current. One wrong number is a mistake; one wrong number and one right
number is a document that cannot be trusted anywhere.

Say what is superseded and why, not only what is now true. A reader who meets
the old version somewhere you missed can then tell which way the correction ran.

**Which places take a correction, and which take a note.** The rule above says
apply it everywhere it belongs. This says where that is, because without it a
moved number forces a false choice - falsify a record to keep it consistent with
today, or leave a false claim standing because rewriting felt dishonest.

- **A record of what happened keeps its number and gains a note.** A devlog
  entry, a dry-run result, a captured command output, an archived spine. These
  say what was observed at a moment. Rewriting one falsifies it: it becomes a
  transcript of something that did not happen. Annotate instead - what the figure
  was, that it has since moved, and that nothing should be quoted from there.
- **A claim about what is true gets corrected.** A published document, a caption,
  a README line, a registered claim in a spine. These assert something about the
  present tense. Annotating one leaves it false, and the annotation is not
  travelling with the sentence when someone quotes it.

The instance this came from: *"sixteen checks passed"* appeared in a published
case study and in three records of runs that genuinely printed sixteen. The case
study was corrected to "every check passed" - which is what was true and stays
true. The run records kept their number and gained a note saying the total has
since moved to fifteen.

*Cross-reference: the claim rules in a publication script - **say what held, not
how many of it there were**. Any count a tool produces is a number that moves,
and a caption cannot be patched after publishing.*

**The checklist item, stated as an item because it was advice for three rounds
and was broken in all three:**

> **Re-read the summary last, before calling the artifact finished.**

That is the specific mechanical cause rather than carelessness: a summary is
written first, the body changes underneath it, and nothing sends the writer back
to the top. It has happened to this project's proposal, its acceptance criteria,
its requirements review, and to an audit document written to record corrections.

**Nothing checks this rule. It depends on a person noticing.** That is worth
saying outright rather than leaving to inference, because a rule that sounds
like a machine is watching invites people to relax, and here nobody is.

No check can find these. The three instances caught so far were each a different
shape: a figure in a published write-up that had moved; a heading corrected in
one file while the record it was derived from kept the old wording; and two
pieces of code printing the same information, one corrected and one not. Nothing
static links any of those pairs - the connection is that two sentences mean the
same thing, and no scan reads meaning.

**All three were found by someone reading, and all three were found.** That is
the case for the habit, not an apology for the missing check: attention has a
record here, and it is the only thing that has ever caught this.

*Why a strategy and not a guardrail:* nothing mechanical knows which documents
state the same fact. The `reviewer` agent assesses it under `clarity`.

### Voice audition: read against a calibration sample (`S8`)

**Soft, assessed - not a guardrail.** Any change that writes prose a future
session will read or imitate - a skill, a command doc, a governance strategy,
a template's worked example, a devlog entry - is read against a calibration
sample before it ships: the worked-example rewrite in
`skills/compass-runtime/writing-voice-worked-example.md`, paired with the
"Never stash across a worktree hop" section of
`skills/worktree-swarm/SKILL.md`. One shows a formal artifact rewritten into
the register this strategy asks for; the other is a real incident told the
way a colleague would tell it. Together they are the standing sample - not a
one-off exhibit for the cycle that wrote them.

This audition does not lapse when that cycle ends. It applies to any future
slice that writes prose, not only the one that introduced it, and a reviewer
does not need to be reminded to run it - the pointer lives at the review
dimension itself (see below).

The test, stated the same way `writing-voice.md` states it: read it aloud -
would you say this sentence to a colleague at your desk? An "after" that only
shortens form-speak while dropping the facts the "before" carried has not
passed the audition and fails it - keeping the facts is the harder half and
the part that matters; shortening alone is easy and proves nothing.

*Why a strategy and not a guardrail:* whether a sentence sounds human is
judgement, not a fixed string. No mechanical check reliably tells a faithful
rewrite from one that quietly dropped a fact, and a check that tried and got
it wrong on its first real use would be worse than no check at all - the
findable/judgement split in `writing-voice.md`'s own tells list exists for
exactly that reason: three tells a grep can find safely, six that need a
reader. The `reviewer` agent assesses this at Verify under the `clarity`
review dimension.

*Cross-reference: cold reader (`S7`), which this specialises with a named
calibration sample; `skills/compass-runtime/writing-voice.md` for the full
tells list and the worked before/after pairs; assessed under the `clarity`
review dimension in `agents/reviewer.md` and `skills/evidence-gates/SKILL.md`.*

---

### Fresh eyes on a sweep: verification by someone who did not make the change (`S9`)

**Soft, assessed - not a guardrail.** Any sweep, rename, or cleanup that
touches many files is verified by a fresh agent - one that has not seen the
change. Given only the stated goal, that agent greps the codebase
independently and reports the residuals it finds, each with file and line.
It does not read the implementer's summary, and it does not trust it: the
summary is not the thing checked against, and it plays no part in the check.

The author of a sweep checks their own work against a mental list of what
they changed, not against the goal - so exactly the files they forgot are the
files they will not think to look for. The failure is invisible from the
inside: a summary written by the sweeper reads clean while residuals sit in
the tree. This repository has the evidence twice over - two cleanups here
leaked, and in both cases the agent that made the change reported it
complete. This is about who verifies, not about trying harder.

Verify against the primary record for the claim being made, not the nearest
document that mentions it. The primary record is the artifact that would be
wrong if the claim were false: a pull request's own file list for what a
change touched, a commit for what a commit says, the code for what the code
does. The nearest document that mentions a fact is often a summary of it,
one step removed, and a summary can be checked in good faith while the claim
it summarises has already changed meaning. ADR-013's Context once described
an install failure in the past tense, with a specific timing figure
attached - reading as a report of a real outside user, which this
repository has never had. It was verified against `.compass/work/plain-language-3-2-0/design.md`,
the document it was lifted from (written before the artifact was renamed to
`technical-design.md`), which put the same point in the present tense as a
description of what any newcomer meets - not against the primary record for
whether this happened to a real person, which does not exist, because it did
not happen. Fresh eyes stop helping the moment fresh eyes reach for the same
document the claim was drawn from.

*Why a strategy and not a guardrail:* nothing in `compass check` can confirm
that the agent running a verification grep is actually the one who did not
write the change - agent identity and prior context are not properties a
mechanical check can inspect, and a check that tried would end up trusting
the same self-report this practice exists to distrust. The `reviewer` agent
assesses this at Verify under the `governance` dimension, as a strategy
followed or departed from - never as a gate.

*Cross-reference: voice audition (`S8`) - both are about who judges, not
about trying harder. See `commands/verify.md` and
`skills/evidence-gates/SKILL.md` for the pointer at the point of use.*


### Mutation proof: a guard is accepted on a failure, not on a pass (`S10`)

**Soft, assessed - not a guardrail.** A check, guard or assertion is accepted
when it has been shown to fail. Break the thing it guards, watch it go red,
restore, watch it go green, and record the result where the change is
reviewed. A passing test proves the guard runs; it does not prove the guard
is connected to the thing it names, and the gap between those two is where
this repository has repeatedly lost coverage without noticing.

Four of the five guards corrected in 2.1.0 had passing tests throughout. The
one that settles the argument was written specifically to close this class:
it compared nothing at all at the single location it existed for, because a
filter dropped every candidate line, and setting both version banners to a
wrong value left it green. No amount of reading found that. Breaking it did,
in seconds.

The recorded result matters as much as the act. A reviewer cannot tell a
guard that was mutation-proved from one that was not, so the table - what was
broken, what failed, what passed on restore - travels with the change.

**What this actually yields, measured across three groups of work.** Seven
checks that asserted nothing, in `plain-language-3-2-0`, every test green and
every scenario looking done before proving began. **Not one was a defect in the
code. All seven were tests.**

**And they have a shape: almost every one was a presence check** - an assertion
that some required text is on the page. Presence is the easiest thing in the
world to satisfy by accident, and the two worst cases were both the same check:
one draft passed because the phrase it looked for appeared inside a
cross-reference *pointing at a rule that did not exist*, and the next draft used
a substring test that `quoted_term_exception_RENAMED` satisfied - a test written
to catch a rename, passing because of the rename.

So: **treat a presence-shaped assertion as wrong until a mutation says
otherwise.** On this evidence they usually are. Three worked examples:

- A check written *after* its defect had been fixed passed on first run. It was
  proved only by planting the original offending content back; until that was
  done, its pass established nothing at all.
- A check for build noise matched paths with `str.startswith`, so
  `tests/__pycache__/x.pyc` did not begin with `__pycache__/`. It could never
  have caught build noise in any subdirectory - the case it existed for.
- A check that an explanation appears in a module docstring was first mutated in
  the *test function's own* docstring rather than the module docstring its
  assertion reads. It reported "not proved" and was right to: the mutation had
  not touched the subject.

Three catches in nine scenarios, none of them findable by reading, all of them
in tests whose green was indistinguishable from a real one. On that evidence
this is not a formality attached to a strategy - it is the highest-yield check
in the workflow, and it is aimed at the tests rather than at the code.

**When a presence check fails, find out which thing is broken before you touch
either.** A check asserting that some required text is on the page can fail for
two unrelated reasons: the rule really is absent, or the matcher is brittle. One
of these failed against a correctly written rule because the prose was
hard-wrapped and the phrase it looked for spanned a line break, so it was not a
substring. It read as a real finding until someone looked.

That distinction is not pedantry, because **loosening a matcher to cure a false
negative is how the next false positive is born.** The sequence runs: the check
fails spuriously, someone widens the pattern to make it green, and now it passes
on anything. Several of the empty checks found in this project arrived that way.
So: establish whether the rule is missing or the match is wrong, and only then
change the one that is actually at fault.

**Changing a matcher stales every mutation proof that used it.** This is the
general form and the one that will catch someone else. A proof establishes that
a check fails when its subject is broken - but "its subject" means the text the
assertion consumes, and a matcher change redefines that. Widen a normaliser,
switch a substring test to a parsed lookup, add a case fold, and every proof
established through it was made against something the assertion no longer reads.
The checks may still be sound; the proofs no longer say so.

So a matcher change is not a local edit. **It obliges a re-proof of everything
downstream of it**, and the re-proof is cheap while working out why a check
quietly stopped catching things is not.

**Aim the mutation at the text the assertion actually reads - and remember the
assertion may normalise it.** A check that joins hard-wrapped prose before
matching is reading a string that does not exist on disk in that form. One
mutation here removed the only literal "blog post" in a file and the check still
passed, because a second copy was wrapped as "blog" / "post" across a line break
and the normaliser rejoined it. The raw file said one; the text the assertion
consumed said two. Normalising is the right fix for a brittle matcher and it
creates a place a mutation can miss, so do both: normalise the matcher, then
mutate what the normalised text contains. Three of the
empty checks found here were not weak checks at all - they were mutations that
never touched the subject. One edited a test function's own docstring while the
assertion read the module's. One renamed a dictionary key while the patterns
under it stayed in place. One removed a phrase near an identifier while a second
copy of that identifier survived elsewhere in the same passage. Each reported
"not proved" and invited the wrong conclusion, that the check was untestable.

The remedy is one cheap step: **before mutating, identify the exact text the
assertion consumes** - not the text you believe it consumes. Read the assertion,
find that string on disk, change that string.

**Assert what must hold, not the words it is currently written in.** A test
pinned to an exact layout fails the moment those words move for a good reason -
and the person who meets that failure does not usually stop to work out which
kind it is. They loosen the match until it passes, and the check ends up
asserting nothing. That is the same ending as a check that could never fail,
reached from the opposite direction.

The instance: a test matched the literal string `[RP-REQUIRE-003] requirement:`.
Its real subject was that a rule which only attaches a gate must not describe
itself as one that raises the whole process. When the output was corrected to
put the rule's meaning before its code, a true property failed because the
punctuation had moved. Rewritten to assert that the code and the kind appear on
the same line, in whatever order the line puts them, it survives the next
rewording as well.

Write the assertion so it would still be true if someone rephrased the output
without changing what it means. If it would not, it is pinned to prose rather
than to behaviour.

**Two procedural rules, learned by getting them wrong.** Clear any bytecode
cache between steps, and re-run after restoring to confirm green before
recording the proof. A proof that reads stale bytecode can report either result,
and the dangerous direction is the one that says PROVED. An unreproducible
"restore was not honoured" was observed once and never explained; by
intermittency is failure (`S5`) that stays open rather than being written off as
noise.

**The same rule for a search: a result of zero is not believed until the search
has been run against a case it must find.** A grep that reports nothing and a
grep that cannot match anything look identical, and the second is common enough
to plan for - a pattern with a typo, a path that does not exist, a flag the tool
silently ignores. Before reporting a surface clean, run the search against one
string you know is there and watch it come back. Two seconds, and it turns
"clean" from an assumption into an observation.

This is not hypothetical. Auditing this repository for a banned word,
`git grep -n -i -E '\bseam\b'` returned nothing at all, because `git grep -E`
does not honour `\b` - while the plain pattern found four uses. A scan reporting
zero had in fact read nothing. The same audit's markdown-only scan reported a
count for the repository and missed a use in a Python file, for the same reason
one level up: the search could not reach where the answer was.

**Nothing checks this, and one attempt to change that was withdrawn.** The
question "does a proof EXIST?" is mechanically answerable, unlike "is the proof
REAL?", and a check for the first was built and then removed - not because the
distinction was wrong but because declaring it required contradicting a recorded
decision that this repository holds no rules of its own. See
`declare-a-project-guardrail-or-do-not`.

Asking the existence question is worth it on its own evidence: run once by hand,
it found twenty of thirty-eight checks with no proof on record at all, and a
registered claim saying otherwise was false. No fabrication was involved. There
was nothing there.

*Why a strategy and not a guardrail:* nothing mechanical can tell
whether an author actually broke the subject, and a check that demanded proof of
a genuine mutation would be satisfied by a pasted table as easily as by a real
one - trusting the same self-report the practice exists to replace. The `reviewer` agent assesses it
at Verify under the `correctness` dimension, and a guard offered without one
is a conversation, never an automatic gate failure.

*Cross-reference: fresh eyes on a sweep (`S9`) - both answer "who or what
establishes that this is true", where `S9` answers who and this answers how.
See `commands/verify.md` and `skills/evidence-gates/SKILL.md` for the pointer
at the point of use.*

### Conventional comments: label a review comment before you write it (`S12`)

**Soft, assessed - not a guardrail.** A review comment opens with a plain-word
label naming what kind of comment it is:

- **issue** - this is wrong and blocks the merge.
- **suggestion** - a change worth making, and the author may decline it.
- **nitpick** - taste; explicitly not blocking.
- **question** - the reviewer does not know yet and is asking.
- **praise** - worth saying out loud, and worth keeping in the record.

The label goes first, so a reader can tell a blocking comment from a
non-blocking one without reading to the end of the thread.

The cost of not doing it is paid by the author, not the reviewer. "This will
crash on an empty list" and "I would have named this differently" look
identical in a list of twelve comments, and the author has to reconstruct the
reviewer's intent for each before deciding what actually stops the merge. That
reconstruction is guesswork, it happens under time pressure, and it is exactly
the thing the reviewer knew for certain and did not write down.

A label is not a substitute for the comment. **issue** still has to say what
breaks; the label tells the author how urgently to read it.

*Why a strategy and not a guardrail:* nothing mechanical can judge whether a
comment was labelled *correctly* - a blocking defect filed as a nitpick passes
any check that looks for a word at the front, and it fails worse than no label
would. The `reviewer` agent applies it and the author answering the review
assesses it, which is where the judgement belongs.

*Cross-reference: the cold reader (`S7`) - both are about the reader's cost
rather than the writer's convenience. See `agents/reviewer.md` and
`skills/receiving-code-review/SKILL.md` for the pointer at the point of use.*

### Measure before arguing: settle a disagreement with the number (`S11`)

**Soft, assessed - not a guardrail.** When a recommendation and an
instruction disagree, measure the disputed quantity and report the numbers
before defending either position. The disagreement is almost always about a
quantity somebody has guessed - how many call sites, how much output, how
often it fires - and the guess is doing the arguing.

This is written down because measuring has changed the outcome twice, in
both directions:

- **The vendored dependency.** The argument was whether bundling PyYAML was
  worth carrying a dependency. The measurement was the artifact size and a
  run on an interpreter that genuinely could not import it - which settled
  what neither position had established.
- **Two decisions on the stub removal.** The author recommended against
  deleting the retired flag aliases and against scanning fenced code blocks,
  on the grounds that both would sprawl. Counting first - 268 and 69 call
  sites, and 200 scan hits across 38 files - showed the sprawl was not there,
  and the objection dissolved. The instruction was right and the
  recommendation was wrong, and no further argument was needed once the
  numbers existed.

The second case is the one that matters: the practice is not a way to win,
it is a way to stop needing to. Restating a recommendation more forcefully
is the cheap move and the one to distrust in yourself.

Report the numbers plainly and say what they mean for the decision, including
when they undercut your own position - a measurement produced and then argued
around is worse than none, because it lends the argument false weight.

*Why a strategy and not a guardrail:* no check can tell whether a quantity
was genuinely in dispute, and demanding a measurement before every
disagreement would tax the ordinary case where somebody simply knows the
answer. The `reviewer` agent assesses it at Verify under the `correctness`
dimension.

*Cross-reference: mutation proof (`S10`) - both replace a confident assertion
with an observation. See `CLAUDE.md` and `commands/verify.md` for the pointer
at the point of use.*

**A worked instance.** A findings report from the lead listed five identifiers
the receipt printed "with nothing beside them". Rendering a receipt from a
reconstructed spine took one command. Two of the five already printed their
meaning, and the genuinely broken case - evidence ids truncated mid-token, so
they could not be matched to the entry defining them eight lines below - was
not on the list at all.

The cost of checking was one command. The cost of not checking would have been
three false statements inside an instruction that was about to shape a day's
work. That asymmetry is the whole strategy: the disputed quantity is almost
always cheaper to measure than to argue about, and the argument is usually
being carried by somebody's pattern-match.

---

## Project strategies

<!-- Add strategies specific to this project here. Add freely - strategies are
     meant to accrete. A strategy is anything directional and assessed: a
     preference, a default, a "how we tend to do X". It does NOT need to be
     checkable or blocking; if it is both of those, it is a guardrail - put it
     in guardrails.md instead.

     These are what the old constitution called "product / engineering / voice
     principles". Group them however helps. Examples of the shape:

       Product strategies
         - "When two valid features compete, we favour depth for existing
            users over breadth for prospective ones."
         - "We never dark-pattern, even when it would convert."

       Engineering strategies
         - "Modular monolith; a module does not reach into another's internals."
         - "A new third-party dependency needs a one-paragraph justification
            and a named alternative considered."

       Voice & positioning strategies
         - "Our voice is plain, exact, and warm. Never 'military-grade'."
         - "We describe what the product cannot yet do honestly, in the open."

     Curate this section - see README.md. A strategy nobody follows is noise;
     drop it. Leave the section empty rather than padding it. -->

### Voice and writing strategies

**House style, this repository.** Compass's own prose follows the cold-reader strategy, plus two
conventions this repository holds itself to.

- **No em dashes.** Where an em dash would go, write a plain hyphen with spaces
  around it. En dashes stay: they do real work in ranges like `G1-G5` and
  `2-3 streams`.
- **No agent co-author trailer**, which is the cold-reader strategy's fourth rule stated as the thing
  this repository enforces on itself rather than merely prefers.
- **Conventional commits.** A commit subject opens with a type and an optional
  scope - `fix(hooks): ...`, `docs: ...` - so a log is skimmable and a release
  can be assembled from it. This is *format*; `S7` already governs commit
  **substance**, and substance is the part that ships to adopters. A team with
  a different convention loses nothing by keeping theirs.

The first two are checked by `tests/test_house_style.py`, and all three are strategies
rather than guardrails. What separates them is *what the check protects*. The
checks in `guardrails.yml` run against an adopting project's `task.yml` and
`evidence/`, and can block a ship. `tests/test_house_style.py` is one of this
repository's own source invariants, alongside `test_release_invariants.py`. It
never runs in an adopting project and never touches a gate. A style rule is a
preference held consistently, not a must-never, so it does not become a sixth
guardrail (ADR-002).

**If you are adopting Compass:** the rules above are a worked example of the
shape a project strategy takes, not something you inherit. `/compass:init`
copies this file wholesale, so **delete this block if your team writes
differently.** The cold reader (`S7`) above it is the part that ships on, and
it governs what a commit message must *say*; how you format the subject line
is yours.

---

## How strategies are used

- **Assess** reads routing strategies (`routing-policy.md`) to pick a
  default route shape at triage.
- **The `reviewer` agent** assesses, at Verify, whether the work followed the
  applicable strategies - and reports that as *judgement*, clearly distinct
  from the evidence-backed guardrail checks. A strategy not followed is a note
  and a conversation, not an automatic gate failure.
- **`/compass:roundtable`** is where strategy-vs-strategy tensions get
  resolved when a decision sits across them.

A strategy that has hardened into a real must-never - checkable, blocking -
has outgrown this file. Promote it to `guardrails.md`. That should be rare.
