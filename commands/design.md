---
description: Designer entry point - write the UI contract as scenarios that flow into Specify
argument-hint: "<surface or interaction being designed>"
allowed-tools: Read, Write, Edit, Glob, Grep
---

# /compass:design

The designer entry point. UI contracts in Compass are not mockup annotations -
they are **scenarios**, written Given/When/Then, that flow *into* Specify as
first-class spec input. The designer feeds the shared spec; they are not a
downstream consumer of it.

**Surface:** $ARGUMENTS

## Setup

- Adopt the designer's vocabulary - surfaces, states, interactions, the user's
  path through them.
- Load `role-translation` - the UI contract is the interaction lens on the
  shared spec.
- Load `bdd-specification` - the contract is written in the same
  Given/When/Then form as the rest of the spec, so it composes cleanly when it
  reaches Specify.
- Read `governance/` - any accessibility or UX floor is either a project
  guardrail (`guardrails.md`) or a strategy (`strategies.md`); the contract
  must honour the guardrails and respect the strategies.
- Read `prd.md` if one exists - the interaction serves the outcome.

## Procedure

1. **Write the UI contract as scenarios.** From `templates/ui-contract.md`,
   capture each interaction as Given/When/Then: the state the user is in, the
   action they take, the observable result. Cover the empty state, the loading
   state, the error state, and the accessibility expectations - not just the
   happy path.
2. **Honour the guardrails.** Every contract scenario must be consistent with
   the guardrails in `governance/guardrails.md` (e.g. a project accessibility
   floor). A contract that cannot meet a guardrail is a tension to name now,
   not later.
3. **Write `ui-contract.md`** into `.compass/work/<task-slug>/`.

## How this connects to the pipeline

`ui-contract.md` is an input to **Specify**. When `spec-author` runs, it folds
the UI contract scenarios into `acceptance-criteria.md` - they become acceptance
checks and seed the TDD cycle like any other scenario. Because the contract is
already Given/When/Then, nothing is lost in translation.

## Gate

`ui-contract.md` exists; every interaction is a Given/When/Then scenario
including the non-happy states; it is consistent with the guardrails in
`governance/`. Next: `/compass:frame` to route the work, then
`/compass:specify` will absorb the contract.
