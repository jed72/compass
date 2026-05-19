# The Compass 1.0 safety contract

A short, central statement of what Compass 1.0 promises — and what it does
not. Everything else in the framework exists to keep this promise.

## What Compass 1.0 guarantees

Compass 1.0 is an adaptive spec-driven development kit for AI-assisted
engineering workflows. **When it is in use, it guarantees:**

1. **A task receives a deterministic route once its readings are known.** The
   four-dimension readings are judgement (the Needle's); given those readings
   plus `governance/routing-policy.yml`, the route is a pure function — same
   readings, same policy, same route, every run, on every machine.

2. **A declared guardrail cannot silently become advisory.** Every guardrail's
   declared check must be implemented in the CLI; both `compass policy lint`
   and `compass check` fail closed on the absence. There is no "marked pass
   without an implementation."

3. **Delivery work cannot land without required evidence.** Gate evidence is
   typed, registered, and traceable; `verify.correctness` cannot be cleared
   with a written note, and an unbacked claim cannot ship. Backfills are
   tracked and block Land until paid.

4. **Exploration cannot silently become production delivery.** A Spike is
   mechanically constrained: no production-landable `changed_files`, a written
   `spike-conclusion` with an explicit decision (discard / graduate-to-delivery
   / defer), and any decision to act on the findings becomes a fresh Frame for
   a real route. The router refuses to silently promote a Spike onto delivery
   surface when a risk floor applies — it raises a routing conflict instead.

5. **Human approvals are required and recorded for irreversible or high-risk
   changes.** Changes that touch auth, payments, personal data, or migrations
   route to Expedition and demand a structured `human-approval` evidence
   record — approver, role, decision, timestamp, scope, conditions — before
   Land can complete.

6. **Compass CI validates process integrity. It does not replace project CI.**
   `compass ci` proves routes, evidence, approvals, traceability, and backfills
   are coherent and complete. It does **not** re-run your test suite, your
   linter, your security scanner, your build, or your deployment checks —
   those remain your project's responsibility. The two pipelines complement
   each other; neither substitutes for the other.

7. **Users can install, run, and recover from common failures using
   documented workflows.** Install is verifiable (`docs/install-smoke-test.md`);
   onboarding is five minutes (`docs/five-minutes.md`); every failure message
   tells you *what failed, why it matters, and how to fix it*; adoption is
   gradient — start in `advisory` mode and tighten to `enforced` when the
   team is ready.

## What Compass 1.0 does NOT claim

Equally important. Honest scope is what makes the promise credible.

- **Compass does not prove software correctness.** It enforces that
  acceptance is stated and tested, that evidence exists and is the right
  kind, and that the route is the right shape for the task. It does not
  reason about whether your code is correct — only your tests and reviewers do
  that.

- **Compass is not a replacement for CI/CD.** See guarantee 6. A
  production-bound project still needs its own test, lint, security, build,
  and deploy pipeline. Compass adds a *process-integrity* lane to that
  pipeline; it does not absorb it.

- **Compass is not a full autonomous-development governance system.** It
  governs how human-and-AI teams shape work; it does not police what AI
  agents do outside its pipeline.

- **Compass is not a universal process framework.** The methodology layer is
  general; the kit is concrete. Teams adopt and tune both. There is no claim
  it fits every team or every project unchanged.

## How the contract is honoured mechanically

| Guarantee | How |
|---|---|
| 1 (deterministic routing) | `compass route evaluate` — pure function over readings + policy |
| 2 (no silent guardrails) | `compass policy lint` + `compass check` both fail on missing CHECK_FNS implementation |
| 3 (typed, registered evidence) | `governance/guardrails.yml` declares per-gate accepted types; gates reference entries in the task's evidence registry by id |
| 4 (Spike safety) | Routing guardrail raises a conflict on unsafe exploration; `compass check` enforces the spike-conclusion + no-production-changed_files invariants on a Spike route |
| 5 (recorded approvals) | `human-approval` typed evidence with structured fields, validated at Land |
| 6 (CI lane, not CI itself) | `ci/README.md` + the reference workflow run alongside project CI; the docs say so explicitly |
| 7 (recoverable, gradient) | `docs/install-smoke-test.md`, `docs/five-minutes.md`, structured failure messages, `mode: advisory \| enforced` in `.compass/config.yml` |

## Versioning and stability

Compass 1.0 declares its policy and schema versions in `governance/*.yml` and
the task spine (`schema_version`). The CLI will warn — or in `enforced` mode,
fail — when it meets a task whose schema is not compatible with the running
CLI. Migration guidance ships with every breaking change.

This contract is the bar for 1.0. Future versions may *add* guarantees; they
must not weaken these without a major-version bump and a written migration
path.
