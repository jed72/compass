"""The vocabulary rename: assess, plan, intent, technical-design.

Five words in this framework named more than one thing, or named a thing whose
own output disagreed with them:

  the stage that produces an `assessment:` block was called `triage`
  the stage whose key, skill and agent all say `plan` was commanded as `design`
  `design` named a command, an artifact, an artifact kind, a CLI verb and a
      role, and was the only overloaded word with no glossary entry
  `/compass:intent` wrote a file called `prd.md`
  `frame` was banned as a phase name and survived as a live machine key,
      because governance/*.yml is not a scanned surface

THE ORDER IS THE DESIGN. Every new spelling is accepted before any caller
switches to it - see design.md D2. These tests are written so the accept phase
can be green on its own.

Scenario ids trace to
.compass/work/the-vocabulary-rename/acceptance-criteria.md.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "cli"))

MAP = REPO_ROOT / "cli" / "migrate-map.yml"

# The six that move. `plan` and `verify` are deliberately absent: `plan` stays
# because the command moves TO it, and `verify` already agrees.
STAGE_RENAMES = {
    "frame": "assess",
    "specify": "define",
    "clarify": "refine",
    "distribute": "breakdown",
    "build": "implement",
    "land": "ship",
}
STAGE_UNCHANGED = {"plan", "verify"}


def _map():
    import compass_pkg  # resolves the bundled yaml
    import yaml
    return yaml.safe_load(MAP.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Group C - the map, and any copy of it
# ---------------------------------------------------------------------------

def test_trc_c1():
    """TRC-C1: the map carries the stage keys, and any copy is proven to match.

    The second half is the point. The guard that existed before this asserted
    `migrate.artifact_name_map() == artifacts` - and that function reads the
    map file whenever it can, so it compared the file to itself and the
    in-module fallback was never exercised. They agreed, all six entries; but
    this change adds to both, which is when such a guard gets relied on.
    """
    import compass_pkg  # noqa: F401
    from compass_pkg import migrate

    data = _map()
    keys = data.get("stage_keys")
    assert keys, (
        "cli/migrate-map.yml has no `stage_keys:` section. The stage keys are "
        "the one set of renames the map never covered, which is why they were "
        "never migrated. Sections present: %s" % sorted(data))
    assert keys == STAGE_RENAMES, (
        "the stage-key map is not the six renames this issue makes:\n"
        "  expected: %s\n  found:    %s" % (STAGE_RENAMES, keys))
    for k in STAGE_UNCHANGED:
        assert k not in keys, (
            "%r is in the rename map and must not be. `plan` stays because the "
            "command moves TO it - migrate-map.yml records that the artifact "
            "was `plan.md` in v1, so a later reader may take the key for a "
            "vestige and 'fix' it. `verify` already agrees." % k)

    # THE FALLBACK, EXERCISED. Point the reader at a path that is not there so
    # the in-module copy is what answers.
    #
    # PATCH `core`, NOT `migrate`. `migrate` imports the name, but the reader
    # (`core.migrate_map_section`) calls `migrate_map_path()` resolved in
    # core's OWN namespace - so patching `migrate._map_path` is invisible to
    # it, the file answers anyway, and this guard goes back to comparing the
    # file with itself, which is the defect it exists for. It did exactly that
    # until 2026-08-25, including its own rigour assertion, which inspected
    # the patched lambda and confirmed nothing about what was read.
    from compass_pkg import core

    real_artifacts = migrate.artifact_name_map()
    real_stages = migrate.stage_key_map()
    original = core.migrate_map_path
    try:
        core.migrate_map_path = lambda: "/nonexistent/migrate-map.yml"
        # The positive control: with the file unreachable, a section asked for
        # with a sentinel fallback must come back as exactly that sentinel. If
        # the file is still answering, this fails here rather than silently
        # further down.
        sentinel = {"__unreachable__": "__sentinel__"}
        assert core.migrate_map_section("artifacts", sentinel) == sentinel, (
            "the map file still answered with the path patched out, so the "
            "in-module fallback was never reached and the comparison below "
            "would be the file against itself")
        fb_artifacts = migrate.artifact_name_map()
        fb_stages = migrate.stage_key_map()
    finally:
        core.migrate_map_path = original

    for name, from_file, from_code in (("artifacts", real_artifacts, fb_artifacts),
                                       ("stage_keys", real_stages, fb_stages)):
        assert from_code == from_file, (
            "the in-module fallback for `%s` has drifted from "
            "cli/migrate-map.yml, so a bare checkout would migrate differently "
            "from an installed one:\n  only in the file: %s\n"
            "  only in the code: %s"
            % (name, sorted(set(from_file) - set(from_code)),
               sorted(set(from_code) - set(from_file))))


def test_trc_e2_map_guard_declines_an_empty_input():
    """TRC-E2 for the map: a scan handed nothing does not report a pass."""
    from compass_pkg import migrate

    assert migrate.artifact_name_map(), (
        "the artifact map is empty, so every assertion about it above compares "
        "two empty things and passes")
    assert _map().get("stage_keys"), "the stage-key map is empty"


# ---------------------------------------------------------------------------
# Group B - nothing already written breaks
# ---------------------------------------------------------------------------

def test_trc_b1():
    """TRC-B1: a spine written before the rename still reads.

    107 spines carry the retired keys. ADR-006 makes this
    non-negotiable inside a major version.
    """
    from compass_pkg.core import normalize_spine

    old = {"schema_version": "2.0", "task": "t",
           "stages": {k: "full" for k in STAGE_RENAMES} | {"plan": "full",
                                                           "verify": "full"}}
    got = normalize_spine(old)["stages"]
    for retired, current in STAGE_RENAMES.items():
        assert current in got, (
            "a spine holding the retired stage key %r did not resolve to %r - "
            "107 spines carry these:\n  %s" % (retired, current, got))
        assert retired not in got, (
            "%r survived normalisation alongside %r" % (retired, current))
    for k in STAGE_UNCHANGED:
        assert k in got, "%r must survive normalisation unchanged" % k

    # A spine already speaking the new keys normalises to itself.
    new = {"schema_version": "2.0", "task": "t",
           "stages": {v: "full" for v in STAGE_RENAMES.values()}}
    assert normalize_spine(new)["stages"] == new["stages"], (
        "a spine holding the current keys did not survive normalisation")


def test_trc_b2():
    """TRC-B2: a document written before the rename still resolves.

    Also asserts the compatibility map has not collapsed to an identity. A
    blanket rename over the tree rewrote its values to the current filenames
    on 2026-08-25 - the map whose only job is to remember the old name had the
    old name renamed out of it, and every assertion below still passed because
    the fixture wrote whatever the map said.
    """
    from compass_pkg.core import _RENAMED_KIND_FILES

    assert _RENAMED_KIND_FILES, "the compatibility map is empty"
    for kind, filename in _RENAMED_KIND_FILES.items():
        assert filename != "%s.md" % kind, (
            "the compatibility entry for %r points at its own current "
            "filename, so it maps nothing and a landed issue holding the old "
            "name no longer resolves" % kind)
    import tempfile
    from compass_pkg.core import FOUND, resolve_artifact

    tmp = Path(tempfile.mkdtemp(prefix="compass-rename-"))
    (tmp / "design.md").write_text("# old name\n")
    (tmp / "prd.md").write_text("# old name\n")

    for kind, flat in (("technical-design", "design.md"), ("intent", "prd.md")):
        state, path, reason = resolve_artifact(str(tmp), kind)
        assert state == FOUND, (
            "asking for %r did not find the file a landed issue actually holds "
            "(%s): %s" % (kind, flat, reason))
        assert Path(path).name == flat, (
            "resolved to %s rather than the file on disk, %s"
            % (Path(path).name, flat))
        assert flat in reason or "flat" in reason, (
            "the reason does not say which route found it: " + reason)


# ---------------------------------------------------------------------------
# Group A - the names agree
# ---------------------------------------------------------------------------

COMMANDS = REPO_ROOT / "commands"

def _cli_stage_keys():
    """The stage keys the CLI itself writes into a spine.

    Read from the machinery rather than restated here. A hand-written
    `{"assess": "assess", "define": "define", ...}` map stood in this file
    until 2026-08-25 and the test compared each key with itself - an identity
    dict makes `command == key` structurally incapable of failing, so the
    assertion read as the rule and checked nothing.

    NOT read from governance/routing-policy.yml: that file still declares the
    v1 keys (`frame`, `specify`, ...) and is migrated in its own slice. The
    spine loader maps them forward, so what a spine HOLDS is what matters
    here.
    """
    from compass_pkg.core import STAGE_DISPLAY
    return set(STAGE_DISPLAY)

# Retired command names that must answer with a pointer rather than vanish.
# `design` is NOT here: it is a retired name for the engineering stage AND the
# live name for the designer's, so a stub pointing at `/compass:plan` would
# take the designer's command away again.
RETIRED_COMMANDS = {"triage": "assess", "wireframe": "design"}


def _command_names():
    return {p.stem for p in COMMANDS.glob("*.md")}


def _is_stub(name):
    """A retired name that points and stops, rather than doing the work.

    TRC-A1 and TRC-A2 say a retired name must not be a live command; TRC-B4
    says it must still answer. Both are right and the first was written too
    bluntly - the file existing is not the same as the command being live. A
    stub is identified by what it does: it names its replacement, it says it is
    retired, and it is short enough that it plainly carries no procedure.
    """
    p = COMMANDS / ("%s.md" % name)
    if not p.is_file():
        return False
    text = p.read_text(encoding="utf-8")
    return ("retired" in text.lower()
            and "/compass:" in text
            and len(text.splitlines()) < 40)


def test_trc_a1():
    """TRC-A1: a command, its machine key and its artifact name the same thing.

    The rule is about an artifact CLAIMING another stage, not about sharing a
    word with one - four artifacts already differ from their stage's name and
    none is a defect (`define`/`acceptance-criteria`,
    `refine`/`requirements-review`, `assess`/`delivery-approach`,
    `verify`/`verification-report`).
    """
    names = _command_names()
    assert names, "no command files found, so this checks nothing"

    keys = _cli_stage_keys()
    assert keys, "the CLI declares no stage keys, so this checks nothing"
    missing = sorted(k for k in keys if k not in names)
    assert not missing, (
        "the spine holds these stage keys and no command of the same name "
        "exists: %s. The word a person types and the word the spine holds "
        "must be the same. Commands present: %s"
        % (missing, sorted(names)))

    # The two defects this rule exists for, asserted directly rather than left
    # to the general shape above.
    intent = (COMMANDS / "intent.md").read_text(encoding="utf-8")
    assert "prd.md" not in intent, (
        "`/compass:intent` still writes prd.md - a command and its own output "
        "naming different things is the defect this issue opened on")
    assert "intent.md" in intent, (
        "`/compass:intent` does not name intent.md as what it writes")
    assert _is_stub("triage"), (
        "`/compass:triage` is still a live command rather than a stub. It "
        "produces an `assessment:` block, and the command for that is "
        "`/compass:assess`; the old name may point at it and nothing more.")


def test_trc_a2():
    """TRC-A2: the designer's command is `design` again, and does not claim
    the engineering stage's job."""
    names = _command_names()
    for want in ("design", "plan"):
        assert want in names, "no `/compass:%s` command: %s" % (want, sorted(names))
    assert _is_stub("wireframe"), (
        "`/compass:wireframe` is still a live command rather than a stub - the "
        "designer's entry point is `/compass:design` again")

    design = (COMMANDS / "design.md").read_text(encoding="utf-8")
    plan = (COMMANDS / "plan.md").read_text(encoding="utf-8")

    assert "ui-contract.md" in design, (
        "`/compass:design` does not produce the UI contract, so it is not the "
        "designer's entry point")
    assert "technical-design.md" in plan, (
        "`/compass:plan` does not produce technical-design.md")
    assert "ui-contract.md" not in plan, (
        "`/compass:plan` claims the designer's artifact")
    assert "technical-design.md" not in design, (
        "`/compass:design` claims the engineering stage's artifact")


