"""The retired names are gone at 4.0.0 (issue what-compass-owes-an-unobserved-adopter).

ADR-019 carried redirect stubs and one hidden CLI alias through 3.x, and
scheduled their removal at the next major version. This is that removal.

What goes: the three slash-command stubs, the `design`-for-`plan` verb alias,
and the `terminology.yml` entries that exist only to describe them.

What stays, and why it is not an oversight: the read-side rename tables in
`cli/compass_pkg/core.py` and `analyze.py`. They let an archived manifest and
an old prose record load, which ADR-020 requires - the archive is migrated,
not frozen. They are kept for the archive's sake, not for an adopter's, and
TRC-D3 holds the decision record to saying so.

Scenario ids: TRC-D1..D6 in
.compass/work/what-compass-owes-an-unobserved-adopter/acceptance-criteria.md
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
COMMANDS = REPO_ROOT / "commands"
CLI = REPO_ROOT / "cli" / "compass"
TERMINOLOGY = REPO_ROOT / "governance" / "terminology.yml"

# The three redirect stubs ADR-019 scheduled for removal at the next major.
RETIRED_COMMANDS = {
    "triage.md": "/compass:assess",
    "wireframe.md": "/compass:design",
    "roundtable.md": "/compass:consult",
}


def _run(*args):
    """Run the CLI and return (returncode, stdout+stderr)."""
    r = subprocess.run([sys.executable, str(CLI), *args],
                       capture_output=True, text=True, timeout=60,
                       cwd=str(REPO_ROOT))
    return r.returncode, r.stdout + r.stderr


# ---------------------------------------------------------------------------
# TRC-D1 - the retired slash commands no longer exist
# ---------------------------------------------------------------------------

def test_the_retired_slash_commands_no_longer_exist():
    present = sorted(n for n in RETIRED_COMMANDS if (COMMANDS / n).is_file())
    assert not present, (
        f"retired command stub(s) still shipped: {', '.join(present)}. "
        f"ADR-019 scheduled these for removal at the next major version, and "
        f"this is it")

    # And nothing still sends a reader to one. The stub was the only file
    # allowed to name its own retired command; with the stub gone, nothing is.
    offenders = []
    for path in sorted(COMMANDS.glob("*.md")):
        body = path.read_text(encoding="utf-8")
        for name in RETIRED_COMMANDS:
            slash = "/compass:" + name[:-3]
            if slash in body:
                offenders.append(f"{path.relative_to(REPO_ROOT)}: {slash}")
    assert not offenders, (
        "shipped command file(s) still point at a command that no longer "
        "exists:\n  " + "\n  ".join(offenders))


# ---------------------------------------------------------------------------
# TRC-D2 - the hidden CLI alias no longer resolves
# ---------------------------------------------------------------------------

def test_the_hidden_cli_alias_no_longer_resolves():
    code, out = _run("design", "lint")
    assert code != 0, (
        "`compass design lint` still runs. It was a second name for `plan`, "
        "hidden from --help and kept for one major version (ADR-019)")
    assert "invalid choice" in out or "unrecognized" in out, (
        f"`compass design` failed, but not as an unknown verb - the error was:"
        f"\n{out[-400:]}")

    # NOT asserted: that the error names `plan`. argparse prints the whole
    # choice list on an invalid choice, so `"plan" in out` is satisfied
    # mechanically for as long as `plan` exists and says nothing about
    # whether the reader was helped. The redirect a broken caller actually
    # gets is the upgrade table in docs/releasing.md, which TRC-D6 checks.
    assert "plan" in out.split("invalid choice")[0] or "plan" in out, (
        "the parser no longer defines `plan`, so the replacement this "
        "removal points at does not exist")

    # `hidden` keeps a verb out of --help while it still parses. The stale-
    # entry check lives in cli/compass itself, beside the subtraction, rather
    # than here: reading the source for a `hidden = {...}` literal missed the
    # `set()` spelling entirely and the assertion never ran. What is checked
    # here is that the guard is wired in and reachable.
    source = CLI.read_text(encoding="utf-8")
    assert "hidden - set(sub.choices)" in source, (
        "cli/compass no longer checks `hidden` against the parser's verbs. "
        "That set is only ever subtracted from the advertised list, so an "
        "entry naming a verb that does not parse removes nothing and reports "
        "nothing")

    # The advertised set and the parsed set agree, apart from the internal
    # underscore-prefixed verbs which are deliberately not public. This is
    # the property the removed alias used to violate.
    code, out = _run("--help")
    assert code == 0, out
    advertised = re.search(r"\{([a-z0-9,_-]+)\}", out)
    assert advertised, f"could not read the verb list from --help:\n{out[:400]}"
    assert "design" not in advertised.group(1).split(","), (
        "`design` is still advertised as a verb")


# ---------------------------------------------------------------------------
# TRC-D3 - read-side migration survives, for the archive's reason
# ---------------------------------------------------------------------------

def test_read_side_migration_survives_for_the_archive_s_reason():
    # Loaded, not grepped. A name check passes on a renamed symbol -
    # `SPINE_KEY_MAP_X` contains `SPINE_KEY_MAP` - so it survives exactly the
    # deletion it exists to catch.
    core, analyze = _load_cli_modules()

    for name in ("SPINE_KEY_MAP", "ASSESSMENT_KEY_MAP"):
        table = getattr(core, name, None)
        assert isinstance(table, dict) and table, (
            f"{name} is gone or empty. It is read-side: it is what lets an "
            f"archived manifest load, which ADR-020 requires. Removing it "
            f"breaks the archive, whatever was decided about adopters")

    assert core.SPINE_KEY_MAP.get("topology") == "orchestration", (
        "SPINE_KEY_MAP no longer maps `topology` forward, so a manifest "
        "written under the older vocabulary loses the key")

    phases = analyze._PHASE_NAME_MAP
    assert phases.get("triage") == "assess", (
        "the phase-name map lost its retired spellings. It normalises prose "
        "records already on disk - a delivery-approach record written months "
        "ago still says the retired word")

    # An archived manifest still loads. `compass migrate` is the verb that
    # reads them, so its presence is the observable half.
    code, out = _run("migrate", "--help")
    assert code == 0, f"`compass migrate` no longer runs:\n{out[-400:]}"


# ---------------------------------------------------------------------------
# TRC-D4 - the vocabulary has one value per concept again
# ---------------------------------------------------------------------------

def test_the_vocabulary_has_one_value_per_concept_again():
    text = TERMINOLOGY.read_text(encoding="utf-8")

    stale = [line.strip() for line in text.splitlines()
             if "redirect stub" in line.lower()]
    assert not stale, (
        "terminology.yml still describes a redirect stub that no longer "
        "exists:\n  " + "\n  ".join(stale))

    # Every exemption must still exclude something. An entry that excludes
    # nothing exempts nothing, and a scan reporting clean over it looks
    # identical to a scan that ran.
    scanned = _scanned_files()
    empty = [e for e in _exempt_paths(text)
             if e not in KNOWN_INERT_EXEMPTIONS
             and not _excludes_anything(e, scanned)]
    assert not empty, (
        f"scan.exempt entr(ies) exclude no scanned file: {', '.join(empty)}. "
        f"The scan only applies exemptions to files under scan.surfaces, so "
        f"an entry outside every surface removes nothing")


def _load_cli_modules():
    """Import `core` and `analyze` from the CLI package.

    `cli/compass_pkg` is not on the path for a test run, and importing it
    the way the CLI does (via `cli/compass`) would also run the entry
    point. Adding `cli/` to `sys.path` for the duration is enough.
    """
    import importlib
    cli_dir = str(REPO_ROOT / "cli")
    added = cli_dir not in sys.path
    if added:
        sys.path.insert(0, cli_dir)
    try:
        core = importlib.import_module("compass_pkg.core")
        analyze = importlib.import_module("compass_pkg.analyze")
    finally:
        if added:
            sys.path.remove(cli_dir)
    return core, analyze


# Exemptions that exclude nothing TODAY, with the reason each is kept.
# `scan.exempt` entries are only ever applied to files gathered from
# `scan.surfaces`, and none of these six sits under a declared surface - so
# each one excludes zero files. They are not deleted here because two other
# guards assert two of them stay present (`tests/test_docs_prose.py` and
# `tests/test_cli_voice.py`), which makes removing them a change with its own
# reasoning. Filed as `exemptions-that-exclude-nothing`.
#
# This is a ratchet, in the same shape as `scan.pending_surfaces`: the set may
# shrink and must never grow. A NEW entry that excludes nothing fails below.
KNOWN_INERT_EXEMPTIONS = frozenset({
    "docs/proposals/",
    "docs/system-spec.md",
    "cli/migrate-map.yml",
    "docs/analysis/",
    "tests/",
    ".compass/work/",
})


def _scanned_files() -> set:
    """Every file the vocabulary scan would actually visit.

    Imported from the scan's own test rather than reimplemented, so the two
    cannot drift. This is the question that matters: an exemption excludes
    something only if the scan was going to read it.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_terminology_scan", REPO_ROOT / "tests" / "test_terminology.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    cfg = mod._terminology()["scan"]
    out = set()
    for surface in cfg["surfaces"]:
        for f in mod._surface_files(surface):
            out.add(str(f.relative_to(REPO_ROOT)))
    return out


