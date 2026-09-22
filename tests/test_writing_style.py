"""The mechanical half of the writing-style rewrite, enforced.

The writing-style audit records 2,928 findings across 474 files against the
standard in the maintainer's global `CLAUDE.md`. It is not itself part of
this repository's tracked tree - it lives under `docs/analysis/`, which is
gitignored, so it opens on the maintainer's machine and nowhere else. Nine
batches fix the 474 files it names; this module is what judges every one of
them, and what stops the prose drifting back afterwards.

Fourteen rules can be held mechanically - a sweep reads the tracked tree,
reports a file, a line and what it found, and is silent when the prose is
clean. Each sweep is proven able to fail before it is trusted: a breach is
planted in `tests/fixtures/writing-style/`, and the sweep must report it
before a zero from the real tree means anything (`PBW-E1`, `PBW-E2`).

The sweeps must land before the batches that use them, or the suite goes red
the moment they land and blocks every batch. `tests/writing_style_pending/`
holds nine lists, one per batch, of the paths its sweep skips; a batch's
definition of done is deleting its own list in the same commit as its prose,
so the sweep starts judging a file the moment its batch fixes it. The lists
are checked pairwise disjoint and shrink-only (`PBW-D8`), which is what makes
the audit's "the batches share no files" claim a checked fact rather than an
assertion.

`RULES` is a registry, not fourteen hand-written test bodies: `PBW-E1` proves
every rule in it in one loop, so a fifteenth rule cannot be added unproven.
Each rule owns its own patterns and its own named exemptions - the classes of
prose this covers have nothing in common beyond the text a reader sees, so a
shared matcher would fit none of them well.
"""
from __future__ import annotations

import ast
import io
import json
import re
import subprocess
import tokenize
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Callable, Iterable

import pytest
import yaml

REPO_ROOT = Path(__file__).parent.parent
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "writing-style"
PENDING_DIR = REPO_ROOT / "tests" / "writing_style_pending"
TERMINOLOGY_PATH = REPO_ROOT / "governance" / "terminology.yml"

# The audit's own file count. A per-batch pending list may only shrink: the
# ratchet's meta-checks (further down) hold this number as the high-water
# mark, and the close-out unit deletes it along with the lists themselves.
PENDING_PATHS_HIGH_WATER = 254

# What `reader.prose_spans` treats as prose inside a YAML value: the keys
# whose value a reader or a printed message actually sees, not the machine
# contract a migration would rename. Mirrors the key list the behaviour
# comparison blanks (`DD-3`), so the two halves cannot disagree about what
# prose is.
PROSE_KEYS = frozenset({"description", "statement", "rationale", "name", "help",
                        "means", "not", "context", "why", "reason", "also",
                        "appears_in", "referent"})

# Files this issue does not touch, matched by exact path or by directory
# prefix (a trailing slash). `docs/system-spec.md` is derived and regenerated
# by `compass ship`; the two `cli/vendor/` paths are upstream code copied
# unmodified (DD-7 keeps `cli/vendor/README.md` out of this set, because
# Compass wrote it); `LICENSE` and `assets/` are out of scope.
EXCLUDED_PATHS: frozenset[str] = frozenset({
    "docs/system-spec.md",
    "cli/vendor/yaml/",
    "cli/vendor/LICENSE-PyYAML",
    "LICENSE",
    "assets/",
})


# ---------------------------------------------------------------------------
# The shapes every rule and every sweep share.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ProseSpan:
    """One line of prose a rule may judge, with the file and kind it came
    from. A markdown line, a Python comment or docstring line, a shell
    comment, or a YAML/JSON prose value - never a printed string, an
    asserted string or a machine key."""

    path: str
    line: int
    text: str
    kind: str  # markdown | comment | docstring | yaml_value | json_value


@dataclass(frozen=True)
class Finding:
    """One rule-reported breach: the file, the line and what the rule found."""

    path: str
    line: int
    detail: str


@dataclass(frozen=True)
class Exemption:
    """A named, reasoned carve-out for one rule at one file. Never a widened
    pattern (`PBW-E3`) - the pattern stays the same for every other file."""

    path: str
    quote: str
    reason: str


@dataclass(frozen=True)
class Report:
    """One sweep's result: which rule ran, what it found, and how many files
    it looked at - so a zero from an empty file set reads differently from a
    zero from clean prose (`PBW-E2`)."""

    rule_id: str
    findings: tuple[Finding, ...]
    files_scanned: int

    def render(self) -> str:
        lines = [f"{self.rule_id}: {len(self.findings)} finding(s) over "
                 f"{self.files_scanned} file(s) scanned"]
        for finding in self.findings:
            lines.append(f"  {finding.path}:{finding.line}: {finding.detail}")
        return "\n".join(lines)


@dataclass(frozen=True)
class Rule:
    """One mechanical rule: its id, the scenario it satisfies, the finder
    that reads one span at a time, and the exemptions found in review."""

    id: str
    scenario: str
    find: Callable[[ProseSpan], list[Finding]]
    exemptions: tuple[Exemption, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# reader - what counts as prose, per file type. The one place that decides,
# so a rule cannot quietly read a different surface from its siblings.
# ---------------------------------------------------------------------------

def _read(path: Path) -> str | None:
    """A file's text, or None when it is binary or has gone since git listed it."""
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def _markdown_spans(rel: str, text: str) -> list[ProseSpan]:
    """Every line, with a fenced block's contents and a blockquote line
    blanked rather than dropped - so a reported line number stays true."""
    spans: list[ProseSpan] = []
    in_fence = False
    fence_char = ""
    for lineno, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        fence = re.match(r"^(`{3,}|~{3,})", stripped)
        if fence:
            if not in_fence:
                in_fence, fence_char = True, fence.group(1)[0]
            elif stripped[0] == fence_char:
                in_fence = False
            spans.append(ProseSpan(rel, lineno, "", "markdown"))
            continue
        if in_fence or re.match(r"^\s*>", line):
            spans.append(ProseSpan(rel, lineno, "", "markdown"))
            continue
        spans.append(ProseSpan(rel, lineno, line, "markdown"))
    return spans


def _python_spans(rel: str, text: str) -> list[ProseSpan]:
    """Comments from `tokenize`, docstrings from `ast`. Never another string
    literal - a printed message or an assertion is not what this module
    checks, and the behaviour comparison (`DD-3`) is what proves neither
    changed."""
    spans: list[ProseSpan] = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(text).readline):
            if tok.type == tokenize.COMMENT:
                spans.append(ProseSpan(rel, tok.start[0],
                                        tok.string.lstrip("#").strip(),
                                        "comment"))
    except (tokenize.TokenizeError, IndentationError, SyntaxError):
        pass
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return spans
    docstring_ids = set()
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if (isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                               ast.ClassDef))
                and body and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)):
            doc = body[0].value
            docstring_ids.add(id(doc))
            for offset, line in enumerate(doc.value.splitlines()):
                spans.append(ProseSpan(rel, doc.lineno + offset, line, "docstring"))
    return spans


def _shell_spans(rel: str, text: str) -> list[ProseSpan]:
    """`#` comment text only - never a command line, so a printed message a
    hook emits through `cat >&2 <<EOF` is out of reach the same way a Python
    string literal is."""
    spans: list[ProseSpan] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        match = re.search(r"(?:^|\s)#(.*)$", line)
        if match:
            spans.append(ProseSpan(rel, lineno, match.group(1), "comment"))
    return spans


_YAML_KEY_RE = re.compile(r"^(\s*-?\s*)([\w.\-]+)\s*:\s?(.*)$")


def _yaml_comment_spans(rel: str, text: str) -> list[ProseSpan]:
    """Whole-line `#` comments. An inline comment after a value is rare in
    this tree's YAML and is left to the value-side walk below, which already
    reads the value itself."""
    spans: list[ProseSpan] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("#"):
            spans.append(ProseSpan(rel, lineno, stripped[1:], "comment"))
    return spans


def _walk_yaml_node(node, rel: str, spans: list[ProseSpan]) -> None:
    """Depth-first walk of a composed YAML node tree, collecting the value of
    every `PROSE_KEYS` key at any depth. Composing rather than a line regex
    is what makes a folded or literal block scalar (`description: >`) read
    correctly - the parser already knows where the value starts and ends."""
    if isinstance(node, yaml.MappingNode):
        for key_node, value_node in node.value:
            if (isinstance(key_node, yaml.ScalarNode)
                    and key_node.value in PROSE_KEYS
                    and isinstance(value_node, yaml.ScalarNode)):
                start = value_node.start_mark.line + 1
                for offset, line in enumerate(str(value_node.value).splitlines()):
                    spans.append(ProseSpan(rel, start + offset, line, "yaml_value"))
            else:
                _walk_yaml_node(value_node, rel, spans)
    elif isinstance(node, yaml.SequenceNode):
        for item in node.value:
            _walk_yaml_node(item, rel, spans)


def _yaml_spans(rel: str, text: str) -> list[ProseSpan]:
    """`#` comment text, plus the values of `PROSE_KEYS` keys at any depth.
    Never another value - a machine enum naming a retired-word compound
    stays out of reach, the same protection `PBW-D1` already holds for
    identifiers."""
    spans = _yaml_comment_spans(rel, text)
    try:
        node = yaml.compose(text)
    except yaml.YAMLError:
        return spans
    if node is not None:
        _walk_yaml_node(node, rel, spans)
    return spans


_JSON_DESCRIPTION_RE = re.compile(r'"description"\s*:\s*"((?:[^"\\]|\\.)*)"')


def _json_spans(rel: str, text: str) -> list[ProseSpan]:
    """`description` values only - the text a validation error quotes back,
    and the closest thing a schema has to documentation."""
    spans: list[ProseSpan] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        match = _JSON_DESCRIPTION_RE.search(line)
        if match:
            spans.append(ProseSpan(rel, lineno, match.group(1), "json_value"))
    return spans


def _spans_for_file(path: Path) -> list[ProseSpan]:
    rel = str(path.relative_to(REPO_ROOT))
    text = _read(path)
    if text is None:
        return []
    suffix = path.suffix
    if suffix == ".py":
        return _python_spans(rel, text)
    if suffix == ".md":
        return _markdown_spans(rel, text)
    if suffix in (".yml", ".yaml"):
        return _yaml_spans(rel, text)
    if suffix == ".json":
        return _json_spans(rel, text)
    if suffix == ".sh" or suffix == "":
        # A dotfile or an extensionless script such as Makefile or
        # .gitignore reads the same way a shell script does: a `#` comment
        # is prose, a command line is not.
        return _shell_spans(rel, text)
    return []


def prose_spans(paths: Iterable[Path]) -> list[ProseSpan]:
    """Every span a rule may read, across every path given."""
    spans: list[ProseSpan] = []
    for path in paths:
        spans.extend(_spans_for_file(path))
    return spans


# ---------------------------------------------------------------------------
# The file set - git's own tracked tree, minus the excluded paths and the
# pending lists still in force.
# ---------------------------------------------------------------------------

def _git_ls_files() -> list[str]:
    out = subprocess.run(["git", "ls-files"], cwd=REPO_ROOT,
                          capture_output=True, text=True, check=True)
    return [line for line in out.stdout.splitlines() if line]


def _pending_list_files() -> list[Path]:
    if not PENDING_DIR.is_dir():
        return []
    return sorted(PENDING_DIR.glob("batch-*.txt"))


@lru_cache(maxsize=1)
def _pending_paths() -> frozenset[str]:
    """Every path any batch's pending list still names. A batch removes its
    own file's path only by deleting the whole list in the same commit as
    its prose (DD-2) - there is no partial removal to support."""
    paths: set[str] = set()
    for list_file in _pending_list_files():
        for line in list_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                paths.add(line)
    return frozenset(paths)


def _is_excluded(rel: str) -> bool:
    for excluded in EXCLUDED_PATHS:
        if excluded.endswith("/"):
            if rel == excluded.rstrip("/") or rel.startswith(excluded):
                return True
        elif rel == excluded:
            return True
    return False


_FIXTURE_PREFIX = "tests/fixtures/writing-style/"


def scanned_paths() -> list[Path]:
    """Every tracked path, minus `EXCLUDED_PATHS`, minus the pending lists,
    minus this mechanism's own planted-breach fixtures. The fixtures are not
    on `EXCLUDED_PATHS` - that set is the audit's own five paths - but they
    plant a breach on purpose (`PBW-E1`) and every sweep's own per-rule test
    would otherwise see them as a real, unfixed finding."""
    pending = _pending_paths()
    return [REPO_ROOT / rel for rel in _git_ls_files()
            if rel not in pending and not _is_excluded(rel)
            and not rel.startswith(_FIXTURE_PREFIX)]


# ---------------------------------------------------------------------------
# runner
# ---------------------------------------------------------------------------

def _is_exempt(rule: Rule, span: ProseSpan) -> bool:
    return any(ex.path == span.path and ex.quote in span.text
               for ex in rule.exemptions)


def run_sweep(rule: Rule, paths: Iterable[Path]) -> Report:
    path_list = list(paths)
    findings: list[Finding] = []
    for span in prose_spans(path_list):
        if _is_exempt(rule, span):
            continue
        findings.extend(rule.find(span))
    return Report(rule_id=rule.id, findings=tuple(findings),
                  files_scanned=len(path_list))


# ---------------------------------------------------------------------------
# RULES - one entry per mechanical rule. PBW-E1 iterates this registry, so a
# rule that is not in it is not proven and does not run.
# ---------------------------------------------------------------------------

RULES: dict[str, Rule] = {}


def _register(rule: Rule) -> Rule:
    RULES[rule.id] = rule
    return rule


# ---------------------------------------------------------------------------
# PBW-A1 - no retired v1 word survives in prose, a comment or a test docstring
# ---------------------------------------------------------------------------

# Reused rather than copied (DD-1): `tests/test_terminology.py` already holds
# the tuned, fixture-proven pattern for every banned term. A second copy
# would be a second list to correct, which is exactly what `S14` refuses.
from test_terminology import BAN_PATTERNS  # noqa: E402

# The one definition of the per-line scan exemption marker (allow_marker.py),
# reused for the same reason BAN_PATTERNS is: a retired-word citation that
# governance/terminology.yml's own scan already accepts - a real command name
# retired at a major version, quoted so a reader whose script broke can find
# the row that fixes it - is not a fresh breach for this sweep to invent a
# second opinion about. This module checks the marker only on the span's own
# line: every citation it now guards carries an inline marker in the
# same table cell or sentence, not a marker on a preceding line.
from allow_marker import ALLOW_MARKER_RE  # noqa: E402

# The four reasons the terminology scan misses most retired words
# (audit 5.1) are surface gaps this module's reader already closes: it reads
# comments, it reads tests/, and its patterns are not narrowed to a single
# capitalised form. One gap is not a surface gap but a pattern gap - a
# hyphenated compound naming the retired unit-of-work word or the retired
# work-item word, the two forms the audit names by example - and that is
# what this table widens, term by term, rather than by loosening every
# pattern in BAN_PATTERNS.
HYPHEN_WIDENING: dict[str, tuple[re.Pattern, ...]] = {
    "stream": (re.compile(r"\b[a-z]+-streams?\b", re.IGNORECASE),),
    "task": (re.compile(r"\btask-[a-z]+\b", re.IGNORECASE),),
}

# tests/fixtures/terminology/ plants every banned word on purpose, to prove
# test_terminology.py's own patterns catch it (PBW-D2). This sweep reads the
# same tree and would otherwise report the same fixtures a second time for
# no reason - a structural exclusion for the one directory that exists to
# hold banned words, not a per-quote exemption for prose believed correct.
_RETIRED_WORD_STRUCTURAL_SKIP = "tests/fixtures/terminology/"

# governance/terminology.yml's own `scan.exempt` already excuses
# architecture/decisions/ - "ADRs may quote v1 terms" - because ADR-023
# rules that an accepted record keeps the words it was decided in. The
# retired-word rule honours the same exemption its own governance already
# grants; the idiom rule (PBW-A5) does not, because an ADR's idiom is
# ordinary prose, not the vocabulary the decision was made in.
_ADR_VOCABULARY_SKIP = "architecture/decisions/"

_TERMINOLOGY_PATH_STR = "governance/terminology.yml"
# terminology.yml's own `scan.exempt_regions` already names these four
# top-level blocks as the ones that "carry every retired word by
# necessity" - a ban must name the term it retires, and a rename table must
# name both spellings. PBW-D2 holds the retired-word and idiom sweeps to
# that same exemption for this one file, computed from the blocks'
# real line spans rather than a line range that would go stale on edit.
_TERMINOLOGY_EXEMPT_BLOCKS = frozenset(
    {"banned", "retired_machine_names", "retired_machine_name_exempt", "scan"})


def _leading_banner_start(lines: list[str], key_line_index: int) -> int:
    """The first line of the `# ===...` banner immediately above a key, or
    the key's own line index when there is no such banner. `blocks:` in
    `governance/terminology.yml`'s own `scan.exempt_regions` names a region
    by its key, but the key never explains itself - the comment banner
    directly above it does, and that banner exists BECAUSE the block below
    needs the retired words it names. Stopping the exempt range at the key
    line would flag the explanation and exempt only the list it explains."""
    i = key_line_index
    while i > 0 and (lines[i - 1].strip() == "" or lines[i - 1].lstrip().startswith("#")):
        i -= 1
    return i


@lru_cache(maxsize=1)
def _terminology_exempt_line_ranges() -> tuple[tuple[int, int], ...]:
    path = REPO_ROOT / _TERMINOLOGY_PATH_STR
    if not path.is_file():
        return ()
    text = path.read_text(encoding="utf-8")
    node = yaml.compose(text)
    if not isinstance(node, yaml.MappingNode):
        return ()
    lines = text.splitlines()
    ranges = []
    for key_node, value_node in node.value:
        if (isinstance(key_node, yaml.ScalarNode)
                and key_node.value in _TERMINOLOGY_EXEMPT_BLOCKS):
            start = _leading_banner_start(lines, key_node.start_mark.line)
            ranges.append((start + 1, value_node.end_mark.line + 1))
    return tuple(ranges)


def _in_terminology_exempt_block(span: ProseSpan) -> bool:
    if span.path != _TERMINOLOGY_PATH_STR:
        return False
    return any(start <= span.line <= end
               for start, end in _terminology_exempt_line_ranges())


def _find_retired_word(span: ProseSpan) -> list[Finding]:
    if span.path.startswith(_RETIRED_WORD_STRUCTURAL_SKIP):
        return []
    if ALLOW_MARKER_RE.search(span.text):
        return []
    if span.path.startswith(_ADR_VOCABULARY_SKIP):
        return []
    if _in_terminology_exempt_block(span):
        return []
    findings = []
    for term, patterns in BAN_PATTERNS.items():
        widened = tuple(patterns) + HYPHEN_WIDENING.get(term, ())
        for pattern in widened:
            match = pattern.search(span.text)
            if match:
                findings.append(Finding(
                    span.path, span.line,
                    f'retired word "{match.group(0)}" ({term})'))
                break
    return findings


