---
id: ADR-011
title: Which file types need a red should be project-configurable, not a fixed list
status: accepted
date: 2026-08-04
supersedes: ''
superseded_by: ''
---

## Context

`hooks/pre-tool.sh` decides whether a file change needs a failing test on
record by classifying the path: a list of application-source extensions
(`.py`, `.ts`, `.go`, …), a list of infrastructure ones (`.tf`, `.sql`,
`Dockerfile`), and a set of path-scoped rules (anything under `migrations/`,
`k8s/`, `.github/workflows/`).

**Shell scripts are in none of them.** A `.sh` file is not classified as
production code, so red-before-green does not apply to it - for any tool, not
just Bash. The framework's own `hooks/*.sh` and `scripts/*.sh` are therefore
outside the mechanism they implement: `scripts/release.sh` cuts releases and
`scripts/integrate.sh` merges worktrees, and either can be rewritten with no
test on record.

This was found by a false-negative sweep while adding Bash-command detection
to the hook. The sweep asked which write
shapes the new branch blocked, and one case came back allowed:
`python3 -c 'open("hooks/post-tool.sh","w")'`. The command shape was detected
correctly; the *path* was classified as not-production.

## Decision

**Accepted and implemented 2026-08-06.** The enforced set is project
configuration - `enforcement.code_globs` in `.compass/config.yml`, added to the
framework's built-in set - and this repository declares `hooks/*.sh` and
`scripts/*.sh`, closing the gap where its own enforcement scripts were outside
the mechanism they implement.

Two things the implementation settled that this ADR had left open:

1. **A project may only add.** There is no key that removes framework
   enforcement. Compass's model is that project rules can only add - a project
   guardrail may exceed a floor, never fall short of one - and an exemption key
   would let a project switch enforcement off while appearing to configure it.
2. **Every block names the rule that matched**, built-in or project-declared.
   That is the other half of the reported problem: the surface was not just
   narrow, it was invisible, and an author could not predict which edit would
   block until one did.

Adding `.sh` to the framework's own default extension list, rather than making
the set project-configurable, was rejected. Enough is not the same as right
for adopters:

1. **Shell scripts are the least-tested file type in most repositories.**
   `deploy.sh`, `setup.sh`, `entrypoint.sh`, typically with no bats or
   shellspec harness anywhere in the project. The first edit after upgrading
   would block, with an instruction to write a failing test the project has no
   way to run.
2. **A fixed default gives a project no dial.** Without `enforcement.code_globs`,
   there would be no supported way to soften this short of unregistering the
   hook - which would remove red-before-green for `.py` and everything else
   too. An enforcement a team would switch off entirely is worth less than a
   partial one it keeps, which is why the setting exists instead.
3. **`.sh` alone is arbitrary.** `Makefile`, `justfile`, `package.json`
   scripts, `.bash`/`.zsh`, and extensionless files with a shebang are equally
   production-impacting and equally unclassified. Doing this consistently means
   a shebang check or a considered list, not an extension.
4. **It enforces edits to the hook against itself.** A project whose hook
   misbehaves has to satisfy it to repair it. A recovery path
   exists (record a red, or re-frame as a Spike), and that recovery line is
   documented alongside the setting.

The enforced set is project configuration, with the framework's list as the
default:

```yaml
# .compass/config.yml
enforcement:
  code_globs: ["*.sh"]        # added to the framework defaults
```

A project that says nothing keeps exactly today's behaviour (Inv-8, backward
compatibility). A project that wants its shell scripts covered opts in; this
repository opts in on the same commit that shipped the setting.

## Consequences

The classifier is a floor the framework sets and a project can raise -
matching how guardrails already work, where project guardrails only add.
That is a better fit than an all-or-nothing default. Naming the enforced set
in `.compass/config.yml` also makes the gap visible rather than implied,
which is the minimum this framework owes its own evidence-not-assertion
guardrail (`G4`).

**What it does not change.** The exemptions stay exempt in either version: test
files must remain editable so the red can be written, and Compass's own
artifacts under `.compass/` are never production code.

## Alternatives considered

- **Add `.sh` to the default list.** One line, and correct for this
  repository. Rejected as a default for the four reasons above; the friction
  would land on every adopter with no setting to soften it.
- **Special-case `hooks/` and `scripts/` as production paths.** Fixes the
  framework's own gap without touching adopters. Rejected: it is a rule that
  only makes sense inside this repository, shipped to everyone, and the
  path-scoped rules are supposed to describe categories (migrations,
  manifests), not one project's layout.
- **Detect a shebang rather than an extension.** More accurate than any
  extension list and catches extensionless scripts. Rejected for now - it
  needs the hook to read file contents, which it does not do today for any
  classification. Worth revisiting if the setting proves too coarse.

## References

- The Bash-detection work whose false-negative sweep found this; its
  `verification-report.md` records the finding and the decision to leave it
  out of scope.
- `docs/safety-contract.md` - states, under what Compass does not claim, both
  that shell-command detection is best-effort and that shell script *files* are
  not classified as production code.
- **ADR-006** (backward compatibility is non-negotiable) - the constraint that
  makes "default stays as it is, projects opt in" the required shape.
- **ADR-010** (governance layers rather than copies) - the same pattern one
  level up: the framework sets a floor, the project adds to it, and a project
  that has adopted nothing keeps working unchanged.
