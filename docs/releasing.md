# Compass - Releasing

The procedure for cutting a Compass release. The mechanics live in
[`scripts/release.sh`](../scripts/release.sh); this file is the
human-readable guidance for invoking it and the lessons that pin a
release to a clean, reproducible artifact.

> **What this file is.** Generic operational guidance - apply it for
> every release. Frozen rc.1-era status tables and per-release "owed
> items" no longer live here; that history lives in git.

---

## The release procedure

**Compass follows semantic versioning.** The number describes the
compatibility promise, not the size of the change:

- **major** - something a caller could call stops working. Removing a command,
  a verb, a flag spelling or a spine key is a major bump however small the
  diff, and however few people it affects. 3.0.0 removed the retired command
  and flag spellings; "no adopters yet" was the reason it was cheap, not a
  reason to call it minor.
- **minor** - new capability, nothing removed.
- **patch** - a fix that changes no interface.

ADR-006 is the other half of this: backward compatibility is non-negotiable
*within* a major, so a new mechanism no-ops on projects that have not adopted
it, and a break is paid once, at a major, with the reason recorded.

1. **Bump the version** in every location that carries it. There are seven:

   | Location | Guarded by |
   |---|---|
   | `VERSION` (root) | `tests/test_version_consistency.py` |
   | `COMPASS_VERSION` in `cli/compass` | `tests/test_version_consistency.py` |
   | `COMPASS_VERSION` in `cli/compass_pkg/core.py` | `tests/test_version_consistency.py`, and `cli/compass` asserts equality with it at import time |
   | `.claude-plugin/plugin.json` `$.version` | `tests/test_version_consistency.py` |
   | `.claude-plugin/marketplace.json` `$.metadata.version` | `tests/test_version_consistency.py` |
   | `.claude-plugin/marketplace.json` `$.plugins[0].version` | `tests/test_version_consistency.py` |
   | The expected `compass --version` output in `docs/install-smoke-test.md` | `tests/test_version_consistency.py` and `tests/test_cli_surface_drift.py` |

   **And one more thing to edit, which is not a published location.**
   `EXPECTED_VERSION` in `tests/test_version_consistency.py` is hardcoded on
   purpose - reading it from `VERSION` would make the test self-maintaining
   and blind to the case it exists for, a release where nothing was bumped.
   Editing it is the deliberate act that says a release is intended, so it
   is part of the procedure even though it ships nowhere. Bumping the seven
   without it leaves the suite red.

   This table said six for two releases while there were seven, and then
   seven while the procedure needed eight edits. Do not trust the count
   here alone: `tests/test_version_guard_covers_every_location.py` derives
   the set from the files themselves and fails if the guard has no case for
   one of them, precisely so a stale table cannot let a partial bump
   through.

   Then update `EXPECTED_VERSION` in `tests/test_version_consistency.py`.
   That constant is hardcoded on purpose: reading it from `VERSION` would
   make the guard self-maintaining but blind to a release where nothing
   was bumped at all. (There used to be an `OLD_VERSIONS` set to extend
   here too. Nothing read it, and a missing comma had silently corrupted
   it, so it was removed rather than repaired.)

   A partial bump ships a plugin whose manifest disagrees with the CLI it
   installs, so do not skip running the suite after this step. The last
   row is the one that gets forgotten, because it lives in prose rather
   than in a manifest.

2. **`make clean`** - clears local noise (`__pycache__`, `*.bak`,
   `.DS_Store`, `.pytest_cache`, `_deltest`, `pytest-cache-files-*`).
   The release tarball must not carry any of these.

3. **`make test`** - must be green. The full test suite, including:
   - `tests/test_cli_surface_drift.py` (every CLI subcommand documented
     in the public CLI surface blocks - added in v1.2-era Issue B)
   - `tests/test_v1_2_narrative.py` (every v1.2.0 feature reflected in
     `AGENTS.md` and methodology - added in v1.2-era Issue C)
   - `tests/test_release_invariants.py` (the partial-version-bump guard
     + the `comparison-requirements` ADR-006 backward-compat fixture +
     `signals.yml` shape invariants)
   - All other existing tests (route selection, guardrail checks,
     evidence handling, Spike safety, CI exit codes, calibration,
     architecture coherence, etc.)

   If any of the drift-guard tests fail, **do not bump VERSION further.**
   A failed drift-guard means a public-facing artifact has not been
   updated for a behaviour change - the framework's own G3 (traceability)
   is at risk. Fix the docs to catch up, re-run, then bump.

