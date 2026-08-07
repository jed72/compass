# Route - Spike

> You do not understand the problem well enough to frame it properly yet.
> Explore freely, learn, then graduate or discard. Nothing lands from here.

Spike is the escape hatch. Every other route assumes you know enough to state
acceptance criteria and build against them. Sometimes you do not - you are
investigating a bug whose cause is unknown, evaluating whether an approach is
even viable, learning an unfamiliar API, prototyping to feel out a design. A
framework that forces that work through a delivery-shaped pipeline is using a
sledgehammer on a nut. Spike is the route that does not.

## The Needle composes toward Spike when

- intent is **exploration** - "I need to understand this before I can frame it"
  - rather than delivery, **and**
- the work is genuinely a question, not a known change, **and**
- nothing irreversible is in scope (see "Spike may NOT" below).

Typical: root-causing a mysterious defect, a viability prototype, a timeboxed
"is this approach even sane" investigation, learning a dependency well enough
to plan real work against it.

Spike is selected by *intent*, the way Hotfix is selected by *urgency* - the
Needle still scores all four dimensions, but exploration intent is what picks
the shape.

## What is different about Spike

Spike **suspends the TDD strategy (S2)**. The pre-tool hook is route-aware and
does not block code edits on a Spike - red-before-green is the wrong
discipline for code you are writing precisely to learn something and may throw
away. Exploration is not throttled.

This is safe because of the hard rule below it: **a Spike does not land
production code.** It cannot smuggle untested code onto `main`, because the
only way a spike's code reaches production is by *graduating* - and graduating
means re-framing into a real route, where guardrails G1–G3 apply in full.

## Per-phase weight

| Phase | Weight on Spike |
|---|---|
| Frame | Light but real. `delivery-approach.md` is written - even a spike is accountable. It records the **question** and the **timebox**. |
| Specify | **Collapsed** into the question. The spike's spec is "what do we need to learn, and what would a useful answer look like?" - not acceptance criteria for code. |
| Clarify | **Skipped.** There is nothing to QA the spec against - the behaviour is the unknown, and discovering it is the point. |
| Plan | **Collapsed** to a timebox and an approach sketch in `delivery-approach.md`. |
| Distribute | **Skipped.** Solo. |
| Build | **= Explore.** Write code freely to answer the question. TDD strategy suspended; the hook does not block. Code here is assumed throwaway. |
| Verify | **= Conclude.** Not a test gate - a findings check: *did we answer the question?* The output is a written conclusion, not a passing suite. |
| Land | **= Graduate or Discard.** Never "merge to main." Either the findings feed a fresh `/compass:frame` for real delivery work, or the spike is discarded with its learnings recorded. |

## Gate set

One gate, at Conclude: the question is answered (or explicitly answered with
"inconclusive - here is why"), and the finding is written down. That is it.
Spike has no test gate because it ships nothing.

## Swarm topology

Solo. No worktree.

## De-scope ledger - what Spike collapses or skips, and why it is safe

| Phase | Action | Standing justification |
|---|---|---|
| Specify | collapsed to a question | A spike has no acceptance criteria - its output is knowledge, not behaviour. |
| Clarify | skipped | Nothing to QA; the unknown is the point. |
| Plan | collapsed to a timebox | The plan for exploration is "explore, with a clock." |
| Distribute | skipped | One person, one question. |
| Build | TDD strategy suspended | Red-before-green is the wrong discipline for throwaway learning code. The G1 guardrail is not skipped - it is *deferred to graduation*, where it applies in full. |

Every justification rests on the same fact: **nothing lands from a Spike.**
The de-scopes are safe because the route has no delivery output to protect.

## Graduation - the only way out that keeps code

When a spike answers its question and the team wants to act on it:

1. **Re-frame.** Run `/compass:frame` afresh for the real delivery work. The
   spike's `delivery-approach.md`, conclusion, and any reference code are inputs to that
   Frame - often very good inputs, because the terrain is now mapped.
2. **The new route owns the code.** Any code carried over from the spike is
   now subject to that route's guardrails - G1 (tested before it lands), G2
   (acceptance defined), G3 (traceability). In practice most spike code is
   rewritten under TDD; some is kept and retro-tested. Either way it meets the
   guardrails before it lands.
3. **The spike closes.** Its `delivery-approach.md` records "graduated → task `<slug>`".

Graduation *is* re-framing. There is no path from spike code to `main` that
skips a real route - that is the whole safety model.

## Discard - the honourable other ending

A spike that concludes "this approach is not viable" or "the bug is X, fixable
in Y" has succeeded. Discard it: record the finding in `devlog.md`, note any
follow-up task, and close. A discarded spike that produced a clear answer was
cheap and worth it. The failure mode is not discarding - it is a spike with no
conclusion, which is just untracked work.

## Spike may NOT

- **Land production code.** The only exit that keeps code is graduation, which
  is re-framing. If you find yourself wanting to merge a spike branch to
  `main`, stop - that is a re-frame, not a merge.
- **Touch anything irreversible.** No auth, payments, personal data, or
  migrations - the routing guardrails floor those to Expedition regardless of
  intent. If the question can only be answered by touching irreversible
  surface, it is not a spike; it is Expedition with a discovery-heavy Specify.
- **Run past its timebox silently.** When the clock runs out, either conclude
  or re-frame the spike with a new timebox and a written reason. An open-ended
  spike is how exploration becomes drift.
- **Skip the graduate-or-discard decision.** A spike with no conclusion has
  not used the route - it has just avoided the framework.
