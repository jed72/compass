"""The v2 vocabulary freeze, enforced.

`governance/terminology.yml` is the frozen v2 vocabulary: every term with its
exact meaning, the banned v1 words, and the scan config naming which
user-facing surfaces are checked. This file is the mechanical half of that
freeze - the same shape as `tests/test_house_style.py`, which enforces the
repository's writing style: these are invariants of this repository's own
prose, never a check an adopting project runs.

Three groups of checks:

1. Well-formedness. The vocabulary file exists, parses, and every entry
   carries the fields that make it usable: a meaning per term, a replacement
   and a context per ban, and the three scan lists.
2. Scanner precision, proven by fixtures. Each ban is enforced as one or more
   tuned regexes, not a bare word. `tests/fixtures/terminology/` holds two
   files: one planting every banned usage (each must be flagged), one reusing
   the same words innocently (none may be flagged). The context notes in the
   vocabulary file are the intent; the patterns here are the executable form;
   the fixtures prove the two agree. Pattern tuning lives here, beside the
   fixtures, and accumulates as rename slices clean their surfaces.
3. The ratchet. A surface still listed in `pending_surfaces` may carry banned
   terms without failing, so CI stays green while the rename is in flight. A
   surface absent from that list must be clean, forever. The pending list may
   only ever shrink: the committed baseline below is the high-water mark, and
   a rename slice's definition of done includes removing its surface from
   both the vocabulary file and that baseline in the same diff.

Docstrings cite the acceptance criteria they satisfy by TRC id; the criteria
live in this issue's archived spec, indexed in its `task.yml` (machine state,
exempt from the vocabulary scan during the transition).
"""
from __future__ import annotations

import ast
import re
from functools import lru_cache
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).parent.parent
TERMINOLOGY_PATH = REPO_ROOT / "governance" / "terminology.yml"
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "terminology"
FIXTURE_BANNED = FIXTURE_DIR / "banned_usage.md"
FIXTURE_INNOCENT = FIXTURE_DIR / "innocent_usage.md"

# Directory noise never worth scanning, whatever the surface list says.
PRUNE_DIRS = {
    ".git", "__pycache__", ".ruff_cache", ".pytest_cache", ".mypy_cache",
    ".idea", ".vscode", "node_modules", "dist", "build",
}

MAX_REPORTED = 40