def test_trc_b4():
    """TRC-B4: a retired command answers with a pointer, not as unknown.

    `design` is deliberately excluded: it is retired for one stage and live for
    another, and a stub pointing at `/compass:plan` would take the designer's
    command away a second time.
    """
    names = _command_names()
    for retired, replacement in RETIRED_COMMANDS.items():
        stub = COMMANDS / ("%s.md" % retired)
        assert stub.is_file(), (
            "`/compass:%s` was removed rather than left as a redirect stub. "
            "governance/terminology.yml says a retired name 'is a redirect "
            "stub for one major version'." % retired)
        text = stub.read_text(encoding="utf-8")
        assert replacement in text, (
            "the `%s` stub does not name its replacement %r"
            % (retired, replacement))
        assert len(text.splitlines()) < 40, (
            "the `%s` stub is %d lines - a stub points, it does not carry a "
            "copy of the command that replaced it"
            % (retired, len(text.splitlines())))

    assert "design" in names, "the design command vanished"
    design = (COMMANDS / "design.md").read_text(encoding="utf-8")
    assert "/compass:plan" not in design or "designer" in design.lower(), (
        "`/compass:design` reads as a stub pointing at `/compass:plan`. It is "
        "the designer's command now, not a redirect")


# ---------------------------------------------------------------------------
# Group B (continued) - a rename has two halves, and only one was tested
#
# TRC-B2 proved a document written BEFORE the rename still resolves. Nothing
# asked the other question: does a document written AFTER it resolve? It did
# not. `_flat_name` replaced the current filename with the retired one instead
# of falling back to it, so `compass issue dashboard` reported a technical
# design that was sitting on disk as "not written yet" - the review page
# denying a document that exists.
# ---------------------------------------------------------------------------

