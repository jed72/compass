"""Compass does not use a word its readers would have to look up.

A maintainer ruling, 2026-08-14: prefer more words to a precise but obscure
one. The reader is a junior or mid engineer meeting the output for the first
time, and "vacuous"/"vacuity" is accurate and almost never used in ordinary
speech.

This is ADR-017's principle applied to ordinary words rather than short
codes. An unexplained term is a defect whether it is `G5` or `vacuity`, and
the fix is the same: say the thing in words the reader already has.

Scoped to what a user reads - printed output, governance a project adopts, the
docs. Test names and internal comments are for someone reading the code.
"""
from __future__ import annotations

import ast
import pathlib
import re

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
OBSCURE = re.compile(r"vacuous|vacuity", re.I)


def test_ff_5_no_obscure_word_in_user_facing_text():
    hits = []

    # 1. strings the CLI prints
    for p in sorted((ROOT / "cli").rglob("*.py")):
        try:
            tree = ast.parse(p.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            continue
        docstrings = {
            id(n.body[0].value) for n in ast.walk(tree)
            if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                              ast.ClassDef))
            and n.body and isinstance(n.body[0], ast.Expr)
            and isinstance(n.body[0].value, ast.Constant)
            and isinstance(n.body[0].value.value, str)
        }
        for n in ast.walk(tree):
            if (isinstance(n, ast.Constant) and isinstance(n.value, str)
                    and id(n) not in docstrings and OBSCURE.search(n.value)):
                hits.append(f"{p.relative_to(ROOT)}:{n.lineno} (printed string)")

    # 2. governance a project adopts, and the docs it reads
    for p in [*sorted((ROOT / "governance").glob("*.yml")),
              ROOT / "docs" / "five-minutes.md"]:
        # terminology.yml has to name every banned term to ban it, the same
        # exemption the vocabulary scan already gives itself.
        if not p.is_file() or p.name == "terminology.yml":
            continue
        for lineno, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if OBSCURE.search(line):
                hits.append(f"{p.relative_to(ROOT)}:{lineno}")

    assert not hits, (
        "'vacuous'/'vacuity' appears in text a user reads. Say it in plain "
        "words - a check that had nothing to inspect:\n  " + "\n  ".join(hits))


def test_ff_5b_the_vocabulary_bans_it():
    """So it cannot come back. Without this the sweep above is a one-off."""
    doc = yaml.safe_load(
        (ROOT / "governance" / "terminology.yml").read_text(encoding="utf-8"))
    banned = {str(e.get("term", "")).lower() for e in (doc.get("banned") or [])}
    assert any("vacuous" in b or "vacuity" in b for b in banned), (
        "the vocabulary does not ban 'vacuous'/'vacuity', so nothing stops it "
        "returning the next time someone needs a word for this")
