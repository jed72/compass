# Devlog - notifications-subsystem

> **Issue:** Build the in-app notifications subsystem - durable delivery, per-category preferences, an un-mutable security category · **Opened:** 2026-03-02
> Append-only. Newest at the bottom.

---

## 2026-03-02 11:00 - triage

- **Event:** Needle ran; route computed.
- **Route:** initiative - see `delivery-approach.md` revision 1.
- **Assessment:** risk contained, familiarity greenfield, size standard, intent & role product-owner/delivery, touches [migrations].
- **Routing guardrails fired:** RP-FLOOR-003 (touches migrations → candidate raised standard→expedition); RP-ROLE-002 (product-owner → prd.md required, Plan blocked until intent-fidelity check).
- **Outstanding follow-ups:** none - initiative borrows no ceremony. (`G5` applies because of the `migrations` tag - a ship sign-off, not a follow-up.)
- **Next:** define.

## 2026-03-05 16:30 - define

- **Event:** Full BDD discovery from `prd.md`. Six scenarios discovered, grouped by independence into group A (delivery & dispatch) and group B (preferences) - that grouping is the seed for the distribution map.
- **Artifact:** `acceptance-criteria.md` - 6 scenarios in 2 groups (+ a failure-mode scenario, TRC-006).
- **Next:** refine.

## 2026-03-06 14:00 - refine

- **Event:** Full pass. Three ambiguities resolved - Q1 (security override → fixed category, not a flag), Q2 (dedup → once-ever), Q3 (the 5s in TRC-001 → test bound, not an SLA). Product owner reviewed and signed the intent-fidelity check at the foot of `prd.md` - that clears the RP-ROLE-002 block on Plan.
- **Artifact:** `requirements-review.md` - Definition of Ready ticked.
- **Next:** Plan (now unblocked).

## 2026-03-07 10:00 - Plan

- **Event:** Full `design.md` + `distribution-map.md`. Three design decisions recorded - DD-1 (fixed security category), DD-2 (idempotency key), DD-3 (write-before-deliver durability). Governance check passed, including how `G5`'s migration sign-off is routed into ship. Two independent streams + a shared U0 foundation (`migrations/0042`).
- **Artifact:** `design.md`, `distribution-map.md`.
- **Next:** breakdown.

## 2026-03-08 09:30 - breakdown

- **Event:** `scripts/swarm.sh` ran. U0 (`migrations/0042_notifications.sql`) landed on the integration branch first. Two worktrees created - `stream-1` (dispatch/store), `stream-2` (preferences) - one `builder` each, plus the `orchestrator` watching the shared `api.py` surface.
- **Artifact:** worktrees under `../.compass-worktrees`.
- **Next:** Build (parallel).

## 2026-03-09 10:14 - Build

- **Event:** Both builders wrote their failing scenarios first. `compass tdd-red` recorded the combined red - all 6 scenarios fail (`ModuleNotFoundError`, the subsystem does not exist yet).
- **Evidence:** `evidence/red-TRC-001.json`.
- **Next:** parallel implementation in the two worktrees.

## 2026-03-11 15:20 - note: orchestrator intervention

- **Event:** The orchestrator flagged stream-1 and stream-2 both about to add a route to `api.py` with the same path prefix in incompatible ways.
- **Detail:** Resolved before collision - the orchestrator had stream-2 rebase onto stream-1's `api.py` router skeleton, then both added their own endpoints under it. This is the swarm machinery doing the job a pair (no orchestrator) could not.

## 2026-03-13 14:50 - Verify

- **Event:** Per-stream verification (stream-1: 3 green, stream-2: 3 green), then `scripts/integrate.sh` merged both onto the integration branch and the orchestrator ran the combined regression - 71 passed. All seven initiative gates GREEN. `ruff` + `mypy` clean. Coverage 85% (floor 80%).
- **Artifact:** `verification-report.md` - Definition of Done ticked.
- **Evidence:** per-stream + combined runs in `verification-report.md` §2; `evidence/green-TRC-001.json`.
- **Next:** ship.

## 2026-03-13 16:20 - note: `G5` sign-off

- **Event:** Guardrail `G5` - irreversible change. L. Haddad (eng lead) reviewed `migrations/0042` forward and rollback paths and approved in PR #618.
- **Detail:** Recorded in `task.yml` `approvals:`. `compass check` requires this because the assessment include `labels: [migrations]`.

## 2026-03-13 17:00 - ship

- **Event:** issue closed.
- **What landed:** The `src/notifications/` subsystem - `dispatch.py`, `store.py`, `preferences.py`, `api.py` - and `migrations/0042_notifications.sql`. Orchestrated merge of both streams; combined regression clean.
- **How verified:** `verification-report.md` gate decision - all seven gates GREEN; `G5` approval on record.
- **Follow-ups resolved:** none outstanding.
- **Follow-up issues filed:** none outstanding by this issue. (The external launch - positioning, claims, a marketer - is the separate already-planned next issue, not a follow-up this issue generated.)
