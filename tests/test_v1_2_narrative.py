"""Acceptance tests for task v1-2-narrative.

13 scenarios from .compass/work/v1-2-narrative/spec.feature.md, covering
the v1.2.0 surface (architect-lens, architecture/, signals.yml,
quarantine.yml + fitness functions, Trigger-on-intent rule, typed inline
DoD tags) that is missing from the public-facing docs.

Tests are grep/regex assertions over docs at file:line precision. The
F1 coverage rule asserts every v1.2.0 capability named in CLAUDE.md is
documented in AGENTS.md or methodology.md - the structural anti-drift
guard analogous to Task B's `compass --help` parsing.
"""
import re
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _read(rel):
    return (ROOT / rel).read_text()


def _section_after(text, heading_pattern):
    """Return the text of the section starting at heading_pattern up to the
    next heading at the same level (or end of file)."""
    m = re.search(heading_pattern, text, re.MULTILINE)
    if not m:
        return None
    start = m.start()
    # Find the next heading at the same level
    level = re.match(r"^(#+)", text[start:]).group(1)
    next_heading = re.search(rf"^{re.escape(level)} ", text[m.end():], re.MULTILINE)
    if next_heading:
        return text[start:m.end() + next_heading.start()]
    return text[start:]


# ---------------------------------------------------------------------------
# Group A - port-author contract (AGENTS.md + portability.md)
# ---------------------------------------------------------------------------

def test_trc_a1_agents_subagent_list_names_architect_lens():
    """AGENTS.md's adapter mapping table names architect-lens as a subagent."""
    agents = _read("AGENTS.md")
    section = _section_after(agents, r"^##\s+What a runtime adapter must provide")
    assert section, "'What a runtime adapter must provide' section not found"
    assert "architect-lens" in section, (
        "AGENTS.md adapter section does not name architect-lens. "
        "The 10th agent is invisible to a port author."
    )


def test_trc_a2_portability_listings_include_architect_lens():
    """docs/portability.md's three subagent listings all include architect-lens."""
    port = _read("docs/portability.md")
    # All three places that enumerate subagents should mention architect-lens.
    # We just count occurrences of the string; should be at least 3.
    occurrences = port.count("architect-lens")
    assert occurrences >= 3, (
        f"portability.md mentions architect-lens only {occurrences} time(s); "
        "expected at least 3 (adapter-layer code block, mapping table row, "
        "boundary-description paragraph)."
    )


def test_trc_a3_agents_state_on_disk_lists_per_task_architecture_files():
    """AGENTS.md State on disk names architecture-loaded.yml and architecture-notes.md."""
    agents = _read("AGENTS.md")
    section = _section_after(agents, r"^##\s+State on disk")
    assert section, "'State on disk' section not found in AGENTS.md"
    assert "architecture-loaded.yml" in section, (
        "AGENTS.md State on disk does not name architecture-loaded.yml - "
        "a port author would not know to support it."
    )
    assert "architecture-notes.md" in section, (
        "AGENTS.md State on disk does not name architecture-notes.md."
    )


def test_trc_a4_agents_states_trigger_on_intent_rule():
    """AGENTS.md's Frame discussion includes the trigger-on-intent rule."""
    agents = _read("AGENTS.md")
    # The rule must appear in AGENTS.md (per DD-2 Clarify decision: AGENTS.md only).
    # We look for an explicit articulation: "intent" near "Frame" with the rule's substance.
    has_rule = (
        re.search(r"(?i)trigger\s+\S*\s*frame\s+on\s+intent", agents) is not None
        or re.search(r"(?i)intent\s*[^.]*invoke\s+\S*\s*frame", agents) is not None
        or re.search(r"(?i)when\s+the\s+user\s+describes\s+intent", agents) is not None
    )
    assert has_rule, (
        "AGENTS.md does not state the Trigger-Frame-on-intent rule. "
        "The adapter contract is incomplete - a port author following AGENTS.md "
        "would only invoke Frame on literal `/compass:frame`, missing the "
        "intent-recognition trigger."
    )


