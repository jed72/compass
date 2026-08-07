<!--
TEMPLATE: delivery-approach.md
Produced by: triage (`/compass:triage`).
Lives at:    .compass/work/<task-slug>/delivery-approach.md
Authority:   This is the audit centrepiece. It records the assessment, the
             delivery approach the policy computed, every policy rule that
             fired, and - first-class - what was skipped and why it is safe.
             Rubric: the delivery-approach reference docs. Policy:
             governance/routing-policy.md (hard rules + soft biases).

On a spike, triage also writes a `.spike` marker file in the issue
directory so the pre-tool hook knows to suspend the TDD strategy.

Fill every {{PLACEHOLDER}}. A dimension with no justification is not an
assessment - ask the human instead. A stage with no "safe to skip because…"
line is not skippable - it runs.
-->

# Delivery approach - {{TASK_SLUG}}

> **Issue:** {{ONE-LINE DESCRIPTION AS INVOKED}}
> **Triaged:** {{DATE}} by {{WHO}} · **Revision:** {{N}} (revision 1 = first triage; bump on `--reframe`)
> **Reference shape:** {{quick fix | feature | initiative | hotfix | spike}}

<!-- On a re-assessment (`--reframe`), keep the prior revision below this
     line under a "## Superseded - revision <N-1>" heading so the history
     stays visible. -->

---

## 1. The assessment

<!-- Each dimension gets a value from the reference docs plus a one-line
     justification. No justification → ask, do not guess. -->

| Dimension | Value | One-line justification |
|---|---|---|
| **Risk** | {{trivial \| contained \| cross-cutting \| critical}} | {{Why this value. Consequence, not effort.}} |
| **Familiarity** | {{greenfield \| brownfield-mapped \| brownfield-unmapped}} | {{Why this value. Is current behaviour written down?}} |
| **Size** | {{atomic \| small \| standard \| large \| product}} | {{Why this value. When unsure, estimate up.}} |
| **Goal & role** | {{engineer \| product-owner \| product-marketer \| designer \| qa}} | {{Who invoked, and the outcome actually wanted - read the PRD or intake if one exists.}} |

