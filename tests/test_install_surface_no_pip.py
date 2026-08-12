"""Scenario group D - the instruction surface.

TRC-D1: nothing tracked instructs a user or an adopter to `pip install`
PyYAML. TRC-D3: the copyable CI workflow has no dependency-install step.
TRC-D4: the install smoke test asserts the zero-install path rather than
setting one up. TRC-D6: no tracked document claims Compass carries nothing
beyond the standard library, in any of that claim's usual phrasings, and
none says PyYAML is a package the reader installs rather than something the
plugin already carries.

The scanner matches `pip install` forms specifically, not the bare word
"pip" - `docs/security.md`'s corrected audit instructions legitimately
contain `pip download pyyaml==6.0.2` (how an auditor reproduces the vendored
tree), and a scanner that fired on that sentence would fail the build on the
exact text that repairs the audit posture.

Every needle this file searches for is assembled from its parts at import
time, the same convention `tests/test_house_style.py` uses for its banned
em dash and co-author trailer - so this scanner, and any test file that
merely *discusses* the removed instruction, never has to exempt itself from
its own rule.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent

# Assembled from parts - see the module docstring - so this file's own source
# never contains the literal banned command.
_PIP = "pip"
_INSTALL = "install"
_PYYAML = "pyyaml"

# `pip install <anything up to 200 chars> pyyaml` - the actual command shape,
# not the bare co-occurrence of the words "pip" and "pyyaml" on a line (that
# would also match the legitimate `pip download` audit instruction).
_PIP_INSTALL_PYYAML_RE = re.compile(
    rf"{_PIP}\s+{_INSTALL}\b[^\n]{{0,200}}\b{_PYYAML}\b", re.IGNORECASE)

# Text that claims Compass has nothing to bundle at all - assembled the same
# way, and deliberately narrow: a generic "no dependencies" pattern once
# false-positived on schemas/README.md's true, unrelated claim that the
# built-in structural linter (not the CLI as a whole) needs none.
_STDLIB_ONLY_RES = [
    re.compile(r"\bstdlib" + r"[\s-]only\b", re.IGNORECASE),
    re.compile(r"\bpure" + r"[\s-]standard" + r"[\s-]library\b", re.IGNORECASE),
    re.compile(r"\b" + "dependency" + r"[\s-]free\b", re.IGNORECASE),
    # The two claim shapes TRC-D6's own comment names as what was actually
    # in the tree before this issue: "its only hard dependency is PyYAML"
    # and "depends only on Python 3 and PyYAML". Neither of the three
    # needles above ever matched either one (probe 8) - these two do, and
    # narrowly enough that the corrected wording ("bundled", "travels inside
    # the plugin") does not trip them.
    re.compile(r"\bonly\s+(?:hard\s+)?dependency\s+is\s+PyYAML\b", re.IGNORECASE),
    re.compile(r"\bdepends?\s+only\s+on\s+Python\s*3\s+and\s+PyYAML\b", re.IGNORECASE),
    re.compile(r"\bdependency\s+is\s+Python\s*3\s+and\s+PyYAML\b", re.IGNORECASE),
]

# Directories not to walk - build output, VCS internals, vendored third-party
# source (which legitimately names pip/PyYAML in its own upstream files).
_EXCLUDE_DIR_PREFIXES = (
    ".git/", "dist/", "cli/vendor/", "node_modules/",
)

# This file and its sibling TRC-D5 test discuss the removed instruction by
# name, in prose about its own absence - not a shipped instruction. Excluded
# the same way `tests/test_house_style.py` excludes nothing by exemption and
# everything by construction; here the discussion is unavoidable in a
# docstring, so it is excluded explicitly instead.
_SELF_REFERENTIAL_FILES = {
    "tests/test_install_surface_no_pip.py",
    "tests/test_plugin_doc_drift.py",
    # Both assert the phrase's ABSENCE from CLI output/docs - the phrase
    # appears in their own source as the needle they check for, not as an
    # instruction to anyone.
    "tests/test_zero_install_cli.py",
    "tests/test_release_packaging.py",
    # The case study's subject IS the retired instruction. It quotes
    # `pip install pyyaml` to say what the quickstart used to tell people,
    # and the word "stdlib-only" to correct a premise the repository never
    # actually claimed. Both are history being reported, not an instruction
    # being given. `tests/test_public_copy_claims.py` guards the other
    # direction - that the file keeps stating the correction rather than
    # drifting into the claim.
    "docs/case-study-compass-rebuilt-itself.md",
    # Guards the case study's exemption above, so it necessarily quotes the
    # same two phrases as the needles it looks for.
    "tests/test_public_copy_claims.py",
}


def _tracked_and_untracked_files():
    """Every file this repository currently has, enumerated at run time -
    tracked (with any uncommitted edits) and untracked-but-not-gitignored
    alike, so a file this session added is covered as much as one already
    committed."""
    listing = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=str(FRAMEWORK_ROOT), capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    out = []
    for rel in listing:
        if any(rel.startswith(p) for p in _EXCLUDE_DIR_PREFIXES):
            continue
        full = FRAMEWORK_ROOT / rel
        if full.is_file():
            out.append(rel)
    return out


def _read_text(rel: str) -> str:
    try:
        return (FRAMEWORK_ROOT / rel).read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return ""


def test_no_shipped_instruction_installs_pyyaml():
    """TRC-D1: no tracked file - Markdown, YAML, shell, or Python - contains
    a `pip install ... pyyaml` command."""
    hits = []
    for rel in _tracked_and_untracked_files():
        if rel in _SELF_REFERENTIAL_FILES:
            continue
        text = _read_text(rel)
        if not text:
            continue
        for m in _PIP_INSTALL_PYYAML_RE.finditer(text):
            line_no = text.count("\n", 0, m.start()) + 1
            hits.append(f"{rel}:{line_no}: {m.group(0)!r}")
    assert not hits, (
        "the following tracked files still instruct a `pip install ... "
        "pyyaml`:\n  " + "\n  ".join(hits)
    )


def test_adopter_ci_template_needs_no_pip_step():
    """TRC-D3: the reference workflow and its copyable snippets have no step
    installing a Python package in order to run `compass ci` - checkout, set
    up Python, run `compass ci`."""
    ci_workflow = _read_text("ci/github-actions.yml")
    assert "pip install" not in ci_workflow.lower(), ci_workflow
    assert "actions/checkout" in ci_workflow
    assert "setup-python" in ci_workflow
    assert re.search(r"run:\s*python3\s+\S*COMPASS_CLI\S*\s+ci", ci_workflow), ci_workflow

    readme = _read_text("README.md")
    assert not _PIP_INSTALL_PYYAML_RE.search(readme), readme

    ci_readme = _read_text("ci/README.md")
    assert not _PIP_INSTALL_PYYAML_RE.search(ci_readme), ci_readme


def test_install_smoke_test_asserts_the_zero_install_path():
    """TRC-D4: the smoke test proves the claim rather than setting it up -
    no PyYAML install step, a step that runs the CLI on an interpreter with
    no third-party packages and states the expected output, and the old
    'PyYAML missing' gotcha is gone."""
    text = _read_text("docs/install-smoke-test.md")
    assert not _PIP_INSTALL_PYYAML_RE.search(text), text
    assert "PyYAML missing" not in text, text
    assert "venv" in text and "--without-pip" in text, (
        "expected a step that runs the CLI on an interpreter with no "
        "third-party packages on its path"
    )
    assert "compass --version" in text or "cli/compass --version" in text, text


def test_no_test_locks_the_removed_instruction():
    """TRC-D5: no test's *anchor* - the pattern it requires README to match -
    still requires the removed pip-install line. `test_plugin_doc_drift.py`
    may still discuss that history in a comment (excluded above as
    self-referential); what it must not do is search for a regex ending in
    the old line, because that would fail once README no longer has it.
    The real evidence for this scenario is the whole suite passing with the
    line gone - this is the one anchor known to have depended on it."""
    text = _read_text("tests/test_plugin_doc_drift.py")
    old_anchor = re.compile(
        r're\.search\(\s*\n?\s*r?["\'][^"\']*' + _PIP + r"." + _INSTALL
        + r"." + _PYYAML + r'["\']', re.IGNORECASE)
    assert not old_anchor.search(text), (
        "a test still searches for a regex ending in the removed "
        "pip-install line:\n" + text
    )
    readme = _read_text("README.md")
    assert not _PIP_INSTALL_PYYAML_RE.search(readme)


def test_stdlib_only_patterns_catch_the_claim_shapes_that_actually_shipped():
    """Unit-level proof the document-half needles fire on real prose, not
    only on strings nobody ever wrote (probe 8: before this widening, none
    of the three original needles - "stdlib-only", "pure standard library",
    "dependency-free" - ever matched anything in this repository's history,
    because the actual claim was phrased two other ways)."""
    shape_one = "Its only hard dependency is PyYAML. `jsonschema` is optional."
    shape_two = ("This layer is tool-agnostic - its only hard dependency is "
                "Python 3 and PyYAML (`jsonschema` is optional), and nothing "
                "in it knows what Claude Code is.")
    corrected = ("Compass needs Python 3. The YAML parser it uses travels "
                "inside the plugin, so there is nothing to install.")

    assert any(p.search(shape_one) for p in _STDLIB_ONLY_RES), shape_one
    assert any(p.search(shape_two) for p in _STDLIB_ONLY_RES), shape_two
    assert not any(p.search(corrected) for p in _STDLIB_ONLY_RES), corrected


def test_no_document_claims_compass_is_stdlib_only():
    """TRC-D6: no tracked document says Compass is stdlib-only, pure
    standard library, or dependency-free; none says PyYAML is a dependency
    the reader installs; each that names PyYAML says it is bundled."""
    hits = []
    for rel in _tracked_and_untracked_files():
        if not rel.endswith((".md", ".py")):
            continue
        if rel in _SELF_REFERENTIAL_FILES:
            continue
        text = _read_text(rel)
        if not text:
            continue
        for pattern in _STDLIB_ONLY_RES:
            m = pattern.search(text)
            if m:
                line_no = text.count("\n", 0, m.start()) + 1
                hits.append(f"{rel}:{line_no}: {m.group(0)!r}")
    assert not hits, (
        "the following files still claim Compass has no dependencies:\n  "
        + "\n  ".join(hits)
    )

    # The sixteen CLI module headers + cli/compass, checked directly: each
    # must say "bundled", not "pip install" or "the only dependency" framed
    # as something to install.
    cli_files = ["cli/compass"] + sorted(
        str(p.relative_to(FRAMEWORK_ROOT))
        for p in (FRAMEWORK_ROOT / "cli" / "compass_pkg").glob("*.py")
        if p.name not in ("__init__.py", "_all.py")
    )
    header_problems = []
    checked = []
    unmarked = []
    for rel in cli_files:
        text = _read_text(rel)
        if "DEPENDENCY: PyYAML" not in text:
            # Self-exempting: a module that stops carrying the marker used to
            # leave this check silently, so coverage could drain away without
            # a red. Collect them and assert on the set instead.
            unmarked.append(rel)
            continue
        checked.append(rel)
        if "bundled" not in text.lower():
            header_problems.append(rel)
        if _PIP_INSTALL_PYYAML_RE.search(text):
            header_problems.append(rel)

    # The antidote: prove the scan actually read what it claims to cover.
    # `migrate.py` and `terminology_cmd.py` carry no dependency header today
    # and are named here deliberately, so a THIRD module quietly losing its
    # header fails rather than shrinking the check.
    assert set(unmarked) <= {"cli/compass_pkg/migrate.py",
                             "cli/compass_pkg/terminology_cmd.py"}, (
        "these CLI files no longer carry a dependency header, so this scan "
        "silently stopped covering them:\n  " + "\n  ".join(sorted(unmarked))
    )
    assert len(checked) >= len(cli_files) - 2, (
        f"the scan read only {len(checked)} of {len(cli_files)} CLI files"
    )
    assert not header_problems, (
        "these CLI files still describe PyYAML as something to install "
        "rather than something bundled:\n  " + "\n  ".join(header_problems)
    )


# ---------------------------------------------------------------------------
# The audit instruction - one runnable copy, referenced, not restated
# (found by review: the old three-copy version had no extraction step, no
# __pycache__ exclusion, and disagreed with itself on the path)
# ---------------------------------------------------------------------------


def test_third_party_notices_audit_instruction_is_complete_and_self_consistent():
    """`THIRD-PARTY-NOTICES.md` carries the one runnable reproduce-and-diff
    block. Checked statically (shape and internal consistency) rather than
    by actually running `pip download` in the suite - a network call in an
    ordinary test run is exactly the intermittency risk this repository's own
    discipline (S5) warns against. The block was run for real, once, by hand
    (see devlog) and produced no output, confirming the shape asserted here
    is also the shape that works."""
    text = _read_text("THIRD-PARTY-NOTICES.md")
    m = re.search(r"```\n\s*(pip download.*?expect no output)\n\s*```", text, re.S)
    assert m, "no fenced reproduce block found in THIRD-PARTY-NOTICES.md"
    lines = [l.strip() for l in m.group(1).splitlines() if l.strip()]
    assert len(lines) == 4, (
        f"expected download, hash, extract, diff - got {len(lines)}:\n{lines}")

    download, hash_check, extract, diff = lines
    assert download.startswith("pip download pyyaml==6.0.2"), download
    assert "-d /tmp/pyyaml-src" in download, download
    assert hash_check.startswith("shasum -a 256 /tmp/pyyaml-src/pyyaml-6.0.2.tar.gz"), hash_check
    # The step the old instruction skipped: pip download only saves the
    # archive, it does not unpack it, so a diff step immediately after would
    # target a directory that does not exist yet.
    assert extract.startswith("tar xzf /tmp/pyyaml-src/pyyaml-6.0.2.tar.gz"), extract
    assert "-C /tmp/pyyaml-src" in extract, extract
    assert diff.startswith("diff -r -x __pycache__"), (
        f"the diff step must exclude __pycache__ - Python writes it into "
        f"cli/vendor/yaml/ on first run, which breaks 'expect no output' "
        f"otherwise:\n{diff}")
    # The extract step's output directory is exactly the diff step's input -
    # the two are not free to disagree on where the tree landed.
    assert "/tmp/pyyaml-src/pyyaml-6.0.2/lib/yaml" in diff, diff
    assert "cli/vendor/yaml" in diff, diff


def test_other_two_copies_point_at_the_one_runnable_block_rather_than_restate_it():
    """`cli/vendor/README.md` and `docs/security.md` used to each carry their
    own copy of the reproduce command, and the three disagreed - two
    different paths and one internal self-contradiction
    (`THIRD-PARTY-NOTICES.md` treating `/tmp/pyyaml-src/pyyaml-6.0.2.tar.gz`
    as an archive on one line and a directory on the next). One copy, two
    references."""
    for rel in ("cli/vendor/README.md", "docs/security.md"):
        text = _read_text(rel)
        assert "pip download" not in text, (
            f"{rel} restates the reproduce command instead of pointing at "
            f"THIRD-PARTY-NOTICES.md - a second copy is a second chance to "
            f"drift")
        assert "THIRD-PARTY-NOTICES.md" in text, (
            f"{rel} does not point the reader at the one runnable copy")
