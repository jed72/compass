<!--
TEMPLATE: delivery-approach.md
Produced by: Frame phase / the Needle (`/compass:frame`).
Lives at:    .compass/work/<task-slug>/delivery-approach.md
Authority:   This is the audit centrepiece. It records what the Needle
             assessed, the route it computed, every routing guardrail that
             fired, and - first-class - what was skipped and why it is safe.
             Rubric: routes/router.md. Policy: governance/routing-policy.md
             (routing guardrails + routing strategies).

On a Spike route, the Needle also writes a `.spike` marker file in the task
directory so the pre-tool hook knows to suspend the TDD strategy.

Fill every {{PLACEHOLDER}}. A dimension with no justification is not a
reading - ask the human instead. A phase with no "safe to skip because…"
line is not skippable - it runs.
-->

# Route - {{TASK_SLUG}}

> **Task:** {{ONE-LINE TASK DESCRIPTION AS INVOKED}}
> **Framed:** {{DATE}} by {{WHO}} · **Revision:** {{N}} (revision 1 = first frame; bump on `--reframe`)
> **Reference route:** {{Express | Standard | Expedition | Hotfix | Spike}}

<!-- On a `--reframe`, keep the prior revision below this line under a
     "## Superseded - revision <N-1>" heading so the history stays visible. -->

---

## 1. The four dimension readings

<!-- Each reading is a value from routes/router.md plus a one-line
     justification. No justification → ask, do not guess. -->

| Dimension | Reading | One-line justification |
|---|---|---|
| **Blast radius** | {{trivial \| contained \| cross-cutting \| critical}} | {{Why this value. Consequence, not effort.}} |
| **Terrain** | {{greenfield \| brownfield-mapped \| brownfield-unmapped}} | {{Why this value. Is current behaviour written down?}} |
| **Magnitude** | {{atomic \| small \| standard \| large \| product}} | {{Why this value. When unsure, estimate up.}} |
| **Intent & role** | {{engineer \| product-owner \| product-marketer \| designer \| qa}} | {{Who invoked, and the outcome actually wanted - read the brief if one exists.}} |

**Domain tags (`touches:`):** {{[auth, payments, personal-data, migrations, public-api, …] or "none"}}
<!-- These tags are what the routing guardrails (floors) key on. Be honest -
     a one-line auth change still touches auth. -->

---

## 2. The composed candidate route

<!-- The route assembled from the dimension contributions, biased by the
     routing strategies, BEFORE the routing guardrails are applied. Name the
     reference route for shared vocabulary, then list deviations. -->

Candidate route: **{{reference route name}}**, with these deviations from its reference shape:

- {{e.g. "Verify also runs the `security` dimension because blast radius is cross-cutting." - or "none"}}

Candidate review dimensions: {{correctness, governance, traceability, … per the table in routes/router.md}}

---

## 3. Routing guardrails that fired

### 3a. Policy provenance

<!-- WHICH POLICY produced this route. `compass route evaluate` prints both
     lines below - copy them here. Without this, a reader months later cannot
     tell a genuinely light route from one computed against stale governance,
     and the audit trail is honest about what happened while blind to what
     should have. If the CLI reported drift, record it: a route computed
     against a policy missing framework rules is a route missing gates. -->

- Policy file: {{path to the routing-policy.yml that was read}}
- Policy version: {{the `version:` that file declares}}
- Drift: {{"none - the project's policy matches framework vX.Y.Z" - or "N rule(s)/check(s) missing against framework vX.Y.Z; see `compass policy lint`"}}



<!-- Every floor / cap / immovable_gate / blocking role_rule from
     governance/routing-policy.md that matched. Quote each one's rationale.
     If none fired, say so explicitly - silence is not a record. Routing
     strategies that biased the composition can be noted here too, but the
     guardrails are what this section must capture. -->

| Rule type | Rule | What it changed | Rationale (quoted from the policy) |
|---|---|---|---|
| {{floor \| cap \| immovable_gate \| role_rule}} | {{e.g. `touches: [auth]`}} | {{e.g. "Candidate Express raised to Expedition."}} | {{"…"}} |

<!-- If nothing fired: "No routing guardrail fired. Candidate route stands." -->

---

## 4. The final route

### 4a. Per-phase weight

