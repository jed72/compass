---
name: tdd-discipline
description: The red→green→refactor cycle as Compass runs it — TDD as strategy S2 satisfying guardrail G1, how test surface scales with blast radius, what "the failing test first" means, route-awareness (suspended on Spike), and working under the pre-tool hook. Triggers during Build, on every delivery route.
---

# TDD Discipline

**TDD is strategy S2** — the red-green-refactor discipline. It is the strong,
shipped-on default *way* to satisfy **guardrail G1**: *tested before it lands*.
Keep that relationship straight, because it is the whole point.

- **G1 is the guardrail** — hard, checkable, universal. No code reaches `main`
  without a passing automated test it traces to. G1 is checked at Verify and
  Land, with evidence. It never adapts and it has no exception.
- **TDD is the strategy** — red-before-green. It is strong and shipped-on, the
  default on every *delivery* route. But it is a strategy, which means it has
  exactly one suspension: the **Spike** route turns it off (see below). The
  *outcome* (G1) is non-negotiable; the *ritual* (red-first) is the default
  method, suspendable in one defined place.

This is the distinction that keeps Compass from being a sledgehammer. A
one-character typo fix still has to satisfy G1 — it must be tested before it
lands — but a route may decide it does not need the full red-before-green ritual
to get there. What the route adapts is how much *surface* the tests cover, and
on Spike, whether the ritual runs at all. What no delivery route adapts is G1.

## Route-awareness: suspended on Spike

On the **Spike** route the TDD strategy is **suspended**. Red-before-green is
the wrong discipline for code you are writing precisely to learn something and
will likely throw away — forcing it would throttle exploration for no safety
gain.

This is safe because of the hard rule under it: **nothing lands from a Spike.**
A spike's code reaches production only by *graduating* — re-framing into a real
delivery route — and at that point G1 applies in full: graduated code is tested
before it lands, usually rewritten under TDD, sometimes kept and retro-tested.
The strategy is suspended; the guardrail is only *deferred to graduation*, never
skipped.

On every other route — Express, Standard, Expedition, Hotfix — the TDD strategy
applies. Red comes first. It is on Express, it is on Hotfix at 3am.

## The cycle

**Red → Green → Refactor**, one scenario at a time.

1. **Red.** Write a test for the next behaviour and watch it fail *for the
   right reason*. A test that fails because of a typo or a missing import is not
   a red — it has not yet described the behaviour. The failure message should
   read like the absence of the feature.
2. **Green.** Write the smallest correct code that makes the test pass. Not the
   most elegant, not the most general — the smallest *correct*. Generality is
   earned in refactor, under a green suite.
3. **Refactor.** With the suite green, improve the design — names, duplication,
   structure. The test does not change here; if it has to, you were refactoring
   behaviour, which means going back to red.

Then the next scenario. Small loops. A long gap between red and green is a sign
the step was too big.

## What "the failing test first" actually means

- The test exists and fails *before* the production code that satisfies it is
  written. Not after. Not "alongside."
- It fails because the behaviour is absent — not because it is malformed.
- It is derived from a scenario in `spec.feature.md`. The TDD strategy (S2) and
  the BDD strategy (S1) are not two systems: the BDD scenario is the
  acceptance-level test and seeds the unit-level TDD cycle. The chain is
  scenario → test → code.
- One red at a time. A wall of failing tests written up front is not TDD; it is
  a test plan. Take them one behaviour at a time so each green is a real,
  isolated step.

## Working under the pre-tool hook

`hooks/pre-tool.sh` enforces the red-before-green strategy mechanically: it will
**block a code edit that has no corresponding failing test.** It is the TDD
strategy made physical, in service of guardrail G1. It is also **route-aware**:
it reads a `.compass/work/<task>/.spike` marker file and does **not** block on a
Spike route, because the TDD strategy is suspended there.

- If the hook blocks you on a delivery route, the correct response is to go
  write the failing test, not to find a path past the hook.
- Disabling, bypassing, or tricking the hook on a route where it applies is
  breaking the TDD strategy — and on a delivery route that is how G1 gets
  quietly broken. There is no deadline and no convenience that licenses it.
- The hook checks for a *failing* test, so the natural workflow already
  satisfies it: write the red, see it fail, then edit the code.
- On a Spike the hook is silent by design — that is the strategy being
  suspended, not the hook being bypassed. The safety comes from the fact that
  nothing lands from a Spike, not from the hook.

## How test surface scales with blast radius

This is the dimension the route *does* adapt. "More surface" means more of the
behaviour's space is pinned by tests — more edges, more failure modes, more
adversarial inputs — not "tests at all," which is constant.

- **`trivial` blast radius** — the scenario and its obvious edges. Express
  territory.
- **`contained`** — the scenario, its realistic edges, the failure modes that
  matter. Standard territory.
- **`cross-cutting`** — the above plus the interaction surface: how this
  behaviour holds when adjacent features are also exercised.
- **`critical`** — the above plus adversarial and boundary inputs, the rollback
  path, and the failure modes that lose data or money. Plus whatever any
  project coverage or security guardrail floor requires.

A route may never go *below* a project coverage-floor guardrail in
`governance/guardrails.md`. It may require *more* for higher blast radius; it
may never require less.

## Working inside a worktree (swarm routes)

On a swarm you run the full cycle — including a red, failing suite — inside
your own git worktree. That isolation is the point: your red does not
destabilise a sibling. Keep every change inside your stream. If a test you need
to write reaches into another stream's surface, that is a signal for the
orchestrator, not a reason to reach across.

## Anti-patterns

- **Green-first, test-after.** Writing the code, then a test that happens to
  pass. The test never proved anything; it only documented what the code
  already did. This is the single thing the hook exists to prevent.
- **The assertion-free test.** A test that runs the code but asserts nothing,
  or asserts something trivially true. It is green theatre.
- **The test that never went red.** If you did not watch it fail, you do not
  know it can.
- **Refactoring in green's clothing.** Changing behaviour during the refactor
  step. Behaviour changes start at red.
- **Skipping refactor under deadline.** The mess compounds. Refactor is part of
  the cycle, not an optional third act — even Hotfix refactors, when the
  refactor is itself low-risk.
