---
name: evidence-gates
description: What counts as evidence versus assertion, how guardrails are cleared with evidence while strategies are assessed as judgement, how to pass a gate, and the review-dimension checklists. Triggers during Verify and any time a gate must be passed.
---

# Evidence Gates

"Evidence, not assertion" is **the evidence-not-assertion guardrail**. A guardrail is cleared with
artifacts and command output - never with a claim. "The tests pass" is not a
gate-passing statement in any route; the *paste of the test run* is. This skill
covers what counts as evidence, the checklists for each review dimension, and -
just as important - the line between what is *checked* and what is *assessed*.

## Guardrails are checked; strategies are assessed

This is the distinction the whole gate model rests on. The two kinds of
governance are verified two different ways, and conflating them is the failure
mode the evidence-not-assertion guardrail exists to prevent.

- **Guardrails are *checkable*.** They are cleared with evidence - a test ran, a
  scan passed, a human approved, the artifact exists. A guardrail clears or it
  does not, and "clears" means there is pasted output a sceptic could re-run. A
  failed guardrail is a no-pass. A guardrail beats any strategy.
- **Strategies are *assessed*.** They are the reviewer's judgement - is this the
  simplest thing that works, does it follow the team's engineering or voice
  strategies, was a departure recorded. There is no pass/fail artifact for a
  strategy; there is an honest opinion, and it must be **labelled as judgement**,
  not dressed up as evidence. A strategy not followed is a note and a
  conversation, not an automatic gate failure.

Naming them differently is what stops a judgement call being presented as a
hard gate, and stops a hard gate being waved through on an opinion. When you
write the `governance` dimension into `verification-report.md`, the guardrail
findings and the strategy assessment go in clearly separated - evidence on one
side, judgement on the other.

## Evidence vs. assertion

| Assertion (does not clear a guardrail) | Evidence (clears a guardrail) |
|---|---|
| "The tests pass." | The pasted test-runner output: counts, the green summary, the command that produced it. |
| "Coverage is fine." | The coverage report, with the number, against any project coverage-floor guardrail. |
| "It's fast enough." | The benchmark output against any project performance-budget guardrail. |
| "No regressions." | The regression run, before-and-after, showing nothing previously green is now red. |
| "It's secure." | The scan output; the dependency-CVE result where a project security guardrail requires it. |
| "Every claim is backed." | `launch-readiness.md` with each claim's backing scenario and that scenario's passing status. |

The test is simple: **could someone who does not trust you verify it from what
you pasted?** If yes, it is evidence. If they would have to take your word, it
is assertion.

## Properties of real evidence

- **Reproducible** - it includes the command, so it can be re-run.
- **Current** - it is from this change, this run, not a remembered earlier one.
- **Complete** - it shows the whole relevant output, not a hand-picked green
  line. A run with skipped tests is not a green run; show the skips.
- **Honest about gaps** - where evidence is missing or a scenario could not be
  run, that absence is itself reported. A gap surfaced is a finding; a gap
  hidden is a lie the gate cannot catch.

## Pipeline stage vocabulary - commit, acceptance, and beyond

A deployment pipeline distinguishes stages by what they test and how fast
they test it - commit, acceptance, release, production. Compass maps onto
two of those stages and explicitly stays out of the rest.

**The commit stage** is the `.red`/`tdd-green` loop - "anything that can fail
fast." `compass tdd-red` records a failing test; `compass tdd-green` records a
passing suite. These are fast, isolated, developer-feedback cycles. Evidence
here is `test-run`; it is the closest feedback loop in the pipeline. The
pre-tool hook enforces the ordering (the TDD strategy); the evidence-not-assertion guardrail enforces
that the evidence is real, not asserted.

**The acceptance/releasability stage** is `verify.correctness` - "anything
that defines releasable." This is the gate that says *yes, this behaviour is
what was specified* (acceptance-before-code in evidence form) and *yes, the tests pass* (tested-before-ship in
evidence form). `verify.correctness` accepts only `test-run` evidence - not
assertions, not opinions, not coverage numbers. An issue that clears
`verify.correctness` is an issue whose acceptance criteria were met by running
the acceptance suite. That is the definition of releasable within Compass.

**Release and Production stages** are out of scope for Compass - see
safety-contract guarantee 6: Compass is not a deployment pipeline. It has no
concept of staging environments, progressive rollout, smoke tests in
production, or canary evaluation. Those are deployment concerns; Compass ends
at ship time. The standing version of the falsification principle (the evidence-not-assertion guardrail)
is what Compass contributes: *evidence, not assertion* - the same principle
that drives continuous delivery discipline, but scoped to the development and
verification pipeline.

## How the two halves of Verify split

- The **Verifier** does the mechanical half: runs the scenarios as the
  acceptance suite, runs the TDD suite, runs regression, gathers artifacts,
  pastes raw output into `verification-report.md`. It establishes what is true.
- The **Reviewer** does the judgement half: applies the review dimensions to
  that evidence and the change, and renders pass / no-pass. It decides whether
  what is true is good enough.

Judgement rests on evidence. The Reviewer never passes a gate without the
Verifier's artifacts in hand.

## The review-dimension checklists

Which dimensions apply is set by the route (see the table in `approaches/rubric.md`).
`correctness`, `governance`, `traceability` are on every delivery approach - the
default guardrails in review form. The route and routing policy can add; they
can never remove those or an `immovable_gate`. (Spike runs none of these - it
ships nothing, so it has only its own Conclude gate.)

**correctness** - Does the change do what the scenarios describe? Is the green
genuine, or green-by-skipped-test? Do the acceptance scenarios actually exercise
the new behaviour, not just run near it?

