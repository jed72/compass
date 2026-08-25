<!--
TEMPLATE: distribution-map.md
Produced by: the plan stage (`/compass:plan`) on pair/swarm-capable work;
             consumed by breakdown (`/compass:breakdown`) and the
             `orchestrator` agent.
Lives at:    .compass/work/<task-slug>/distribution-map.md
Role in the pipeline: the record of what could run in parallel and why.
The design stage produces it; `scripts/swarm.sh` reads it to create
worktrees. Initiative-scale work writes this file even if a cap pins it
solo - the map is the
record of what could have been parallel and why it wasn't.

Independence has two tests, both must hold: disjoint code AND disjoint
scenario groups (see the worktree-swarm skill).

Fill every {{PLACEHOLDER}}.
-->

# Distribution Map - {{TASK_SLUG}}

> **Phase:** Plan · **Date:** {{DATE}} · **Reads from:** technical-design.md §4, acceptance-criteria.md
> **Consumed by:** breakdown, `scripts/swarm.sh`, the `orchestrator` agent

---

## 1. Work units

| Unit | From technical-design.md | Scenario group(s) | Code surface |
|---|---|---|---|
| U1 | {{plan §4 U1}} | {{group A}} | {{files / modules}} |
| U2 | {{plan §4 U2}} | {{group B}} | {{…}} |
| U3 | {{…}} | {{…}} | {{…}} |

## 2. Independence analysis

<!-- For each pair of units, are they independent? Independent = disjoint
     code AND disjoint scenarios. Shared surface = either fold into one
     stream or sequence them. Be honest - optimistic decomposition surfaces
     as a collision at integration. -->

| Unit pair | Disjoint code? | Disjoint scenarios? | Verdict |
|---|---|---|---|
| U1 ↔ U2 | {{yes/no}} | {{yes/no}} | {{independent \| shared surface - fold \| shared surface - sequence}} |
| U1 ↔ U3 | {{…}} | {{…}} | {{…}} |

**Shared foundations pulled forward:** {{e.g. "U0: the shared `Money` type - lands first, others branch from it" - or "none"}}

## 3. Scenario-group → stream mapping

<!-- One stream per independent unit. Each stream owns a disjoint set of
     scenarios from acceptance-criteria.md. -->

| Stream | Owns work unit(s) | Owns scenario ids | Branch name |
|---|---|---|---|
| stream-1 | {{U1}} | {{TRC-A1, TRC-A2}} | {{compass/<task-slug>/stream-1}} |
| stream-2 | {{U2}} | {{TRC-B1}} | {{compass/<task-slug>/stream-2}} |

## 4. Proposed worktree topology

- Proposed topology: {{solo \| pair (2–3) \| swarm (4+)}}
- Proposed stream count: {{N}}
- Worktree root: {{.compass/config.yml `swarm.worktree_root`, default ../.compass-worktrees}}
- One worktree + one `builder` per stream; {{plus one `orchestrator` (swarm) \| lead builder integrates (pair)}}.

## 5. The cap that applies

<!-- Topology is a routed decision. The worktree cap comes from the
     routing-guardrail `caps` in governance/routing-policy.yml, recorded in
     delivery-approach.md by the CLI. THE STANDING CAP: critical risk pins
     max_worktrees to 1 - initiative-scale work can be heavy AND solo. If the cap
     and the proposed count disagree, the cap wins; record it as
     cap-driven, not as a de-scope. -->

- Routing-guardrail cap from `delivery-approach.md`: {{e.g. "critical risk → max_worktrees: 1" - or "none"}}
- **Final stream count after caps:** {{N}}
- If capped below the proposed count: {{which units were folded/sequenced as a result, and the new branch plan}}

---

## Gate

- [ ] Every scenario in `acceptance-criteria.md` is owned by exactly one stream.
- [ ] Every "independent" verdict in §2 passed both tests (disjoint code AND scenarios).
- [ ] Final stream count respects every cap in §5.

Next stage: **break down the work** (`/compass:breakdown`) - runs `scripts/swarm.sh` with this map.
