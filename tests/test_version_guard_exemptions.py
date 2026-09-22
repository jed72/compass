"""A version a published file talks about is not a version it publishes.

A version a published file mentions but does not publish is exempt only
with an allow marker and a reason on its line; a wider skip pattern is not
allowed. `tests/test_version_guard_covers_every_location.py` scans every
`\\d+.\\d+.\\d+` in the published surfaces and fails any that is not the
declared version, which is right for a version location and wrong for a
historical reference. One example, kept for the shape it documents even
though 4.0.0 removed the real instance:

    # `compass design lint` shipped in 3.3.0, so it keeps working until the
    # next major version rather than breaking an adopter's script mid-major

The fix is an explicit, individually-justified exemption - the shape
`docs/releasing.md` already uses for the vocabulary scan - not a wider skip
pattern. The guard's own docstring records what a broad skip costs: it must
match the neighbouring token, not the whole line, or a version inside an
unrelated word is silently dropped.

Scenario ids: VGH-A1, VGH-A2 in
version-guard-cannot-see-a-historical-version/acceptance-criteria.md
"""
from __future__ import annotations

import pytest

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
    """A marker with no reason is the same as a skip pattern.

    Skips rather than passes when there is nothing to check. The published
    surfaces have carried zero exemptions since 4.0.0 removed the one real
    instance, and a green tick over an empty list is indistinguishable from a
    scan that found every exemption sound.
    """
    exemptions = _exempt_lines()
    if not exemptions:
        pytest.skip("no version-guard exemptions in the published surfaces")
    bare = [f"{rel}:{n}" for rel, n, reason in exemptions if not reason.strip()]
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
    if not exemptions:
        pytest.skip("no version-guard exemptions in the published surfaces")
    assert len(exemptions) <= 2, (
        f"{len(exemptions)} version-guard exemptions now exist:\n  "
        + "\n  ".join(f"{rel}:{n} - {reason}" for rel, n, reason in exemptions)
        + "\nEach one is a place the partial-bump guard no longer looks. If "
          "this list is growing, the guard is measuring the wrong thing - fix "
          "that rather than raising this number.")


def test_vgh_a3_the_marker_still_recognises_the_shape_it_documents():
    """The mechanism, exercised directly, because no published file carries
    an exemption now. The marker is tested against the shape it documents."""
    documented = ("    # `compass design lint` shipped in 3.3.0 "
                  "<!-- version-guard: allow - when the redirect started -->")
    m = MARKER.search(documented)
    assert m, (
        "the marker pattern no longer matches the shape the module docstring "
        "documents, so a real exemption written that way would be read as a "
        "stale version location")
    assert m.group("reason") == "when the redirect started", (
        f"the reason was captured as {m.group('reason')!r}")

    bare = "x = 1  # version-guard: allow -"
    m2 = MARKER.search(bare)
    assert m2 and not m2.group("reason").strip(), (
        "a marker with no reason is no longer detected as bare, so "
        "test_vgh_a1 above would stop catching one")
