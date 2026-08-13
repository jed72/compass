# Route - search-crash-on-empty-filter

> **Task:** `/search` returns a 500 for any request whose `filter` is an empty object `{}` - a mobile-client release started sending that shape this morning and is crashing for every user on the new build.
> **Framed:** 2026-05-11 by P. Adeyemi (engineer) · **Revision:** 1
> **Reference route:** Hotfix

<!-- This route.md was written in two passes: an urgent stub at 08:50 to start
     the audit trail, then completed properly at Land as backfill BF-002. What
     you are reading is the completed version. -->

---

## 1. The four dimension readings

| Dimension | Reading | One-line justification |
|---|---|---|
| **Blast radius** | cross-cutting | `/search` is on the home screen of every client. The crash is not isolated to one feature - it takes out the primary surface. Not `critical` (no data loss, no auth/payment exposure), but wide. |
| **Terrain** | brownfield-mapped | The filter-compiler path is known and has a test module (`tests/api/test_search.py`); the bug is a missing guard in mapped code, not unknown territory. |
| **Magnitude** | small | The fix is a one-branch null/empty guard in `filter_compiler.py`. A *large* fix here would have meant routing this Expedition under incident command - it is genuinely small. |
| **Intent & role** | engineer | An engineer responding to a live production crash. Often paired with QA on Hotfix; here QA reviewed the Verify gate. |

**Domain tags (`touches:`):** none - the filter compiler touches no auth, payments, personal data, or migrations.

---

## 2. The composed candidate route

Candidate route: **Hotfix**, with no deviations from its reference shape.

Hotfix is selected by **urgency**, not by the magnitude/blast/terrain
composition - `urgency: live-defect` with `magnitude: small` matched routing
strategy RS-SHAPE-002 ("a live defect, small enough to reproduce-and-fix
fast"). The Needle still scored all four dimensions; they shape the backfill
and confirm this is a hotfix and not an incident.

Candidate review dimensions: correctness, governance, traceability, regression,
security. `clarity` is deferred to the backfill - that is Hotfix's one
permitted Verify deferral, and it is *deferred*, not dropped.

---

## 3. Routing guardrails that fired

No routing guardrail fired. Candidate route stands.

`compass route evaluate` confirmed it. The reading that *did not* fire is worth
recording: blast radius is `cross-cutting`, **not `critical`** - had it been
`critical`, RG-FLOOR-001 would have raised this to Expedition ("critical
changes coordinate, or they break things quietly"), because a critical-blast
production defect is an incident with incident command, not a solo hotfix. The
Needle held the line at `cross-cutting` deliberately: wide, but no data or
trust at stake.

---

## 4. The final route

### 4a. Per-phase weight

| Phase | Weight | Notes |
|---|---|---|
| Frame | Light | Urgent stub at 08:50, completed at Land (BF-002). Even under the clock the audit trail starts here. |
| Specify | Reproduce-first | The spec *is* the failing regression test - `test_empty_filter_object_does_not_crash`, written RED before any fix. |
| Clarify | Collapsed | The reproduction is the clarification - once the test reproduces, the bug is unambiguous. |
| Plan | Collapsed | One-line root-cause note below. |
| Distribute | Skipped | Solo. One clear owner beats coordination here. |
| Build | Expedited | The reproduction test is already red; make it green with the smallest correct guard; no refactor (the branch was already minimal). |
| Verify | Full | **Not compressed.** All five Hotfix gates, evidence pasted - see `verification-report.md`. |
| Land | Full + backfill | Ship the fix, then pay the mandatory backfill - §6. |

### 4b. Gate set

- Number of gates: full Verify gate - five review dimensions.
- Review dimensions applied: correctness, governance, traceability, regression, security. `clarity` deferred to the backfill (BF-001's promoted scenario carries the readable record).
- Immovable gates stapled on: verify.correctness, verify.governance, verify.traceability - all already in Hotfix's shape. `verify.regression` is part of Hotfix's own set: a fast fix that breaks something else is just a faster outage.

### 4c. Swarm topology

- Topology: solo
- Stream count: n/a (solo)
- Orchestrator agent: n/a

---

## 5. The de-scope ledger

| Phase / check | Action | Safe to skip / collapse because… |
|---|---|---|
| Clarify | collapsed | The reproduction test *is* the clarification - a bug that reliably reproduces is unambiguous. Not skipped silently: the reproduction does Clarify's job. |
| Plan | collapsed to a root-cause note | Magnitude `small`, mapped terrain - there is no design decision, only a missing guard to add. The root cause is named below so this is a *decision*, not a skip. |
| Distribute | skipped | One stream, one owner. Parallelism on a hotfix is coordination cost with no payoff. |
| `clarity` review dimension | **deferred, not dropped** | Hotfix defers `clarity` to the backfill: BF-001 promotes the reproduction into a readable Given/When/Then scenario, which is where the clarity record lands. Deferred ceremony is owed ceremony - see §6. |

**One-line edit note (Hotfix collapsed Plan - root cause, not symptom):**
`filter_compiler.py` calls `.items()` on the `filter` value without first
checking it is non-empty; an empty object `{}` is falsy-but-not-None, slipped
past the `if filter is not None` guard, and the compiler produced a `None`
WHERE-clause that the query builder dereferenced. Root cause: the guard tested
`is not None` when it needed to test "has at least one key". The fix tests the
real condition. (This is the root cause, not the symptom - the symptom was the
500; treating only the symptom would owe a follow-up Expedition.)

---

## 6. Owed backfills

Hotfix borrows speed from the front of the pipeline and **pays it back at
Land**. All three are recorded in `task.yml` under `backfills:` and `compass
check` fails the task while any is `owed`. As of Land, all are **paid**:

- [x] **BF-001** - the reproduction test promoted into a proper Given/When/Then
  scenario in `spec.feature.md` (SCN-001), traceable to the defect. *Paid 2026-05-11 11:20.*
- [x] **BF-002** - this `route.md` completed properly: the four dimension
  readings with justifications and the root-cause note, not the urgent stub. *Paid 2026-05-11 11:35.*
- [x] **BF-003** - root-cause line in `devlog.md`, and the follow-up task filed
  for the gap class (the missing empty-collection scenario that would have
  caught this). *Paid 2026-05-11 11:45 - follow-up filed as task `audit-search-input-edge-scenarios`.*

---

## 7. Human overrides

No human overrides. Route confirmed as composed.

---

## 8. Confirmation

- [x] Route presented to the invoker and confirmed.
- [x] Every dimension in §1 has a justification (completed at Land - BF-002).
- [x] Every collapsed phase in §5 has a "safe to skip because…" line.
- [x] Not a Spike route - no `.spike` marker needed.
- [x] `devlog.md` opened with the Frame entry.

Next phase: **Specify** (reproduce-first) - `/compass:define`.
