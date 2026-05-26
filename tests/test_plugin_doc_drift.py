"""Acceptance tests for task fix-plugin-doc-drift.

Each test_trc_* function asserts the fix for one scenario in
.compass/work/fix-plugin-doc-drift/spec.feature.md. The "production" change
is text in README.md, AGENTS.md, and docs/*.md, so these tests are grep/regex
assertions over the published doc files.

Why this file exists separate from the rest of tests/: the existing test
suite defends the CLI's safety contract (see tests/README.md). These tests
defend a one-off documentation fix. They are still real tests — they run
under `pytest tests/`, they fail when the docs drift, and `compass tdd-red`
/ `compass tdd-green` write typed test-run evidence the verify gates accept.
"""
import re
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _read(rel):
    return (ROOT / rel).read_text()


# ---------------------------------------------------------------------------
# Group A — install-surface accuracy (D1)
# ---------------------------------------------------------------------------

def test_trc_a1_readme_source_install_has_path_note():
    """README's source-install paragraph tells the reader how to invoke the
    compass CLI — by adding bin/ to PATH or via `python3 cli/compass`."""
    readme = _read("README.md")

    # The source-install code block (clone → bash install.sh → pip install).
    m = re.search(
        r"git clone https://github\.com/jed72/compass\.git.*?pip install pyyaml",
        readme,
        re.DOTALL,
    )
    assert m, "Source-install code block not found in README.md"

    # Within 800 chars after the block, expect a CLI-invocation instruction.
    after = readme[m.end():m.end() + 800]
    has_path_note = bool(
        re.search(r"add\s+\S*bin\b[^.]*?\bPATH\b", after, re.IGNORECASE)
        or re.search(r"\bPATH\b[^.]*?\bbin\b", after)
        or re.search(r"python3\s+\S*cli/compass", after)
    )
    assert has_path_note, (
        "README's source-install paragraph does not tell the reader how to "
        "make `compass` invokable. Expected a phrase about adding `bin/` to "
        "PATH or invoking as `python3 cli/compass`. Looked in 800 chars "
        "following the source-install code block; got:\n"
        + after[:400]
    )


def test_trc_a2_quickstart_drops_install_sh_path_claim():
    """quickstart.md §1 must not claim install.sh modifies PATH, and must
    explain how to invoke the CLI after a source install."""
    quickstart = _read("docs/quickstart.md")

    # The misleading phrase from the Spike must be gone.
    misleading = re.search(
        r"puts\s+the\s+[`']?compass[`']?\s+CLI\s+on\s+your\s+path",
        quickstart,
        re.IGNORECASE,
    )
    assert misleading is None, (
        "quickstart.md still claims install.sh puts the compass CLI on PATH. "
        f"Found:\n"
        f"{quickstart[max(0, misleading.start()-60):misleading.end()+60] if misleading else ''}"
    )

    # And there must be a positive instruction about CLI invocation.
    has_invocation_note = bool(
        re.search(r"add\s+\S*bin\b[^.]*?\bPATH\b", quickstart, re.IGNORECASE)
        or re.search(r"\bPATH\b[^.]*?\bbin\b", quickstart)
        or re.search(r"python3\s+\$?\S*cli/compass", quickstart)
    )
    assert has_invocation_note, (
        "quickstart.md does not explain how to invoke the compass CLI after a "
        "source install. Expected a PATH note or a `python3 cli/compass` "
        "invocation hint."
    )


# ---------------------------------------------------------------------------
# Group B — adapter-layer file listings (D2)
# ---------------------------------------------------------------------------

def test_trc_b1_readme_tree_lists_bin_and_plugin_manifest():
    """README's 'What's in the box' tree contains entries for bin/ and
    .claude-plugin/."""
    readme = _read("README.md")
    m = re.search(
        r"##\s+What's in the box.*?(?=^##\s+|\Z)",
        readme,
        re.DOTALL | re.MULTILINE,
    )
    assert m, "'What's in the box' section not found in README.md"
    block = m.group(0)

    # The tree is the code block inside that section.
    code = re.search(r"```\n(.*?)\n```", block, re.DOTALL)
    assert code, "No fenced code block found in 'What's in the box'"
    tree = code.group(1)

    assert "bin/" in tree, "README's tree is missing the `bin/` entry"
    assert ".claude-plugin/" in tree, (
        "README's tree is missing the `.claude-plugin/` entry"
    )


