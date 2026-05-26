# Compass in five minutes

The shortest path from "what is this" to "I've shipped a task with it." Read
`docs/methodology.md` afterwards for the design; read `docs/safety-contract.md`
for the 1.0 promises. This page is just enough to get going.

---

## The mental model in five points

1. **Compass reads the task.** Before you change a file, `/compass:frame`
   triages it on four dimensions — blast radius, terrain, magnitude, intent
   & role. That part is judgement; you produce the readings.
2. **It routes by risk and uncertainty.** Given the readings,
   `compass route evaluate` applies `governance/routing-policy.yml` and
   computes the route deterministically — same readings, same route, every
   time. You don't pick a process from a menu.
3. **It creates only the artifacts that route needs.** Express collapses
   Clarify, Plan, and Distribute to nothing. Expedition expands them.
   Spike skips most of the pipeline because it ships nothing. The route
   tells the pipeline what to skip and *why it is safe to skip it* — and
   the reason is written down in `route.md`.
4. **It requires typed, traceable evidence before delivery work lands.**
   "The tests pass" is not the sentence — it is the run, recorded as a
   `test-run` evidence entry the CLI can read. Gates accept specific
   evidence types; a written note will not clear a mechanical gate.
5. **It checks the task spine in CI.** `compass ci` runs `policy lint`,
   `task lint`, and `check` for every task under `.compass/work/`. It does
   not re-run your test suite — it verifies that the *task state is
   coherent and backed by evidence*. Your project's own CI still runs
   tests, lints, builds, deploys.

The full statement of what Compass 1.0 promises (and explicitly does *not*
claim) lives in `docs/safety-contract.md`. Everything below is how it feels
in practice.

---

## The five reference routes, one line each

- **Express** — atomic, contained, mapped. Frame → Specify (1 scenario) →
  Build → Verify. One gate. Still tested before it lands.
- **Standard** — standard size, contained blast radius. The full pipeline,
  solo or pair. Two gates.
- **Expedition** — large or cross-cutting, often greenfield. Full weight.
  Distribution map, agent swarm across worktrees, all gates.
- **Hotfix** — critical and small, brownfield. Reproduce-first: a failing
  regression test *is* the spec. Expedited Build, mandatory backfill of
  `route.md` and a real scenario before close.
- **Spike** — exploration. TDD strategy suspended, hook does not block.
  **Nothing lands from a Spike**; the only exit that keeps code is
  graduating (re-framing into a real route).

Routes are *composed* from readings, not chosen from a menu — these five
are starting shapes the Needle tunes. See `docs/methodology.md` §8.

---

## A worked example — fix a typo on Express

You notice the JWT refresh error message has a typo: "invald token". You
fix the string. Here is the whole walk.

### Frame

```
/compass:frame "fix typo in the JWT refresh error message"
```

The Needle reads the four dimensions — magnitude `atomic`, blast radius
`trivial`, terrain `brownfield-mapped`, intent `engineering` — and records
them in `.compass/work/fix-jwt-typo/task.yml`:

```yaml
schema_version: "1.0"
slug: fix-jwt-typo
title: fix typo in the JWT refresh error message
readings:
  blast_radius: trivial
  terrain: brownfield-mapped
  magnitude: atomic
  intent: engineering
  role: engineer
```

Then the mechanism takes over. `/compass:frame` shells out to
`compass route evaluate --write`, which composes the route, applies the
routing guardrails, and folds the result back into `task.yml`:

```
  readings        : {"blast_radius": "trivial", "terrain": "brownfield-mapped", ...}
  candidate route : express
  FINAL ROUTE     : express
  routing guardrails fired: none
  topology        : solo
  per-phase weight:
    frame      : light
    specify    : light
    clarify    : collapsed
    plan       : collapsed
    distribute : skipped
    build      : full
    verify     : light
    land       : light
  gate set        : verify.correctness
```

`.compass/current-task` now points at `fix-jwt-typo`. `route.md` records
the readings, the route, and the de-scope reasons.

### Specify

```
/compass:specify
```

One scenario is enough:

```gherkin
Scenario: SCN-001 — the JWT refresh error message reads correctly
  Given a request with an expired JWT
  When the user attempts to refresh it with a malformed payload
  Then the response includes the message "invalid token", correctly spelled
```

`task.yml` gains the scenario; `tests:` lists the test file that will
exercise it.

### Build — red, then green, through the CLI

The pre-tool hook is watching: edit a code file with no failing test on
record and it blocks the call. So you write the test first, then run it
through `compass tdd-red`:

