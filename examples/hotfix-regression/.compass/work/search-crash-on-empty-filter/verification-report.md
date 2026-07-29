# Verification Report - search-crash-on-empty-filter

> **Phase:** Verify · **Date:** 2026-05-11 · **Owning role:** QA
> **Agents:** verifier, reviewer
> **Route (from route.md):** Hotfix · **Gate count:** full Verify gate
> **Topology:** solo

<!-- Hotfix compresses the phases BEFORE Verify. It does NOT compress Verify.
     This report is the same weight it would be on Standard - that is the
     point of the route. -->

---

## 1. Scenario acceptance results

| Scenario id | Title | Result | Evidence |
|---|---|---|---|
| SCN-001 | Search with an empty filter object returns results, does not crash | PASS | §2 |

## 2. Test suite evidence

**Command run:** `pytest tests/api/`

```
tests/api/test_search.py ............                                    [ 27%]
tests/api/test_rate_limit.py .....                                       [ 38%]
tests/api/test_auth.py ..................                                [ 79%]
tests/api/test_upload_errors.py ........                                 [ 97%]
tests/api/test_health.py ..                                              [100%]

========================== 45 passed in 3.18s =============================
```

`test_empty_filter_object_does_not_crash` - the reproduction test that was red
at 09:08 (`evidence/red.json`) - now passes. The other 44 API tests still pass.

**Coverage (against the guardrail floor):**

```
src/api/search/filter_compiler.py    100%   (the new empty-filter branch is
                                             covered by SCN-001's test)
--------------------------------------------------
project line coverage                87%   (floor: 80% - met; unchanged by a
                                             one-branch guard)
```

## 3. Review dimensions

| Dimension | Applies on this route? | Result | Evidence |
|---|---|---|---|
| correctness | always | PASS | SCN-001 passes - the reproduction test is green. |
| governance | always | PASS | G1: the fix has a passing test it traces to (§2). G2: the acceptance criterion existed before the fix - it *was* the red test (`evidence/red.json` at 09:08 precedes the fix at ~10:20). G3: see traceability. G4: every gate has a resolving evidence pointer. S2 red-before-green followed - that is exactly how Hotfix's reproduce-first works. |
| traceability | always | PASS | `src/api/search/filter_compiler.py` → SCN-001 → INT-1; `compass check` confirms the chain. |
| regression | yes | PASS | The 44 pre-existing API tests in §2 still pass - the guard broke nothing. A fast fix that regressed something is just a faster outage; this did not. |
| security | yes | PASS | The empty-filter path now compiles to an explicit "no filtering applied", not a `None` that the query builder dereferenced. No injection surface introduced - the empty case takes a constant code path, no user value reaches the query string unfiltered that did not before. |
| clarity | deferred | n/a (deferred) | Per `route.md` §5, Hotfix defers `clarity` to the backfill. BF-001 promoted the reproduction into the readable SCN-001 Given/When/Then - that promoted scenario is the clarity record, and it is paid (see `task.yml` `backfills:`). |

## 4. Gate decision

| Gate | Required by | Status |
|---|---|---|
| verify.correctness | immovable + route | GREEN |
| verify.governance | immovable + route | GREEN |
| verify.traceability | immovable + route | GREEN |
| verify.regression | route | GREEN |
| verify.security | route | GREEN |

**Overall:** PASS - advance to Land (then the mandatory backfill).

---

## Gate

- [x] Every required review dimension passed with evidence attached (`clarity` deferred to the paid backfill BF-001, per the route).
- [x] Every gate in `route.md` and every immovable gate is GREEN.
- [x] This report is complete - no empty evidence blocks.

### Definition of Done

- [x] **Every scenario passes** - §1 is PASS.
- [x] **TDD suite green** - §2 shows all 45 API tests passing, output pasted.
- [x] **Coverage meets the guardrail floor** - 87% project, floor 80%.
- [x] **No lint / format / type errors** - `ruff check src/api/search/` clean (logged in `devlog.md`).
- [x] **Traceability intact** - code → scenario → intent holds.
- [x] *(carried to Land)* Living docs updated - the `/search` API reference now notes that an empty `filter` object means "no filtering".
- [x] *(carried to Land)* **Every owed backfill paid** - BF-001, BF-002, BF-003 all `paid` in `task.yml`. This is the Hotfix-defining check: `/compass:land` refuses to close while any backfill is `owed`.

Next phase: **Land** (`/compass:land`) - ship, then pay the backfill.
