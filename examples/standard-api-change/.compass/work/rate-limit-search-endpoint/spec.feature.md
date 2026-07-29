# Spec - rate-limit-search-endpoint

> **Phase:** Specify · **Last updated:** 2026-04-22 · **Owning agent:** spec-author
> **Terrain:** brownfield-mapped - the middleware chain is known; these are new scenarios for a new link in it, no blueprint-distillation needed.

## How each role reads this file

- **Product owner / manager** - reads for *intent fidelity*: do these scenarios deliver the outcome in `brief.md`?
- **Product marketer** - reads for *claims*: every line of launch copy must point at a scenario id here.
- **Engineer** - reads for *tests*: scenarios are the acceptance suite and seed the TDD red→green cycle.
- **QA** - reads for *coverage*: which scenarios are exercised, which edges are not.
- **Designer** - UI behaviour authored in `ui-contract.md` flows in here as scenarios.

---

## Intent links

| Intent id | Source | Statement |
|---|---|---|
| INT-1 | The incident write-up | A single client must not be able to degrade `/search` latency for everyone else; each client gets a fair, bounded share of the endpoint. |
| INT-2 | The incident write-up | When a client is limited, it must be able to recover on its own - the response has to tell it how long to wait. |

---

## Scenario group A - Rate limiting behaviour

**Independence note:** single group. All five scenarios exercise the one new middleware; per `plan.md` §4 they share code surface and are built as one solo stream.

### Scenario: Requests under the limit pass through unchanged
<!-- traceability id: SCN-001 · serves: INT-1 -->

```gherkin
Scenario: Requests under the limit pass through unchanged
  Given the limit for /search is 100 requests per minute
  And client "acme" has made 40 requests in the current window
  When client "acme" sends another /search request
  Then the request is handled normally
  And the response status is 200
```

### Scenario: The request over the limit is rejected with 429
<!-- traceability id: SCN-002 · serves: INT-1 -->

```gherkin
Scenario: The request over the limit is rejected with 429
  Given the limit for /search is 100 requests per minute
  And client "acme" has made 100 requests in the current window
  When client "acme" sends another /search request
  Then the response status is 429
  And the search query is not executed
```

### Scenario: A 429 response tells the client when to retry
<!-- traceability id: SCN-003 · serves: INT-2 -->

```gherkin
Scenario: A 429 response tells the client when to retry
  Given client "acme" has been rejected with a 429
  When the client reads the response
  Then the response carries a Retry-After header
  And the header value is the seconds remaining in the current window
```

### Scenario: The window resets and the client can call again
<!-- traceability id: SCN-004 · serves: INT-1 -->

```gherkin
Scenario: The window resets and the client can call again
  Given client "acme" was rejected with a 429 at the end of a window
  When the rate-limit window rolls over
  And client "acme" sends a /search request
  Then the request is handled normally
  And the response status is 200
```

### Scenario: Two clients have independent limits
<!-- traceability id: SCN-005 · serves: INT-1 -->

```gherkin
Scenario: Two clients have independent limits
  Given the limit for /search is 100 requests per minute
  And client "acme" has made 100 requests in the current window
  When client "globex" sends its first /search request
  Then client "globex" is handled normally
  And client "globex" receives a 200
```

---

## Failure-mode scenarios

The failure mode that mattered here - the over-limit case - is SCN-002, kept in
group A because it is the core behaviour, not an afterthought. `contained`
blast radius does not call for adversarial inputs; the missing-client-id edge
was raised in Clarify and resolved as a config default (see
`clarifications.md` Q2), not a separate scenario.

---

## Coverage ledger

| Traceability id | Serves intent | Has a failing test (Build) | Passes as acceptance (Verify) |
|---|---|---|---|
| SCN-001 | INT-1 | [x] | [x] |
| SCN-002 | INT-1 | [x] | [x] |
| SCN-003 | INT-2 | [x] | [x] |
| SCN-004 | INT-1 | [x] | [x] |
| SCN-005 | INT-1 | [x] | [x] |
