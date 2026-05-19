<!--
TEMPLATE: plan.md
Produced by: the Plan phase (`/compass:plan`); owning agent `planner`.
Lives at:    .compass/work/<task-slug>/plan.md
Role in the pipeline: the technical plan. Records the approach, the design
decisions as ADR-style notes, the governance check against all of
governance/, and the independent work units. On Express/Hotfix, Plan
collapses to a one-line note in route.md and this file is not written; on
Spike it collapses to a timebox sketch in route.md. On Standard this is a
real file; on Expedition it is paired with distribution-map.md.

The governance check here is run by the `governance-check` skill.

Fill every {{PLACEHOLDER}}.
-->

# Plan — {{TASK_SLUG}}

> **Phase:** Plan · **Date:** {{DATE}} · **Owning agent:** planner
> **Plan weight (from route.md):** {{real plan.md \| plan.md + distribution-map.md}}

---

## 1. Approach

<!-- The technical approach in a few paragraphs. How the scenarios in
     spec.feature.md get satisfied. What changes, where, in what order. -->

{{APPROACH}}

## 2. Design decisions (ADR-style)

<!-- One block per real design decision. A decision with no alternative
     considered is usually not a decision yet. Express has none of these by
     definition; if you have one, the route was mis-composed — re-frame. -->

### DD-1 — {{DECISION TITLE}}

- **Context:** {{what forced a choice}}
- **Decision:** {{what was chosen}}
- **Alternatives considered:** {{what else, and why not}}
- **Consequences:** {{what this commits us to; what it rules out}}
- **Governance tie:** {{which guardrail or engineering strategy this honours — or "n/a"}}

### DD-2 — {{DECISION TITLE}}

- **Context:** {{…}}
- **Decision:** {{…}}
- **Alternatives considered:** {{…}}
- **Consequences:** {{…}}
- **Governance tie:** {{…}}

## 3. Governance check

<!-- Run against ALL of governance/ — guardrails.md, strategies.md, and
     routing-policy.md. A failed guardrail here blocks the phase — fix the
     plan, do not note the violation and move on. A strategy not followed is
     a recorded judgement, not an automatic block. This is the
     `governance-check` skill's output. -->

| Area | Result | Evidence / note |
|---|---|---|
| Guardrails (G1–G5 + project) | {{pass \| fail}} | {{e.g. "G2 acceptance criteria stated before Build; G3 traceability chains designed in; coverage targets the guardrail floor"}} |
| Method strategies (S1–S4 + project) | {{followed \| deviation recorded}} | {{e.g. "S1 BDD + S2 TDD apply; S3 simplest-thing honoured. Any deviation noted with its reason."}} |
| Product strategies | {{followed \| deviation recorded \| n/a}} | {{e.g. "plan delivers brief.md's outcome; honours the no-dark-patterns strategy"}} |
| Voice & positioning strategies | {{followed \| deviation recorded \| n/a}} | {{n/a unless marketer in play; if so, claims traceable}} |
| Routing policy | {{pass \| fail}} | {{plan does not require skipping anything route.md kept; floors honoured}} |

## 4. Work units

<!-- The independent (or shared-surface) units of work. On Standard this is
     a short list; on Expedition it becomes the input to distribution-map.md.
     Independence = disjoint code AND disjoint scenario groups. -->

| Unit | Scenario group(s) it satisfies | Code surface it touches | Independent of |
|---|---|---|---|
| U1 | {{group A — TRC-A1, TRC-A2}} | {{files / modules}} | {{U2, U3 — or "shares surface with U2"}} |
| U2 | {{group B — TRC-B1}} | {{…}} | {{…}} |

**Parallelism assessment:** {{"U1 and U2 are genuinely independent → candidate pair/swarm" — or "all units share surface → solo"}}

---

## Gate

- [ ] Every scenario in `spec.feature.md` is covered by a work unit.
- [ ] Governance check passes — every guardrail clears with evidence; any strategy deviation is recorded (above).
- [ ] If parallel work is possible, `distribution-map.md` is written next.

Next phase: **Distribute** (`/compass:distribute`) — or straight to **Build** if the route is solo.
