# Compass operating contract

This project uses Compass. Follow this in every session.

**Assess before you change anything.** Before editing code, specs or product
artefacts, run `/compass:assess`. You read four things - how risky the work is,
how well the ground is mapped, how big it is, and what the goal is - and the
CLI turns them into the process. You do not choose the process. Conversation
is exempt: answering a question, explaining code, reading to understand.

**Never skip assessment.** The only exempt work is conversation - answering a
question, explaining code, reading to understand. The moment a tool call would
change a file, the current issue must already have been assessed.

**Trigger on intent, not on the command.** If someone describes work to build,
change or fix, assess first even if they never typed the command. This adds to
explicit invocation rather than replacing it: typing any Compass command
always works. If `.compass/current-task` already points at an assessed issue,
carry on with it rather than assessing again.

**Guardrails are hard. Strategies are soft.** Five guardrails: every change
lands with a passing test that covers it; acceptance criteria exist before the
code; code traces to a criterion and a reason; evidence is a recorded command
output, never a claim that something passed; a human approves anything
irreversible. Strategies - writing the failing test first, Given/When/Then
scenarios - are how you satisfy those, and they bend where a guardrail does
not.

**Evidence, not assertion.** "The tests pass" clears nothing. Drive the cycle
through the CLI: `compass tdd-red -- <cmd>` proves a test fails and records it;
`compass tdd-green -- <cmd>` proves it passes. `compass check` verifies the
guardrails against what is on disk.

**If it is not on disk, it did not happen.** Each stage writes its artefact
under `.compass/work/<issue>/`. A later session, or another agent, picks the
work up from those files without re-deriving anything.

**Stages, in order:** assess, define acceptance criteria, refine, plan, break
down, implement, verify, ship - each with a `/compass:*` command. The delivery
approach written at assessment says which run at what weight and why any was
skipped. Honour it.

**Where to look.** `compass <verb> --help` explains any verb; the
`compass-runtime` skill has the stage map, the agents and the on-disk layout.

**Write for someone with no context.** Why before what, no reference a reader
cannot follow, and stop once you have said it.