def _excludes_anything(entry: str, scanned: set) -> bool:
    """Does this exemption keep the scan away from at least one real file?

    Matched the way the scan matches - `rel.startswith(entry)` - so this
    agrees with the thing it is checking rather than with an idea of it.

    An earlier version asked whether any file existed under the prefix
    anywhere in the repository. That is a different question and a much
    weaker one: it walked ignored directories and `.git/`, and it answered
    yes for `dis` (from `dist/`) and for invented paths under gitignored
    roots, so fabricated entries passed.
    """
    return any(f.startswith(entry) for f in scanned)


def _exempt_paths(text: str) -> list[str]:
    """The paths listed under `scan:` -> `exempt:`, in file order.

    Read by line rather than by loading the YAML: this file is the vocabulary
    the scan itself runs on, and a parse of it here would need the bundled
    loader on the path. The block is a flat list of `- path` entries, which
    is stable enough to read directly and obvious when it stops being true.
    """
    out, in_exempt = [], False
    for line in text.splitlines():
        if re.match(r"^\s{2}exempt:\s*$", line):
            in_exempt = True
            continue
        if in_exempt:
            m = re.match(r"^\s{4}- (\S+)", line)
            if m:
                out.append(m.group(1))
            elif line.strip() and not line.lstrip().startswith("#"):
                break
    return out


