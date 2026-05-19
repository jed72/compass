# Clarifications — notifications-subsystem

> **Phase:** Clarify · **Date:** 2026-03-06 · **Owning agent:** spec-author
> **Clarify weight (from route.md):** full pass

---

## Self-QA of the spec

- Every scenario has an observable `Then` — checked across all six. SCN-001's
  "within 5 seconds" is observable via the test harness clock, not a vibe.
- SCN-002 and SCN-005 do not contradict: SCN-005's "default is deliver" and
  SCN-002's idempotency are orthogonal — one is about *whether*, the other
  about *how many times*.
- No scenario reaches into another group's surface in its `Then`. Group A
  scenarios never assert on preference state; group B scenarios never assert on
  the durable store internals. This is what makes the two-stream split honest.

## Governance QA of the spec

- No scenario crosses a guardrail. The work touches `migrations` — that is
  exactly why the route is Expedition and why G5 applies — but no *scenario*
  describes an irreversible action a user takes; the migration is
  infrastructure, signed off at Land.
- No scenario pursues a `brief.md` non-goal: nothing here touches email/push/SMS,
  digests, or an admin console. Checked explicitly against the Non-goals list.
- The "depth for existing users" product strategy is honoured — category-level
  preferences for the existing event types, not a broad new surface.

---

## Ambiguity ledger

### Q1 — What is the security-override mechanism: a flag or a category?

- **Question:** SCN-006 says a muted "security" category still delivers. But
  *how* is "this notification overrides mute" decided — a per-notification
  boolean the producer sets, or membership in a fixed "security" category?
- **Resolution:** A fixed `security` category, not a per-notification flag. The
  brief's pre-mortem named the failure mode directly — a per-notification flag
  drifts ("everything claims to be security and mute becomes meaningless"). A
  small, fixed category is auditable. SCN-006's Given was tightened to "muted
  every category, including 'security'" to make the category model explicit.
- **Decided by:** S. Voss (product owner), with R. Okafor (engineer).
- **Governance reference:** `brief.md` Internal FAQ pre-mortem — the
  security-override risk; product strategy "make the safe path the easy path".
- **Spec change:** SCN-006 Given edited.
- **Status:** resolved

### Q2 — Does "delivered once" (SCN-002) mean once-ever or once-per-window?

- **Question:** SCN-002's idempotency — is a duplicate suppressed forever, or
  only within some dedup window?
- **Resolution:** Once-ever, keyed on a producer-supplied idempotency key
  stored with the notification. v1 has no batching/digest concept (a brief
  non-goal), so there is no window to scope dedup to — once-ever is both
  simpler and correct for the v1 cut.
- **Decided by:** R. Okafor (engineer).
- **Governance reference:** `brief.md` Non-goals (no digest/batching);
  engineering strategy S3 (simplest thing that works).
- **Spec change:** no spec change — SCN-002 already says "exactly one"; this
  records *how*, captured in `plan.md` DD-2.
- **Status:** resolved

### Q3 — "Within 5 seconds" (SCN-001) — is that a hard SLA or an illustrative bound?

- **Question:** Is the 5s in SCN-001 a contractual latency target the system
  must guarantee, or a reasonable upper bound for the acceptance test?
- **Resolution:** An acceptance-test bound, not an SLA. The brief says "within
  seconds", not a number; 5s is a generous, testable ceiling that proves
  "near-real-time" without committing the team to an SLA it has not load-tested.
  If a real SLA is wanted later, that is a new task with load evidence.
- **Decided by:** S. Voss (product owner).
- **Governance reference:** n/a — scoping clarification.
- **Spec change:** no spec change; the intent of the bound is recorded here so
  a future reader does not mistake it for an SLA.
- **Status:** resolved

---

## Gate

- [x] No ambiguity left `open` — Q1, Q2, Q3 all resolved.
- [x] `spec.feature.md` updated to reflect every resolution (SCN-006 Given tightened; Q2/Q3 needed no scenario change, recorded here and in `plan.md`).
- [x] Non-engineering roles in play have reviewed — the product owner (S. Voss)
  reviewed at this phase, as Expedition requires, and signed the intent-fidelity
  check at the foot of `brief.md`.

### Definition of Ready

- [x] **Problem traces up** — every scenario serves INT-1, INT-2, or INT-3, all
      drawn from `brief.md`. The intent-fidelity check in `brief.md` confirms
      every success signal maps to a scenario.
- [x] **Behaviour is Given/When/Then** — all six scenarios have an observable
      `Then`; SCN-001's "5 seconds" was confirmed testable, not a wish (Q3).
- [x] **Traceability ids assigned** — SCN-001…SCN-006, present in
      `spec.feature.md` and `task.yml`.
- [x] **Affected surface named** — `route.md` and the upcoming `plan.md` /
      `distribution-map.md` name the module tree, the API surface, and
      `migrations/0042`.
- [x] **No open questions** — the ambiguity ledger is fully resolved.
- [x] **Route still fits** — nothing in Clarify changed a reading. Expedition
      still fits; the `migrations` tag (and so RG-FLOOR-003) still holds.

Next phase: **Plan** (`/compass:plan`) — unblocked: RG-ROLE-002's intent-fidelity check passed (`brief.md` foot, 2026-03-06).
