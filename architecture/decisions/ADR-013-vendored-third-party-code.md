---
id: ADR-013
title: Compass may redistribute third-party code inside the plugin, and a bundled copy takes precedence over any system copy
status: accepted
date: 2026-08-10
supersedes: ''
superseded_by: ''
---

## Context

Reaching a completed first triage required a machine to already have PyYAML
installed - the CLI's one hard dependency, and the only step of the
quickstart that could fail. It is the step a newcomer meets first, before
they have any reason to persist through it, and it fails silently in one
place worse than an error: on a machine that never had PyYAML,
`hooks/pre-tool.sh`'s acceptance-before-code check raised on the missing
import, the hook exited
silently, and the edit was allowed - a guardrail that looked like it was
enforcing G2 was not enforcing anything at all.

Two routes were open. Vendor a minimal YAML reader Compass would write and
maintain itself, or bundle an unmodified copy of PyYAML inside the plugin.
The first was assumed cheaper until the CLI's write path was read: `yaml.
safe_dump` appears at four sites, one of them the issue spine. A vendored
reader is not enough - the subset route needed an emitter too, and the
emitter would have to round-trip the parity set (135 `.yml` files, plus the
YAML frontmatter of every ADR - no `.yml` glob would have found that) without
changing a byte of meaning. That is a parser, an emitter, and a conformance
proof, not the one-session fix the guide estimated. Bundling makes none of
that necessary: the library parsing YAML after this change is the library
parsing it today, so there is nothing to prove agreement with.

Compass has never redistributed third-party code before. This is the first
time, and the architecture had no position on it - `architecture/ownership.md`
has no row for a component that is a version, an update obligation, and a
licence to carry correctly, rather than something Compass wrote.

## Decision

**Compass may bundle a third-party library inside the plugin's kit layer,
under stated conditions, and the bundled copy takes precedence over any
system-installed copy, deterministically.**

1. **What is bundled, and how.** PyYAML's pure-Python package, unmodified,
   pinned to an exact version (6.0.2), committed at `cli/vendor/yaml/` -
   taken directly from the upstream sdist's `lib/yaml/`. Its own licence
   travels beside it (`cli/vendor/LICENSE-PyYAML`, byte-identical to the
   sdist's `LICENSE`), and `THIRD-PARTY-NOTICES.md` at the repository root
   declares the package, the version, the upstream URL, the sdist's sha256,
   the licence, the path, and that it is unmodified. Only names that are not
   already in the Python standard library may ever be vendored this way,
   since the resolution mechanism below shadows the standard library too if
   it does not take care - PyYAML does not, and any future addition must be
   checked the same way.
2. **One resolution mechanism, written down once.**
   `cli/compass_pkg/__init__.py` inserts `cli/vendor` at `sys.path[0]` -
   position 0, ahead of `PYTHONPATH` and site-packages both. Because Python
   runs a package's `__init__` before any module inside it, every Python
   caller resolves the vendored copy by construction; there is no import
   path that bypasses it. The shell face is one function,
   `scripts/lib/compass-python.sh`'s `compass_python()`, which puts `cli/`
   on `PYTHONPATH` and knows nothing about where the vendored tree itself
   lives - that knowledge stays in the one file above. A repository fitness
   test (`tests/test_bundled_pyyaml.py` and the static check alongside it)
   walks every tracked file for a YAML import in any spelling and fails the
   build on a reader that invents its own answer to "where is the bundled
   copy" instead of going through one of these two.
3. **Precedence is unconditional.** The bundled copy wins over any
   system-installed PyYAML, at any version, and over a `PYTHONPATH` entry an
   adopter set for their own reasons - no fallback, no preference for a
   system copy, no warning when the two differ. `compass --version` reports
   the resolved version and its file path, so which copy is running is
   always a published fact rather than something a user has to go and find
   out.
4. **The cost, stated rather than left implicit.** Precedence means Compass,
   not the adopter, decides which parser version runs inside every one of
   Compass's own invocations. An adopter who pinned or patched their own
   system PyYAML - the exact posture `docs/security.md` recommends to them a
   few lines above this - has that choice shadowed. Two things bound it:
   the shadowing is process-scoped, so an adopter's other tooling and their
   system PyYAML itself are untouched; and the version is a pinned,
   published fact rather than something ambient.
5. **Ownership of currency is named, not implied.** The maintainer updates
   the vendored copy on one of two triggers - a PyYAML security advisory, or
   a contributor hitting a bug already fixed upstream. No cadence is
   promised. The update is an ordinary Compass issue: replace
   `cli/vendor/yaml/`, update the version and sha256 in
   `THIRD-PARTY-NOTICES.md` and `cli/vendor/README.md`, run the suite.

## Alternatives considered

| Alternative | Why considered | Why rejected |
|---|---|---|
| Vendor a minimal YAML subset - a reader Compass writes and maintains | Looked like less code than bundling an entire third-party library | The CLI writes YAML as well as reading it (four `safe_dump` sites); "minimal reader" was never true, and the real scope was a parser, an emitter, and a byte-for-byte parity proof across 135 files plus ADR frontmatter |
| Unpack PyYAML from a wheel or sdist at release time, rather than committing it | Keeps the repository's own tree smaller | `scripts/release.sh` builds its file list from `git ls-files`; a tree that only exists after a release-time step is invisible to that list and to every test that reads it. This repository has already shipped a tarball missing files it contained once - a release-time-only vendor tree is that exact failure mode, and it would turn every install into the error this issue removes |
| A git submodule for the vendored tree | Keeps the upstream provenance visible via git itself | `git ls-files` reports a submodule as a single gitlink; the tarball would carry an empty directory, and a marketplace install that clones the repository does not fetch submodules by default |
| A committed `.whl` on `sys.path` via zipimport | Avoids committing ~300KB of extracted source | `.gitignore` already ignores archives at the root, and the pattern is easy to widen by accident; a zip is not diffable, which damages rather than repairs the audit posture this issue also has to fix |
| Prefer a system-installed copy when present, bundle only as fallback | Seemed to respect an adopter's own environment more | Reintroduces exactly the two-behaviour, machine-dependent CLI this issue exists to remove - the parser that ran on the maintainer's machine would not be the one that ran on a fresh install, and nothing would prove the two agree |
| Warn when the bundled copy and a system copy disagree | A softer version of precedence, more transparent-seeming | Reintroduces the friction this issue exists to remove, and still leaves two behaviours to reason about rather than one |
| pip install into a target directory on first run | Keeps the repository unchanged; installs the dependency lazily | This is the pip step, only moved to happen automatically instead of by hand - it still requires network access and a working `pip`, which is exactly the failure mode on the machine this issue is for |

## Consequences

**Positive:**
- A machine with nothing but `python3` reaches a completed first triage -
  the quickstart is one command, and the pre-tool hook's acceptance-before-
  code check now runs on every machine instead of failing open on some of
  them.
- Every entry point - the CLI and the five shell surfaces that read YAML -
  resolves the same parser, the same version, deterministically. A
  divergence between `compass check` and a hook silently reading something
  else is structurally prevented, not merely discouraged.
- The parser is the one already in production use; there is no new parity
  risk to prove, because nothing about how YAML is parsed or written
  changed.

**Negative:**
- About twenty files and roughly 300KB of code Compass did not write now
  live in the repository and appear in every diff of `cli/`.
- Compass now controls which PyYAML version runs inside its own processes,
  everywhere it runs - an adopter's own pin or patch on their system PyYAML
  is shadowed inside Compass's invocations, bounded as stated above.
- The C extension is not bundled, so `yaml.__with_libyaml__` is `False`
  under the bundled copy and `CSafeLoader` is unavailable - slower on large
  files. Nothing in `cli/` uses it today; every call site is `safe_load`,
  `safe_dump`, or `YAMLError`.
- Carrying someone else's code carries their security fixes too. Nobody
  owned that before, because until now there was nothing to own.

**Neutral / follow-on:**
- `architecture/ownership.md` still has no row naming who keeps a
  redistributed dependency's currency, beyond what this record states. That
  row is issue `vendored-dependency-ownership`, written so
  `cli/vendor/README.md`'s answer lifts into it directly rather than being
  re-derived. It matters because an adopter gets a PyYAML security fix only
  when Compass ships a new copy, and nobody is currently watching for that.
- The five pre-existing shell readers that embed their own Python instead of
  calling the CLI (`docs/portability.md`'s "call the kit, do not
  reimplement it") are unchanged in shape by this decision - they still
  embed a reader - but now all resolve the bundled copy through one shared
  mechanism rather than five independently-written ones. Migrating them to
  call the CLI instead is issue `shell-readers-use-the-kit`; this record
  does not decide it.

## References

- `cli/vendor/README.md` - what is vendored, its provenance, and who updates
  it, written so this record and that file agree.
- `THIRD-PARTY-NOTICES.md` - the declaration: package, version, URL, sha256,
  licence, path, unmodified.
- `docs/security.md` §"CLI dependencies" and §"Supply-chain stance" - the
  corrected audit posture: nothing installs onto an adopter's Python path,
  and how to reproduce and verify the vendored tree.
- `docs/portability.md` - the adapter contract's clause for a port that
  embeds Python parsing YAML.
- `.compass/work/zero-friction-install/technical-design.md` - the design record this
  ADR is drawn from (DD-1 through DD-3, DD-7), including the full cost/
  benefit reasoning behind each alternative above. `.compass/work/` is
  gitignored in this repository, which is exactly why this decision is
  recorded here as well rather than only there.
- **ADR-006** (backward compatibility is non-negotiable) - an adopting
  project that never touches this surface sees no behaviour change; TRC-F4
  and TRC-F5 hold that as scenarios.
- **ADR-002** (the framework grows by adding artifacts, not rules) - this
  decision adds no guardrail and no routing dimension; it is a supply-chain
  position, recorded the way Compass records its own structural decisions.