def _issue_dir(**files):
    """A throwaway issue directory holding exactly the files named."""
    import tempfile

    tmp = Path(tempfile.mkdtemp(prefix="compass-rename-"))
    for name, body in files.items():
        (tmp / name.replace("_", ".")).write_text(body, encoding="utf-8")
    return tmp


def test_trc_b5():
    """TRC-B5: a document written after the rename resolves under its new name.

    This is TRC-B2 read the other way round. The compatibility map exists so a
    landed issue keeps working; it must not cost the framework the ability to
    find the file it writes today.
    """
    from compass_pkg.core import FOUND, artifact_path, resolve_artifact

    for kind, current in (("technical-design", "technical-design.md"),
                          ("intent", "intent.md")):
        tmp = _issue_dir(**{current.replace(".", "_"): "# written today\n"})
        state, path, reason = resolve_artifact(str(tmp), kind)
        assert state == FOUND, (
            "asking for %r did not find %s, the name this framework writes "
            "today: %s" % (kind, current, reason))
        assert Path(path).name == current
        assert Path(artifact_path(str(tmp), current)).name == current, (
            "artifact_path and resolve_artifact disagree about %r" % kind)


def test_trc_b6():
    """TRC-B6: when both filenames are present, the current one wins.

    Resuming a landed issue and re-running the plan stage writes the current
    name beside the retired one. Preferring the retired file would make every
    reader - the governance check, the review page, the design lint - quietly
    take the stale document, with nothing on screen to say so.
    """
    from compass_pkg.core import FOUND, artifact_path, resolve_artifact

    for kind, current, retired in (("technical-design", "technical-design.md",
                                    "design.md"),
                                   ("intent", "intent.md", "prd.md")):
        tmp = _issue_dir(**{current.replace(".", "_"): "# current\n",
                            retired.replace(".", "_"): "# stale\n"})
        state, path, _why = resolve_artifact(str(tmp), kind)
        assert state == FOUND and Path(path).name == current, (
            "resolve_artifact took %s over %s - every reader would get the "
            "stale document" % (Path(path).name if path else None, current))
        assert Path(artifact_path(str(tmp), current)).name == current, (
            "artifact_path took the retired %s over %s" % (retired, current))


