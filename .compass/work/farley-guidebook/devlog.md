# Devlog — farley-guidebook

> **Task:** Carry `docs/proposals/farley-guidebook.md` through the pipeline — deliver the five-candidate shortlist (A1, B1, A2, C1, C2). · **Opened:** 2026-05-25
> Append-only. Newest at the bottom.

---

## 2026-05-25 17:55 — Frame

- **Event:** Needle ran; route computed.
- **Route:** Expedition (swarm) — see `route.md` revision 1.
- **Readings:** blast radius `cross-cutting`, terrain `brownfield-mapped`, magnitude `large`, intent `delivery`, role `engineer`, `touches: [public-api]`.
- **Composed candidate via:** `RS-SHAPE-004` (large → expedition; *"Large work — full weight, plausibly parallel."*).
- **Routing guardrails fired:** none. (`cross-cutting` doesn't trip the `critical` floors; `public-api` isn't on `RG-FLOOR-003/004/005` lists; engineer role — no role rule fires.)
- **Gates seeded:** `verify.correctness`, `verify.governance`, `verify.traceability`, `verify.regression`, `verify.security`, `verify.clarity`, `verify.claims` — all pending.
- **Architecture loaded:** 3 narrative artifacts + 8 ADRs into `architecture-loaded.yml`. ADR-002/004/006/007 are the load-bearing decisions the proposal anchors against.
- **Owed backfills:** none.
- **Next:** Specify — formalise the five candidates as Given/When/Then scenarios with stable SCN ids and intent links, plus the absent-by-design scenarios (e.g. old evidence without `attempts` passes G4 trivially; empty fitness set is a valid state).

## 2026-05-25 18:10 — Specify

- **Event:** scenarios authored — full BDD discovery per the Expedition Specify weight.
- **Artifact:** `spec.feature.md` — 37 scenarios in 7 groups (A through F + failure modes), with 13 intent ids (INT-1…INT-9 deliver the five candidates and their sub-goals; INT-10…INT-13 are the hard-line guards). Coverage ledger added at the foot.
- **task.yml:** `scenarios:` block populated — every scenario carries id + title + intent (G3 traceability open for Build to fill `tests:` per scenario).
- **Independence groups (for distribution):** A=A1 (intermittent-test integrity), B=A2 (fitness functions), C=B1 (TDD-as-design rebalance), D+E=C1+C2 (skill enrichments — pair into one stream), F+failure-modes are cross-cutting integration scenarios run at Land.
- **Open questions surfaced for Clarify:** location/shape of the quarantine registry (A1); whether `command-passes` accepts env/timeout knobs (A2); whether to generalise the route-promotion floors for `verify.fitness` beyond the two `verify.analyze` mirrors (A2); how to enumerate the `design_smell` signal patterns precisely (B1); whether B1's coverage-floor caveat lives in `guardrails.yml` comments or only in `evidence-gates` (B1); whether a new ADR is owed for the fitness-functions pattern.
- **Next:** Clarify.

## 2026-05-25 18:30 — Clarify

- **Event:** full pass — 11 questions raised, all resolved. The spec passes self-QA and governance QA against guardrails G1–G5, strategies S1/S3/S4, and ADRs 002/004/006/007.
- **Artifact:** `clarifications.md` — 11 entries, all `resolved`.
- **Headline resolutions:**
  - Q3: `verify.fitness` floor is *broader* than `RG-FLOOR-004` (cross-cutting OR critical; plus the `touches_any` irreversible-surface list). Rationale recorded — fitness is more naturally relevant on cross-cutting changes than coherence is. New floor ids reserved: `RG-FLOOR-006` (blast_radius) + `RG-FLOOR-007` (touches_any).
  - Q6: a new ADR (candidate **ADR-009**) is owed for the fitness-functions pattern. Working title *"Architectural fitness functions are project guardrails, not framework guardrails."* Drafted in Plan.
  - Q7: A1's `no-trusted-rerun` informs the existing `verify.governance` gate as a check under G4 — **no new gate**. ADR-007's separate-gate-per-check pattern is *not* applied uniformly; A1 is universal across routes and so deserves a universal gate, not a route-promoted one.
  - Q9: failure semantics tightened — `attempts > 1` without `rerun_without_change` marker is **fail** (the conservative interpretation: incomplete evidence does not clear G4). TRC-FM3 updated in `spec.feature.md` and `task.yml`.
