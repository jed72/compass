"""Two mechanical guards against the way a vocabulary rename actually breaks.

Every defect found reviewing the ADR-023 rename was one of two shapes, and
neither had a check:

1. **A rename table whose retired side holds the current spelling.** A
   repository-wide text sweep rewrites the left-hand side of a mapping as
   readily as the right, and the result is valid code that migrates nothing.
   `SPINE_KEY_MAP` gained `"orchestration": "orchestration"`, which silently
   disabled the manifest migration; `RETIRED_ORCHESTRATION_CEILING` lost the
   only word it existed to translate. Both were masked because a missing key
   and a self-mapping produce the same answer.

2. **A data file naming a path that does not exist.** The same sweep rewrote
   a decision record's filename inside
   `governance/plain-language-baseline.json`, so thirteen suppressions stopped
   matching anything and the count they pinned silently regressed. Valid JSON,
   no parse error, nothing to notice.

Neither is specific to this rename. Both will recur on the next one, which is
why these are guards rather than fixes.
"""

from __future__ import annotations

import json
import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "cli"))

from compass_pkg import core  # noqa: E402


def _in_module_tables():
    """Every retired-to-current mapping this module ships as a fallback."""
    return {
        "SPINE_KEY_MAP": core.SPINE_KEY_MAP,
        "ASSESSMENT_KEY_MAP": core.ASSESSMENT_KEY_MAP,
        "FOLLOW_UP_STATUS_MAP": core.FOLLOW_UP_STATUS_MAP,
        "FRICTION_CATEGORY_MAP": core.FRICTION_CATEGORY_MAP,
        "EVIDENCE_TYPE_MAP": core.EVIDENCE_TYPE_MAP,
        "GATE_ID_MAP": core.GATE_ID_MAP,
        "CHECK_NAME_MAP": core.CHECK_NAME_MAP,
        "_V1_STAGE_KEYS": core._V1_STAGE_KEYS,
    }


def _migrate_map_tables():
    """Every rename table in the shipped data file, flattened to name -> dict."""
    data = yaml.safe_load(
        (ROOT / "cli" / "migrate-map.yml").read_text(encoding="utf-8")) or {}
    # `shape_display` maps a machine value to the words printed for it, so a
    # row whose two sides match is correct there rather than a dead rename.
    DISPLAY_MAPS = {"shape_display"}
    tables = {}
    for section, body in data.items():
        if not isinstance(body, dict) or section in DISPLAY_MAPS:
            continue
        if all(isinstance(v, dict) for v in body.values()) and body:
            for sub, table in body.items():
                tables[f"{section}.{sub}"] = table
        else:
            tables[section] = body
    return tables


def test_no_rename_table_maps_a_name_to_itself():
    """A self-mapping is a migration that does not happen.

    It is what a text sweep leaves behind when it rewrites both sides of a
    row, and it cannot be spotted by running the code: the value is returned
    unchanged either way.
    """
    offenders = []
    for source in (_in_module_tables(), _migrate_map_tables()):
        for name, table in source.items():
            for old, new in (table or {}).items():
                if old == new:
                    offenders.append(f"{name}: {old!r} maps to itself")
    assert not offenders, (
        "a rename table maps a name to itself, so nothing migrates:\n  "
        + "\n  ".join(offenders))


def test_the_shipped_tables_and_the_in_module_fallbacks_agree():
    """The fallback exists for a checkout with no framework install. If the two
    disagree, which one you get depends on where the code is run from."""
    shipped = _migrate_map_tables()
    pairs = [
        ("values.friction_category", core.FRICTION_CATEGORY_MAP),
        ("values.evidence_type", core.EVIDENCE_TYPE_MAP),
        ("values.check_name", core.CHECK_NAME_MAP),
        ("gate_ids", core.GATE_ID_MAP),
        ("stage_keys", core._V1_STAGE_KEYS),
    ]
    for key, fallback in pairs:
        assert shipped.get(key) == fallback, (
            f"cli/migrate-map.yml {key} and its in-module fallback disagree:\n"
            f"  shipped : {shipped.get(key)}\n"
            f"  fallback: {fallback}")


def test_every_path_named_in_a_governance_data_file_resolves():
    """A suppression keyed by a path that no longer exists suppresses nothing.

    The baseline pins where a count started. A sweep that rewrites a filename
    inside it leaves every entry matching nothing, and the count it was
    protecting regresses with no failure anywhere.
    """
    baseline = json.loads(
        (ROOT / "governance" / "plain-language-baseline.json").read_text(
            encoding="utf-8"))
    missing = sorted({
        entry["file"] for entry in baseline.get("locations", [])
        if entry.get("file") and not (ROOT / entry["file"]).exists()
    })
    assert not missing, (
        "governance/plain-language-baseline.json names files that do not "
        "exist, so their entries match nothing:\n  " + "\n  ".join(missing))