| Phase | Weight | Notes |
|---|---|---|
| Frame | Full | Always. This document is the output. |
| Specify | {{one scenario \| small feature set \| full BDD discovery \| reproduce-first failing test \| collapsed to a question (Spike)}} | {{discovery vs. blueprint-distillation; how deep}} |
| Clarify | {{collapsed \| light pass \| full pass \| skipped (Spike)}} | {{if collapsed, the de-scope ledger below must justify it}} |
| Plan | {{one-line edit note \| real design.md \| design.md + distribution-map.md \| timebox sketch (Spike)}} | {{design decisions expected; governance check scope}} |
| Distribute | {{skipped (solo) \| pair \| swarm}} | {{stream count comes from the distribution map}} |
| Build | {{test surface target}} | {{scaled to blast radius - see tdd-discipline}} |
| Verify | {{gate count}} | {{which review dimensions - section 4b}} |
| Land | {{trivial commit \| coordinated merge}} | {{which backfills are owed - section 6}} |

### 4b. Gate set

- Number of gates: {{1 \| 2 \| all \| 1 Conclude gate (Spike)}}
- Review dimensions applied: {{list - correctness, governance, traceability are always on for a delivery route; Spike runs none of these}}
- Immovable gates stapled on (from routing-policy.md): {{verify.correctness, verify.governance, verify.regression, verify.claims, …}}

### 4c. Swarm topology

- Topology: {{solo \| pair (2–3 streams) \| swarm (4+ streams)}}
- Stream count: {{N - from distribution-map.md, or "n/a (solo)"}}
- Worktree root: {{from .compass/config.yml `swarm.worktree_root`, default ../.compass-worktrees}}
- Cap in effect: {{e.g. "critical blast radius → max_worktrees: 1" - from a routing-guardrail cap in routing-policy.yml - or "none"}}
- Orchestrator agent: {{yes (swarm) \| no - lead builder integrates (pair) \| n/a (solo)}}

---

## 5. The de-scope ledger

<!-- THE AUDIT CENTREPIECE. Every phase or check that is collapsed or
     skipped, each with an explicit "safe to skip because…" line. A phase
     with no justification CANNOT be skipped - it runs. On Expedition this
     table is empty by definition; cap-driven reductions go in section 4c,
     not here. On Spike the standing justification for every row is the same:
     nothing lands from a Spike (see routes/spike.md). -->

| Phase / check | Action | Safe to skip / collapse because… |
|---|---|---|
| {{e.g. Clarify}} | {{collapsed \| skipped}} | {{e.g. "The spec is a single scenario the Needle certified unambiguous - nothing to clarify."}} |
| {{e.g. Plan}} | {{collapsed to one-liner}} | {{e.g. "atomic magnitude on mapped terrain - no design decision; the plan is 'edit src/foo.ts'."}} |
| {{e.g. Distribute}} | {{skipped}} | {{e.g. "One stream of work - parallelism would be pure overhead."}} |

**One-line edit note (Express/Hotfix collapsed Plan only):** {{which file(s) to edit, or root-cause note}}

**Spike question + timebox (Spike collapsed Specify/Plan only):** {{the question to answer, and the timebox}}

---

## 6. Owed backfills

<!-- Ceremony borrowed from the front of the pipeline that must be paid
     back at Land before the task can close. Hotfix always owes a backfill;
     other routes owe whatever the de-scope ledger marked for backfill. A
     Spike owes nothing - it lands nothing; its exit is graduate or discard,
     not a backfill. -->

- [ ] {{e.g. "Hotfix backfill: delivery-approach.md completed properly, reproduction test promoted to a real scenario in acceptance-criteria.md, root-cause line in devlog.md."}}
- [ ] {{e.g. "none owed"}}

---

## 7. Human overrides

<!-- Routing is advisory until confirmed. Any reading or the final route may
     be overridden by a human - recorded here with who and why. What CANNOT
     be overridden: an immovable_gate, or a floor (a routing guardrail is
     governance speaking; changing it means amending
     governance/routing-policy.md, not overriding a route). -->

| What was overridden | From → To | Who | Why |
|---|---|---|---|
| {{e.g. "Magnitude reading"}} | {{standard → small}} | {{name}} | {{reason}} |

<!-- If none: "No human overrides. Route confirmed as composed." -->

---

## 8. Confirmation

- [ ] Route presented to the invoker and confirmed (or overridden - see §7).
- [ ] Every dimension in §1 has a justification.
- [ ] Every skipped/collapsed phase in §5 has a "safe to skip because…" line.
- [ ] On a Spike route: the `.spike` marker file is written to the task directory.
- [ ] `devlog.md` opened with the Frame entry.

Next phase: **Specify** (`/compass:specify`) - or **Explore** on a Spike route.