- **Deferred to Plan as DDs (with recommendations):** quarantine registry location/shape (Q1 — recommend `governance/quarantine.yml`), `command-passes` knobs (Q2 — recommend `command:` + optional `timeout_seconds: 300`).
- **Route still fits:** Clarify revealed no scope/magnitude that would re-frame. Expedition (swarm) stands.
- **Definition of Ready:** all six boxes checked.
- **Next:** Plan.

## 2026-05-25 18:55 — Plan

- **Event:** technical approach + 9 design decisions + governance check + distribution map produced.
- **Artifacts:** `plan.md` (4-stream decomposition; 9 DDs; governance verdict **pass**) and `distribution-map.md` (4 streams: A intermittent-tests, B fitness functions, C strategy+skill rebalance, D cross-cutting verification).
- **Design decision highlights:**
  - DD-1: `governance/quarantine.yml` (new file; shipped empty; lint-validated).
  - DD-2: `command-passes` knobs minimal — `command:` (required) + `timeout_seconds:` (optional, default 300). Shell=True. Env knobs deferred.
  - DD-4: `verify.fitness` floor is *broader* than `verify.analyze`'s — `RG-FLOOR-006` matches `blast_radius: [cross-cutting, critical]`; `RG-FLOOR-007` matches the irreversible-domain `touches_any`. Rationale recorded.
  - DD-5: `command-passes` registers under G4 (no sixth guardrail; ADR-002 honoured).
  - DD-6: vacuous-clear pattern for `verify.fitness` when project declares zero fitness functions — emits a `command-output` evidence entry "0 project guardrails; clearing by vacuity".
  - DD-7: `cmd_tdd_green` detects "no source change between runs" via a stable SHA-256 of the source tree; stored in an `evidence/.tdd-state.json` sidecar.
  - DD-8: ADR-009 reserved — *"Architectural fitness functions are project guardrails, not framework guardrails."*
  - DD-9: no `task.yml` `schema_version` bump — `attempts`/`rerun_without_change` are additive fields on `test-run` evidence (`additionalProperties: true` is the existing contract).
