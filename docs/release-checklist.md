# Compass — release checklist (1.0.0-rc.1 → 1.0.0)

This release is tagged **`1.0.0-rc.1`**. The framework's architecture, governance, CLI, tests, examples, and docs are all v1-shaped — but a few items still gate the move to `1.0.0`, and they belong to *this clone* of the repo, not the framework code. Tick them on the way to publication.

## Status of the v1 checklist (from the readiness review)

| Item | Status |
|---|---|
| CLI has automated tests for routing, guardrails, evidence, approvals, Spike conflict, CI exit codes | **Done** — `tests/` has 93 tests; `make test` is the canonical command. |
| Missing guardrail implementation fails in `policy lint` AND `check` | **Done** — the integrity rule fails closed in both places. |
| Spike has mechanical close-out checks | **Done** — S1 (conclusion required, valid decision, `next_task` if graduating) and S2 (no production `changed_files`); `compass check` enforces them on the Spike route. |
| Compass CI clearly documented as process validation, not project test validation | **Done** — `README.md`, `ci/README.md`, the safety contract, and a combined GHA pattern. |
| Evidence registry supports typed evidence | **Done** — top-level `evidence:` registry; gates reference by id. |
| Gates can require specific evidence types | **Done** — `gate_evidence_requirements` in `governance/guardrails.yml`. |
| Human approval records are structured and validated | **Done** — `human-approval` evidence type with approver/role/scope/decision/timestamp/conditions; the check rejects missing fields. |
| Claude Code install smoke test documented | **Done** — `docs/install-smoke-test.md`. **Manual verification on a real Claude Code install is owed — see below.** |
| Five-minute onboarding page | **Done** — `docs/five-minutes.md`. |
| Route examples used as regression fixtures | **Done** — `tests/fixtures/routes/`. |
| Failure messages include fix guidance | **Done** — every check failure prints `what / why / fix`. |
| Policy/schema versions explicit | **Done** — `VERSION` (CLI), `version:` in governance YAML, `schema_version:` in task.yml; the CLI rejects a major mismatch. |
| Security note for local hooks and CI usage | **Done** — `docs/security.md`. |

## What still owes a human (you) before tagging 1.0.0

These cannot be cleared in code. They need running against the real world.

- [ ] **Run the install smoke test on a real Claude Code session.** Follow `docs/install-smoke-test.md` end to end — install, frame a tiny test task, confirm `task.yml` / `route.md` / `.compass/current-task` all appear, run `compass check` against it. The static install test only proves the file paths resolve; this proves Claude Code picks the commands up.
- [ ] **Pilot Compass on at least one real task per category** (Express, Standard, Expedition). Set `mode: advisory` in `.compass/config.yml` first so it does not block. Watch what the team trips on. Capture re-frames; run `compass calibration` after a week or two.
- [x] **Replace the placeholder repo URL** (`<YOUR-ORG-OR-FORK>`) in `README.md`, `docs/quickstart.md`, and `docs/install-smoke-test.md` with the real Compass repository URL before publication.
- [ ] **Audit any project guardrails** the team adds before turning on `mode: enforced`. A project-added guardrail must reference a check the CLI implements (the integrity rule is enforced, but reviewing the policy by eye still matters).
- [ ] **Pin to a commit SHA in CI**, not a branch — `ci/README.md` and `docs/security.md` describe the supply-chain stance.

## Releasing

When the items above are closed:

1. Bump `VERSION` (and the CLI's `COMPASS_VERSION`) to `1.0.0` (drop `-rc.1`).
2. `make clean` — clears any local noise (`__pycache__`, `*.bak`, `.DS_Store`,
   `.pytest_cache`).
3. `make test` — must be green.
4. `make ci` — must be green.
5. `make release` — produces `dist/compass-1.0.0.tar.gz`. The script:
   - clears `dist/` of any prior tarball so you publish one artifact, not two;
   - runs `validate.sh` + `policy lint` + the test suite + the
     examples-present check *before* packaging;
   - **hard-fails** (exit 1) if the tarball contains any noise file
     (`.DS_Store`, `__MACOSX`, `__pycache__`, `*.bak`, `.pytest_cache`,
     `_deltest`, `pytest-cache-files-*`) — it does not print and continue;
   - **hard-fails** if any of the five worked examples is missing its
     `.compass/work/<slug>/task.yml`. This was a real packaging bug in
     `rc.1`: the `.compass/work` exclude was not root-anchored and silently
     stripped the example task files.
6. Inspect: `tar -tzf dist/compass-1.0.0.tar.gz | less`.
7. **Distribute ONLY the tarball from step 5.** Do not zip the source tree
   from Finder, GitHub's "Download ZIP," or any other tool. Those zip the
   live working tree, including `__MACOSX`, `.DS_Store`, `.pytest_cache`,
   any `.bak` file, and any other dev noise. The release script is the one
   place the artifact is guaranteed clean — every other path round-trips
   through dirt. The previous two RC reviewers both flagged the same dirty
   zip; the fix is operational, not in code: ship `dist/compass-<ver>.tar.gz`
   and only that.
8. Verify the tarball one more time, OUT OF THE SOURCE TREE:

   ```bash
   cp dist/compass-1.0.0.tar.gz /tmp/
   cd /tmp && tar -xzf compass-1.0.0.tar.gz
   cd compass-1.0.0
   bash scripts/validate.sh
   python3 cli/compass policy lint
   python3 cli/compass ci
   ```

   All four commands must succeed against the extracted release. This is the
   final smoke test the v1 reviewer asked for: "run against the generated
   tarball, not the dirty source directory."
9. Tag and publish.

The release script (`scripts/release.sh`) is the one canonical way to build
the tarball.
