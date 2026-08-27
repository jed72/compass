# Distribution Map - notifications-subsystem

> **Phase:** Plan · **Date:** 2026-03-07 · **Reads from:** technical-design.md §4, acceptance-criteria.md
> **Consumed by:** breakdown, `scripts/multiagent.sh`, the `orchestrator` agent

---

## 1. Work units

| Unit | From technical-design.md | Scenario group(s) | Code surface |
|---|---|---|---|
| U0 | plan §4 U0 | foundation (none directly) | `migrations/0042_notifications.sql` |
| U1 | plan §4 U1 | group A - TRC-001, TRC-002, TRC-003 | `src/notifications/dispatch.py`, `store.py`, `api.py` (read/mark-read) |
| U2 | plan §4 U2 | group B - TRC-004, TRC-005, TRC-006 | `src/notifications/preferences.py`, `api.py` (preferences) |

## 2. Independence analysis

| Unit pair | Disjoint code? | Disjoint scenarios? | Verdict |
|---|---|---|---|
| U1 ↔ U2 | mostly - overlap only on `api.py` (different endpoints) and `migrations/0042` (the U0 foundation) | yes - group A vs group B, no shared TRC-id | independent - the bounded `api.py` overlap is what the orchestrator polices, not a reason to fold |
| U0 ↔ U1 | no - U1 reads the table U0 creates | n/a (U0 has no scenarios) | shared foundation - sequence: U0 lands first |
| U0 ↔ U2 | no - U2 reads the table U0 creates | n/a | shared foundation - sequence: U0 lands first |

**Shared foundations pulled forward:** U0 - `migrations/0042_notifications.sql`.
The table both subtasks read. It lands first on the integration branch; subtask-1
and subtask-2 branch from it. This is the standard "shared foundation lands
first" move - it is why U1 and U2 can then run truly in parallel.

## 3. Scenario-group → subtask mapping

| Subtask | Owns work unit(s) | Owns scenario ids | Branch name |
|---|---|---|---|
| subtask-1 | U1 | TRC-001, TRC-002, TRC-003 | `compass/notifications-subsystem/subtask-1` |
| subtask-2 | U2 | TRC-004, TRC-005, TRC-006 | `compass/notifications-subsystem/subtask-2` |

U0 is not a subtask - it is a single commit on the integration branch
(`compass/notifications-subsystem/integration`) that both subtasks branch from,
landed by the orchestrator before the subtasks start.

## 4. Proposed worktree orchestration

- Proposed orchestration: multiagent (2 subtasks)
- Proposed subtask count: 2
- Worktree root: `../.compass-worktrees` (from `.compass/config.yml`)
- One worktree + one `builder` per subtask, plus one `orchestrator` that writes
  no feature code - it lands U0, watches the shared `api.py` surface during
  Build, and integrates at ship.

<!-- 2 subtasks is below the "4+" that the word "multiagent" usually implies, but it
     runs the multiagent machinery - worktrees + orchestrator - because the two
     subtasks share `api.py` and the migration. A pair (no dedicated
     orchestrator) would leave that shared surface unpoliced. The orchestration
     follows the surface, not the headcount. -->

## 5. The cap that applies

- `.compass/config.yml` `max_worktrees`: 6
- Routing-guardrail cap from `delivery-approach.md`: none - risk is `contained`, so
  the standing `critical → max_worktrees: 1` cap does not apply.
- **Final subtask count after caps:** 2 - unchanged, no cap bit.
- If capped below the proposed count: n/a - nothing was capped.

---

## Gate

- [x] Every scenario in `acceptance-criteria.md` is owned by exactly one subtask - TRC-001…003 → subtask-1, TRC-004…006 → subtask-2.
- [x] Every "independent" verdict in §2 passed both tests - U1 ↔ U2 are disjoint in scenarios and near-disjoint in code, with the bounded overlap assigned to the orchestrator, not ignored.
- [x] Final subtask count respects every cap in §5 - 2 ≤ 6, no routing cap in play.

Next stage: **breakdown** (`/compass:breakdown`) - runs `scripts/multiagent.sh` with this map.
