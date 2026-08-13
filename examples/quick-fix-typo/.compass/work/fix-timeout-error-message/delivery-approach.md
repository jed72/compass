# Route - fix-timeout-error-message

> **Task:** The upload timeout error tells users to "try again later" - it should name the file-size limit, which is the actual cause.
> **Framed:** 2026-05-04 by R. Okafor (engineer) · **Revision:** 1
> **Reference route:** Express

---

## 1. The four dimension readings

| Dimension | Reading | One-line justification |
|---|---|---|
| **Blast radius** | trivial | A user-facing string in one error branch. Worst case if wrong: the message is still unhelpful - no data, no behaviour, no money at risk. |
| **Terrain** | brownfield-mapped | `src/api/upload.py` is well-understood; the timeout branch and its test file already exist. |
| **Magnitude** | small | One string, one branch. The fix and its test are under twenty lines together. |
| **Intent & role** | engineer | An engineer fixing a misleading message they hit in support triage. No brief - the request is the intent. |

**Domain tags (`touches:`):** none

---

## 2. The composed candidate route

Candidate route: **Express**, with no deviations from its reference shape.

Candidate review dimensions: correctness, governance, traceability - the three Express always runs.

---

## 3. Routing guardrails that fired

No routing guardrail fired. Candidate route stands.

`compass route evaluate` confirmed it: no floor matched (blast radius is not critical, terrain is mapped, `touches` is empty), no cap applied, no role rule (the role is `engineer`).

---

## 4. The final route

### 4a. Per-phase weight

| Phase | Weight | Notes |
|---|---|---|
| Frame | Full | This document. |
| Specify | One scenario | A single Given/When/Then naming the corrected message. That scenario is the spec. |
| Clarify | Collapsed | See the de-scope ledger. |
| Plan | Collapsed | One-line edit note below. No `plan.md`. |
| Distribute | Skipped | Solo, current branch. |
| Build | Full TDD | Failing test for SCN-001 → green → no refactor needed. |
| Verify | Light | Run the new test plus the upload test module; paste output. |
| Land | Light | Commit on the current branch, one devlog entry. |

### 4b. Gate set

- Number of gates: 1 (at Verify)
- Review dimensions applied: correctness, governance, traceability
- Immovable gates stapled on: verify.correctness, verify.governance, verify.traceability - these *are* Express's whole gate set; `verify.regression` is route-scoped and Express does not run it.

### 4c. Swarm topology

- Topology: solo
- Stream count: n/a (solo)
- Orchestrator agent: n/a

---

## 5. The de-scope ledger

| Phase / check | Action | Safe to skip / collapse because… |
|---|---|---|
| Clarify | collapsed | The spec is a single scenario the Needle certified unambiguous - the corrected message is quoted verbatim in the `Then`. Nothing to QA against itself. |
| Plan | collapsed to one-liner | Magnitude `small` on mapped terrain. No design decision: there is exactly one place the string lives and one correct value for it. |
| Distribute | skipped | One stream of work. A worktree would be pure overhead. |

**One-line edit note (Express collapsed Plan):** edit the timeout branch in `src/api/upload.py` - replace the generic string with one that names the configured `MAX_UPLOAD_MB` limit.

---

## 6. Owed backfills

- [x] None owed. Express borrows no ceremony from the front of the pipeline - its de-scopes are collapses, not loans.

---

## 7. Human overrides

No human overrides. Route confirmed as composed.

---

## 8. Confirmation

- [x] Route presented to the invoker and confirmed.
- [x] Every dimension in §1 has a justification.
- [x] Every collapsed phase in §5 has a "safe to skip because…" line.
- [x] Not a Spike route - no `.spike` marker needed.
- [x] `devlog.md` opened with the Frame entry.

Next phase: **Specify** (`/compass:define`).