- **Governance check:** **pass** across G1-G5, ADR-002/004/006/007, routing policy, all four method strategies. S5 (this task's own addition) is followed by construction. No marketer in play; voice/positioning strategies n/a. Project strategies empty; no addition proposed. `compass policy lint` on current governance: **pass**.
- **Distribution map:** 4 streams; no cap fires (cross-cutting, not critical). Stream-A, stream-B, stream-C run in parallel; stream-D runs sequentially after the A→B→C integration. Branch names recorded. Section-level non-collision analysis recorded — no semantic conflicts predicted on shared files (`guardrails.yml`, `strategies.md`, `skills/evidence-gates/SKILL.md`).
- **Next:** Distribute.

## 2026-05-25 19:05 — Distribute

- **Event:** swarm worktrees created — 4 streams, branched from `main@af0facf`. No cap fired (`cross-cutting`, not `critical`; route-cap is 6, config-max is 6, actual is 4).
- **Topology:** swarm (4 streams; one builder per worktree + one orchestrator).
- **Worktree-to-stream-to-scenario assignment (from `distribution-map.md`):**

| Stream | Worktree | Branch | Scenarios |
|---|---|---|---|
| stream-A | `../.compass-worktrees/farley-guidebook-stream-A` | `compass/farley-guidebook/stream-A-intermittent-tests` | TRC-A1, A2, A3, A4, A5, A6, A7, FM2, FM3 (9) |
| stream-B | `../.compass-worktrees/farley-guidebook-stream-B` | `compass/farley-guidebook/stream-B-fitness-functions` | TRC-B1, B2, B3, B4, B5, B6, B7, B8, FM1 (9) |
| stream-C | `../.compass-worktrees/farley-guidebook-stream-C` | `compass/farley-guidebook/stream-C-tdd-design-rebalance` | TRC-C1, C2, C3, C4, C5, C6, D1, D2, E1, E2, E3 (11) |
| stream-D | `../.compass-worktrees/farley-guidebook-stream-D` | `compass/farley-guidebook/stream-D-cross-cutting-verification` | TRC-F1, F2, F3, F4, F5, F6, F7, FM4 (8) |

- **Builder rule (enforced):** each builder works *only* inside its assigned worktree; cross-stream needs route through the orchestrator.
- **Orchestrator role:** watches for stream convergence on shared surfaces (`governance/guardrails.yml`, `governance/strategies.md`, `skills/evidence-gates/SKILL.md` — see distribution-map §2). Writes no feature code. Will run `scripts/integrate.sh farley-guidebook` at Land in order A → B → C, then D runs against the integrated branch.
- **Next:** Build — `/compass:build` launches builder agents in each worktree.

## 2026-05-25 19:15 — Build (launch)

- **Event:** three builder agents launched in background, one per worktree. Stream-D held back per Plan §1 — runs against the integrated A+B+C state at Land.
- **Charters issued:**
  - **stream-A** (worktree `farley-guidebook-stream-A`): 9 scenarios (TRC-A1…A7, FM2, FM3). Owns `cmd_tdd_green` extension, `no-trusted-rerun` CHECK_FN, `governance/quarantine.yml` (new file), S5 in `strategies.md`. DDs that apply: DD-1, DD-3, DD-7, DD-9.
  - **stream-B** (worktree `farley-guidebook-stream-B`): 9 scenarios (TRC-B1…B8, FM1). Owns `command-passes` CHECK_FN, `verify.fitness` gate recognition + vacuous-clear, `RG-FLOOR-006/007`, ADR-009. DDs that apply: DD-2, DD-4, DD-5, DD-6, DD-8.
  - **stream-C** (worktree `farley-guidebook-stream-C`): 11 scenarios (TRC-C1…C6, D1, D2, E1, E2, E3). Owns S2 amend, `design_smell` signal category, coverage-floor inline caveat, three skill enrichments. No DDs of its own — judgement-side rebalance.
- **Charter boundaries enforced in each prompt** to prevent cross-stream collision on the three shared files (`governance/guardrails.yml`, `governance/strategies.md`, `skills/evidence-gates/SKILL.md`).
- **Each builder is instructed:** commit often (prior task lost work on socket disconnects), record `tests:` and `changed_files:` in task.yml as they go, the final suite must pass before they signal done.
- **Next:** monitor builder completions. Orchestrator integrates at Land via `scripts/integrate.sh farley-guidebook` once all three are green.

## 2026-05-25 19:37 — edit: /Users/jed/dev/.compass-worktrees/farley-guidebook-stream-A/tests/test_intermittent_tests.py

- **Tool:** Write

## 2026-05-25 19:37 — edit: /Users/jed/dev/.compass-worktrees/farley-guidebook-stream-A/governance/strategies.md

- **Tool:** Edit

## 2026-05-25 19:38 — edit: /Users/jed/dev/.compass-worktrees/farley-guidebook-stream-B/tests/test_fitness_functions.py

- **Tool:** Write

## 2026-05-25 19:38 — edit: /Users/jed/dev/.compass-worktrees/farley-guidebook-stream-C/tests/test_strategies_s2_design_role.py

- **Tool:** Write

## 2026-05-25 19:38 — edit: /Users/jed/dev/.compass-worktrees/farley-guidebook-stream-B/tests/test_verify_fitness_route_promotion.py

- **Tool:** Write

## 2026-05-25 — Build (stream-B complete)

**All 9 stream-B scenarios green. 298 tests pass (2 pre-existing skips).**

### What was built

- `cli/compass` — `_check_command_passes` function registered in `CHECK_FNS`; `_lint_errors_guardrails` extended to validate `command-passes` params on project guardrails only (framework's G4 is exempt from the params requirement).
- `governance/guardrails.yml` — `command-passes` added to the `checks:` registry; added to G4's `checks:` list; `verify.fitness: [test-run, command-output]` added to `gate_evidence_requirements:`.
- `governance/routing-policy.yml` — `RG-FLOOR-006` (blast_radius: [cross-cutting, critical] → add_gate: verify.fitness) and `RG-FLOOR-007` (touches_any irreversible domains → add_gate: verify.fitness) added after RG-FLOOR-005.
- `architecture/decisions/ADR-009-fitness-functions-are-project-guardrails.md` — new, status: proposed.
- `architecture/decisions/README.md` — ADR-009 indexed.
- `architecture/system-context.md` — boundary condition #3 updated to reference ADR-009 and RG-FLOOR-006/007.
- `skills/evidence-gates/SKILL.md` — new section "Architectural fitness functions and the verify.fitness gate" added before Anti-patterns.
- `tests/test_fitness_functions.py` — 12 tests (TRC-B1, B2, B3, B6, B7, FM1).
- `tests/test_verify_fitness_route_promotion.py` — 16 tests (TRC-B4, B5, B8).
- `tests/fixtures/route-baseline.yml` — expedition entry updated to include `verify.fitness` in expected_gates (correct consequence of RG-FLOOR-006 firing on cross-cutting blast_radius).

### Notable decisions during build

1. **Test approach** — Tests use `subprocess.run([sys.executable, CLI_PATH, ...])` throughout, matching the existing test pattern. Initial attempt used `import cli.compass` directly; that failed because the CLI has no `.py` extension and is not a Python package.

2. **`_make_project` helper** — copies the real shipped `guardrails.yml` and patches only the `project:` section. The initial version built a minimal `guardrails.yml` with `defaults: []`; this caused vacuous-clear tests to behave unexpectedly (the `command-passes` check was never in any guardrail's `checks:` list so `compass check` never ran it).

3. **Policy lint false failure on G4** — `_lint_errors_guardrails` originally iterated over `defaults + project` when validating `command-passes` params. G4 legitimately uses `command-passes` without per-guardrail `params:` (it reads params from project guardrails at runtime). Fixed by moving the params validation to a separate loop that covers only `project:` guardrails.

4. **Route baseline update** — `tests/fixtures/route-baseline.yml` expedition entry did not include `verify.fitness`. This is intentional: RG-FLOOR-006 was added in this stream, so the expedition's expected gates legitimately gained `verify.fitness`. The file's own comment says "the diff is the audit trail."

5. **`compass policy lint` binary vs local** — `which compass` resolves to the installed plugin binary, not the worktree's `cli/compass`. The installed binary does not have stream-B's changes, so `compass policy lint` (system) fails with "command-passes not in CHECK_FNS". `python3 cli/compass policy lint` (local) passes cleanly. The verifier should run `python3 cli/compass` not `compass`.

### Evidence on disk

```
evidence/red.json    — first genuine red (TRC-B1 pre-rewrite; tests were actually red before code was written)
evidence/green-TRC-B1.json through evidence/green-TRC-FM1.json — 9 per-scenario green records
```

### Stream-B handoff

All 9 scenarios are implemented and tested. `python -m pytest tests/ 2>&1 | tail -2` → `298 passed, 2 skipped`. `python3 cli/compass policy lint` → PASS. `python3 cli/compass task lint --task farley-guidebook` → PASS. Ready for integration.

## 2026-05-25 19:38 — edit: /Users/jed/dev/.compass-worktrees/farley-guidebook-stream-C/governance/strategies.md

- **Tool:** Edit

## 2026-05-25 19:38 — edit: /Users/jed/dev/.compass-worktrees/farley-guidebook-stream-A/cli/compass

- **Tool:** Edit

## 2026-05-25 19:39 — edit: /Users/jed/dev/.compass-worktrees/farley-guidebook-stream-C/tests/test_skill_tdd_discipline_listen.py

- **Tool:** Write

## 2026-05-25 20:11 — edit: /Users/jed/dev/compass/cli/compass

- **Tool:** Edit

## 2026-05-25 20:11 — edit: /Users/jed/dev/compass/governance/guardrails.yml

- **Tool:** Edit

## 2026-05-25 20:12 — edit: /Users/jed/dev/compass/governance/guardrails.yml

- **Tool:** Edit

## 2026-05-25 20:13 — edit: /Users/jed/dev/compass/skills/evidence-gates/SKILL.md

- **Tool:** Edit

## 2026-05-25 20:15 — edit: /Users/jed/dev/compass/tests/test_stream_c_no_new_checks_or_gates.py

- **Tool:** Edit

## 2026-05-25 20:16 — edit: /Users/jed/dev/compass/cli/compass

- **Tool:** Edit

## 2026-05-25 20:18 — edit: /Users/jed/dev/.compass-worktrees/farley-guidebook-stream-D/tests/test_farley_invariants.py

- **Tool:** Write

## 2026-05-25 — Land

- **Event:** task closed — farley-guidebook landed on main.
- **Merge sequence:** A → B → C → D (orchestrator-resolved conflicts on `cli/compass` CHECK_FNS, `governance/guardrails.yml` G4.checks, `skills/evidence-gates/SKILL.md` sections — all additive unions; integration tests updated baseline to acknowledge legitimate sibling additions).
- **BF-1 paid:** `cli/compass` cmd_tdd_green now always records `rerun_without_change` when attempts > 1 (true/false per source-hash). Stream-A's TRC-A1 green.json regenerated (attempts:1).
- **BF-INTEGRATION paid:** Stream-D's 8 invariant tests added to `tests/test_farley_invariants.py`; combined regression on integrated main: **371 passed, 2 skipped**.
- **Final compass check:** **PASS — all 13 checks passed**, including the new `no-trusted-rerun`, `command-passes` (vacuous-clear), `dod-evidence-typed`.
- **Gates closed:** all 8 gates (correctness, governance, traceability, regression, security, clarity, claims, fitness) GREEN with typed evidence pointers in `task.yml.gates`. `verify.fitness` cleared by vacuity (DD-6) — framework declares no project guardrails.
- **What landed:** 5 candidates from the Farley proposal — A1 (intermittent-test integrity via S5 + no-trusted-rerun check + governance/quarantine.yml), A2 (architectural fitness functions via command-passes + verify.fitness gate + RG-FLOOR-006/007 + ADR-009), B1 (TDD-as-design rebalance via S2 amend + tdd-discipline skill + design_smell signal), C1 (example-first refinement in bdd-specification skill), C2 (commit-vs-acceptance vocabulary in evidence-gates skill).
- **Surface added (USP-5 budget):** 1 strategy id (S5), 1 gate (verify.fitness), 2 check names (no-trusted-rerun, command-passes), 1 evidence-record field (attempts + rerun_without_change), 1 signal category (design_smell), 1 ADR (ADR-009). No new guardrail, no new routing dimension (ADR-002 honoured).
- **task.yml.status:** `landed`. **task.yml.backfills:** both `paid`. **No owed obligations remain.**
- **Worktrees:** stream-A/B/C/D kept (`--no-clean` used during integration); orchestrator can remove with `git worktree remove` after final review.