_register(Rule(
    "PBW-A1", "No retired v1 word survives in prose, a comment "
    "or a test docstring", _find_retired_word,
    exemptions=(
        # PBW-F7's <!-- absorbed: "..." --> markers quote a merge-base
        # sentence verbatim so a reader can see what the rewrite carried
        # forward - the same reason ADR quotes and voice-tells fixtures are
        # exempt elsewhere in this file. HTML comments are not blanked by
        # _markdown_spans, so the quoted retired word is read as prose
        # unless named here.
        Exemption(
            "templates/architecture/decisions/ADR-004-lens-first-planner-second.md",
            "lens annotates), and parallel (both",
            "an absorbed-into marker quoting the merge-base sentence "
            "verbatim, per PBW-F7 - not a v1-vocabulary use of \"lens\"."),
        Exemption(
            "templates/architecture/decisions/ADR-004-lens-first-planner-second.md",
            "no lens consultation applied",
            "the same absorbed-into marker mechanism as the entry above, "
            "for the sentence naming the pre-rename note text."),
        Exemption(
            "tests/test_frame_loads_architecture.py", "# noqa: S102",
            "a flake8 noqa suppression code (exec-builtin), not a "
            "strategy id; found while fixing batch 7, not by the audit."),
        Exemption(
            "docs/compass/2026-08-27-sdd-loop-spike.md",
            "cross-task-architectural-integrity",
            "the real slug of a filed, landed issue - an identifier "
            "(section 4), not a v1-vocabulary use of \"task\""),
        Exemption(
            "docs/compass/2026-08-27-sdd-loop-spike.md",
            "task-reviewer-prompt.md",
            "the literal filename of a file inside the Superpowers "
            "repository, cited so the reference stays openable - not "
            "this project's vocabulary"),
        Exemption(
            "templates/architecture/decisions/README.md",
            "ADR-004-lens-first-planner-second.md",
            "the ADR's real, tracked filename, linked from the index row - "
            "an identifier (section 4), not a v1-vocabulary use of \"lens\". "
            "The row's own title reads \"Architect First Planner Second\"."),
        Exemption(
            "agents/planner.md",
            "templates/architecture/decisions/ADR-004-lens-first-planner-second.md",
            "the real filename of a template ADR this repository ships; "
            "\"lens\" is part of the identifier, not prose, and cannot be "
            "reworded without renaming the file (section 4 protects "
            "identifiers)."),
        Exemption(
            "skills/bdd-specification/refinement-chain.md",
            "architecture/decisions/ADR-004-one-spec-many-lenses.md",
            "the real filename of the shipped ADR this repository has; "
            "\"lenses\" is part of the identifier, not prose. "
            "test_terminology.py's own scan.exempt already carries the "
            "identical exemption for its sweep; this sweep does not read "
            "that list, so it needs its own entry."),
        Exemption(
            "skills/compass-runtime/writing-voice.md",
            "cross-task-architectural-integrity/devlog.md",
            "the real slug of a past, archived issue - the \"Source:\" "
            "line names which issue an archive quote came from. Section "
            "4's verbatim-quote protection covers this citation the same "
            "way it covers the quote: renaming the slug would misattribute "
            "it to an issue that never existed."),
        Exemption(
            "skills/compass-runtime/writing-voice.md",
            "swarm-script-strips-markdown/devlog.md",
            "the real slug of a past, archived issue - the same protected "
            "citation as the cross-task-architectural-integrity exemption "
            "above."),
        Exemption(
            "skills/evidence-gates/architecture-checks.md",
            "ADR-009-fitness-functions-are-project-guardrails.md",
            "the real filename of the shipped ADR this repository has, "
            "cited three times, plus its title quoted verbatim per section "
            "4's quoted-term exception (\"Architectural fitness functions "
            "are project guardrails, not framework guardrails\") - "
            "\"fitness function\" is part of the identifier and the quote, "
            "not prose describing the mechanism in this sweep's own words."),
        Exemption(
            "skills/evidence-gates/architecture-checks.md",
            "Architectural fitness functions are project guardrails",
            "the second line of ADR-009's title, wrapped onto its own "
            "markdown line - the same verbatim quote as the exemption "
            "above; this sweep reads one markdown line at a time, so the "
            "wrapped continuation needs its own entry."),
        Exemption(
            "skills/evidence-gates/architecture-checks.md",
            "a fitness function is an automated check",
            "the parenthetical explaining the quoted term, required by "
            "section 4's quoted-term exception (\"quote it exactly and say "
            "what 'fitness function' means\") - it has to use the term to "
            "define it."),
        # test_terminology.py's own broad bare-word pattern for the ship
        # stage's retired spelling matches the ordinary verb too. The author
        # already marked this exact sentence "vocabulary-scan: allow" for
        # that scan; this sweep reuses the same BAN_PATTERNS (DD-1) but does
        # not read that marker, so the false positive needs its own named
        # exemption.
        Exemption("approaches/spike.md", "Land production code",
                   "ordinary verb, already marked vocabulary-scan: allow "
                   "for the same reason."),
        Exemption("governance/routing-policy.yml", "full-plus-backfill",
                   "a machine stage-weight enum value, already marked "
                   "vocabulary-scan: allow for the same reason."),
        # Each of these five terminology.yml `not:` entries states what a
        # v2 term is NOT, which cannot be written without naming the
        # retired word it replaced - already marked vocabulary-scan: allow
        # for test_terminology.py's own scan, which this sweep does not
        # read.
        Exemption("governance/terminology.yml",
                   "A 'task' - that word survives only as machine state",
                   "a not: field naming the retired word on purpose."),
        Exemption("governance/terminology.yml",
                   "NOT triage. Triage means sorting BETWEEN cases",
                   "a not: field naming the retired word on purpose."),
        Exemption("governance/terminology.yml",
                   "what makes an issue ready. v1 called this \"Clarify\"",
                   "a not: field naming the retired word on purpose."),
        Exemption("governance/terminology.yml",
                   "v1 called this a 'backfill', with states 'owed'",
                   "a not: field naming the retired word on purpose."),
        Exemption("governance/terminology.yml",
                   "recorded, the derived system spec is regenerated. v1 called this \"Land\"",
                   "a not: field naming the retired word on purpose."),
        # docs/glossary.md is DERIVED from governance/terminology.yml by
        # `compass _derive-glossary`, so a `not:` field that has to name a
        # retired word reappears here verbatim. The source entries already
        # carry their own exemptions; the derived copy is a separate path and
        # needs its own. Fixing these would mean editing a generated file,
        # which the drift guard reverts, or removing the ban's own statement
        # of what it bans.
        Exemption("docs/glossary.md",
                   "v1 called this a 'backfill', with states 'owed' and 'paid'",
                   "the derived text of terminology.yml's follow-up `not:` "
                   "field, which cannot say what the term is NOT without "
                   "naming the retired word."),
        Exemption("docs/glossary.md",
                   "A 'task' - that word survives only as machine state",
                   "the derived text of terminology.yml's issue `not:` "
                   "field, same reason as the entry above."),
        # Both comments carry their own "# vocabulary-scan: allow" marker
        # for governance/terminology.yml's scanner, which this sweep does
        # not read (it reuses BAN_PATTERNS, not the marker). The retired
        # spelling in the quote below is deliberate: it is the pre-ADR-023
        # map syntax these lines read for back-compat, not a live use of
        # the retired word.
        Exemption(
            "scripts/integrate.sh", "stream-N",
            "reads the pre-ADR-023 map spelling for back-compat; already "
            "marked '# vocabulary-scan: allow', which this sweep does not "
            "read."),
        Exemption(
            "scripts/multiagent.sh", "stream-N",
            "reads the pre-ADR-023 map spelling for back-compat; already "
            "marked '# vocabulary-scan: allow', which this sweep does not "
            "read."),
        Exemption(
            "cli/compass_pkg/analyze.py",
            'records write "full, streams unbounded by policy"',
            "quotes what an archived 1.x record literally says, already "
            "marked '# vocabulary-scan: allow', which this sweep does not "
            "read."),
        Exemption(
            "cli/compass_pkg/core.py",
            "retired `task` key still load through this row",
            "documents the retired key SPINE_KEY_MAP maps forward, the same "
            "purpose terminology.yml's own `not:` fields serve."),
        Exemption(
            "cli/compass_pkg/core.py",
            "multiagent work, and fan out \"independent subtasks\"; "
            "`topology` and",
            "documents the two retired words this map reads for back-compat, "
            "the same purpose terminology.yml's own `not:` fields serve."),
        Exemption(
            "cli/compass_pkg/core.py",
            "`stream` were Compass-only words for both",
            "documents the two retired words this map reads for back-compat, "
            "the same purpose terminology.yml's own `not:` fields serve."),
        Exemption(
            "cli/compass_pkg/core.py",
            "Evidence types. ADR-023 renamed `coherence-check` to "
            "`consistency-check`;",
            "documents the retired evidence type this map reads for "
            "back-compat, the same purpose terminology.yml's own `not:` "
            "fields serve."),
        Exemption(
            "cli/compass_pkg/core.py",
            "Friction categories. ADR-023 retired `ceremony`, and the enum "
            "holds",
            "documents the retired word this map reads for back-compat, the "
            "same purpose terminology.yml's own `not:` fields serve."),
        Exemption(
            "cli/compass_pkg/analyze.py",
            "Extract the reference route name from delivery-approach.md",
            "the function reads the literal 1.x field `**Reference "
            "route:**`, which route.md wrote before the v2 rename; the "
            "docstring names the field it searches for."),
        Exemption(
            "cli/compass_pkg/analyze.py",
            "Looks for: **Reference route:** Express",
            "quotes the literal 1.x field and a real 1.x route name, the "
            "text the regex searches an old document for."),
        Exemption(
            "cli/compass_pkg/test_ids.py",
            "governance/strategies.md carries S7",
            "a worked example of a sentence that merely mentions a file, "
            "inside quotes - prose, not a path reference, so S7 here names "
            "nothing and needs no meaning."),
        Exemption(
            "cli/migrate-map.yml",
            "ADR-023 retired `ceremony`",
            "documents which retired word the data rows below map away "
            "from, the same purpose terminology.yml's own `not:` fields "
            "serve - this file is data exempt from the vocabulary scan and "
            "must name retired words on purpose (audit note on this file)."),
        Exemption(
            "cli/compass_pkg/migrate.py",
            "the same document: `brief.md` and `prd.md` both become "
            "`intent.md`",
            "names the real v1 filenames this migration function reads - "
            "the module's whole purpose is v1-to-v2 filename mapping, the "
            "same reason migrate-map.yml's data rows name retired words."),
        Exemption(
            "cli/compass_pkg/landed_by.py",
            "and `backfills-paid` still apply",
            "backfills-paid is the real check id in "
            "governance/guardrails.yml:74, an identifier - the audit notes "
            "the `backfills:` key is an identifier and stays; this is the "
            "same class of identifier."),
        Exemption(
            "cli/compass_pkg/checks.py",
            'in preference to task.get("task") which may be a',
            "quotes the real dict lookup at line 669 below, over the "
            "legacy `task` root key normalize_spine reads - an identifier, "
            "not prose."),
        Exemption(
            "cli/compass_pkg/receipt.py",
            'Records written before ADR-023 say "Topology"',
            "documents the retired label a pre-ADR-023 record literally "
            "carries, so this reader can still parse it - the same "
            "back-compat reading terminology.yml's own not: fields and the "
            "stream-N exemptions above cover."),
        Exemption(
            "cli/compass_pkg/receipt.py",
            '"Topology" (ADR-006)',
            "documents the retired label a pre-ADR-023 record literally "
            "carries, so this reader can still parse it."),
    ),
))


# ---------------------------------------------------------------------------
# PBW-A2 - the shorter word stands where the word is not an identifier
# ---------------------------------------------------------------------------

# The audit's own found-candidates table (section 5.2) - the longer word or
# words on the left, the plain replacement on the right. Each row becomes one
# pattern with verb-form flexibility, matching the shape of the audit's own
# `git grep` example rather than a bare word.
WORD_TABLE: tuple[tuple[tuple[str, ...], str], ...] = (
    (("verify", "validate"), "check"),
    (("require",), "need"),
    (("attempt",), "try"),
    (("provide", "supply"), "give"),
    (("perform", "execute"), "do"),
    (("modify", "alter"), "change"),
    (("currently", "presently"), "now"),
    (("previously", "prior to"), "before"),
    (("ensure",), "make sure"),
    (("indicate", "denote"), "show"),
    (("utilise", "leverage", "employ"), "use"),
    (("in order to",), "to"),
    (("sufficient",), "enough"),
    (("obtain", "acquire"), "get"),
)


def _verb_pattern(word: str) -> str:
    """One word's alternation, widened for its common verb forms. A phrase
    (a space inside it) has no verb forms and is matched exactly."""
    if " " in word:
        return re.escape(word)
    if word.endswith("y") and word[-2:-1] not in "aeiou":
        return re.escape(word[:-1]) + r"(?:y|ies|ied|ying)"
    return re.escape(word) + r"(?:s|es|ed|ing)?"


_WORD_TABLE_PATTERNS: dict[tuple[str, ...], re.Pattern] = {
    words: re.compile(r"\b(?:" + "|".join(_verb_pattern(w) for w in words) + r")\b",
                       re.IGNORECASE)
    for words, _ in WORD_TABLE
}


def _word_table_exempt(text: str, match: re.Match) -> bool:
    """The identifiers PBW-A2 names: a gate id (`verify.analyze`), a
    backticked or code-spanned reference, a slash command
    (`/compass:verify`), and "the verify stage" - the one place the stage
    name, not the verb, is what the sentence means."""
    start, end = match.span()
    if start > 0 and text[start - 1] in "`/:":
        return True
    if text[end:end + 1] == ".":
        return True
    if re.match(r"\s+stage\b", text[end:end + 8], re.IGNORECASE):
        return True
    return False


def _find_word_table(span: ProseSpan) -> list[Finding]:
    findings = []
    for words, replacement in WORD_TABLE:
        pattern = _WORD_TABLE_PATTERNS[words]
        for match in pattern.finditer(span.text):
            if _word_table_exempt(span.text, match):
                continue
            findings.append(Finding(
                span.path, span.line,
                f'"{match.group(0)}" -> "{replacement}"'))
    return findings


# CLAUDE.md and AGENTS.md each carry the maintainer's own "Use the shorter
# word" reference table - the rule's documentation, not prose that breaks the
# rule. Its rows name the very words the rule retires, so the table cannot
# pass this sweep by rewording (PBW-F4 refuses a rewrite that would). Each
# row is its own named exemption (PBW-E3): the quote is the whole row, so a
# later row sharing one short word from an earlier row cannot exempt
# unrelated prose elsewhere in the same file.
_SHORTER_WORD_TABLE_ROWS: tuple[str, ...] = (
    "| utilise, leverage | use |",
    "| obtain, acquire | get |",
    "| provide, supply | give |",
    "| indicate, denote | show |",
    "| validate | check |",
    "| modify, alter | change |",
    "| require | need |",
    "| ensure | make sure |",
    "| perform, execute | do |",
    "| facilitate | help |",
    "| attempt | try |",
    "| sufficient | enough |",
    "| currently | now |",
    "| subsequently | then |",
    "| prior to | before |",
    "| in order to | to |",
    "| due to the fact that | because |",
    "| with regard to | about |",
)

_SHORTER_WORD_TABLE_EXEMPTIONS: tuple[Exemption, ...] = tuple(
    Exemption(path, row,
              "the \"Use the shorter word\" table names the retired word as "
              "documentation of the rule, not as prose that breaks it")
    for path in ("CLAUDE.md", "AGENTS.md")
    for row in _SHORTER_WORD_TABLE_ROWS
)

