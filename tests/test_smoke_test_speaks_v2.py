"""The install smoke test describes the framework a reader actually installed.

`docs/install-smoke-test.md` is the first document a new user follows, so it
must use the v2 names: `/compass:assess`, `assessment:`, `delivery_approach:`,
schema 2.0.

Zero pending surfaces means the listed surfaces are clean, not the whole
repository - `docs/install-smoke-test.md` was never in
`governance/terminology.yml`'s `scan.surfaces`, so nothing held it to the
frozen vocabulary through the whole of v2.

This asserts both halves: the document speaks v2, and it is in the scanned
set so a retired term in it fails the build.

Scenario ids: see docs/system-spec.md (TRC-1, `TRC-2`).
"""

# These tests assert the current file names; files written under older
# names still load (ADR-006).
from __future__ import annotations

import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
SMOKE_TEST = ROOT / "docs" / "install-smoke-test.md"
SMOKE_TEST_REL = "docs/install-smoke-test.md"

# Retired v1 spellings that describe behaviour this framework no longer has.
# Each is paired with what a reader should see instead, so a failure says what
# to write rather than only what is wrong.
RETIRED = {
    "/compass:frame": "/compass:assess",
    "readings:": "assessment:",
    'schema_version: "1.0"': 'schema_version: "2.0"',
}


def test_trc_1_the_smoke_test_describes_v2_behaviour():
    text = SMOKE_TEST.read_text(encoding="utf-8")
    found = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for retired, replacement in RETIRED.items():
            if retired in line:
                found.append(
                    f"{SMOKE_TEST_REL}:{lineno}: {retired!r} - v2 says "
                    f"{replacement!r}"
                )
    assert not found, (
        "the install smoke test describes v1 behaviour, on the first "
        "document a new user follows:\n  " + "\n  ".join(found)
    )


def test_trc_2_the_smoke_test_is_scanned_for_the_frozen_vocabulary():
    """The smoke test must be in the scanned set: that keeps a retired
    term out of it."""
    terminology = yaml.safe_load(
        (ROOT / "governance" / "terminology.yml").read_text(encoding="utf-8")
    )
    surfaces = terminology.get("scan", {}).get("surfaces", [])
    assert SMOKE_TEST_REL in surfaces, (
        f"{SMOKE_TEST_REL} is not in governance/terminology.yml's "
        f"scan.surfaces, so nothing holds it to the frozen vocabulary - "
        f"which is exactly how it kept describing v1 through the whole of v2"
    )
