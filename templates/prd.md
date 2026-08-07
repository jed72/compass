<!--
TEMPLATE: prd.md
Produced by: the product owner / manager via `/compass:intent`.
Lives at:    .compass/work/<task-slug>/prd.md
Role in the pipeline: the intent artifact. It sits UPSTREAM of the spec -
the BDD scenarios in acceptance-criteria.md are checked back against this brief
for intent fidelity before Plan (the product-owner role_rule in
governance/routing-policy.md). The Needle reads it during Frame: intent is
the outcome wanted, not just the literal request.

Fill every {{PLACEHOLDER}}. Keep it in the product owner's language, not
engineering's - do not pre-solve the problem here.
-->

# Brief - {{TASK_SLUG}}

> **Author:** {{PRODUCT OWNER / MANAGER NAME}} · **Date:** {{DATE}}
> **Governance owner check:** this brief should be consistent with the
> product strategies in `governance/strategies.md`.

---

## Problem

<!-- What is wrong, missing, or possible today? Who feels it, and how?
     State the problem, not a feature. "Finance cannot self-serve their
     numbers" - not "add a CSV export button". -->

{{PROBLEM STATEMENT}}

## Desired outcome

<!-- The world after this is done, described as an outcome a user
     experiences - not a UI, not an implementation. One or two sentences. -->

{{DESIRED OUTCOME}}

## Success signals

<!-- How will we know the outcome was actually achieved? Each signal should
     be observable. These seed the success metrics in design.md and the
     acceptance perspective on acceptance-criteria.md. -->

- {{SIGNAL 1 - e.g. "Finance pulls month-end numbers without filing a data request."}}
- {{SIGNAL 2}}
- {{SIGNAL 3}}

## Constraints

<!-- Hard boundaries the solution must respect: deadlines, platforms,
     budgets, compliance, things that must not change. -->

- {{CONSTRAINT 1}}
- {{CONSTRAINT 2}}

## Non-goals

<!-- Explicitly out of scope. Naming non-goals is what stops scope creep and
     what lets triage size the work honestly. "We are NOT building a
     full reporting suite." -->

- {{NON-GOAL 1}}
- {{NON-GOAL 2}}

## Internal FAQ

<!-- The questions a sharp colleague would ask before agreeing to build this.
     Adapted from the Amazon working-backwards PRFAQ. Answer them honestly -
     a weak answer here is cheaper to find now than in Build. The Needle reads
     "why now" for urgency and "what could make this fail" for risk. -->

**Why now?**
{{Why is this worth doing this cycle and not next? What changed, or what
breaks if it waits?}}

**What is in v1, and what is explicitly later?**
{{The MVP cut. Sharper than the non-goals list - non-goals are never; this is
the v1/later line. Feeds triage's size assessment.}}

**How will we know it worked?**
{{Restate the success signals above as the one or two that actually decide
whether this was worth it. If they are not measurable, say how they will be
judged.}}

**What could make this fail?**
{{A short pre-mortem. The risks - product, technical, adoption. Each risk the
team accepts should be visible here, not discovered later.}}

## Affected roles

<!-- Which of the five roles this brief pulls into the pipeline. The Needle
     uses this when scoring the intent & role dimension. -->

- {{e.g. designer - there is a new user-facing surface; expect a ui-contract.md}}
- {{e.g. product-marketer - this is launch-visible; expect positioning.md}}

---

## Intent-fidelity check (filled at the pre-Plan gate)

<!-- The product-owner role_rule blocks Plan until the spec is checked
     against this brief. Record the check here. -->

- [ ] Every success signal above maps to at least one scenario in `acceptance-criteria.md`.
- [ ] No scenario contradicts a constraint, pursues a non-goal, or runs against a product strategy.
- [ ] Checked by: {{NAME}} on {{DATE}}.