def test_trc_b2_methodology_section_9_names_bin_and_plugin_manifest():
    """methodology.md §9's adapter-layer paragraph names bin/compass and
    .claude-plugin/."""
    method = _read("docs/methodology.md")
    m = re.search(
        r"##\s+9\.\s+The three layers.*?(?=^##\s+\d+\.|\Z)",
        method,
        re.DOTALL | re.MULTILINE,
    )
    assert m, "§9 'The three layers' not found in methodology.md"
    section9 = m.group(0)
    assert "bin/compass" in section9, (
        "methodology §9 does not name `bin/compass` as an adapter-layer artifact"
    )
    assert ".claude-plugin/" in section9, (
        "methodology §9 does not name `.claude-plugin/` as an adapter-layer artifact"
    )


def test_trc_b3_portability_adapter_block_and_mapping_table():
    """portability.md's adapter-layer block lists bin/ and .claude-plugin/,
    and the mapping table has a row for the install surface."""
    port = _read("docs/portability.md")

    # The adapter-layer block — the fenced code listing that starts with
    # `commands/` and lists agents/, skills/, hooks/, etc.
    m = re.search(
        r"###\s+The Claude Code adapter layer.*?(?=^###\s|\Z)",
        port,
        re.DOTALL | re.MULTILINE,
    )
    assert m, "'The Claude Code adapter layer' section not found in portability.md"
    adapter_section = m.group(0)
    code = re.search(r"```\n(.*?)\n```", adapter_section, re.DOTALL)
    assert code, "No fenced adapter-layer code block found in portability.md"
    block = code.group(1)
    assert "bin/" in block, "portability.md adapter-layer block missing `bin/`"
    assert ".claude-plugin/" in block, (
        "portability.md adapter-layer block missing `.claude-plugin/`"
    )

    # And there must be a mapping-table row about the install surface. The
    # row should reference the plugin shim or manifest.
    has_install_row = bool(
        re.search(r"\|\s*Install surface\s*\|", port, re.IGNORECASE)
        or (
            re.search(r"\|[^|\n]*bin/compass[^|\n]*\|", port)
            and re.search(r"\.claude-plugin", port)
        )
    )
    assert has_install_row, (
        "portability.md's mapping table does not have a row for the install "
        "surface. Expected either an explicit `| Install surface |` row, or a "
        "row mentioning `bin/compass` and `.claude-plugin/`."
    )


# ---------------------------------------------------------------------------
# Group C — runtime-neutral path string (D3)
# ---------------------------------------------------------------------------

def test_trc_c1_agents_uses_compass_prefix():
    """AGENTS.md's State on disk section uses .compass/work/<task-slug>/ (not
    the unprefixed work/<task-slug>/)."""
    agents = _read("AGENTS.md")
    m = re.search(
        r"##\s+State on disk.*?(?=^##\s+|\Z)",
        agents,
        re.DOTALL | re.MULTILINE,
    )
    assert m, "'State on disk' section not found in AGENTS.md"
    section = m.group(0)
    assert ".compass/work/<task-slug>/" in section, (
        "AGENTS.md State on disk does not use the `.compass/work/<task-slug>/` form"
    )
    bare = re.search(r"(?<!\.compass/)\bwork/<task-slug>/", section)
    assert bare is None, (
        "AGENTS.md State on disk still contains the unprefixed "
        "`work/<task-slug>/` form (must be `.compass/work/<task-slug>/`)"
    )


# ---------------------------------------------------------------------------
# Failure-mode coverage — no half-fix (F1)
# ---------------------------------------------------------------------------

def test_trc_f1_no_half_fix_misleading_phrases_removed():
    """No file contains its specific misleading phrase from the Spike's findings."""
    quickstart = _read("docs/quickstart.md")
    bad_quickstart = re.search(
        r"puts\s+the\s+[`']?compass[`']?\s+CLI\s+on\s+your\s+path",
        quickstart,
        re.IGNORECASE,
    )
    assert bad_quickstart is None, (
        "quickstart.md still contains the install.sh-puts-CLI-on-PATH claim"
    )

    agents = _read("AGENTS.md")
    m = re.search(
        r"##\s+State on disk.*?(?=^##\s+|\Z)",
        agents,
        re.DOTALL | re.MULTILINE,
    )
    if m:
        bare = re.search(r"(?<!\.compass/)\bwork/<task-slug>/", m.group(0))
        assert bare is None, (
            "AGENTS.md State on disk still has the unprefixed work/<task-slug>/"
        )