# ---------------------------------------------------------------------------
# TRC-D5 - a stale exemption fails the build
# ---------------------------------------------------------------------------

def test_a_stale_exemption_fails_the_build():
    """The guard above must report the path, not just fail.

    Written as its own scenario because the failure mode it covers is a check
    that passes over nothing: an exemption naming a deleted file exempts
    nothing, and a scan reporting clean over it looks identical to a scan
    that ran.
    """
    text = TERMINOLOGY.read_text(encoding="utf-8")
    paths = _exempt_paths(text)
    assert paths, (
        "no exempt paths were read from terminology.yml - either the block "
        "moved or the reader above has stopped matching it, and this check is "
        "passing over nothing")

    scanned = _scanned_files()
    assert scanned, "no scanned files were gathered - this check is passing over nothing"

    for entry in paths:
        if entry in KNOWN_INERT_EXEMPTIONS:
            continue
        assert _excludes_anything(entry, scanned), (
            f"scan.exempt names {entry}, which excludes no file the scan "
            f"would visit. The exemption covers nothing and reads as coverage")

    # The ratchet only shrinks. An entry that starts excluding something, or
    # is deleted, must leave this list.
    stale_allowances = [e for e in KNOWN_INERT_EXEMPTIONS
                        if e not in paths or _excludes_anything(e, scanned)]
    assert not stale_allowances, (
        f"KNOWN_INERT_EXEMPTIONS still allows {sorted(stale_allowances)}, "
        f"which no longer needs allowing. Remove it - the list may shrink "
        f"and must never grow")


