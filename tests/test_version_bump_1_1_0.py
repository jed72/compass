"""TRC-1 — every published version surface reports `1.1.0`.

The Compass version appears in five places: the build artifact VERSION file,
the plugin manifest, two fields of the marketplace listing, and the CLI's
`COMPASS_VERSION` constant. This test asserts every surface reports `1.1.0`
and the prior `1.0.0` (or `1.0.0-rc.1`) does not appear anywhere those
surfaces are read.

Spec: .compass/work/version-bump-1-1-0/spec.feature.md (TRC-1).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest


FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent
EXPECTED_VERSION = "1.1.0"
OLD_VERSIONS = {"1.0.0", "1.0.0-rc.1"}


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_compass_version_constant() -> str:
    text = (FRAMEWORK_ROOT / "cli" / "compass").read_text(encoding="utf-8")
    m = re.search(r'^COMPASS_VERSION\s*=\s*"([^"]+)"', text, re.MULTILINE)
    assert m, "COMPASS_VERSION constant not found in cli/compass"
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
    ],
)
def test_published_surface_reports_new_version(label, reader):
    """Every published surface reports 1.1.0 — no partial bumps."""
    actual = reader()
    assert actual == EXPECTED_VERSION, (
        f"{label} reports {actual!r}, expected {EXPECTED_VERSION!r}"
    )