**Labels (the spine's `touches:` field):** {{[auth, payments, personal-data, migrations, public-api, …] or "none"}}
<!-- These are what the policy's hard floors key on. Be honest - a one-line
     auth change still carries the auth label. -->

---

## 2. The composed candidate

<!-- The delivery approach assembled from the assessment, biased by the
     policy's soft defaults, BEFORE the hard rules are applied. Name the
     reference shape for shared vocabulary, then list deviations. -->

Candidate: **{{reference shape}}**, with these deviations from its reference form:

- {{e.g. "Test & review also runs the security dimension because the risk is cross-cutting." - or "none"}}

Candidate review dimensions: {{correctness, governance, traceability, … per the reference docs}}

---

## 3. Policy rules that fired

### 3a. Policy provenance

<!-- WHICH POLICY produced this approach. `compass route evaluate` prints
     both lines below - copy them here. Without this, a reader months later
     cannot tell a genuinely light approach from one computed against stale
     governance. If the CLI reported drift, record it: an approach computed
     against a policy missing framework rules is an approach missing
     gates. -->

- Policy file: {{path to the routing-policy.yml that was read}}
- Policy version: {{the `version:` that file declares}}
- Drift: {{"none - the project's policy matches framework vX.Y.Z" - or "N rule(s)/check(s) missing against framework vX.Y.Z; see `compass policy lint`"}}

<!-- Every floor / cap / immovable gate / blocking role rule from
     governance/routing-policy.md that matched. Quote each one's rationale.
     If none fired, say so explicitly - silence is not a record. -->

| Rule type | Rule | What it changed | Rationale (quoted from the policy) |
|---|---|---|---|
| {{floor \| cap \| immovable_gate \| role_rule}} | {{e.g. the auth label}} | {{e.g. "Candidate quick fix raised to initiative-scale ceremony."}} | {{"…"}} |

<!-- If nothing fired: "No hard policy rule fired. The candidate stands." -->

---

## 4. The final delivery approach

### 4a. Per-stage weight

| Stage | Weight | Notes |
|---|---|---|
| Triage | Full | Always. This document is the output. |
| Define acceptance criteria | {{one scenario \| small feature set \| full BDD discovery \| reproduce-first failing test \| collapsed to a question (spike)}} | {{discovery vs. distilling existing behaviour first; how deep}} |
| Requirements review | {{collapsed \| light pass \| full pass \| skipped (spike)}} | {{if collapsed, the de-scope ledger below must justify it}} |
| Design | {{one-line edit note \| real design.md \| design.md + distribution-map.md \| timebox sketch (spike)}} | {{design decisions expected; governance check scope}} |
| Break down the work | {{skipped (solo) \| pair \| swarm}} | {{stream count comes from the distribution map}} |
| Implement | {{test surface target}} | {{scaled to risk - see the TDD skill}} |
| Test & review | {{gate count}} | {{which review dimensions - section 4b}} |
| Ship | {{trivial commit \| coordinated merge}} | {{which follow-ups are owed - section 6}} |

### 4b. Gate set

- Number of gates: {{1 \| 2 \| all \| 1 conclude gate (spike)}}
- Review dimensions applied: {{list - correctness, governance, traceability are always on for delivery work; a spike runs none of these}}
- Immovable gates stapled on (from routing-policy.md): {{verify.correctness, verify.governance, verify.regression, verify.claims, …}}

### 4c. Swarm topology

- Topology: {{solo \| pair (2-3 streams) \| swarm (4+ streams)}}
- Stream count: {{N - from distribution-map.md, or "n/a (solo)"}}
- Worktree root: {{from .compass/config.yml `swarm.worktree_root`, default ../.compass-worktrees}}
- Cap in effect: {{e.g. "critical risk → max_worktrees: 1" - from a hard cap in routing-policy.yml - or "none"}}
- Orchestrator agent: {{yes (swarm) \| no - lead builder integrates (pair) \| n/a (solo)}}

---

## 5. The de-scope ledger

<!-- THE AUDIT CENTREPIECE. Every stage or check that is collapsed or
     skipped, each with an explicit "safe to skip because…" line. A stage
     with no justification CANNOT be skipped - it runs. On initiative-scale
     work this table is empty by definition; cap-driven reductions go in
     section 4c, not here. On a spike the standing justification for every
     row is the same: nothing ships from a spike. -->

| Stage / check | Action | Safe to skip / collapse because… |
|---|---|---|
| {{e.g. Requirements review}} | {{collapsed \| skipped}} | {{e.g. "The acceptance criteria are a single scenario certified unambiguous at triage - nothing to review."}} |
| {{e.g. Design}} | {{collapsed to one-liner}} | {{e.g. "atomic size on familiar ground - no design decision; the design is 'edit src/foo.ts'."}} |
| {{e.g. Break down the work}} | {{skipped}} | {{e.g. "One stream of work - parallelism would be pure overhead."}} |

**One-line edit note (quick fix / hotfix collapsed design only):** {{which file(s) to edit, or root-cause note}}

**Spike question + timebox (spike collapsed stages only):** {{the question to answer, and the timebox}}

---

## 6. Owed follow-ups

<!-- Ceremony borrowed from the front of the pipeline that must be settled
     at ship time before the issue can close. A hotfix always owes one;
     other work owes whatever the de-scope ledger marked. A spike owes
     nothing - it ships nothing; its exit is graduate or discard. -->

- [ ] {{e.g. "Hotfix follow-up: this record completed properly, reproduction test promoted to a real scenario in acceptance-criteria.md, root-cause line in devlog.md."}}
- [ ] {{e.g. "none owed"}}

---

## 7. Human overrides

<!-- The computed approach is advisory until confirmed. Any assessment value
     or the final approach may be overridden by a human - recorded here with
     who and why. What CANNOT be overridden: an immovable gate, or a floor
     (a hard policy rule is governance speaking; changing it means amending
     governance/routing-policy.md, not overriding one issue's approach). -->

| What was overridden | From → To | Who | Why |
|---|---|---|---|
| {{e.g. "Size"}} | {{standard → small}} | {{name}} | {{reason}} |

<!-- If none: "No human overrides. Approach confirmed as composed." -->

---

## 8. Confirmation

- [ ] Approach presented to the invoker and confirmed (or overridden - see §7).
- [ ] Every dimension in §1 has a justification.
- [ ] Every skipped/collapsed stage in §5 has a "safe to skip because…" line.
- [ ] On a spike: the `.spike` marker file is written to the issue directory.
- [ ] `devlog.md` opened with the triage entry.

Next stage: **define acceptance criteria** (`/compass:define`) - or explore, on a spike.