4. **`make ci`** - must be green. Runs `compass policy lint` + `issue
   lint` + `check` across all tasks under `.compass/work/`. (`make ci`
   is what CI runs; failing it locally means CI will fail.)

5. **`make release`** - produces `dist/compass-<version>.tar.gz`.

   The release script:
   - Clears `dist/` of any prior tarball so you publish one artifact,
     not two.
   - Runs `validate.sh` + `policy lint` + the test suite + the
     examples-present check *before* packaging.
   - **Hard-fails (exit 1)** if the tarball contains any noise file
     (`.DS_Store`, `__MACOSX`, `__pycache__`, `*.bak`, `.pytest_cache`,
     `_deltest`, `pytest-cache-files-*`).
   - **Hard-fails** if any of the worked examples under `examples/` is
     missing its `.compass/work/<slug>/task.yml`. This was a real
     packaging bug in early releases: the `.compass/work` exclude was
     not root-anchored and silently stripped the example issue files.

6. **Inspect the tarball.** `tar -tzf dist/compass-<version>.tar.gz | less`
   - eyeballs are still useful even when the script's checks have
   passed.

7. **Distribute ONLY the tarball from step 5.** Do not zip the source
   tree from Finder, GitHub's "Download ZIP," or any other tool. Those
   zip the live working tree, including `__MACOSX`, `.DS_Store`,
   `.pytest_cache`, any `.bak` file, and any other dev noise. The
   release script is the one place the artifact is guaranteed clean -
   every other path round-trips through dirt.

   The previous two RC reviewers both flagged the same dirty zip; the
   fix is operational, not in code: ship `dist/compass-<version>.tar.gz`
   and only that.

8. **Verify the tarball OUT OF THE SOURCE TREE.** The final smoke test:

   ```bash
   cp dist/compass-<version>.tar.gz /tmp/
   cd /tmp && tar -xzf compass-<version>.tar.gz
   cd compass-<version>
   bash scripts/validate.sh
   python3 cli/compass policy lint
   python3 cli/compass ci
   ```

   All four commands must succeed against the extracted release. This is
   the v1 reviewer's recommendation: "run against the generated tarball,
   not the dirty source directory."

9. **Tag and publish.** The release-script run, the out-of-tree smoke
   test, and the four-locations version bump are the gate; tagging is
   the consequence.

---

## Supply-chain stance

[`docs/security.md`](security.md) is the canonical reference. The
release-time touchpoints:

- **Pin to a commit SHA, not a branch**, wherever Compass is consumed
  downstream (in CI workflows, in vendored copies, in plugin
  installations). A branch can be rewritten; a SHA cannot.
- **Mirror to a trusted location** for organisational use - a private
  fork or an internal package mirror - and pin to that mirror.
- **Review the diff between SHAs** before bumping the pin. Compass is
  small enough that this is realistic.

A release does not loosen these rules; if anything, a new release is
the moment to re-verify them.

---

## What defends each invariant

When a release commit touches code or docs, the suite has guards that
catch common drift:

| Invariant | Defender |
|---|---|
| All four version locations agree | `tests/test_release_invariants.py` (partial-bump guard) |
| Pre-v1.1.0 task.yml shapes still lint clean | `tests/test_release_invariants.py` (ADR-006 backward-compat, via the `tests/fixtures/comparison-requirements/` fixture) |
| `signals.yml` shape stays valid | `tests/test_release_invariants.py` (`design_smell` category, etc.) |
| Every CLI subcommand appears in the public CLI blocks | `tests/test_cli_surface_drift.py` (parses `compass --help`) |
| `docs/install-smoke-test.md` shows the current version | `tests/test_cli_surface_drift.py` (reads `VERSION`, asserts the smoke-test matches) |
| Every v1.2.0 capability named in CLAUDE.md is in AGENTS.md or methodology | `tests/test_v1_2_narrative.py` (coverage rule) |
| `install.sh` does not double-register hooks in a plugin-source repo | `tests/test_install_plugin_detection.py` |
| The release tarball contains no noise files | `scripts/release.sh` (built into `make release`) |

These tests are not formalities - they are what makes a Compass
release credibly reproducible. Run them; honour them.

---

## Historical note

The release-procedure substance above is preserved from the
1.0.0-rc.1 → 1.0.0 release checklist (see commit history). The
rc.1-era readiness status table and the per-release "owed items" list
that lived in that file are *resolved history* and live in git -
this file is now generic guidance.
