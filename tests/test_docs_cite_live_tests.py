"""The release guide must not name a test file that does not exist.

`docs/releasing.md` listed `tests/test_v1_2_narrative.py` twice - once as a
suite the release must run, once in the invariants table as the defender of
"every v1.2.0 capability named in CLAUDE.md is in AGENTS.md or methodology".
When that guard was retired (ADR-021) the citations stayed, so the guide told a
releaser to run a file that is not there and claimed an invariant nothing
defends. Nothing caught it.

Scoped to the release guide on purpose. Other documents name test paths as
worked examples - `docs/writing-specs-and-plans.md` walks through a
`tests/test_ledger_export.py` that was never meant to exist, and ADR-021 names
the very file it retires. Those are illustrations, not coverage claims. The
release guide is the one document where every test path is an instruction to
run something and a claim that something is defended.

Scenario id: DOC-A4 in .compass/work/docs-slimming-pass/acceptance-criteria.md
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GUIDE = ROOT / "docs" / "releasing.md"

CITATION = re.compile(r"tests/[A-Za-z0-9_/]+\.py")


def test_doc_a4_release_guide_cites_no_missing_test_file():
    text = GUIDE.read_text(encoding="utf-8")
    cited = sorted(set(CITATION.findall(text)))
    assert cited, (
        "docs/releasing.md names no test files at all - either the guide has "
        "been rewritten or this check is reading the wrong document, and "
        "either way it is now passing over nothing")

    dangling = [rel for rel in cited if not (ROOT / rel).is_file()]
    assert not dangling, (
        "docs/releasing.md names test files that do not exist: "
        + ", ".join(dangling)
        + ". A retired guard leaves its citations behind, and the guide then "
          "tells a releaser to run a file that is gone and claims an "
          "invariant nothing defends.")
