# Guardrails

Guardrails are the few hard limits. They are **checkable** (cleared with
evidence, never a claim), **blocking** (a failed guardrail stops the work),
and **sticky** (slow to add, slower to remove). A guardrail always beats a
strategy.

This file ships with five **default guardrails** active. They are real,
in-force content - not a template to fill in. A project may *add* guardrails
below them; it should not weaken them. `/compass:init` copies this file into
the project so the team can extend it.

> **Version:** 0.2.0 · **Last amended:** {{DATE}}
> Bump the version and log amendments at the foot of this file.

**This document explains; `guardrails.yml` enforces.** The companion
`governance/guardrails.yml` is the machine-readable authority for *how each
guardrail is checked* - it names the mechanical check behind every guardrail,
and `compass check` runs those checks against an issue's `task.yml` and
`evidence/`. Where this prose and that file could be read to differ on a
mechanical detail, `guardrails.yml` wins. The asymmetry is deliberate:
guardrails get a `.yml` because they are *checkable*; strategies do not,
because they are *assessed* - that is the guardrail/strategy distinction made
physical.

---

## The default guardrails

These five ship on. They are the floor under every route, including the
lightest. They are deliberately few - the whole point of a guardrail is that
there are not many.

### Tested before it lands (`G1`)

No code reaches `main` unless it traces to a declared test and a green test run is on record. Compass checks that both exist and line up; it does not observe the declared test running - see `docs/safety-contract.md` for what a test-run record does and does not establish.

This is checked at Verify and again at ship time - `verification-report.md`
carries the evidence (the pasted run).

*What this is not:* tested-before-ship is not "red before green on every change." Writing the
failing test first is **TDD**, a default *strategy* (see `strategies.md`) -
the strong, shipped-on way to satisfy tested-before-ship. The spike can suspend that
strategy. The spike cannot suspend tested-before-ship: anything a spike graduates into
production must be tested before it lands.

### Acceptance defined before it is built (`G2`)

No code is written that no stated, checkable acceptance criterion describes.
The criterion exists before the code does, and the same criterion is the
acceptance check at Verify.

*What this is not:* acceptance-before-code is not "everything must be a Gherkin scenario."
Expressing acceptance as **BDD** Given/When/Then scenarios is a default
*strategy* - the shipped-on way to satisfy acceptance-before-code, and a strong one. acceptance-before-code itself is
the outcome: acceptance is stated, and it is checkable.

### Traceability holds (`G3`)

Every change keeps two chains intact, continuously - not reconstructed at the
end:

- **code → acceptance criterion → intent** - every line traces to a criterion;
  every criterion traces to a stated intent.
- **public claim → backing criterion** - every public or marketing claim
  traces to a criterion that, when checked, backs it.

The chains are the audit trail. A broken chain is a failed guardrail.

### Evidence, not assertion (`G4`)

A guardrail is cleared with artifacts and command output, never with a claim.
"The tests pass" is the pasted run, not the sentence. "It works" clears
nothing. This guardrail is *about* the others: it defines what "cleared"
means.

(Strategies, by contrast, are honestly the reviewer's judgement - and are
labelled as judgement, not dressed as evidence. That honesty is the reason
guardrails and strategies are separate things.)

### A human signs off on the irreversible (`G5`)

A change that cannot be cleanly undone - that can lose data, move money, or
breach auth or privacy - gets an explicit human checkpoint before it lands. No
route removes this. The routing policy (`routing-policy.md`) is what makes
sure such changes are *routed* to where the checkpoint happens; this guardrail
is what makes the checkpoint non-negotiable.

---

## Project guardrails

<!-- Add guardrails specific to this project here. Add slowly. A guardrail
     must be HARD (a real must-never), CHECKABLE (you can produce evidence it
     held), and BLOCKING (failing it stops the work). If it is none of those,
     it is a strategy - put it in strategies.md instead.

     Good project guardrails are usually concrete, measurable floors:
       - "Test coverage does not drop below {{N}}%."  (checkable)
       - "No secret or credential is ever committed."  (checkable)
       - "Every migration has a tested rollback."  (checkable)
       - "p95 API latency stays under {{N}}ms; a >10% regression blocks Land."
     Leave this section empty rather than padding it. Empty is a valid state. -->

_(none yet - the shipped default guardrails apply as-is)_

---

## How guardrails are enforced

- **Mechanically, by `compass check`.** Each guardrail in `guardrails.yml`
  names the check(s) that clear it; `compass check` runs them against the
  issue's `task.yml` and `evidence/` and reports pass/fail with specifics. This
  is the backbone of the Verify gate's *checkable* dimensions.
- **Mechanically, by the pre-tool hook**, for the red-before-green strategy in
  service of tested-before-ship - route-aware (it does not block on a Spike). The real tested-before-ship
  *outcome* check is `compass check` at verify and at ship time.
- **By the `verifier` and `reviewer` agents** at Verify, for the parts that
  remain judgement - `verification-report.md` records each with its evidence.
- **By triage**, for routing guardrails - see `routing-policy.md` and
  `routing-policy.yml`; `compass approach evaluate` applies them deterministically.

A guardrail with no way to produce evidence is not a guardrail yet - it is a
strategy that has not been made checkable. Concretely: if you cannot give it a
named check in `guardrails.yml`, it belongs in `strategies.md`.

**The integrity rule - a declared check must be implemented.** It is not
enough for a guardrail to *name* a check; the CLI must actually *implement*
it. A guardrail whose check has no implementation would silently become
advisory - the team would believe they had a hard, blocking guardrail when
they did not. So Compass fails closed on this, in two places: `compass policy
lint` rejects a guardrail referencing a check the CLI does not implement, and
`compass check` fails (not warns) if it meets one at run time. If you add a
project guardrail with a new check, add the check's implementation to the CLI
(`CHECK_FNS`) in the same change - or the guardrail is really a strategy.

---

## Amendment log

| Date | Change | By |
|---|---|---|
| {{DATE}} | Guardrails adopted from the shipped defaults (the five defaults). | {{NAME}} |
