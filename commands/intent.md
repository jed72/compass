---
description: Product owner / manager entry point - capture intent as a PRD, upstream of the acceptance criteria
argument-hint: "<what you want and why>"
allowed-tools: Read, Write, Edit, Glob, Grep
---

# /compass:intent

The product owner / manager entry point. This sits **upstream of the
acceptance criteria** - a PRD is not an engineering issue and must not be
collapsed into one. The spec will later be checked back against it.

**Intent:** $ARGUMENTS

## Setup

- Adopt the product owner's vocabulary - outcomes and users, not files and
  functions.
- Load `role-translation` - the PRD is one role's perspective on the work
  the spec will serve.
- Read `governance/strategies.md` - the product owner curates the product
  strategies there, and the PRD must be consistent with them (and with the
  guardrails in `governance/guardrails.md`).
- Invoke the `product-lens` agent.

## Procedure

1. **Write the PRD.** From `templates/prd.md`, capture:
   - **Problem** - what is wrong or missing today, for whom.
   - **Outcome** - the change in the user's world this should create. Not
     the feature; the result.
   - **Success signals** - how anyone will know the outcome happened. These
     become the seeds of scenarios and, later, of the marketer's claims.
   - **Constraints** - what is fixed: deadlines, platforms, things that
     must not change.
2. **Check against governance.** Does this PRD hold the guardrails and
   respect the product strategies? If it pulls against a product strategy,
   name the tension now - do not pass it downstream silently.
3. **Write `prd.md`** into `.compass/work/<task-slug>/`.

## How this shapes the delivery approach

When triage assesses an issue with a PRD, the `product-owner` role adds two
things (see the delivery-approach rubric and the routing policy's
`role_rules`): the `prd.md` artifact, and the **intent-fidelity gate** - the
spec must be checked against `prd.md` before the design stage. Triage reads
the PRD as the *actual outcome wanted*, not just the literal request.

## Gate

`prd.md` exists with all four sections real; it is consistent with the
product strategies and guardrails in `governance/`, or the tension is named.
Next: `/compass:triage` to compute the delivery approach - the PRD is now an
input triage reads.
