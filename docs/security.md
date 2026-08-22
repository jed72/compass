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

## Project governance is executable code

A team can add project-specific guardrails to `governance/guardrails.md` and
`governance/guardrails.yml`. **Treat those files as code, not as
configuration**, because one of them can run commands.

`command-passes` is a shipped check whose parameter is the command to run.
A project guardrail declaring it looks like this:

```yaml
checks: [command-passes]
params:
  command: "python3 scripts/architecture-fitness.py"
```

`compass check` runs that string with `subprocess.run(..., shell=True)` from
the project root, with whatever permissions the process already has. Anything a
shell can do, a project guardrail can do.

### Two defences this guide used to claim, and why they do not hold

This section previously argued that a hostile guardrail could not run code,
for two reasons. An outside review of 3.2.0 showed both were wrong, and they
are recorded here rather than quietly deleted.

**"A hostile guardrail cannot just name a check and have the CLI run it."**
That is true of a check the project invents - the name must resolve to an
implementation in the CLI, and adding one is a change to a different repository
under separate review. It is not true of `command-passes`, which is already
implemented and whose entire purpose is to run what it is given. The registry
constrains which *kinds* of check exist. It does not constrain what one of them
executes.

**"It has to come through pull-request review."** Continuous integration
normally runs on a pull request **before** it is approved. A contribution from
a fork can therefore reach the runner without anyone having read it, which is
the point at which review was supposed to be the boundary.

### What Compass does about it now

Three things sit in front of that execution path, and they are not equally
strong. Knowing which is which is the point of this section.

**Running a project command is opt-in, and the default is off.** Add this to
`.compass/config.yml` to turn it on:

```yaml
allow_project_commands: true
```

**This is not a security control, and it is important not to read it as one.**
The setting lives in your repository, so a hostile pull request can add the
command and the opt-in in the same diff. What it defends against is accidents
and defaults - a project executing something it never asked to execute.

**The refusal on an untrusted contribution is the strongest thing here.**
Compass decides, from the CI runner's own state, whether the contribution being
checked is trusted, and refuses to run any project command unless it is
**positively confirmed** as trusted. Nothing in your repository is consulted on
that path - including the opt-in above.

The rule is confirmation, not suspicion, and the difference matters. Compass
does not ask "has anything told me this is untrusted?" - a contribution could
answer that by deleting the signal. It asks "has anything confirmed this is
trusted?", and an absent, blank or unreadable signal confirms nothing, so it
refuses. On GitHub the confirmation comes from the runner's event payload, which
must be readable and must sit outside the checkout; a payload path pointing back
into your repository is rejected rather than believed.

On a provider Compass does not recognise it has nothing to read, so your project
commands will not run until you say so:

```yaml
# In your CI configuration - NOT in a file inside the repository, which a
# contribution could edit.
env:
  COMPASS_CONTRIBUTION_TRUST: trusted
```

**A safer way to declare the work.** Name a script instead of writing a shell
string, and no shell is involved at all - arguments are passed as a list rather
than interpolated:

```yaml
checks: [command-passes]
params:
  script: scripts/architecture-fitness.py
  args: ["--strict"]
```

The script path is resolved before it is used, and a path that resolves outside
the project root is refused - a symlink inside the project pointing out of it
does not get past this. The `command:` form still works, and it still runs a
shell; prefer `script:` where the shape allows.

### What you still have to configure yourself

- **Declare your workflow's token permissions.** Compass cannot do this for
  you. Without a `permissions:` block your workflow gets whatever your
  repository or organisation default is, and a project command inherits it. The
  reference workflow in `ci/github-actions.yml` declares
  `permissions: contents: read`; copy that posture and widen it only where a
  job genuinely needs more.
- **Review `governance/` changes as you would review a script**, especially any
  `params.command`. A one-line YAML addition can be a one-line shell command.
- **Decide what your CI does on untrusted pull requests.** Restricting workflow
  triggers for fork pull requests, or requiring approval before workflows run,
  is a control Compass cannot apply on your behalf.

### Where this came from

The two defences above were described in this guide as holding when they did
not. An outside review of 3.2.0 found both, the description was corrected
first, and the mechanism described on this page landed in
[issue #65](https://github.com/jed72/compass/issues/65) - the explicit opt-in,
the refusal on untrusted contributions, the script form, and the token
permissions in the reference workflow.

One recommendation from that review was considered and not taken: an allowlist
of permitted command strings. It keeps the shell and constrains only the
strings that reach it, which is weaker than not invoking a shell at all, so the
script form above was built instead.

### The limit, stated plainly

**A contributor with push access to your repository is not defended against.**
They can add a command, set the opt-in, and merge. No arrangement of in-repo
configuration defends a repository against its own contents - GitHub's own
answer to the same problem is to withhold secrets from forks rather than to
trust a setting.

**And the refusal is not unforgeable either.** It is worth being exact about
this, because the obvious way to describe it would be wrong. On a
`pull_request` event GitHub runs the workflow from the pull request's own merge
ref, so the contribution controls its workflow file - and therefore controls
every environment variable the Compass process sees. Compass makes the cheap
attacks fail: blanking `GITHUB_EVENT_NAME` or `CI` refuses, declaring
`COMPASS_CONTRIBUTION_TRUST=trusted` does not override GitHub's own report of a
fork, and a payload inside the checkout is rejected. What remains is that a
contribution could write a forged event payload outside the checkout and point
at it. That is a real gap, it takes deliberate work rather than one line of
YAML, and you should know it is there.

What actually bounds a fork pull request is not this at all: GitHub withholds
your secrets from fork pull requests and issues a read-only token on the
`pull_request` trigger. That is the boundary. Everything on this page reduces
what a contribution can reach and how easily; it does not replace GitHub's own
answer, and it is not a substitute for `pull_request_target` hygiene.

So what you get is a bounded reach: the default is off, the cheap forgeries
fail, a project can avoid the shell entirely, and the runner's token is narrowed
to what the job needs. That is not an impassable boundary, and this guide will
not describe it as one.

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

Compass publishes through the Claude Code plugin marketplace, and that install
path deserves the same supply-chain caution as any other
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
