"""The surface a newcomer reads first says what is true.

Issue: public-docs-tell-the-truth. Scenarios TRC-A1 to TRC-A6, TRC-D2,
TRC-E1, TRC-F1, TRC-F2.

An outside engineering review of 3.2.0 opened the README and found `issk`,
opened the safety contract and found it titled for version 1.0, and opened the
portability guide and found filenames that do not exist. Each of these checks
is one of those defects turned into something that fails.
"""

import ast
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

#: Live prose surfaces. Decision records are excluded on purpose: they record
#: what was decided at the time, and rewriting one would falsify the account.
PROSE_ROOTS = ("approaches", "skills", "agents", "commands", "templates",
               "docs", "governance", "architecture")
EXEMPT = ("architecture/decisions/", "templates/architecture/decisions/",
          "docs/proposals/", "docs/analysis/", "docs/system-spec.md")


def _prose_files() -> list[Path]:
    files = [p for r in PROSE_ROOTS for p in (REPO_ROOT / r).rglob("*.md")]
    files += [REPO_ROOT / n for n in ("README.md", "CLAUDE.md", "AGENTS.md")]
    return [p for p in files
            if p.is_file() and not str(p.relative_to(REPO_ROOT)).startswith(EXEMPT)]


# --- TRC-A1 -----------------------------------------------------------------

def test_a1_no_file_says_issk():
    """TRC-A1 - a rename search-and-replaced "issue" into "issk".

    It reached the README twice, the five-minute guide, and the architecture
    context file. It is the first word a newcomer reads about the framework's
    central object.
    """
    hits = [f"{p.relative_to(REPO_ROOT)}:{n}"
            for p in _prose_files()
            for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
            if "issk" in line]
    assert not hits, "the word 'issk' survives in:\n  " + "\n  ".join(hits)


# --- TRC-A2 -----------------------------------------------------------------

def test_a2_contract_title_carries_no_version():
    """TRC-A2 - a title carrying a version has to move at every major.

    That is how it came to say 1.0 on a 3.2.0 release. The version moves into
    the body, where a check can compare it to VERSION.
    """
    title = (REPO_ROOT / "docs" / "safety-contract.md").read_text(
        encoding="utf-8").splitlines()[0]
    assert not re.search(r"\b\d+\.\d+", title), (
        f"the safety contract's title still carries a version: {title!r}. A "
        f"title that must move at every major is a scheduled defect")


def test_a2b_contract_states_the_version_it_applies_from():
    body = (REPO_ROOT / "docs" / "safety-contract.md").read_text(encoding="utf-8")
    m = re.search(r"applies from (?:version )?[`]?(\d+)\.(\d+)\.(\d+)", body, re.I)
    assert m, ("the contract does not state the version it applies from. The "
               "title no longer carries one, so the body must")
    stated = tuple(int(x) for x in m.groups())
    current = tuple(int(x) for x in
                    (REPO_ROOT / "VERSION").read_text().strip().split("."))
    assert stated <= current, (
        f"the contract claims to apply from {stated}, which is later than "
        f"VERSION {current} - it is describing a release that does not exist")


# --- TRC-A3 -----------------------------------------------------------------

def test_a3_guide_does_not_deny_the_marketplace():
    """TRC-A3 - the guide denied a channel the project publishes on."""
    body = " ".join((REPO_ROOT / "docs" / "security.md").read_text(
        encoding="utf-8").replace("`", "").split())
    assert "no Compass plugin marketplace" not in body, (
        "docs/security.md still says there is no Compass plugin marketplace. "
        "The README's primary install path is the marketplace and the manifest "
        "ships in this repository")
    assert "marketplace" in body.lower(), (
        "the supply-chain caution the denial was carrying has gone with it - "
        "the guide should still tell a reader to treat a marketplace install "
        "with the same care")


# --- TRC-A4 -----------------------------------------------------------------

def test_a4_named_files_resolve():
    """TRC-A4 - docs/portability.md listed approach files that do not exist.

    Scoped to filenames a document presents as shipping with the framework:
    a backticked or bare path ending in .md under a known framework directory.
    """
    named = re.compile(r"\b((?:approaches|governance|templates|skills|agents"
                       r"|commands|docs)/[\w./-]+\.md)\b")
    missing = []
    for p in _prose_files():
        for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            for path in named.findall(line):
                if not (REPO_ROOT / path).exists():
                    missing.append(f"{p.relative_to(REPO_ROOT)}:{n}: {path}")
    assert not missing, (
        "documents name files that do not exist:\n  " + "\n  ".join(missing))


