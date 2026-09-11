# Delivery approach - pdf-export-library-viability

> **Issue:** Customers want to export reports as PDF. Before we plan that feature: is `weasyprint` a viable engine for our report layouts, or do we need a heavier tool? Timeboxed investigation.
> **Triaged:** 2026-05-12 by N. Brandt (engineer) · **Revision:** 1
> **Reference shape:** Spike

<!-- On a spike triage also writes a `.spike` marker file in this
     issue directory, so the pre-tool hook knows to suspend the TDD strategy.
     That marker is present alongside this delivery-approach.md. -->

---

## 1. The four dimension assessment

| Dimension | Value | One-line justification |
|---|---|---|
| **Risk:** | contained | Nothing ships from this. The exploration code is throwaway on a scratch branch. Worst case if the spike is wrong: we learn the wrong thing and re-spike - no production impact. |
| **Familiarity:** | greenfield | There is no PDF export today and no prior art in the codebase. There is nothing to map - the spike *is* the mapping of this familiarity. |
| **Size:** | small | A timeboxed two-day investigation: render three representative report layouts, check fidelity, measure speed and memory. Not a large effort - it is a *bounded* one. |
| **Goal & role** | engineer / **exploration** | An engineer who cannot yet frame the real feature - the open question ("is this library viable?") has to be answered before a delivery delivery approach can be composed. Exploration intent is what selects Spike. |

**Domain tags (`labels:`):** none - and this is load-bearing for a spike. A
Spike may not touch anything irreversible (auth, payments, personal-data,
migrations); those are floored to initiative regardless of intent. This
question can be answered entirely with throwaway rendering code, so Spike is
legitimately available.

---

## 2. The composed candidate approach

Candidate approach: **Spike**, with no deviations from its reference shape.

Spike is selected by **intent**, the way Hotfix is selected by urgency.
`intent: exploration` matched routing strategy RP-SHAPE-001 ("exploration
intent - cannot frame for delivery yet"). The Needle still scored the other
three dimensions - they confirm the work is bounded and touches nothing
irreversible, which is what makes Spike *safe* to use here.

Candidate review dimensions: none of the delivery dimensions. A Spike runs no
`correctness` / `governance` / `traceability` review - it has one Conclude
gate (§4b).

---

## 3. Routing guardrails that fired

No routing guardrail fired. Candidate route stands.

The guardrails that *could* have fired and did not, both worth recording:
- **RP-FLOOR-003** (`labels_any: [auth, payments, personal-data, migrations]`)
  did not fire - `touches:` is empty. Had this question required touching any
  of those, it would not be a spike: the floor would force initiative, because
  you cannot "explore" an irreversible change.
- **RP-FLOOR-002** (`familiarity: brownfield-unmapped`) did not fire - familiarity is
  `greenfield`, not unmapped brownfield. (On a brownfield-unmapped spike it
  *would* fire and force a full define with behaviour-mapping, even on a
  Spike - a useful thing to know the policy does.)

---

## 4. The final approach

### 4a. Per-phase weight

| Phase | Weight | Notes |
|---|---|---|
| Assess | Light but real | This document. Even a spike is accountable - it records the question and the timebox. |
| Define | Collapsed into the question | The spike's "spec" is the question in §5, not acceptance criteria for code. |
| Refine | Skipped | Nothing to QA - the behaviour is the unknown, and discovering it is the point. |
| Plan | Collapsed to a timebox | "Explore, with a clock" - §5. |
| Breakdown | Skipped | Solo. One person, one question. |
| Build | = **Explore** | Write rendering code freely to answer the question. **TDD strategy (`S2`) suspended** - the pre-tool hook is route-aware and does not block edits here. Code is assumed throwaway. |
| Verify | = **Conclude** | Not a test gate - a findings check: did we answer the question? Output is a written conclusion (in `devlog.md`), not a passing suite. |
| Ship | = **Graduate or Discard** | Never "merge to main." Either the findings feed a fresh `/compass:assess` for real delivery work, or the spike is discarded with its learnings recorded. |

### 4b. Gate set

- Number of gates that matter: 1 - the Conclude gate (`spike.conclude`). It
  asks one thing: *is the question answered, and is the answer written down?*
- Review dimensions applied: none. A Spike runs no delivery review dimensions -
  it ships nothing, so there is nothing to review for correctness or
  traceability. Guardrails `G1`–`G3` are not skipped - they are **deferred to
  graduation**, where they apply in full to any code that is kept.
- A note on the immovable gates: `compass approach evaluate` staples the policy's
  `immovable_gates` (`verify.correctness`, `verify.governance`,
  `verify.traceability`) onto *every* route's gate set, including this one -
  the policy comment says they are "for any DELIVERY approach", but the CLI
  applies them unconditionally. On a spike they are inert: `manifest.yml` carries
  them at `status: pending` forever, because a spike never produces anything
  for them to be about. Only `spike.conclude` is ever `pass`. This is recorded,
  not hidden - see the comment in `manifest.yml`.

### 4c. Multiagent orchestration

- Orchestration: solo
- Subtask count: n/a (solo)
- Orchestrator agent: n/a

---

## 5. The de-scope ledger

| Phase / check | Action | Safe to skip / collapse because… |
|---|---|---|
| Define | collapsed to a question | A spike has no acceptance criteria - its output is knowledge, not behaviour. **Nothing lands from a spike.** |
| Refine | skipped | Nothing to QA against - the unknown is the point. **Nothing lands from a spike.** |
| Plan | collapsed to a timebox | The plan for exploration is "explore, with a clock." **Nothing lands from a spike.** |
| Breakdown | skipped | One person, one question. **Nothing lands from a spike.** |
| Build - TDD strategy | suspended | Red-before-green is the wrong discipline for throwaway learning code. `G1` is not skipped - it is **deferred to graduation**, where it applies in full. **Nothing lands from a spike.** |

Every justification rests on the same fact, repeated deliberately: **nothing
lands from a spike.** The de-scopes are safe because the delivery approach has no delivery
output to protect.

**Spike question + timebox:**
- **Question:** Can `weasyprint` render our three most layout-demanding report
  templates (the financial summary, the multi-page audit log, the chart-heavy
  dashboard export) with acceptable fidelity, speed, and memory - or do we need
  a heavier headless-browser engine?
- **What a useful answer looks like:** a clear "viable" / "not viable" /
  "viable with caveats", each of the three templates rated on fidelity, plus
  rough speed and peak-memory numbers - enough to *frame* the real feature, or
  to rule this library out.
- **Timebox:** 2 days. When the clock runs out: conclude with what is known, or
  re-frame the spike with a new timebox and a written reason. No silent
  overrun.

---

## 6. Outstanding follow-ups

- [x] None outstanding. A Spike owes nothing - it borrows no process weight because it lands
  nothing. Its exit is graduate-or-discard, not a follow-up. (Contrast Hotfix,
  which always owes one: Hotfix *ships* and borrows from the front of the
  pipeline; a spike ships nothing, so there is nothing to repay.)

---

## 7. Human overrides

No human overrides. Route confirmed as composed.

---

## 8. Confirmation

- [x] Route presented to the invoker and confirmed.
- [x] Every dimension in §1 has a justification.
- [x] Every skipped/collapsed phase in §5 has a "safe to skip because…" line (all the same fact: nothing lands).
- [x] On a spike: the `.spike` marker file is written to the issue directory.
- [x] `devlog.md` opened with the triage entry.

Next stage: **explore** (`/compass:implement` on a spike).
