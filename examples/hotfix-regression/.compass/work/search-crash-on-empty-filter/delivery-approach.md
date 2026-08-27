# Delivery approach - search-crash-on-empty-filter

> **Issue:** `/search` returns a 500 for any request whose `filter` is an empty object `{}` - a mobile-client release started sending that shape this morning and is crashing for every user on the new build.
> **Triaged:** 2026-05-11 by P. Adeyemi (engineer) · **Revision:** 1
> **Reference shape:** Hotfix

<!-- This delivery-approach.md was written in two passes: an urgent stub at 08:50 to start
     the audit trail, then completed properly at ship as follow-up FU-002. What
     you are reading is the completed version. -->

---

## 1. The four dimension assessment

| Dimension | Value | One-line justification |
|---|---|---|
| **Risk:** | cross-cutting | `/search` is on the home screen of every client. The crash is not isolated to one feature - it takes out the primary surface. Not `critical` (no data loss, no auth/payment exposure), but wide. |
| **Familiarity:** | brownfield-mapped | The filter-compiler path is known and has a test module (`tests/api/test_search.py`); the bug is a missing guard in mapped code, not unknown territory. |
| **Size:** | small | The fix is a one-branch null/empty guard in `filter_compiler.py`. A *large* fix here would have meant routing this initiative under incident command - it is genuinely small. |
| **Goal & role** | engineer | An engineer responding to a live production crash. Often paired with QA on Hotfix; here QA reviewed the Verify gate. |

**Domain tags (`labels:`):** none - the filter compiler touches no auth, payments, personal data, or migrations.

---

## 2. The composed candidate approach

Candidate approach: **Hotfix**, with no deviations from its reference shape.

Hotfix is selected by **urgency**, not by the size/blast/familiarity
composition - `urgency: live-defect` with `size: small` matched routing
strategy RP-SHAPE-002 ("a live defect, small enough to reproduce-and-fix
fast"). The Needle still scored all four dimensions; they shape the follow-up
and confirm this is a hotfix and not an incident.

Candidate review dimensions: correctness, governance, traceability, regression,
security. `clarity` is deferred to the follow-up - that is Hotfix's one
permitted Verify deferral, and it is *deferred*, not dropped.

---

## 3. Routing guardrails that fired

No routing guardrail fired. Candidate route stands.

`compass approach evaluate` confirmed it. The reading that *did not* fire is worth
recording: risk is `cross-cutting`, **not `critical`** - had it been
`critical`, RP-FLOOR-001 would have raised this to initiative ("critical
changes coordinate, or they break things quietly"), because a critical-blast
production defect is an incident with incident command, not a solo hotfix. The
Needle held the line at `cross-cutting` deliberately: wide, but no data or
trust at stake.

---

## 4. The final approach

### 4a. Per-phase weight

| Phase | Weight | Notes |
|---|---|---|
| Assess | Light | Urgent stub at 08:50, completed at ship (FU-002). Even under the clock the audit trail starts here. |
| Define | Reproduce-first | The spec *is* the failing regression test - `test_empty_filter_object_does_not_crash`, written RED before any fix. |
| Refine | Collapsed | The reproduction is the clarification - once the test reproduces, the bug is unambiguous. |
| Plan | Collapsed | One-line root-cause note below. |
| Breakdown | Skipped | Solo. One clear owner beats coordination here. |
| Build | Expedited | The reproduction test is already red; make it green with the smallest correct guard; no refactor (the branch was already minimal). |
| Verify | Full | **Not compressed.** All five Hotfix gates, evidence pasted - see `verification-report.md`. |
| Ship | Full + follow-up | Ship the fix, then pay the mandatory follow-up - §6. |

### 4b. Gate set

- Number of gates: full Verify gate - five review dimensions.
- Review dimensions applied: correctness, governance, traceability, regression, security. `clarity` deferred to the follow-up (FU-001's promoted scenario carries the readable record).
- Immovable gates stapled on: verify.correctness, verify.governance, verify.traceability - all already in Hotfix's shape. `verify.regression` is part of Hotfix's own set: a fast fix that breaks something else is just a faster outage.

### 4c. Multiagent orchestration

- Orchestration: solo
- Subtask count: n/a (solo)
- Orchestrator agent: n/a

---

## 5. The de-scope ledger

| Phase / check | Action | Safe to skip / collapse because… |
|---|---|---|
| Refine | collapsed | The reproduction test *is* the clarification - a bug that reliably reproduces is unambiguous. Not skipped silently: the reproduction does refine's job. |
| Plan | collapsed to a root-cause note | Size `small`, mapped familiarity - there is no design decision, only a missing guard to add. The root cause is named below so this is a *decision*, not a skip. |
| Breakdown | skipped | One subtask, one owner. Parallelism on a hotfix is coordination cost with no payoff. |
| `clarity` review dimension | **deferred, not dropped** | Hotfix defers `clarity` to the follow-up: FU-001 promotes the reproduction into a readable Given/When/Then scenario, which is where the clarity record lands. Deferred process weight is outstanding process weight - see §6. |

**One-line edit note (Hotfix collapsed Plan - root cause, not symptom):**
`filter_compiler.py` calls `.items()` on the `filter` value without first
checking it is non-empty; an empty object `{}` is falsy-but-not-None, slipped
past the `if filter is not None` guard, and the compiler produced a `None`
WHERE-clause that the query builder dereferenced. Root cause: the guard tested
`is not None` when it needed to test "has at least one key". The fix tests the
real condition. (This is the root cause, not the symptom - the symptom was the
500; treating only the symptom would owe a follow-up initiative.)

---

## 6. Outstanding follow-ups

Hotfix borrows speed from the front of the pipeline and **pays it back at
Ship**. All three are recorded in `manifest.yml` under `follow-ups:` and `compass
check` fails the issue while any is `outstanding`. As of ship, all are **paid**:

- [x] **FU-001** - the reproduction test promoted into a proper Given/When/Then
  scenario in `acceptance-criteria.md` (TRC-001), traceable to the defect. *Resolved 2026-05-11 11:20.*
- [x] **FU-002** - this `delivery-approach.md` completed properly: the four dimension
  assessment with justifications and the root-cause note, not the urgent stub. *Resolved 2026-05-11 11:35.*
- [x] **FU-003** - root-cause line in `devlog.md`, and the follow-up issue filed
  for the gap class (the missing empty-collection scenario that would have
  caught this). *Resolved 2026-05-11 11:45 - follow-up issue filed as issue `audit-search-input-edge-scenarios`.*

---

## 7. Human overrides

No human overrides. Route confirmed as composed.

---

## 8. Confirmation

- [x] Route presented to the invoker and confirmed.
- [x] Every dimension in §1 has a justification (completed at ship - FU-002).
- [x] Every collapsed phase in §5 has a "safe to skip because…" line.
- [x] Not a spike - no `.spike` marker needed.
- [x] `devlog.md` opened with the triage entry.

Next stage: **define** (reproduce-first) - `/compass:define`.
