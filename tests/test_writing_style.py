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
PENDING_PATHS_HIGH_WATER = 452

# What `reader.prose_spans` treats as prose inside a YAML value: the keys
# whose value a reader or a printed message actually sees, not the machine
# contract a migration would rename. Mirrors the key list the behaviour
# comparison blanks (`DD-3`), so the two halves cannot disagree about what
# prose is.
PROSE_KEYS = frozenset({"description", "statement", "rationale", "name", "help"})

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


def _find_retired_word(span: ProseSpan) -> list[Finding]:
    if span.path.startswith(_RETIRED_WORD_STRUCTURAL_SKIP):
        return []
    if ALLOW_MARKER_RE.search(span.text):
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


_register(Rule("PBW-A3", "The spelling is British", _find_spelling))


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


def _idiom_exempt(text: str, match: re.Match) -> bool:
    """"code smell" is the one kept phrase this table would otherwise flag -
    every other kept term (drift, stale, ratchet, in flight, lightweight) is
    simply absent from IDIOM_TABLE, so no pattern exists to exempt it from."""
    if match.group(0).lower() in ("smell", "smells"):
        before = text[:match.start()].rstrip().lower()
        if before.endswith("code"):
            return True
    return False


def _find_idiom(span: ProseSpan) -> list[Finding]:
    if span.path.startswith(_RETIRED_WORD_STRUCTURAL_SKIP):
        # tests/fixtures/terminology/ plants every banned word on purpose
        # (PBW-D2), and one of the retired assessment-dimension words is also
        # on the idiom table above - the same structural skip PBW-A1 uses
        # applies here for the same reason.
        return []
    findings = []
    for pattern, replacement in _IDIOM_PATTERNS:
        for match in pattern.finditer(span.text):
            if _idiom_exempt(span.text, match):
                continue
            findings.append(Finding(
                span.path, span.line,
                f'"{match.group(0)}" -> {replacement}'))
    return findings


_register(Rule("PBW-A5", "No idiom from the table survives", _find_idiom))


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
        if "<" in path:
            # A placeholder shape such as docs/compass/<created>-<slug>/ -
            # naming the convention, not citing one issue's real document.
            # git check-ignore matches the literal string regardless, so
            # this is excluded rather than reported.
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
    ),
))


# ---------------------------------------------------------------------------
# PBW-A7 - a bare code carries its meaning or goes
# ---------------------------------------------------------------------------

_BARE_CODE_RE = re.compile(
    r"\b(?:G[1-5]|S\d+|TRC-\w+|DD-\d+|R\d+|MP-\d+|Inv-\d+|BR-\d+|AMB-\d+|"
    r"U-\d+|review finding \d+|probe \d+|slice \d+[a-z]?|Phase \d+)\b")


def _find_bare_code(span: ProseSpan) -> list[Finding]:
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
            "docs/quickstart.md", "`--scenario TRC-x`",
            "a placeholder scenario id, the same shape as `<test cmd>` "
            "elsewhere on this page - not a real code pointing at meaning "
            "kept outside the file"),
    ),
))


# ---------------------------------------------------------------------------
# PBW-A8 - every file and command a comment names exists
# ---------------------------------------------------------------------------

_REFERENCE_RE = re.compile(
    r"`?((?:[\w.][\w-]*/)+[\w.-]+\.(?:md|py|yml|yaml|json|sh|feature))`?")


def _reference_exempt(text: str, match: re.Match) -> bool:
    start = match.start()
    before = text[:start]
    # A URL - the path segment after the scheme is not repository-relative.
    return before.rstrip().endswith(("://", "http:", "https:")) or "://" in \
        text[max(0, start - 12):start]


def _find_missing_reference(span: ProseSpan) -> list[Finding]:
    findings = []
    for match in _REFERENCE_RE.finditer(span.text):
        if _reference_exempt(span.text, match):
            continue
        path = match.group(1)
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
        Exemption(
            "docs/quickstart.md",
            ".compass/work/add-rate-limiting/manifest.yml",
            "the walkthrough's own hypothetical issue, not a real path in "
            "this repository - see the PBW-A6 exemption above for the "
            "same line"),
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


_register(Rule("PBW-A9", "No sentence is left broken by an earlier "
               "find-and-replace", _find_doubled_word))


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
