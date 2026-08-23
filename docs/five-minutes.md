# Compass in five minutes

The shortest path from "what is this" to "I've shipped an issue with it." This
page is just enough to get going. Read `docs/methodology.md` afterwards for the
design, and `docs/safety-contract.md` for what Compass 1.0 does and does not
promise.

To run the commands below you need Compass installed. The quickest way, inside
Claude Code, is `/plugin marketplace add jed72/compass` then
`/plugin install compass@compass`. Compass needs Python 3; the YAML parser it
uses travels inside the plugin, so there is nothing else to install.
`docs/quickstart.md` §1 covers that and the install-from-source alternative.

---

## The mental model in five points

1. **Compass reads the issue.** Before you change a file, `/compass:triage`
   triages it on four dimensions - risk, familiarity, size, intent
   & role. That part is judgement; you produce the assessment.
2. **It routes by risk and uncertainty.** Given the assessment,
   `compass approach evaluate` applies `governance/routing-policy.yml` and
   computes the delivery approach deterministically - same assessment, same route, every
   time. You don't pick a process from a menu.
3. **It creates only the artifacts that route needs.** quick fix collapses
   the requirements review, the design stage, and the breakdown to
   nothing. An initiative expands them.
   Spike skips most of the pipeline because it ships nothing. The route
   tells the pipeline what to skip and *why it is safe to skip it* - and
   the reason is written down in `delivery-approach.md`.
4. **It requires typed, traceable evidence before delivery work lands.**
   "The tests pass" is not the sentence - it is the run, recorded as a
   `test-run` evidence entry the CLI can read. Gates accept specific
   evidence types; a written note will not clear a mechanical gate.
5. **It checks the issue spine in CI.** `compass ci` runs `policy lint`,
   `issue lint`, and `check` for every issue under `.compass/work/`. It does
   not re-run your test suite - it verifies that the *issue state is
   coherent and backed by evidence*. Your project's own CI still runs
   tests, lints, builds, deploys.

The full statement of what Compass 1.0 promises (and explicitly does *not*
claim) lives in `docs/safety-contract.md`. Everything below is how it feels
in practice.

---

## The five reference shapes, one line each

- **Quick fix** - atomic, contained, mapped. triage → define (1 scenario) →
  implement → verify. One gate. Still tested before it ships.
- **Feature** - standard size, contained risk. The full pipeline,
  solo or pair. Two gates.
- **Initiative** - large or cross-cutting, often greenfield. Full weight.
  Distribution map, agent swarm across worktrees, all gates.
- **Hotfix** - critical and small, brownfield. Reproduce-first: a failing
  regression test *is* the spec. Implementation is expedited, and two
  things are owed before the issue closes: the approach record completed
  properly (not the urgent stub), and the reproduction test promoted into
  a real Given/When/Then scenario.
- **Spike** - exploration. TDD strategy suspended, hook does not block.
  **Nothing ships from a spike**; the only exit that keeps code is
  graduating - re-triaging into a real delivery approach.

Approaches are *composed* from assessment, not chosen from a menu - these five
are starting shapes triage tunes. See `docs/methodology.md` §8.

---

## A worked example - fix a typo on quick fix

You notice the JWT refresh error message has a typo: "invald token". You
fix the string. Here is the whole walk.

### Triage

```
/compass:triage "fix typo in the JWT refresh error message"
```

Triage reads the four dimensions - size `atomic`, risk
`trivial`, familiarity `brownfield-mapped`, intent `delivery` - and records
them in `.compass/work/fix-jwt-typo/task.yml`:

<!-- vocabulary-scan: allow - the spine's own field names; machine state, which the ban exempts -->
```yaml
schema_version: "2.0"
task: fix-jwt-typo
assessment:
  risk: trivial
  familiarity: brownfield-mapped
  size: atomic
  goal: delivery
  role: engineer
```

Then the mechanism takes over. `/compass:triage` shells out to
`compass approach evaluate --write`, which composes the delivery approach, applies the
routing guardrails, and folds the result back into `task.yml`:

```
  policy          : governance/routing-policy.yml (v2.1.1)
  assessment      : {"risk": "trivial", "familiarity": "brownfield-mapped", ...}
  candidate shape : quick fix  <- RP-SHAPE-003 (Small on every axis, on mapped ground.)
  FINAL APPROACH  : quick fix
  policy rules fired: none
  topology        : solo
  per-stage weight:
    triage     : full
    define     : light
    refine     : collapsed
    design     : collapsed
    breakdown  : skipped
    implement  : full
    verify     : light
    ship       : light
  gate set        : verify.correctness, verify.governance, verify.traceability
```

