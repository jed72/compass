# The Compass safety contract

A short, central statement of what Compass promises - and what it does not.
Everything else in the framework exists to keep this promise.

**This contract applies from version 1.0.0.** The title used to carry a version
and had to be edited at every major, which is how it came to read "1.0" on a
3.2.0 release. The version lives here instead, where a check compares it to
`VERSION`.

## What Compass guarantees

Compass is an adaptive spec-driven development kit for AI-assisted engineering
workflows. **When it is in use, it guarantees:**

1. **An issue receives a deterministic route once its assessment are known.** The
   four-dimension assessment are judgement (triage's); given those assessment
   plus `governance/routing-policy.yml`, the route is a pure function - same
   assessment, same policy, same route, every run, on every machine.

2. **A declared guardrail cannot silently become advisory.** Every guardrail's
   declared check must be implemented in the CLI; both `compass policy lint`
   and `compass check` fail closed on the absence. There is no "marked pass
   without an implementation."

3. **Delivery work cannot land without required evidence.** Gate evidence is
   typed, registered, and traceable; `verify.correctness` cannot be cleared
   with a written note, and an unbacked claim cannot ship. Follow-ups are
   tracked and block Land until paid.

4. **Exploration cannot silently become production delivery.** A Spike is
   mechanically constrained: no production-landable `changed_files`, a written
   `spike-conclusion` with an explicit decision (discard / graduate-to-delivery
   / defer), and any decision to act on the findings becomes a fresh Frame for
   a real route. The router refuses to silently promote a Spike onto delivery
   surface when a risk floor applies - it raises a routing conflict instead.

5. **Human approvals are required and recorded for irreversible or high-risk
   changes.** Changes that touch auth, payments, personal data, or migrations
   route to initiative and demand a structured `human-approval` evidence
   record - approver, role, decision, timestamp, scope, conditions - before
   Land can complete. **So does any change whose risk is `critical`**,
   which the router defines as one that can lose data, lose money, breach
   auth or privacy, or resist a clean rollback. That second arm matters
   because those consequences do not always carry one of the four tags: a
   backup and restore path, a destructive cleanup job, a retention policy
   change, or a storage migration written in application code can be exactly
   what this guarantee is for and touch none of them.

6. **Compass CI validates process integrity. It does not replace project CI.**
   `compass ci` proves routes, evidence, approvals, traceability, and follow-ups
   are coherent and complete. It does **not** re-run your test suite, your
   linter, your security scanner, your build, or your deployment checks -
   those remain your project's responsibility. The two pipelines complement
   each other; neither substitutes for the other.

7. **Users can install, run, and recover from common failures using
   documented workflows.** Install is verifiable (`docs/install-smoke-test.md`);
   onboarding is five minutes (`docs/five-minutes.md`); adoption is gradient -
   start in `advisory` mode and tighten to `enforced` when the team is ready.

   **On failure messages, narrowed to what is true.** The messages the CLI
   raises through its own error type carry what failed and what to do about it,
   and that is the house style every new one follows. It is a **design intent,
   not a checked property**: whether a sentence explains a cause is a judgement
   no check can make, and writing one that counted keywords would report a
   quality it had not inspected. Earlier wording claimed this of *every*
   failure message. Nothing established that.

## What Compass does NOT claim

Equally important. Honest scope is what makes the promise credible.

- **Compass does not prove software correctness.** It enforces that
  acceptance is stated and tested, that evidence exists and is the right
  kind, and that the route is the right shape for the issue. It does not
  reason about whether your code is correct - only your tests and reviewers do
  that.

- **Compass is not a replacement for CI/CD.** See guarantee 6. A
  production-bound project still needs its own test, lint, security, build,
  and deploy pipeline. Compass adds a *process-integrity* lane to that
  pipeline; it does not absorb it.

- **Compass is not a full autonomous-development governance system.** It
  governs how human-and-AI teams shape work; it does not police what AI
  agents do outside its pipeline.

- **A green test record does not establish which tests ran.** A `test-run`
  record holds **one exit code for one command**. It does not enumerate the
  tests the command collected, so Compass cannot tell which tests a run
  exercised - only that a command it was given exited zero. The record is also
  **not bound to the state of the code** when it was made: a genuine green from
  before later edits still satisfies the check, and so would an unrelated
  command that happens to exit zero.

  What Compass does establish is the declared relationship - this changed file
  traces to this scenario, which names this test, which exists - plus the fact
  that a green run was recorded. That is a real and useful thing, and it is
  less than a reader hears in "a passing automated test it traces to", which is
  why that wording was withdrawn.

  Closing the gap means recording the commit or tree identity, the acceptance
  spec's hash, and the exact test ids a run collected, then requiring every
  scenario to be covered by an observed test rather than a declared one. That
  is being built; it is not built yet, and this contract does not promise it.

- **Red-before-green enforcement on shell commands is best-effort.**
  `hooks/pre-tool.sh` intercepts the file-editing tools completely: an `Edit`,
  `Write`, or `MultiEdit` of a production file cannot proceed without a
  recorded red. A shell command is a different problem, because what it writes
  is generally not knowable from the command string - `bash deploy.sh` may
  rewrite the whole repository and say nothing about it. The hook therefore
  recognises a fixed set of write shapes and lets everything else through:

  - `>` and `>>` redirects, including the `cat > file <<EOF` heredoc form
  - `sed -i`, `perl -i`
  - `tee`, and the destination argument of `cp` and `mv`
  - `patch -p<n>` and `git apply` (treated as writers with unknowable targets)
  - an inline interpreter script - `python3 -c`, a `python3 - <<PY` heredoc,
    `node -e` - that opens a file for writing

  Anything else runs unchecked. A command that writes through a script, a
  build step, or an interpreter reached via a wrapper is not detected. This
  fails open on purpose: blocking every unrecognised command would block
  `make`, `npm test`, and `git commit`, and an enforcement that teams switch
  off is worth less than a partial one they keep. If red-before-green matters
  absolutely for your project, the file-editing tools are where the guarantee
  is complete.

- **Shell scripts are not classified as production code.** Separately from the
  point above - which is about the *command* - the hook decides whether a
  *file* needs a red by its path and extension: application source (`.py`,
  `.ts`, `.go`, …), infrastructure (`.tf`, `.sql`, `Dockerfile`), and
  path-scoped rules for migrations, manifests, and CI workflows. `.sh` is in
  none of them, so editing a shell script never requires a failing test, with
  any tool. `Makefile`, `justfile`, and extensionless scripts are the same.

  This applies to Compass's own `hooks/` and `scripts/` as much as to yours.
  The fix is deliberately deferred rather than defaulted on: adding `.sh` to
  the list would require a red for every shell edit in every project on
  upgrade, and the hook has no per-project dial to soften it - `mode: advisory`
  in `.compass/config.yml` governs `compass check`, not the hook. The intended
  shape is a project-configurable enforced set, with today's list as the
  default. See `architecture/decisions/ADR-011-enforced-file-types-are-project-configurable.md`.

- **Compass is not a universal process framework.** The methodology layer is
  general; the kit is concrete. Teams adopt and tune both. There is no claim
  it fits every team or every project unchanged.

## How the contract is honoured mechanically

| Guarantee | How |
|---|---|
| 1 (deterministic routing) | `compass approach evaluate` - pure function over assessment + policy |
| 2 (no silent guardrails) | `compass policy lint` + `compass check` both fail on missing CHECK_FNS implementation |
| 3 (typed, registered evidence) | `governance/guardrails.yml` declares per-gate accepted types; gates reference entries in the issue's evidence registry by id |
| 4 (Spike safety) | Routing guardrail raises a conflict on unsafe exploration; `compass check` enforces the spike-conclusion + no-production-changed_files invariants on a spike |
| 5 (recorded approvals) | `human-approval` typed evidence with structured fields, validated at ship time |
| 6 (CI lane, not CI itself) | `ci/README.md` + the reference workflow run alongside project CI; the docs say so explicitly |
| 7 (recoverable, gradient) | `docs/install-smoke-test.md`, `docs/five-minutes.md`, structured failure messages, `mode: advisory \| enforced` in `.compass/config.yml` |

## Versioning and stability

Compass declares its policy and schema versions in `governance/*.yml` and
the issue spine (`schema_version`). The CLI will warn - or in `enforced` mode,
fail - when it meets an issue whose schema is not compatible with the running
CLI. Migration guidance ships with every breaking change.

This contract is the bar from 1.0.0 onward. Future versions may *add* guarantees; they
must not weaken these without a major-version bump and a written migration
path.