_register(Rule(
    "PBW-A2", "The shorter word stands where the word is not an "
    "identifier", _find_word_table,
    exemptions=_SHORTER_WORD_TABLE_EXEMPTIONS + (
        Exemption(
            "docs/five-minutes.md", "## 5. Verify and ship",
            "\"Verify\" here is the stage name, in the same heading form "
            "as \"1. Assess the work\", \"2. Define acceptance\" and "
            "\"4. Implement with evidence\" above it - an identifier "
            "(section 4), not the verb the word table retires"),
        Exemption(
            "docs/releasing.md", "## Supply-chain stance",
            "\"supply chain\" is the standard security term for this "
            "section's subject, not the verb \"supply\" the word table "
            "retires"),
        Exemption(
            "docs/security.md", "supply-chain requirements",
            "\"supply chain\" is the standard security term, not the verb "
            "\"supply\" the word table retires"),
        Exemption(
            "ci/README.md", "supply-chain stance",
            "the same standard security term as the docs/security.md "
            "exemption above."),
        Exemption(
            "ci/github-actions.yml", "supply-chain stance",
            "the same standard security term as the docs/security.md "
            "exemption above."),
        Exemption(
            ".github/workflows/compass.yml", "supply-chain stance",
            "the same standard security term as the docs/security.md "
            "exemption above."),
        Exemption(
            "compass-contract.md", "7. verify",
            "\"verify\" here is the stage name, one word per line in the "
            "stage list, in the same form as \"1. assess\" and \"6. "
            "implement\" beside it - an identifier (section 4), not the "
            "verb the word table retires"),
        Exemption(
            "docs/methodology.md", "| `/compass:verify` | Verify |",
            "\"Verify\" is the stage name in the stage-mapping table's own "
            "column, beside \"Assess\", \"Define\" and \"Plan\" - an "
            "identifier (section 4), not the verb the word table retires"),
        Exemption(
            "docs/quickstart.md", "### Verify",
            "\"Verify\" here is the stage name, in the same heading form as "
            "the \"### Assess\", \"### Define\" and \"### Implement\" "
            "headings in the same walkthrough - an identifier (section 4), "
            "not the verb the word table retires"),
        Exemption(
            "docs/quickstart.md", "verify, ship -",
            "\"verify\" here is one stage name in a list of stage names "
            "(implement, verify, ship) - an identifier (section 4), not "
            "the verb the word table retires"),
        Exemption(
            "tests/test_command_renames.py",
            "implement, verify, ship; the designer entry point is design;",
            "\"verify\" is one stage name in the list of eight pipeline "
            "commands, the same shape as the docs/quickstart.md exemption "
            "above; found while fixing batch 7, not by the audit."),
        Exemption(
            "tests/test_command_renames.py",
            "point. It inlines assess, define, implement, verify and ship for a small,",
            "\"verify\" is one stage name in a list of stage names, the "
            "same shape as the docs/quickstart.md exemption above; found "
            "while fixing batch 7, not by the audit."),
        Exemption(
            "docs/safety-contract.md", "Human approvals are required",
            "tests/test_g5_trigger.py pins this exact phrase and is not "
            "named for this unit in DD-6 - changing the assertion is not "
            "this batch's to make, so the word-table finding is left "
            "unapplied here and reported instead"),
        Exemption(
            "docs/quickstart.md", "does **not** modify your PATH",
            "tests/test_plugin_doc_drift.py::"
            "test_trc_a2_quickstart_drops_install_sh_path_claim pins this "
            "exact phrase and is not named for this unit in DD-6 - "
            "changing the assertion is not this batch's to make, so the "
            "word-table finding is left unapplied here and reported "
            "instead"),
        Exemption(
            "docs/routing-deep-dive.md", "but verify also runs the",
            "\"verify\" is the stage name here, matching \"feature\" and "
            "the other lowercase reference-shape names beside it - an "
            "identifier (section 4), not the verb the word table retires"),
        Exemption(
            "docs/routing-deep-dive.md", "[refine, verify, ship]",
            "the literal `never_skip` policy value quoted from "
            "governance/routing-policy.yml:109 - an identifier (section "
            "4), not the verb the word table retires"),
        Exemption(
            "docs/routing-deep-dive.md", "implement expedited; verify",
            "\"verify\" is the stage name in a list of stage names, "
            "matching \"implement\" and \"ship\" beside it - an "
            "identifier (section 4), not the verb the word table retires"),
        Exemption(
            "docs/routing-deep-dive.md", "at full verify weight",
            "\"verify\" is the stage name - an identifier (section 4), "
            "not the verb the word table retires"),
        Exemption(
            "docs/routing-deep-dive.md", "not skipped; verify and ship",
            "\"verify\" is the stage name in a list of stage names, "
            "matching \"ship\" beside it - an identifier (section 4), "
            "not the verb the word table retires"),
        Exemption(
            "docs/routing-deep-dive.md", "*before* verify and never verify",
            "\"verify\" is the stage name, twice - an identifier "
            "(section 4), not the verb the word table retires"),
        Exemption(
            "docs/routing-deep-dive.md", "spike. verify becomes",
            "\"verify\" is the stage name - an identifier (section 4), "
            "not the verb the word table retires"),
        Exemption(
            "docs/routing-deep-dive.md",
            "**Verify** runs **at full weight",
            "\"Verify\" is the stage name, bold as one item in the "
            "stage-by-stage list beside \"Plan\", \"Breakdown\", "
            "\"Implement\" and \"Ship\" - an identifier (section 4), "
            "not the verb the word table retires"),
        Exemption(
            "commands/flow.md", "verifying",
            "one label in a parallel list of pipeline-stage gerunds "
            "(\"defining criteria . reviewing requirements . designing . "
            "implementing . verifying . shipping\") - the stage name, not "
            "the verb, and singling it out with \"the verify stage\" would "
            "break the list's parallel form."),
        Exemption(
            "commands/quick-fix.md", "## 4. Verify",
            "a step heading naming the verify stage, parallel to \"## 1. "
            "Assess\" and \"## 5. Ship\" two headings over - those two "
            "escape only because \"assess\" and \"ship\" are not in the "
            "word table, not because a bare stage-name heading is wrong."),
        Exemption(
            "skills/adaptive-routing/composition.md", "**Verify** - which "
            "review dimensions",
            "one label in a parallel bulleted list of pipeline-stage names "
            "(Define, Refine, Plan, Breakdown, Implement, Verify, Ship) - "
            "the stage name, not the verb."),
        Exemption(
            "skills/evidence-gates/review-dimensions.md",
            'as "verified"',
            "the word being quoted is the point of the sentence: it names "
            "the stronger claim a reader wrongly hears in a gate that only "
            "promises \"traceable\". Replacing the quoted word erases the "
            "contrast the sentence exists to make."),
        Exemption(
            "skills/compass-runtime/writing-voice.md",
            "do not perform the process",
            "the pinned principle line, verbatim - "
            "tests/test_human_voice.py:138 asserts this exact string "
            "(PRINCIPLE), and the audit's own per-file entry for this file "
            "lists it under \"Pinned\", to keep as it stands."),
        Exemption(
            "skills/evidence-gates/architecture-checks.md", "RP-REQUIRE-003",
            "a real routing-policy rule id (governance/routing-policy.yml, "
            "`RP-REQUIRE-003`) - the match lands mid-identifier on the "
            "\"REQUIRE\" substring, not the standalone verb the word table "
            "means to catch."),
        Exemption(
            "skills/evidence-gates/architecture-checks.md", "RP-REQUIRE-004",
            "the same rule-id false match as RP-REQUIRE-003 above, for the "
            "sibling rule."),
        Exemption(
            "templates/rollback-plan.md", "RP-REQUIRE-006",
            "the same rule-id false match as RP-REQUIRE-003 above, for the "
            "migrations floor."),
        Exemption(
            "templates/threat-model.md", "RP-REQUIRE-005",
            "the same rule-id false match as RP-REQUIRE-003 above, for the "
            "auth/payments/personal-data floor."),
        Exemption(
            "templates/technical-design.md", "RP-REQUIRE-005",
            "the same rule-id false match as RP-REQUIRE-003 above, for the "
            "auth/payments/personal-data floor."),
        Exemption(
            "templates/technical-design.md", "RP-REQUIRE-006",
            "the same rule-id false match as RP-REQUIRE-003 above, for the "
            "migrations floor."),
        Exemption(
            "schemas/routing-policy.schema.json", "RP-REQUIRE-003",
            "the same rule-id false match as the skills/evidence-gates "
            "exemption above, quoted here as the schema's own example "
            "waiver id."),
        Exemption(
            "cli/compass_pkg/routing.py",
            "calling it a floor is the same conflation the RP-REQUIRE ids "
            "were",
            "RP-REQUIRE is a real routing-policy id prefix - the match "
            "lands mid-identifier on the \"REQUIRE\" substring, the same "
            "false match as the architecture-checks.md exemption above."),
        Exemption(
            "cli/compass_pkg/routing.py",
            "introduced to end - and it would print \"[RP-REQUIRE-003] "
            "floor:\"",
            "RP-REQUIRE-003 is a real rule id, quoted as the literal "
            "printed text this comment explains."),
        Exemption(
            "skills/quick-fix/SKILL.md", "--verified-by",
            "a real CLI flag (`cli/compass:246,258`, `dest=\"verified_by\"`) "
            "- the match lands mid-flag-name on the \"verified\" substring, "
            "not the standalone verb the word table means to catch."),
        Exemption(
            "tests/test_acceptance_verb.py", "--verified-by",
            "the same real CLI flag false match as skills/quick-fix/SKILL.md "
            "above; found while fixing batch 7, not by the audit."),
        Exemption(
            "skills/tdd-discipline/no-natural-red.md", "terraform validate",
            "a third-party command's real name (Terraform's own CLI verb), "
            "not the English verb the word table means to catch - Compass "
            "does not own or spell this identifier."),
        Exemption(
            "cli/compass_pkg/tdd.py", "The sanctioned verified-by kinds",
            "names the `--verified-by` flag's accepted values - the match "
            "lands mid-flag-name on the \"verified\" substring, not the "
            "standalone verb the word table means to catch."),
        Exemption(
            "cli/compass_pkg/tdd.py", "terraform validate`, a schema parse",
            "a third-party command's real name (Terraform's own CLI verb), "
            "not the English verb the word table means to catch."),
        Exemption("approaches/README.md", "but verify adds the security",
                   "names the Verify stage, not the verb."),
        Exemption("approaches/composition-reference.md",
                   "**Verify** - which review dimensions",
                   "names the Verify stage, not the verb."),
        Exemption("approaches/composition-reference.md",
                   "Feature, but Verify also runs",
                   "names the Verify stage, not the verb."),
        Exemption("approaches/feature.md",
                   "| Verify | **Two review points**",
                   "names the Verify stage, not the verb."),
        Exemption("approaches/hotfix.md",
                   "All Verify gates, no exceptions",
                   "names the Verify stage and the Verify gate, not the verb."),
        Exemption("approaches/hotfix.md",
                   "Full Verify gate. Review dimensions",
                   "names the Verify gate, not the verb."),
        Exemption("approaches/hotfix.md", "never Verify itself",
                   "names the Verify stage, not the verb."),
        Exemption("approaches/hotfix.md",
                   "Compress the Verify gate. The stages before Verify are "
                   "compressed; Verify is",
                   "names the Verify gate and stage, not the verb."),
        Exemption("approaches/initiative.md",
                   "| Verify | **All gates, all dimensions.**",
                   "names the Verify stage, not the verb."),
        Exemption("approaches/quick-fix.md", "| Verify | Light gate",
                   "names the Verify stage, not the verb."),
        Exemption("approaches/quick-fix.md",
                   "One review point, at Verify, clearing three gates",
                   "names the Verify stage, not the verb."),
        Exemption("approaches/rubric.md", "Owns the Verify gate",
                   "names the Verify gate, not the verb."),
        Exemption("approaches/spike.md", "| Verify | **= Conclude.**",
                   "names the Verify stage, not the verb."),
        Exemption("architecture/ownership.md", "(verify → ship gate)",
                   "names the Verify stage, not the verb."),
        Exemption("architecture/system-context.md",
                   "implement → verify → ship",
                   "names the Verify stage, not the verb."),
        Exemption("ci/README.md", "verify time - it does not",
                   "names the Verify stage, not the verb."),
        Exemption("examples/README.md", "Verify is a short note",
                   "names the Verify stage, not the verb."),
        Exemption("examples/README.md", "uncompressed* Verify gate",
                   "names the Verify gate, not the verb."),
        Exemption(
            "examples/bdd-adapters/behave/docs/compass/"
            "2026-08-03-reset-password/acceptance-criteria.md",
            "Passes as acceptance (verify)",
            "names the Verify stage in the coverage ledger's own column "
            "header, not the verb."),
        Exemption(
            "examples/bdd-adapters/cucumber-js/docs/compass/"
            "2026-08-03-reset-password/acceptance-criteria.md",
            "Passes as acceptance (verify)",
            "the same coverage-ledger column header as the behave copy."),
        Exemption(
            "examples/bdd-adapters/godog/docs/compass/"
            "2026-08-03-reset-password/acceptance-criteria.md",
            "Passes as acceptance (verify)",
            "the same coverage-ledger column header as the behave copy."),
        Exemption(
            "examples/bdd-adapters/pytest-bdd/docs/compass/"
            "2026-08-03-reset-password/acceptance-criteria.md",
            "Passes as acceptance (verify)",
            "the same coverage-ledger column header as the behave copy."),
        Exemption(
            "examples/feature-api-change/.compass/work/"
            "rate-limit-search-endpoint/devlog.md",
            "13:10 - Verify",
            "a devlog entry heading naming the Verify stage, not the verb."),
        Exemption(
            "examples/feature-api-change/docs/compass/"
            "2026-04-21-rate-limit-search-endpoint/acceptance-criteria.md",
            "Passes as acceptance (verify)",
            "the same coverage-ledger column header as the bdd-adapters "
            "exemption above."),
        Exemption(
            "examples/feature-api-change/docs/compass/"
            "2026-04-21-rate-limit-search-endpoint/delivery-approach.md",
            "| Verify | Full - one gate",
            "names the Verify stage in the per-stage weight table, not the "
            "verb."),
        Exemption(
            "examples/feature-api-change/docs/compass/"
            "2026-04-21-rate-limit-search-endpoint/delivery-approach.md",
            "gate at Verify (the feature's",
            "names the Verify stage, not the verb."),
        Exemption(
            "examples/hotfix-regression/.compass/work/"
            "search-crash-on-empty-filter/devlog.md",
            "10:40 - Verify",
            "a devlog entry heading naming the Verify stage, not the verb."),
        Exemption(
            "examples/hotfix-regression/.compass/work/"
            "search-crash-on-empty-filter/devlog.md",
            "Full Verify - not compressed",
            "names the Verify stage, not the verb."),
        Exemption(
            "examples/hotfix-regression/docs/compass/"
            "2026-05-11-search-crash-on-empty-filter/acceptance-criteria.md",
            "Passes as acceptance (verify)",
            "the same coverage-ledger column header as the bdd-adapters "
            "exemption above."),
        Exemption(
            "examples/hotfix-regression/docs/compass/"
            "2026-05-11-search-crash-on-empty-filter/delivery-approach.md",
            "reviewed the Verify gate",
            "names the Verify gate, not the verb."),
        Exemption(
            "examples/hotfix-regression/docs/compass/"
            "2026-05-11-search-crash-on-empty-filter/delivery-approach.md",
            "permitted Verify deferral",
            "names the Verify stage, not the verb."),
        Exemption(
            "examples/hotfix-regression/docs/compass/"
            "2026-05-11-search-crash-on-empty-filter/delivery-approach.md",
            "| Verify | Full |",
            "names the Verify stage in the per-stage weight table, not the "
            "verb."),
        Exemption(
            "examples/hotfix-regression/docs/compass/"
            "2026-05-11-search-crash-on-empty-filter/delivery-approach.md",
            "full Verify gate - five review",
            "names the Verify gate, not the verb."),
        Exemption(
            "examples/initiative-new-subsystem/.compass/work/"
            "notifications-subsystem/devlog.md",
            "14:50 - Verify",
            "a devlog entry heading naming the Verify stage, not the verb."),
        Exemption(
            "examples/initiative-new-subsystem/docs/compass/"
            "2026-03-02-notifications-subsystem/acceptance-criteria.md",
            "Passes as acceptance (verify)",
            "the same coverage-ledger column header as the bdd-adapters "
            "exemption above."),
        Exemption(
            "examples/initiative-new-subsystem/docs/compass/"
            "2026-03-02-notifications-subsystem/delivery-approach.md",
            "| Verify | All gates, all dimensions",
            "names the Verify stage in the per-stage weight table, not the "
            "verb."),
        Exemption(
            "examples/quick-fix-typo/.compass/work/"
            "fix-timeout-error-message/devlog.md",
            "09:27 - Verify",
            "a devlog entry heading naming the Verify stage, not the verb."),
        Exemption(
            "examples/quick-fix-typo/.compass/work/"
            "fix-timeout-error-message/devlog.md",
            "light Verify output",
            "names the Verify stage, not the verb."),
        Exemption(
            "examples/quick-fix-typo/docs/compass/"
            "2026-05-04-fix-timeout-error-message/acceptance-criteria.md",
            "Passes as acceptance (verify)",
            "the same coverage-ledger column header as the bdd-adapters "
            "exemption above."),
        Exemption(
            "examples/quick-fix-typo/docs/compass/"
            "2026-05-04-fix-timeout-error-message/delivery-approach.md",
            "| Verify | Light |",
            "names the Verify stage in the per-stage weight table, not the "
            "verb."),
        Exemption(
            "examples/quick-fix-typo/docs/compass/"
            "2026-05-04-fix-timeout-error-message/delivery-approach.md",
            "1 (at Verify)",
            "names the Verify stage, not the verb."),
        Exemption(
            "examples/quick-fix-typo/docs/compass/"
            "2026-05-04-fix-timeout-error-message/verification-note.md",
            "its Verify is light",
            "names the Verify stage, not the verb."),
        Exemption(
            "examples/spike-technical-unknown/docs/compass/"
            "2026-05-12-pdf-export-library-viability/delivery-approach.md",
            "| Verify | = **Conclude**",
            "names the Verify stage in the per-stage weight table, not the "
            "verb."),
        Exemption(
            "schemas/signals.schema.json",
            "reviewer agent at verify - judgement",
            "the JSON mirror of the already-exempted governance/signals.yml "
            "line above - names the Verify stage, not the verb."),
        Exemption(
            "templates/acceptance-criteria.md",
            "Passes as acceptance (verify)",
            "names the Verify stage in the coverage ledger's own column "
            "header, not the verb - every example's copy of this table is "
            "exempted the same way above."),
        Exemption(
            "templates/delivery-approach.md",
            "| Verify | {{gate count}}",
            "names the Verify stage in the per-stage weight table, not the "
            "verb."),
        Exemption(
            "templates/devlog.md",
            "Implement | Verify}}",
            "names the Verify stage in a placeholder list of stage names, "
            "not the verb."),
        Exemption(
            "templates/launch-readiness.md",
            "passed at Verify?",
            "names the Verify stage, not the verb."),
        Exemption(
            "templates/launch-readiness.md",
            "failed at Verify}}",
            "names the Verify stage, not the verb."),
        Exemption(
            "templates/verification-report.md",
            "the Verify output",
            "names the Verify stage, not the verb."),
        Exemption("governance/guardrails.md",
                   "Checked at Verify and again at ship time",
                   "names the Verify stage, not the verb."),
        Exemption("governance/guardrails.md",
                   "`verifier` and `reviewer` agents** at Verify",
                   "names the Verify stage, not the verb."),
        Exemption("governance/signals.yml",
                   "reviewer agent at Verify - judgement",
                   "names the Verify stage, not the verb."),
        Exemption("governance/guardrails.yml", "compass bdd verify",
                   "compass bdd verify is a CLI verb, not the plain verb."),
        Exemption("cli/compass_pkg/bdd.py", "and `compass bdd verify`",
                   "compass bdd verify is a CLI verb, not the plain verb."),
        Exemption("cli/compass_pkg/bdd.py", "compass bdd verify -- <run",
                   "compass bdd verify is a CLI verb, not the plain verb."),
        Exemption("cli/compass_pkg/checks.py", "written by `compass bdd verify`",
                   "compass bdd verify is a CLI verb, not the plain verb."),
        Exemption("tests/test_bdd_optin_noop.py", "compass bdd verify",
                   "compass bdd verify is a CLI verb, not the plain verb; "
                   "found while fixing batch 7, not by the audit."),
        Exemption("governance/guardrails.yml", "checked_at: [verify]",
                   "an example YAML value inside a comment, not the verb."),
        Exemption("governance/guardrails.yml", "attempts: <int>",
                   "attempts: <int> names the evidence field, not the verb "
                   "\"attempt\"."),
        # The first half of a hyphenated compound noun about a chain of
        # suppliers is not the plain verb the word table replaces with
        # "give". The exemption function does not check for a hyphen right
        # after the match.
        Exemption("architecture/decisions/ADR-013-vendored-third-party-code.md",
                   "it is a supply-chain",
                   "\"supply\" opens the compound noun \"supply-chain\", "
                   "not the verb."),
        # An id prefix (ADR-016) reuses the spelling of the plain verb the
        # word table replaces with "need". The match is the second half of
        # the hyphenated identifier, so the backtick before its first half
        # does not sit immediately before the match.
        Exemption("architecture/decisions/"
                   "ADR-016-id-codes-are-part-of-the-frozen-vocabulary.md",
                   "They become `RP-REQUIRE-*`",
                   "RP-REQUIRE is an id prefix, not the verb."),
        Exemption("architecture/decisions/"
                   "ADR-016-id-codes-are-part-of-the-frozen-vocabulary.md",
                   "define `RP-FLOOR` and `RP-REQUIRE` honestly",
                   "RP-REQUIRE is an id prefix, not the verb."),
        Exemption("architecture/decisions/README.md",
                   "RP-REQUIRE-001/002, verify.analyze",
                   "RP-REQUIRE is an id prefix, not the verb."),
        Exemption("architecture/system-context.md",
                   "added by `RP-REQUIRE-003` and `RP-REQUIRE-004`",
                   "RP-REQUIRE is an id prefix, not the verb."),
        Exemption("governance/routing-policy.yml",
                   "six of the entries below carry RP-REQUIRE ids",
                   "RP-REQUIRE is an id prefix, not the verb."),
        Exemption("governance/strategies-rationale.md",
                   "[RP-REQUIRE-003] requirement:",
                   "RP-REQUIRE is an id prefix, not the verb; this is a "
                   "quoted literal string a test matched."),
        Exemption("governance/terminology.yml",
                   "the result. RP-REQUIRE attaches a gate",
                   "RP-REQUIRE is an id prefix, not the verb."),
        Exemption("docs/glossary.md",
                   "the result. RP-REQUIRE attaches a gate",
                   "the derived text of the same terminology.yml line - "
                   "RP-REQUIRE is an id prefix, not the verb the word table "
                   "retires."),
        Exemption("tests/test_artifact_registry.py",
                   "`RP-REQUIRE-003` already adds",
                   "RP-REQUIRE-003 is a policy rule id, not the verb the "
                   "word table retires; found while fixing batch 7, not by "
                   "the audit."),
        Exemption("tests/test_allow_marker_needs_a_reason.py",
                   "(allow-marker-supplies-its-own-reason)",
                   "the issue's own slug, an identifier (section 4), not "
                   "the verb the word table retires; found while fixing "
                   "batch 7, not by the audit."),
        Exemption("tests/test_fresh_eyes_verify_sweeps.py",
                   "(issue fresh-eyes-verify-sweeps)",
                   "the issue's own slug, an identifier (section 4), not "
                   "the verb the word table retires; found while fixing "
                   "batch 7, not by the audit."),
        Exemption("tests/test_allow_marker_needs_a_reason.py",
                   "allow-marker-supplies-its-own-reason/acceptance-criteria.md",
                   "the issue's own slug, an identifier (section 4), not "
                   "the verb the word table retires; found while fixing "
                   "batch 7, not by the audit."),
        Exemption(
            "scripts/verify-archive-quotes.py",
            "verify against the primary",
            "restates strategy S9's own defining sentence "
            "(governance/strategies.md: 'Verify against the primary record "
            "for the claim'); the audit's human review ruled this instance "
            "keeps the word (section 9, batch 6, scripts/verify-archive-"
            "quotes.py note on L27-28)."),
        Exemption(
            "templates/architecture/relations.md",
            "A change that modifies a",
            "an absorbed-into marker quoting the merge-base sentence "
            "verbatim, per PBW-F7 - not a new use of the retired word."),
    ),
))


# ---------------------------------------------------------------------------
# PBW-A3 - the spelling is British
# ---------------------------------------------------------------------------

# Four named forms (audit 5.3), each with the British spelling it becomes.
# "analyse/analyze" needs its own exemption logic below - the verb
# `compass analyze`, the gate `verify.analyze` and the module `analyze.py`
# keep the American spelling because they are identifiers, not prose.
_SPELLING_PATTERNS: tuple[tuple[re.Pattern, str], ...] = (
    (re.compile(r"\btoward\b", re.IGNORECASE), "towards"),
    (re.compile(r"\bmodeling\b", re.IGNORECASE), "Modelling"),
    (re.compile(r"\blabeled\b", re.IGNORECASE), "labelled"),
)

_ANALYZE_RE = re.compile(r"\banalyz(e|es|ed|ing|ation|ations)\b", re.IGNORECASE)


def _analyze_exempt(text: str, match: re.Match) -> bool:
    start, end = match.span()
    before = text[max(0, start - 9):start]
    if before.rstrip().endswith("compass"):
        return True
    if text[start - 1:start] in "`/.":  # a code span, a slash command, or
        return True                     # the qualified gate id verify.analyze
    if text[end:end + 3] == ".py":
        return True
    return False


def _find_spelling(span: ProseSpan) -> list[Finding]:
    findings = []
    for pattern, replacement in _SPELLING_PATTERNS:
        for match in pattern.finditer(span.text):
            findings.append(Finding(
                span.path, span.line,
                f'"{match.group(0)}" -> "{replacement}"'))
    for match in _ANALYZE_RE.finditer(span.text):
        if _analyze_exempt(span.text, match):
            continue
        replacement = match.group(0).replace("z", "s")
        findings.append(Finding(
            span.path, span.line,
            f'"{match.group(0)}" -> "{replacement}"'))
    return findings


_register(Rule(
    "PBW-A3", "The spelling is British", _find_spelling,
    exemptions=(
        # The quoted title below is the real, external organisation's own
        # name (threatmodelingmanifesto.org), spelt with the American form in
        # its own title. Respelling it would misquote the name, the same
        # protection section 4 gives a verbatim quote or an identifier.
        Exemption("cli/compass_pkg/borrowed_docs.py",
                   "The threat model asks the Threat Modeling Manifesto's",
                   "the manifesto's own name, spelt as it spells itself; "
                   "not the ordinary word."),
        Exemption("cli/compass_pkg/borrowed_docs.py",
                   "The Threat Modeling Manifesto names the failure",
                   "the manifesto's own name, spelt as it spells itself; "
                   "not the ordinary word."),
        # An evidence-id prefix carries the gate's own American spelling as
        # a machine identifier, not the ordinary word it is spelt like. The
        # exemption function recognises a backtick right before the match,
        # but the backtick here opens two segments earlier, so the
        # identifier is not caught. Swapping the one lowercase letter that
        # separates the two spellings is a no-op in the all-caps form
        # (only a lowercase instance matches), which is why the sweep's own
        # reported replacement reads identical to the original.
        Exemption("architecture/decisions/"
                   "ADR-007-conditional-gate-promotion-via-floors.md",
                   "EV-ANALYZE-ADVISORY",
                   "evidence-id prefix, a machine identifier."),
        # Disagrees with the audit's finding for this line. The manifesto
        # this file quotes is the real, external body's own name, spelt
        # with the American form of the word - confirmed by the domain it
        # names two lines below, threatmodelingmanifesto.org, which uses
        # the same spelling. Changing the spelling would misname the source
        # the file instructs the reader not to reword.
        Exemption("templates/threat-model.md",
                   "Threat Modeling",
                   "the real name of the external manifesto this file "
                   "quotes, confirmed by threatmodelingmanifesto.org's own "
                   "spelling two lines below; not the ordinary word."),
        Exemption("cli/compass_pkg/analyze.py",
                   "id prefix `EV-ANALYZE-<task>-<ts>`",
                   "evidence-id prefix, a machine identifier - the same "
                   "class as the ADR-007 exemption above."),
        Exemption("cli/compass_pkg/analyze.py",
                   "id prefix `EV-ANALYZE-ADVISORY-<task>-<ts>`",
                   "evidence-id prefix, a machine identifier."),
        Exemption("cli/compass_pkg/analyze.py",
                   "Gate-clearing: type=consistency-check, prefix "
                   "EV-ANALYZE-<task>-<ts>",
                   "evidence-id prefix, a machine identifier."),
        Exemption("cli/compass_pkg/analyze.py",
                   "Advisory:      type=command-output,  prefix "
                   "EV-ANALYZE-ADVISORY-<task>-<ts>",
                   "evidence-id prefix, a machine identifier."),
        Exemption("cli/compass_pkg/analyze.py",
                   "--- command: analyze ---",
                   "names the CLI verb `compass analyze`, an identifier "
                   "(section 4 rule 1), not the ordinary word."),
        Exemption("cli/compass_pkg/receipt.py",
                   'is worse than a bare one: "EV-ANALYZE-signup-email-va...',
                   "evidence-id prefix, a machine identifier, inside a "
                   "worked example of a truncated one."),
        Exemption("cli/compass_pkg/receipt.py",
                   "`EV-ANALYZE-<slug>-<timestamp>` runs to 51 characters",
                   "evidence-id prefix, a machine identifier."),
    ),
))