Triage is `full` on every delivery approach - it is the one stage that never collapses.

`.compass/current-task` now points at `fix-jwt-typo`. `delivery-approach.md` records
the assessment, the delivery approach, and the de-scope reasons.

### Define the acceptance criteria

```
/compass:define
```

One scenario is enough:

```gherkin
Scenario: SCN-001 - the JWT refresh error message reads correctly
  Given a request with an expired JWT
  When the user attempts to refresh it with a malformed payload
  Then the response includes the message "invalid token", correctly spelled
```

`task.yml` gains the scenario; `tests:` lists the test file that will
exercise it.

### Build - red, then green, through the CLI

The pre-tool hook is watching: edit a code file with no failing test on
record and it blocks the call. So you write the test first, then run it
through `compass tdd-red`:

```
$ compass tdd-red --scenario SCN-001 -- pytest tests/auth/test_jwt_refresh.py::test_typo
  ran: pytest tests/auth/test_jwt_refresh.py::test_typo
  exit code: 1  (test correctly fails)
  wrote evidence/red-SCN-001.json, .red marker
```

The CLI confirmed the test actually failed before it wrote the marker.
Now you edit the production code - fix the typo, two characters - and
the hook lets the edit through because `.red` exists. Then:

```
$ compass tdd-green --scenario SCN-001 -- pytest tests/auth/test_jwt_refresh.py::test_typo
  ran: pytest tests/auth/test_jwt_refresh.py::test_typo
  exit code: 0  (test passes)
  wrote evidence/green-SCN-001.json, cleared .red marker
```

`task.yml` now has both records in its evidence registry, and a
`changed_files` entry tracing the production change to `SCN-001`.

### Verify

```
/compass:verify
```

The verifier runs the scenario as the acceptance test, runs the full
suite, and then calls the kit:

This is the real output, from the shipped `examples/quick-fix-typo/` issue -
run `compass check` in that directory to reproduce it verbatim:

<!-- vocabulary-scan: allow - verbatim output; editing a transcript would make it untrue, and the guardrail codes come from guardrails.yml -->
```
$ compass check
compass check - issue 'fix-timeout-error-message' (approach: quick-fix)
[mode: enforced]

  G1 Tested before it lands
    PASS scenarios-have-tests: all 1 scenario(s) list a test
    PASS declared-tests-resolve: issue is landed - declared test ids are a historical record
    PASS suite-passed: 1 test-run(s) on record, all green, bound to scenarios ['SCN-001']
    PASS changed-code-traces-to-scenario: all 1 changed file(s) trace to a scenario, but 1 no longer exist (src/api/upload.py) - reported only, because the issue is landed - historical record
    PASS scenarios-are-executable: no BDD runner wired (project.bdd_runner is unset) - nothing to verify; see examples/bdd-adapters/ to opt in

  G2 Acceptance defined before it is built
    PASS scenario-has-id-and-intent: all 1 scenario(s) have an id and a linked intent

  G3 Traceability holds
    PASS changed-code-traces-to-scenario: all 1 changed file(s) trace to a scenario, but 1 no longer exist (src/api/upload.py) - reported only, because the issue is landed - historical record
    PASS scenario-has-id-and-intent: all 1 scenario(s) have an id and a linked intent
    PASS claim-traces-to-scenario: no claims recorded (no marketer in play, or none yet)

  G4 Evidence, not assertion
    PASS gate-evidence-present: 3/3 pass gate(s), all backed by registry evidence of accepted type
    PASS dod-evidence-typed: DoD section is empty or absent - nothing to evidence
    PASS coherence-check-passes: verify.analyze not in gate set - coherence check not required
    PASS no-trusted-rerun: no trusted-rerun violations
    PASS command-passes: verify.fitness: this project declares no guardrail that runs a command, so there was nothing to check and this passed without checking anything. To add fitness functions, declare a project guardrail with `check: command-passes`

  G5 A human signs off on the irreversible: not applicable for this assessment - skipped
  outstanding follow-ups
    PASS backfills-paid: no outstanding follow-ups

------------------------------------------------------------
compass check: PASS - all 15 check(s) passed.
```