```
$ compass tdd-red --scenario SCN-001 -- pytest tests/auth/test_jwt_refresh.py::test_typo
  ran: pytest tests/auth/test_jwt_refresh.py::test_typo
  exit code: 1  (test correctly fails)
  wrote evidence/red.json, .red marker
```

The CLI confirmed the test actually failed before it wrote the marker.
Now you edit the production code — fix the typo, two characters — and
the hook lets the edit through because `.red` exists. Then:

```
$ compass tdd-green --scenario SCN-001 -- pytest tests/auth/test_jwt_refresh.py::test_typo
  ran: pytest tests/auth/test_jwt_refresh.py::test_typo
  exit code: 0  (test passes)
  wrote evidence/green.json, cleared .red marker
```

`task.yml` now has both records in its evidence registry, and a
`changed_files` entry tracing the production change to `SCN-001`.

### Verify

```
/compass:verify
```

The verifier runs the scenario as the acceptance test, runs the full
suite, and then calls the kit:

```
$ compass check
compass check — task 'fix-jwt-typo' (route: express)
[mode: enforced]

  G1 Tested before it lands
    PASS suite-passed: 1 test-run(s) on record, all green, bound to scenarios ['SCN-001']
  G2 Acceptance defined before it is built
    PASS scenarios-have-tests: all 1 scenario(s) list a test
    PASS scenario-has-id-and-intent: all 1 scenario(s) have an id and a linked intent
  G3 Traceability holds
    PASS changed-code-traces-to-scenario: all 1 changed file(s) trace to a scenario
    PASS claim-traces-to-scenario: no claims recorded (no marketer in play, or none yet)
  G4 Evidence, not assertion
    PASS gate-evidence-present: 1/1 pass gate(s), all backed by registry evidence
  G5 A human signs off on the irreversible
    G5 ... not applicable for these readings — skipped

compass check: PASS — all 6 check(s) passed.
```

The `verify.correctness` gate's status flips to `pass` with the
`test-run` evidence id referenced. The verifier writes
`verification-report.md`, the DoD checklist at the foot is ticked.

### Land

```
/compass:land
```

Solo route, no swarm. The commit lands on the current branch, regression
runs, the de-scope ledger has nothing owed, the task closes. Total
artifacts on disk: `route.md`, `task.yml`, `spec.feature.md`, `evidence/`,
`verification-report.md`, `devlog.md`. Anyone can pick the task up from
the artifacts alone.

---

## What to read next

- `docs/safety-contract.md` — the seven things Compass 1.0 guarantees and
  the things it explicitly does not claim.
- `docs/methodology.md` — the canonical design doc. The eight phases, the
  determinism boundary, governance as guardrails-and-strategies, the
  three layers.
- `docs/quickstart.md` — a longer walkthrough including the product
  owner's and marketer's entry points (`/compass:intent`,
  `/compass:position`) and how the same literal request routes
  differently depending on role and brief.
- `docs/install-smoke-test.md` — the manual install verification
  checklist. Run it once after `scripts/install.sh` to confirm everything
  is wired correctly.
- `docs/security.md` — what the hooks do, what the CLI depends on, and
  how to install Compass safely.
- `ci/README.md` — the CI integration contract: "run `compass ci`, honour
  the exit code." Compass CI does not replace your project CI; they run
  alongside each other.

The CLI surface, for reference:

```
compass route evaluate   apply routing-policy.yml to a task's readings -> the route
compass check            run the guardrails.yml checks against task.yml + evidence/
compass tdd-red   -- CMD run a test, assert it FAILS, record the red
compass tdd-green -- CMD run a test, assert it PASSES, clear the red marker
compass policy lint      structurally validate the governance YAML
compass task lint        structurally validate a task.yml
compass analyze          cross-artifact coherence check (orphaned scenarios,
                         route disagreements, orphan claims)
compass adr new          create a new numbered ADR in architecture/decisions/
compass rework-scan      scan tasks for rework patterns (uses signals.yml)
compass flow [--digest]  cross-task flow view; --digest writes a dated digest
compass next             surface the next action on the current task
compass backfill pay     mark a backfill as paid in a task's task.yml
compass calibration      aggregate the re-frame log — is routing well-sized?
compass ci               the full mechanical gate suite, for CI
```

The slash commands call the CLI under the hood — `/compass:frame` runs
`compass route evaluate`, `/compass:verify` runs `compass check`, the
build procedure runs `compass tdd-red`/`tdd-green` — so you rarely invoke
it directly. But it is the part that makes the framework's checks real
rather than aspirational; see `docs/methodology.md` §6.