def test_trc_a5_typed_dod_tags_documented_in_both_agents_and_methodology():
    """Both AGENTS.md and methodology.md document the typed inline DoD-tag mechanism."""
    agents = _read("AGENTS.md")
    method = _read("docs/methodology.md")
    # The typed tags look like `(evidence: EV-<id>)` and
    # `(follow-up: BF-<id>)` - the second renamed with schema 2.0; the
    # checker still reads the v1 spelling from old archives.
    # We require both files to mention the typed-tag form.
    def _has_typed_tag(text):
        return ("evidence: EV-" in text
                and ("follow-up: BF-" in text or "backfill: BF-" in text)) or (
            "(evidence: EV-" in text
            and ("(follow-up: BF-" in text or "(backfill: BF-" in text)
        )

    assert _has_typed_tag(agents), (
        "AGENTS.md does not document the typed inline DoD tags "
        "`(evidence: EV-<id>)` / `(follow-up: BF-<id>)` mechanism."
    )
    assert _has_typed_tag(method), (
        "docs/methodology.md does not document the typed inline DoD tags "
        "mechanism. Per DD-3, this is required in BOTH files."
    )
    # Also assert the dod-evidence-typed rule is mentioned in at least one.
    has_rule_name = (
        "dod-evidence-typed" in agents or "dod-evidence-typed" in method
    )
    assert has_rule_name, (
        "Neither AGENTS.md nor methodology.md names the `dod-evidence-typed` "
        "check that enforces the typed-tag mechanism."
    )


# ---------------------------------------------------------------------------
# Group B - public-facing pitch (README + methodology)
# ---------------------------------------------------------------------------

def test_trc_b1_readme_architect_lens_in_surrounding_prose_not_table():
    """README mentions architect-lens in prose adjacent to the roles table, NOT inside it.

    Per DD-1: the roles table stays about entry-point roles; architect-lens
    has no entry point and lives in surrounding prose.
    """
    readme = _read("README.md")
    section = _section_after(readme, r"^##\s+Roles are full citizens")
    assert section, "'Roles are full citizens' section not found in README"
    # architect-lens must be mentioned somewhere in this section
    assert "architect-lens" in section, (
        "README's roles section does not mention architect-lens."
    )
    # But it must NOT appear in the markdown table rows (rows start with `|`).
    table_rows = [line for line in section.split("\n") if line.strip().startswith("|")]
    table_text = "\n".join(table_rows)
    assert "architect-lens" not in table_text, (
        "architect-lens appears inside the entry-points table. Per DD-1, "
        "the table stays about entry-point roles; architect-lens belongs in "
        "surrounding prose only."
    )
    # And the prose reconciles the role/agent count. Look for a recognisable
    # reconciliation: either mention of "5" and "10" or "lens" and "entry point".
    has_reconciliation = (
        re.search(r"(?i)\bentry[- ]point", section) is not None
    )
    assert has_reconciliation, (
        "README's architect-lens prose does not reconcile the entry-point-role "
        "vs. lens distinction. Without that, readers will be confused by the "
        "5-roles-vs-10-agents mismatch."
    )


def test_trc_b2_readme_tree_lists_architecture_dir():
    """README's "What's in the box" tree includes the architecture/ directory."""
    readme = _read("README.md")
    section = _section_after(readme, r"^##\s+What's in the box")
    assert section, "'What's in the box' section not found in README"
    code = re.search(r"```\n(.*?)\n```", section, re.DOTALL)
    assert code, "No fenced tree block in 'What's in the box'"
    tree = code.group(1)
    assert "architecture/" in tree, (
        "README's tree does not list the architecture/ directory."
    )


def test_trc_b3_methodology_three_layer_split_names_architecture():
    """methodology §9 names architecture/ in the three-layer split discussion."""
    method = _read("docs/methodology.md")
    section = _section_after(method, r"^##\s+9\.\s+The three layers")
    assert section, "§9 'The three layers' not found in methodology"
    assert "architecture/" in section or "`architecture/`" in section, (
        "methodology §9 does not name architecture/ in the three-layer split."
    )


def test_trc_b4_signals_yml_acknowledged_in_public_docs():
    """README or methodology mentions signals.yml with its purpose."""
    readme = _read("README.md")
    method = _read("docs/methodology.md")
    in_either = "signals.yml" in readme or "signals.yml" in method
    assert in_either, (
        "signals.yml is not named in either README.md or docs/methodology.md. "
        "An in-force governance file remains invisible to public readers."
    )


def test_trc_b5_fitness_functions_subsection_in_readme_and_paragraph_in_methodology():
    """README has a subsection heading + methodology has a paragraph naming fitness-functions/intermittent-test."""
    readme = _read("README.md")
    method = _read("docs/methodology.md")

    # README: a subsection heading (## or ###) mentioning the discipline.
    has_readme_heading = bool(re.search(
        r"^#{2,3}\s+.*(fitness\s+function|intermittent[- ]test|quarantine)",
        readme,
        re.MULTILINE | re.IGNORECASE,
    ))
    assert has_readme_heading, (
        "README does not have a subsection heading naming fitness functions / "
        "intermittent-test integrity / quarantine. Per DD-4, the v1.1.0 feature "
        "needs heading-level presence."
    )

    # The README subsection should mention both ideas.
    assert re.search(r"(?i)fitness\s+function", readme), (
        "README does not name fitness functions."
    )
    assert re.search(r"(?i)quarantine", readme), (
        "README does not name the quarantine / intermittent-test discipline."
    )

    # methodology: paragraph in §4 (or elsewhere) mentioning both ideas.
    assert re.search(r"(?i)fitness\s+function", method), (
        "docs/methodology.md does not name fitness functions."
    )
    assert re.search(r"(?i)quarantine", method), (
        "docs/methodology.md does not name quarantine / intermittent-test."
    )


