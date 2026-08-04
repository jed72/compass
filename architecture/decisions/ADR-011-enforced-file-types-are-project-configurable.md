---
id: ADR-011
title: Which file types require a red should be project-configurable, not a fixed list
status: proposed
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
to the hook (task `hook-bash-write-bypass`). The sweep asked which write
shapes the new branch blocked, and one case came back allowed:
`python3 -c 'open("hooks/post-tool.sh","w")'`. The command shape was detected
correctly; the *path* was classified as not-production.

## Decision

**Deferred to a future version, and deliberately not fixed by adding `.sh` to
the extension list.**

Adding one line is technically sufficient for this repository - all eight
shipped scripts already have test coverage. It is the wrong default for
adopters:

1. **Shell scripts are the least-tested file type in most repositories.**
   `deploy.sh`, `setup.sh`, `entrypoint.sh`, typically with no bats or
   shellspec harness anywhere in the project. The first edit after upgrading
   would block, with an instruction to write a failing test the project has no
   way to run.
2. **The hook has no per-project dial.** It never reads `.compass/config.yml`;
   the `mode: advisory | enforced` setting governs `compass check`, not the
   hook. So there is no supported way to soften this short of unregistering the
   hook - which would remove red-before-green for `.py` and everything else
   too. That is the trade recorded in the shell-detection design: an
   enforcement teams switch off is worth less than a partial one they keep.
3. **`.sh` alone is arbitrary.** `Makefile`, `justfile`, `package.json`
   scripts, `.bash`/`.zsh`, and extensionless files with a shebang are equally
   production-impacting and equally unclassified. Doing this consistently means
   a shebang check or a considered list, not an extension.
4. **It would enforce edits to the hook against itself.** A project whose hook
   misbehaves would have to satisfy it in order to repair it. A recovery path
   exists (record a red, or re-frame as a Spike), but shipping that failure
   mode needs an explicit self-exemption and a documented recovery line.

**The shape the fix should take instead:** the enforced set becomes project
configuration, with the current list as the default.

```yaml
# .compass/config.yml
enforcement:
  code_globs: ["*.sh"]        # added to the framework defaults
```

A project that says nothing keeps exactly today's behaviour (Inv-8, backward
compatibility). A project that wants its shell scripts covered opts in, and
this repository would opt in on the same commit that ships the knob.

## Consequences

**Until it ships,** shell scripts are unenforced everywhere including here, and
`docs/safety-contract.md` says so under what Compass does not claim. The gap is
visible rather than implied, which is the minimum this framework owes its own
guardrail G4.

**When it ships,** the classifier stops being a fixed list the framework
decides and becomes a floor the framework sets and a project can raise -
matching how guardrails already work, where project guardrails only ratchet
up. That is a better fit than the current all-or-nothing default.

**What it does not change.** The exemptions stay exempt in either version: test
files must remain editable so the red can be written, and Compass's own
artifacts under `.compass/` are never production code.

## Alternatives considered

- **Add `.sh` to the default list now.** One line, and correct for this
  repository. Rejected as a default for the four reasons above; the friction
  lands on every adopter and the escape hatch does not exist yet.
- **Special-case `hooks/` and `scripts/` as production paths.** Fixes the
  framework's own gap without touching adopters. Rejected: it is a rule that
  only makes sense inside this repository, shipped to everyone, and the
  path-scoped rules are supposed to describe categories (migrations,
  manifests), not one project's layout.
- **Detect a shebang rather than an extension.** More accurate than any
  extension list and catches extensionless scripts. Worth revisiting when the
  knob exists - it needs the hook to read file contents, which it does not do
  today for any classification.

## References

- Task `hook-bash-write-bypass` - the Bash-detection work whose false-negative
  sweep found this; its `verification-report.md` records the finding and the
  decision to leave it out of scope.
- `docs/safety-contract.md` - states, under what Compass does not claim, both
  that shell-command detection is best-effort and that shell script *files* are
  not classified as production code.
- **ADR-006** (backward compatibility is non-negotiable) - the constraint that
  makes "default stays as it is, projects opt in" the required shape.
- **ADR-010** (governance layers rather than copies) - the same pattern one
  level up: the framework sets a floor, the project adds to it, and a project
  that has adopted nothing keeps working unchanged.