# --- TRC-A5 -----------------------------------------------------------------

def test_a5_architecture_context_uses_current_stage_names():
    """TRC-A5 - the context file describes the system as it is now.

    `architecture/decisions/` is exempt as history. `system-context.md` is not
    a decision record; it says what is true today, and it said the manifest is
    "written by Frame".
    """
    body = (REPO_ROOT / "architecture" / "system-context.md").read_text(encoding="utf-8")
    for retired in ("Frame", "Specify", "Clarify", "Distribute", "Land"):
        assert not re.search(rf"\bwritten by {retired}\b", body), (
            f"architecture/system-context.md still says the manifest is written "
            f"by {retired}, a stage that no longer exists")


# --- TRC-A6 -----------------------------------------------------------------

RETIRED_STAGES = ("Frame", "Specify", "Clarify", "Distribute", "Land")


def _printed_strings() -> list[tuple[Path, int, str]]:
    """Every string literal in the CLI that is not a docstring.

    Parsed rather than grepped. Comments and docstrings are position-exempt
    (PX-1) because the parser discards them - there is no path from a comment
    to a user, and a comment explaining an old name is the record. A string
    literal is the opposite: it is what the user reads.
    """
    out = []
    files = list((REPO_ROOT / "cli" / "compass_pkg").glob("*.py"))
    files.append(REPO_ROOT / "cli" / "compass")
    for p in files:
        try:
            tree = ast.parse(p.read_text(encoding="utf-8"))
        except SyntaxError:                      # pragma: no cover
            continue
        docstrings = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.FunctionDef,
                                 ast.AsyncFunctionDef, ast.ClassDef)):
                if ast.get_docstring(node, clean=False):
                    docstrings.add(id(node.body[0].value))
        for node in ast.walk(tree):
            if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                    and id(node) not in docstrings):
                out.append((p, node.lineno, node.value))
    return out


def test_a6_printed_strings_name_no_retired_stage():
    """TRC-A6 - a message must not tell a user to run a stage that is gone.

    Worse than the documentation drift. A reader can put a document down; a
    user meeting "has Frame run?" is being told to run a stage that does not
    exist, while already stuck - and the redirect that keeps the advice merely
    old expires at the next major.
    """
    strings = _printed_strings()
    assert len(strings) > 200, (
        f"only {len(strings)} string literals parsed out of the CLI - the "
        f"parse has broken and this check would pass without inspecting "
        f"anything")

    hits = []
    for p, lineno, value in strings:
        for stage in RETIRED_STAGES:
            if re.search(rf"\b{stage}\b", value):
                hits.append(f"{p.relative_to(REPO_ROOT)}:{lineno}: "
                            f"{stage!r} in {value.strip()[:60]!r}")
    assert not hits, (
        f"{len(hits)} retired stage name(s) in strings the CLI prints:\n  "
        + "\n  ".join(hits))


# --- TRC-E1 -----------------------------------------------------------------

def test_e1_failure_message_claim_is_checked_or_narrowed():
    """TRC-E1 - guarantee 7 claimed something about EVERY failure message.

    Nothing checks it, and nothing can: judging whether prose explains a cause
    is not mechanisable. So it is narrowed to what is true, and says which
    messages it covers.
    """
    body = " ".join((REPO_ROOT / "docs" / "safety-contract.md").read_text(
        encoding="utf-8").replace("`", "").replace("*", "").split())
    assert "every failure message tells you" not in body.lower(), (
        "the contract still claims every failure message explains itself. "
        "Nothing checks that, and no check could")
    assert re.search(r"(structured failure|failure message)", body, re.I), (
        "the narrowed guarantee no longer says anything about failure "
        "messages - narrowing past what is true is its own defect")


# --- TRC-F1 -----------------------------------------------------------------

