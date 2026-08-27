# How test surface scales with risk, working in a worktree, and listening to your tests

Split out of `SKILL.md`: reference for how much test to write and what the tests are telling you, plus the worktree rules that apply only on a swarm.

## How test surface scales with risk

This is the dimension the delivery approach *does* adapt. "More surface" means more of the
behaviour's space is pinned by tests - more edges, more failure modes, more
adversarial inputs - not "tests at all," which is constant.

- **`trivial` risk** - the scenario and its obvious edges. Quick-fix
  territory.
- **`contained`** - the scenario, its realistic edges, the failure modes
  that matter. Feature territory.
- **`cross-cutting`** - the above plus the interaction surface: how this
  behaviour holds when adjacent features are also exercised.
- **`critical`** - the above plus adversarial and boundary inputs, the rollback
  path, and the failure modes that lose data or money. Plus whatever any
  project coverage or security guardrail floor requires.

An approach may never go *below* a project coverage-floor guardrail in
`governance/guardrails.md`. It may require *more* for higher risk; it may
never require less.

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

