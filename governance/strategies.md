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

> **Version:** 0.4.0 · **Last amended:** 2026-08-13

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

It adds **no guardrail and no new gate**, and it **does not block Land** when
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
saying "the G5 guard kicked in" to someone who has never read
`guardrails.yml` communicates nothing.

`compass check` is the shipped example: it prints `G5 A human signs off on
the irreversible`, the identifier and its meaning together. Match it rather
than inventing a second convention. Never solve this by dropping the code -
the codes carry the traceability, and the machine checks read them.

**Correct a retired name in a comment you were touching anyway.** The
vocabulary scan does not read comments or docstrings - the parser discards
them, so nothing there reaches a user (`PX-1` in `terminology.yml`). But the
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
`commands/land.md` (commit messages).*

---

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
repository has never had. It was verified against `design.md`, the document
it was lifted from, which put the same point in the present tense as a
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

*Why a strategy and not a guardrail:* nothing mechanical can tell whether an
author actually broke the subject, and a check that demanded proof would be
satisfied by a pasted table as easily as by a real one - trusting the same
self-report the practice exists to replace. The `reviewer` agent assesses it
at Verify under the `correctness` dimension, and a guard offered without one
is a conversation, never an automatic gate failure.

*Cross-reference: fresh eyes on a sweep (`S9`) - both answer "who or what
establishes that this is true", where S9 answers who and this answers how.
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
`evidence/`, and can block a Land. `tests/test_house_style.py` is one of this
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

- **Triage** reads routing strategies (`routing-policy.md`) to pick a
  default route shape at triage.
- **The `reviewer` agent** assesses, at Verify, whether the work followed the
  applicable strategies - and reports that as *judgement*, clearly distinct
  from the evidence-backed guardrail checks. A strategy not followed is a note
  and a conversation, not an automatic gate failure.
- **`/compass:roundtable`** is where strategy-vs-strategy tensions get
  resolved when a decision sits across them.

A strategy that has hardened into a real must-never - checkable, blocking -
has outgrown this file. Promote it to `guardrails.md`. That should be rare.