# ---------------------------------------------------------------------------
# PBW-A4 - "artifact" is the only spelling
# ---------------------------------------------------------------------------

# The one exception to British English (audit section 7): "artifact" matches
# the manifest key `artifacts:`, the verb `compass issue artifact` and the
# evidence type `artifact`, so the prose is spelled to match the identifier.
_ARTEFACT_RE = re.compile(r"\bartefacts?\b", re.IGNORECASE)


def _find_artefact(span: ProseSpan) -> list[Finding]:
    return [Finding(span.path, span.line, f'"{match.group(0)}" -> "artifact"')
            for match in _ARTEFACT_RE.finditer(span.text)]


_register(Rule("PBW-A4", '"artifact" is the only spelling', _find_artefact))


# ---------------------------------------------------------------------------
# PBW-A5 - no idiom from the table survives
# ---------------------------------------------------------------------------

# The maintainer's global CLAUDE.md table (audit 5.5), one row per idiom.
# The row below for the sign-of-a-problem sense excludes the kept two-word
# form ("code" plus that word); the row for the goes-out-of-date sense
# carries no such exception - the audit's keep list does not name it.
IDIOM_TABLE: tuple[tuple[str, str], ...] = (
    ("full citizens", "fully supported, or name what they support"),
    ("backbone", "name the function or module everything else calls"),
    ("blast radius", "what a failure affects"),
    ("load-bearing", "name what depends on it"),
    ("escape hatch", "override, opt-out"),
    ("nudge", "prompt, remind"),
    ("knobs?", "setting, settings"),
    ("accretes", "adds"),
    ("substrate", "name the layer or file underneath"),
    ("stapled on", "added separately"),
    ("cry wolf", "report false failures"),
    ("belt and braces", "a second check"),
    ("front door", "entry point"),
    ("rubber stamp", "approval without a check"),
    ("theatre", "a check that catches nothing"),
    ("safety net", "name the check"),
    ("papercuts", "small irritations"),
    ("smell", "sign of a problem"),
    ("rots?", "goes out of date"),
    ("pay back the process weight", "do the follow-up work skipped earlier"),
    ("what's in the box", "what it contains"),
)

_IDIOM_PATTERNS: tuple[tuple[re.Pattern, str], ...] = tuple(
    (re.compile(r"\b" + pattern + r"\b", re.IGNORECASE), replacement)
    for pattern, replacement in IDIOM_TABLE
)


def _idiom_exempt(path: str, text: str, match: re.Match) -> bool:
    """"code smell" is the one kept phrase this table would otherwise flag -
    every other kept term (drift, stale, ratchet, in flight, lightweight) is
    simply absent from IDIOM_TABLE, so no pattern exists to exempt it from.
    One idiom-table entry names a retired v1 risk dimension too; inside
    architecture/decisions/ it is always the dimension name an accepted
    record was decided in (ADR-023), never the idiom, so it takes the same
    exemption PBW-A1 already gives that directory."""
    if match.group(0).lower() in ("smell", "smells"):
        before = text[:match.start()].rstrip().lower()
        if before.endswith("code"):
            return True
    if (match.group(0).lower() == "blast radius"
            and path.startswith(_ADR_VOCABULARY_SKIP)):
        return True
    return False


def _find_idiom(span: ProseSpan) -> list[Finding]:
    if span.path.startswith(_RETIRED_WORD_STRUCTURAL_SKIP):
        # tests/fixtures/terminology/ plants every banned word on purpose
        # (PBW-D2), and one of the retired assessment-dimension words is also
        # on the idiom table above - the same structural skip PBW-A1 uses
        # applies here for the same reason.
        return []
    if _in_terminology_exempt_block(span):
        # PBW-D2: the same four blocks that must keep naming every banned
        # word also carry idiom-table words as part of what they ban or
        # rename - an idiom this table replaces, quoted inside a `context:`
        # explaining why a word was retired.
        return []
    findings = []
    for pattern, replacement in _IDIOM_PATTERNS:
        for match in pattern.finditer(span.text):
            if _idiom_exempt(span.path, span.text, match):
                continue
            findings.append(Finding(
                span.path, span.line,
                f'"{match.group(0)}" -> {replacement}'))
    return findings


_register(Rule(
    "PBW-A5", "No idiom from the table survives", _find_idiom,
    exemptions=(
        Exemption(
            "skills/compass-runtime/writing-voice.md",
            '"papercuts" | "what the hell is papercuts?"',
            "the term is the subject of the row, not the prose: the table "
            "quotes the jargon a cold reader stumbled on so the row can "
            "show its plain form beside it (\"a list of small "
            "irritations\", already given). Replacing it would delete the "
            "example the section exists to show, and "
            "tests/test_reply_shape_instructions.py:125-152 requires the "
            "literal word on its row."),
        Exemption(
            "templates/requirements-review.md",
            "> a knob.",
            "an absorbed-into marker quoting the merge-base sentence "
            "verbatim, per PBW-F7 - not a new use of the retired idiom."),
    ),
))


# ---------------------------------------------------------------------------
# PBW-A6 - no citation points at a path git does not distribute
# ---------------------------------------------------------------------------

_CITATION_RE = re.compile(
    r"`?((?:docs/compass|\.compass/work)/[^\s`()\[\]]+)`?")


@lru_cache(maxsize=4096)
def _git_ignores(rel: str) -> bool:
    result = subprocess.run(["git", "check-ignore", "-q", rel], cwd=REPO_ROOT)
    return result.returncode == 0


def _find_citation(span: ProseSpan) -> list[Finding]:
    findings = []
    for match in _CITATION_RE.finditer(span.text):
        path = match.group(1).rstrip(".,;:'\"")
        if "<" in path or "*" in path:
            # A placeholder shape - the angle-bracket form
            # (docs/compass/<created>-<slug>/) or a shell-glob form
            # (.compass/work/*/) - names the convention, not one issue's
            # real document. A literal "*" is never a real filename, so
            # widening for it cannot mask a genuinely broken citation. git
            # check-ignore matches the literal string regardless, so this
            # is excluded rather than reported.
            continue
        if _git_ignores(path):
            findings.append(Finding(
                span.path, span.line,
                f'citation of "{path}", which git does not distribute'))
    return findings


_register(Rule(
    "PBW-A6", "No citation points at a path git does not distribute",
    _find_citation,
    exemptions=(
        Exemption(
            "docs/quickstart.md",
            ".compass/work/add-rate-limiting/manifest.yml",
            "the walkthrough's own hypothetical issue - it shows the "
            "reader where their own file will be, not a citation of a "
            "document that already exists in this repository"),
        # The citation regex matches from the compass-work segment onward,
        # so the placeholder "<x>" marker in the fuller path this comment
        # names sits before the match and is never captured; rstrip then
        # drops the trailing dots and the sweep is left checking a bare
        # compass-work directory path against git check-ignore, which is
        # true by construction: this is the .gitignore file defining that
        # very pattern two lines below.
        Exemption(
            ".gitignore",
            "examples/<x>/.compass/work/",
            "a placeholder path (the \"<x>\" marker sits before what the "
            "citation regex captures) explaining this file's own pattern, "
            "not a citation of a document a reader cannot open."),
        # A path relative to the README's own directory, the same PBW-A8 gap
        # named for these four files above: git check-ignore is asked about
        # the literal string against the repository root, where the root
        # .gitignore's `/docs/compass/*/` pattern matches it - even though
        # the real file, nested under examples/<adapter>/, is tracked.
        Exemption(
            "examples/bdd-adapters/behave/README.md",
            "docs/compass/2026-08-03-reset-password/acceptance-criteria.md",
            "a path relative to this README's own directory; the real "
            "file, examples/bdd-adapters/behave/docs/compass/2026-08-03-"
            "reset-password/acceptance-criteria.md, is tracked."),
        Exemption(
            "examples/bdd-adapters/cucumber-js/README.md",
            "docs/compass/2026-08-03-reset-password/acceptance-criteria.md",
            "the same directory-relative path as the behave README's "
            "exemption above."),
        Exemption(
            "examples/bdd-adapters/godog/README.md",
            "docs/compass/2026-08-03-reset-password/acceptance-criteria.md",
            "the same directory-relative path as the behave README's "
            "exemption above."),
        Exemption(
            "examples/bdd-adapters/pytest-bdd/README.md",
            "docs/compass/2026-08-03-reset-password/acceptance-criteria.md",
            "the same directory-relative path as the behave README's "
            "exemption above."),
        Exemption(
            "examples/bdd-adapters/pytest-bdd/README.md",
            ".compass/work/reset-password/acceptance-criteria.feature",
            "a path relative to this README's own directory; the real "
            "file is generated at run time under examples/bdd-adapters/"
            "pytest-bdd/.compass/work/reset-password/, the same shape as "
            "this rule's docs/quickstart.md exemption above."),
        Exemption(
            "tests/test_archive_citations_resolve.py",
            ".compass/work/demo/technical-design.md",
            "the comment quotes a fixture path a test builds "
            "(`make_task([...])`), not a citation of a real record; found "
            "while fixing batch 7, not by the audit."),
        Exemption(
            "tests/test_bdd_optin_noop.py",
            ".compass/work/, so running it here would fail",
            "names the gitignored directory generically, to explain why "
            "the test builds a synthetic project - not a citation of one "
            "document a reader cannot open; found while fixing batch 7, "
            "not by the audit."),
    ),
))


# ---------------------------------------------------------------------------
# PBW-A7 - a bare code carries its meaning or goes
# ---------------------------------------------------------------------------

_BARE_CODE_RE = re.compile(
    r"\b(?:G[1-5]|S\d+|TRC-\w+|DD-\d+|R\d+|MP-\d+|Inv-\d+|BR-\d+|AMB-\d+|"
    r"U-\d+|review finding \d+|probe \d+|slice \d+[a-z]?|Phase \d+)\b")

# architecture/decisions/README.md's Index and Principle-to-ADR tables are
# reference lookups keyed by id - the same shape as terminology.yml's own
# codes: section, where the code IS the row's key and its meaning sits in
# the adjacent cell. The "plain words, then the code in brackets" house
# form is a prose rule; a two-column table row is not prose in that sense,
# and every one of this rule's findings in this file is a table row.
_BARE_CODE_TABLE_SKIP = "architecture/decisions/README.md"


def _find_bare_code(span: ProseSpan) -> list[Finding]:
    if span.path == _BARE_CODE_TABLE_SKIP:
        return []
    findings = []
    for match in _BARE_CODE_RE.finditer(span.text):
        start = match.start()
        # Already in the house form - "the plain words (`G5`)" - or a
        # backticked cross-reference beside a rule already stated in full.
        if start > 0 and span.text[start - 1] in "(`":
            continue
        findings.append(Finding(
            span.path, span.line,
            f'bare code "{match.group(0)}" with no plain words beside it'))
    return findings


_register(Rule(
    "PBW-A7", "A bare code carries its meaning or goes", _find_bare_code,
    exemptions=(
        Exemption(
            "tests/test_frame_loads_architecture.py", "# noqa: S102",
            "a flake8 noqa suppression code (exec-builtin), not a "
            "strategy id; found while fixing batch 7, not by the audit."),
        Exemption(
            "architecture/decisions/ADR-017-an-identifier-is-a-key-not-jargon.md",
            "the G5 guard kicked in",
            "a verbatim quote of the bad phrasing the ADR exists to fix; "
            "explaining it would destroy the example."),
        Exemption(
            "architecture/decisions/ADR-017-an-identifier-is-a-key-not-jargon.md",
            "what a G5 guard was",
            "restates the same verbatim quote."),
        # The traceability id comment above every scenario is not prose a
        # reader loses meaning from - it is the machine-parsed marker
        # `cli/compass_pkg/bdd.py`'s extraction regex reads (bdd.py:137),
        # which needs the id to start immediately after the colon with no
        # backtick or other character in between. Wrapping it broke
        # `compass bdd extract`, caught by tests/test_bdd_adapters_all.py -
        # the marker is a real identifier (section 4), not a dangling
        # reference.
        Exemption(
            "templates/acceptance-criteria.md", "<!-- traceability id:",
            "the machine-parsed scenario-id marker `compass bdd extract` "
            "reads; see the comment above."),
        Exemption(
            "templates/ui-contract.md", "<!-- traceability id:",
            "the machine-parsed scenario-id marker `compass bdd extract` "
            "reads; see the comment above."),
        Exemption(
            "examples/bdd-adapters/behave/docs/compass/"
            "2026-08-03-reset-password/acceptance-criteria.md",
            "<!-- traceability id:",
            "the machine-parsed scenario-id marker `compass bdd extract` "
            "reads; see the comment above."),
        Exemption(
            "examples/bdd-adapters/cucumber-js/docs/compass/"
            "2026-08-03-reset-password/acceptance-criteria.md",
            "<!-- traceability id:",
            "the machine-parsed scenario-id marker `compass bdd extract` "
            "reads; see the comment above."),
        Exemption(
            "examples/bdd-adapters/godog/docs/compass/"
            "2026-08-03-reset-password/acceptance-criteria.md",
            "<!-- traceability id:",
            "the machine-parsed scenario-id marker `compass bdd extract` "
            "reads; see the comment above."),
        Exemption(
            "examples/bdd-adapters/pytest-bdd/docs/compass/"
            "2026-08-03-reset-password/acceptance-criteria.md",
            "<!-- traceability id:",
            "the machine-parsed scenario-id marker `compass bdd extract` "
            "reads; see the comment above."),
        Exemption(
            "examples/feature-api-change/docs/compass/"
            "2026-04-21-rate-limit-search-endpoint/acceptance-criteria.md",
            "<!-- traceability id:",
            "the machine-parsed scenario-id marker `compass bdd extract` "
            "reads; see the comment above."),
        Exemption(
            "examples/hotfix-regression/docs/compass/"
            "2026-05-11-search-crash-on-empty-filter/acceptance-criteria.md",
            "<!-- traceability id:",
            "the machine-parsed scenario-id marker `compass bdd extract` "
            "reads; see the comment above."),
        Exemption(
            "examples/initiative-new-subsystem/docs/compass/"
            "2026-03-02-notifications-subsystem/acceptance-criteria.md",
            "<!-- traceability id:",
            "the machine-parsed scenario-id marker `compass bdd extract` "
            "reads; see the comment above."),
        Exemption(
            "examples/quick-fix-typo/docs/compass/"
            "2026-05-04-fix-timeout-error-message/acceptance-criteria.md",
            "<!-- traceability id:",
            "the machine-parsed scenario-id marker `compass bdd extract` "
            "reads; see the comment above."),
        # That id's own meaning is not documented anywhere this sweep can
        # check, so it is quoted as originally written (test_pl_x3 in
        # tests/test_plain_language.py pins its presence) rather than
        # guessed at.
        Exemption(
            "architecture/decisions/ADR-015-the-vocabulary-scan-covers-code-positions.md",
            "`RCD-G5` needs that to be demonstrated",
            "RCD-G5's meaning is unverified; quoted as originally written, "
            "pinned by test_pl_x3."),
        Exemption(
            "architecture/decisions/ADR-015-the-vocabulary-scan-covers-code-positions.md",
            "mutation proof. `RCD-G5` needs the",
            "RCD-G5's meaning is unverified; quoted as originally written, "
            "pinned by test_pl_x3."),
        Exemption(
            "scripts/voice-tells.py", "TRC-F2",
            "found while building this sweep, not by the audit: the file is "
            "outside the audit's 474 files and outside every batch's "
            "pending list, so no batch owns the fix and this subtask cannot "
            "edit it (outside its own code surface). Filed separately as "
            "voice-tells-cites-trc-f2-with-no-plain-words."),
        Exemption(
            "docs/case-study-compass-rebuilt-itself.md",
            "--scenario TRC-G3",
            "the literal CLI command a person typed, inside backticks - "
            "rewording it to add plain words would misquote what was run"),
        Exemption(
            "examples/bdd-adapters/pytest-bdd/tests/steps/"
            "test_reset_password_steps.py",
            '-k TRC-A2',
            "a literal CLI command example, inside backticks - rewording it "
            "to add plain words would misquote the command."),
        Exemption(
            "examples/bdd-adapters/pytest-bdd/tests/steps/"
            "test_reset_password_steps.py",
            "--tags TRC-A2",
            "the same literal CLI command example, for a different runner."),
        Exemption(
            "examples/README.md", "--scenario TRC-001",
            "a literal CLI command example, inside backticks - rewording it "
            "to add plain words, or nesting a second backtick span inside "
            "it, would misquote the command."),
        Exemption(
            "examples/README.md", "evidence/green-TRC-001.json",
            "a literal filename example, inside backticks - the same "
            "reasoning as the CLI command exemption on this line."),
        Exemption(
            "templates/threat-model.md", "EV-T-TRC-B4",
            "a placeholder evidence id, inside backticks, built from the "
            "placeholder scenario id `TRC-B4` on the same row - not a real "
            "code pointing at meaning kept outside the file."),
        Exemption(
            "examples/quick-fix-typo/docs/compass/"
            "2026-05-04-fix-timeout-error-message/verification-note.md",
            "evidence/green-TRC-001.json",
            "the real evidence filename `compass tdd-green` wrote for this "
            "issue's one real scenario, inside backticks - nesting a "
            "second backtick span inside it would break the filename."),
        Exemption(
            "examples/quick-fix-typo/docs/compass/"
            "2026-05-04-fix-timeout-error-message/verification-note.md",
            "evidence/red-TRC-001.json",
            "the real evidence filename `compass tdd-red` wrote for this "
            "issue's one real scenario, inside backticks - nesting a "
            "second backtick span inside it would break the filename."),
        Exemption(
            "docs/quickstart.md", "`--scenario TRC-x`",
            "a placeholder scenario id, the same shape as `<test cmd>` "
            "elsewhere on this page - not a real code pointing at meaning "
            "kept outside the file"),
        Exemption(
            "templates/verification-report.md", "green-TRC-x.json",
            "the placeholder evidence filename `compass tdd-green` writes "
            "for a placeholder scenario id, the same shape as the "
            "docs/quickstart.md exemption above."),
        Exemption(
            "templates/devlog.md", "green-TRC-3.json",
            "the placeholder evidence filename `compass tdd-green` writes "
            "for a placeholder scenario id, the same shape as the "
            "docs/quickstart.md exemption above."),
        Exemption(
            "templates/manifest.yml", "TRC-001",
            "the one placeholder scenario id the file's five commented-out "
            "worked examples share (evidence, scenarios, changed_files, "
            "claims) - not a real code pointing at meaning kept outside "
            "the file, the same shape as the docs/quickstart.md exemption "
            "above."),
        Exemption(
            "tests/test_evidence_path_docs.py",
            "`compass tdd-green --scenario TRC-x` writes",
            "a placeholder scenario id, the same shape as the "
            "docs/quickstart.md exemption above; found while fixing batch "
            "7, not by the audit."),
        Exemption(
            "tests/test_evidence_path_docs.py",
            "writes `evidence/green-TRC-x.json`",
            "the placeholder filename the same placeholder scenario id "
            "produces; found while fixing batch 7, not by the audit."),
        Exemption(
            "governance/terminology.yml",
            "it prints 'G5 A human signs off",
            "a verbatim quote of `compass check`'s real printed output, "
            "itself the house-form example this ban describes."),
        Exemption(
            "templates/architecture/decisions/ADR-005-signals-yml-governance-file.md",
            "- Plan DD-1 (signals.yml as a separate file)",
            "an absorbed-into marker quoting the merge-base sentence "
            "verbatim, per PBW-F7 - the code is explained where it is "
            "used, not where this marker quotes it."),
        Exemption(
            "templates/architecture/relations.md",
            "(see TRC-B2).",
            "an absorbed-into marker quoting the merge-base sentence "
            "verbatim, per PBW-F7 - the code is explained where it is "
            "used (line 8, \"the scenario that added automatic "
            "triggering, `TRC-B2`\"), not where this marker quotes it."),
        Exemption(
            "cli/compass_pkg/analyze.py",
            "traceability id: TRC-A1",
            "a literal syntax example of the HTML comment the function "
            "parses, byte-identical to templates/acceptance-criteria.md's "
            "own example - not a pointer standing in for an explanation."),
        Exemption(
            "cli/compass_pkg/bdd.py",
            "traceability id: TRC-A1",
            "a literal syntax example of the HTML comment the extractor "
            "looks for, byte-identical to templates/acceptance-criteria.md's "
            "own example - not a pointer standing in for an explanation."),
        Exemption(
            "cli/compass_pkg/test_ids.py",
            "governance/strategies.md carries S7",
            "a worked example of a sentence that merely mentions a file, "
            "inside quotes - the point is that this text is prose, not a "
            "path reference, so S7 here names nothing and needs no meaning."),
        Exemption(
            "cli/compass_pkg/receipt.py",
            "Ids written by the CLI do (`EV-T-TRC-A1`)",
            "a real evidence-id shape this module itself generates and "
            "sorts on (`row[0].startswith(\"EV-T-\")` below) - not a "
            "dangling reference."),
    ),
))


