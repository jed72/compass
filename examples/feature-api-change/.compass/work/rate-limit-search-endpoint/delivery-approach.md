# Delivery approach - rate-limit-search-endpoint

> **Issue:** Add per-client rate limiting to the public `/search` endpoint - it has no limit today and one client's bulk job degraded latency for everyone last week.
> **Triaged:** 2026-04-21 by D. Mensah (engineer) · **Revision:** 1
> **Reference shape:** Standard

---

## 1. The four dimension assessment

| Dimension | Value | One-line justification |
|---|---|---|
| **Risk:** | contained | One endpoint and a new middleware. If the limit is wrong it returns a 429 too eagerly or too late - annoying, recoverable, observable; it does not corrupt or lose anything. |
| **Familiarity:** | brownfield-mapped | The request pipeline and middleware chain are documented and already have a test harness; this adds one well-understood link to a known chain. |
| **Size:** | standard | A new middleware, a config addition, and a route wiring change - several files, a couple of design decisions (storage backend, window algorithm), about two days. |
| **Goal & role** | engineer | An engineer hardening a public endpoint after an incident review. No brief - the incident write-up is the intent. |

**Domain tags (`labels:`):** none - the limiter reads a client id that auth already resolved; it does not itself touch auth, payments, personal data, or migrations.

---

## 2. The composed candidate approach

Candidate approach: **Standard**, with no deviations from its reference shape.

Candidate review dimensions: correctness, governance, traceability, regression, clarity, and security *scaled to risk* - `contained` means a focused security pass on the new reject path, not a full adversarial sweep.

---

## 3. Routing guardrails that fired

No routing guardrail fired. Candidate route stands.

`compass approach evaluate` confirmed it: no floor (risk is `contained` not `critical`; `touches` is empty so RP-FLOOR-003 does not match), no cap, no role rule (role is `engineer`). The route is the unmodified Standard shape.

---

## 4. The final approach

### 4a. Per-phase weight

| Phase | Weight | Notes |
|---|---|---|
| Triage | Full | This document. |
| Define | Small feature set | Five scenarios - happy path, the over-limit reject, the retry-after contract, the window reset, per-client isolation. See `acceptance-criteria.md`. |
| Refine | Light pass | Two ambiguities surfaced and resolved; spec QA'd against itself and governance. See `requirements-review.md`. |
| Plan | Real `design.md` | Two design decisions recorded (storage backend, window algorithm); governance check run. |
| Breakdown | Skipped (solo) | The work units share surface - see `design.md` §4. Solo on the current branch. |
| Build | Full TDD | Five scenarios, red→green→refactor each. Test surface scaled to `contained`. |
| Verify | Full - one gate | Six review dimensions, all evidenced in `verification-report.md`. |
| Ship | Full | Commit on the current branch, regression run, living docs updated, one devlog entry. |

### 4b. Gate set

- Number of gates: the Standard gate at Verify (Standard's mid-Build checkpoint was a quick spec re-read against `design.md` §4 - logged in `devlog.md`, no separate artifact).
- Review dimensions applied: correctness, governance, traceability, regression, clarity, security.
- Immovable gates stapled on: verify.correctness, verify.governance, verify.traceability. `verify.regression` is part of Standard's own shape. No `verify.claims` - no marketer in play.

### 4c. Swarm topology

- Topology: solo
- Stream count: n/a - Plan §4 found the three work units share the middleware surface; splitting them would create a merge conflict, not parallelism.
- Orchestrator agent: n/a (solo)

---

## 5. The de-scope ledger

| Phase / check | Action | Safe to skip / collapse because… |
|---|---|---|
| Breakdown | skipped | The three work units (middleware, route wiring, config) all touch `rate_limit.py` or depend on it. They are not independent - disjoint code is one of the two independence tests and it fails. Solo is correct, not a shortcut. |
| Dedicated orchestrator agent | skipped | Standing Standard de-scope: at solo/≤3 streams the lead builder integrates; a separate orchestrator is overhead. |

Note what is *not* in this ledger: refine is not skipped - a feature's spec is a feature set, and there was real ambiguity to resolve (`requirements-review.md`). The requirements review is *light*, never absent, on a feature.

---

## 6. Outstanding follow-ups

- [x] None outstanding. Standard runs its pipeline in order; it borrows no ceremony from the front.

---

## 7. Human overrides

No human overrides. Route confirmed as composed.

---

## 8. Confirmation

- [x] Route presented to the invoker and confirmed.
- [x] Every dimension in §1 has a justification.
- [x] Every skipped phase in §5 has a "safe to skip because…" line.
- [x] Not a spike - no `.spike` marker needed.
- [x] `devlog.md` opened with the triage entry.

Next stage: **define** (`/compass:define`).
