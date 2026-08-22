# Clarifications - notifications-subsystem

> **Phase:** refine · **Date:** 2026-03-06 · **Owning agent:** spec-author
> **Requirements review weight (from delivery-approach.md):** full pass

---

## Self-QA of the spec

- Every scenario has an observable `Then` - checked across all six. TRC-001's
  "within 5 seconds" is observable via the test harness clock, not a vibe.
- TRC-002 and TRC-005 do not contradict: TRC-005's "default is deliver" and
  TRC-002's idempotency do not overlap - one is about *whether*, the other
  about *how many times*.
- No scenario reaches into another group's surface in its `Then`. Group A
  scenarios never assert on preference state; group B scenarios never assert on
  the durable store internals. This is what makes the two-stream split honest.

## Governance QA of the spec

- No scenario crosses a guardrail. The work touches `migrations` - that is
  exactly why the delivery approach is initiative and why `G5` applies - but no *scenario*
  describes an irreversible action a user takes; the migration is
  infrastructure, signed off at ship.
- No scenario pursues a `prd.md` non-goal: nothing here touches email/push/SMS,
  digests, or an admin console. Checked explicitly against the Non-goals list.
- The "depth for existing users" product strategy is honoured - category-level
  preferences for the existing event types, not a broad new surface.

---

## Ambiguity ledger

### Q1 - What is the security-override mechanism: a flag or a category?

- **Question:** TRC-006 says a muted "security" category still delivers. But
  *how* is "this notification overrides mute" decided - a per-notification
  boolean the producer sets, or membership in a fixed "security" category?
- **Resolution:** A fixed `security` category, not a per-notification flag. The
  brief's pre-mortem named the failure mode directly - a per-notification flag
  drifts ("everything claims to be security and mute becomes meaningless"). A
  small, fixed category is auditable. TRC-006's Given was tightened to "muted
  every category, including 'security'" to make the category model explicit.
- **Decided by:** S. Voss (product owner), with R. Okafor (engineer).
- **Governance reference:** `prd.md` Internal FAQ pre-mortem - the
  security-override risk; product strategy "make the safe path the easy path".
- **Spec change:** TRC-006 Given edited.
- **Status:** resolved

### Q2 - Does "delivered once" (TRC-002) mean once-ever or once-per-window?

- **Question:** TRC-002's idempotency - is a duplicate suppressed forever, or
  only within some dedup window?
- **Resolution:** Once-ever, keyed on a producer-supplied idempotency key
  stored with the notification. v1 has no batching/digest concept (a brief
  non-goal), so there is no window to scope dedup to - once-ever is both
  simpler and correct for the v1 cut.
- **Decided by:** R. Okafor (engineer).
- **Governance reference:** `prd.md` Non-goals (no digest/batching);
  engineering strategy `S3` (simplest thing that works).
- **Spec change:** no spec change - TRC-002 already says "exactly one"; this
  records *how*, captured in `design.md` DD-2.
- **Status:** resolved

### Q3 - "Within 5 seconds" (TRC-001) - is that a hard SLA or an illustrative bound?

- **Question:** Is the 5s in TRC-001 a contractual latency target the system
  must guarantee, or a reasonable upper bound for the acceptance test?
- **Resolution:** An acceptance-test bound, not an SLA. The brief says "within
  seconds", not a number; 5s is a generous, testable ceiling that proves
  "near-real-time" without committing the team to an SLA it has not load-tested.
  If a real SLA is wanted later, that is a new issue with load evidence.
- **Decided by:** S. Voss (product owner).
- **Governance reference:** n/a - scoping clarification.
- **Spec change:** no spec change; the intent of the bound is recorded here so
  a future reader does not mistake it for an SLA.
- **Status:** resolved

---

## Gate

- [x] No ambiguity left `open` - Q1, Q2, Q3 all resolved.
- [x] `acceptance-criteria.md` updated to reflect every resolution (TRC-006 Given tightened; Q2/Q3 needed no scenario change, recorded here and in `design.md`).
- [x] Non-engineering roles in play have reviewed - the product owner (S. Voss)
  reviewed at this phase, as initiative requires, and signed the intent-fidelity
  check at the foot of `prd.md`.

### Definition of Ready

- [x] **Problem traces up** - every scenario serves INT-1, INT-2, or INT-3, all
      drawn from `prd.md`. The intent-fidelity check in `prd.md` confirms
      every success signal maps to a scenario.
- [x] **Behaviour is Given/When/Then** - all six scenarios have an observable
      `Then`; TRC-001's "5 seconds" was confirmed testable, not a wish (Q3).
- [x] **Traceability ids assigned** - TRC-001…TRC-006, present in
      `acceptance-criteria.md` and `task.yml`.
- [x] **Affected surface named** - `delivery-approach.md` and the upcoming `design.md` /
      `distribution-map.md` name the module tree, the API surface, and
      `migrations/0042`.
- [x] **No open questions** - the ambiguity ledger is fully resolved.
- [x] **Route still fits** - nothing in refine changed a reading. initiative
      still fits; the `migrations` tag (and so RP-FLOOR-003) still holds.

Next stage: **design** (`/compass:design`) - unblocked: RP-ROLE-002's intent-fidelity check passed (`prd.md` foot, 2026-03-06).