# ---------------------------------------------------------------------------
# The tuned ban patterns - the executable form of the `banned:` context notes.
#
# Keys are the exact `term` strings in governance/terminology.yml;
# test_every_ban_is_bound_to_a_pattern holds the two files in one-to-one
# correspondence. Each ban is pattern-plus-context, never a bare word: the
# fixture pair under tests/fixtures/terminology/ is the proof that each
# pattern catches the banned sense and tolerates the ordinary one.
# ---------------------------------------------------------------------------
BAN_PATTERNS: dict[str, list[re.Pattern]] = {
    # The v1 triage phase and its agent, as names and command. Ordinary
    # lowercase "frame" (the verb) stays legal.
    "Frame / the Needle": [
        re.compile(r"/compass:frame\b"),
        re.compile(r"\bFrame\s+phase\b"),
        re.compile(r"\bthe\s+Needle\b"),
        re.compile(r"\bFrame\s*(?:→|->)"),
        re.compile(r"(?:→|->)\s*Frame\b"),
        re.compile(r"^#+\s+Frame\b"),
        # Tuned at the skills-prose review: the capitalised stage name
        # after a preposition ("during Frame,") is stage-name usage the
        # suffix forms above miss; lowercase "frame the problem" stays
        # legal.
        re.compile(r"\b(?:during|at|before|after|since|until)\s+Frame\b"),
    ],
    # The four-dimension judgement. The plural is the v1 term of art;
    # singular "reading" (the ordinary gerund) stays legal.
    "reading / readings": [
        re.compile(r"\breadings\b", re.IGNORECASE),
        re.compile(r"\bdimension\s+reading\b", re.IGNORECASE),
    ],
    # The computed process shape. Ordinary "route" (a path somewhere)
    # stays legal; the file, the command, and the qualified process
    # senses do not.
    "route": [
        re.compile(r"\broute\.md\b"),
        re.compile(r"\broute\s+evaluate\b"),
        re.compile(r"\broutes?/"),
        re.compile(
            r"\b(?:computed|reference|delivery|solo|swarm|"
            r"Express|Standard|Expedition|Hotfix|Spike)\s+routes?\b"
        ),
        # Tuned at the skills-prose review: "compute the route" is the
        # process-noun sense (the thing computed is the delivery
        # approach); "computed a route home" stays legal.
        re.compile(r"\bcomputes?\s+the\s+route\b"),
    ],
    # The v1 name for a quick fix. Capitalised only: "express delivery"
    # stays legal.
    "Express": [
        re.compile(r"\bExpress\b"),
    ],
    # The v1 name for an initiative-scale delivery. Capitalised only.
    "Expedition": [
        re.compile(r"\bExpedition\b"),
    ],
    # The v1 phase names, as names: command, "X phase", pipeline arrows,
    # headings. Ordinary lowercase verbs ("specify the format", "landing
    # gear") stay legal.
    "Specify / Clarify / Distribute / Land": [
        re.compile(r"/compass:(?:specify|clarify|distribute|land)\b"),
        re.compile(r"\b(?:Specify|Clarify|Distribute|Land)\s+phase\b"),
        re.compile(r"(?:→|->)\s*(?:Specify|Clarify|Distribute|Land)\b"),
        re.compile(r"\b(?:Specify|Clarify|Distribute|Land)\s*(?:→|->)"),
        re.compile(r"^#+\s+(?:Specify|Clarify|Distribute|Land)\b"),
        # Tuned at the skills-prose review: the capitalised stage name
        # after a preposition or conjunction ("at Land", "and Land",
        # "during Specify") is stage-name usage the suffix forms miss;
        # lowercase ordinary verbs ("planes land") stay legal.
        re.compile(r"\b(?:during|at|before|after|since|until|and|into)\s+"
                   r"(?:Specify|Clarify|Distribute|Land)\b"),
    ],
    # The role-perspective concept, in any casing. Tuned at the
    # skills-prose slice: a hyphen-preceded "lens" is an agent identifier
    # (product-lens, architect-lens, marketing-lens) - machine vocabulary
    # that keeps its spelling until an agent-rename decision - and is no
    # longer flagged. The concept word alone still is.
    "lens": [
        re.compile(r"(?<!-)\blens(?:es)?\b", re.IGNORECASE),
    ],
    # The v1 risk dimension, prose or key form.
    "blast radius": [
        re.compile(r"\bblast[\s_-]radius\b", re.IGNORECASE),
    ],
    # The v1 familiarity dimension.
    "terrain": [
        re.compile(r"\bterrain\b", re.IGNORECASE),
    ],
    # The v1 size dimension. "order(s) of magnitude" is ordinary English
    # and stays legal.
    "magnitude": [
        re.compile(r"(?<!order of )(?<!orders of )\bmagnitude\b", re.IGNORECASE),
    ],
    # The v1 domain-tag mechanism. Ordinary "touches" (the verb) stays
    # legal; the underscored keys and the bare key-in-prose form do not.
    # (A backticked `touches:` is a machine identifier and never reaches
    # these patterns - markdown code spans are stripped before scanning.)
    "touches": [
        re.compile(r"\btouches?_(?:any|common)\b"),
        re.compile(r"\btouches:\s"),
    ],
    # The v1 word for owed follow-up work. The DoD tag and the spine key
    # renamed with schema 2.0 ("(follow-up:" and "follow_ups:"); the CLI
    # verb renamed with the CLI-voice slice (`compass follow-up resolve`),
    # which re-tightened this ban to its final form - no tolerated
    # spelling remains. Ordinary "backfilled" (the plain verb, past tense)
    # stays legal.
    "backfill": [
        re.compile(r"\bbackfills?\b", re.IGNORECASE),
    ],
    # The v1 work-item noun in human-facing prose. Machine-state forms
    # stay legal during the transition: task.yml, current-task, --task,
    # task-slug and friends.
    "task": [
        re.compile(
            r"(?<!current-)(?<!--)(?<!<)\btasks?\b(?!\.yml)(?![-_>])",
            re.IGNORECASE,
        ),
    ],
    # Governance shorthand codes in human-facing prose. The plain
    # statement of the rule replaces the code; codes may live in
    # governance config files, which the scan does not read.
    "G1..G5 / S1..S7 codes": [
        re.compile(r"\bG[1-5]\b"),
        re.compile(r"\bS[1-7]\b"),
    ],
    # The v1 intake artifact filename; v2 writes prd.md.
    "brief.md": [
        re.compile(r"\bbrief\.md\b"),
    ],
    # The v1 acceptance-criteria artifact filename.
    "spec.feature.md": [
        re.compile(r"\bspec\.feature(?:\.md)?\b"),
    ],
}

