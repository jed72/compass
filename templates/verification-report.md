<!--
TEMPLATE: verification-report.md
Produced by: the Verify phase (`/compass:verify`); owning role QA, agents
             `verifier` (runs the suites) and `reviewer` (applies the
             review dimensions).
Lives at:    .compass/work/<task-slug>/verification-report.md
Role in the pipeline: the Verify output. Proves the work with EVIDENCE -
pasted command output and artifacts, never assertion. "It works" is not a
gate-passing statement on any route. The route's gate set and review
dimensions come from route.md; the `immovable_gates` from
governance/routing-policy.md are stapled on regardless.

Fill every {{PLACEHOLDER}}. Every pass needs evidence attached - an empty
evidence block is an automatic fail.
-->

# Verification Report - {{TASK_SLUG}}

> **Phase:** Verify · **Date:** {{DATE}} · **Owning role:** QA
> **Agents:** verifier, reviewer{{, marketing-lens if claims dimension applies}}
> **Route (from route.md):** {{reference route}} · **Gate count:** {{1 \| 2 \| all}}
> **Topology:** {{solo \| pair \| swarm - swarm verifies per-stream then combined}}

---

## 1. Scenario acceptance results

<!-- Every scenario in spec.feature.md run as an acceptance check - the same
     artifact the spec was, read now at verification time. -->

| Scenario id | Title | Result | Evidence (where the run is pasted below) |
|---|---|---|---|
| TRC-A1 | {{…}} | {{PASS \| FAIL}} | §2 |
| TRC-A2 | {{…}} | {{PASS \| FAIL}} | §2 |
| TRC-B1 | {{…}} | {{PASS \| FAIL}} | §2 |
| TRC-F1 | {{…}} | {{PASS \| FAIL}} | §2 |

## 2. Test suite evidence

<!-- Pasted command output. Not a description of it - the actual run.
     On a swarm, paste per-stream runs first, then the combined run. -->

**Command run:** `{{e.g. npm test}}`

```
{{PASTE THE FULL TEST RUN OUTPUT HERE}}
```

**Coverage (against the guardrail floor - G1-related):**

```
{{PASTE COVERAGE OUTPUT - must meet or exceed the guardrail coverage floor}}
```

<!-- Swarm: repeat the block above per stream, then add a "Combined
     regression" block for the integrated result. -->

## 3. Review dimensions

<!-- Apply each dimension route.md lists. correctness, governance,
     traceability are ALWAYS on for a delivery route - they are the default
     guardrails in review form. Others per the route: regression, security
     (scaled or full), clarity, claims. Each gets pass/fail AND evidence.

     "Assessed by" records WHO reached the judgement: the `reviewer` agent, a
     named person, or "author" where the person who did the work also graded
     it. Be accurate rather than flattering. An author-assessed dimension is
     weaker evidence than an independently assessed one - the author cannot
     see what they did not think of, and clarity in particular has no
     mechanical backstop. This is a record, not a gate: nothing fails because
     a dimension was self-assessed, but a reader can weigh it, and
     `compass calibration` can spot a project where one dimension is never
     independently reviewed. The mechanical checks (`compass check`, the test
     suite) are unaffected either way - they do not care who ran them. -->

| Dimension | Applies on this route? | Result | Assessed by | Evidence |
|---|---|---|---|---|
| correctness | always | {{PASS \| FAIL}} | {{reviewer \| name \| author}} | {{every scenario in §1 passes}} |
| governance | always | {{PASS \| FAIL}} | {{…}} | {{honours governance/ - guardrails clear with evidence, strategy deviations recorded; cite checks}} |
| traceability | always | {{PASS \| FAIL}} | {{…}} | {{code→scenario→intent and claim→scenario chains intact}} |
| regression | {{yes / no}} | {{PASS \| FAIL \| n/a}} | {{…}} | {{nothing previously passing now fails - paste the run}} |
| security | {{full / scaled / no}} | {{PASS \| FAIL \| n/a}} | {{…}} | {{OWASP-style pass, scaled to blast radius}} |
| clarity | {{yes / no}} | {{PASS \| FAIL \| n/a}} | {{…}} | {{a future reader can follow it}} |
| claims | {{if role / yes}} | {{PASS \| FAIL \| n/a}} | {{…}} | {{see launch-readiness.md - every claim traces to a passing scenario}} |

