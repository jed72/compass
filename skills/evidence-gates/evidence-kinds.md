# The kinds of evidence, and what each is for

Split out of `SKILL.md`: it is a vocabulary, looked up when you meet a kind you do not recognise.

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

