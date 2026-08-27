"""A version a published file TALKS ABOUT is not a version it PUBLISHES.

`tests/test_version_guard_covers_every_location.py` scans every `\\d+.\\d+.\\d+`
in the published surfaces and fails any that is not the declared version. That
is right for a version location and wrong for a historical reference:

    # `compass design lint` shipped in 3.3.0, so it keeps working until the
    # next major version rather than breaking an adopter's script mid-major

That sentence is true and must not be bumped. It records when the redirect
started, which is what tells a reader how long ADR-006 obliges it to survive.
Bumping it to make a release pass would make it false, and the redirect would
look removable a major version early.

The comment was written during 3.3.0 development, when the declared version WAS
3.3.0, so the guard passed on a coincidence. Every release from then on hits it.

The fix is an explicit, individually-justified exemption - the shape
`docs/releasing.md` already uses for the vocabulary scan - not a wider skip
pattern. The guard's own docstring records what a broad skip costs:

    This filter used to look at the whole LINE, which silently swallowed the
    one location this test exists for [...] Setting both banners to 9.9.9 left
    the test green.

Scenario ids: VGH-A1, VGH-A2 in
.compass/work/version-guard-cannot-see-a-historical-version/acceptance-criteria.md
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GUARD = ROOT / "tests" / "test_version_guard_covers_every_location.py"

MARKER = re.compile(r"version-guard:\s*allow\s*-\s*(?P<reason>[^\n]*?)\s*(?:-->|$)")


def _exempt_lines():
    """Every line in the published surfaces carrying an allow marker."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("vg", GUARD)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    found = []
    for rel in mod.PUBLISHED_LOCATIONS:
        for n, line in enumerate((ROOT / rel).read_text(encoding="utf-8")
                                 .splitlines(), 1):
            m = MARKER.search(line)
            if m:
                found.append((rel, n, m.group("reason")))
    return found


def test_vgh_a1_every_exemption_carries_a_reason():
    """A marker with no reason is a skip pattern with extra steps."""
    bare = [f"{rel}:{n}" for rel, n, reason in _exempt_lines() if not reason.strip()]
    assert not bare, (
        "these version-guard exemptions say nothing about why the version "
        f"beside them is not a published one: {', '.join(bare)}")


def test_vgh_a2_the_exemption_list_stays_short():
    """The count is checked so the list cannot grow quietly.

    An exemption mechanism nobody counts becomes the wide skip pattern it
    replaced, one line at a time. Raising this number is a deliberate act;
    doing it twice in a release is the signal that the guard is wrong rather
    than the file.
    """
    exemptions = _exempt_lines()
    assert len(exemptions) <= 2, (
        f"{len(exemptions)} version-guard exemptions now exist:\n  "
        + "\n  ".join(f"{rel}:{n} - {reason}" for rel, n, reason in exemptions)
        + "\nEach one is a place the partial-bump guard no longer looks. If "
          "this list is growing, the guard is measuring the wrong thing - fix "
          "that rather than raising this number.")


def test_vgh_a3_the_historical_reference_is_exempt_and_still_says_3_3_0():
    """The case this exists for, pinned so a later edit cannot quietly bump it."""
    text = (ROOT / "cli" / "compass").read_text(encoding="utf-8")
    line = next((l for l in text.splitlines()
                 if "design lint" in l and "shipped in" in l), None)
    assert line, (
        "cli/compass no longer records when `compass design lint` shipped - "
        "that date is what says how long ADR-006 obliges the redirect to live")
    assert "3.3.0" in line, (
        f"the shipped-in version has been changed: {line.strip()}")
    assert MARKER.search(line), (
        "the historical reference carries no version-guard exemption, so the "
        "partial-bump guard will read it as a stale version location")
