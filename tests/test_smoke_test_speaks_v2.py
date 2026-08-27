"""The install smoke test describes the framework a reader actually installed.

`docs/install-smoke-test.md` is the first document a new user follows. It
told them to run `/compass:frame` and to expect a manifest carrying `readings:`,
`route:` and `schema_version: "1.0"` - all v1. In v2 the command is
`/compass:assess`, the manifest carries `assessment:` and `delivery_approach:`,
and the schema version is "2.0".

It survived the v2 rename because the file is not in
`governance/terminology.yml`'s `scan.surfaces` and never was. The ratchet
that went from nine pending surfaces to zero was never reading it. Zero
pending surfaces means the nine listed surfaces came clean; it does not mean
the repository came clean.

This asserts both halves: the document speaks v2, and it is in the scanned
set so it cannot drift back out of sight.

Scenario ids: see docs/system-spec.md (TRC-1, TRC-2).
"""

# The vocabulary rename landed on 2026-08-25: the assess and plan stages took
# the names their machine keys, skills and agents already used; `design` went
# back to the designer; design.md became technical-design.md and prd.md became
# intent.md. Spines and documents written before still load and resolve
# (ADR-006), so what moved is the CANONICAL spelling these tests assert - not
# what the framework computes. Re-pointed, not relaxed.
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
    """The fix that matters more than the edit.

    Correcting the prose fixes today. Adding the file to the scanned set is
    what keeps it fixed, and is why this was missed for a whole major
    version.
    """
    terminology = yaml.safe_load(
        (ROOT / "governance" / "terminology.yml").read_text(encoding="utf-8")
    )
    surfaces = terminology.get("scan", {}).get("surfaces", [])
    assert SMOKE_TEST_REL in surfaces, (
        f"{SMOKE_TEST_REL} is not in governance/terminology.yml's "
        f"scan.surfaces, so nothing holds it to the frozen vocabulary - "
        f"which is exactly how it kept describing v1 through the whole of v2"
    )
