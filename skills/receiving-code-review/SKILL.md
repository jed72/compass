---
name: receiving-code-review
description: How to answer a reviewer - verify each suggestion against the code before acting on it, push back with technical reasoning when the reviewer is wrong, and treat "implement this properly" as a question about scope. Triggers whenever review feedback arrives, during Verify and on any pull request.
---

# Receiving Code Review

There are two ways to answer a reviewer badly, and agreeing too readily is the
more common one.

**Verify each suggestion against the code before you implement it.** Every
comment is a hypothesis about code the reviewer read faster than you wrote it.
A suggestion right about the smell and wrong about the cause is the normal
case - implementing it verbatim leaves the smell and adds a change nobody
needed.

**"You're absolutely right", before checking, is the failure this prevents.** It
feels cooperative. It converts the reviewer's guess into your commit, and
removes the second opinion review was supposed to provide.

**Push back with technical reasoning when the reviewer is wrong.** Show the case
their suggestion breaks, the constraint it misses, or the measurement that
contradicts it - not preference, not seniority, not how long the current version
took. If you cannot produce a technical reason, they are probably right.

**Treat "implement this properly" as a question about scope.** Ask what breaks
today without it. If the answer is nothing, it belongs in a Frame, not a review
thread. Say so and offer to file it.

**Say what you did.** Per comment: changed it, or did not and why. A resolved
thread with no reply is a decision nobody can audit - and under G4, a change
with no recorded reason is an assertion. A good reply is short: *"Checked -
`validate()` runs before the cache write, so that race cannot happen here. It
can on the batch path, which your comment led me to; fixed there."*

## Anti-patterns

- **Reflexive agreement** - implementing without checking.
- **Reflexive defence** - explaining why the code is fine before reading properly.
- **Silent compliance** - changing it with no reply, so the reasoning is lost.
- **Deferring on authority** - the code does not know who filed the comment.
