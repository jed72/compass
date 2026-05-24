"""TRC-1 — every published version surface reports `1.0.0`.

The Compass version appears in four places: the plugin manifest, two fields
of the marketplace listing, and the CLI's `COMPASS_VERSION` constant. This
test asserts every surface reports `1.0.0` and the prior `1.0.0-rc.1` does
not appear anywhere those surfaces are read.

Spec: .compass/work/version-bump-1-0-0/spec.feature.md (TRC-1).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest


FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent
EXPECTED_VERSION = "1.0.0"
OLD_VERSION = "1.0.0-rc.1"


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_compass_version_constant() -> str:
    """Extract the COMPASS_VERSION value from cli/compass via a literal regex."""
    text = (FRAMEWORK_ROOT / "cli" / "compass").read_text(encoding="utf-8")
    m = re.search(r'^COMPASS_VERSION\s*=\s*"([^"]+)"', text, re.MULTILINE)
    assert m, "COMPASS_VERSION constant not found in cli/compass"
    return m.group(1)


@pytest.mark.parametrize(
    "label,reader,absent_in_file",
    [
        (
            ".claude-plugin/plugin.json $.version",
            lambda: _read_json(FRAMEWORK_ROOT / ".claude-plugin" / "plugin.json")["version"],
            FRAMEWORK_ROOT / ".claude-plugin" / "plugin.json",
        ),
        (
            ".claude-plugin/marketplace.json $.metadata.version",
            lambda: _read_json(FRAMEWORK_ROOT / ".claude-plugin" / "marketplace.json")["metadata"]["version"],
            FRAMEWORK_ROOT / ".claude-plugin" / "marketplace.json",
        ),
        (
            ".claude-plugin/marketplace.json $.plugins[0].version",
            lambda: _read_json(FRAMEWORK_ROOT / ".claude-plugin" / "marketplace.json")["plugins"][0]["version"],
            FRAMEWORK_ROOT / ".claude-plugin" / "marketplace.json",
        ),
        (
            "cli/compass COMPASS_VERSION",
            _read_compass_version_constant,
            FRAMEWORK_ROOT / "cli" / "compass",
        ),
    ],
    ids=[
        "plugin.json",
        "marketplace.json-metadata",
        "marketplace.json-plugins-0",
        "cli-compass-COMPASS_VERSION",
    ],
)
def test_version_is_1_0_0(label, reader, absent_in_file):
    actual = reader()
    assert actual == EXPECTED_VERSION, (
        f"{label}: expected {EXPECTED_VERSION!r}, got {actual!r}"
    )
    file_text = absent_in_file.read_text(encoding="utf-8")
    assert OLD_VERSION not in file_text, (
        f"{label}: file {absent_in_file} still contains the old version "
        f"{OLD_VERSION!r} somewhere (partial edit?)"
    )