**governance** - Two distinct checks under one dimension, and keeping them
distinct *is* the check:
- *Guardrails (checked with evidence).* Does the change clear every applicable
  guardrail - the five shipped defaults and any project guardrails? Each is cleared with the
  verifier's artifacts, never a claim. A failed guardrail is a no-pass; a
  guardrail beats any strategy. See the `governance-check` skill.
- *Strategies (assessed as judgement).* Did the work follow the applicable
  default and project strategies - and where it departed, is the departure
  recorded? This is honestly the reviewer's opinion; record it *as* judgement,
  clearly separated from the guardrail evidence. A strategy not followed is a
  note, not an automatic gate failure. On a sweep, rename, or cleanup that
  touches many files, this includes whether verification came from a fresh
  agent rather than the implementer - `governance/strategies.md` `S9` names A new or changed guard is accepted on a demonstrated failure, not a passing test - see `governance/strategies.md` `S10`.
  the practice.

**traceability** - Are both chains intact and current - code → scenario →
intent, and claim → scenario? A break is a no-pass. See the `traceability` skill.

**regression** - Does the evidence show nothing previously passing now fails?
On a swarm, this is per-stream at the checkpoint gates and *combined* at ship time -
per-stream green does not imply integrated green.

**security** - Full on initiative and Hotfix, scaled to risk on
Standard, off on quick-fix unless a `touches:` tag stapled it on. OWASP floor;
dependency-CVE scan where a project security guardrail requires it; evidence is
scan output, not "looks fine."

**clarity** - Is the code and are its tests legible to the next person - names,
structure, no surprising control flow? Off on quick-fix; deferred to the
mandatory follow-up on Hotfix. This is also where the writing-voice tells
named in `skills/compass-runtime/writing-voice.md` are judged - does the
artifact communicate a decision, or does it narrate the pipeline? Run
`scripts/voice-tells.py` over the issue's artifacts for the three tells a fixed string can find; a hit is a note and a conversation, never an automatic gate failure.
This audition is standing, not scoped to any one cycle - `governance/strategies.md`
`S8` names the calibration sample it is read against.

**claims** - When the product-marketer role is in play (and `verify.claims` is
an immovable gate, so it is always at least live for the marketer): does every
public claim trace to a *passing* scenario? Evidence is `launch-readiness.md`
with no red rows.

## Passing a gate - the procedure

1. Read `delivery-approach.md` for the gate set and the dimensions in play.
2. Verifier: run everything the dimensions require, paste raw output into
   `verification-report.md`, flag every gap.
3. Reviewer: walk each dimension's checklist against the evidence and the
   change. Record per-dimension **pass** or **no-pass with the specific reason**.
4. The gate passes only if every applicable dimension passes. One no-pass sends
   the work back - to Build, or to a re-assess. A gate is not "mostly passed."

## Architectural fitness functions and the verify.fitness gate

The `verify.fitness` gate is the route-promoted pattern for architectural
fitness functions - project-declared `command-passes` guardrails that assert
structural properties of the codebase (e.g. "modules respect the dependency
direction", "no cyclic imports in the domain layer"). Adopters declare each
fitness function as a project guardrail in `governance/guardrails.yml` with
`check: command-passes` and a `params.command:` that exits 0 on pass. The gate
is advisory by default and promoted to blocking by routing floors `RP-REQUIRE-003`
(risk ∈ {cross-cutting, critical}) and `RP-REQUIRE-004` (touches ∈
irreversible domains) - following the same promotion pattern as `verify.analyze`
(ADR-007). When no project guardrails declare `command-passes`, the gate clears
without checking anything: a project that has not yet declared any fitness functions sees no
behavioural change (ADR-006; ADR-009). Evidence type accepted: `command-output`
(the subprocess result) or `test-run` (if the fitness function is run as part
of a test suite).

See ADR-009 - *Architectural fitness functions are project guardrails, not
framework guardrails* - for the ownership-boundary decision and the full list
of alternatives considered.

## Coverage as evidence

A project coverage-floor guardrail (e.g. "line coverage does not drop below
80%") is expressed as a *project guardrail* backed by a check, not as a
claim or an assertion. The coverage report is the evidence; the number
speaks for itself.

One important caveat: **coverage is a floor, never a target**. A high coverage
number is a side effect of test discipline, not its goal. Chasing a coverage
metric - writing tests specifically to hit a number - produces tests that
cover lines without asserting anything useful.
The real goal is the design-feedback loop (the TDD strategy: "Listen to your
tests"). Treat the floor as a safety net that catches a serious regression in
test discipline; treat the design-feedback loop as the thing that builds
quality in.

## Anti-patterns

- **The assertion gate** - "all green, looks good" with nothing pasted. The most
  common way the evidence-not-assertion guardrail is quietly broken.
- **The dressed-up strategy** - presenting a strategy assessment ("this follows
  our engineering strategies") as if it were an evidence-backed guardrail
  clearance. It is judgement; label it as judgement.
- **The waved-through guardrail** - clearing a guardrail on an opinion instead
  of an artifact. The mirror of the dressed-up strategy, and worse.
- **Cherry-picked output** - pasting the one green line and not the summary that
  shows three skips.
- **Stale evidence** - output from a run before the last change.
- **The judgement-free pass** - Reviewer signing off without the Verifier's
  artifacts, on the change "looking fine."
- **Deadline as a dimension** - letting "we need to ship" stand in for a real
  check. Hotfix compresses the phases *before* Verify; it never compresses the
  gate.
