"""TRC-C4 - signals.yml defines a design_smell advisory category.

Serves: INT-6
Spec:
  - governance/signals.yml must have a top-level key design_smell
  - it must be a sibling to scope_bloat_phrases
  - it must list at least: tests dominated by mocking/setup,
    assertions on internal method calls
  - the reviewer agent assesses these at Verify (judgement, never a gate)
  - schemas/signals.schema.json must accept the design_smell property
"""
from __future__ import annotations
from pathlib import Path
import json

import pytest
import yaml

SIGNALS_YML = Path(__file__).parent.parent / "governance" / "signals.yml"
SIGNALS_SCHEMA = Path(__file__).parent.parent / "schemas" / "signals.schema.json"


def _load_signals() -> dict:
    return yaml.safe_load(SIGNALS_YML.read_text(encoding="utf-8"))


def test_signals_has_design_smell_key():
    """signals.yml must have a top-level design_smell key."""
    signals = _load_signals()
    assert "design_smell" in signals, (
        "governance/signals.yml must have a top-level 'design_smell' key. "
        f"Current keys: {list(signals.keys())}"
    )


def test_design_smell_is_a_list():
    """design_smell must be a list (array of pattern strings)."""
    signals = _load_signals()
    assert isinstance(signals["design_smell"], list), (
        "governance/signals.yml design_smell must be a list of pattern strings. "
        f"Got: {type(signals['design_smell'])}"
    )


def test_design_smell_has_mocking_pattern():
    """design_smell must include the mocking/setup dominated pattern."""
    signals = _load_signals()
    patterns = [p.lower() for p in signals["design_smell"]]
    assert any("mock" in p or "setup" in p for p in patterns), (
        "design_smell must include 'tests dominated by mocking or setup'. "
        f"Current patterns: {signals['design_smell']}"
    )


def test_design_smell_has_internal_calls_pattern():
    """design_smell must include the assertions on internal method calls pattern."""
    signals = _load_signals()
    patterns = [p.lower() for p in signals["design_smell"]]
    assert any("internal" in p for p in patterns), (
        "design_smell must include 'assertions on internal method calls'. "
        f"Current patterns: {signals['design_smell']}"
    )


def test_design_smell_has_multiple_behaviour_pattern():
    """design_smell must include the single test asserts more than one behaviour pattern."""
    signals = _load_signals()
    patterns = [p.lower() for p in signals["design_smell"]]
    assert any(
        ("single" in p and "assert" in p) or ("more than one" in p) or ("multiple" in p and "behav" in p)
        for p in patterns
    ), (
        "design_smell must include a 'single test asserts more than one behaviour' pattern. "
        f"Current patterns: {signals['design_smell']}"
    )


def test_signals_schema_accepts_design_smell():
    """schemas/signals.schema.json must accept the design_smell property."""
    schema = json.loads(SIGNALS_SCHEMA.read_text(encoding="utf-8"))
    properties = schema.get("properties", {})
    assert "design_smell" in properties, (
        "schemas/signals.schema.json must have a 'design_smell' property. "
        f"Current properties: {list(properties.keys())}"
    )


def test_signals_yml_validates_against_schema():
    """The updated signals.yml must validate against its schema."""
    try:
        import jsonschema
    except ImportError:
        pytest.skip("jsonschema not installed")

    schema = json.loads(SIGNALS_SCHEMA.read_text(encoding="utf-8"))
    signals = _load_signals()
    jsonschema.validate(signals, schema)  # raises if invalid