def test_f1_decay_rule_states_its_ask():
    """TRC-F1 - the mechanical half. The judgement half needs a reader.

    Carried from a closed issue that asked for a reader three times and never
    found one. This half can pass alone, on purpose: the reader's answer is
    recorded as evidence when it arrives, and anything it finds becomes its own
    issue rather than blocking a release.
    """
    body = (REPO_ROOT / "governance" / "strategies.md").read_text(encoding="utf-8")
    # Anchored on the rule's own opening sentence, not on a heading. It has no
    # heading, and never uses the word "decay" - it is called the decay rule
    # only in conversation, which is part of why pointing a reader at it was
    # awkward in the first place.
    anchor = "**Correct a retired name in a comment you were touching anyway.**"
    assert anchor in body, (
        "the rule about retired names in comments is not where this check "
        "expects it. If it moved or was reworded, this check has stopped "
        "reading the thing it was written for")
    # The anchor sentence IS the imperative, so it stays in the section.
    section = anchor + body.split(anchor, 1)[1].split("\n\n**", 1)[0]
    flat = " ".join(section.replace("`", "").replace("*", "").split())

    # Suffixes allowed: the rule says "fixed on the way past", and a check
    # that misses that is failing on word form rather than on meaning.
    assert re.search(r"\b(correct|fix|replace|update|rewrite)(?:s|ed|ing)?\b",
                     flat, re.I), (
        "the decay rule never states the action it asks for. A rule a reader "
        "cannot act on has not landed")
    bare = re.findall(r"\b([GS]\d+)\b(?!\s*[-\u2013\u2014:(])", flat)
    assert not bare, (
        f"the decay rule uses short codes without expanding them: {bare}. A "
        f"reader outside the conversation cannot resolve them")


# --- TRC-F2 -----------------------------------------------------------------

def test_f2_launch_article_carries_no_working_notes():
    """TRC-F2 - the mechanical half of "does it read as publication copy"."""
    article = REPO_ROOT / "docs" / "launch-article.md"
    assert article.is_file(), "docs/launch-article.md is missing"
    body = article.read_text(encoding="utf-8")
    tells = [t for t in ("TODO", "TBD", "FIXME", "XXX", "draft note",
                         "[ ]", "placeholder") if t in body]
    assert not tells, (
        f"the article carries working-notes markers: {tells}. It is published "
        f"copy, not a scratchpad")


# --- TRC-D2 -----------------------------------------------------------------

def test_d2_repairs_change_only_retired_names():
    """TRC-D2 - the sweep changed wording, not structure.

    Fourteen of the repaired files are under agents/ and skills/ - instructions
    to an agent, not prose - so a careless rename changes behaviour rather than
    reading.

    The design asked for something stronger: replay a substitution map over the
    pre-repair text and require it to reproduce the result byte for byte. That
    turned out not to be true and was not made true by pretending. Several
    repairs needed rephrasing rather than substitution ("Clarify may be *light*
    on Standard" does not become correct English by swapping one word), and a
    check asserting otherwise would have been a check nobody could satisfy
    honestly.

    What is checked instead is the structural property the map was a proxy for,
    fingerprinted from the pre-repair text and committed: heading levels and
    order, fenced code blocks, table rows, list items. All 59 were identical
    across the repair. A repair that drops a step, merges a table row or edits
    a code example fails this; one that renames a stage does not.
    """
    import json
    snap = json.loads(
        (REPO_ROOT / "tests" / "fixtures" / "repaired-file-structure.json")
        .read_text(encoding="utf-8"))
    assert len(snap) > 50, (
        f"only {len(snap)} files in the structure fixture - it has been "
        f"truncated, and this check would pass over almost nothing")

    drift = []
    for rel, expected in sorted(snap.items()):
        p = REPO_ROOT / rel
        if not p.is_file():
            drift.append(f"{rel}: gone")
            continue
        lines = p.read_text(encoding="utf-8").splitlines()
        actual = {
            "heading_levels": [len(m.group(1)) for l in lines
                               if (m := re.match(r"^(#+)\s", l))],
            "fences": sum(1 for l in lines if l.lstrip().startswith("```")),
            "table_rows": sum(1 for l in lines if l.lstrip().startswith("|")),
            "list_items": sum(1 for l in lines
                              if re.match(r"^\s*(?:[-*]|\d+\.)\s", l)),
        }
        for key in expected:
            if actual[key] != expected[key]:
                drift.append(f"{rel}: {key} changed")
    assert not drift, (
        "the vocabulary repair changed document structure, not just wording:\n  "
        + "\n  ".join(drift))
