---
description: Optionally adopt project-specific governance - copy governance/ in and extend it
allowed-tools: Read, Write, Edit, Bash, Glob
---

# /compass:init

`/compass:init` is **optional**. Compass ships with five default guardrails,
a set of default method strategies (including BDD and TDD), and a default
routing policy - all active out of the box. `/compass:frame` works on day one
with zero project setup; it routes against those shipped defaults. Init is not
a gate you must clear before the first task.

What init *is*: the step where a project starts to **accrete its own
governance**. It copies `governance/` into the project so the team can extend
it - adding project-specific guardrails and strategies, and tuning the routing
policy to the project's real risk surface. Governance is a gradient, not a
threshold (see `docs/methodology.md` §4): "the shipped defaults and nothing
project-specific yet" is a complete, valid governance state. Init is how a
team moves *along* that gradient, when it has formed opinions worth writing
down - not before.

Run it whenever the team is ready. It does not change application code, so it
is exempt from Frame.

## Steps

1. **Check for an existing install.** If a project `governance/` directory or
   `.compass/config.yml` already exists, stop and report what is present. Do
   not overwrite live governance; offer to show a diff against the shipped
   defaults instead.

2. **Copy `governance/` into the project.** Place the shipped `governance/`
   files at the project root: the prose `guardrails.md`, `strategies.md`,
   `routing-policy.md`, `README.md`, **and the machine-readable
   `guardrails.yml` and `routing-policy.yml`** - the latter two are what the
   `compass` CLI runs (`compass route evaluate`, `compass check`,
   `compass policy lint`). These arrive with their defaults already active and
   in force - they are not empty templates. The `cli/` and `schemas/`
   directories ship with the framework and are not copied per-project; the CLI
   walks up to find a project-local `governance/`, falling back to the shipped
   defaults. The default guardrails G1–G5 and the default method strategies are
   real content from the moment they land.

3. **Walk the team through extending them** - additively, in each role's own
   language, a few questions at a time. Nothing here is required to be filled;
   an empty project section is a valid, complete state.
   - **`guardrails.md` - project guardrails section.** Add a guardrail only
     when the team hits something that must *never* recur and can be checked
     with evidence. Guardrails are sticky: slow to add, slower to remove.
     Leave the section empty rather than padding it.
   - **`strategies.md` - project strategies section.** Add freely - strategies
     are meant to accrete. Product, engineering, and voice & positioning
     preferences all live here (this is what the old constitution called
     "principles"). A strategy is directional and assessed, not checkable or
     blocking.
   - **`routing-policy.md` / `routing-policy.yml`.** Tune them to the project,
     keeping the prose and the YAML in step - the YAML is authoritative for what
     the CLI runs. Routing strategies (`default_shapes`, `biases`) are meant to
     be adjusted as the team learns how its work distributes. Routing guardrails
     (floors, caps, immovable_gates, role_rules) bound the Needle - adjust them
     deliberately; loosening one weakens the framework for everyone. Run
     `compass policy lint` after any edit to the governance YAML.
   Fill `{{PROJECT_NAME}}`, `{{DATE}}` (today), and each file's amendment-log
   first row. Do not leave `{{...}}` placeholders behind.

4. **Create the config.** Copy `.compass/config.yml` into place and set
   `project.name` and `project.test_command`. It holds only genuine project
   knobs - routing rules (default route, route shapes, worktree caps) live in
   `governance/routing-policy.yml`, which is authoritative; tune routing there,
   not here.

5. **Create working state.** Make `.compass/work/`. Add a `.gitkeep` if empty.
   Remind the user that `.compass/work/` **is committed** - it is the audit
   trail, not scratch. `/compass:frame` will later write `.compass/current-task`
   (the pointer the CLI uses to resolve which task a `compass` call acts on);
   it does not need to be created now.

6. **Report.** Summarise what was created, which project sections the team
   chose to leave empty (a valid state, not owed work), and the next command:
   `/compass:frame` for an engineer, or a role entry point - `/compass:intent`
   (product owner/manager), `/compass:position` (product marketer), or
   `/compass:design` (designer).

## Gate

Init is complete when the project `governance/` files are in place with no
remaining `{{...}}` placeholders in their headers and amendment logs, and
`.compass/config.yml` is set. The project guardrail and strategy *sections* may
be left empty - that is accretion not yet begun, not an unfinished step. The
shipped defaults are in force regardless.