# ---------------------------------------------------------------------------
# PBW-A8 - every file and command a comment names exists
# ---------------------------------------------------------------------------


# The first path segment may open with a single dot - `.compass/config.yml`
# is a real, hidden-directory path this repository has, not a relative-path
# marker, and the old pattern silently dropped the dot and checked the
# wrong (word-only) path for existence, reporting a false break on every
# reference to it. Later segments never carry a leading dot.
_REFERENCE_RE = re.compile(
    r"`?((?:[\w.][\w-]*/)+[\w.-]+\.(?:md|py|yml|yaml|json|sh|feature))`?")


def _reference_exempt(text: str, match: re.Match) -> bool:
    start = match.start()
    before = text[:start]
    # A URL - the path segment after the scheme is not repository-relative.
    return before.rstrip().endswith(("://", "http:", "https:")) or "://" in \
        text[max(0, start - 12):start]


@lru_cache(maxsize=1)
def _repo_top_level_names() -> frozenset[str]:
    """Every real top-level file or directory name, so a reference whose
    first segment is not one of these cannot be a repository-relative path
    at all."""
    return frozenset(p.name for p in REPO_ROOT.iterdir())


# The document names `<slug>/<document>.md` citations use (audit 5.7,
# commit 899d391) - a per-issue directory under the gitignored
# `docs/compass/`, cited by slug rather than by the path a reader's machine
# cannot open. Such a citation can never resolve in a shared tree by
# construction, so it is not the broken reference PBW-A8 exists to catch -
# `skills/compass-runtime/writing-voice.md`'s archive quotes cite six real
# past issues exactly this way.
_ISSUE_DOCUMENT_NAMES = frozenset({
    "intent.md", "acceptance-criteria.md", "requirements-review.md",
    "technical-design.md", "distribution-map.md", "manifest.yml",
    "delivery-approach.md", "verification-report.md", "devlog.md",
    "positioning.md", "launch-readiness.md", "ui-contract.md",
    "architecture-notes.md",
})


def _looks_like_issue_citation(path: str) -> bool:
    first_segment = path.split("/", 1)[0]
    document_name = path.rsplit("/", 1)[-1]
    return (first_segment not in _repo_top_level_names()
            and document_name in _ISSUE_DOCUMENT_NAMES)


def _looks_like_runtime_evidence(path: str) -> bool:
    """A path relative to the current issue's own `evidence/` directory
    (`.compass/work/<issue-slug>/evidence/...`, per `skills/compass-runtime/
    SKILL.md`'s "Where state lives" diagram) - written at run time, never
    committed at that bare location, so it is never on disk to find. A
    tracked example fixture's evidence lives nested under its own
    `.compass/work/<slug>/evidence/`, never at this top-level path, so the
    two cannot collide."""
    return path.split("/", 1)[0] == "evidence"


def _find_missing_reference(span: ProseSpan) -> list[Finding]:
    findings = []
    for match in _REFERENCE_RE.finditer(span.text):
        if _reference_exempt(span.text, match):
            continue
        path = match.group(1)
        if _looks_like_issue_citation(path) or _looks_like_runtime_evidence(path):
            continue
        if not (REPO_ROOT / path).exists():
            findings.append(Finding(
                span.path, span.line, f'named path "{path}" does not exist'))
    return findings


_register(Rule(
    "PBW-A8", "Every file and command a comment names exists",
    _find_missing_reference,
    exemptions=(
        Exemption(
            "docs/compass/2026-08-27-sdd-loop-spike.md", "obra/superpowers",
            "every path under obra/superpowers/ is inside the Superpowers "
            "repository, not this one - the file itself says so and gives "
            "the github.com URL each path resolves against"),
        # PBW-A8's reference sweep resolves every path against the repository
        # root. Each of the five worked examples under examples/ narrates a
        # fictional application change, naming source and test files that
        # belong to the STORY's application, not to this repository - the same
        # way a textbook's code listing names a file that exists only in the
        # chapter. None of the five examples ships the application source it
        # narrates; only the Compass documents (devlog, delivery-approach,
        # technical-design, and the rest) are real, tracked files.
        Exemption(
            "examples/feature-api-change/.compass/work/"
            "rate-limit-search-endpoint/devlog.md",
            "src/api/middleware/rate_limit.py",
            "the fictional application file the walkthrough narrates, not a "
            "file this repository ships."),
        Exemption(
            "examples/feature-api-change/.compass/work/"
            "rate-limit-search-endpoint/devlog.md",
            "src/api/routes/search.py",
            "the fictional application file the walkthrough narrates, not a "
            "file this repository ships."),
        Exemption(
            "examples/feature-api-change/.compass/work/"
            "rate-limit-search-endpoint/devlog.md",
            "src/api/config.py",
            "the fictional application file the walkthrough narrates, not a "
            "file this repository ships."),
        Exemption(
            "examples/feature-api-change/docs/compass/"
            "2026-04-21-rate-limit-search-endpoint/technical-design.md",
            "src/api/middleware/rate_limit.py",
            "the fictional application file the walkthrough narrates, not a "
            "file this repository ships."),
        Exemption(
            "examples/feature-api-change/docs/compass/"
            "2026-04-21-rate-limit-search-endpoint/technical-design.md",
            "src/api/routes/search.py",
            "the fictional application file the walkthrough narrates, not a "
            "file this repository ships."),
        Exemption(
            "examples/feature-api-change/docs/compass/"
            "2026-04-21-rate-limit-search-endpoint/technical-design.md",
            "src/api/config.py",
            "the fictional application file the walkthrough narrates, not a "
            "file this repository ships."),
        Exemption(
            "examples/hotfix-regression/.compass/work/"
            "search-crash-on-empty-filter/devlog.md",
            "src/api/search/filter_compiler.py",
            "the fictional application file the walkthrough narrates, not a "
            "file this repository ships."),
        Exemption(
            "examples/hotfix-regression/docs/compass/"
            "2026-05-11-search-crash-on-empty-filter/delivery-approach.md",
            "tests/api/test_search.py",
            "a path relative to this issue's own directory - it resolves "
            "at examples/hotfix-regression/tests/api/test_search.py, "
            "which is tracked; the sweep checks every path against the "
            "repository root, the same gap the bdd-adapters exemptions "
            "above name."),
        Exemption(
            "examples/hotfix-regression/docs/compass/"
            "2026-05-11-search-crash-on-empty-filter/verification-report.md",
            "src/api/search/filter_compiler.py",
            "the fictional application file the walkthrough narrates, not a "
            "file this repository ships."),
        Exemption(
            "examples/initiative-new-subsystem/docs/compass/"
            "2026-03-02-notifications-subsystem/distribution-map.md",
            "src/notifications/dispatch.py",
            "the fictional application file the walkthrough narrates, not a "
            "file this repository ships."),
        Exemption(
            "examples/initiative-new-subsystem/docs/compass/"
            "2026-03-02-notifications-subsystem/distribution-map.md",
            "src/notifications/preferences.py",
            "the fictional application file the walkthrough narrates, not a "
            "file this repository ships."),
        Exemption(
            "examples/initiative-new-subsystem/docs/compass/"
            "2026-03-02-notifications-subsystem/technical-design.md",
            "src/notifications/dispatch.py",
            "the fictional application file the walkthrough narrates, not a "
            "file this repository ships."),
        Exemption(
            "examples/initiative-new-subsystem/docs/compass/"
            "2026-03-02-notifications-subsystem/technical-design.md",
            "src/notifications/store.py",
            "the fictional application file the walkthrough narrates, not a "
            "file this repository ships."),
        Exemption(
            "examples/initiative-new-subsystem/docs/compass/"
            "2026-03-02-notifications-subsystem/technical-design.md",
            "src/notifications/api.py",
            "the fictional application file the walkthrough narrates, not a "
            "file this repository ships."),
        Exemption(
            "examples/initiative-new-subsystem/docs/compass/"
            "2026-03-02-notifications-subsystem/technical-design.md",
            "src/notifications/preferences.py",
            "the fictional application file the walkthrough narrates, not a "
            "file this repository ships."),
        Exemption(
            "examples/initiative-new-subsystem/docs/compass/"
            "2026-03-02-notifications-subsystem/verification-report.md",
            "tests/notifications/test_dispatch.py",
            "a path relative to this issue's own directory - it resolves "
            "at examples/initiative-new-subsystem/tests/notifications/"
            "test_dispatch.py, which is tracked."),
        Exemption(
            "examples/initiative-new-subsystem/docs/compass/"
            "2026-03-02-notifications-subsystem/verification-report.md",
            "tests/notifications/test_preferences.py",
            "a path relative to this issue's own directory - it resolves "
            "at examples/initiative-new-subsystem/tests/notifications/"
            "test_preferences.py, which is tracked."),
        Exemption(
            "examples/quick-fix-typo/.compass/work/"
            "fix-timeout-error-message/devlog.md",
            "src/api/upload.py",
            "the fictional application file the walkthrough narrates, not a "
            "file this repository ships."),
        Exemption(
            "examples/quick-fix-typo/docs/compass/"
            "2026-05-04-fix-timeout-error-message/delivery-approach.md",
            "src/api/upload.py",
            "the fictional application file the walkthrough narrates, not a "
            "file this repository ships."),
        Exemption(
            "examples/quick-fix-typo/docs/compass/"
            "2026-05-04-fix-timeout-error-message/verification-note.md",
            "tests/api/test_upload_errors.py",
            "a path relative to this issue's own directory - it resolves "
            "at examples/quick-fix-typo/tests/api/test_upload_errors.py, "
            "which is tracked."),
        Exemption(
            "examples/quick-fix-typo/docs/compass/"
            "2026-05-04-fix-timeout-error-message/verification-note.md",
            "src/api/upload.py",
            "the fictional application file the walkthrough narrates, not a "
            "file this repository ships."),
        Exemption(
            "docs/quickstart.md",
            ".compass/work/add-rate-limiting/manifest.yml",
            "the walkthrough's own hypothetical issue, not a real path in "
            "this repository - see the PBW-A6 exemption above for the "
            "same line"),
        Exemption(
            "tests/test_archive_citations_resolve.py",
            ".compass/work/demo/technical-design.md",
            "the comment quotes a fixture path a test builds, not a real "
            "path - see the PBW-A6 exemption above for the same line."),
        Exemption(
            "docs/quickstart.md", "evidence/green-TRC-x.json",
            "the filename `compass tdd-green` would write for the "
            "placeholder scenario id `TRC-x`, not a file this repository "
            "ships"),
        Exemption(
            "docs/quickstart.md", "evidence/green.json",
            "the filename `compass tdd-green` writes with no scenario "
            "bound, shown here as an example of the naming rule, not a "
            "file this repository ships"),
        Exemption(
            "agents/architect.md", "architecture/invariants.yml",
            "a real, conditional artifact a consuming project supplies - "
            "`cli/compass_pkg/core.py`'s `_INVARIANTS_FILE` reads it \"if "
            "present\", and `tests/test_frame_loads_architecture.py` "
            "exercises both the present and absent case. Compass's own "
            "architecture/ does not ship one, which is correct, not a "
            "broken reference."),
        Exemption(
            "agents/spec-author.md", "architecture/invariants.yml",
            "the same conditional artifact reference as agents/architect.md."),
        Exemption(
            "commands/consult.md", "architecture/invariants.yml",
            "the same conditional artifact reference as agents/architect.md."),
        Exemption(
            "templates/architecture/ownership.md", "architecture/invariants.yml",
            "the same conditional artifact reference as agents/architect.md."),
        Exemption(
            "templates/architecture/relations.md", "architecture/invariants.yml",
            "the same conditional artifact reference as agents/architect.md."),
        Exemption(
            "templates/manifest.yml", "tests/api/test_ledger_export.py",
            "the template's own worked example of a scenarios: entry, not a "
            "file this repository ships - the same shape as the "
            "docs/quickstart.md exemptions above."),
        Exemption(
            "templates/manifest.yml", "src/api/ledger_export.py",
            "the template's own worked example of a changed_files: entry, "
            "not a file this repository ships."),
        Exemption(
            "examples/bdd-adapters/behave/README.md",
            "docs/compass/2026-08-03-reset-password/acceptance-criteria.md",
            "a path relative to this README's own directory - it resolves "
            "at examples/bdd-adapters/behave/docs/compass/2026-08-03-"
            "reset-password/acceptance-criteria.md, which is tracked; the "
            "sweep checks every path against the repository root."),
        Exemption(
            "examples/bdd-adapters/behave/README.md",
            "features/steps/reset_password_steps.py",
            "a path relative to this README's own directory - it resolves "
            "at examples/bdd-adapters/behave/features/steps/"
            "reset_password_steps.py, which is tracked."),
        Exemption(
            "examples/bdd-adapters/cucumber-js/README.md",
            "docs/compass/2026-08-03-reset-password/acceptance-criteria.md",
            "the same directory-relative path as the behave README's "
            "exemption above; it resolves under this adapter's own "
            "docs/compass/2026-08-03-reset-password/."),
        Exemption(
            "examples/bdd-adapters/godog/README.md",
            "docs/compass/2026-08-03-reset-password/acceptance-criteria.md",
            "the same directory-relative path as the behave README's "
            "exemption above; it resolves under this adapter's own "
            "docs/compass/2026-08-03-reset-password/."),
        Exemption(
            "examples/bdd-adapters/pytest-bdd/README.md",
            "docs/compass/2026-08-03-reset-password/acceptance-criteria.md",
            "the same directory-relative path as the behave README's "
            "exemption above; it resolves under this adapter's own "
            "docs/compass/2026-08-03-reset-password/."),
        Exemption(
            "examples/bdd-adapters/pytest-bdd/README.md",
            ".compass/work/reset-password/acceptance-criteria.feature",
            "a path relative to this README's own directory - it resolves "
            "at examples/bdd-adapters/pytest-bdd/.compass/work/"
            "reset-password/acceptance-criteria.feature, which is "
            "generated at run time, the same shape as the runtime-evidence "
            "exemption this rule already carries for a bare evidence/ path."),
        Exemption(
            "examples/bdd-adapters/pytest-bdd/README.md",
            "tests/steps/test_reset_password_steps.py",
            "a path relative to this README's own directory - it resolves "
            "at examples/bdd-adapters/pytest-bdd/tests/steps/"
            "test_reset_password_steps.py, which is tracked."),
        Exemption(
            "tests/test_architect_lens.py", "architecture/invariants.yml",
            "the same conditional artifact reference as agents/architect.md; "
            "found while fixing batch 7, not by the audit."),
        Exemption(
            "tests/test_frame_loads_architecture.py", "architecture/invariants.yml",
            "the same conditional artifact reference as agents/architect.md; "
            "found while fixing batch 7, not by the audit."),
        # The reference regex needs a word character to open the first path
        # segment, so it drops the leading dot from a citation of a file
        # under a dotdir and then checks a path that was never meant to
        # exist at the repo root - the tracked file sits one character to
        # the left of what got checked. Found while building this sweep,
        # not by the audit: the same gap can fire on any dotdir citation
        # repository-wide, so it is filed separately as
        # writing-style-sweep-drops-the-leading-dot-on-a-dotdir-citation.
        Exemption("approaches/composition-reference.md",
                   ".compass/config.yml",
                   "the sweep drops the leading dot; the file is tracked."),
        Exemption("approaches/feature.md", ".compass/config.yml",
                   "the sweep drops the leading dot; the file is tracked."),
        Exemption("architecture/decisions/"
                   "ADR-011-enforced-file-types-are-project-configurable.md",
                   ".compass/config.yml",
                   "the sweep drops the leading dot; the file is tracked."),
        Exemption("governance/strategies.md", ".compass/config.yml",
                   "the sweep drops the leading dot; the file is tracked."),
        # test_anthropic_aligned_names.py's own module docstring is a "Was |
        # Is" rename table (ADR-023): the five retired .md filenames it names
        # in the "Was" column no longer exist by design, the same shape as
        # the ADR-019 stub references below. Found while fixing batch 7, not
        # by the audit.
        Exemption("tests/test_anthropic_aligned_names.py", "agents/navigator.md",
                   "the rename table's own retired filename; historical."),
        Exemption("tests/test_anthropic_aligned_names.py", "agents/product-lens.md",
                   "the rename table's own retired filename; historical."),
        Exemption("tests/test_anthropic_aligned_names.py", "agents/marketing-lens.md",
                   "the rename table's own retired filename; historical."),
        Exemption("tests/test_anthropic_aligned_names.py", "agents/architect-lens.md",
                   "the rename table's own retired filename; historical."),
        Exemption("tests/test_anthropic_aligned_names.py", "commands/roundtable.md",
                   "the rename table's own retired filename; historical."),
        # These two stub files existed only for the 3.x cycle and were
        # removed at the next major version, per this ADR's own rule - a
        # historical reference, not a stale one.
        Exemption("architecture/decisions/"
                   "ADR-019-retired-names-carry-redirects-once-there-are-adopters.md",
                   "commands/triage.md",
                   "historical: removed at the next major version, as this "
                   "ADR's own rule says."),
        Exemption("architecture/decisions/"
                   "ADR-019-retired-names-carry-redirects-once-there-are-adopters.md",
                   "commands/wireframe.md",
                   "historical: removed at the next major version, as this "
                   "ADR's own rule says."),
        # The retired narrative-guard test module is the file this ADR
        # decides to delete; every mention of it names the file being
        # retired, not a live reference.
        Exemption("architecture/decisions/"
                   "ADR-021-a-release-narrative-guard-retires-with-its-release.md",
                   "tests/test_v1_2_narrative.py",
                   "the file this ADR retires; the citation is historical."),
        # The manifest schema's pre-rename filename was the schema's name
        # before this ADR renamed it; the citation describes the pre-rename
        # state on purpose.
        Exemption("architecture/decisions/ADR-022-the-issue-record-is-a-manifest.md",
                   "schemas/task.schema.json",
                   "names the schema's pre-rename filename; historical."),
        # A per-issue relative filename convention inside
        # .compass/work/<issue>/, not a repo-root path - the reference
        # regex cannot tell the two apart, since both look like
        # "dir/file.ext".
        Exemption("architecture/decisions/ADR-005-state-lives-on-disk.md",
                   "evidence/green.json",
                   "names the per-issue evidence filename convention, not "
                   "a repo-root path."),
        Exemption("governance/guardrails.yml", "evidence/green.json",
                   "names the per-issue evidence filename convention, not "
                   "a repo-root path."),
        # A hypothetical example test in a commented-out sample entry - it
        # was never meant to exist.
        Exemption("governance/quarantine.yml",
                   "tests/api/test_export.py",
                   "a hypothetical example path in a commented-out sample."),
        Exemption("governance/strategies-rationale.md",
                   "tests/__pycache__/x.pyc",
                   "a hypothetical example path; the extension list stops "
                   "the match one character short of the real suffix."),
        Exemption("tests/test_docs_cite_live_tests.py",
                   "tests/test_v1_2_narrative.py",
                   "the retired test file this guard's own example names; "
                   "it does not exist on purpose - found while fixing "
                   "batch 7, not by the audit."),
        Exemption("tests/test_docs_cite_live_tests.py",
                   "tests/test_ledger_export.py",
                   "a worked-example path that was never meant to exist, "
                   "named by this file's own docstring as the contrast "
                   "case; found while fixing batch 7, not by the audit."),
        # A rejected alternative's hypothetical path - it does not exist
        # because the alternative was never built, which is the point of
        # naming it in the Alternatives table.
        Exemption("architecture/decisions/ADR-008-cross-task-derived-artifacts.md",
                   ".compass/cache/system-spec.json",
                   "a rejected alternative's hypothetical path; it was "
                   "never built."),
        # A pinned test in test_fresh_eyes_verify_sweeps.py needs this exact
        # path as the ADR-013 evidence trail's own citation, and the
        # sentence around it already says "not in this repository" - the
        # file was never meant to be tracked here.
        Exemption("governance/strategies-rationale.md",
                   "plain-language-3-2-0/technical-design.md",
                   "a pinned citation of another issue's document; the "
                   "sentence already says it is not in this repository."),
        # The regex this rule matches on starts at `[\w]`, so it cannot
        # include a leading `.` or `$`. Each entry below names a real
        # citation the regex mis-slices, found while fixing batch 6
        # (`scripts/` and `hooks/`); none is a broken reference in the text.
        Exemption(
            "hooks/post-tool.sh", "evidence/green.json",
            "a per-issue relative path under .compass/work/<issue>/evidence/, "
            "not a path this repository tracks."),
        Exemption(
            "hooks/post-tool.sh", "claude/settings.json",
            "the regex does not match a leading '.'; the real path is "
            ".claude/settings.json, an adopter's own settings file."),
        Exemption(
            "hooks/post-tool.sh", "CLAUDE_PROJECT_DIR/hooks/post-tool.sh",
            "the regex does not match a leading '$'; "
            "$CLAUDE_PROJECT_DIR/hooks/post-tool.sh is a real path once the "
            "shell variable expands."),
        Exemption(
            "hooks/pre-tool.sh", "evidence/red.json",
            "a per-issue relative path under .compass/work/<issue>/evidence/, "
            "not a path this repository tracks."),
        Exemption(
            "hooks/pre-tool.sh", "evidence/green.json",
            "a per-issue relative path under .compass/work/<issue>/evidence/, "
            "not a path this repository tracks."),
        Exemption(
            "hooks/pre-tool.sh", "claude/settings.json",
            "the regex does not match a leading '.'; the real path is "
            ".claude/settings.json, an adopter's own settings file."),
        Exemption(
            "hooks/pre-tool.sh", "CLAUDE_PROJECT_DIR/hooks/pre-tool.sh",
            "the regex does not match a leading '$'; "
            "$CLAUDE_PROJECT_DIR/hooks/pre-tool.sh is a real path once the "
            "shell variable expands."),
        Exemption(
            "hooks/pre-tool.sh", "src/app.py",
            "an illustrative example path in a comment, not a citation of a "
            "file in this repository."),
        Exemption(
            "hooks/pre-tool.sh", "compass/config.yml",
            "the regex does not match a leading '.'; the real path is "
            ".compass/config.yml, which is tracked."),
        Exemption(
            "hooks/pre-tool.sh", "github/workflows/ci.yml",
            "a generic illustrative filename pair (with docker-compose.yml), "
            "not a citation of a file in this repository; kept per the "
            "audit's own replacement text."),
        Exemption(
            "hooks/stop.sh", "claude/settings.json",
            "the regex does not match a leading '.'; the real path is "
            ".claude/settings.json, an adopter's own settings file."),
        Exemption(
            "hooks/stop.sh", "CLAUDE_PROJECT_DIR/hooks/stop.sh",
            "the regex does not match a leading '$'; "
            "$CLAUDE_PROJECT_DIR/hooks/stop.sh is a real path once the "
            "shell variable expands."),
        Exemption(
            "scripts/install.sh", "claude/settings.json",
            "the regex does not match a leading '.'; the real path is "
            ".claude/settings.json (or ~/.claude/settings.json), the "
            "install destination, not a path this repository tracks."),
        Exemption(
            "scripts/install.sh", "claude-plugin/plugin.json",
            "the regex does not match a leading '.'; the real path is "
            ".claude-plugin/plugin.json, which is tracked."),
        Exemption(
            "scripts/integrate.sh", "lib/compass-python.sh",
            "a shellcheck `source=` directive, resolved relative to the "
            "sourcing file's own directory (scripts/), not to the "
            "repository root; the real file is scripts/lib/compass-python.sh."),
        Exemption(
            "scripts/multiagent.sh", "compass/config.yml",
            "the regex does not match a leading '.'; the real path is "
            ".compass/config.yml, which is tracked."),
        Exemption(
            "scripts/multiagent.sh", "lib/compass-python.sh",
            "a shellcheck `source=` directive, resolved relative to the "
            "sourcing file's own directory (scripts/), not to the "
            "repository root; the real file is scripts/lib/compass-python.sh."),
        Exemption(
            "cli/compass_pkg/migrate.py", "commands/technical-design.md",
            "the path's non-existence is the point of the sentence - it "
            "names the wrong path a filename-only rewrite would produce, "
            "as a worked example of the bug this function avoids."),
    ),
))


