# Composing and constraining, and the spike case

Split out of `SKILL.md`: it describes what `compass approach evaluate` does,
and a session does not do it by hand. `approaches/composition-reference.md`
covers the same ground from the policy's side; this is the reading that goes
with the skill.

## Composing the candidate route

Go phase by phase, not route by route:

- **Define** - scenario count and discovery depth; distillation if brownfield.
- **Refine** - full / light / collapsed. Collapsed is permitted *only* when the
  spec is a single unambiguous scenario *and* no routing guardrail requires the requirements review.
- **Plan** - one-liner / real `technical-design.md` / plan + distribution map.
- **Breakdown** - solo / pair / swarm, stream count from the distribution map.
- **Build** - test-surface target, scaled to risk.
- **Verify** - which review dimensions, how many gates (see the router's
  dimensions-by-route table).
- **Ship** - trivial integration vs. coordinated merge; which follow-ups are owed.

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
- **The define stage collapses to the question, the requirements review is skipped, design collapses to a
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

