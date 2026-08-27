"""Slice 5a of the v2 rename: the command files speak the ratified v2 names.

The content specification is the ratified command table in the slice's issue
archive (machine state, exempt from the vocabulary scan). The eight pipeline
commands become triage, define, refine, design, breakdown, implement, verify,
ship; the designer entry point becomes wireframe; the seven retired names
remain as redirect stubs for one major version; the vocabulary file is
amended in the same diff; and no live instruction surface may point at a
retired name.
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).parent.parent
COMMANDS = REPO_ROOT / "commands"

# Updated 2026-08-25 by `the-vocabulary-rename`: `triage` -> `assess`, the
# planning stage's command -> `plan`, and `design` back to the designer, whose
# command it was before `wireframe`.
V2_COMMANDS = {
    "assess", "define", "refine", "plan", "breakdown", "implement",
    "verify", "ship", "design", "intent", "position", "consult",
    "status", "flow", "resume", "init",
}

# Retired name -> its v2 replacement. Each remains on disk as a redirect
# stub so an adopter's muscle memory gets a pointer, not a dead command.
# NOTE `plan` is absent, and `frame` points at the FINAL name. `plan` was a
# retired v1 command and is live again - ADR-014 removes retired names, it does
# not reserve them - and `frame`'s replacement is `assess`, because `triage`
# is itself retired now. A stub naming a retired replacement sends a reader to
# a word they must rename again.
STUBS = {
    "frame": "assess",
    "triage": "assess",
    "specify": "define",
    "clarify": "refine",
    "wireframe": "design",
    "distribute": "breakdown",
    "build": "implement",
    "land": "ship",
    # ADR-023: the word Anthropic's platform docs use for consulting an
    # advisor mid-turn. Goes at the next major version, like the two above it.
    "roundtable": "consult",
}

INLINE_CODE = re.compile(r"`[^`]*`")
DEAD_NAME = re.compile(
    r"/compass:(?:frame|triage|specify|clarify|wireframe|distribute|build|land"
    r"|roundtable)\b")


def test_the_command_set_carries_the_v2_names():
    """TRC-1: all sixteen v2 commands exist, each with an H1 naming itself."""
    names = {p.stem for p in COMMANDS.glob("*.md")}
    missing = V2_COMMANDS - names
    assert not missing, f"missing v2 command files: {sorted(missing)}"
    stray = names - V2_COMMANDS - set(STUBS)
    assert not stray, f"unexpected command files: {sorted(stray)}"
    for name in sorted(V2_COMMANDS):
        text = (COMMANDS / f"{name}.md").read_text(encoding="utf-8")
        assert re.search(rf"^# .?/compass:{name}\b", text, re.M), (
            f"{name}.md lacks an H1 naming /compass:{name}")


# The redirect-stub contract used to be asserted here: each retired command
# name existed as a short stub pointing at its v2 replacement. ADR-014 deleted
# those stubs at the major version. The replacement assertion - that no such
# stub exists, by filename and by content - is
# tests/test_no_deprecation_stubs.py (RCD-F1).


def test_the_vocabulary_carries_the_command_names_and_a_version_bump():
    """TRC-3: terminology.yml is amended in the same diff that lands the
    names - version bumped past 2.0.0-pre5, the banned command entries name
    their exact replacement commands, and the ruling's reading of the naming
    rule (anti-jargon, not grammatical purity) is recorded."""
    text = (REPO_ROOT / "governance" / "terminology.yml").read_text(
        encoding="utf-8")
    doc = yaml.safe_load(text)
    m = re.fullmatch(r"2\.0\.0-pre(\d+)", str(doc["version"]))
    assert m and int(m.group(1)) > 5, (
        f"terminology.yml version is {doc['version']} - the command renames "
        "must land with a version bump past 2.0.0-pre5")
    bans = {b["term"]: b for b in doc["banned"]}
    frame = bans["Frame / the Needle"]
    joined = frame.get("replacement", "") + frame.get("context", "")
    assert "triage" in joined, (
        "the Frame ban entry does not name /compass:triage as the command "
        "replacement")
    stages = bans["Specify / Clarify / Distribute / Land"]
    joined = stages.get("replacement", "") + stages.get("context", "")
    for cmd in ("define", "refine", "breakdown", "ship"):
        assert cmd in joined, (
            f"the stage-name ban entry does not name the '{cmd}' command")
    assert "anti-jargon" in text, (
        "the recorded reading of the naming rule (anti-jargon, not "
        "grammatical purity) is missing from terminology.yml")


def test_commands_and_manifests_are_enforced_surfaces():
    """TRC-4: commands/ and .claude-plugin/ leave pending_surfaces in the
    vocabulary file and the committed baseline in the same diff. Their
    cleanliness is then enforced by the existing terminology scan."""
    from test_terminology import PENDING_BASELINE
    scan = yaml.safe_load(
        (REPO_ROOT / "governance" / "terminology.yml").read_text(
            encoding="utf-8"))["scan"]
    for surface in ("commands/", ".claude-plugin/"):
        assert surface not in scan["pending_surfaces"], (
            f"{surface} is still pending in terminology.yml - slice 5a's "
            "definition of done includes de-pending it")
        assert surface not in PENDING_BASELINE, (
            f"{surface} is still in the committed baseline - the ratchet "
            "shrinks in the same diff that cleans the surface")


def test_no_live_surface_points_at_a_dead_command_name():
    """TRC-5: the surfaces that drive live sessions carry no retired command
    name - the stubs excepted (they are the pointer), and the not-yet-renamed
    skills and docs excepted until their own slices (the stubs keep those
    references functional meanwhile)."""
    surfaces: list[Path] = [
        REPO_ROOT / "CLAUDE.md",
        REPO_ROOT / "AGENTS.md",
        REPO_ROOT / "skills" / "compass-runtime" / "SKILL.md",
        REPO_ROOT / "cli" / "compass",
    ]
    surfaces += sorted((REPO_ROOT / "agents").glob("*.md"))
    surfaces += sorted((REPO_ROOT / "templates").rglob("*.md"))
    surfaces += sorted((REPO_ROOT / "cli").rglob("*.py"))
    surfaces += sorted((REPO_ROOT / "hooks").glob("*.sh"))
    surfaces += sorted((REPO_ROOT / ".claude-plugin").glob("*.json"))
    hits = []
    for path in surfaces:
        if not path.is_file():
            continue
        for lineno, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), 1):
            if DEAD_NAME.search(line):
                rel = path.relative_to(REPO_ROOT)
                hits.append(f"{rel}:{lineno}: {line.strip()[:80]}")
    assert not hits, (
        "retired command names on live surfaces:\n  " + "\n  ".join(hits[:20]))


def test_the_ruling_conditions_hold():
    """TRC-6: define's one-line description leads with 'Acceptance criteria';
    design's says it produces the UI contract; and the UI-contract
    template's producer line points at /compass:design."""
    def description(name: str) -> str:
        text = (COMMANDS / f"{name}.md").read_text(encoding="utf-8")
        m = re.search(r"^description:\s*(.+)$", text, re.M)
        assert m, f"{name}.md has no description line"
        return m.group(1)

    assert description("define").startswith("Acceptance criteria"), (
        "define's description must lead with 'Acceptance criteria' - the "
        "bare verb is the vaguest in the set")
    assert "UI contract" in description("design"), (
        "wireframe's description must state it produces the UI contract")
    assert "/compass:design" in (
        REPO_ROOT / "templates" / "ui-contract.md").read_text(
        encoding="utf-8"), (
        "templates/ui-contract.md's producer line must point at "
        "/compass:design")