# ---------------------------------------------------------------------------
# PBW-A9 - no sentence is left broken by an earlier find-and-replace
# ---------------------------------------------------------------------------

# Immediate repetition, allowing punctuation such as a bracket between the
# two occurrences - a word restated in brackets right after itself is this
# shape, one of the audit's own named passages (5.10).
_DOUBLED_WORD_RE = re.compile(r"\b(\w+)\b[\s(]+\1\b", re.IGNORECASE)

# The audit's own named passages (5.10) that a word-level check cannot see,
# because the repeated word is not adjacent to itself.
KNOWN_BROKEN_PHRASES: tuple[str, ...] = (
    "five roles read through five roles",
    "Architectural architecture checks",
    "agent multiagent",
    "delivery delivery approach",
)


def _find_doubled_word(span: ProseSpan) -> list[Finding]:
    findings = []
    for match in _DOUBLED_WORD_RE.finditer(span.text):
        findings.append(Finding(
            span.path, span.line, f'doubled text "{match.group(0)}"'))
    for phrase in KNOWN_BROKEN_PHRASES:
        if phrase.lower() in span.text.lower():
            findings.append(Finding(
                span.path, span.line, f'broken passage "{phrase}"'))
    return findings


_register(Rule(
    "PBW-A9", "No sentence is left broken by an earlier find-and-replace",
    _find_doubled_word,
    exemptions=(
        # The doubled-word pattern matches any repeated \w+ token, including
        # two adjacent numbers - a date immediately followed by a time whose
        # hour repeats the day is not a doubled English word, and rewording a
        # timestamp to dodge the pattern would be an edit for the sweep's own
        # convenience rather than for clarity.
        Exemption(
            "examples/hotfix-regression/.compass/work/"
            "search-crash-on-empty-filter/devlog.md",
            "2026-05-11 11:",
            "a date immediately followed by a time starting with the same "
            "number, not a doubled word."),
        Exemption(
            "examples/hotfix-regression/docs/compass/"
            "2026-05-11-search-crash-on-empty-filter/delivery-approach.md",
            "2026-05-11 11:",
            "a date immediately followed by a time starting with the same "
            "number, not a doubled word."),
    ),
))


# ---------------------------------------------------------------------------
# PBW-A10 - a stated count matches the thing it counts
# ---------------------------------------------------------------------------

_WORD_NUMBERS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
    "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
    "twenty": 20,
}


def _as_number(token: str) -> int | None:
    if token.isdigit():
        return int(token)
    return _WORD_NUMBERS.get(token.lower())


def _count_hooks() -> int:
    data = json.loads((REPO_ROOT / "hooks" / "hooks.json").read_text())
    commands = set()
    for entries in data["hooks"].values():
        for entry in entries:
            for hook in entry.get("hooks", []):
                commands.add(hook["command"].rsplit("/", 1)[-1])
    return len(commands)


def _count_releasing_version_locations() -> int:
    """The row count of step 1's own table - every `| ... | ... |` line
    between the header separator and the next blank line. Not every row
    opens with a backtick (the `docs/install-smoke-test.md` row opens with
    "The expected"), so the count is rows, not rows-that-start-with-code."""
    text = (REPO_ROOT / "docs" / "releasing.md").read_text()
    section = text.split("Bump the version", 1)[1].split("**And one more", 1)[0]
    rows = [line for line in section.splitlines()
            if line.strip().startswith("|") and "---" not in line]
    return len(rows) - 1  # the header row is not a location


def _count_methodology_commands() -> int:
    return len(list((REPO_ROOT / "commands").glob("*.md")))


def _count_terminology_exempt_files() -> int:
    """The file count the two path-PREFIX entries in `scan.exempt` hide
    between them - what the comment above that list calls "197 tracked
    files" (really 30). A single named file such as
    `templates/architecture/decisions/README.md` is a different kind of
    entry: it names one file rather than hiding a directory's worth, so it
    is not part of the count the comment is about."""
    tracked = set(_git_ls_files())
    total = 0
    for entry in yaml.safe_load(TERMINOLOGY_PATH.read_text())["scan"]["exempt"]:
        entry = str(entry)
        if entry in tracked:
            continue
        if entry.endswith("/"):
            total += len(subprocess.run(
                ["git", "ls-files", entry], cwd=REPO_ROOT,
                capture_output=True, text=True, check=True
            ).stdout.splitlines())
        else:
            directory, _, fragment = entry.rpartition("/")
            total += sum(1 for f in subprocess.run(
                ["git", "ls-files", directory + "/"], cwd=REPO_ROOT,
                capture_output=True, text=True, check=True
            ).stdout.splitlines() if fragment in f)
    return total


def _count_landed_by_relaxes() -> int:
    from compass_pkg import landed_by
    return len(landed_by.LANDED_BY_RELAXES)


def _count_add_parser_calls() -> int:
    text = (REPO_ROOT / "cli" / "compass").read_text()
    return len(re.findall(r"\badd_parser\(", text))


@dataclass(frozen=True)
class _CountClaim:
    name: str
    file: str
    pattern: re.Pattern
    source: Callable[[], int]


COUNT_REGISTRY: tuple[_CountClaim, ...] = (
    _CountClaim("hooks", "docs/quickstart.md",
                re.compile(r"\b(\w+)\s+hooks?\b", re.IGNORECASE), _count_hooks),
    _CountClaim("hooks", "docs/security.md",
                re.compile(r"\b(\w+)\s+hooks?\b", re.IGNORECASE), _count_hooks),
    _CountClaim("hooks", "docs/safety-contract.md",
                re.compile(r"\b(\w+)\s+hooks?\b", re.IGNORECASE), _count_hooks),
    _CountClaim("hooks", "docs/install-smoke-test.md",
                re.compile(r"\b(\w+)\s+hooks?\b", re.IGNORECASE), _count_hooks),
    _CountClaim("version locations", "docs/releasing.md",
                re.compile(r"\b(\w+)\s+version locations?\b", re.IGNORECASE),
                _count_releasing_version_locations),
    _CountClaim("primary user commands", "docs/methodology.md",
                re.compile(r"\b(\w+)\s+primary user commands?\b", re.IGNORECASE),
                _count_methodology_commands),
    _CountClaim("tracked files", "governance/terminology.yml",
                re.compile(r"\b(\w+)\s+tracked files?\b", re.IGNORECASE),
                _count_terminology_exempt_files),
    _CountClaim("relaxed checks", "cli/compass_pkg/landed_by.py",
                re.compile(r"\bexactly the (\w+)\b", re.IGNORECASE),
                _count_landed_by_relaxes),
    _CountClaim("add_parser calls", "cli/compass_pkg/terminal.py",
                re.compile(r"\b(\w+)\s*`?\s*add_parser`?\s*calls?\b",
                           re.IGNORECASE),
                _count_add_parser_calls),
)


# The files the registry already watches. A new counted claim inside one of
# THESE documents, about a thing the registry already tracks elsewhere in the
# same file, is scope creep the registry should have a row for. A mention of
# the same noun in a file the registry has never claimed - "the two hooks
# [that call this module]" in cli/compass_pkg/issue_layout.py, a different
# count of a different subset - is not: policing every noun the registry
# happens to share a word with, repository-wide, is the false-positive class
# `PBW-E3` warns against, not the drift `PBW-A10` exists to catch.
_REGISTRY_FILES = frozenset(row.file for row in COUNT_REGISTRY)


def _find_count_claim(span: ProseSpan) -> list[Finding]:
    if span.path not in _REGISTRY_FILES:
        return []
    findings = []
    # Several rows can share one pattern - four files all claim a hook count
    # with the identical "\b(\w+)\s+hooks?\b" regex. Matching every row against
    # every span would report this file's own correctly-registered claim as
    # belonging to the other three files' rows too. So: match each pattern at
    # most once per span, against the row registered for THIS file if one
    # exists, and only fall through to "no row for this file" when it does not.
    seen_patterns: set[re.Pattern] = set()
    for row in COUNT_REGISTRY:
        if row.pattern in seen_patterns:
            continue
        own_row = next(
            (r for r in COUNT_REGISTRY
             if r.pattern is row.pattern and r.file == span.path), None)
        for match in row.pattern.finditer(span.text):
            stated = _as_number(match.group(1))
            if stated is None:
                continue
            if own_row is None:
                findings.append(Finding(
                    span.path, span.line,
                    f'counted claim "{match.group(0)}" about "{row.name}" '
                    f'has no row in the registry for this file'))
                continue
            actual = own_row.source()
            if stated != actual:
                findings.append(Finding(
                    span.path, span.line,
                    f'"{match.group(0)}" states {stated}, the source counts '
                    f'{actual}'))
        seen_patterns.add(row.pattern)
    return findings


_register(Rule("PBW-A10", "A stated count matches the thing it counts",
               _find_count_claim))


# ---------------------------------------------------------------------------
# PBW-B7 - no document holds a changelog, a version banner or a dated count
# ---------------------------------------------------------------------------

_DATED_COUNT_RE = re.compile(
    r"\b\d+\s*(?:->|→)\s*\d+\s+on\s+\d{4}-\d{2}-\d{2}\b")
_CHANGELOG_HEADING_RE = re.compile(
    r"^#+\s*(Changelog|Version History|Revision History)\b", re.I | re.M)


def _find_changelog(span: ProseSpan) -> list[Finding]:
    findings = []
    for match in _DATED_COUNT_RE.finditer(span.text):
        findings.append(Finding(
            span.path, span.line, f'dated count history "{match.group(0)}"'))
    if _CHANGELOG_HEADING_RE.match(span.text):
        findings.append(Finding(
            span.path, span.line, f'changelog heading "{span.text.strip()}"'))
    return findings


_register(Rule("PBW-B7", "No document holds a changelog, a version banner "
               "or a dated count", _find_changelog))


# ---------------------------------------------------------------------------
# PBW-C3 - a CLI module's header describes that module
# ---------------------------------------------------------------------------

# The three literal markers the entry point's copied header carries into
# every module under cli/compass_pkg/ (audit 5.6): the banner naming
# cli/compass itself, the orphaned DoD-checklist-regex comment with no regex
# after it, and the rework-scan comment, which belongs only in rework.py.
_ENTRY_POINT_BANNER = "compass - the Compass CLI"
_DOD_REGEX_MARKER = "Regex to match a DoD checklist item"
_REWORK_SCAN_MARKER = "command: rework-scan"


def _find_cli_module_header(span: ProseSpan) -> list[Finding]:
    if span.path == "cli/compass":
        return []  # the entry point's own header describes itself
    if not span.path.startswith("cli/compass_pkg/"):
        return []
    findings = []
    if _ENTRY_POINT_BANNER in span.text:
        findings.append(Finding(
            span.path, span.line,
            "module header still describes the entry point"))
    if _DOD_REGEX_MARKER in span.text:
        findings.append(Finding(
            span.path, span.line,
            "orphaned DoD-checklist-regex comment, with no regex after it"))
    if _REWORK_SCAN_MARKER in span.text and span.path != "cli/compass_pkg/rework.py":
        findings.append(Finding(
            span.path, span.line,
            "rework-scan comment survives outside rework.py"))
    return findings


_register(Rule("PBW-C3", "A CLI module's header describes that module",
               _find_cli_module_header))


# ---------------------------------------------------------------------------
# PBW-C4 - a copied block is fixed the same way in every file that holds it
# ---------------------------------------------------------------------------

# The four blocks copied across test files (audit 5.6), matched by the
# distinctive phrase `git grep` finds each one by.
COPIED_BLOCK_MARKERS: tuple[str, ...] = (
    "vocabulary rename landed on 2026-08-25",
    "moved to --verbose",
    "moved next door",
    "only where they are looked for widened",
)


def _find_copied_block(span: ProseSpan) -> list[Finding]:
    if not span.path.startswith("tests/"):
        return []
    findings = []
    for marker in COPIED_BLOCK_MARKERS:
        if marker in span.text:
            findings.append(Finding(
                span.path, span.line, f'copied block "{marker}" survives'))
    return findings


_register(Rule("PBW-C4", "A copied block is fixed the same way in every "
               "file that holds it", _find_copied_block))


# ---------------------------------------------------------------------------
# PBW-C5 - a test docstring says what the file tests and cites its issue by
# slug
# ---------------------------------------------------------------------------

# The wrong form this rule refuses: docs/compass/<date>-<slug>/<doc>.md. The
# right form, <slug>/<doc>.md, has no docs/compass/ prefix and no date, so it
# never matches this pattern - nothing to exempt.
_OLD_STYLE_CITATION_RE = re.compile(
    r"\bdocs/compass/\d{4}-\d{2}-\d{2}-[\w-]+/[\w.-]+\b")


def _find_docstring_shape(span: ProseSpan) -> list[Finding]:
    if span.kind != "docstring" or not span.path.startswith("tests/"):
        return []
    findings = []
    for match in _OLD_STYLE_CITATION_RE.finditer(span.text):
        findings.append(Finding(
            span.path, span.line,
            f'citation "{match.group(0)}" is not in the <slug>/<document>.md '
            f'form'))
    for match in _BARE_CODE_RE.finditer(span.text):
        start = match.start()
        if start > 0 and span.text[start - 1] in "(`":
            continue
        findings.append(Finding(
            span.path, span.line,
            f'bare code "{match.group(0)}" with no plain words beside it'))
    return findings


_register(Rule("PBW-C5", "A test docstring says what the file tests and "
               "cites its issue by slug", _find_docstring_shape))


def test_pbw_a1_no_retired_word_in_prose_comments_or_docstrings():
    """The retired-word sweep is silent over every file not yet on a
    pending list. `PBW-A1`."""
    report = run_sweep(RULES["PBW-A1"], scanned_paths())
    assert not report.findings, report.render()
    assert report.files_scanned > 0


def test_pbw_a2_the_shorter_word_stands():
    """The word-table sweep is silent over every file not yet on a pending
    list. `PBW-A2`."""
    report = run_sweep(RULES["PBW-A2"], scanned_paths())
    assert not report.findings, report.render()
    assert report.files_scanned > 0


def test_pbw_a3_the_spelling_is_british():
    """The spelling sweep is silent over every file not yet on a pending
    list. `PBW-A3`."""
    report = run_sweep(RULES["PBW-A3"], scanned_paths())
    assert not report.findings, report.render()
    assert report.files_scanned > 0


def test_pbw_a4_artifact_is_the_only_spelling():
    """The spelling sweep reports no occurrence of the retired e-spelling.
    `PBW-A4`."""
    report = run_sweep(RULES["PBW-A4"], scanned_paths())
    assert not report.findings, report.render()
    assert report.files_scanned > 0


def test_pbw_a5_no_idiom_from_the_table():
    """The idiom sweep is silent over every file not yet on a pending list,
    and never fires on a kept term. `PBW-A5`."""
    report = run_sweep(RULES["PBW-A5"], scanned_paths())
    assert not report.findings, report.render()
    assert report.files_scanned > 0


def test_pbw_a6_no_citation_of_an_undistributed_path():
    """The citation sweep is silent over every file not yet on a pending
    list. `PBW-A6`."""
    report = run_sweep(RULES["PBW-A6"], scanned_paths())
    assert not report.findings, report.render()
    assert report.files_scanned > 0


def test_pbw_a7_a_bare_code_carries_its_meaning():
    """The bare-code sweep is silent over every file not yet on a pending
    list. `PBW-A7`."""
    report = run_sweep(RULES["PBW-A7"], scanned_paths())
    assert not report.findings, report.render()
    assert report.files_scanned > 0


def test_pbw_a8_every_named_file_and_command_exists():
    """The reference sweep is silent over every file not yet on a pending
    list. `PBW-A8`."""
    report = run_sweep(RULES["PBW-A8"], scanned_paths())
    assert not report.findings, report.render()
    assert report.files_scanned > 0


def test_pbw_a9_no_doubled_word_or_phrase():
    """The doubled-word sweep is silent over every file not yet on a
    pending list. `PBW-A9`."""
    report = run_sweep(RULES["PBW-A9"], scanned_paths())
    assert not report.findings, report.render()
    assert report.files_scanned > 0


