---
name: tdd-discipline
description: The red→green→refactor cycle as Compass runs it - TDD as the TDD strategy satisfying the tested-before-ship guardrail, how test surface scales with risk, what "the failing test first" means, route-awareness (suspended on Spike), and working under the pre-tool hook. Triggers during Build, on every delivery approach.
---

# TDD Discipline

**TDD is the TDD strategy** - the red-green-refactor discipline. It is the strong,
shipped-on default *way* to satisfy **the tested-before-ship guardrail**: *tested before it lands*.
Keep that relationship straight, because it is the whole point.

- **Tested-before-ship is the guardrail** - hard, checkable, universal. No code reaches `main`
  without a passing automated test it traces to. It is checked at verify and
  Land, with evidence. It never adapts and it has no exception.
- **TDD is the strategy** - red-before-green. It is strong and shipped-on, the
  default on every *delivery* route. But it is a strategy, which means it has
  exactly one suspension: the **Spike** route turns it off (see below). The
  *outcome* (the tested change) is non-negotiable; the *ritual* (red-first) is the default
  method, suspendable in one defined place.

This is the distinction that keeps Compass from being a sledgehammer. A
one-character typo fix still has to satisfy the guardrail - it must be tested before it
lands - but a route may decide it does not need the full red-before-green ritual
to get there. What the route adapts is how much *surface* the tests cover, and
on a spike, whether the ritual runs at all. What no delivery approach adapts is the outcome.

## Route-awareness: suspended on Spike

On the **Spike** route the TDD strategy is **suspended**. Red-before-green is
the wrong discipline for code you are writing precisely to learn something and
will likely throw away - forcing it would throttle exploration for no safety
gain.

This is safe because of the hard rule under it: **nothing lands from a Spike.**
A spike's code reaches production only by *graduating* - re-framing into a real
delivery approach - and at that point tested-before-ship applies in full: graduated code is tested
before it lands, usually rewritten under TDD, sometimes kept and retro-tested.
The strategy is suspended; the guardrail is only *deferred to graduation*, never
skipped.

On every other route - quick-fix, Standard, initiative, Hotfix - the TDD strategy
applies. Red comes first. It is on quick-fix, it is on Hotfix at 3am.

## The cycle

**Red → Green → Refactor**, one scenario at a time.

1. **Red.** Write a test for the next behaviour and watch it fail *for the
   right reason*. A test that fails because of a typo or a missing import is not
   a red - it has not yet described the behaviour. The failure message should
   read like the absence of the feature.
2. **Green.** Write the smallest correct code that makes the test pass. Not the
   most elegant, not the most general - the smallest *correct*. Generality is
   earned in refactor, under a green suite.
3. **Refactor.** With the suite green, improve the design - names, duplication,
   structure. The test does not change here; if it has to, you were refactoring
   behaviour, which means going back to red.

Then the next scenario. Small loops. A long gap between red and green is a sign
the step was too big.

## What "the failing test first" actually means

- The test exists and fails *before* the production code that satisfies it is
  written. Not after. Not "alongside."
- It fails because the behaviour is absent - not because it is malformed.
- It is derived from a scenario in `acceptance-criteria.md`. The TDD strategy (red-before-green) and
  the BDD strategy are not two systems: the BDD scenario is the
  acceptance-level test and seeds the unit-level TDD cycle. The chain is
  scenario → test → code.
- One red at a time. A wall of failing tests written up front is not TDD; it is
  a test plan. Take them one behaviour at a time so each green is a real,
  isolated step.

## Working under the pre-tool hook

`hooks/pre-tool.sh` enforces the red-before-green strategy mechanically: it will
**block a code edit that has no corresponding failing test.** It is the TDD
strategy made physical, in service of the tested-before-ship guardrail. It is also **route-aware**:
it reads a `.compass/work/<task>/.spike` marker file and does **not** block on a
spike, because the TDD strategy is suspended there.

- If the hook blocks you on a delivery approach, the correct response is to go
  write the failing test, not to find a path past the hook.
- Disabling, bypassing, or tricking the hook on a route where it applies is
  breaking the TDD strategy - and on delivery work that is how the guardrail gets
  quietly broken. There is no deadline and no convenience that licenses it.
- The hook checks for a *failing* test, so the natural workflow already
  satisfies it: write the red, see it fail, then edit the code.
- On a Spike the hook is silent by design - that is the strategy being
  suspended, not the hook being bypassed. The safety comes from the fact that
  nothing lands from a Spike, not from the hook.

## When the change has no natural red

