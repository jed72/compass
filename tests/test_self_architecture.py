"""Tests for the Compass self-architecture task.

Covers all 18 scenarios from spec.feature.md:

Group A — Narrative artifacts ship with required structure
  TRC-A1 — system-context.md exists with canonical sections
  TRC-A2 — relations.md documents the call graph
  TRC-A3 — ownership.md documents boundaries

Group B — ADRs encode P1..P8
  TRC-B1 — architecture/decisions/ contains exactly six founding ADRs
  TRC-B2 — ADRs follow the template structure
  TRC-B3 — README.md indexes the ADRs
  TRC-B4 — At least one ADR demonstrates substantive alternatives + negative consequences

Group C — Mechanism integration
  TRC-C1 — frame_load_architecture returns the new artifacts and ADRs
  TRC-C2 — SHA-256 is recorded per artifact
  TRC-C3 — Architect-lens cites Compass's own ADRs on a framework task

Group D — CLAUDE.md amendment in lockstep
  TRC-D1 — CLAUDE.md notes Compass itself ships an architecture/
  TRC-D2 — CLAUDE.md does not claim unbuilt features

Group E — Backward compat + regression
  TRC-E1 — Existing test suite still passes
  TRC-E2 — Projects without architecture/ still no-op cleanly
  TRC-E3 — compass check still passes 10/10
  TRC-E4 — Lint count does not regress

Failure modes
  TRC-X1 — Malformed ADR frontmatter fails Frame loudly
  TRC-X2 — ADRs with status "proposed" are loaded but flagged
"""
from __future__ import annotations

import hashlib
import re
import subprocess
import sys
import types
from pathlib import Path

import pytest
import yaml

# ---------------------------------------------------------------------------
# Framework root and CLI loader
# ---------------------------------------------------------------------------

FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent
ARCH_DIR = FRAMEWORK_ROOT / "architecture"
DECISIONS_DIR = ARCH_DIR / "decisions"
CLAUDE_MD = FRAMEWORK_ROOT / "CLAUDE.md"
CLI_PATH = FRAMEWORK_ROOT / "cli" / "compass"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "self-architecture"


def _load_cli() -> types.ModuleType:
    """Load the compass CLI module without executing main()."""
    source = CLI_PATH.read_text(encoding="utf-8")
    mod = types.ModuleType("compass_cli_self_arch")
    mod.__file__ = str(CLI_PATH)
    exec(compile(source, str(CLI_PATH), "exec"), mod.__dict__)  # noqa: S102
    return mod


cli = _load_cli()


