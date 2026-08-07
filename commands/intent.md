---
description: Product owner / manager entry point - capture intent as a brief, upstream of the spec
argument-hint: "<what you want and why>"
allowed-tools: Read, Write, Edit, Glob, Grep
---

# /compass:intent

The product owner / manager entry point. This sits **upstream of Specify** - a
brief is not an engineering task and must not be collapsed into one. The spec
will later be checked back against it.

**Intent:** $ARGUMENTS

## Setup

- Adopt the product owner's vocabulary - outcomes and users, not files and
  functions.
- Load `role-translation` - the brief is one lens on the work the spec will
  serve.
- Read `governance/strategies.md` - the product owner curates the product
  strategies there, and the brief must be consistent with them (and with the
  guardrails in `governance/guardrails.md`).
- Invoke the `product-lens` agent.

## Procedure

1. **Write the brief.** From `templates/prd.md`, capture:
   - **Problem** - what is wrong or missing today, for whom.
   - **Outcome** - the change in the user's world this should create. Not the
     feature; the result.
   - **Success signals** - how anyone will know the outcome happened. These
     become the seeds of scenarios and, later, of the marketer's claims.
   - **Constraints** - what is fixed: deadlines, platforms, things that must
     not change.
2. **Check against governance.** Does this brief hold the guardrails and
   respect the product strategies? If it pulls against a product strategy,
   name the tension now - do not pass it downstream silently.
3. **Write `prd.md`** into `.compass/work/<task-slug>/`.

## How this shapes the route

When the Needle frames a task with a brief, the `product-owner` reading adds
two things (see `routes/router.md` and the routing policy's `role_rules`):
the `prd.md` artifact, and the **intent-fidelity gate** - the spec must be
checked against `prd.md` before Plan. Frame reads the brief as the *actual
outcome wanted*, not just the literal request.

## Gate

`prd.md` exists with all four sections real; it is consistent with the
product strategies and guardrails in `governance/`, or the tension is named.
Next: `/compass:frame` to route the work - the brief is now an input the Needle
reads.
