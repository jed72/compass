# Spec - fix-timeout-error-message

> **Phase:** Specify · **Last updated:** 2026-05-04 · **Owning agent:** spec-author
> **Familiarity:** brownfield-mapped - the timeout branch already exists; this is one scenario for its corrected behaviour, not a discovery.

## How each role reads this file

- **Product owner / manager** - reads for *intent fidelity*: do these scenarios deliver the outcome in `prd.md`?
- **Product marketer** - reads for *claims*: every line of launch copy must point at a scenario id here.
- **Engineer** - reads for *tests*: scenarios are the acceptance suite and seed the TDD red→green cycle.
- **QA** - reads for *coverage*: which scenarios are exercised, which edges are not.
- **Designer** - UI behaviour authored in `ui-contract.md` flows in here as scenarios.

---

## Intent links

| Intent id | Source | Statement |
|---|---|---|
| INT-1 | The issue description | When an upload times out, the user should be told the real cause (the file exceeds the size limit) so they can act, instead of being told to "try again later". |

---

## Scenario group A - Timeout error messaging

**Independence note:** single group, no parallelism expected - the change is one branch in one file.

### Scenario: Upload timeout reports the real cause and the real limit
<!-- traceability id: TRC-001 · serves: INT-1 -->

```gherkin
Scenario: Upload timeout reports the real cause and the real limit
  Given the upload size limit is configured to 25 MB
  When a user uploads a 60 MB file and the request times out
  Then the error message states the file exceeds the 25 MB limit
  And the message does not say "try again later"
```

---

## Coverage ledger

| Traceability id | Serves intent | Has a failing test (Build) | Passes as acceptance (Verify) |
|---|---|---|---|
| TRC-001 | INT-1 | [x] | [x] |
