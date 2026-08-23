# CI integration

Wiring Compass into CI is genuinely small, because the kit layer already does
the work. The whole integration is:

> **Run `compass ci`. Honour the exit code.**

`compass ci` is the full mechanical gate suite - it runs `compass policy lint`,
then `compass issue lint` and `compass check` for every task under
`.compass/work/`, and exits non-zero if anything fails. That is the one command
a CI job needs; everything else is just the platform's way of running it.

## Compass CI does not replace your project CI

Compass CI is a **process-integrity lane**, not a substitute for the rest of
your pipeline. It does *not* re-run your test suite, your linter, your type
checker, your security scanner, your build, or your deployment checks. What it
checks is whether the task state is coherent and backed by evidence: the
route was framed, scenarios have tests, changed files trace to scenarios,
gates carry evidence of the right type, approvals are recorded where they
must be. Your project's own CI keeps running everything else.

The two are designed to run alongside each other. The recommended pattern is
two jobs in the same workflow - `project-ci` for the application checks,
`compass-ci` gated on `project-ci` so a failing test suite stops the
pipeline before Compass even runs. `compass tdd-green` records that the
test passed *during Build*, and `compass check` then reads that record at
verify time - it does not re-run the test. The two pipelines together cover
*both* code correctness and process integrity, and neither substitutes for
the other; this is guarantee 6 of `docs/safety-contract.md`.

## What `compass ci` catches on a pull request

- **Governance drift** - `routing-policy.yml` or `guardrails.yml` is malformed,
  or a guardrail names a check the CLI does not implement (the integrity rule).
- **A malformed task spine** - a `task.yml` that does not match the schema.
- **An unmet guardrail** - a task whose `compass check` fails: a scenario with
  no test, a changed file with no traced scenario, a gate marked `pass` with
  missing or wrongly-typed evidence, an unpaid backfill.

It does **not** re-run your test suite - that is `compass tdd-green`'s job
during Build, and its result is the green record that `compass check`
reads. CI verifies the *task state is coherent and backed by evidence*, fast.

## GitHub Actions

Copy `ci/github-actions.yml` to `.github/workflows/compass.yml` in your
project. It checks out the repo, installs the CLI's dependencies
(`pyyaml`, and `jsonschema` for full schema validation), and runs `compass ci`.

The recommended pattern is to put `compass-ci` in the same workflow as your
project's own tests, gated on them so a red test suite halts the pipeline
before Compass runs:

```yaml
name: CI

on:
  pull_request:
  push:
    branches: [main]

jobs:
  project-ci:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      # your normal pipeline: tests, lint, type-check, build, etc.
      - run: make test
      - run: make lint

  compass-ci:
    runs-on: ubuntu-latest
    needs: project-ci             # only run Compass once code is green
    env:
      COMPASS_CLI: cli/compass    # adjust to wherever Compass lives in your repo
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: python3 "$COMPASS_CLI" ci
```

Pin `COMPASS_CLI` to a specific commit SHA, not a branch - see
`docs/security.md` for the supply-chain stance.

## Piloting Compass without blocking delivery - `mode: advisory`

When a team is first adopting Compass, you may want `compass ci` to *report*
failures without exiting non-zero, so it does not block PRs while the team
is still learning the model. Set the adoption mode in `.compass/config.yml`:

```yaml
mode: advisory     # report failures, exit 0 - non-blocking
# mode: enforced   # the default - fail the CI job on any failure
```

In `advisory` mode every failure is still printed (with the structured
`what / why / fix` blocks) under a clear `[mode: advisory]` banner - an
advisory run is never mistaken for an enforced one. Flip to `mode:
enforced` when the team is ready and the gates start blocking landings.
Adoption is a gradient - see guarantee 7 of `docs/safety-contract.md`.

## Any other CI

The pattern ports unchanged - it is two lines on any platform:

```sh
python3 path/to/compass ci
# the job fails if compass ci exits non-zero
```

PyYAML travels inside the plugin, so there is no install step. If you want full JSON Schema validation in the lint commands, `pip install jsonschema` is a genuinely optional extra - the built-in linter runs without it.

GitLab CI, CircleCI, Buildkite, a git pre-push hook - all the same. There is
no Compass-specific CI plugin to install, and there never needs to be: the kit
layer is a plain CLI with honest exit codes, and that is the entire contract.

## A note on where the CLI lives

`compass ci` resolves `governance/` and the task working directory by walking
up from the working directory, and finds `schemas/` relative to the CLI
script. In a project that has Compass installed, point the CI step at wherever
`cli/compass` is (vendored, a submodule, or a pinned checkout). In the Compass
framework repo itself, it is just `cli/compass`.
