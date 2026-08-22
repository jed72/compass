# Compass - Worked Examples

Five completed Compass issues, one per reference shape. Each is a real-shaped
`.compass/work/<task-slug>/` directory exactly as it would look *after the issue
finished* - the artifacts, the evidence, the gates, all filled in.

The framework's docs tell you what Compass *is*. These show you what it *looks
like done*. Read one and you have seen a route end to end; read all five and
you have seen the whole adaptive range - from a one-string fix that stays out
of its own way, to a swarmed subsystem that runs every gate.

Each example is self-contained and verifiable. From inside any example's issue
directory:

```
compass issue lint --file task.yml         # the spine is well-formed
compass approach evaluate --issue <slug>   # the assessment composes to the claimed shape
compass check --issue <slug>                 # the guardrail checks pass (see the Spike note)
```

---

## The five examples

### 1. `quick-fix-typo/` - the quick fix

**Issue:** the upload timeout error says "try again later" when it should name
the file-size limit that is the actual cause.

**What it demonstrates:** the *lightness*. the requirements review, design, and breakdown all
collapse - and `delivery-approach.md` §5 carries an explicit "safe to skip because…" line
for each. One scenario is the whole spec. Verify is a short note, not a full
report. The artifact set is four files and an `evidence/` pair, and that is
*correct* - quick fix adapts test surface, never test existence, so `red.json`
and `green.json` are still there. The `task.yml` is the new 1.0 shape: a
top-level `evidence:` registry of two typed entries (a `test-run` and an
`artifact`), and each `pass` gate references them by id - `verify.correctness`
points at the `test-run`, governance and traceability at the `artifact`.

**One-line lesson:** when the change is small on every axis, the process gets
out of the way - but the de-scopes are written down, not assumed.

### 2. `feature-api-change/` - the feature approach

**Issue:** add per-client rate limiting to the public `/search` endpoint after
one client's bulk job degraded latency for everyone.

**What it demonstrates:** the default working shape at full artifact weight -
`requirements-review.md` with the Definition of Ready ticked, a real `design.md` with
two ADR-style design decisions, a full `verification-report.md` with the
Definition of Done and pasted test output. It also shows breakdown being
*skipped for a reason* (the work units share code surface, so a swarm would
manufacture a merge conflict, not parallelism).

**One-line lesson:** the normal case - every phase runs, the two checklist
gates are real, and "solo" is a justified finding, not a default.

### 3. `hotfix-regression/` - the hotfix

**Issue:** `/search` returns a 500 for any request with an empty `filter` object -
a live crash on a new mobile build.

**What it demonstrates:** reproduce-first (the failing regression test *is* the
spec - `evidence/red.json` reproduces the crash before any fix), the compressed
front of the pipeline, the *uncompressed* Verify gate, and the **mandatory
follow-up**. `task.yml`'s `follow-ups:` lists three outstanding items; `delivery-approach.md` §6 and
the `devlog.md` ship entry show all three **paid** - which is what makes this a
closed issue and not an open one. `compass check` enforces it.

**One-line lesson:** speed is borrowed from the front of the pipeline and paid
back at the end - a Hotfix with an outstanding follow-up is an open issue, full stop.

### 4. `initiative-new-subsystem/` - the initiative

**Issue:** build the in-app notifications subsystem - durable delivery,
per-category preferences, a security category that mute cannot suppress.

**What it demonstrates:** full weight, every gate, a swarm across worktrees -
and two routing guardrails *firing visibly*. The assessment include
`labels: [migrations]`, so **RP-FLOOR-003** raises the candidate from Standard
to initiative ("domain risk overrides size") - you can see it in
`task.yml`'s `fired_guardrails` and in `delivery-approach.md` §3. A product owner is
involved, so **RP-ROLE-002** requires `prd.md` and blocks Plan until the spec
is checked against it for intent fidelity. The `migrations` tag also makes
guardrail `G5` apply - `task.yml`'s `evidence:` registry carries a typed
`human-approval` entry (approver, role, scope, decision, timestamp,
conditions) for the irreversible schema change, and the JSON record it points
at lives under `evidence/approval-migration-0042.json`. Full set: `prd.md`
with an Internal FAQ, `distribution-map.md` with the two-stream swarm
topology, per-stream *and* combined verification.

**One-line lesson:** the router is governed too - a domain tag can overrule a
size reading, and the heavy route is heavy on purpose.

### 5. `spike-technical-unknown/` - the spike

**Issue:** is `weasyprint` a viable PDF engine for our report layouts, or do we
need a heavier tool? A timeboxed investigation.

**What it demonstrates:** the escape hatch. `intent: exploration` selects
Spike; `scenarios:` and `changed_files:` are empty *on purpose* - a spike has
no acceptance criteria and lands no production code. The `.spike` marker file
suspends the TDD strategy (the hook does not block edits). There is no
`design.md` and no `verification-report.md`; the `devlog.md` ends in a written
**conclusion** ("viable with caveats") and a **graduate-or-discard decision**
(graduate - re-assess into a real delivery issue; the scratch branch is *not*
merged). `task.yml`'s `evidence:` registry carries a single
`spike-conclusion` entry with `decision: graduate-to-delivery` and a
`next_task:` link to the fresh delivery issue.

**Note on `compass check` for the Spike:** `compass check` is route-aware. On
a spike it skips the delivery defaults (`G1`-`G5`) and runs the spike-only
guardrails instead - `S1` (a `spike-conclusion` is recorded with a valid
decision; if `graduate-to-delivery`, `next_task` is set) and `S2`
(`changed_files` is empty - a spike ships nothing). Both *run and pass* for
this example; the run reports `compass check: PASS - all 2 Spike check(s)
passed`. The delivery guardrails are not bypassed, they are *deferred to
graduation*: if the finding is acted on, a fresh triage re-assesses it into a
real route where the delivery checks apply in full to any code that is kept.

**One-line lesson:** exploration is not forced through a delivery-shaped
pipeline - and it is safe because nothing lands from a spike.

---

## Reading order

If you read them in approach-weight order - `quick-fix-typo`, `feature-api-change`,
`hotfix-regression`, `initiative-new-subsystem`, `spike-technical-unknown` -
you watch the same eight-phase pipeline and the same artifact vocabulary
stretch and compress around a constant spine. That constancy is the point: a
person who has read one Compass issue can read any other. The *weight* changes;
the *shape* does not.

## BDD adapters

`bdd-adapters/` holds a worked project per BDD runner - `pytest-bdd`,
`cucumber-js`, `behave` and `godog`. Each takes the same Compass spec through
the same four steps (declare the runner, `compass bdd extract`, bind the steps,
run) and only the binding differs. Each is run by its own CI job, because an
example no job runs is an example nobody can trust.
