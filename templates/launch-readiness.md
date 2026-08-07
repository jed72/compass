<!--
TEMPLATE: launch-readiness.md
Produced by: the product marketer via `/compass:position`; completed at Land.
Lives at:    .compass/work/<task-slug>/launch-readiness.md
Role in the pipeline: the marketer's GATE artifact. The routing-policy
role_rule for `product-marketer` requires this file and blocks Land until
every claim in positioning.md traces to a PASSING scenario. This is where
the claims→scenario chain is proven before anything ships publicly. The
`claims` review dimension and the `verify.claims` immovable gate both read
this file.

Fill every {{PLACEHOLDER}}. A claim with no passing scenario is a no-go,
full stop - Land refuses to close on it.
-->

# Launch Readiness - {{TASK_SLUG}}

> **Author:** {{PRODUCT MARKETER NAME}} · **Date:** {{DATE}} · **Owning agent:** `marketing-lens`
> **Reads from:** positioning.md (the claims), verification-report.md (the scenario results)
> **Gates:** Land - per the routing-policy.md role_rule and the `verify.claims` immovable gate.

---

## Claims-to-scenarios traceability checklist

<!-- One row per claim from positioning.md. The scenario must not just
     EXIST - it must PASS at Verify. Pull the pass/fail from
     verification-report.md. -->

| Claim # | Claim | Backing scenario id | Scenario passed at Verify? | Cleared to ship? |
|---|---|---|---|---|
| C1 | {{from positioning.md}} | {{TRC-id}} | {{[ ] / [x] - from verification-report.md}} | {{[ ] / [x]}} |
| C2 | {{…}} | {{TRC-id}} | {{[ ]}} | {{[ ]}} |
| C3 | {{…}} | {{TRC-id}} | {{[ ]}} | {{[ ]}} |

## What is verified vs. not

### Verified - cleared to ship
- {{claim # - backed by a passing scenario}}

### Not verified - may NOT ship
<!-- A claim lands here if: it has no backing scenario, or its scenario
     failed/was not run. Each one is either cut from the launch copy, or
     the issue does not ship. -->
- {{claim # - reason: no backing scenario / scenario TRC-id failed at Verify}}

## Voice & positioning check

- [ ] Every shipping claim respects the voice and word-discipline strategies in `governance/strategies.md`.
- [ ] No claim overstates what the product can do - the honesty-policy strategy.

---

## Go / No-Go

<!-- The marketer's gate decision. NO-GO if any claim in the "not verified"
     list is still in the launch copy. -->

**Decision:** {{GO \| NO-GO}}

**Rationale:** {{e.g. "All three claims trace to passing scenarios; cleared." - or "C2 has no backing scenario; either cut C2 from launch copy or the issue does not ship."}}

**Decided by:** {{NAME}} on {{DATE}}.

<!-- If NO-GO, the issue stays open. `/compass:status` keeps flagging the
     unbacked claim; the ship command (`/compass:ship`) refuses to close. -->