Several checks appear under more than one guardrail - one check can serve
two guardrails, and the count is of check *runs*, not distinct checks.
Each of the three gates flips to `pass` with its evidence id referenced.
The verifier writes `verification-report.md`, and the DoD checklist at the
foot is ticked.

### Ship

```
/compass:ship
```

Solo topology, no swarm. The commit lands on the current branch, regression
runs, the de-scope ledger has nothing owed, the issue closes. Total
artifacts on disk: `delivery-approach.md`, `task.yml`, `acceptance-criteria.md`, `evidence/`,
`verification-report.md`, `devlog.md`. Anyone can pick the issue up from
the artifacts alone.

---

## What to read next

- `docs/safety-contract.md` - the seven things Compass 1.0 guarantees and
  the things it explicitly does not claim.
- `docs/methodology.md` - the canonical design doc. The eight phases, the
  determinism boundary, governance as guardrails-and-strategies, the
  three layers.
- `docs/quickstart.md` - a longer walkthrough including the product
  owner's and marketer's entry points (`/compass:intent`,
  `/compass:position`) and how the same literal request routes
  differently depending on role and brief.
- `docs/install-smoke-test.md` - the manual install verification
  checklist. Run it once after `scripts/install.sh` to confirm everything
  is wired correctly.
- `docs/security.md` - what the hooks do, what the CLI depends on, and
  how to install Compass safely.
- `ci/README.md` - the CI integration contract: "run `compass ci`, honour
  the exit code." Compass CI does not replace your project CI; they run
  alongside each other.

The CLI surface, for reference. `compass` is the executable at `cli/compass`
in the Compass checkout - the examples below write it bare, which assumes
you have put that directory on your `PATH`. Otherwise call it by path
(`/path/to/compass/cli/compass check`); the slash commands resolve it for
themselves either way.

```
compass approach evaluate   apply routing-policy.yml to an issue's assessment -> the approach
compass check            run the guardrails.yml checks against the spine + evidence/
compass bdd extract     extract an issue's acceptance-criteria.md into a runnable .feature
compass tdd-red   -- CMD run a test, assert it FAILS, record the red
compass tdd-green -- CMD run a test, assert it PASSES, clear the red marker
compass policy lint      structurally validate the governance YAML
compass issue lint        structurally validate a task.yml
compass design lint        scan a design.md for placeholder phrases - advisory
compass issue receipt     render a one-screen receipt for a landed issue -
                         assessment → approach → typed evidence → gate verdicts
compass issue dashboard   render the per-issue review README - the decision,
                         the pack, and what was deliberately omitted
compass issue artifact   set a document's status in the pack - omitting one
                         needs --reason, so an omission is never a gap
compass issue set-status  record an issue as queued | active | parked | landed |
                         abandoned - the mutator for the lifecycle field
compass acceptance start declare the acceptance for a change with no natural
                         red - a validator (--kind validation) or a green suite
                         to preserve (--kind refactor); record closes it
compass gate pass        flip a gate to pass; validates evidence type at write time
compass scenario add     append a scenario to task.yml (schema-owning mutator, R9)
compass changed-file add trace a changed production file to a scenario
compass evidence add     append a typed evidence entry to the registry
compass analyze          cross-artifact coherence check (orphaned scenarios,
                         route disagreements, orphan claims)
compass adr new          create a new numbered ADR in architecture/decisions/
compass rework-scan      scan issues for rework patterns (uses signals.yml)
compass flow [--digest]  cross-issue flow view; --digest writes a dated digest
compass next             surface the next action on the current issue
compass follow-up resolve  mark an outstanding follow-up resolved in task.yml
compass ship-commit -m   commit staged artifacts robustly; verifies HEAD advanced
compass retro      aggregate the re-assessment log - is the sizing right?
compass migrate          migrate a 1.x issue tree to schema 2.0 (dry-run; --apply)
compass terminology      render the v2 vocabulary - one term or the whole glossary
compass ci               the full mechanical gate suite, for CI
```

The slash commands call the CLI under the hood - `/compass:triage` runs
`compass approach evaluate`, `/compass:verify` runs `compass check`, the
build procedure runs `compass tdd-red`/`tdd-green` - so you rarely invoke
it directly. But it is the part that makes the framework's checks real
rather than aspirational; see `docs/methodology.md` §6.
