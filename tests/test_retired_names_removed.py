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
    assert "plan" in out, (
        "the unknown-verb error does not name `plan`, so a reader whose "
        "script breaks is not told what to call it now")

    # The `hidden` set is only ever subtracted from the advertised verb list,
    # so an entry naming a verb that no longer exists is silent. Checked here
    # because nothing else would notice.
    source = CLI.read_text(encoding="utf-8")
    match = re.search(r"^\s*hidden = \{(.*?)\}", source, re.M)
    if match:
        assert not match.group(1).strip(), (
            f"the `hidden` set still names {match.group(1).strip()}, but the "
            f"verb it hides is gone. A stale entry here is invisible: the set "
            f"is only ever subtracted from the public verb list")

    # Nothing parses that --help does not advertise, apart from the internal
    # underscore-prefixed verbs, which are deliberately not public.
    code, out = _run("--help")
    assert code == 0, out


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

    # Every exemption must still cover something. An entry matching nothing
    # exempts nothing, and a scan reporting clean over it looks identical to
    # a scan that ran.
    empty = [e for e in _exempt_paths(text) if not _matches_anything(e)]
    assert not empty, (
        f"scan.exempt entr(ies) match no file: {', '.join(empty)}")


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


def _deliberately_absent(entry: str) -> bool:
    """Is this path one the repository intentionally does not ship?

    `docs/proposals/`, `docs/analysis/` and `.compass/work/` are gitignored -
    present in a working clone, absent from a packaged export or a fresh
    checkout. An exemption naming one of those is not stale; it covers files
    that exist wherever the scan actually runs.

    Read from `.gitignore` rather than hardcoded, and rooted comparisons only,
    so this cannot quietly start excusing a path nobody ignores. `.gitignore`
    is tracked, so it is present in an export too - which is the whole reason
    this check can run there.
    """
    ignore = REPO_ROOT / ".gitignore"
    if not ignore.is_file():
        return False
    for line in ignore.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "*" in line:
            continue
        pattern = line.lstrip("/")
        if pattern and (entry.startswith(pattern) or pattern.startswith(entry)):
            return True
    return False


def _matches_anything(entry: str) -> bool:
    """Does this exemption still cover at least one file?

    Entries are PREFIXES, not paths - the scan tests
    `rel.startswith(exempt)`, so `docs/proposals/` covers a directory and
    `templates/architecture/decisions/ADR-0` covers the sample records
    ADR-001 through ADR-005. Checking for a file at the literal path would
    call every prefix entry stale.

    A gitignored path counts as covered. This guard has to give the same
    answer in a working clone and in a packaged export, or it fails on
    continuous integration for a reason that has nothing to do with the
    exemption being stale.
    """
    if (REPO_ROOT / entry).exists():
        return True
    if _deliberately_absent(entry):
        return True
    return any(str(p.relative_to(REPO_ROOT)).startswith(entry)
               for p in REPO_ROOT.rglob("*") if p.is_file())


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

    for entry in paths:
        assert _matches_anything(entry), (
            f"scan.exempt names {entry}, which matches no file in the "
            f"repository. The exemption covers nothing and reads as coverage")


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

    # The removals are named where someone upgrading would look.
    notes = REPO_ROOT / "docs" / "releasing.md"
    assert notes.is_file(), "docs/releasing.md is missing"
    body = notes.read_text(encoding="utf-8")
    for name in sorted(RETIRED_COMMANDS):
        stem = name[:-3]
        assert stem in body, (
            f"docs/releasing.md does not name `{stem}` among the removals. A "
            f"reader whose script breaks has nowhere to find out why")


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
