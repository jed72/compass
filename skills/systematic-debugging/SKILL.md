---
name: systematic-debugging
description: Root-cause-first debugging - instrument at boundaries, compare against a working case, test one hypothesis at a time, and fix through a failing test. Includes the escape clause - three failed fixes means the framing is wrong, not that a fourth fix is needed. Triggers during Build on an unexpected test failure, and any time a fix does not hold.
---

# Systematic Debugging

A test failed and you did not expect it to. The reflex is to change something
plausible and re-run. That reflex is why debugging sessions get long: each
attempted fix is a guess, guesses do not accumulate into understanding, and the
fourth one lands on a system you no longer have a model of.

This is the method that replaces the reflex. It is four phases and one escape
clause, and the escape clause is the part Compass adds.

## Phase 1 - Root cause investigation

**Read, do not infer.** The single biggest cost in debugging is reasoning about
what the code *should* do instead of observing what it *does*.

- Instrument at every component boundary the failing path crosses - the call in,
  the call out, and the value at each hand-off. Not inside the function you
  suspect: at the edges, so you learn *where* the truth changes.
- Read the whole log, not the last line. The last line is where it surfaced;
  somewhere above is where it started.
- Reproduce it deliberately before changing anything. A failure you cannot
  trigger on demand is one you cannot confirm you fixed.

You leave this phase when you can point at the line where correct becomes
incorrect. Not before.

## Phase 2 - Pattern analysis

**Find a working case and compare.** Almost every bug has a neighbour that
works: a sibling test, an earlier commit, a different input, another
environment.

Run the working case and the failing case side by side, and write down the
delta. Keep narrowing it until one difference remains. That difference is not
always the cause, but it is the only honest place to start hypothesising.

## Phase 3 - Single-hypothesis test

**One hypothesis, stated out loud, with a test that can falsify it.**

- State it in a sentence: "the token is expired by the time the validator sees
  it, because the clock is read twice."
- Design the smallest check that would come out differently if it were false.
- Run it. If it does not falsify cleanly, the hypothesis was too vague - sharpen
  it and repeat.

Changing two things at once is what makes a debugging session unrecoverable.
You stop being able to attribute the result, and both changes stay in the code.

## Phase 4 - Fix through a failing test

**Write the regression test first, watch it go red, then fix it.**

This is the same red-green discipline Build already runs (`compass tdd-red`,
then `compass tdd-green`) - see `tdd-discipline`. It matters more here, not
less: a bug fixed without a test that failed for the bug's reason is a bug you
cannot prove you fixed, and one that returns without anyone noticing.

If the test does not go red first, you have not reproduced the bug. Go back to
phase 1.

## The escape clause - three failed fixes means the framing is wrong

**After three consecutive fixes that did not hold, stop fixing.** Do not attempt
a fourth.

Three failures in a row is not bad luck. It means the model you are debugging
against does not match the system - and continuing to make changes against a
wrong model damages code that was not broken. The question stops being "what is
the bug" and becomes "why do I keep being wrong about this".

In Compass terms that is a **routing** signal, not just a debugging one. A task
whose fixes keep failing is usually a task whose blast radius, terrain or
magnitude was misread at Frame - most often terrain scored `brownfield-mapped`
when the behaviour was never actually written down.

So:

```
/compass:frame --reframe --reason "three fixes failed; the terrain was misread"
```

Re-score the dimensions honestly. If terrain is genuinely unmapped,
`RG-FLOOR-002` will force `blueprint-distillation`, and writing the current
behaviour down is very often the thing that ends the bug hunt. A re-frame here
is the system working; a fourth guess is not.

## Anti-patterns

- **The plausible change.** Editing something that looks wrong without a
  hypothesis that predicts the failure. If you cannot say what you expect to
  change, you are not testing anything.
- **Debugging by diff.** "It worked before this commit" locates a change, not a
  cause. Use it to build a hypothesis, not to skip phase 1.
- **The silent fourth fix.** Attempting one more after three failures because
  this one *feels* right. Feeling right is what the previous three felt like.
- **Fixing the symptom.** Making the test pass without understanding why it
  failed. On a Hotfix route this is an explicit, recorded backfill; anywhere
  else it is a bug you have hidden rather than removed.
