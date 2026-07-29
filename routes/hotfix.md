# Route - Hotfix

> Something is broken in production now. Reproduce first, fix fast, backfill
> properly. The clock is real - the default guardrails still aren't negotiable.

## The Needle composes toward Hotfix when

- there is a live defect with user impact happening *now*, **and**
- magnitude is `atomic` or `small` (a large fix is an incident, not a hotfix -
  route it Expedition under incident command), **and**
- blast radius is `critical` or high `cross-cutting` (that is *why* it's
  urgent), **and**
- role is typically `engineer`, often paired with `qa`.

Hotfix is the one route defined by *urgency* rather than by the magnitude /
blast-radius / terrain composition. The Needle still scores all four
dimensions - they shape the backfill - but urgency is what selects the shape.

## Per-phase weight

| Phase | Weight on Hotfix |
|---|---|
| Frame | Fast but real. `route.md` is written - even under time pressure, the audit trail starts here. |
| Specify | **Reproduce-first.** The spec *is* a failing regression test that reproduces the defect. Writing that test is non-negotiable and comes before any fix - it is simultaneously the BDD scenario and the TDD red. |
| Clarify | Collapsed - the reproduction *is* the clarification. The bug is unambiguous once it reproduces. |
| Plan | Collapsed to a one-line root-cause note in `route.md`. (Root cause, not symptom - a hotfix that treats the symptom owes a follow-up Expedition.) |
| Distribute | Skipped. Solo. Speed and a single clear owner beat parallelism here. |
| Build | Expedited TDD: the reproduction test is already red; make it green with the smallest correct change; refactor only if the refactor itself is low-risk. |
| Verify | **All Verify gates, no exceptions.** This is the phase Hotfix does *not* compress. The reproduction test passes, the full suite passes, regression is clean, output is pasted. |
| Land | Ship the fix. Then the **mandatory backfill** - see below. The task is not closed until the backfill is done. |

## Gate set

Full Verify gate. Review dimensions: `correctness`, `governance`,
`traceability`, `regression`, `security`. `clarity` is deferred to the
backfill. The gate is *not* lighter than Standard's - Hotfix compresses the
phases *before* Verify, never Verify itself.

## Swarm topology

Solo. No worktree.

## The mandatory backfill - Hotfix's defining obligation

Hotfix borrows speed from the front of the pipeline and **pays it back at the
end**. Before the task closes, Land requires:

1. **`route.md` completed** - the dimension readings and root-cause note,
   filled in properly, not just the urgent stub.
2. **A real scenario** - the reproduction test is promoted into a proper
   Given/When/Then scenario in `spec.feature.md`, traceable to the defect.
3. **A root-cause line in the devlog** - what allowed this defect to exist,
   and whether a follow-up task is owed (e.g. "the missing scenario that would
   have caught this is now filed as task #…").

A Hotfix with an unpaid backfill is an open task, full stop. `/compass:status`
flags it; `/compass:land` refuses to close it.

## Hotfix may NOT

- Skip the reproduction test. "Fix first, test later" is not a Hotfix - it is
  the thing Hotfix exists to prevent. Guardrail G1 (tested before it lands) is
  not negotiable, and the S2 red-before-green strategy is how Hotfix meets it
  - even at 3am.
- Compress the Verify gate. The phases before Verify are compressed; Verify is
  not. A fast fix that isn't verified is just a faster outage.
- Close without the backfill. Borrowed ceremony is a debt with a due date, and
  the due date is "before the task closes."
- Be used for a fix that is actually `standard`+ in magnitude. That is an
  incident: route it Expedition, put someone in incident command, and use the
  swarm if it helps.