def test_trc_b7():
    """TRC-B7: `compass design lint` still reads a landed issue's design.

    Every other artifact reader goes through `artifact_path`, which knows both
    names. This one joined the filename itself, so it reported "no such file"
    on all 36 landed issues that have a design - and then explained the absence
    with a reason it could have checked and did not, that the design stage
    collapses on some approaches.
    """
    import subprocess
    import sys
    import tempfile

    project = Path(tempfile.mkdtemp(prefix="compass-rename-"))
    work = project / ".compass" / "work" / "landed"
    work.mkdir(parents=True)
    (project / ".compass" / "config.yml").write_text("version: 1.0.0\n")
    (project / ".compass" / "current-task").write_text("landed\n")
    (work / "task.yml").write_text(
        'schema_version: "2.0"\ntask: "landed"\ncreated: "2026-03-01"\n'
        "status: landed\ndelivery_approach: feature\n"
        "stages: {plan: full}\n")
    # The name 36 landed issue directories actually hold.
    (work / "design.md").write_text(
        "# Design - landed\n\n## DD-1\n\nChosen: this. Rejected: that.\n")

    run = subprocess.run([sys.executable, str(REPO_ROOT / "cli" / "compass"),
                          "design", "lint"],
                         cwd=str(project), capture_output=True, text=True,
                         timeout=120)
    combined = run.stdout + run.stderr
    assert "no such file" not in combined.lower(), (
        "the design lint could not find the design.md sitting in a landed "
        "issue directory:\n" + combined)
    assert run.returncode == 0, combined


