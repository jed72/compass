---
name: receiving-code-review
description: How to answer a reviewer - verify every suggestion against the code before acting on it, push back with technical reasoning when the reviewer is wrong, and treat "implement this properly" as a question rather than an instruction. Triggers whenever review feedback arrives, during Verify and on any pull request.
---

# Receiving Code Review

A reviewer has left comments. There are two ways to get this wrong, and
agreeing too readily is the more common one.

**Verify each suggestion against the code before you implement it.** Every
suggestion is a hypothesis about code the reviewer read faster than you wrote
it. Go and look. Does the case they describe actually exist? Does the function
behave the way their comment assumes? A
suggestion that is right about the smell and wrong about the cause is the normal
case, not the exception - implementing it verbatim leaves the smell and adds a
change nobody needed.

**"You're absolutely right" before checking is the failure this exists to
prevent.** It feels cooperative and it is not: it converts the reviewer's guess
into your commit, with your name on it, and removes the second opinion that
review was supposed to provide.

**Push back with technical reasoning when the reviewer is wrong.** Not with
preference, not with seniority, and not with how long the current version took.
Show the case their suggestion breaks, or the constraint it misses, or the
measurement that contradicts it. A reviewer given a concrete reason usually
agrees in one round; a reviewer given "I'd rather not" escalates.

If you cannot produce a technical reason, that is information: they are probably
right.

**YAGNI-check anything phrased as "implement this properly".** Ask what breaks
today without it. If the answer is nothing, the suggestion is scope, and scope
belongs in a Frame, not in a review thread. Say so plainly and offer to file it.

**Say what you did.** For each comment: changed it, or did not and why. A
resolved thread with no reply is a decision nobody can audit later - and under
guardrail G4, a change with no recorded reason is an assertion.

## The shape of a good response

> Checked - `validate()` is called before the cache write, so the race you
> describe cannot happen on this path. It *can* on the batch path, which your
> comment led me to; fixed there and added a test.

Verified, disagreed on the specific, credited the reviewer for the finding, and
recorded what changed. Roughly forty words.

## Anti-patterns

- **Reflexive agreement.** Implementing without checking.
- **Reflexive defence.** Explaining why the current code is fine before reading
  the comment properly.
- **Silent compliance.** Making the change with no reply, so the reasoning is
  lost and the same comment arrives again next time.
- **Deferring on authority.** Doing it because a senior reviewer said so. The
  code does not know who filed the comment.
