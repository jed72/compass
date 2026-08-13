---
name: adaptive-routing
description: How to score the four assessment dimensions, how the delivery approach is composed and constrained, and how to keep an honest de-scope ledger. Triggers whenever triage runs, and whenever an issue is re-assessed mid-flight.
---

# Adaptive Routing

This skill is the craft behind `approaches/rubric.md`. The router file is the
rubric; this is how you actually use it well.

## The mental model

You are not picking a process. You are computing one. The four dimensions are
four independent questions, and the route is their composition - heavier where
they read high, lighter where they read low. The composition is **biased** by
the routing strategies and **bounded** by the routing guardrails, both in
`governance/routing-policy.md`. The five reference shapes
(quick-fix/Standard/initiative/Hotfix/Spike) are shapes the composition tends to
land near, not boxes to sort into.

## Governance is a gradient - you work with the shipped defaults

`/compass:init` is optional. The framework ships `governance/` with active
default guardrails, default strategies, and a default routing policy. If a
project has not run init and has no project-specific additions, that is a
valid, complete governance state - you route against the shipped defaults
exactly as you would route against an extended set. "Frame-and-go on day one"
is honest precisely because the defaults are real, in-force content. Never
treat an un-extended `governance/` as a missing prerequisite.

## Scoring the dimensions - heuristics

**risk** - *consequence, never effort.*
- The tell for `critical`: can this lose data, lose money, breach auth/privacy,
  or resist a clean rollback? If yes, it is critical even if it is one line.
- The tell for `trivial`: is the worst case cosmetic, instantly obvious, and
  instantly reversible - with no data, money, auth, or other team touched?
- The common mistake: scoring risk by how hard the change is. A hard
  change can be contained; a trivial-looking change can be critical. Score the
  failure, not the work.

**Familiarity** - *new code, or old code, and is the old code mapped?*
- `brownfield-unmapped` is not a judgement of code quality - it means the
  behaviour is not written down as scenarios. It triggers a routing guardrail
  floor: `blueprint-distillation` must run. Do not route around it.
- "Trivially readable" greenfield or brownfield can be treated as mapped, but
  be honest - "I could figure it out" is not "it is written down."

**Size** - *the dimension humans get wrong most.*
- People under-estimate size far more than they over-estimate it. When
  genuinely torn between two values, take the higher one. Collapsing a phase
  that turned out easy is cheap; discovering mid-Build that the route was too
  light is expensive and demoralising.
- Anchor on concrete tests: `atomic` is one file and no design decision;
  `standard` has one or two design decisions; `large` has real architecture and
  is plausibly parallelisable.

**Intent & role** - *the actual outcome, not the literal request.*
- Read `prd.md` if it exists. "Add a CSV export" under a brief that says "let
  finance self-serve" may need filters, scheduling, and permissions - the
  literal request under-describes the intent.
- A non-engineering role in play almost always pulls the route up: it adds
  artifacts and assessed strategies. That is the framework working, not overhead.
- One intent value is not a role: **exploration** - "I cannot frame this well
  enough to deliver it yet." Exploration composes toward the **Spike** route the
  way live-defect urgency composes toward Hotfix. Still score all four
  dimensions; the intent is what selects the shape. See "Composing the Spike
  route" below.

If you cannot justify a reading in one honest line, **ask the human.** An
unjustified guess is worse than a question, every time.

## Composing the candidate route

Go phase by phase, not route by route:

- **Specify** - scenario count and discovery depth; distillation if brownfield.
- **Clarify** - full / light / collapsed. Collapsed is permitted *only* when the
  spec is a single unambiguous scenario *and* no routing guardrail requires Clarify.
- **Plan** - one-liner / real `design.md` / plan + distribution map.
- **Distribute** - solo / pair / swarm, stream count from the distribution map.
- **Build** - test-surface target, scaled to risk.
- **Verify** - which review dimensions, how many gates (see the router's
  dimensions-by-route table).
- **Land** - trivial integration vs. coordinated merge; which follow-ups are owed.

Name the nearest reference shape for shared vocabulary, then list deviations
explicitly. "Standard, but Verify also runs `security` because risk is
cross-cutting" is a correct, expected output - not an exception.