# ---------------------------------------------------------------------------
# Group A (continued) - the command moved; its call sites did not
# ---------------------------------------------------------------------------

def test_trc_a4():
    """TRC-A4: the planning stage answers to `plan` in the CLI too.

    `commands/design.md` was renamed to `commands/plan.md`, but the CLI verb
    stayed `compass design lint`. That leaves the same word meaning the
    engineering design in the CLI and the designer's UI contract in the slash
    command, in one release - which is the exact ambiguity this rename exists
    to remove.
    """
    import subprocess
    import sys

    cli = REPO_ROOT / "cli" / "compass"
    run = subprocess.run([sys.executable, str(cli), "plan", "lint", "--help"],
                         capture_output=True, text=True)
    assert run.returncode == 0, (
        "`compass plan lint` is not a verb: " + (run.stderr or run.stdout))


# Files that may name `/compass:design` without saying which design they mean:
# the two redirect stubs, whose whole body is a pointer.
_DESIGN_REF_EXEMPT = {"commands/wireframe.md", "commands/triage.md"}

# `design` names the designer's command AND, until this rename, the
# engineering stage. A reference that does not say which one it means is the
# ambiguity itself, so the window around it must carry a designer marker - or
# name another role entry point, which makes it a roll-call of role commands.
_DESIGNER_MARKERS = ("designer", "Designer", "ui-contract", "UI contract",
                     "wireframe", "Wireframe")
_ROLE_ROLL_CALL = ("/compass:intent", "/compass:position")


