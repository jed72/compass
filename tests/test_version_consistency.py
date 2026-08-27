"""Every published version surface reports the same version.

The Compass version appears in seven places: the VERSION file, the plugin
manifest, two fields of the marketplace listing, the `COMPASS_VERSION`
constant in both `cli/compass` and `cli/compass_pkg/core.py`, and the
expected output in the install smoke test. A release that updates some but
not all of them ships a plugin whose manifest disagrees with the CLI it
installs.

This list said five for two releases while there were seven, and the two it
omitted were the ones no manifest carries. `tests/test_version_guard_covers_every_location.py`
now derives the set from the files themselves rather than from a list anyone
has to remember to extend.

EXPECTED_VERSION below is deliberately hardcoded rather than read from the
VERSION file. Reading it would make this test self-maintaining but blind to
the case it most needs to catch: a release where nothing was bumped at all.
Editing this constant is the deliberate act that says a release is intended.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest


FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent
EXPECTED_VERSION = "3.4.0"

# OLD_VERSIONS used to live here: a set of every version shipped before this
# one. Nothing ever read it, and a missing comma had concatenated two of its
# entries into "1.0.0-rc.11.8.1", quietly dropping 1.8.1 - which nothing
# noticed, because nothing was looking. It was removed rather than repaired.
# A constant that only exists to look careful is reassurance the repository
# has not earned.


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_compass_version_constant() -> str:
    text = (FRAMEWORK_ROOT / "cli" / "compass").read_text(encoding="utf-8")
    m = re.search(r'^COMPASS_VERSION\s*=\s*"([^"]+)"', text, re.MULTILINE)
    assert m, "COMPASS_VERSION constant not found in cli/compass"
    return m.group(1)


def _read_core_version_constant() -> str:
    """The package's own constant.

    `cli/compass` asserts equality with this at import time, so a mismatch
    crashes the CLI - a stronger guard than a test, but an accidental one:
    it was never named in the release procedure and nothing checked it here.
    """
    text = (FRAMEWORK_ROOT / "cli" / "compass_pkg" / "core.py").read_text(encoding="utf-8")
    m = re.search(r'^COMPASS_VERSION\s*=\s*"([^"]+)"', text, re.MULTILINE)
    assert m, "COMPASS_VERSION constant not found in cli/compass_pkg/core.py"
    return m.group(1)


def _read_smoke_test_version() -> str:
    """The version in the smoke test's expected `compass --version` output.

    docs/releasing.md calls this "the one that gets forgotten, because it
    lives in prose rather than in a manifest". It was forgotten.
    """
    text = (FRAMEWORK_ROOT / "docs" / "install-smoke-test.md").read_text(encoding="utf-8")
    m = re.search(r'^compass (\d+\.\d+\.\d+) \(', text, re.MULTILINE)
    assert m, "no `compass <version> (...)` banner found in the smoke test"
    return m.group(1)


def _read_version_file() -> str:
    return (FRAMEWORK_ROOT / "VERSION").read_text(encoding="utf-8").strip()


@pytest.mark.parametrize(
    "label,reader",
    [
        ("VERSION", _read_version_file),
        (
            ".claude-plugin/plugin.json $.version",
            lambda: _read_json(FRAMEWORK_ROOT / ".claude-plugin" / "plugin.json")["version"],
        ),
        (
            ".claude-plugin/marketplace.json $.metadata.version",
            lambda: _read_json(FRAMEWORK_ROOT / ".claude-plugin" / "marketplace.json")["metadata"]["version"],
        ),
        (
            ".claude-plugin/marketplace.json $.plugins[0].version",
            lambda: _read_json(FRAMEWORK_ROOT / ".claude-plugin" / "marketplace.json")["plugins"][0]["version"],
        ),
        ("cli/compass COMPASS_VERSION", _read_compass_version_constant),
        ("cli/compass_pkg/core.py COMPASS_VERSION", _read_core_version_constant),
        ("docs/install-smoke-test.md expected output", _read_smoke_test_version),
    ],
)
def test_published_surface_reports_new_version(label, reader):
    """Every published surface reports the same version - no partial bumps."""
    actual = reader()
    assert actual == EXPECTED_VERSION, (
        f"{label} reports {actual!r}, expected {EXPECTED_VERSION!r}"
    )