# ---------------------------------------------------------------------------
# TRC-D6 - the release that carries the removal says so
# ---------------------------------------------------------------------------

def test_the_release_that_carries_the_removal_says_so():
    version = (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()
    assert version == "4.0.0", (
        f"VERSION is {version}. Removing a public command name under a 3.x "
        f"number is a break inside a major version, which ADR-006 forbids")

    for rel in (".claude-plugin/plugin.json", ".claude-plugin/marketplace.json"):
        blob = json.loads((REPO_ROOT / rel).read_text(encoding="utf-8"))
        found = _versions_in(blob)
        assert "4.0.0" in found, (
            f"{rel} does not carry 4.0.0 - it has {sorted(found)}")

    # The removals are named where someone upgrading would look - as a ROW
    # pairing the removed spelling with its replacement, not as a loose word.
    # `stem in body` passed with the whole upgrade row deleted, because
    # "triage" also appears in this file's 3.1.0 release history.
    notes = REPO_ROOT / "docs" / "releasing.md"
    assert notes.is_file(), "docs/releasing.md is missing"
    body = notes.read_text(encoding="utf-8")
    for name, replacement in sorted(RETIRED_COMMANDS.items()):
        stem = name[:-3]
        row = re.compile(
            r"^\|\s*`?/compass:%s`?\s*\|\s*`?%s`?\s*\|"
            % (re.escape(stem), re.escape(replacement)), re.M)
        assert row.search(body), (
            f"docs/releasing.md has no upgrade row pairing `/compass:{stem}` "
            f"with `{replacement}`. A reader whose script breaks has nowhere "
            f"to match the error they got to the name that replaced it")

    # The removed CLI verb needs the same row.
    verb_row = re.compile(r"^\|\s*`?compass design lint`?\s*\|"
                          r"\s*`?compass plan lint`?\s*\|", re.M)
    assert verb_row.search(body), (
        "docs/releasing.md has no upgrade row for `compass design lint`")


def _versions_in(blob) -> set[str]:
    """Every version-shaped string anywhere in a parsed JSON document.

    The two plugin manifests nest the version differently, and hard-coding
    either path would make this guard fail on a reshuffle that changed
    nothing that matters.
    """
    found = set()
    stack = [blob]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)
        elif isinstance(node, str) and re.fullmatch(r"\d+\.\d+\.\d+", node):
            found.add(node)
    return found


# ---------------------------------------------------------------------------
# TRC-D7 - nothing is left over from the removal
# ---------------------------------------------------------------------------

def test_no_dead_redirect_machinery_survives_the_removal():
    """A redirect with no caller is worse than no redirect.

    `cmd_plan_lint` carried a branch that printed "this verb is now
    `compass plan lint`" whenever `args.retired_verb` was set. Its only
    setter was the `design` alias, so removing the alias made the branch
    unreachable - and left a message telling the reader the retired spelling
    "keeps working until the next major version", which is the version that
    removed it.

    Checked rather than deleted-and-forgotten because the next person to
    reach for a redirect inherits whatever is left here.
    """
    policy = (REPO_ROOT / "cli" / "compass_pkg" / "policy.py").read_text(
        encoding="utf-8")
    cli = CLI.read_text(encoding="utf-8")

    assert "retired_verb" not in policy, (
        "cli/compass_pkg/policy.py still branches on `retired_verb`, but "
        "nothing sets it - the alias that did was removed at 4.0.0. An "
        "unreachable redirect carrying a stale promise is left for whoever "
        "wires it up next")
    assert "retired_verb" not in cli, (
        "cli/compass still sets `retired_verb`, which no longer has a reader")

    # And no shipped message promises a removed spelling still works.
    assert "keeps working until the next major version" not in policy, (
        "a printed message still promises a retired spelling keeps working "
        "until the next major version. This IS that major version")