# Directories that are not a shipped surface: version control, the framework's
# own issue archive (kept as written - ADR-014), the tests doing the checking,
# and the two untracked planning directories.
_SKIP_DIRS = {".git", "tests", "node_modules"}
# Only at the repo root. The worked examples under examples/ carry their own
# .compass/ tree, and those ARE a shipped surface - an adopter reads them to
# learn the pipeline, so a wrong command name there teaches the wrong command.
_SKIP_ROOTS = {".compass"}
_SKIP_DOCS = {"docs/proposals", "docs/analysis"}
# Generated from governance/terminology.yml - fix the source, not the output.
_GENERATED = {"docs/system-spec.md", "docs/glossary.md"}


def _shipped_docs():
    """Every markdown surface a reader or a session actually reads."""
    for path in sorted(REPO_ROOT.rglob("*.md")):
        rel = path.relative_to(REPO_ROOT)
        if set(rel.parts) & _SKIP_DIRS or rel.parts[0] in _SKIP_ROOTS:
            continue
        if str(rel) in _GENERATED:
            continue
        if any(str(rel).startswith(d + "/") for d in _SKIP_DOCS):
            continue
        yield rel, path


def test_trc_a5():
    """TRC-A5: no live surface sends the engineering stage to `/compass:design`.

    `/compass:design` was not retired - it was REPURPOSED, from the
    engineering design stage to the designer's UI-contract entry point. A
    redirect stub cannot catch that, and neither can a check that only asks
    whether a command name still exists: the name is live, under a new
    meaning. A reader following one of these lands in the designer's flow,
    writes `ui-contract.md` instead of the technical design, and is told it
    worked.

    The rule is a meaning check, not an existence check: a line naming
    `/compass:design` must say, within three lines, which design it means.
    """
    offenders = []
    for rel, path in _shipped_docs():
        if str(rel) in _DESIGN_REF_EXEMPT:
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            if "/compass:design" not in line:
                continue
            if any(cmd in line for cmd in _ROLE_ROLL_CALL):
                continue
            window = "\n".join(lines[max(0, i - 3):i + 4])
            if any(m in window for m in _DESIGNER_MARKERS):
                continue
            offenders.append("%s:%d: %s" % (rel, i + 1, line.strip()))
    assert not offenders, (
        "these name `/compass:design` without saying which design they mean, "
        "so they read as the engineering stage and run the designer's "
        "command:\n  " + "\n  ".join(offenders))


# ---------------------------------------------------------------------------
# Group D - the frozen vocabulary must not contradict itself
# ---------------------------------------------------------------------------

TERMINOLOGY = REPO_ROOT / "governance" / "terminology.yml"


def _terminology():
    import compass_pkg  # resolves the bundled yaml
    import yaml
    return yaml.safe_load(TERMINOLOGY.read_text(encoding="utf-8"))


def _banned_spellings(doc):
    """Every individual word a `banned:` entry retires.

    A `term:` may name several at once - "Specify / Clarify / Distribute /
    Land" is one entry retiring four words - so the slash-separated parts are
    split out and lowercased.
    """
    out = {}
    for entry in doc.get("banned") or []:
        for part in str(entry.get("term", "")).split("/"):
            word = part.strip().lower()
            if word:
                out[word] = entry
    return out


def test_trc_d1():
    """TRC-D1: a ban never points at a replacement that is itself banned.

    A reader who hits a banned word looks up its replacement and uses it. If
    that replacement is also retired they rename twice, and the second rename
    is one nobody told them about - so the vocabulary reads as settled while
    handing out words it has already withdrawn.

    The rule was already written into one ban's own context line, as prose:
    "Points at the FINAL name, not at `triage` - a ban naming a banned
    replacement sends a reader to a word they must rename again." This is that
    sentence as a check.
    """
    doc = _terminology()
    banned = _banned_spellings(doc)
    offenders = []
    for entry in doc.get("banned") or []:
        for part in str(entry.get("replacement", "")).split("/"):
            word = part.strip().lower()
            if word and word in banned:
                offenders.append(
                    "%r is replaced by %r, which is itself retired (in favour "
                    "of %r)" % (entry.get("term"), part.strip(),
                                banned[word].get("replacement")))
    assert not offenders, (
        "these bans send a reader to a word they must rename again:\n  "
        + "\n  ".join(offenders))


