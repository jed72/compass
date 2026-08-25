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
    # the in-module copy is what answers. Patching `_map_path` rather than
    # `os.path.join` on purpose: a mock that matches on argument shape is one
    # more thing that can silently stop matching, and then this guard goes back
    # to comparing the file with itself - which is the defect it exists for.
    real_artifacts = migrate.artifact_name_map()
    real_stages = migrate.stage_key_map()
    original = migrate._map_path
    try:
        migrate._map_path = lambda: "/nonexistent/migrate-map.yml"
        assert not Path(migrate._map_path()).exists(), (
            "the path meant to be unreadable exists, so the fallback was never "
            "reached and this compares the file with itself")
        fb_artifacts = migrate.artifact_name_map()
        fb_stages = migrate.stage_key_map()
    finally:
        migrate._map_path = original

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

    94 landed issues carry the retired keys. ADR-006 makes this
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
            "94 landed issues carry these:\n  %s" % (retired, current, got))
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

# Command -> the machine key it runs, for every stage that has both.
STAGE_COMMANDS = {
    "assess": "assess",
    "define": "define",
    "refine": "refine",
    "plan": "plan",
    "breakdown": "breakdown",
    "implement": "implement",
    "verify": "verify",
    "ship": "ship",
}

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

    for command, key in STAGE_COMMANDS.items():
        assert command in names, (
            "no `/compass:%s` command, and the machine key is %r - the word a "
            "person types and the word the spine holds must be the same. "
            "Commands present: %s" % (command, key, sorted(names)))
        assert command == key, (
            "the command %r and its machine key %r are different words"
            % (command, key))

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