def test_pbw_a10_a_stated_count_matches_its_source():
    """The count sweep is silent over every file not yet on a pending list -
    the registry's own claims are all in files pending at this stage.
    `PBW-A10`."""
    report = run_sweep(RULES["PBW-A10"], scanned_paths())
    assert not report.findings, report.render()
    assert report.files_scanned > 0


def test_pbw_b7_no_changelog_or_dated_count():
    """The changelog sweep is silent over every file not yet on a pending
    list. `PBW-B7`."""
    report = run_sweep(RULES["PBW-B7"], scanned_paths())
    assert not report.findings, report.render()
    assert report.files_scanned > 0


def test_pbw_c3_no_module_header_describes_the_entry_point():
    """The CLI-module-header sweep is silent over every module not yet on a
    pending list. `PBW-C3`."""
    report = run_sweep(RULES["PBW-C3"], scanned_paths())
    assert not report.findings, report.render()
    assert report.files_scanned > 0


def test_pbw_c4_no_copied_block_survives():
    """The copied-block sweep is silent over every file not yet on a
    pending list. `PBW-C4`."""
    report = run_sweep(RULES["PBW-C4"], scanned_paths())
    assert not report.findings, report.render()
    assert report.files_scanned > 0


def test_pbw_c5_a_docstring_states_its_behaviour_and_cites_by_slug():
    """The docstring-shape sweep is silent over every test file not yet on
    a pending list. `PBW-C5`."""
    report = run_sweep(RULES["PBW-C5"], scanned_paths())
    assert not report.findings, report.render()
    assert report.files_scanned > 0


def test_pbw_d2_no_ban_line_is_removed():
    """`governance/terminology.yml` still spells every word it bans, and the
    retired-word and idiom sweeps report nothing inside the `banned:` block
    or the terminology fixtures. `PBW-D2`."""
    terminology = yaml.safe_load(TERMINOLOGY_PATH.read_text(encoding="utf-8"))
    banned = terminology["banned"]
    assert banned, "the banned: block must not be emptied by this issue"
    for entry in banned:
        assert entry.get("term")
        assert entry.get("replacement")
        assert entry.get("context")
    # The retired-word rule's own structural skip is the mechanism: it never
    # reads governance/terminology.yml's banned: block (PROSE_KEYS does not
    # include `context`, `term` or `replacement`) or the terminology
    # fixtures, so both are naturally silent rather than exempted per-quote.
    fixture_dir = REPO_ROOT / "tests" / "fixtures" / "terminology"
    if fixture_dir.is_dir():
        fixture_paths = [REPO_ROOT / "tests" / "fixtures" / "terminology" / p.name
                          for p in fixture_dir.iterdir() if p.is_file()]
        report = run_sweep(RULES["PBW-A1"], fixture_paths)
        assert not report.findings, report.render()
        idiom_report = run_sweep(RULES["PBW-A5"], fixture_paths)
        assert not idiom_report.findings, idiom_report.render()


# ---------------------------------------------------------------------------
# PBW-E1, PBW-E2 - the sweeps can fail, and a zero is believed only after one
# ---------------------------------------------------------------------------

# Two rules are scoped to a specific real path (PBW-A10's registry, PBW-C3's
# cli/compass_pkg/ check) rather than to any file a fixture could live at, so
# their proof constructs the span directly instead of reading a fixture file.
# The text is the same text the matching fixture file states, so a reader
# checking the proof against the fixture sees the same breach either way.
_SYNTHETIC_BREACH_SPANS: dict[str, ProseSpan] = {
    "PBW-A10": ProseSpan(
        "docs/quickstart.md", 1,
        "Compass registers three hooks in this repository.", "markdown"),
    "PBW-C3": ProseSpan(
        "cli/compass_pkg/example.py", 3, "compass - the Compass CLI",
        "comment"),
}


def _fixture_spans_for(rule_id: str) -> list[ProseSpan]:
    if rule_id in _SYNTHETIC_BREACH_SPANS:
        return [_SYNTHETIC_BREACH_SPANS[rule_id]]
    matches = sorted(FIXTURE_DIR.glob(f"{rule_id.lower()}.*"))
    assert matches, f"no fixture file for {rule_id} under {FIXTURE_DIR}"
    return prose_spans(matches)


def test_pbw_e1_each_sweep_reports_a_planted_breach():
    """Every rule in `RULES` reports the breach planted for it, names the
    file and the line, and returns to silence once the breach is gone from
    the span it reads. `PBW-E1`."""
    proof: list[str] = []
    for rule_id, rule in sorted(RULES.items()):
        spans = _fixture_spans_for(rule_id)
        findings = [f for span in spans for f in rule.find(span)]
        assert findings, f"{rule_id} reported nothing over its own fixture"
        for finding in findings:
            assert finding.path and finding.line
        proof.append(f"{rule_id}: reported {len(findings)} over "
                     f"{[s.path for s in spans][0]}")
        # Silence on return: a span with the reported text removed is clean.
        for span in spans:
            span_findings = rule.find(span)
            if not span_findings:
                continue
            cleaned = ProseSpan(span.path, span.line, "", span.kind)
            assert not rule.find(cleaned), (
                f"{rule_id} still reports a blanked span - the pattern is "
                f"not reading the text it claims to")
    assert len(proof) == len(RULES) == 14, "\n".join(proof)


def test_pbw_e2_each_sweep_reports_the_files_it_scanned():
    """Every `Report` carries the number of files it scanned, so a zero from
    an empty file set reads differently from a zero from clean prose.
    `PBW-E2`."""
    for rule in RULES.values():
        empty_report = run_sweep(rule, [])
        assert empty_report.files_scanned == 0
        assert not empty_report.findings
        real_report = run_sweep(rule, scanned_paths())
        assert real_report.files_scanned > 0
        assert real_report.files_scanned == len(scanned_paths())


def test_pbw_e3_every_exemption_names_a_file_and_a_reason():
    """Every exemption on every rule names the file, the quote and the
    reason - a widened pattern is not how a sweep clears a report.
    `PBW-E3`."""
    total = 0
    for rule in RULES.values():
        for exemption in rule.exemptions:
            total += 1
            assert exemption.path, f"{rule.id} exemption has no path"
            assert exemption.quote, f"{rule.id} exemption has no quote"
            assert len(exemption.reason) > 20, (
                f"{rule.id} exemption for {exemption.path} gives no real "
                f"reason")
    assert total >= 1, "at least the PBW-A7 exemption should exist by now"


# ---------------------------------------------------------------------------
# PBW-E4 - no changed file's behaviour changes
# ---------------------------------------------------------------------------

COMPARE_BEHAVIOUR = REPO_ROOT / "scripts" / "compare-behaviour.py"


def _sandbox_repo(tmp_path) -> Path:
    repo = tmp_path / "sandbox"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True)
    return repo


def _commit(repo: Path, message: str) -> None:
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", message], cwd=repo, check=True)


def _run_compare(repo: Path, base: str, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["python3", str(COMPARE_BEHAVIOUR), "--base", base, *extra],
        cwd=repo, capture_output=True, text=True)


def test_pbw_e4_the_behaviour_comparison_reports_a_planted_change(tmp_path):
    """`scripts/compare-behaviour.py` exits non-zero on a body change, exits
    0 on a docstring-only change, catches a changed printed string in a
    shell script, and still refuses a test file's behaviour change even
    when `--allow-pinned-test` names a different path. `PBW-E4`."""
    repo = _sandbox_repo(tmp_path)

    # Case 1: a docstring-only change in a Python file - exit 0.
    (repo / "mod.py").write_text('"""Old docstring."""\n\n\ndef f():\n    return 1\n')
    _commit(repo, "base")
    base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo,
                           capture_output=True, text=True, check=True).stdout.strip()
    (repo / "mod.py").write_text('"""New docstring, rewritten."""\n\n\ndef f():\n    return 1\n')
    _commit(repo, "docstring only")
    result = _run_compare(repo, base)
    assert result.returncode == 0, result.stdout + result.stderr

    # Case 2: a one-line body change plus a docstring rewrite - exit
    # non-zero, naming the file.
    (repo / "mod.py").write_text('"""Newer docstring."""\n\n\ndef f():\n    return 2\n')
    _commit(repo, "body change")
    result = _run_compare(repo, base)
    assert result.returncode != 0
    assert "mod.py" in result.stdout

    # Case 3: a changed printed string in a shell script - exit non-zero.
    (repo / "say.sh").write_text('#!/bin/sh\n# a comment\necho "old"\n')
    _commit(repo, "shell base")
    base2 = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo,
                            capture_output=True, text=True, check=True).stdout.strip()
    (repo / "say.sh").write_text('#!/bin/sh\n# a comment, reworded\necho "new"\n')
    _commit(repo, "shell changed")
    result = _run_compare(repo, base2)
    assert result.returncode != 0
    assert "say.sh" in result.stdout

    # Case 4: a behaviour change in a test file not named by
    # --allow-pinned-test - still refused.
    (repo / "tests").mkdir(exist_ok=True)
    (repo / "tests" / "test_thing.py").write_text(
        '"""Doc."""\n\n\ndef test_x():\n    assert 1 == 1\n')
    _commit(repo, "test base")
    base3 = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo,
                            capture_output=True, text=True, check=True).stdout.strip()
    (repo / "tests" / "test_thing.py").write_text(
        '"""Doc, reworded."""\n\n\ndef test_x():\n    assert 2 == 2\n')
    _commit(repo, "test pin changed")
    result = _run_compare(
        repo, base3, "--allow-pinned-test",
        "tests/test_other.py=a different file, named to show the allowance "
        "is per path")
    assert result.returncode != 0
    assert "test_thing.py" in result.stdout

    # A path outside tests/ passed to --allow-pinned-test is refused.
    result = _run_compare(repo, base3, "--allow-pinned-test",
                           "src/mod.py=a stated reason does not help here")
    assert result.returncode != 0


def test_pbw_e4_a_comment_only_rewrite_that_moves_line_counts_is_not_a_change(
        tmp_path):
    """A comment-only edit that changes how many lines a comment block
    occupies exits 0, in shell and in YAML, and a real change in either still
    exits non-zero. `PBW-E4`.

    This is the shape that made the tool useless on batch 6: a stripper that
    replaces a comment with an empty line keeps one line per input line, so
    rewrapping a comment block changed the number of empty lines and the
    joined text differed with no command line changed. Nearly every rewrite
    this issue makes moves a comment's line count, so a tool that reports it
    reports on almost every batch.

    Markdown and JSON are covered here too. Neither can carry the defect -
    the markdown reader collects fenced lines and link targets rather than
    blanking prose, and the JSON reader compares parsed structures - and the
    two cases record that rather than leaving a later reader to re-derive it.
    """
    repo = _sandbox_repo(tmp_path)

    def _base() -> str:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo,
                               capture_output=True, text=True,
                               check=True).stdout.strip()

    # Case 1: a shell comment block of three lines becomes one, and every
    # command line is byte-identical - exit 0.
    (repo / "run.sh").write_text(
        '#!/bin/sh\n# one\n# two\n# three\necho "x"\n')
    _commit(repo, "shell base")
    base = _base()
    (repo / "run.sh").write_text(
        '#!/bin/sh\n# one, two and three, said once\necho "x"\n')
    _commit(repo, "shell comment rewrapped")
    result = _run_compare(repo, base)
    assert result.returncode == 0, result.stdout + result.stderr

    # Case 2: the same rewrap, plus a real command change - exit non-zero.
    (repo / "run.sh").write_text(
        '#!/bin/sh\n# one, two and three\n# said over two lines now\necho "y"\n')
    _commit(repo, "shell command changed too")
    result = _run_compare(repo, base)
    assert result.returncode != 0
    assert "run.sh" in result.stdout

    # Case 3: an extensionless shell script takes the same path.
    (repo / "hook").write_text('#!/bin/sh\n# a\n# b\nexit 0\n')
    _commit(repo, "hook base")
    base = _base()
    (repo / "hook").write_text('#!/bin/sh\n# a and b\nexit 0\n')
    _commit(repo, "hook comment rewrapped")
    result = _run_compare(repo, base)
    assert result.returncode == 0, result.stdout + result.stderr

    # Case 4: a YAML whole-line comment reworded over a different number of
    # lines, with no value touched - exit 0.
    (repo / "conf.yml").write_text(
        "# the old note\n# spread over two lines\nthreshold: 5\n")
    _commit(repo, "yaml base")
    base = _base()
    (repo / "conf.yml").write_text(
        "# the new note, said on one line\nthreshold: 5\n")
    _commit(repo, "yaml comment rewrapped")
    result = _run_compare(repo, base)
    assert result.returncode == 0, result.stdout + result.stderr

    # Case 5: a YAML trailing comment reworded, with no value touched -
    # exit 0.
    (repo / "conf.yml").write_text("threshold: 5  # the old note\n")
    _commit(repo, "yaml trailing base")
    base = _base()
    (repo / "conf.yml").write_text("threshold: 5  # a rather longer note\n")
    _commit(repo, "yaml trailing comment reworded")
    result = _run_compare(repo, base)
    assert result.returncode == 0, result.stdout + result.stderr

    # Case 6: a real YAML value change, with the comment reworded too - exit
    # non-zero. The fix must not buy exit 0 by going blind.
    (repo / "conf.yml").write_text("threshold: 6  # a different note again\n")
    _commit(repo, "yaml value changed")
    result = _run_compare(repo, base)
    assert result.returncode != 0
    assert "conf.yml" in result.stdout

    # Case 7: a YAML prose value whose line count changes - exit 0. The key
    # is in PROSE_KEYS, so its value is prose by the same list the sweeps use.
    (repo / "prose.yml").write_text(
        "description: >\n  one\n  two\nthreshold: 5\n")
    _commit(repo, "yaml prose base")
    base = _base()
    (repo / "prose.yml").write_text(
        "description: >\n  one two\nthreshold: 5\n")
    _commit(repo, "yaml prose rewrapped")
    result = _run_compare(repo, base)
    assert result.returncode == 0, result.stdout + result.stderr

    # Case 8: markdown prose rewritten around an unchanged fenced block -
    # exit 0, and a changed fenced block still exits non-zero.
    (repo / "doc.md").write_text(
        "Old prose.\n\nMore old prose.\n\n```sh\necho hi\n```\n")
    _commit(repo, "md base")
    base = _base()
    (repo / "doc.md").write_text("New prose, shorter.\n\n```sh\necho hi\n```\n")
    _commit(repo, "md prose only")
    result = _run_compare(repo, base)
    assert result.returncode == 0, result.stdout + result.stderr
    (repo / "doc.md").write_text("New prose.\n\n```sh\necho bye\n```\n")
    _commit(repo, "md fence changed")
    result = _run_compare(repo, base)
    assert result.returncode != 0
    assert "doc.md" in result.stdout

    # Case 9: a JSON description reworded and the file reformatted - exit 0,
    # and a changed non-description value still exits non-zero.
    (repo / "data.json").write_text('{"description": "old words", "n": 1}')
    _commit(repo, "json base")
    base = _base()
    (repo / "data.json").write_text(
        '{\n  "description": "new and rather longer words",\n  "n": 1\n}')
    _commit(repo, "json description only")
    result = _run_compare(repo, base)
    assert result.returncode == 0, result.stdout + result.stderr
    (repo / "data.json").write_text('{"description": "new words", "n": 2}')
    _commit(repo, "json value changed")
    result = _run_compare(repo, base)
    assert result.returncode != 0
    assert "data.json" in result.stdout


def test_pbw_e4_a_quoted_hash_is_not_a_comment(tmp_path):
    """A `#` inside a quoted shell string is part of the command, so a change
    after it is reported. A real trailing comment is still stripped. `PBW-E4`.

    This was a false negative in the one tool whose purpose is proving that
    no behaviour changed: the comment stripper matched ` #` anywhere outside
    a comment's own syntax, so `echo "tag #alpha"` was cut to `echo "tag` and
    a change to the part after the hash compared equal. The direction matters
    more than the count - over-reporting costs a second look, while this
    missed the change the tool is run to catch.
    """
    repo = _sandbox_repo(tmp_path)

    def _base() -> str:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo,
                               capture_output=True, text=True,
                               check=True).stdout.strip()

    # Case 1: a double-quoted hash, with the change after it - reported.
    (repo / "a.sh").write_text('#!/bin/sh\necho "tag #alpha"\n')
    _commit(repo, "quoted hash base")
    base = _base()
    (repo / "a.sh").write_text('#!/bin/sh\necho "tag #beta"\n')
    _commit(repo, "quoted hash changed")
    result = _run_compare(repo, base)
    assert result.returncode != 0, result.stdout + result.stderr
    assert "a.sh" in result.stdout

    # Case 2: a hash inside a sed substitution - reported.
    (repo / "b.sh").write_text('#!/bin/sh\nsed -i "s/ #a/ #b/" f\n')
    _commit(repo, "sed base")
    base = _base()
    (repo / "b.sh").write_text('#!/bin/sh\nsed -i "s/ #a/ #c/" f\n')
    _commit(repo, "sed changed")
    result = _run_compare(repo, base)
    assert result.returncode != 0, result.stdout + result.stderr
    assert "b.sh" in result.stdout

    # Case 3: a single-quoted hash - reported.
    (repo / "c.sh").write_text("#!/bin/sh\necho 'tag #alpha'\n")
    _commit(repo, "single quote base")
    base = _base()
    (repo / "c.sh").write_text("#!/bin/sh\necho 'tag #beta'\n")
    _commit(repo, "single quote changed")
    result = _run_compare(repo, base)
    assert result.returncode != 0, result.stdout + result.stderr

    # Case 4: `$#` and `${#var}` are shell parameters, not comments - a
    # change to the line is reported.
    (repo / "d.sh").write_text('#!/bin/sh\necho "$# args ${#PATH} chars"\n')
    _commit(repo, "param base")
    base = _base()
    (repo / "d.sh").write_text('#!/bin/sh\necho "$# args ${#HOME} chars"\n')
    _commit(repo, "param changed")
    result = _run_compare(repo, base)
    assert result.returncode != 0, result.stdout + result.stderr

    # Case 5: the fix must not over-correct. A genuine trailing comment,
    # reworded over a different length, is still stripped - exit 0. A
    # quoted hash on the same line stays part of the command.
    (repo / "e.sh").write_text(
        '#!/bin/sh\necho "tag #alpha"  # what this line does\n')
    _commit(repo, "trailing comment base")
    base = _base()
    (repo / "e.sh").write_text(
        '#!/bin/sh\necho "tag #alpha"  # a much longer note about the line\n')
    _commit(repo, "trailing comment reworded")
    result = _run_compare(repo, base)
    assert result.returncode == 0, result.stdout + result.stderr

    # Case 6: an escaped hash outside quotes is part of the command.
    (repo / "f.sh").write_text('#!/bin/sh\nprintf %s a\\#alpha\n')
    _commit(repo, "escaped base")
    base = _base()
    (repo / "f.sh").write_text('#!/bin/sh\nprintf %s a\\#beta\n')
    _commit(repo, "escaped changed")
    result = _run_compare(repo, base)
    assert result.returncode != 0, result.stdout + result.stderr


