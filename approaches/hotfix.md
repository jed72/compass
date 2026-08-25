# Delivery approach - Hotfix

> Something is broken in production now. Reproduce first, fix fast, follow-up
> properly. The clock is real - the default guardrails still aren't negotiable.

## Assess composes toward Hotfix when

- there is a live defect with user impact happening *now*, **and**
- size is `atomic` or `small` (a large fix is an incident, not a hotfix -
  route it initiative under incident command), **and**
- risk is `critical` or high `cross-cutting` (that is *why* it's
  urgent), **and**
- role is typically `engineer`, often paired with `qa`.

Hotfix is the one route defined by *urgency* rather than by the size /
risk / familiarity composition. Triage still scores all four
dimensions - they shape the follow-up - but urgency is what selects the shape.

## Per-phase weight

| Phase | Weight on Hotfix |
|---|---|
| Triage | Fast but real. `delivery-approach.md` is written - even under time pressure, the audit trail starts here. |
| Define | **Reproduce-first.** The spec *is* a failing regression test that reproduces the defect. Writing that test is non-negotiable and comes before any fix - it is simultaneously the BDD scenario and the TDD red. |
| Refine | Collapsed - the reproduction *is* the clarification. The bug is unambiguous once it reproduces. |
| Plan | Collapsed to a one-line root-cause note in `delivery-approach.md`. (Root cause, not symptom - a hotfix that treats the symptom owes a follow-up initiative.) |
| Breakdown | Skipped. Solo. Speed and a single clear owner beat parallelism here. |
| Build | Expedited TDD: the reproduction test is already red; make it green with the smallest correct change; refactor only if the refactor itself is low-risk. |
| Verify | **All Verify gates, no exceptions.** This is the phase Hotfix does *not* compress. The reproduction test passes, the full suite passes, regression is clean, output is pasted. |
| Ship | Ship the fix. Then the **mandatory follow-up** - see below. The issue is not closed until the follow-up is done. |

## Gate set

Full Verify gate. Review dimensions: `correctness`, `governance`,
`traceability`, `regression`, `security`. `clarity` is deferred to the
follow-up. The gate is *not* lighter than Standard's - Hotfix compresses the
phases *before* Verify, never Verify itself.

## Swarm topology

Solo. No worktree.

## The mandatory follow-up - Hotfix's defining obligation

Hotfix borrows speed from the front of the pipeline and **pays it back at the
end**. Before the issue closes, shipping requires:

1. **`delivery-approach.md` completed** - the dimension assessment and root-cause note,
   filled in properly, not just the urgent stub.
2. **A real scenario** - the reproduction test is promoted into a proper
   Given/When/Then scenario in `acceptance-criteria.md`, traceable to the defect.
3. **A root-cause line in the devlog** - what allowed this defect to exist,
   and whether a follow-up issue is owed (e.g. "the missing scenario that would
   have caught this is now filed as issue #…").

A Hotfix with an unpaid follow-up is an open issue, full stop. `/compass:status`
flags it; `/compass:ship` refuses to close it.

## Hotfix may NOT

- Skip the reproduction test. "Fix first, test later" is not a Hotfix - it is
  the thing a hotfix exists to prevent. The tested-before-ship guardrail is
  not negotiable, and the red-before-green TDD strategy is how Hotfix meets it
  - even at 3am.
- Compress the Verify gate. The phases before Verify are compressed; Verify is
  not. A fast fix that isn't verified is just a faster outage.
- Close without the follow-up. Borrowed ceremony is a debt with a due date, and
  the due date is "before the issue closes."
- Be used for a fix that is actually `standard`+ in size. That is an
  incident: route it initiative, put someone in incident command, and use the
  swarm if it helps.