Some legitimate changes have no behavioural red to write, and pretending
otherwise is what produces dishonest tests. A compose `mem_limit`, a CI
`exit-code`, a Prometheus rule, a Terraform runbook, a dead-code removal: for a
refactor in particular, the *whole point* is that behaviour does not change, so
there is no new behaviour to be absent.

The failure mode this creates is well documented in the wild: authors satisfy
the hook with a red like

```
compass tdd-red --verified-by regression -- '! grep -q "_ = is_unique" solver.py'
```

which asserts that a **string appears in a file**. That is the "test the
implementation, not the behaviour" anti-pattern below, dressed as compliance.

**Declare an acceptance instead.** State what would convince a reviewer, before
the change:

```
compass acceptance start --kind validation -- promtool check rules alerts.yml
compass acceptance start --kind refactor   -- pytest -q
# ... make the change ...
compass acceptance record -- <the same command>
```

- **`validation`** - a validator must pass after the change: `docker compose
  config`, `promtool check rules`, `terraform validate`, a schema parse. There
  may be no meaningful "before" (a new rules file has none), so no baseline is
  required.
- **`refactor`** - a command that passes now must **still** pass afterwards,
  across a source tree that demonstrably changed. Behaviour preservation is the
  contract, so the baseline is required, and green-then-green with an unchanged
  tree is refused: that is two runs, not a refactor.

It writes its own `.acceptance` marker, which the hook honours. `.red` keeps
meaning exactly one thing - a real failure was observed here - and the recorded
acceptance counts as the issue's run, so there is nothing left to gain by faking
a red.

This is not an escape hatch for ordinary code. A change that *does* have a
natural behavioural red still owes one; reaching for `acceptance` because the
red is inconvenient is the same bypass as any other.

## How test surface scales with risk

This is the dimension the route *does* adapt. "More surface" means more of the
behaviour's space is pinned by tests - more edges, more failure modes, more
adversarial inputs - not "tests at all," which is constant.

- **`trivial` risk** - the scenario and its obvious edges. quick-fix
  territory.
- **`contained`** - the scenario, its realistic edges, the failure modes that
  matter. Standard territory.
- **`cross-cutting`** - the above plus the interaction surface: how this
  behaviour holds when adjacent features are also exercised.
- **`critical`** - the above plus adversarial and boundary inputs, the rollback
  path, and the failure modes that lose data or money. Plus whatever any
  project coverage or security guardrail floor requires.

A route may never go *below* a project coverage-floor guardrail in
`governance/guardrails.md`. It may require *more* for higher risk; it
may never require less.

## Working inside a worktree (swarm topologies)

On a swarm you run the full cycle - including a red, failing suite - inside
your own git worktree. That isolation is the point: your red does not
destabilise a sibling. Keep every change inside your stream. If a test you need
to write reaches into another stream's surface, that is a signal for the
orchestrator, not a reason to reach across.

## Listen to your tests

A hard-to-write test is a design smell - not a reason to write a clever test,
but a signal to change the design.

When a test requires extensive setup, elaborate mocking, or deep knowledge of
internal state to run, the code under test is telling you something: it has too
many dependencies, it couples the what to the how, or it lives in the wrong
place. The test is the first client of your code; if that client is struggling,
the next client will too.

The response to a hard-to-write test is **not** to write a harder test. It is
to ask: *what would make this test easy to write?* Then change the design to
match. This is TDD's second payoff - not just coverage, but continuous
design pressure toward simplicity.

Signals that your test is listening to a design problem:

- You cannot test the new behaviour without instantiating five other classes.
- Your test setup is longer than the assertion.
- You need to reach into private state or patch internal calls to set up the
  scenario.
- The test breaks every time you touch an unrelated part of the codebase.

Each of these is the test speaking. The right answer is refactoring the
production code so the test becomes easy, not accepting the pain.

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
  the cycle, not an optional third act - even Hotfix refactors, when the
  refactor is itself low-risk.
- **Test behaviour, not implementation.** Writing assertions that are coupled
  to how the code works internally - checking which methods were called, which
  internal variables were set, or which collaborators were invoked in which
  order. The test should observe *what* the code does from outside, not *how*
  it does it. A reliable check: **swap the implementation - does the test
  survive? It should.** If swapping a correct reimplementation breaks the test,
  the test was asserting implementation details, not behaviour. Test what the
  contract promises; let the implementation change freely underneath.

## When red does not become green

If a test is failing for a reason you did not predict, stop cycling and load
`systematic-debugging`. Repeatedly re-running a red test with a different guess
each time is not the TDD cycle - it is the reflex the cycle exists to replace.
That skill also carries the escape clause: three consecutive failed fixes means
the framing was wrong, and the next move is `/compass:frame --reframe`, not a
fourth attempt.
