# Devlog - search-crash-on-empty-filter

> **Task:** `/search` returns a 500 for any request with an empty `filter` object - live crash on the new mobile build · **Opened:** 2026-05-11
> Append-only. Newest at the bottom.

---

## 2026-05-11 08:50 - Frame

- **Event:** Needle ran; route computed. Urgent stub of `route.md` written to start the audit trail - completed properly at Land (BF-002).
- **Route:** Hotfix - selected by `urgency: live-defect` + `magnitude: small` (RS-SHAPE-002).
- **Readings:** blast radius cross-cutting, terrain brownfield-mapped, magnitude small, intent & role engineer/delivery, urgency live-defect.
- **Routing guardrails fired:** none - blast radius held at `cross-cutting`, not `critical`; had it been critical, RG-FLOOR-001 would have forced Expedition (incident, not hotfix).
- **Owed backfills:** BF-001 (promote reproduction to scenario), BF-002 (complete route.md), BF-003 (root-cause line + follow-up task). Hotfix always owes a backfill.
- **Next:** Specify - reproduce-first.

## 2026-05-11 09:08 - Specify (reproduce-first)

- **Event:** Wrote `test_empty_filter_object_does_not_crash` and watched it fail - it reproduces the production 500 (`AttributeError: 'NoneType' object has no attribute 'render'`). On Hotfix this failing test *is* the spec. `compass tdd-red` recorded it.
- **Artifact:** the red test; `evidence/red.json`.
- **Next:** Plan collapsed (root-cause note in `route.md` §5) → Build.

## 2026-05-11 09:30 - note: root cause identified

- **Event:** Root cause, not symptom. `filter_compiler.py:44` guarded with `if filter is not None` - but an empty object `{}` is not `None`, so it passed the guard and the compiler produced a `None` WHERE-clause the query builder then dereferenced. The guard tested the wrong condition.
- **Detail:** Symptom was the 500; root cause is the guard. The fix tests "has at least one key", not `is not None`.

## 2026-05-11 10:21 - edit: src/api/search/filter_compiler.py

- **Tool:** Edit · **Red marker:** cleared - the smallest correct guard added; `compass tdd-green` recorded the full `tests/api/` suite green (45 passed).

## 2026-05-11 10:40 - Verify

- **Event:** Full Verify - not compressed. Five gates applied (correctness, governance, traceability, regression, security), all GREEN. `clarity` deferred to backfill BF-001 per the route. `ruff check` clean.
- **Artifact:** `verification-report.md`.
- **Evidence:** test run in `verification-report.md` §2; `evidence/green.json`.
- **Next:** Land - ship, then the mandatory backfill.

## 2026-05-11 11:05 - Land - fix shipped

- **Event:** Fix deployed to production; the crash on the mobile build stopped. Living docs updated (the `/search` API reference now documents empty-filter behaviour).

## 2026-05-11 11:45 - Land - backfill paid

- **Event:** task closed - the mandatory Hotfix backfill is paid in full.
- **What landed:** A one-branch empty-filter guard in `src/api/search/filter_compiler.py`.
- **How verified:** `verification-report.md` gate decision - all five gates GREEN.
- **Backfills paid:**
  - BF-001 - reproduction test promoted into SCN-001, a proper Given/When/Then in `spec.feature.md`, traceable to INT-1. Paid 11:20.
  - BF-002 - `route.md` completed: four dimension readings with justifications, root-cause note. Paid 11:35.
  - BF-003 - **root cause:** a `is not None` guard where an "is non-empty" guard was needed; the empty-collection edge had no scenario, so nothing caught it. **Follow-up filed:** task `audit-search-input-edge-scenarios` - sweep the search input surface for other empty/edge shapes with no scenario. Paid 11:45.
- **Follow-ups filed:** `audit-search-input-edge-scenarios` (the gap class, not just this instance).
