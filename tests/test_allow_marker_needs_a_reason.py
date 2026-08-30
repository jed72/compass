"""A scan exemption needs a reason a person wrote (issue
allow-marker-supplies-its-own-reason).

`governance/terminology.yml` argues that a per-line marker beats a path prefix
because it is countable:

    grep -rn "vocabulary-scan: allow" .

enumerates every exemption, each carrying the reason someone wrote for it. That
argument only holds if the reason is real. The pattern demanded
`allow\\s*-\\s*\\S`, and in markdown the marker lives inside an HTML comment
whose `-->` supplies the dash and a non-space - so
`<!-- vocabulary-scan: allow -->` was accepted as reasoned while carrying
nothing. Nine markers in scanned markdown are HTML comments, so this is the
normal shape in prose.

Scenario ids: TRC-A1, TRC-A2, TRC-B1 in
.compass/work/allow-marker-supplies-its-own-reason/acceptance-criteria.md
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Every guard that honours the marker. Each must use the shared definition
# rather than its own copy - three copies of one rule drift, and these already
# had: two required a letter while the third accepted any non-space.
HONOURING_GUARDS = (
    "tests/test_terminology.py",
    "tests/test_docs_prose.py",
    "tests/test_documented_commands_exist.py",
)

SHARED_DEFINITION = "tests/allow_marker.py"

# An attempt at an exemption, as opposed to a mention of the marker. The dash
# is what makes it an attempt; the shared pattern then decides whether the
# reason after it is real.
ATTEMPT_RE = re.compile(r"vocabulary-scan:\s*allow\s*-")


def _marker_re():
    """The one definition, imported the way the guards import it."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_allow_marker", REPO_ROOT / SHARED_DEFINITION)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.ALLOW_MARKER_RE


# ---------------------------------------------------------------------------
# TRC-A1 - a marker with no reason is refused
# ---------------------------------------------------------------------------

def test_a_marker_with_no_reason_is_refused():
    pattern = _marker_re()

    bare = [
        "<!-- vocabulary-scan: allow -->",
        "# vocabulary-scan: allow -",
        "<!-- vocabulary-scan: allow - -->",
    ]
    for line in bare:
        assert not pattern.search(line), (
            f"a marker with no reason was accepted: {line!r}. The `-->` that "
            f"closes an HTML comment supplies a dash and a non-space "
            f"character, so a pattern asking only for `- <non-space>` reads "
            f"the comment terminator as the reason")


# ---------------------------------------------------------------------------
# TRC-A2 - a marker with a real reason still exempts
# ---------------------------------------------------------------------------

def test_a_marker_with_a_real_reason_still_exempts():
    pattern = _marker_re()

    real = [
        "<!-- vocabulary-scan: allow - the upgrade table names the removed spelling -->",
        "# vocabulary-scan: allow - ordinary verb, not the retired stage name",
        "    - entry  # vocabulary-scan: allow - the mapping data must name both",
    ]
    for line in real:
        assert pattern.search(line), (
            f"a marker carrying a written reason was rejected: {line!r}")

    # And every marker already in the repository still works. Tightening a
    # pattern that guards live exemptions must not silently un-exempt them.
    #
    # Read from the surfaces the vocabulary scan actually visits, using the
    # scan's own file gatherer. Sweeping the whole repository counted prose
    # that DISCUSSES the marker as if it carried one: `terminology.yml` quotes
    # the grep command in a comment, the guards match the string to decide
    # whether to skip a line, and this file quotes bare markers on purpose as
    # the thing being refused. None of those is an exemption anybody relies on.
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_terminology_scan", REPO_ROOT / "tests" / "test_terminology.py")
    scan = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scan)
    cfg = scan._terminology()["scan"]

    live, rejected = 0, []
    for surface in cfg["surfaces"]:
        for path in scan._surface_files(surface):
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for n, line in enumerate(text.splitlines(), 1):
                # An ATTEMPTED exemption is the marker followed by a dash.
                # Without one it is a mention - `terminology.yml` quotes the
                # `grep -rn "vocabulary-scan: allow" .` command in a comment
                # while arguing why per-line markers are countable, and that
                # sentence exempts nothing.
                if not ATTEMPT_RE.search(line):
                    continue
                live += 1
                if not pattern.search(line):
                    rejected.append(f"{path.relative_to(REPO_ROOT)}:{n}")

    assert live >= 10, (
        f"only {live} markers were found in the repository - the sweep has "
        f"stopped matching and this check is passing over almost nothing")
    assert not rejected, (
        "tightening the pattern un-exempted markers that carry a real "
        "reason:\n  " + "\n  ".join(rejected))


# ---------------------------------------------------------------------------
# TRC-B1 - the guards that honour the marker share its definition
# ---------------------------------------------------------------------------

def test_the_guards_that_honour_the_marker_share_its_definition():
    shared = REPO_ROOT / SHARED_DEFINITION
    assert shared.is_file(), (
        f"{SHARED_DEFINITION} is missing, so each guard is free to define the "
        f"marker its own way again")

    for rel in HONOURING_GUARDS:
        body = (REPO_ROOT / rel).read_text(encoding="utf-8")
        assert "vocabulary-scan: allow" in body, (
            f"{rel} no longer honours the marker at all, so this list is "
            f"stale and the check below is asserting nothing about it")
        assert "allow_marker import" in body or "from allow_marker" in body, (
            f"{rel} does not import the shared marker definition. Three "
            f"copies of one rule drift apart - these already had, with two "
            f"requiring a letter and one accepting any non-space, which is "
            f"the defect this issue exists to close")
        assert not re.search(r"^ALLOW_MARKER_RE\s*=\s*re\.compile", body, re.M), (
            f"{rel} defines its own ALLOW_MARKER_RE alongside the shared one")