def test_trc_d4_no_term_is_both_defined_and_banned():
    """A word cannot be the current vocabulary AND the retired vocabulary.

    `docs/glossary.md` is generated from the `terms:` block and titled "Every
    word and every id prefix Compass uses". A term defined there while banned
    below publishes the retired word as current, to the one document a reader
    consults to find out which word is current.
    """
    doc = _terminology()
    banned = _banned_spellings(doc)
    offenders = sorted(name for name in (doc.get("terms") or {})
                       if str(name).lower() in banned)
    assert not offenders, (
        "these are defined as live vocabulary and banned in the same file, so "
        "the generated glossary publishes a retired word as current: "
        + ", ".join(offenders))


def test_trc_d5_the_code_position_scan_knows_this_rename():
    """`retired_machine_names` must carry the filenames this cycle retired.

    That block is what `tests/test_terminology.py` scans Python string
    literals against - the check that exists specifically to catch a retired
    filename left in a code position. It carried the v1 filenames and was not
    extended when `design.md` became `technical-design.md` and `prd.md` became
    `intent.md`, so it was blind to the rename it shipped beside.
    """
    doc = _terminology()
    retired = {str(e.get("name")): str(e.get("replacement"))
               for e in (doc.get("retired_machine_names") or [])}
    for old, new in (("design.md", "technical-design.md"),
                     ("prd.md", "intent.md")):
        assert retired.get(old) == new, (
            "retired_machine_names does not map %s to %s (it says %r), so the "
            "code-position scan cannot see this rename"
            % (old, new, retired.get(old)))



# ---------------------------------------------------------------------------
# Group C (continued) - two retired names, one current name
# ---------------------------------------------------------------------------

def test_trc_c5_migrate_refuses_a_many_to_one_collision():
    """Two retired filenames mapping to one current name must not race.

    `artifacts:` now has two such pairs, both created on 2026-08-25 when this
    rename was added beside the v2 freeze's:

        brief.md -> intent.md            prd.md    -> intent.md
        plan.md  -> technical-design.md  design.md -> technical-design.md

    A directory holding BOTH members of a pair used to be resolved by dict
    insertion order: the first rename happened, the second silently did not,
    and the dry run had promised both. Insertion order puts the older v1 file
    first, so the STALE document won and the current one was left orphaned
    under a name nothing reads. Re-running then reported "nothing to do",
    which was a confident falsehood about a directory holding two designs.

    The archive in this repository has no `plan.md` or `brief.md` left, so it
    is latent here - and live for an adopter mid-upgrade, which is exactly who
    `compass migrate` is for.
    """
    import subprocess
    import sys
    import tempfile

    project = Path(tempfile.mkdtemp(prefix="compass-collide-"))
    work = project / ".compass" / "work" / "collide"
    work.mkdir(parents=True)
    (project / ".compass" / "config.yml").write_text("version: 1.0.0\n")
    (work / "brief.md").write_text("# v1 brief - stale\n")
    (work / "prd.md").write_text("# v2 intake - the real content\n")

    run = subprocess.run([sys.executable, str(REPO_ROOT / "cli" / "compass"),
                          "migrate", "--apply"],
                         cwd=str(project), capture_output=True, text=True,
                         timeout=120)
    combined = run.stdout + run.stderr

    assert run.returncode != 0, (
        "migrate silently picked one of two files that both claim the same "
        "current name:\n" + combined)
    assert "brief.md" in combined and "prd.md" in combined, (
        "the refusal does not name both files, so the reader cannot tell "
        "which two collided:\n" + combined)
    assert (work / "brief.md").is_file() and (work / "prd.md").is_file(), (
        "migrate renamed one of the colliding files before refusing - a "
        "refusal must leave the directory as it found it")
