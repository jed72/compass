# Install smoke test

A documented manual checklist to verify that a fresh Compass install works
end to end. A real Claude Code install cannot be smoke-tested in a sandbox -
the framework relies on the local Claude Code config and the user's
shell - so this is the procedure to walk by hand once.

This checklist covers the **install-from-source** path. Run it once after
`scripts/install.sh`, and again whenever you change how Compass is installed.
Each step lists the *expected output* so you can compare line by line. Common
gotchas are at the end. If you installed through the plugin marketplace
instead, steps 1 and 7 do not apply; the rest still does.

Throughout, `COMPASS_HOME` means the directory you cloned the framework
into - wherever `scripts/install.sh` lives.

---

## 1. Clone the framework and install the adapter layer

```bash
git clone https://github.com/jed72/compass.git
cd compass
bash scripts/install.sh --global       # or: bash scripts/install.sh --project DIR
```

Expected output (the message text may vary slightly; the shape is what
matters):

```
Compass installer
  source (COMPASS_HOME): /path/to/compass
  mode:                  global
  destination:           /Users/you/.claude
  link mode:             symlink

Installing adapter layer...
  linked  commands/compass -> /path/to/compass/commands
  linked  agents/compass -> /path/to/compass/agents
  linked  skills/compass -> /path/to/compass/skills
  registered hooks in /Users/you/.claude/settings.json (PreToolUse, PostToolUse, Stop)

Done. Compass is wired into Claude Code (global).
```

Verify the symlinks (or copies, with `--copy`) actually exist:

```bash
ls -la ~/.claude/commands/compass
ls -la ~/.claude/agents/compass
ls -la ~/.claude/skills/compass
```

Each should resolve into the `compass/` repo you cloned. The hook
registration should be visible in `~/.claude/settings.json` - three
entries naming `pre-tool.sh`, `post-tool.sh`, and `stop.sh` under
`$COMPASS_HOME/hooks/`.

## 2. Install the CLI's Python dependencies

```bash
pip install pyyaml               # required
pip install jsonschema           # optional but recommended
```

PyYAML is the CLI's only hard dependency. Without it, `compass` prints a
clear message and exits with code 3. `jsonschema` turns on full JSON
Schema validation in `compass policy lint` and `compass task lint`; the
built-in linter still runs without it.

To confirm:

```bash
python3 -c "import yaml; print(yaml.__version__)"
python3 -c "import jsonschema; print(jsonschema.__version__)"   # optional
```

## 3. Frame a test task in Claude Code

Open Claude Code in a directory you do not mind getting a `.compass/`
folder in (a scratch repo is ideal). Type:

```
/compass:frame "test installation"
```

Expected outcomes:

- A new task directory appears: `.compass/work/test-installation/` (the
  slug is derived from the title).
- That directory contains `delivery-approach.md` and `task.yml`. `task.yml` has a
  `readings:` block, a `route:` field, a `phases:` map, a `gates:` list,
  and `schema_version: "1.0"`.
- `.compass/current-task` exists at the project root and contains the
  one-line slug `test-installation`.

If `/compass:frame` is unknown to Claude Code, the adapter layer is not
on the Claude Code config path - re-check step 1.

## 4. Validate the governance YAML

```bash
python3 $COMPASS_HOME/cli/compass policy lint
```

Expected output ends in:

```
compass policy lint: PASS
```

A `FAIL` here means either the shipped `governance/*.yml` is corrupt
(rare - re-clone) or a project-local `governance/` exists and has a
problem (the CLI prefers project-local; `find_governance` walks up from
the cwd).

## 5. Check the CLI's version

```bash
python3 $COMPASS_HOME/cli/compass --version
```

Expected output:

```
compass 1.8.1 (task schema 1.0)
```

The schema version is what the CLI will accept in a `task.yml`. A
`task.yml` with a different *major* schema version makes
`compass check` fail closed.

## 6. Run the task-level check on the test task

```bash
python3 $COMPASS_HOME/cli/compass check --task test-installation
```

The check runs against an early-task state - Frame has run but Specify,
Build, and Verify have not. The check will report what is missing
honestly. Expected output shape:

```
compass check - task 'test-installation' (route: express)
[mode: enforced]

  G1 Tested before it lands
    FAIL suite-passed
         what: no test-run evidence in the registry - run `compass tdd-green` to record a passing suite
         why : Guardrail G1 (tested before it lands) requires a recorded green test run.
         fix : Run `compass tdd-green --scenario <SCN-ID> -- <your test command>` ...
  ...
compass check: FAIL - N of M check(s) failed.
```

That is the correct early-task state: the gates have not been cleared
yet because no work has been done. The structured `what / why / fix`
blocks are how the CLI guides you to the next move. If `compass check`
*errors* - a traceback, "could not find governance/", "no .compass/
directory found" - re-check steps 1 and 3.

## 7. Uninstall and reinstall

```bash
bash $COMPASS_HOME/scripts/install.sh --uninstall
```

Expected output:

```
Uninstalling...
  removed commands/compass
  removed agents/compass
  removed skills/compass
  unregistered Compass hooks from /Users/you/.claude/settings.json

Compass adapter layer removed. The methodology layer in /path/to/compass is untouched.
```

The methodology and kit layers (`docs/`, `governance/`, `routes/`,
`templates/`, `cli/`, `schemas/`) are unchanged - only the adapter
wiring is removed.

Now reinstall to confirm idempotency:

```bash
bash $COMPASS_HOME/scripts/install.sh --global
bash $COMPASS_HOME/scripts/install.sh --global       # second run
```

Both runs should succeed. The second run refreshes existing symlinks
in place and does not duplicate the hook entries in `settings.json`
(the script strips prior Compass entries before re-adding).

---

## Common gotchas

**PyYAML missing.** `compass: PyYAML is required but not installed.` The
CLI exits 3. Fix: `pip install pyyaml`. This is the only hard
dependency; without it nothing else runs.

**Claude Code's `~/.claude` does not exist yet.** `install.sh` creates
it. If you have never run Claude Code on the machine, the installer
will still wire everything correctly, but you may want to open Claude
Code at least once to confirm `settings.json` is in a place Claude
respects.

**An existing non-Compass `~/.claude/commands/compass` directory.** The
installer refuses to clobber files it did not create - it stops with:

```
  ERROR: ~/.claude/commands/compass exists and was not created by Compass - refusing to overwrite.
         Move it aside and re-run.
```

Move the offending directory aside (`mv ~/.claude/commands/compass
~/.claude/commands/compass.bak`) and re-run the installer.

**`jq` missing.** The installer uses `jq` to splice hooks into
`settings.json`. Without it, the install still completes, but the hook
registration is printed for manual paste-in. Install `jq` (`brew
install jq`, `apt install jq`, etc.) and re-run for the automatic path.

**`compass check` reports "no governance/ found."** The CLI looks for a
project-local `governance/` walking up from the cwd, and falls back to
the framework's shipped one next to the CLI script. If you have moved
or stripped the framework directory, point your CI step at the
correct CLI location (see `ci/README.md`).

**The hook blocks an edit unexpectedly.** That is the red-before-green
TDD strategy working - it means you tried to edit production code with
no failing test recorded for the current task. The fix is always:
write the test first, then `compass tdd-red -- <test cmd>`, then edit.
On a Spike route the hook does not block; if you want to suspend the
strategy for genuinely exploratory work, frame the task as a Spike.

If a step here fails in a way the docs do not anticipate, the failure
itself is signal - open an issue with the exact command, expected
output, and what you saw.
