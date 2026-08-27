"""The machine keys renamed to match Anthropic's platform vocabulary.

ADR-023 records the rule: where a term has a counterpart in Anthropic's
platform documentation, Compass uses their word with their meaning. Four
machine names move under it, and each has to keep reading what is already on
disk (ADR-006).

| Was | Is | Why |
|---|---|---|
| `topology` | `orchestration` | their docs split single agent from multiagent |
| `stream_ceiling` | `subtask_ceiling` | they fan out "independent subtasks" |
| `verify.fitness` | `verify.architecture` | printed by `compass check`, so a teaching surface |
| config `swarm:` | config `multiagent:` | the one vocabulary file adopters hand-edit |

The route shapes stop carrying a word at all. `routing.py` was already
converting `solo`/`solo-or-pair`/`swarm` into 1/2/None through a lookup table
and using the number, so the shapes now declare the number and the conversion
goes. The table survives in `core` because archived manifests still carry the
words.

Scenario ids: .compass/work/anthropic-aligned-vocabulary/acceptance-criteria.md
"""

from __future__ import annotations

import json
import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "cli"))

from compass_pkg import core  # noqa: E402

RETIRED_SHAPE_WORDS = {"solo", "pair", "swarm", "solo-or-pair"}


def _yaml(path: pathlib.Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


# --- TRC-B2 / TRC-B4 - the read side keeps old manifests loading -----------

def test_key_map_renames_topology_and_the_ceiling():
    """TRC-B2, TRC-B4: both retired keys are named in the read-side map."""
    assert core.SPINE_KEY_MAP.get("topology") == "orchestration"
    assert core.SPINE_KEY_MAP.get("stream_ceiling") == "subtask_ceiling"


def test_a_manifest_written_with_topology_still_loads():
    """TRC-B2: the old key normalises; nothing is dropped."""
    out = core.normalize_spine({"issue": "x", "topology": "swarm"})
    assert "topology" not in out
    assert out["orchestration"] == "swarm"


def test_a_manifest_written_with_stream_ceiling_still_loads():
    """TRC-B4: same contract for the ceiling."""
    out = core.normalize_spine({"issue": "x", "stream_ceiling": 2})
    assert "stream_ceiling" not in out
    assert out["subtask_ceiling"] == 2


def test_the_new_key_wins_when_both_are_present():
    """A v2 key alongside its v1 twin wins - the rule normalize_spine already
    applies to every other renamed key."""
    out = core.normalize_spine(
        {"issue": "x", "stream_ceiling": 2, "subtask_ceiling": 4})
    assert out["subtask_ceiling"] == 4


# --- TRC-B3 - a retired word is read as the ceiling it always implied ------

def test_a_retired_topology_word_yields_its_ceiling():
    """TRC-B3: the words were standing in for numbers all along."""
    assert core.normalize_spine(
        {"issue": "x", "topology": "solo"})["subtask_ceiling"] == 1
    assert core.normalize_spine(
        {"issue": "x", "topology": "solo-or-pair"})["subtask_ceiling"] == 2
    assert core.normalize_spine(
        {"issue": "x", "topology": "swarm"})["subtask_ceiling"] is None


# --- TRC-B1 / TRC-B4 - the schemas ----------------------------------------

def test_manifest_schema_declares_the_new_keys():
    """TRC-B1, TRC-B4: a schema description is what a validation error quotes,
    so the schema is a teaching surface too."""
    props = json.loads(
        (ROOT / "schemas" / "manifest.schema.json").read_text()
    )["properties"]
    assert "orchestration" in props
    assert "subtask_ceiling" in props
    assert "topology" not in props
    assert "stream_ceiling" not in props


# --- TRC-B6 - route shapes declare a number -------------------------------

def test_route_shapes_declare_a_ceiling_not_a_word():
    """TRC-B6: no shape carries a topology word or an orchestration word."""
    policy = _yaml(ROOT / "governance" / "routing-policy.yml")
    shapes = policy["route_shapes"]
    for name, shape in shapes.items():
        assert "topology" not in shape, f"{name} still declares a topology"
        assert "orchestration" not in shape, (
            f"{name} declares an orchestration; breakdown decides that, "
            f"not the policy")
        assert "subtask_ceiling" in shape, f"{name} declares no ceiling"
        ceiling = shape["subtask_ceiling"]
        assert ceiling is None or isinstance(ceiling, int), (
            f"{name} ceiling is {ceiling!r}, not a number or null")


# --- TRC-B8 - who integrates is decided by the count ----------------------

def test_breakdown_stage_weight_carries_no_retired_word():
    """TRC-B8: `stages.breakdown` said solo / solo-or-pair / swarm, which is
    the same vocabulary the shapes are losing."""
    policy = _yaml(ROOT / "governance" / "routing-policy.yml")
    for name, shape in policy["route_shapes"].items():
        weight = shape.get("stages", {}).get("breakdown")
        assert weight not in RETIRED_SHAPE_WORDS, (
            f"{name} breakdown weight is {weight!r}")


# --- TRC-B5 - the gate id -------------------------------------------------

def test_the_architecture_gate_is_named_for_what_it_checks():
    """TRC-B5: `compass check` prints the gate id on every run."""
    guardrails = _yaml(ROOT / "governance" / "guardrails.yml")
    accepts = guardrails["gate_evidence_requirements"]
    assert "verify.architecture" in accepts
    assert "verify.fitness" not in accepts

    policy_text = (ROOT / "governance" / "routing-policy.yml").read_text()
    assert "add_gate: verify.fitness" not in policy_text


def test_an_archived_gate_id_still_resolves():
    """TRC-B5: roughly a hundred manifests carry the old id (ADR-006)."""
    gate_ids = core.migrate_map_section("gate_ids", {})
    assert gate_ids.get("verify.fitness") == "verify.architecture"


# --- TRC-B7 - the config block adopters hand-edit -------------------------

def test_the_config_names_multiagent_work_by_its_new_name():
    """TRC-B7: shipped template and this repository's own config."""
    for rel in (".compass/config.yml", "templates/config.yml"):
        path = ROOT / rel
        if not path.exists():
            continue
        cfg = _yaml(path)
        assert "multiagent" in cfg, f"{rel} has no multiagent block"
        assert "swarm" not in cfg, f"{rel} still has a swarm block"


def test_a_config_still_using_the_swarm_block_is_read():
    """TRC-B7: an adopter's config is not rewritten by an upgrade."""
    cfg = core.normalize_config({"swarm": {"worktree_root": "../wt"}})
    assert cfg["multiagent"]["worktree_root"] == "../wt"


# --- TRC-F2 - a rename that drops data fails loudly -----------------------

def test_an_unmapped_retired_key_is_not_silently_dropped():
    """TRC-F2: normalisation preserves every value it does not map."""
    out = core.normalize_spine({"issue": "x", "some_unknown_key": 7})
    assert out["some_unknown_key"] == 7