## 4. Gate decision

<!-- A gate passes only with evidence. List every gate in route.md's set
     PLUS every immovable gate from governance/routing-policy.md. -->

| Gate | Required by | Status |
|---|---|---|
| verify.correctness | immovable + route | {{GREEN \| RED}} |
| verify.governance | immovable + route | {{GREEN \| RED}} |
| verify.regression | immovable | {{GREEN \| RED}} |
| verify.claims | immovable (if marketer in play) | {{GREEN \| RED \| n/a}} |
| {{verify.traceability / verify.security / verify.clarity …}} | route | {{GREEN \| RED}} |

**Overall:** {{PASS - advance to Land \| FAIL - task does not advance}}

<!-- If FAIL: the task does not advance. Fix it, or QA sends it back to
     Specify if the scenarios are uncoverable. Record which below. -->

**If FAIL - disposition:** {{"fix and re-verify" \| "sent back to Specify: scenarios TRC-… are uncoverable because …"}}

---

## Gate

- [ ] Every required review dimension passed with evidence attached.
- [ ] Every gate in `route.md` and every immovable gate is GREEN.
- [ ] This report is complete - no empty evidence blocks.

### Definition of Done

<!-- The crisp exit check. The Definition of Ready (clarifications.md) was the
     entry gate into Plan; this is the exit gate out of Verify. Items 1–5 are
     proven here, with evidence above. Items 6–7 are carried into Land - they
     are listed so the close-out is one continuous checklist, not two.

TYPED DOD - REQUIRED INLINE-TAG SYNTAX (G4: evidence, not assertion):
  Every unchecked box must carry exactly ONE of these inline tags, or be ticked:

    - [ ] (evidence: EV-<id>) <description>
        Passes when EV-<id> is in task.yml's evidence registry with an accepted
        type (test-run, command-output, manual-review, human-approval, artifact,
        security-review, migration-plan, rollback-plan, claim-review).

    - [ ] (backfill: BF-<id>) <description>
        Passes (defers) when BF-<id> is in task.yml backfills with status: owed.
        Add target_task: <slug> on the backfill entry to block that task's Land
        until paid (compass backfill pay --task <source-slug> BF-<id>).

    - [x] <description>
        A human-ticked box passes unconditionally - the human took responsibility.

    - [ ] <bare description>   ← FAILS compass check (bare unchecked box)
        Narrative notes in devlog.md do NOT clear a DoD item. G4 applies.

  Cross-task: if another task has a backfill with target_task pointing at this
  task and status: owed, compass check at Land fails until that backfill is paid.
-->

- [ ] (evidence: {{EV-id}}) **Every scenario passes** - §1 is all PASS; the
      spec, read as the acceptance suite, is green.
- [ ] (evidence: {{EV-id}}) **TDD suite green** - §2 shows the full suite
      passing, output pasted.
- [ ] (evidence: {{EV-id}}) **Coverage meets the guardrail floor (G1-related)**
      - evidence in §2.
- [ ] (evidence: {{EV-id}}) **No lint / format / type errors** - clean,
      evidence pasted.
- [ ] (evidence: {{EV-id}}) **Traceability intact** - code → scenario → intent
      holds; claim → scenario holds where the marketer is in play.
- [ ] (backfill: {{BF-id}}) *(carried to Land)* Living docs updated to match
      reality.
- [ ] (backfill: {{BF-id}}) *(carried to Land)* Every owed backfill paid - no
      unpaid Hotfix backfill, no unbacked marketing claim.

Next phase: **Land** (`/compass:land`) - only on overall PASS.
