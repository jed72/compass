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

> **Version:** 0.3.0 · **Last amended:** {{DATE}}

---

## Default method strategies

These ship on. They are how Compass satisfies the guardrails by default -
strong, shipped-on, and you would need a deliberate, recorded reason to
deviate. They are still *strategies*: the Spike route can suspend the first
two, and a project can refine any of them.

### S1 - BDD: behaviour as Given/When/Then

Acceptance criteria are expressed as Given/When/Then scenarios, and those same
scenarios are the acceptance check at Verify. This is the shipped-on way to
satisfy **guardrail G2** ("acceptance defined before it is built"). The
scenario file is also the shared artifact every role reads - see
`docs/roles-guide.md`.

*Why a strategy and not a guardrail:* G2 - that acceptance is *stated and
checkable* - is the hard line. Given/When/Then is the *form*. The form is
strong and shipped-on; a context where it genuinely does not fit is a strategy
deviation, not a framework violation.

### S2 - TDD: red, green, refactor

Code is built by writing the failing test first, watching it fail for the
right reason, writing the minimal code to pass, then refactoring. This is the
shipped-on way to satisfy **guardrail G1** ("tested before it lands"). The
pre-tool hook enforces red-before-green by default.

TDD serves **two purposes**, not one. The first is governance: red-before-green
is the mechanism that makes G1 checkable - it ensures there is a test, and that
the test was there first. The second is **design feedback**: a hard-to-write
test is the design speaking. TDD is less about testing and more about good
design. A test that is painful to set up, or that needs elaborate mocking to
run, is not a test problem - it is a design problem. The red-green-refactor
loop is the design-feedback loop: listen to the test, and reshape the design.

*Why a strategy and not a guardrail:* G1 - that code is *tested before it
lands* - is the hard line, checked at Verify and Land. Red-before-green is the
*discipline* that gets you there reliably. It is the strong default on every
route except **Spike**, where it is suspended so exploration is not throttled.
A one-character typo fix still satisfies G1; it does not need to perform the
full ritual to do so. This is the distinction that keeps Compass from being a
sledgehammer on small changes.

### S3 - Simplest thing that satisfies the guardrail

Prefer the simplest change that clears the guardrails and the route's gates.
Not the cleverest, not the most general, not the most future-proof - the
simplest that is actually correct. Complexity is added in response to a
demonstrated need, not in anticipation of one.

### S4 - Persistence over conversation

Decisions, specs, routes, and rationale live in files (`.compass/work/<task>/`,
`governance/`, `docs/`), not only in a chat transcript. A later session - or a
different agent - should be able to resume from disk. If it is not written
down, it did not happen.

### S5 - Intermittency is failure.

A test that fails then passes without an intervening source change is not a
clean green - it is the loss of the most useful signal a test suite produces.
A rerun-to-green hides a real failure behind timing, environment state, or
shared mutable setup. It is never trusted as a pass.

When a test reruns to green: either fix the root cause or quarantine the test
in `governance/quarantine.yml` with a tracking task. Silence is not evidence
(guardrail G4). The `no-trusted-rerun` check attached to G4 reads the
`attempts` and `rerun_without_change` fields from evidence records and refuses
to clear silently when a rerun is unaccounted for.

*Cross-reference: G4 (evidence, not assertion). See also `governance/quarantine.yml`.*

---

### S6 - regression-baseline: green before, re-run after, on shared surface

**Soft, assessed - not a guardrail.** When a change touches shared or critical
surface (`blast_radius` cross-cutting or critical), the highest-value evidence
is a *baseline*: run a designated existing end-to-end / regression suite green
**before** the change, keep the change additive / guarded, and re-run it
**after**. Record both as `test-run` evidence on `verify.regression`.

This is G1's spirit applied to the *non-regression of untouched behaviour* - it
catches a high-consequence break in code you did not mean to change (the field
case: a new emission silently broke a live solve; a pre-change demo baseline
surfaced it immediately). The designated suite is a project knob
(`project.regression_baseline_suite` in `.compass/config.yml`; falls back to
`project.test_command`). Build prompts for the baseline **up front**, not as an
afterthought; `compass approach evaluate` surfaces it under
`applicable_strategies` when the readings match (`RS-ADV-001`).

It adds **no guardrail and no new gate**, and it **does not block Land** when
absent - it reuses the existing `verify.regression` gate and is assessed as
reviewer judgement (a strategy note), never a mechanical failure. The framework
grows by adding artifacts, not rules (ADR-002, ADR-006).

*Cross-reference: G1 (tested before it lands), applied to non-regression;
`verify.regression`; `routing-policy.yml` `advisory_strategies` RS-ADV-001.*

---

### S7 - cold reader: write so a stranger can follow it without asking

**Soft, assessed - not a guardrail.** Assume the reader has zero prior context.
They were not in the conversation, they have not read the review, and they
cannot ask a follow-up question. Every artifact Compass produces - a brief, a
scenario, a route, a plan, a devlog entry, a code comment, a commit message, a
pull-request body - is written to stand on its own.

This is S4 (persistence over conversation) carried one step further. S4 says
put it on disk. S7 says put enough on disk that the next reader does not need
the conversation you had while writing it.

**Context before detail.** Say what the thing is and why it matters before you
say how it works. A reader who does not yet know why should not have to reach
the last paragraph to find out.

**No dangling references.** Never write "Option 2", "Finding 1/3", "per the
review", "as discussed", or an internal review number. Each of those points at
a conversation the reader does not have, and the pointer rots the moment that
conversation ends. Name the thing instead. When you link an issue or a pull
request, say in the same sentence what it actually is - "#412, which moved rate
limiting into the gateway" - so the sentence still works when the link is dead.

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

*Cross-reference: S4 (persistence over conversation), which this extends; G3
(traceability) - a reference the reader cannot resolve is not traceability.
Assessed under the `clarity` review dimension; restated at the point of use in
`commands/land.md` (commit messages).*

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

**House style, this repository.** Compass's own prose follows S7, plus two
conventions this repository holds itself to.

- **No em dashes.** Where an em dash would go, write a plain hyphen with spaces
  around it. En dashes stay: they do real work in ranges like `G1-G5` and
  `2-3 streams`.
- **No agent co-author trailer**, which is S7's fourth rule stated as the thing
  this repository enforces on itself rather than merely prefers.

Both are checked by `tests/test_house_style.py`, and both are still strategies
rather than guardrails. What separates them is *what the check protects*. The
checks in `guardrails.yml` run against an adopting project's `task.yml` and
`evidence/`, and can block a Land. `tests/test_house_style.py` is one of this
repository's own source invariants, alongside `test_release_invariants.py`. It
never runs in an adopting project and never touches a gate. A style rule is a
preference held consistently, not a must-never, so it does not become a sixth
guardrail (ADR-002).

**If you are adopting Compass:** the two rules above are a worked example of
the shape a project strategy takes, not something you inherit. `/compass:init`
copies this file wholesale, so delete this block if your team writes
differently. S7 above it is the part that ships on.

---

## How strategies are used

- **The Needle** reads routing strategies (`routing-policy.md`) to pick a
  default route shape during Frame.
- **The `reviewer` agent** assesses, at Verify, whether the work followed the
  applicable strategies - and reports that as *judgement*, clearly distinct
  from the evidence-backed guardrail checks. A strategy not followed is a note
  and a conversation, not an automatic gate failure.
- **`/compass:roundtable`** is where strategy-vs-strategy tensions get
  resolved when a decision sits across them.

A strategy that has hardened into a real must-never - checkable, blocking -
has outgrown this file. Promote it to `guardrails.md`. That should be rare.
