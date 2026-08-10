# Security notes

Compass is small and inspectable, and most of its surface is plain
markdown. The places worth thinking about before you install it in a
sensitive environment are concentrated and short - this document is the
list.

---

## The hooks run locally with your user permissions

`scripts/install.sh` registers three hooks in Claude Code's
`settings.json` - `hooks/pre-tool.sh`, `hooks/post-tool.sh`, and
`hooks/stop.sh`. They are bash scripts that run on every relevant tool
call (Edit/Write/MultiEdit, and session end), inside your shell, with
your user's permissions. Read them before you install:

- `hooks/pre-tool.sh` - enforces the red-before-green TDD strategy by
  inspecting the current issue's `.red` marker and `.spike` marker. It is
  the one that can *block* an edit.
- `hooks/post-tool.sh` - appends to the issue devlog and clears markers.
- `hooks/stop.sh` - warns at session end if an issue is half-finished.

They are deliberately short and do not call out to the network. The
correct review posture is: open each one, read it top to bottom, and
confirm it does what its header claims. If anything looks off - a
network call you did not expect, a `curl | sh`, an unexplained path
write - do not install.

## Do not install Compass from an untrusted source

`scripts/install.sh` symlinks the framework's `commands/`, `agents/`,
and `skills/` directories straight into your Claude Code config. Those
files become instructions Claude executes against your repository. A
hostile fork is a hostile agent.

For organisational use:

- **Pin to a specific commit SHA, not a branch.** A branch can be
  rewritten; a SHA cannot. In CI, check out by SHA explicitly.
- **Mirror to a trusted location** (a private fork, an internal package
  mirror) and pin to *that*, so a takeover of the upstream cannot
  silently update what your team runs.
- **Review the diff between SHAs** before bumping the pin. Compass is
  small enough that this is realistic, in two parts: for Compass's own
  code, diff `cli/compass`, `cli/compass_pkg/`, `governance/`, and
  `schemas/` between the two SHAs, as before - the methodology layer is
  plain markdown, the kit layer is Compass's own Python plus one vendored
  third-party package, the adapter layer is bash and markdown. For the
  vendored tree, do not diff it between SHAs - it should not change except
  on a deliberate version bump. Reproduce it and compare against upstream
  instead - the full, runnable command is in `THIRD-PARTY-NOTICES.md` at the
  repository root, under "PyYAML" (download the pinned sdist, verify its
  hash, extract it, diff its `lib/yaml/` against `cli/vendor/yaml/`). It is
  an auditor's command, run once when you want to verify the vendored copy -
  it is not an install step, and nothing in Compass runs it for you.

## CLI dependencies

**Nothing is installed onto your Python path.** The CLI's only **hard**
dependency is **PyYAML**, and it travels inside the plugin - a pinned,
unmodified copy at `cli/vendor/yaml/`, declared in
`THIRD-PARTY-NOTICES.md` (version, upstream URL, sha256, licence). It is
only ever added to `sys.path` inside Compass's own processes
(`cli/compass_pkg/__init__.py` is the one place that happens), never to
your environment's site-packages. There is no `setup.py`, no `pip
install compass-cli`, no package that arrives in your site-packages as
a side effect of installing Compass - **if a Compass install puts a
package into your site-packages, that is the bug.**

**`jsonschema` is optional and not bundled.** It turns on full JSON
Schema validation in `compass policy lint` and `compass issue lint`;
the built-in linter runs without it. If you want it, `pip install
jsonschema` yourself - that one remains a genuine install, on your own
terms.

Audit the vendored PyYAML the way you audit any dependency you pull
into a sensitive environment - pin the version (already done: see
`THIRD-PARTY-NOTICES.md`), verify the hash if your policy requires it
(the sha256 is recorded there too), and reproduce it from upstream
yourself using the commands above rather than trusting the tree as
shipped, if that is your posture.

**The precedence cost, stated plainly.** Compass's own processes always
use the bundled PyYAML, at position 0 on `sys.path` - ahead of anything
else on the machine, deliberately and unconditionally, so the same
version runs everywhere Compass runs. If you have pinned or patched
your own system PyYAML for a reason of your own, following the advice
above, that choice is shadowed *inside Compass's own invocations*. It
is not shadowed anywhere else: this is process-scoped, so your other
tooling and your system PyYAML itself are untouched. The version
Compass is running is never a guess - `compass --version` prints it,
alongside where it resolved from.

## Project guardrails go through PR review

A team can add project-specific guardrails to `governance/guardrails.md`
and `governance/guardrails.yml`. In principle, a hostile project-added
guardrail could try to exfiltrate data via a check function. In
practice, it cannot, because of two layers:

1. **It has to come through PR review.** `governance/` lives in the
   project repository - every change to it is a code change like any
   other and goes through your normal code-review process.
2. **The CHECK_FNS implementation gate.** A guardrail in
   `guardrails.yml` declares a `check` by name; that check must have an
   implementation in `cli/compass`'s `CHECK_FNS` table. `compass policy
   lint` and `compass check` both fail closed if a declared check has
   no implementation. So a hostile guardrail cannot just *name* a check
   and have the CLI run it - adding a new check is a code change to the
   CLI itself, which is a separate repo and a separate review.

These two layers do not eliminate risk; they make it impossible for a
guardrail addition to be a one-line surprise. Treat the
`governance/` directory and the CLI's `CHECK_FNS` table as security-
relevant code, and review changes to them accordingly.

## Supply-chain stance

Compass is built so that the surface a malicious change could hide in
is small:

- The **methodology layer** is plain markdown - `docs/`,
  `governance/*.md`, `approaches/`, `templates/`. It cannot execute
  anything.
- The **kit layer** is Compass's own Python (`cli/compass`,
  `cli/compass_pkg/`) plus declarative YAML and JSON Schema in
  `governance/`, `schemas/`, plus one vendored, pinned, unmodified
  third-party package (PyYAML, at `cli/vendor/yaml/` - see "CLI
  dependencies" above). Compass's own code is easy to diff, easy to
  audit, the same way it always was; the vendored tree is reproduced
  from upstream and hash-verified instead of diffed between releases.
- The **Claude Code adapter layer** - `commands/`, `agents/`,
  `skills/`, `hooks/`, `CLAUDE.md` - is markdown and bash. The
  executable parts are the three hook scripts and the install script;
  the rest is instructions to an agent.

There is no Compass plugin marketplace today, and any future plugin or
skill marketplace should be treated with the same supply-chain caution
as any other code source. If Compass ever ships a mechanism for loading
third-party skills or commands, the same rules apply: pin to a SHA,
mirror to a trusted location, review the diff before bumping.

## A note on the `.compass/` directory

`.compass/work/` is the issue audit trail and is **committed to your
repo**, not scratch. That is deliberate - it is the evidence that
guardrails were cleared and that work was framed before it ran. The
test-run records, the human-approval entries, the devlog entries: they
are reviewable history. Treat them as you would any other repository
content. Do not paste secrets into a `command-output` evidence file or
into `devlog.md` any more than you would paste them into a commit
message.

---

If something here is wrong, missing, or under-stated for your
environment, the right response is to harden the install in your own
context rather than soften this document - Compass is small enough that
the safe configuration for one team is rarely far from the safe
configuration for another.
