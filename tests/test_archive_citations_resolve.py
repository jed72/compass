"""A citation into the issue archive must open.

Compass's whole claim is an audit trail: a document says where its evidence
is, and a reader follows the path. A path that does not resolve is not a weak
citation - it is no citation at all, and it looks exactly like a good one.

This went unnoticed because nothing checked it. The v2 vocabulary freeze
migrated the archive, renaming `spec.feature.md` to `acceptance-criteria.md`
in every issue directory, and left 22 test modules citing the old name in
their provenance line. Each of those reads:

    Spec: .compass/work/<slug>/spec.feature.md (TRC-A1..A3, ...)

and none of them opens. ADR-014 said the archive would never be edited, which
would have avoided this; ADR-020 supersedes that and migrates the archive
deliberately, with this guard as the condition - the cost is paid once,
visibly, rather than accumulating unmeasured.

Scenario id: TRC-E4, .compass/work/the-vocabulary-rename/acceptance-criteria.md
"""
from __future__ import annotations

import os
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

CITATION = re.compile(r"\.compass/work/[a-z0-9-]+/[a-z.-]+\.(?:md|feature)")

# A citation is prose that points a reader at a record. A path built inside a
# call - `make_task([".compass/work/demo/technical-design.md"])` - is a fixture
# describing a directory the test creates, and there is nothing to open. The
# difference is the label, so the label is what this looks for in code files.
# Markdown is prose throughout and needs no label.
CITATION_LABEL = re.compile(
    r"(?i)\b(spec|scenario ids?|scenarios|source|source-of-truth|issue|record|"
    r"see|from|per)\b[^\n]{0,40}?\.compass/work/")

# Untracked planning directories, and the archive itself - a record may cite a
# sibling record that has since been renamed, and ADR-020 migrates the archive
# mechanically rather than hand-editing its prose.
SKIP_PREFIXES = (".compass/", "docs/proposals", "docs/analysis",
                 # This file. Its controls quote a citation that must NOT
                 # resolve, which is the only way to prove the guard can fail.
                 "tests/test_archive_citations_resolve.py")
SKIP_DIRS = {".git", "node_modules", "__pycache__"}

# Paths that LOOK like a citation and are not, each with the reason. A list
# rather than a looser pattern: a rule wide enough to let these through would
# also let a real broken citation through, and this way the exceptions are
# enumerable - `grep -n ILLUSTRATIVE tests/` shows every one.
ILLUSTRATIVE = {
    ".compass/work/fix-jwt-typo/delivery-approach.md":
        "docs/five-minutes.md walks a worked example through the pipeline. "
        "The path is what the tutorial's imaginary issue would print, not a "
        "record in this repository.",
    ".compass/work/fixture-issue/devlog.md":
        "test_archive_quote_manifest.py builds this path as the `source:` of "
        "a synthetic quote manifest. The directory is created by the test.",
}
SUFFIXES = (".md", ".py", ".yml", ".yaml", ".sh")


def _search_roots():
    """Where a citation may be rooted.

    The repo root for everything shipped, plus every directory that holds a
    `.compass/` tree of its own - the worked examples, and the BDD adapter
    examples one level below them. A README inside an example cites paths
    relative to that example, not to the repository.
    """
    roots = [REPO_ROOT]
    examples = REPO_ROOT / "examples"
    if examples.is_dir():
        roots += sorted(p.parent for p in examples.rglob(".compass")
                        if p.is_dir())
    return roots


def _unopenable():
    roots = _search_roots()
    found = {}
    for path in sorted(REPO_ROOT.rglob("*")):
        if not path.is_file() or path.suffix not in SUFFIXES:
            continue
        rel = str(path.relative_to(REPO_ROOT))
        if SKIP_DIRS & set(path.parts) or rel.startswith(SKIP_PREFIXES):
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        prose = path.suffix in (".md", ".yml", ".yaml")
        for lineno, line in enumerate(lines, 1):
            if not prose and not CITATION_LABEL.search(line):
                continue
            for cite in CITATION.findall(line):
                if cite in ILLUSTRATIVE:
                    continue
                if any((r / cite).is_file() for r in roots):
                    continue
                found.setdefault(cite, []).append("%s:%d" % (rel, lineno))
    return found


def test_trc_e4_every_citation_into_the_archive_opens():
    """Every path into `.compass/work/` named on a shipped surface resolves.

    The failure names the citation and every file making it, because the fix
    is always the same shape - the record moved, and the pointer did not - and
    a reader needs to see the whole set at once rather than one per run.
    """
    bad = _unopenable()
    report = "\n  ".join(
        "%s\n      cited by: %s" % (cite, ", ".join(where))
        for cite, where in sorted(bad.items()))
    assert not bad, (
        "%d citation(s) into the issue archive do not resolve. A path that "
        "does not open is not a weak citation, it is no citation - and it "
        "reads exactly like a good one:\n  %s" % (len(bad), report))


def test_trc_e4b_the_guard_catches_a_path_that_does_not_exist():
    """The control: prove the guard can fail.

    Without this, a rule change that stopped matching citations entirely would
    leave the test above green while checking nothing - which is the failure
    this repository found four of in one release (`governance/strategies.md`
    S10: a guard is accepted on a demonstrated failure, not on a passing
    test).
    """
    line = "Spec: .compass/work/no-such-issue-here/spec.feature.md (TRC-A1)."
    assert CITATION_LABEL.search(line), "the label rule no longer sees a citation"
    cite = CITATION.search(line)
    assert cite, "the citation pattern no longer matches a citation"
    assert not any((r / cite.group(0)).is_file() for r in _search_roots()), (
        "the path this control relies on being absent exists")


def test_trc_e4c_the_guard_ignores_a_path_a_test_builds():
    """A fixture path is not a citation, and must not be reported as one.

    `make_task([".compass/work/demo/technical-design.md"])` names a directory
    the test creates. Reporting it would flood the real findings with noise
    and train a reader to skip the failure.
    """
    fixture = '    task = make_task([".compass/work/demo/technical-design.md"])'
    assert CITATION.search(fixture), "the fixture line does not contain a path"
    assert not CITATION_LABEL.search(fixture), (
        "a path built inside a call is being read as a citation")


def test_trc_e4d_every_illustrative_path_carries_a_reason():
    """The exemption list is not a place to park a broken citation.

    Each entry says why the path is not a record, in a sentence a reader can
    disagree with. An empty or one-word reason is how a list like this turns
    into a blanket.
    """
    for path, why in ILLUSTRATIVE.items():
        assert len(why.split()) >= 6, (
            "%s is exempt with no real reason: %r" % (path, why))