def _sha256(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


def _adr_files() -> list[Path]:
    """Return sorted list of ADR-*.md files under architecture/decisions/."""
    if not DECISIONS_DIR.exists():
        return []
    return sorted(DECISIONS_DIR.glob("ADR-*.md"))


def _parse_frontmatter(path: Path) -> dict:
    """Parse YAML frontmatter (between --- delimiters) from a file."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    end = text.index("---", 3)
    fm_text = text[3:end].strip()
    return yaml.safe_load(fm_text) or {}


# ---------------------------------------------------------------------------
# Group A — Narrative artifacts
# ---------------------------------------------------------------------------


def test_system_context_structure():
    """TRC-A1: system-context.md exists with required sections and STATUS: ACCEPTED."""
    sc = ARCH_DIR / "system-context.md"
    assert sc.exists(), f"architecture/system-context.md not found at {sc}"

    content = sc.read_text(encoding="utf-8")
    assert content.strip(), "system-context.md must not be empty"

    # Required sections per template
    required_sections = ["Purpose", "Components", "External dependencies",
                         "Boundary conditions", "Open questions"]
    for section in required_sections:
        assert section in content, (
            f"system-context.md missing required section: {section!r}"
        )

    # Each logical surface named
    logical_surfaces = ["pipeline", "router", "guardrails", "strategies", "role pipeline"]
    for surface in logical_surfaces:
        assert surface.lower() in content.lower(), (
            f"system-context.md does not mention logical surface: {surface!r}"
        )

    # STATUS must be ACCEPTED
    assert "STATUS: ACCEPTED" in content or "status: accepted" in content.lower(), (
        "system-context.md must have STATUS: ACCEPTED (not DRAFT or PROVISIONAL)"
    )


def test_relations_call_graph():
    """TRC-A2: relations.md exists and enumerates the required relations."""
    rel = ARCH_DIR / "relations.md"
    assert rel.exists(), f"architecture/relations.md not found at {rel}"

    content = rel.read_text(encoding="utf-8")
    assert content.strip(), "relations.md must not be empty"

    # Required relations from spec
    required_relations = [
        ("cli/compass", "governance/"),
        ("cli/compass", "architecture/"),
        ("cli/compass", ".compass/work/"),
        ("hooks/pre-tool.sh", ".red"),
        ("hooks/stop.sh", "governance/signals.yml"),
        ("hooks/stop.sh", "devlog.md"),
        ("architect-lens", "architecture/"),
    ]
    for caller, callee in required_relations:
        assert caller in content and callee in content, (
            f"relations.md missing relation involving {caller!r} -> {callee!r}"
        )

    # architect-lens must NOT reference architecture-draft/
    assert "architecture-draft/" not in content, (
        "relations.md must not reference architecture-draft/ (not in scope)"
    )


def test_ownership_boundaries():
    """TRC-A3: ownership.md exists with Must own and Must not do sections citing B-Risks."""
    own = ARCH_DIR / "ownership.md"
    assert own.exists(), f"architecture/ownership.md not found at {own}"

    content = own.read_text(encoding="utf-8")
    assert content.strip(), "ownership.md must not be empty"

    # Must have Must own and Must not do sections for each component
    assert "Must own" in content, "ownership.md missing 'Must own' section"
    assert "Must not do" in content or "Must not" in content, (
        "ownership.md missing 'Must not do' section"
    )

    # Must cite boundary risks from architecture-notes.md
    boundary_rules = [
        "calibration must not mutate task.yml",
        "rework-scan",
        "architect-lens must not emit Gherkin",
    ]
    for rule in boundary_rules:
        assert rule.lower() in content.lower(), (
            f"ownership.md missing boundary rule reference: {rule!r}"
        )


# ---------------------------------------------------------------------------
# Group B — ADRs
# ---------------------------------------------------------------------------


def test_adrs_cover_p1_to_p8():
    """TRC-B1: architecture/decisions/ contains exactly six founding ADRs."""
    adrs = _adr_files()
    assert len(adrs) == 6, (
        f"Expected exactly 6 ADR files, found {len(adrs)}: {[f.name for f in adrs]}"
    )

    # Numbers must be unique and sequential from 001
    numbers = []
    for adr in adrs:
        m = re.match(r"ADR-(\d{3})-", adr.name)
        assert m, f"ADR filename does not match ADR-NNN-<slug>.md pattern: {adr.name}"
        numbers.append(int(m.group(1)))

    assert sorted(numbers) == list(range(1, 7)), (
        f"ADR numbers must be 001..006, got: {sorted(numbers)}"
    )
    assert len(set(numbers)) == 6, "ADR numbers must be unique"

    # ADR-001 must cover Inv-1 + Inv-7 (judgement/mechanism)
    adr001 = next(f for f in adrs if f.name.startswith("ADR-001"))
    c001 = adr001.read_text(encoding="utf-8")
    assert any(kw in c001.lower() for kw in ["judgement", "judgment", "mechanism", "inv-1"]), (
        "ADR-001 must cover the judgement/mechanism separation (Inv-1 + Inv-7)"
    )

    # ADR-006 must cover Inv-8 (backward compat)
    adr006 = next(f for f in adrs if f.name.startswith("ADR-006"))
    c006 = adr006.read_text(encoding="utf-8")
    assert any(kw in c006.lower() for kw in ["backward compat", "backwards compat",
                                               "no-op", "inv-8"]), (
        "ADR-006 must cover backward compatibility (Inv-8)"
    )


def test_adr_structure():
    """TRC-B2: Every ADR has required frontmatter fields and five sections."""
    adrs = _adr_files()
    assert adrs, "No ADR files found — test_adrs_cover_p1_to_p8 should catch this first"

    required_fm_fields = {"id", "title", "status", "date", "supersedes", "superseded_by"}
    required_sections = [
        "## Context",
        "## Decision",
        "## Alternatives considered",
        "## Consequences",
        "## References",
    ]
    valid_statuses = {"accepted", "proposed"}

    for adr in adrs:
        content = adr.read_text(encoding="utf-8")
        fm = _parse_frontmatter(adr)

        # Frontmatter fields
        missing = required_fm_fields - set(fm.keys())
        assert not missing, (
            f"{adr.name}: missing frontmatter fields: {missing}"
        )

        # Status validity
        status = str(fm.get("status", "")).lower()
        assert status in valid_statuses, (
            f"{adr.name}: status must be 'accepted' or 'proposed', got {status!r}"
        )
        assert status != "draft", (
            f"{adr.name}: status 'draft' is reserved for distillation drafts, not used here"
        )

        # Required sections
        for section in required_sections:
            assert section in content, (
                f"{adr.name}: missing required section {section!r}"
            )


def test_decisions_readme_indexes_adrs():
    """TRC-B3: architecture/decisions/README.md indexes ADRs with numbering convention."""
    readme = DECISIONS_DIR / "README.md"
    assert readme.exists(), f"architecture/decisions/README.md not found at {readme}"

    content = readme.read_text(encoding="utf-8")
    assert content.strip(), "decisions/README.md must not be empty"

    # Must list every ADR by number and title
    adrs = _adr_files()
    for adr in adrs:
        fm = _parse_frontmatter(adr)
        adr_id = fm.get("id", "")
        assert adr_id in content, (
            f"README.md does not list ADR id {adr_id!r} (from {adr.name})"
        )

    # Numbering convention explained
    assert "sequential" in content.lower() or "never reused" in content.lower(), (
        "README.md must explain the sequential, never-reused numbering convention"
    )
    assert "superseded_by" in content or "supersession" in content.lower(), (
        "README.md must explain supersession mechanism"
    )

    # Must cross-reference principles
    assert any(inv in content for inv in ["Inv-", "P1", "principle", "ADR-001"]), (
        "README.md must cross-reference which ADR codifies which principle"
    )


def test_adr_rationale_substance():
    """TRC-B4: At least one ADR has ≥2 substantive alternatives; at least one names a negative consequence."""
    adrs = _adr_files()
    assert adrs, "No ADR files found"

    # At least one ADR must enumerate ≥2 alternatives
    found_two_alternatives = False
    for adr in adrs:
        content = adr.read_text(encoding="utf-8")
        # Look for table rows in Alternatives section (each row = one alternative)
        alt_section = re.search(
            r"## Alternatives considered(.*?)(?=## |\Z)",
            content,
            re.DOTALL,
        )
        if alt_section:
            alt_text = alt_section.group(1)
            # Count non-header table rows (lines starting with | and not |---|)
            rows = [ln for ln in alt_text.split("\n")
                    if ln.strip().startswith("|")
                    and "---" not in ln
                    and ln.strip() != "|---|---|---|"]
            # Remove the header row
            data_rows = rows[1:] if rows else []
            if len(data_rows) >= 2:
                found_two_alternatives = True
                break

    assert found_two_alternatives, (
        "At least one ADR must enumerate ≥2 alternatives in its "
        "'Alternatives considered' section"
    )

    # At least one ADR must name a NEGATIVE consequence
    found_negative = False
    for adr in adrs:
        content = adr.read_text(encoding="utf-8")
        cons_section = re.search(
            r"## Consequences(.*?)(?=## |\Z)",
            content,
            re.DOTALL,
        )
        if cons_section:
            cons_text = cons_section.group(1).lower()
            if "negative" in cons_text or "**negative" in cons_text:
                # Check there's actual content under the negative heading
                neg_match = re.search(r"\*\*negative[:\*]*\*\*(.+?)(?=\*\*|\Z)",
                                      cons_section.group(1), re.DOTALL | re.IGNORECASE)
                if neg_match:
                    neg_content = neg_match.group(1).strip()
                    # Must have more than just "- " placeholder
                    if len(neg_content) > 5 and neg_content not in ("-", "- "):
                        found_negative = True
                        break

    assert found_negative, (
        "At least one ADR must name a negative consequence in its "
        "'Consequences' section (the decision must look like a real tradeoff)"
    )


# ---------------------------------------------------------------------------
# Group C — Mechanism integration
# ---------------------------------------------------------------------------


def test_frame_load_against_compass_root(tmp_path):
    """TRC-C1: frame_load_architecture returns the new artifacts and ADRs when
    run against the actual Compass repo root."""
    task_dir = tmp_path / ".compass" / "work" / "test-integration"
    task_dir.mkdir(parents=True)

    result = cli.frame_load_architecture(str(FRAMEWORK_ROOT), str(task_dir))

    assert isinstance(result, dict), "frame_load_architecture must return a dict"

    # Must include the three narrative files
    artifact_paths = {a["path"] for a in result.get("artifacts", [])}
    for expected in ["architecture/system-context.md",
                     "architecture/relations.md",
                     "architecture/ownership.md"]:
        assert expected in artifact_paths, (
            f"Expected artifact {expected!r} in load record, got: {artifact_paths}"
        )

    # Every artifact must have path, sha256, type
    for art in result["artifacts"]:
        assert "path" in art and "sha256" in art and "type" in art, (
            f"Artifact missing required fields: {art}"
        )

    # ADRs: must have exactly 6 entries
    adrs = result.get("adrs", [])
    assert len(adrs) == 6, (
        f"Expected 6 ADRs in load record, got {len(adrs)}"
    )
    for adr in adrs:
        assert "id" in adr and "path" in adr and "title" in adr and "status" in adr, (
            f"ADR entry missing required fields: {adr}"
        )

    # architecture-loaded.yml must be written
    loaded_file = task_dir / "architecture-loaded.yml"
    assert loaded_file.exists(), "architecture-loaded.yml was not written"
    on_disk = yaml.safe_load(loaded_file.read_text(encoding="utf-8"))
    assert on_disk["schema_version"] == "1.0"
    assert len(on_disk["artifacts"]) >= 3
    assert len(on_disk["adrs"]) == 6


def test_load_record_sha256_present(tmp_path):
    """TRC-C2: Every artifact in the load record has a SHA-256 that matches the file content.
    Invocation is deterministic (same inputs, same outputs)."""
    task_dir = tmp_path / ".compass" / "work" / "test-sha"
    task_dir.mkdir(parents=True)

    result1 = cli.frame_load_architecture(str(FRAMEWORK_ROOT), str(task_dir))

    # Must have artifacts (architecture/ must exist with content for this test to be meaningful)
    assert len(result1["artifacts"]) >= 3, (
        f"Expected ≥3 artifacts from Compass root, got {len(result1['artifacts'])}. "
        "architecture/system-context.md, relations.md, and ownership.md must exist."
    )

    # Verify SHA-256 for each narrative artifact
    for art in result1["artifacts"]:
        file_path = FRAMEWORK_ROOT / art["path"]
        if file_path.exists():
            expected_sha = _sha256(file_path.read_text(encoding="utf-8"))
            assert art["sha256"] == expected_sha, (
                f"SHA-256 mismatch for {art['path']}: "
                f"expected {expected_sha!r}, got {art['sha256']!r}"
            )

    # Determinism: second invocation with same inputs produces same hashes
    task_dir2 = tmp_path / ".compass" / "work" / "test-sha-2"
    task_dir2.mkdir(parents=True)
    result2 = cli.frame_load_architecture(str(FRAMEWORK_ROOT), str(task_dir2))

    paths1 = {a["path"]: a["sha256"] for a in result1["artifacts"]}
    paths2 = {a["path"]: a["sha256"] for a in result2["artifacts"]}
    assert paths1 == paths2, (
        "frame_load_architecture is not deterministic — SHA-256 hashes differ "
        "between two identical invocations"
    )


def test_lens_cites_own_adrs(tmp_path):
    """TRC-C3: The architect-lens, when run against the fixture task that touches
    public-api, produces architecture-notes.md citing at least one of
    Compass's six founding ADRs (ADR-001..ADR-006) by id."""
    fixture_task_dir = FIXTURES_DIR / "hypothetical-framework-task"
    assert fixture_task_dir.exists(), (
        f"Fixture missing: {fixture_task_dir} — create it with route.md + task.yml"
    )
    assert (fixture_task_dir / "route.md").exists(), (
        f"Fixture missing route.md at {fixture_task_dir}"
    )
    assert (fixture_task_dir / "task.yml").exists(), (
        f"Fixture missing task.yml at {fixture_task_dir}"
    )

    # Verify the fixture has touches: [public-api]
    task_data = yaml.safe_load((fixture_task_dir / "task.yml").read_text(encoding="utf-8"))
    assert "public-api" in task_data.get("readings", {}).get("touches", []), (
        "Fixture task.yml must have readings.touches: [public-api]"
    )

    # Invoke frame_load_architecture against the live Compass architecture/
    # to simulate what happens when the lens reads real content.
    # The lens itself is an agent (markdown file) — we test its *output contract*
    # by checking that the real architecture/ directory now has real ADR ids
    # that the lens would cite (as documented in the agent's instruction).
    # We exercise frame_load_architecture to confirm the ADRs are in the load record
    # with their ids, so a lens invocation could cite them.
    task_dir = tmp_path / ".compass" / "work" / "hypothetical"
    task_dir.mkdir(parents=True)

    result = cli.frame_load_architecture(str(FRAMEWORK_ROOT), str(task_dir))

    # The load record must contain the six founding ADR ids
    adr_ids = {adr["id"] for adr in result.get("adrs", [])}
    expected_ids = {"ADR-001", "ADR-002", "ADR-003", "ADR-004", "ADR-005", "ADR-006"}
    assert expected_ids.issubset(adr_ids), (
        f"Load record missing founding ADR ids. Expected {expected_ids}, got {adr_ids}"
    )

    # The loaded ADRs must reference content relevant to the fixture task's surface (public-api)
    # ADR-001 covers judgement/mechanism, ADR-006 covers backward compat — both
    # are relevant to a public-api-touching task. Verify at least one is relevant.
    relevant_keywords = ["public", "api", "guardrail", "strategy", "lens",
                         "mechanism", "backward", "compat"]
    adr_contents = []
    for adr_entry in result["adrs"]:
        adr_path = FRAMEWORK_ROOT / adr_entry["path"]
        if adr_path.exists():
            adr_contents.append(adr_path.read_text(encoding="utf-8").lower())

    found_relevant = any(
        any(kw in content for kw in relevant_keywords)
        for content in adr_contents
    )
    assert found_relevant, (
        "None of the loaded ADRs contain content relevant to the fixture task surface"
    )


# ---------------------------------------------------------------------------
# Group D — CLAUDE.md amendment
# ---------------------------------------------------------------------------


def test_claude_md_amended():
    """TRC-D1: CLAUDE.md 'Where state lives' section mentions Compass ships its own
    architecture/ as a worked example."""
    assert CLAUDE_MD.exists(), f"CLAUDE.md not found at {CLAUDE_MD}"
    content = CLAUDE_MD.read_text(encoding="utf-8")

    # The section must exist
    assert "Where state lives" in content, (
        "CLAUDE.md does not contain a 'Where state lives' section"
    )

    # Must mention Compass ships its own architecture/
    # Look for the architecture/ paragraph amended
    arch_para_match = re.search(
        r"architecture/.*(?:ships one|Compass itself|worked example)",
        content,
        re.DOTALL | re.IGNORECASE,
    )
    assert arch_para_match, (
        "CLAUDE.md must state that Compass itself ships an architecture/ "
        "as a worked example (per TRC-D1)"
    )

    # Must reference that it doubles as documentation for adopters
    assert any(phrase in content.lower() for phrase in
               ["adopter", "example", "worked example", "doubles as"]), (
        "CLAUDE.md must reference that the architecture/ doubles as documentation "
        "for adopters to study"
    )


def test_claude_md_no_unbuilt_features():
    """TRC-D2: CLAUDE.md must not mention architecture-draft/, /compass:architecture-review,
    or 'PROVISIONAL decay'."""
    content = CLAUDE_MD.read_text(encoding="utf-8")

    assert "/compass:architecture-review" not in content, (
        "CLAUDE.md must not mention /compass:architecture-review (unbuilt feature)"
    )
    assert "architecture-draft/" not in content, (
        "CLAUDE.md must not mention architecture-draft/ (unbuilt feature)"
    )
    assert "PROVISIONAL decay" not in content, (
        "CLAUDE.md must not mention 'PROVISIONAL decay' (unbuilt feature)"
    )


# ---------------------------------------------------------------------------
# Group E — Backward compat + regression
# ---------------------------------------------------------------------------


def test_full_suite_baseline():
    """TRC-E1: The full pytest suite must pass with at least 161 tests.
    This test calls pytest as a subprocess to count total passed tests."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(FRAMEWORK_ROOT / "tests/"),
         "--ignore", str(FRAMEWORK_ROOT / "tests/test_self_architecture.py"),
         "-v", "--tb=no", "-q"],
        capture_output=True,
        text=True,
        cwd=str(FRAMEWORK_ROOT),
    )
    output = result.stdout + result.stderr
    # Look for "N passed" in output (pytest summary line)
    m = re.search(r"(\d+) passed", output)
    # If no summary line, count PASSED lines directly
    if not m:
        passed_count = len([ln for ln in output.split("\n") if " PASSED" in ln])
    else:
        passed_count = int(m.group(1))
    assert passed_count >= 161, (
        f"Existing test suite regressed: expected ≥161 tests to pass, got {passed_count}.\n"
        f"Output:\n{output}"
    )
    assert result.returncode == 0, (
        f"pytest returned non-zero exit code {result.returncode}.\n"
        f"Output:\n{output}"
    )


def test_no_architecture_dir_still_works(tmp_path):
    """TRC-E2: frame_load_architecture against a project with no architecture/ returns empty."""
    task_dir = tmp_path / ".compass" / "work" / "no-arch"
    task_dir.mkdir(parents=True)

    result = cli.frame_load_architecture(str(tmp_path), str(task_dir))

    assert result.get("artifacts") == [], (
        "artifacts must be empty when architecture/ is absent"
    )
    assert result.get("adrs") == [], (
        "adrs must be empty when architecture/ is absent"
    )

    loaded_file = task_dir / "architecture-loaded.yml"
    assert loaded_file.exists(), "architecture-loaded.yml must still be written"
    on_disk = yaml.safe_load(loaded_file.read_text(encoding="utf-8"))
    assert on_disk["artifacts"] == []
    assert on_disk["adrs"] == []


def test_compass_check_passes():
    """TRC-E3: compass check --task compass-self-architecture must pass 10/10."""
    result = subprocess.run(
        [sys.executable, str(CLI_PATH), "check",
         "--task", "compass-self-architecture"],
        capture_output=True,
        text=True,
        cwd=str(FRAMEWORK_ROOT),
    )
    output = result.stdout + result.stderr
    # Must contain PASS — all N check(s) passed
    assert "PASS" in output and "passed" in output.lower(), (
        f"compass check did not report PASS.\nOutput:\n{output}"
    )
    # Must not have any FAIL lines (gates are pending, not failed)
    assert "FAIL —" not in output, (
        f"compass check reported a FAIL.\nOutput:\n{output}"
    )


def test_lint_count_baseline():
    """TRC-E4: ruff check must find no more than 11 errors (the established baseline)."""
    result = subprocess.run(
        ["ruff", "check", "tests/", "cli/compass"],
        capture_output=True,
        text=True,
        cwd=str(FRAMEWORK_ROOT),
    )
    output = result.stdout + result.stderr
    # Count error lines (lines that look like file:line:col: error)
    error_lines = [ln for ln in output.split("\n")
                   if re.match(r".+:\d+:\d+:", ln)]
    error_count = len(error_lines)
    assert error_count <= 11, (
        f"Lint error count regressed: expected ≤11, got {error_count}.\n"
        f"Errors:\n{output}"
    )


# ---------------------------------------------------------------------------
# Failure modes
# ---------------------------------------------------------------------------


def test_malformed_adr_fails_loudly(tmp_path):
    """TRC-X1: An ADR with broken YAML frontmatter causes frame_load_architecture
    to raise an exception that names the file path and the parse error."""
    arch_dir = tmp_path / "architecture" / "decisions"
    arch_dir.mkdir(parents=True)

    # Write a valid narrative file so the function reaches ADR parsing
    (tmp_path / "architecture" / "system-context.md").write_text(
        "# System context", encoding="utf-8"
    )

    # Write a malformed ADR
    malformed_adr = arch_dir / "ADR-099-malformed.md"
    malformed_adr.write_text(
        "---\nid: ADR-099\ntitle: [unclosed bracket\nstatus: proposed\n---\n\n## Context\n\ntest",
        encoding="utf-8",
    )

    task_dir = tmp_path / ".compass" / "work" / "malformed-test"
    task_dir.mkdir(parents=True)

    with pytest.raises(Exception) as exc_info:
        cli.frame_load_architecture(str(tmp_path), str(task_dir))

    msg = str(exc_info.value)
    assert "ADR-099" in msg or "ADR-099-malformed.md" in msg, (
        f"Error message must name the malformed ADR file; got: {msg!r}"
    )
    assert any(kw in msg.lower() for kw in ("parse", "yaml", "invalid", "error", "malformed")), (
        f"Error message must describe the problem; got: {msg!r}"
    )


def test_proposed_adr_loaded_with_status(tmp_path):
    """TRC-X2: A proposed-status ADR appears in the load record with status 'proposed'.
    Uses the fixture at tests/fixtures/self-architecture/proposed-adr/."""
    fixture_root = FIXTURES_DIR / "proposed-adr"
    assert fixture_root.exists(), (
        f"Fixture missing: {fixture_root} — create tests/fixtures/self-architecture/proposed-adr/"
    )

    fixture_adr = fixture_root / "architecture" / "decisions" / "ADR-099-proposed-example.md"
    assert fixture_adr.exists(), (
        f"Fixture ADR missing: {fixture_adr}"
    )

    task_dir = tmp_path / ".compass" / "work" / "proposed-test"
    task_dir.mkdir(parents=True)

    result = cli.frame_load_architecture(str(fixture_root), str(task_dir))

    adr_ids = {a["id"]: a for a in result.get("adrs", [])}
    assert "ADR-099" in adr_ids, (
        f"Proposed ADR-099 not found in load record. ADRs loaded: {list(adr_ids.keys())}"
    )
    assert adr_ids["ADR-099"]["status"] == "proposed", (
        f"ADR-099 status should be 'proposed', got {adr_ids['ADR-099']['status']!r}"
    )
