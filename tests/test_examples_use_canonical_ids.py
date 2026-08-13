"""The shipped samples use one id prefix, and use it consistently.

The five sample issue directories are how an adopter learns what an artifact
looks like. They shipped with two spellings for the same thing - `SCN-` in the
examples, `TRC-` everywhere else - and with ids that had been renamed in one
file and not its siblings.

The second failure is the worse one. A sample whose spec cites an id its own
spine does not carry teaches that the traceability chain is decorative, which
is the opposite of the lesson.

Scenario ids: see docs/system-spec.md.
"""
from __future__ import annotations

import pathlib
import re
import subprocess

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"

# The canonical prefix. `SCN-` is its retired spelling; the parser's anchor is
# the literal keyword `traceability id:`, so `TRC-` keeps keyword and prefix
# in agreement.
CANONICAL = "TRC-"
RETIRED = "SCN-"

# A real id is a number, optionally behind a one-letter group: TRC-001,
# TRC-A1. Deliberately not [A-Za-z0-9]+, which also matched the prose
# placeholder `TRC-id` and reported it as a dangling reference.
ID_RE = re.compile(r"\b(TRC|SCN)-[A-Z]?[0-9]+\b")


def _sample_dirs() -> list[pathlib.Path]:
    return sorted(p for p in EXAMPLES.glob("*/.compass/work/*") if p.is_dir())


def test_the_samples_exist():
    """Guards the two tests below against silently checking nothing."""
    dirs = _sample_dirs()
    assert len(dirs) >= 4, (
        f"found {len(dirs)} sample issue directories under examples/ - the "
        f"checks below would pass by having nothing to look at"
    )


@pytest.mark.parametrize("sample", _sample_dirs(), ids=lambda p: p.name)
def test_no_sample_uses_the_retired_prefix(sample):
    offenders = []
    for path in sorted(sample.rglob("*")):
        if path.suffix not in (".md", ".yml", ".yaml") or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if RETIRED in text:
            offenders.append(f"{path.relative_to(ROOT)}: {text.count(RETIRED)}")
    assert not offenders, (
        f"sample uses the retired id prefix:\n  " + "\n  ".join(offenders)
    )


@pytest.mark.parametrize("sample", _sample_dirs(), ids=lambda p: p.name)
def test_every_id_cited_in_a_sample_exists_in_its_spine(sample):
    """An id in the prose must be an id in the spine.

    This is what a file-by-file rename breaks: the spec keeps one spelling,
    the spine gets another, and the chain the sample exists to demonstrate no
    longer joins up.
    """
    spine_path = sample / "task.yml"
    if not spine_path.is_file():
        pytest.skip(f"{sample.name} has no spine")
    spine = yaml.safe_load(spine_path.read_text(encoding="utf-8")) or {}
    declared = {s.get("id") for s in (spine.get("scenarios") or []) if s.get("id")}
    if not declared:
        pytest.skip(f"{sample.name} declares no scenarios (a spike does not)")

    dangling = {}
    for path in sorted(sample.glob("*.md")):
        cited = {m.group(0) for m in ID_RE.finditer(path.read_text(encoding="utf-8"))}
        missing = cited - declared
        if missing:
            dangling[path.name] = sorted(missing)

    assert not dangling, (
        f"{sample.name}: artifact(s) cite traceability ids their own spine "
        f"does not declare - the chain the sample demonstrates does not join "
        f"up:\n  {dangling}\n  spine declares: {sorted(declared)}"
    )
