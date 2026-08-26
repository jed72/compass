# Compass in five minutes

This walkthrough takes one small change from assessment to a reviewable,
verified result.

## Before you start

You need Claude Code and Python 3. Compass CI currently tests Python 3.11.

Install Compass inside Claude Code:

```text
/plugin marketplace add jed72/compass
/plugin install compass@compass
```

Open a project you are happy to change. Compass will add a `.compass/`
directory containing the issue record and review artefacts.

## 1. Assess the work

Start with a real, contained change:

```text
/compass:assess "Fix the misspelt invalid-token message"
```

Compass assesses four dimensions:

| Dimension | What it asks |
|---|---|
| Risk | What happens if this goes wrong? |
| Familiarity | Is the affected code understood? |
| Size | How much delivery work is involved? |
| Intent and role | What outcome is wanted, and who is asking? |

Judgement goes into the assessment. Everything after it is deterministic: the
same assessment plus the same policy produces the same approach, every time.

For a contained typo, Compass will normally choose a quick-fix-shaped approach.
It writes the result under `.compass/work/<issue>/`, and the spine records the
judgement it routed from. The part of `task.yml` that matters here:

```yaml
schema_version: "2.0"
status: active
assessment:
  risk: contained
  familiarity: brownfield-mapped
  size: atomic
  goal: delivery
  role: engineer
```

Those four dimensions are the only judgement in the routing. Everything after
them - the stages, the gates, the topology - is computed. Run
`compass approach evaluate --verbose` against that assessment and it prints:

```text
  policy          : /Users/jed/dev/compass/governance/routing-policy.yml (v2.5.0)
  assessment      : {"risk": "contained", "familiarity": "brownfield-mapped", "size": "atomic", "goal": "delivery", "role": "engineer"}
  candidate shape : quick fix  <- RP-SHAPE-003 (Small on every axis, on mapped ground.)
  FINAL APPROACH  : quick fix
  policy rules fired: none
  parallel streams: up to 1 (a ceiling - breakdown sets the topology once the distribution map exists)
  per-stage weight:
    assess     : full
    define     : light
    refine     : collapsed
    plan       : collapsed
    breakdown  : skipped
    implement  : full
    verify     : light
    ship       : light
  gate set        : verify.correctness, verify.governance, verify.traceability
```

Generate the issue dashboard:

```bash
compass issue dashboard --issue <issue>
```

Then open `.compass/work/<issue>/README.md`. It tells you:

- the proposed approach;
- what needs human approval;
- which artefacts will be produced;
- what Compass deliberately omitted, and why; and
- the next action.

Approve or correct the assessment before continuing. A good route depends on a
good assessment. Regenerate the dashboard after a stage changes the issue.

## 2. Define acceptance

Run:

```text
/compass:define
```

For this change, one Gherkin scenario is enough:

```gherkin
Scenario: The invalid-token message is spelt correctly
  Given a request contains an invalid token
  When authentication rejects the request
  Then the response says "invalid token"
```

The scenario is the shared specification. It tells the engineer what to test,
QA what to verify, and reviewers what the change is meant to achieve.

## 3. Plan only what is useful

Run:

```text
/compass:plan
```

On a quick fix, planning may collapse to a short note naming the file and test
surface. Larger or riskier work can produce an intent document, high-level design,
low-level design, ADRs, delivery plan or test strategy.

Those documents are selected because they help this issue. They are not a
fixed checklist.

## 4. Implement with evidence

Run:

```text
/compass:implement
```

Compass uses TDD by default where it adds value:

1. record a failing test with `compass tdd-red`;
2. make the smallest useful change; and
3. record the passing test with `compass tdd-green`.

The commands run the test and write evidence beneath the issue directory.
Compass does not treat “the tests pass” in chat as evidence.

## 5. Verify and ship

Run:

```text
/compass:verify
```

Verify checks the acceptance criteria, test evidence, traceability and any
route-specific gates. Read `verification-report.md` and resolve anything still
open.

Then run:

```text
/compass:ship
```

Compass checks the issue record again before completing the delivery workflow.
Your normal CI still owns tests, linting, security scanning, builds and
deployment checks.

## What you should now have

A small issue typically leaves:

```text
.compass/work/<issue>/
├── README.md
├── task.yml
├── delivery-approach.md
├── acceptance-criteria.md
├── verification-report.md
├── devlog.md
└── evidence/
```

The exact pack varies with the work. Another person, session or compatible
runtime should be able to resume from these files without the original chat.

## The mental model in five points

1. **Assess the work, do not choose a process.** Four dimensions are judgement;
   the approach is computed from them.
2. **The approach decides the ceremony.** Which stages run at what weight,
   which artefacts are earned, which gates apply.
3. **Guardrails are hard; strategies are defaults.** An approach reduces
   ceremony around a guardrail and never routes through one.
4. **Evidence, not assertion.** A gate clears with a record a reader can open.
5. **If it is not on disk, it did not happen.** The spine and its artefacts
   outlive the conversation.

## The CLI underneath

Everything above runs through slash commands. The mechanism they call:

```text
compass init               make this directory a Compass project - create .compass/
compass approach evaluate  the assessment -> the delivery approach, deterministically
compass bdd extract        acceptance criteria -> a runnable .feature
compass bdd verify         record which scenarios the runner actually ran
compass check              run the guardrail checks against the spine and evidence
compass analyze            where an issue's artifacts disagree with each other
compass retro              is triage systematically over- or under-sizing the process?
compass ci                 the full mechanical gate suite, for continuous integration
compass tdd-red            run a test, assert it FAILS, record the red
compass tdd-green          run a test, assert it PASSES, record the green
compass policy lint        structurally validate the governance YAML
compass plan lint          scan a technical design for placeholder phrases
compass intent ingest      read a brief that already exists, by path or https URL
compass issue lint         structurally validate an issue spine
compass issue receipt      one screen: assessment, approach, gates, evidence
compass issue dashboard    the per-issue review page
compass issue artifact     set a document's status in the review pack
compass issue set-status   queued | active | parked | landed | abandoned
compass acceptance start   open an honest record where there is no natural red
compass acceptance record  close it with what was observed
compass adr new            create the next numbered decision record
compass rework-scan        add-then-delete patterns across issues
compass flow               blockers, owed follow-ups, the periodic digest
compass next               which stage this issue reached, and what comes next
compass follow-up resolve  settle an owed follow-up
compass ship-commit        commit exactly the files the issue recorded
compass gate pass          mark a gate passed, validating the evidence type
compass scenario add       add a scenario to the spine
compass changed-file add   trace a changed file to the scenario that asked for it
compass evidence add       append a typed evidence record
compass migrate            bring older issue directories up to the current schema
compass terminology        what a term means here, from the frozen vocabulary
```

Every verb describes itself - `compass <verb> --help` says what it does and
what the result means, so this list is a map rather than a manual.

## Next

- Read the [methodology](methodology.md) to understand adaptive routing.
- Read the [roles guide](roles-guide.md) if product, design, marketing or QA
  will contribute.
- Read the [safety contract](safety-contract.md) before relying on Compass
  gates.
- Run the [install smoke test](install-smoke-test.md) if commands or hooks do
  not behave as expected.
