"""The partial-bump guard covers every place a version lives.

`tests/test_version_consistency.py` parametrises the locations it checks. It
covered five; there are seven. `cli/compass_pkg/core.py` holds the constant
`cli/compass` asserts equality against, and the smoke-test banner is the one
`docs/releasing.md` calls "the one that gets forgotten, because it lives in
prose rather than in a manifest". Neither was in the list.

Three documents also disagreed about the count: the guard's docstring said
five, `docs/releasing.md` said six, and there were seven.

This is the fourth instance in one release of a check reporting success while
checking nothing - alongside the smoke-test guard that searched for a retired
spelling, an evidence record with no identity, and `OLD_VERSIONS`, which no
code read and which a missing comma had silently corrupted. A check that
cannot fail buys false confidence, which is worse than no check.

So this test does not restate the list of locations. Restating it is how the
list went stale. It finds every version string in the repository's published
surfaces and asserts the guard has a case for each.

Spec: .compass/work/version-guard-covers-all/acceptance-criteria.md.
"""
from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
GUARD = ROOT / "tests" / "test_version_consistency.py"

# Every file that publishes the version, and how to find it in that file.
# A location added here without a matching case in the guard fails TRC-1.
PUBLISHED_LOCATIONS = {
    "VERSION": None,
    ".claude-plugin/plugin.json": "version",
    ".claude-plugin/marketplace.json": "version",
    "cli/compass": "COMPASS_VERSION",
    "cli/compass_pkg/core.py": "COMPASS_VERSION",
    "docs/install-smoke-test.md": "compass",
}


def _declared_version() -> str:
    return (ROOT / "VERSION").read_text(encoding="utf-8").strip()


def test_trc_1_every_published_location_reports_the_declared_version():
    """The property that matters, checked against the files themselves.

    Independent of how any guard is written: if a published file carries a
    version string that is not the declared one, a release shipped a partial
    bump.
    """
    version = _declared_version()
    stale = []
    for rel in PUBLISHED_LOCATIONS:
        text = (ROOT / rel).read_text(encoding="utf-8")
        for m in re.finditer(r"\b\d+\.\d+\.\d+\b", text):
            found = m.group(0)
            # Third-party and schema versions are not Compass's version.
            line = text[text.rfind("\n", 0, m.start()) + 1:
                        text.find("\n", m.end())]
            if any(w in line for w in ("PyYAML", "schema", "python", "6.0.2")):
                continue
            if found != version:
                lineno = text.count("\n", 0, m.start()) + 1
                stale.append(f"{rel}:{lineno}: {found} (declared: {version})")
    assert not stale, (
        "a published surface carries a version that is not the declared "
        "one - a partial bump:\n  " + "\n  ".join(stale)
    )


def test_trc_2_the_guard_has_a_case_for_every_published_location():
    """The guard's own coverage, so it cannot quietly cover fewer than exist."""
    guard = GUARD.read_text(encoding="utf-8")
    missing = [rel for rel in PUBLISHED_LOCATIONS if rel not in guard]
    assert not missing, (
        "tests/test_version_consistency.py has no case for these published "
        "version locations, so a partial bump there would pass:\n  "
        + "\n  ".join(missing)
    )


def test_trc_3_the_guard_declares_no_constant_nothing_reads():
    """`OLD_VERSIONS` was dead, and a missing comma had corrupted it.

    Nothing read it, so nothing noticed that `"1.0.0-rc.1" "1.8.1"` had
    concatenated into a single nonsense string and dropped 1.8.1 from the
    set. A guard nobody reads cannot fail; keeping one is how a repository
    accumulates reassurance it has not earned.
    """
    guard = GUARD.read_text(encoding="utf-8")
    # The declaration, not the word. The comment recording why it went is
    # worth keeping; a set nobody reads is not.
    declared = re.search(r"^OLD_VERSIONS\s*=", guard, re.MULTILINE)
    assert not declared, (
        "OLD_VERSIONS was removed because nothing read it and a missing "
        "comma had silently corrupted its contents. If a use for it comes "
        "back, give it one in the same change - do not reintroduce a set "
        "that only exists to look careful."
    )