# ---------------------------------------------------------------------------
# Group C - roles-guide architect-lens parity
# ---------------------------------------------------------------------------

def test_trc_c1_roles_guide_has_architect_lens_section_with_parity():
    """docs/roles-guide.md has an architect-lens section mirroring the other lenses."""
    guide = _read("docs/roles-guide.md")
    # Must have a section heading containing "architect" (the lens name).
    section_match = re.search(
        r"^(#{2,4})\s+.*architect[^\n]*$",
        guide,
        re.MULTILINE | re.IGNORECASE,
    )
    assert section_match, (
        "roles-guide.md does not have a section heading for architect-lens. "
        "Per DD-4 (Clarify Q4 ratification), this lens deserves parity with "
        "the other lenses, which means a named section."
    )
    # Extract the section content.
    heading_level = section_match.group(1)
    pattern = rf"^{re.escape(heading_level)}\s+[^\n]*[Aa]rchitect"
    section = _section_after(guide, pattern)
    assert section, "Could not extract architect-lens section content"

    # Parity assertions: the section names what it reads, what it writes,
    # where it gates, and includes some concrete content.
    must_have_patterns = {
        "names architecture/ artifacts": re.compile(
            r"architecture/|system-context|relations\.md|ownership\.md|decisions/|ADR",
            re.IGNORECASE,
        ),
        "names what the lens writes": re.compile(r"architecture-notes\.md"),
        "names where it gates / who applies it": re.compile(
            r"spec-author|planner|Specify|Plan",
            re.IGNORECASE,
        ),
    }
    missing = [
        name for name, pat in must_have_patterns.items()
        if not pat.search(section)
    ]
    assert not missing, (
        f"roles-guide.md's architect-lens section is missing: {missing}. "
        f"Per DD-4, the section must have parity with the other lenses."
    )

    # Parity by length - the architect-lens section should be at least
    # comparable in length to the other lens sections. A footnote does not
    # count as parity.
    word_count = len(section.split())
    assert word_count >= 100, (
        f"roles-guide.md's architect-lens section is only {word_count} words. "
        f"Per DD-4, parity with the other lenses (which run several hundred "
        f"words each) requires real substance, not a footnote."
    )


# ---------------------------------------------------------------------------
# Group D - governance index
# ---------------------------------------------------------------------------

def test_trc_d1_governance_readme_files_table_lists_signals_and_quarantine():
    """governance/README.md's files table includes signals.yml and quarantine.yml."""
    gov_readme = _read("governance/README.md")
    # Both files must be named in governance/README.md.
    assert "signals.yml" in gov_readme, (
        "governance/README.md does not name signals.yml - the index of "
        "governance/ files is incomplete."
    )
    assert "quarantine.yml" in gov_readme, (
        "governance/README.md does not name quarantine.yml."
    )


# ---------------------------------------------------------------------------
# Coverage rule - F1
# ---------------------------------------------------------------------------

def test_trc_f1_no_v1_2_capability_in_claude_md_omitted_from_agents_or_methodology():
    """Every v1.2.0 capability mentioned in CLAUDE.md is named in AGENTS.md or methodology."""
    agents = _read("AGENTS.md")
    method = _read("docs/methodology.md")
    combined = agents + "\n" + method

    capabilities = {
        "architect-lens": r"architect-lens",
        "architecture/ directory": r"`?architecture/`?",
        "architecture-loaded.yml": r"architecture-loaded\.yml",
        "architecture-notes.md": r"architecture-notes\.md",
        "Trigger Frame on intent": r"(?i)(?:trigger\s+\S*\s*frame\s+on\s+intent|intent\s*[^.]*invoke\s+\S*\s*frame|when\s+the\s+user\s+describes\s+intent)",
        "typed inline DoD tags": r"(?:\(evidence:\s+EV-|\(backfill:\s+BF-|evidence:\s+EV-\w|backfill:\s+BF-\w)",
        "signals.yml": r"signals\.yml",
        "compass rework-scan": r"compass rework-scan",
        "flow/rework-<date>.md or rework-<date>": r"rework-\<?date\>?",
    }

    missing = [
        name for name, pattern in capabilities.items()
        if not re.search(pattern, combined)
    ]
    assert not missing, (
        f"v1.2.0 capabilities named in CLAUDE.md but missing from BOTH "
        f"AGENTS.md and methodology.md: {missing}. A port author following "
        f"the runtime-neutral docs would be silently missing them."
    )
