# The review dimensions, one checklist each

Split out of `SKILL.md` because it is reference: you read the checklist for the dimension you are applying, not all of them at once. The skill names which dimensions an approach carries; this says what each asks.

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

**Read the claim, not just the link.** `claim-traces-to-scenario` checks that a
claim points at a scenario that exists. It cannot check that what the claim says
is true, and no machine can. This is the one gate in the set whose name promises
less than a reader hears: passing means "traceable", and a reader will take it
as "verified". Every other check here means roughly what it sounds like.

A worked instance: a claim reading *"7 em dashes in publication copy, repaired
to zero"* traced correctly to its scenario and was false - the file had never
contained one, so nothing was repaired. The check passed. The reviewer is what
catches that, by reading the claim against the scenario it points at and asking
whether the sentence is *so*, not whether the id resolves.

Two questions worth asking of every claim, because both failures showed up in
one release: does it say what it counted **and what it did not**, and would it
still be true if someone quoted it on its own six months from now?

