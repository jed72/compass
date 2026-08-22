# Spec - search-crash-on-empty-filter

> **Phase:** define (reproduce-first) · **Last updated:** 2026-05-11 · **Owning agent:** spec-author
> **Familiarity:** brownfield-mapped - on Hotfix the spec begins as the failing regression test; this file is its promoted, readable form (follow-up FU-001).

## How each role reads this file

- **Product owner / manager** - reads for *intent fidelity*: do these scenarios deliver the outcome in `prd.md`?
- **Product marketer** - reads for *claims*: every line of launch copy must point at a scenario id here.
- **Engineer** - reads for *tests*: scenarios are the acceptance suite and seed the TDD red→green cycle.
- **QA** - reads for *coverage*: which scenarios are exercised, which edges are not.
- **Designer** - UI behaviour authored in `ui-contract.md` flows in here as scenarios.

---

## On a Hotfix, the reproduction is the spec

This file was not written before the work - on Hotfix it cannot be, the bug is
the starting point. The sequence was: a failing regression test
(`test_empty_filter_object_does_not_crash`) was written first and watched fail
(`evidence/red.json`) - that *was* define. At ship, follow-up FU-001 promoted
that test into the proper Given/When/Then below, so the spec reads like every
other Compass spec and the next person finds it where they expect it.

---

## Intent links

| Intent id | Source | Statement |
|---|---|---|
| INT-1 | The production incident | `/search` must handle an empty `filter` object the way it handles an absent filter - return results, never a 500. |

---

## Scenario group A - Filter compilation robustness

**Independence note:** single scenario, single group - a hotfix is one focused change.

### Scenario: Search with an empty filter object returns results, does not crash
<!-- traceability id: TRC-001 · serves: INT-1 -->

```gherkin
Scenario: Search with an empty filter object returns results, does not crash
  Given the search index contains 12 documents
  When a client searches with query "report" and filter {}
  Then the response status is 200
  And the empty filter is treated as "no filtering applied"
  And all matching documents are returned
```

---

## Coverage ledger

| Traceability id | Serves intent | Has a failing test (Build) | Passes as acceptance (Verify) |
|---|---|---|---|
| TRC-001 | INT-1 | [x] | [x] |