# The ratchet's high-water mark: every surface still awaiting its rename
# slice as of the freeze. test_pending_list_only_ever_shrinks compares the
# vocabulary file's live `pending_surfaces` against this frozenset, so the
# live list can drop entries but never gain one. A rename slice removes its
# surface from the vocabulary file AND from here in the same diff, which is
# what makes the shrink visible in review.
# One surface left: the doctrine document, split to the second half of
# the docs-prose slice at a recorded green boundary. The ratchet reaches
# zero when that half lands; the shrink-only meta-test holds every exit.
PENDING_BASELINE: frozenset[str] = frozenset({
    "docs/methodology.md",
})


# ---------------------------------------------------------------------------
# Loading and scanning
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _terminology() -> dict:
    """The parsed vocabulary file, loaded once per test session."""
    if not TERMINOLOGY_PATH.exists():
        pytest.fail(
            "governance/terminology.yml does not exist. It is the frozen v2 "
            "vocabulary; land it alongside this test (content spec: "
            "docs/proposals/terminology.yml)."
        )
    return yaml.safe_load(TERMINOLOGY_PATH.read_text(encoding="utf-8"))


def _read(path: Path) -> str | None:
    """File text, or None when the file is binary or has gone away."""
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


INLINE_CODE_RE = re.compile(r"`[^`]+`")