The composition step is where the **routing strategies** apply. They *bias* the
candidate - `default_shapes` says which reference shape a reading leans toward,
and the tie-breaking `biases` settle the close calls ("when size is
unclear, estimate up"; "prefer the lightest route that still clears the routing
guardrails"). A routing strategy is a starting point, not a verdict: depart from
one when the issue warrants, and record the departure in `delivery-approach.md`.

## Composing a spike

When intent reads `exploration`, the composition leans toward **Spike** - the
escape hatch for work you cannot yet frame as delivery. Compose toward Spike
when *all three* hold: intent is genuinely exploration not delivery, the work is
a question rather than a known change, and nothing irreversible is in scope.

What is different about a Spike composition:

- **The TDD strategy (red-before-green) is suspended.** Red-before-green is the wrong
  discipline for code written precisely to learn something and likely thrown
  away. The route-aware pre-tool hook does not block on a Spike - it reads a
  `.compass/work/<task>/.spike` marker file. **The Navigator writes that marker
  when it composes a spike**; without it the hook will still block.
- **Specify collapses to the question, Clarify is skipped, Plan collapses to a
  timebox.** A spike has no acceptance criteria - its output is knowledge.
- **Nothing lands from a Spike.** The only exit that keeps code is *graduating*
  - re-framing into a real delivery approach where the tested-before-ship, acceptance-before-code, and traceability guardrails apply in full.
  This is what makes suspending the TDD strategy safe: a spike cannot smuggle
  untested code onto `main`, because it has no path to `main` at all.
- A question that can only be answered by touching irreversible surface
  (`auth`, `payments`, `personal-data`, `migrations`) is **not** a Spike - the
  routing guardrail floors force those to initiative regardless of intent.

## Constraining with the routing guardrails

After composing - the candidate already biased by the routing strategies - run
it through the **routing guardrails** in `governance/routing-policy.md` in this
order: **floors** raise it, **caps** limit it, **immovable_gates** are stapled
on, blocking **role_rules** add artifacts and phase blocks. Record every routing
guardrail that fires *and quote its rationale* in `delivery-approach.md`. Never apply a
constraint silently - a reader of `delivery-approach.md` must see which bounds were active.

The split is the whole point: routing strategies *bias* what triage reaches
for, routing guardrails *bound* what it is allowed to do. A human can override a
reading or a strategy-biased choice per-issue; a human cannot override a routing
guardrail per-issue - changing one means amending
`governance/routing-policy.md`.

## The de-scope ledger - the discipline that makes this auditable

This is the heart of the skill. Every phase or check the route collapses or
skips earns a row in the de-scope ledger, and each row needs an explicit
"safe to skip because…" line.

- **A skip with no justification is not allowed. If you cannot justify it, the
  phase runs.** This is non-negotiable - it is what separates "adaptive" from
  "arbitrary."
- Do not copy a reference shape's standing justification on autopilot. Confirm
  it actually holds for *this* issue. quick-fix's "Clarify collapsed - the one
  scenario is unambiguous" is only valid if the scenario really is unambiguous.
- Cap-driven reductions are **not** de-scopes. If the `critical` risk
  cap pins an initiative to one worktree, record that as cap-driven in the
  topology section, not in the de-scope ledger. The ledger is for things the
  route chose to skip, not things a guardrail removed.
- initiative's ledger is empty by definition. If you are writing de-scope rows
  on an initiative route, you have mis-composed.

### Anti-patterns

- **Laundering** - an approach lighter than the assessment warrants, to
  "just get the change in." `delivery-approach.md` makes this visible; do
  not do it.
- **Justification theatre** - a ledger row whose reason is "to save time."
  Time is not a safety argument. The reason must be about why the skip is
  *safe*, not why it is *convenient*.
- **Silent constraint** - applying a floor or omitting an immovable gate without
  a line in `delivery-approach.md`.

## When to re-assess

Re-framing mid-issue is a normal event, not a failure. Trigger it when:

- Build reveals the size was under-read - a "small" change is unspooling
  into a multi-module refactor.
- Clarify finds the spec is bigger or more ambiguous than the route assumed.
- A `touches:` tag surfaces late (you discover the change reaches auth).

Run `/compass:triage --reframe`: re-score the dimensions, write a new `delivery-approach.md`
revision, record what changed and why. A route quietly outgrown is the failure;
a route honestly re-framed is the system working.
