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


def test_vgh_a3_the_marker_still_recognises_the_shape_it_documents():
    """The mechanism, exercised directly, because it currently has no user.

    This scenario used to pin the real instance: a comment in `cli/compass`
    recording that `compass design lint` shipped in 3.3.0, which said how long
    ADR-006 obliged that redirect to live. 4.0.0 removed the alias, and the
    comment went with it - so the published surfaces now carry ZERO
    exemptions, and `test_vgh_a1` and `test_vgh_a2` above both pass over an
    empty list.

    That is worth saying out loud rather than leaving as a quiet green. The
    situation the mechanism exists for - a published file talking about a
    version it does not publish - will recur, so the marker is kept and
    tested against the shape it documents instead of against an instance.
    """
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