def _scan_units(path: Path) -> list[tuple[int, str]]:
    """The (line number, text) pairs the scanner checks for one file.

    Two surfaces get less than full text, for the same reason: the scan
    measures what a surface *teaches*, not what the machinery is currently
    named. `cli/compass` contributes only its Python string literals. In
    markdown, fenced code blocks and inline code spans are machine
    identifiers - a backticked `/compass:frame` names a command that really
    is still called that during the transition - so markdown contributes
    prose only. The rename slices tighten this by making the old names
    disappear from the machinery itself; until then, prose must be clean v2
    vocabulary and live v1 names appear only as code.
    """
    text = _read(path)
    if text is None:
        return []
    if path == REPO_ROOT / "cli" / "compass" or path.suffix == ".py":
        # Python surfaces contribute USER-FACING string literals only.
        # Tightened when the surface widened to cli/compass_pkg/ at the
        # CLI-voice slice, with two deliberate exclusions:
        #   - docstrings: they teach the developer reading the source, not
        #     the user at the terminal; the scan measures what the CLI
        #     *says*, and a docstring is never printed.
        #   - literals with no whitespace: a single token is a machine
        #     identifier (a spine key, a filename, a flag), not prose.
        # Before this, cli/compass was pending and the scan never ran
        # against it, so no enforcement is loosened by the exclusions.
        try:
            tree = ast.parse(text)
        except SyntaxError:
            return list(enumerate(text.splitlines(), 1))
        docstrings: set[int] = set()
        for node in ast.walk(tree):
            body = getattr(node, "body", None)
            if (isinstance(node, (ast.Module, ast.FunctionDef,
                                  ast.AsyncFunctionDef, ast.ClassDef))
                    and body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                docstrings.add(id(body[0].value))
        units = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if id(node) in docstrings or " " not in node.value:
                    continue
                for offset, line in enumerate(node.value.splitlines()):
                    units.append((node.lineno + offset, line))
        return units
    if path.suffix == ".md":
        units = []
        fenced = False
        for lineno, line in enumerate(text.splitlines(), 1):
            if line.lstrip().startswith("```"):
                fenced = not fenced
                continue
            if fenced:
                continue
            units.append((lineno, INLINE_CODE_RE.sub(" ", line)))
        return units
    if path.suffix in (".yml", ".yaml"):
        # The YAML analogue of the markdown rule: in a machine file only the
        # comments are prose - keys and values are the live schema. Backticked
        # names inside a comment are code, as in markdown.
        units = []
        for lineno, line in enumerate(text.splitlines(), 1):
            if "#" in line:
                comment = line.split("#", 1)[1]
                units.append((lineno, INLINE_CODE_RE.sub(" ", comment)))
        return units
    return list(enumerate(text.splitlines(), 1))


def _surface_files(surface: str) -> list[Path]:
    """Every scannable file a surface entry names.

    A trailing slash means a directory, scanned recursively. `governance/`
    contributes only its prose (`*.md`): its YAML files legitimately carry
    machine identifiers, and the vocabulary file itself names every banned
    term by necessity.
    """
    root = REPO_ROOT / surface
    if not surface.endswith("/"):
        return [root] if root.is_file() else []
    if not root.is_dir():
        return []
    files = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if PRUNE_DIRS & set(path.parts):
            continue
        if surface == "governance/" and path.suffix != ".md":
            continue
        files.append(path)
    return files


def _scan_files(files: list[Path]) -> list[str]:
    """Every banned-term hit across `files`.

    Each hit names the file, line, banned term, and the pattern that
    matched, so a failure is actionable without re-running anything.
    """
    hits = []
    for path in files:
        rel = path.relative_to(REPO_ROOT)
        for lineno, line in _scan_units(path):
            for term, patterns in BAN_PATTERNS.items():
                for pattern in patterns:
                    if pattern.search(line):
                        hits.append(
                            f"{rel}:{lineno}: banned '{term}' "
                            f"(pattern {pattern.pattern!r}): {line.strip()[:80]}"
                        )
    return hits


def _enforced_hits(scan_cfg: dict) -> list[str]:
    """The hits that fail the build under a scan config.

    Surfaces in `pending_surfaces` are skipped - that is the ratchet's
    tolerance. Files under an `exempt` path are skipped wherever they
    appear - history stays honest.
    """
    exempt = tuple(scan_cfg.get("exempt", []))
    hits = []
    for surface in scan_cfg["surfaces"]:
        if surface in scan_cfg["pending_surfaces"]:
            continue
        files = [
            f for f in _surface_files(surface)
            if not str(f.relative_to(REPO_ROOT)).startswith(exempt)
        ]
        hits.extend(_scan_files(files))
    return hits


def _report(hits: list[str], rule: str) -> str:
    shown = "\n".join("  " + h for h in hits[:MAX_REPORTED])
    more = ""
    if len(hits) > MAX_REPORTED:
        more = f"\n  ... and {len(hits) - MAX_REPORTED} more"
    return f"{len(hits)} vocabulary violation(s).\n{rule}\n{shown}{more}"


# ---------------------------------------------------------------------------
# Well-formedness of the vocabulary file
# ---------------------------------------------------------------------------

def test_vocabulary_file_parses_with_three_sections():
    """TRC-A1: governance/terminology.yml parses and carries terms, banned,
    and scan - the glossary, the bans, and what the scan covers."""
    cfg = _terminology()
    assert isinstance(cfg, dict), "terminology.yml must parse to a mapping"
    assert cfg.get("version"), "terminology.yml must declare a version"
    assert isinstance(cfg.get("terms"), dict) and cfg["terms"], (
        "terminology.yml needs a non-empty terms: mapping"
    )
    assert isinstance(cfg.get("banned"), list) and cfg["banned"], (
        "terminology.yml needs a non-empty banned: list"
    )
    assert isinstance(cfg.get("scan"), dict), (
        "terminology.yml needs a scan: mapping"
    )


def test_every_term_states_its_meaning():
    """TRC-A2: a term without a meaning is a name, not vocabulary."""
    missing = [
        name for name, entry in _terminology()["terms"].items()
        if not (isinstance(entry, dict) and str(entry.get("means", "")).strip())
    ]
    assert not missing, (
        f"terms without a means: field: {missing}. Every term carries its "
        "exact framework meaning; that is what makes the file a glossary."
    )


def test_every_ban_carries_replacement_and_context():
    """TRC-A3: a ban without a replacement gives no way forward, and one
    without a context note bans the word rather than the usage."""
    broken = [
        entry.get("term", f"<entry {i}>")
        for i, entry in enumerate(_terminology()["banned"])
        if not (
            isinstance(entry, dict)
            and str(entry.get("term", "")).strip()
            and str(entry.get("replacement", "")).strip()
            and str(entry.get("context", "")).strip()
        )
    ]
    assert not broken, (
        f"banned entries missing term, replacement, or context: {broken}"
    )


def test_scan_config_declares_its_three_lists():
    """TRC-A4: the scan section names what is checked (surfaces), what never
    is (exempt), and what is tolerated for now (pending_surfaces)."""
    scan = _terminology()["scan"]
    for key in ("surfaces", "exempt", "pending_surfaces"):
        value = scan.get(key)
        assert isinstance(value, list) and all(
            isinstance(item, str) and item for item in value
        ), f"scan.{key} must be a list of path strings"
    assert scan["surfaces"], "scan.surfaces must not be empty"


def test_every_related_term_is_defined():
    """TRC-A1 (v2-terminology-dangling-refs): a `related:` reference to a
    term the file never defines is a dangling pointer in the glossary - the
    reader clicks through to nothing. Every referenced term must have its
    own entry."""
    terms = _terminology()["terms"]
    dangling = sorted({
        ref
        for entry in terms.values() if isinstance(entry, dict)
        for ref in (entry.get("related") or [])
        if ref not in terms
    })
    assert not dangling, (
        f"related: lists reference terms with no entry: {dangling}. "
        "Define each one under terms: or drop the reference."
    )


def test_pending_entry_must_name_a_scanned_surface():
    """TRC-F1: a pending entry outside the surface list would never burn
    down - nothing would ever scan it, so nothing would ever demand its
    removal."""
    scan = _terminology()["scan"]
    strays = set(scan["pending_surfaces"]) - set(scan["surfaces"])
    assert not strays, (
        f"pending_surfaces entries not in surfaces: {sorted(strays)}. "
        "Pending is a subset of scanned; anything else is dead config."
    )


# ---------------------------------------------------------------------------
# Scanner precision, proven by fixtures
# ---------------------------------------------------------------------------

def test_every_ban_is_bound_to_a_pattern():
    """TRC-B1 (binding): the vocabulary file and the pattern table stay in
    one-to-one correspondence, so a ban cannot be added without a pattern
    and a pattern cannot outlive its ban."""
    banned_terms = {entry["term"] for entry in _terminology()["banned"]}
    bound_terms = set(BAN_PATTERNS)
    assert banned_terms == bound_terms, (
        f"unbound bans (add patterns here): {sorted(banned_terms - bound_terms)}; "
        f"orphan patterns (ban was dropped): {sorted(bound_terms - banned_terms)}"
    )


def test_banned_usage_in_fixture_is_flagged():
    """TRC-B1: every ban catches its planted usage in the banned fixture,
    and every hit names file, line, term, and pattern."""
    hits = _scan_files([FIXTURE_BANNED])
    assert hits, "the banned-usage fixture produced no hits at all"
    flagged_terms = {
        term for term in BAN_PATTERNS
        if any(f"banned '{term}'" in hit for hit in hits)
    }
    unflagged = set(BAN_PATTERNS) - flagged_terms
    assert not unflagged, (
        f"bans with no hit in tests/fixtures/terminology/banned_usage.md: "
        f"{sorted(unflagged)}. Either the pattern is too narrow or the "
        "fixture lacks a planted usage - plant one and make it catch."
    )
    for hit in hits:
        assert re.match(r"^tests/fixtures/terminology/banned_usage\.md:\d+: ", hit), (
            f"hit does not lead with file:line: {hit}"
        )


def test_innocent_usage_is_not_flagged():
    """TRC-B2: ordinary English reuse of the banned words stays legal - a
    hit in the innocent fixture means a pattern is too broad."""
    hits = _scan_files([FIXTURE_INNOCENT])
    assert not hits, _report(
        hits,
        "Rule: bans are pattern-plus-context, not bare words. These lines "
        "use the words innocently and must not match; narrow the pattern in "
        "BAN_PATTERNS.",
    )


# ---------------------------------------------------------------------------
# The ratchet
# ---------------------------------------------------------------------------

def test_pending_surface_may_still_carry_banned_terms():
    """TRC-C1: a surface still in pending_surfaces is tolerated, so CI stays
    green while its rename slice is unshipped."""
    fixture_surface = "tests/fixtures/terminology/"
    hits = _enforced_hits({
        "surfaces": [fixture_surface],
        "exempt": [],
        "pending_surfaces": [fixture_surface],
    })
    assert not hits, (
        "a pending surface was scanned as if enforced; the ratchet's "
        "tolerance is broken"
    )


def test_surface_removed_from_pending_must_be_clean():
    """TRC-C2: once a surface leaves pending_surfaces its banned terms are
    build failures, named by file, line, and pattern."""
    fixture_surface = "tests/fixtures/terminology/"
    hits = _enforced_hits({
        "surfaces": [fixture_surface],
        "exempt": ["tests/fixtures/terminology/innocent_usage.md"],
        "pending_surfaces": [],
    })
    assert hits, (
        "an enforced surface full of banned terms produced no hits; the "
        "scan is not scanning"
    )
    for hit in hits:
        assert re.match(r"^\S+:\d+: banned '.+' \(pattern ", hit), (
            f"hit is not actionable (needs file:line, term, pattern): {hit}"
        )


def test_exempt_path_is_never_scanned():
    """TRC-F2: exempt paths stay unscanned even inside an enforced surface,
    so proposals, analysis, decision records, and this test's own fixtures
    remain honest history."""
    fixture_surface = "tests/fixtures/terminology/"
    hits = _enforced_hits({
        "surfaces": [fixture_surface],
        "exempt": [fixture_surface],
        "pending_surfaces": [],
    })
    assert not hits, _report(
        hits, "Rule: a file under an exempt path never produces a hit."
    )


def test_pending_list_only_ever_shrinks():
    """TRC-C3: the live pending list is a subset of the committed baseline.

    Removing a surface (with the baseline edit in the same diff) is a rename
    slice finishing its job. Adding one means un-renaming a surface, and
    that is a recorded vocabulary decision, not an edit - the freeze gives
    vocabulary changes the same ceremony as a decision record.
    """
    pending = set(_terminology()["scan"]["pending_surfaces"])
    grown = pending - PENDING_BASELINE
    assert not grown, (
        f"pending_surfaces gained entries: {sorted(grown)}. The ratchet only "
        "tightens; growing it requires editing PENDING_BASELINE in this "
        "file, which is a deliberate, reviewed act."
    )


def test_repository_scan_is_green():
    """TRC-C4: the enforced scan over the real config passes. On freeze day
    every surface is pending, so this is green by construction; from the
    first rename slice on, it is green because cleaned surfaces stay clean.
    """
    hits = _enforced_hits(_terminology()["scan"])
    assert not hits, _report(
        hits,
        "Rule: a surface not in pending_surfaces must contain no banned v1 "
        "vocabulary (governance/terminology.yml, banned:). Use each ban's "
        "replacement; the context note says which usages are in scope.",
    )
