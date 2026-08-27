# Compass operating contract

This project uses Compass. Follow this in every session.

**Assess before you change anything.** Before editing code, specs or product
artefacts, run `/compass:assess`. You read four things - how risky the work is,
how well the ground is mapped, how big it is, and what the goal is - and the
CLI turns them into the process. You do not choose the process. Conversation
is exempt: answering a question, explaining code, reading to understand.

**Trigger on intent, not on the command.** If someone describes work to build,
change or fix, assess first even if they never typed the command. If
`.compass/current-task` already points at an assessed issue, carry on with it.

**Guardrails are hard. Strategies are soft.** Five guardrails: every change
lands with a passing test that covers it; acceptance criteria exist before the
code; code traces to a criterion and a reason; evidence is a recorded command
output, never a claim that something passed; a human approves anything
irreversible. Strategies - writing the failing test first, Given/When/Then
scenarios - are how you satisfy those, and they bend where a guardrail does
not.

**Evidence, not assertion.** "The tests pass" clears nothing. Drive the cycle
through the CLI: `compass tdd-red -- <test command>` runs the test, proves it
fails and records that; `compass tdd-green -- <test command>` proves it passes
and records that. `compass check` verifies the guardrails against what is on
disk.

**If it is not on disk, it did not happen.** Each stage writes its artefact
under `.compass/work/<issue>/`. A later session, or another agent, picks the
work up from those files without re-deriving anything.

**Stages, in order:** assess, define acceptance criteria, refine, design, break
down, implement, verify, ship. Each has a `/compass:*` command. The delivery
approach written at assessment says which stages run at what weight, and why
any was skipped. Honour it.

**Where to look.** `compass <verb> --help` explains any verb. `/compass:status`
and `/compass:flow` report across issues. Agents live in `agents/`, skills in
`skills/`, and the governance in force is whichever `governance/` the CLI
resolves - the project's own if it has one, the shipped defaults otherwise.

**Write for someone with no context.** Say why before what. Never leave a
reference a reader cannot follow. Stop once you have said it.
