# Distribution Map - notifications-subsystem

> **Phase:** Plan · **Date:** 2026-03-07 · **Reads from:** plan.md §4, spec.feature.md
> **Consumed by:** Distribute, `scripts/swarm.sh`, the `orchestrator` agent

---

## 1. Work units

| Unit | From plan.md | Scenario group(s) | Code surface |
|---|---|---|---|
| U0 | plan §4 U0 | foundation (none directly) | `migrations/0042_notifications.sql` |
| U1 | plan §4 U1 | group A - SCN-001, SCN-002, SCN-003 | `src/notifications/dispatch.py`, `store.py`, `api.py` (read/mark-read) |
| U2 | plan §4 U2 | group B - SCN-004, SCN-005, SCN-006 | `src/notifications/preferences.py`, `api.py` (preferences) |

## 2. Independence analysis

| Unit pair | Disjoint code? | Disjoint scenarios? | Verdict |
|---|---|---|---|
| U1 ↔ U2 | mostly - overlap only on `api.py` (different endpoints) and `migrations/0042` (the U0 foundation) | yes - group A vs group B, no shared TRC-id | independent - the bounded `api.py` overlap is what the orchestrator polices, not a reason to fold |
| U0 ↔ U1 | no - U1 reads the table U0 creates | n/a (U0 has no scenarios) | shared foundation - sequence: U0 lands first |
| U0 ↔ U2 | no - U2 reads the table U0 creates | n/a | shared foundation - sequence: U0 lands first |

**Shared foundations pulled forward:** U0 - `migrations/0042_notifications.sql`.
The table both streams read. It lands first on the integration branch; stream-1
and stream-2 branch from it. This is the standard "shared foundation lands
first" move - it is why U1 and U2 can then run truly in parallel.

## 3. Scenario-group → stream mapping

| Stream | Owns work unit(s) | Owns scenario ids | Branch name |
|---|---|---|---|
| stream-1 | U1 | SCN-001, SCN-002, SCN-003 | `compass/notifications-subsystem/stream-1` |
| stream-2 | U2 | SCN-004, SCN-005, SCN-006 | `compass/notifications-subsystem/stream-2` |

U0 is not a stream - it is a single commit on the integration branch
(`compass/notifications-subsystem/integration`) that both streams branch from,
landed by the orchestrator before the streams start.

## 4. Proposed worktree topology

- Proposed topology: swarm (2 streams)
- Proposed stream count: 2
- Worktree root: `../.compass-worktrees` (from `.compass/config.yml`)
- One worktree + one `builder` per stream, plus one `orchestrator` that writes
  no feature code - it lands U0, watches the shared `api.py` surface during
  Build, and integrates at Land.

<!-- 2 streams is below the "4+" that the word "swarm" usually implies, but it
     runs the swarm machinery - worktrees + orchestrator - because the two
     streams share `api.py` and the migration. A pair (no dedicated
     orchestrator) would leave that shared surface unpoliced. The topology
     follows the surface, not the headcount. -->

## 5. The cap that applies

- `.compass/config.yml` `max_worktrees`: 6
- Routing-guardrail cap from `route.md`: none - blast radius is `contained`, so
  the standing `critical → max_worktrees: 1` cap does not apply.
- **Final stream count after caps:** 2 - unchanged, no cap bit.
- If capped below the proposed count: n/a - nothing was capped.

---

## Gate

- [x] Every scenario in `spec.feature.md` is owned by exactly one stream - SCN-001…003 → stream-1, SCN-004…006 → stream-2.
- [x] Every "independent" verdict in §2 passed both tests - U1 ↔ U2 are disjoint in scenarios and near-disjoint in code, with the bounded overlap assigned to the orchestrator, not ignored.
- [x] Final stream count respects every cap in §5 - 2 ≤ 6, no routing cap in play.

Next phase: **Distribute** (`/compass:breakdown`) - runs `scripts/swarm.sh` with this map.