def test_pbw_e4_an_extensionless_file_is_read_by_its_shebang(tmp_path):
    """A file with no extension is dispatched on its shebang, so
    `#!/usr/bin/env python3` is read as Python and not as shell. `PBW-E4`.

    `cli/compass` is Python with a shebang and no extension, so the suffix
    test sent it to the shell reader. Batch 5 hit the false positive - "a
    command line changed" for a docstring rewrite - and checked the syntax
    trees by hand to prove nothing moved. The worse half is the other
    direction: a real change to a Python body in an extensionless entry point
    would be judged by a reader that cannot see a Python body at all, and
    would pass. `cli/compass` is the command every adopter runs.
    """
    repo = _sandbox_repo(tmp_path)

    def _base() -> str:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo,
                               capture_output=True, text=True,
                               check=True).stdout.strip()

    # Case 1: an extensionless Python entry point, docstring only - exit 0.
    # The shell reader would see the changed line and report it.
    (repo / "entry").write_text(
        '#!/usr/bin/env python3\n"""Old summary."""\n\n\ndef f():\n    return 1\n')
    _commit(repo, "python entry base")
    base = _base()
    (repo / "entry").write_text(
        '#!/usr/bin/env python3\n"""New summary, rewritten at length."""\n'
        '\n\ndef f():\n    return 1\n')
    _commit(repo, "python entry docstring only")
    result = _run_compare(repo, base)
    assert result.returncode == 0, result.stdout + result.stderr

    # Case 2: the same file, a changed statement - reported. This is the
    # direction the shell reader could not see.
    (repo / "entry").write_text(
        '#!/usr/bin/env python3\n"""New summary, rewritten at length."""\n'
        '\n\ndef f():\n    return 2\n')
    _commit(repo, "python entry body changed")
    result = _run_compare(repo, base)
    assert result.returncode != 0, result.stdout + result.stderr
    assert "entry" in result.stdout

    # Case 3: an extensionless bash entry point keeps the shell reader -
    # bin/compass's shape. A rewrapped comment block is not a change.
    (repo / "shim").write_text(
        '#!/usr/bin/env bash\n# one\n# two\nexec echo hi\n')
    _commit(repo, "bash shim base")
    base = _base()
    (repo / "shim").write_text(
        '#!/usr/bin/env bash\n# one and two, said once\nexec echo hi\n')
    _commit(repo, "bash shim comment rewrapped")
    result = _run_compare(repo, base)
    assert result.returncode == 0, result.stdout + result.stderr

    # Case 4: the same bash file, a changed command - reported.
    (repo / "shim").write_text(
        '#!/usr/bin/env bash\n# one and two\nexec echo bye\n')
    _commit(repo, "bash shim command changed")
    result = _run_compare(repo, base)
    assert result.returncode != 0, result.stdout + result.stderr

    # Case 5: a python3 shebang without `env`, and a bare `#!/bin/sh`.
    (repo / "direct").write_text(
        '#!/usr/bin/python3\n"""Doc."""\nx = 1\n')
    (repo / "posix").write_text('#!/bin/sh\n# note\necho hi\n')
    _commit(repo, "other shebang forms base")
    base = _base()
    (repo / "direct").write_text(
        '#!/usr/bin/python3\n"""Doc, reworded."""\nx = 1\n')
    (repo / "posix").write_text('#!/bin/sh\n# a different note\necho hi\n')
    _commit(repo, "other shebang forms, prose only")
    result = _run_compare(repo, base)
    assert result.returncode == 0, result.stdout + result.stderr

    # Case 6: no extension and no shebang falls back to the shell reader,
    # which is what this repository's VERSION, Makefile, CODEOWNERS and
    # examples/.../current-task files need. A changed line is still reported.
    (repo / "VERSION").write_text("4.0.1\n")
    _commit(repo, "data file base")
    base = _base()
    (repo / "VERSION").write_text("4.0.2\n")
    _commit(repo, "data file changed")
    result = _run_compare(repo, base)
    assert result.returncode != 0, result.stdout + result.stderr

    # Case 7: the false negative that made this worth fixing, rather than the
    # false positive that revealed it. The shell reader drops blank lines and
    # trailing whitespace, because neither carries behaviour in shell. Both
    # are content inside a Python string, so a change to printed text was
    # invisible. `cli/compass` holds four multi-line string constants, so this
    # was reachable in the command every adopter runs.
    (repo / "helptext").write_text(
        '#!/usr/bin/env python3\nBANNER = """line one\nline two\n"""\n')
    _commit(repo, "help text base")
    base = _base()
    (repo / "helptext").write_text(
        '#!/usr/bin/env python3\nBANNER = """line one\n\nline two\n"""\n')
    _commit(repo, "a blank line added to printed help text")
    result = _run_compare(repo, base)
    assert result.returncode != 0, (
        "a blank line inside a Python string constant changes what the "
        "command prints, and the shell reader could not see it:\n"
        + result.stdout + result.stderr)


def test_pbw_e4_a_prose_sequence_item_is_blanked_but_still_counted(tmp_path):
    """A prose sequence item under a `PROSE_KEYS` key can be reworded and
    rewrapped freely, but adding or removing one is reported. `PBW-E4`.

    `governance/routing-policy.yml`'s `biases:` holds free-text tie-breakers,
    and its own comment says they are not machine-evaluated. The reader
    blanked only scalar values, so batch 3 could not prove a rewording of them
    safe and correctly left the findings unfixed in a shipped governance file.

    Each item collapses to one marker rather than the whole list collapsing to
    one, so the item count is still compared. Rewording is prose; deleting a
    tie-breaker is not, and a reader would never see it go.
    """
    repo = _sandbox_repo(tmp_path)

    def _base() -> str:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo,
                               capture_output=True, text=True,
                               check=True).stdout.strip()

    three = (
        "policy:\n"
        "  biases:\n"
        '    - "When size is unclear, estimate up - collapsing an easy\n'
        '       phase is cheaper than discovering it mid-Build."\n'
        '    - "A non-engineering role usually pulls the route heavier."\n'
        '    - "Prefer the lightest route that still clears every guardrail."\n'
        "  default_route: standard\n"
    )
    (repo / "p.yml").write_text(three)
    _commit(repo, "biases base")
    base = _base()

    # Case 1: all three reworded and rewrapped over different line counts,
    # same count of items - exit 0.
    (repo / "p.yml").write_text(
        "policy:\n"
        "  biases:\n"
        '    - "When the size is genuinely unclear, estimate up."\n'
        '    - "A non-engineering role in play usually pulls the route\n'
        '       heavier, and that is a bias rather than a floor."\n'
        '    - "Prefer the lightest route that clears every routing\n'
        '       guardrail and the gates that apply."\n'
        "  default_route: standard\n")
    _commit(repo, "biases reworded and rewrapped")
    result = _run_compare(repo, base)
    assert result.returncode == 0, result.stdout + result.stderr

    # Case 2: one item removed - reported. A deleted tie-breaker is a
    # content change, not a rewording.
    (repo / "p.yml").write_text(
        "policy:\n"
        "  biases:\n"
        '    - "When the size is genuinely unclear, estimate up."\n'
        '    - "A non-engineering role in play pulls the route heavier."\n'
        "  default_route: standard\n")
    _commit(repo, "one bias removed")
    result = _run_compare(repo, base)
    assert result.returncode != 0, result.stdout + result.stderr
    assert "p.yml" in result.stdout

    # Case 3: a fourth item added - reported.
    (repo / "q.yml").write_text(three)
    _commit(repo, "q base")
    base_q = _base()
    (repo / "q.yml").write_text(three.replace(
        "  default_route: standard\n",
        '    - "A fourth tie-breaker nobody agreed."\n'
        "  default_route: standard\n"))
    _commit(repo, "a bias added")
    result = _run_compare(repo, base_q)
    assert result.returncode != 0, result.stdout + result.stderr

    # Case 4: a sequence under a key that is NOT prose - still compared, so
    # the extension cannot be used to hide a rule change.
    (repo / "r.yml").write_text(
        "checks:\n"
        "  - borrowed-documents-answered\n"
        "  - evidence-typed\n")
    _commit(repo, "r base")
    base_r = _base()
    (repo / "r.yml").write_text(
        "checks:\n"
        "  - borrowed-documents-answered\n"
        "  - evidence-untyped\n")
    _commit(repo, "a real check renamed")
    result = _run_compare(repo, base_r)
    assert result.returncode != 0, result.stdout + result.stderr

    # Case 5: a prose key whose value is empty and whose children are a
    # MAPPING, not a sequence - the children are values and stay compared.
    (repo / "s.yml").write_text(
        "name:\n"
        "  threshold: 5\n"
        "  enabled: true\n")
    _commit(repo, "s base")
    base_s = _base()
    (repo / "s.yml").write_text(
        "name:\n"
        "  threshold: 9\n"
        "  enabled: true\n")
    _commit(repo, "a nested value changed under a prose key")
    result = _run_compare(repo, base_s)
    assert result.returncode != 0, result.stdout + result.stderr


def test_pbw_e4_an_allowance_must_name_its_reason(tmp_path):
    """`--allow-pinned-test` takes `PATH=REASON`, prints both, and refuses an
    allowance with no reason or a path outside `tests/`. `PBW-E4`.

    An allowance with no stated reason is the same defect as a loosened
    matcher: the report goes quiet and nothing records why. The plan needs
    every batch to lower `PENDING_PATHS_HIGH_WATER` in
    `tests/test_writing_style.py`, so every batch needs one allowance, and the
    reason is what keeps that from becoming a habit nobody reads.
    """
    repo = _sandbox_repo(tmp_path)
    (repo / "tests").mkdir()
    (repo / "tests" / "test_mech.py").write_text(
        '"""Doc."""\n\n\ndef test_x():\n    assert 1 == 1\n')
    _commit(repo, "base")
    base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo,
                           capture_output=True, text=True,
                           check=True).stdout.strip()
    (repo / "tests" / "test_mech.py").write_text(
        '"""Doc."""\n\n\ndef test_x():\n    assert 2 == 2\n')
    _commit(repo, "mechanism constant lowered")

    # Without an allowance the change is reported.
    result = _run_compare(repo, base)
    assert result.returncode != 0
    assert "test_mech.py" in result.stdout

    # With a reason: exit 0, and the output names the path and the reason.
    reason = "the high-water constant the plan requires this batch to lower"
    result = _run_compare(repo, base, "--allow-pinned-test",
                           f"tests/test_mech.py={reason}")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "tests/test_mech.py" in result.stdout
    assert reason in result.stdout, (
        "the recorded output must say why the path was excused:\n"
        + result.stdout)

    # No reason: refused, and the message says a reason is needed.
    result = _run_compare(repo, base, "--allow-pinned-test",
                           "tests/test_mech.py")
    assert result.returncode != 0
    assert "reason" in result.stdout.lower() + result.stderr.lower()

    # An empty reason is not a reason.
    result = _run_compare(repo, base, "--allow-pinned-test",
                           "tests/test_mech.py=")
    assert result.returncode != 0

    # A path outside tests/ is still refused, reason or not.
    result = _run_compare(repo, base, "--allow-pinned-test",
                           "src/mod.py=a stated reason does not help here")
    assert result.returncode != 0


def test_pbw_e4_a_yaml_comment_is_not_behaviour(tmp_path):
    """A whole-line `#` comment is the same prose position
    `tests/test_writing_style.py`'s `_yaml_spans` reads, so rewording one is
    not a behaviour change - but a `rationale:`-sibling key's real value
    still is. `PBW-E4`, `PBW-D2`."""
    repo = _sandbox_repo(tmp_path)
    (repo / "policy.yml").write_text(
        "# old comment explaining the rule below\n"
        "rule: keep\n")
    _commit(repo, "base")
    base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo,
                           capture_output=True, text=True, check=True).stdout.strip()

    # Comment-only change - exit 0.
    (repo / "policy.yml").write_text(
        "# new comment, reworded for clarity\n"
        "rule: keep\n")
    _commit(repo, "comment reworded")
    result = _run_compare(repo, base)
    assert result.returncode == 0, result.stdout + result.stderr

    # The non-prose value changes too - exit non-zero, naming the file.
    (repo / "policy.yml").write_text(
        "# new comment, reworded for clarity\n"
        "rule: change\n")
    _commit(repo, "rule value changed")
    result = _run_compare(repo, base)
    assert result.returncode != 0
    assert "policy.yml" in result.stdout

    # governance/terminology.yml's own prose keys (means, not, context, why,
    # reason) are not the general PROSE_KEYS - rewording one is still not a
    # behaviour change.
    (repo / "terms.yml").write_text(
        "terms:\n"
        "  issue:\n"
        "    means: old wording about an issue\n"
        "    not: old wording about what it is not\n"
        "    related: [manifest]\n")
    _commit(repo, "terms base")
    base_terms = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo,
                                 capture_output=True, text=True,
                                 check=True).stdout.strip()
    (repo / "terms.yml").write_text(
        "terms:\n"
        "  issue:\n"
        "    means: new wording, reworded entirely, about an issue\n"
        "    not: new wording, reworded entirely, about what it is not\n"
        "    related: [manifest]\n")
    _commit(repo, "terms reworded")
    result = _run_compare(repo, base_terms)
    assert result.returncode == 0, result.stdout + result.stderr

    # `appears_in` is a citation list, not a mapping value - a reader's aid
    # naming where an id shows up, printed by `compass terminology explain`
    # and nowhere read as a rule. `referent` is the same kind of field, a
    # one-line description printed alongside it. Correcting a stale filename
    # inside `appears_in` (the v1 `task.yml` renamed to `manifest.yml`) and
    # rewording `referent` are both not a behaviour change.
    (repo / "codes.yml").write_text(
        "codes:\n"
        "  TRC:\n"
        "    referent: One decision inside a single issue's design.\n"
        "    appears_in: [acceptance-criteria.md, \"task.yml scenarios[].id\"]\n")
    _commit(repo, "codes base")
    base_codes = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo,
                                 capture_output=True, text=True,
                                 check=True).stdout.strip()
    (repo / "codes.yml").write_text(
        "codes:\n"
        "  TRC:\n"
        "    referent: One decision inside a single issue's technical design.\n"
        "    appears_in: [acceptance-criteria.md, \"manifest.yml scenarios[].id\"]\n")
    _commit(repo, "referent and appears_in corrected")
    result = _run_compare(repo, base_codes)
    assert result.returncode == 0, result.stdout + result.stderr

    # A multi-line folded block scalar under a PROSE_KEYS key: rewording
    # every continuation line is not a behaviour change...
    (repo / "block.yml").write_text(
        "checks:\n"
        "  a-check:\n"
        "    description: >\n"
        "      Old wording, spread\n"
        "      across two lines.\n"
        "    checks: [x]\n")
    _commit(repo, "block base")
    base2 = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo,
                            capture_output=True, text=True, check=True).stdout.strip()
    (repo / "block.yml").write_text(
        "checks:\n"
        "  a-check:\n"
        "    description: >\n"
        "      New wording entirely, now spread\n"
        "      across three\n"
        "      lines instead.\n"
        "    checks: [x]\n")
    _commit(repo, "block reworded")
    result = _run_compare(repo, base2)
    assert result.returncode == 0, result.stdout + result.stderr

    # ...but the sibling `checks:` list is still a real change.
    (repo / "block.yml").write_text(
        "checks:\n"
        "  a-check:\n"
        "    description: >\n"
        "      New wording entirely, now spread\n"
        "      across three\n"
        "      lines instead.\n"
        "    checks: [y]\n")
    _commit(repo, "block checks changed")
    result = _run_compare(repo, base2)
    assert result.returncode != 0
    assert "block.yml" in result.stdout

    # A run of whole-line comments collapsing from many short lines to
    # fewer, longer ones is still not a behaviour change.
    (repo / "comments.yml") .write_text(
        "# first old line\n"
        "# second old line\n"
        "# third old line\n"
        "rule: keep\n")
    _commit(repo, "comments base")
    base3 = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo,
                            capture_output=True, text=True, check=True).stdout.strip()
    (repo / "comments.yml").write_text(
        "# one reworded comment covering the same ground\n"
        "rule: keep\n")
    _commit(repo, "comments collapsed")
    result = _run_compare(repo, base3)
    assert result.returncode == 0, result.stdout + result.stderr

    # An inline `#` comment trailing a plain sequence item - not under a
    # PROSE_KEYS key, so `_yaml_spans` reads it only via the whole-line
    # comment walk, which a trailing comment is not. Rewording, or even
    # deleting, the comment must still not read as a behaviour change: the
    # item itself (`agents/`) is untouched.
    (repo / "paths.yml").write_text(
        "exempt:\n"
        "  - agents/    # ten agent definitions, added clean at the freeze\n"
        "  - docs/\n")
    _commit(repo, "paths base")
    base4 = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo,
                            capture_output=True, text=True, check=True).stdout.strip()
    (repo / "paths.yml").write_text(
        "exempt:\n"
        "  - agents/    # ten agent definitions, same shape as the others\n"
        "  - docs/\n")
    _commit(repo, "inline comment reworded")
    result = _run_compare(repo, base4)
    assert result.returncode == 0, result.stdout + result.stderr

    # Dropping the inline comment entirely - not reworded, gone - is the
    # same non-change: a comment carries no behaviour whether it is present,
    # reworded, or removed.
    (repo / "paths.yml").write_text(
        "exempt:\n"
        "  - agents/\n"
        "  - docs/\n")
    _commit(repo, "inline comment deleted")
    result = _run_compare(repo, base4)
    assert result.returncode == 0, result.stdout + result.stderr

    # ...but the item itself changing is still a real change.
    (repo / "paths.yml").write_text(
        "exempt:\n"
        "  - agents/    # ten agent definitions, same shape as the others\n"
        "  - skills/\n")
    _commit(repo, "item changed")
    result = _run_compare(repo, base4)
    assert result.returncode != 0
    assert "paths.yml" in result.stdout


def test_pbw_e4_a_reordered_table_row_is_not_behaviour(tmp_path):
    """A markdown table's rows carry links in document order; moving a row
    to fix a genuinely wrong position - `architecture/decisions/README.md`
    listed ADR-013 last instead of between ADR-012 and ADR-014 - moves its
    link in the extracted sequence too, even though every link target is
    byte-identical. A reader following any of the links lands in the same
    place regardless of row order, so this is not a behaviour change; a
    link actually retargeted, added, or removed still is. `PBW-E4`."""
    repo = _sandbox_repo(tmp_path)
    (repo / "index.md").write_text(
        "| [A](a.md) | first |\n"
        "| [B](b.md) | second |\n"
        "| [C](c.md) | third |\n")
    _commit(repo, "base")
    base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo,
                           capture_output=True, text=True, check=True).stdout.strip()

    # Row C moves to its correct position between A and B - same three
    # links, different order on the page.
    (repo / "index.md").write_text(
        "| [A](a.md) | first |\n"
        "| [C](c.md) | third |\n"
        "| [B](b.md) | second |\n")
    _commit(repo, "row reordered")
    result = _run_compare(repo, base)
    assert result.returncode == 0, result.stdout + result.stderr

    # A link actually retargeted is still a real change.
    (repo / "index.md").write_text(
        "| [A](a.md) | first |\n"
        "| [C](d.md) | third |\n"
        "| [B](b.md) | second |\n")
    _commit(repo, "link retargeted")
    result = _run_compare(repo, base)
    assert result.returncode != 0
    assert "index.md" in result.stdout


# ---------------------------------------------------------------------------
# PBW-F7 - a rewritten instruction still instructs the same behaviour
# ---------------------------------------------------------------------------

INSTRUCTION_INVENTORY = REPO_ROOT / "scripts" / "instruction-inventory.py"


def _run_inventory(repo: Path, base: str, out: Path,
                    *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["python3", str(INSTRUCTION_INVENTORY), "--base", base,
         "--out", str(out), *extra],
        cwd=repo, capture_output=True, text=True)


def test_pbw_f7_every_sentence_maps_or_is_recorded_as_absorbed(tmp_path):
    """A sentence dropped from a rewritten instruction file with neither a
    mapped nor an absorbed-into row is a non-zero exit naming it; the same
    drop with an absorbed-into row on record is exit 0. `PBW-F7`."""
    repo = _sandbox_repo(tmp_path)
    out = tmp_path / "inventory-out"
    skill_dir = repo / "skills" / "example"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "# Example skill\n\n"
        "You must read the assignment before you start.\n"
        "You must write the failing test first.\n"
    )
    _commit(repo, "base")
    base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo,
                           capture_output=True, text=True, check=True).stdout.strip()

    # Drop the second instruction with no mapping and no absorption record.
    (skill_dir / "SKILL.md").write_text(
        "# Example skill\n\n"
        "You must read the assignment before you start.\n"
    )
    _commit(repo, "drop a sentence")
    result = _run_inventory(repo, base, out)
    assert result.returncode != 0
    assert "write the failing test first" in (result.stdout + result.stderr)

    # Record the absorption and try again.
    (skill_dir / "SKILL.md").write_text(
        "# Example skill\n\n"
        "You must read the assignment before you start, and write the "
        "failing test first.\n"
        '<!-- absorbed: "You must write the failing test first." -->\n'
    )
    _commit(repo, "record the absorption")
    result = _run_inventory(repo, base, out)
    assert result.returncode == 0, result.stdout + result.stderr


def test_pbw_d8_the_excluded_paths_are_out_of_every_sweep():
    """`docs/system-spec.md`, `cli/vendor/yaml/`, `cli/vendor/LICENSE-PyYAML`,
    `LICENSE` and `assets/` never appear in `scanned_paths()`, so no sweep in
    group A can report a finding inside them. `PBW-D8`.

    The same "which paths are outside every sweep" question holds the
    pending-list ratchet: the distribution map's "the batches share no
    files" claim rests on the nine lists being pairwise disjoint, and
    `PENDING_PATHS_HIGH_WATER` rests on every listed path being real and the
    total never climbing past the audit's own count."""
    scanned = {str(p.relative_to(REPO_ROOT)) for p in scanned_paths()}
    for excluded in EXCLUDED_PATHS:
        if excluded.endswith("/"):
            assert not any(p.startswith(excluded) for p in scanned), excluded
        else:
            assert excluded not in scanned, excluded
    assert scanned, "scanned_paths() must not be empty"

    tracked = set(_git_ls_files())
    seen: dict[str, str] = {}
    total = 0
    for list_file in _pending_list_files():
        for line in list_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            total += 1
            assert line in tracked, f"{list_file.name}: {line} is not tracked"
            assert (REPO_ROOT / line).exists(), f"{list_file.name}: {line} does not exist"
            assert line not in seen, (
                f"{line} is on both {seen.get(line)} and {list_file.name} - "
                f"the batches are no longer disjoint")
            seen[line] = list_file.name
    assert total <= PENDING_PATHS_HIGH_WATER, (
        f"{total} pending paths exceeds the high-water mark of "
        f"{PENDING_PATHS_HIGH_WATER} - the ratchet only ever shrinks")
