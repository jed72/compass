"""Route selection: the deterministic core.

These tests prove that `compass route evaluate` is a pure function: given
readings + the shipped routing-policy.yml, it produces the documented route,
fires the documented floors/caps, and selects the documented topology.

The bulk of the proof is the YAML-driven parameterised test at the bottom -
each fixture in tests/fixtures/routes/ declares an input + expected output.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import load_route_fixtures


# --- happy-path: each reference route selects for representative readings --


def _reading_args(readings: dict) -> list[str]:
    """Translate a readings dict into --reading key=value CLI args."""
    args = []
    for k, v in readings.items():
        if isinstance(v, list):
            args.extend(["--reading", f"{k}=" + ",".join(v)])
        else:
            args.extend(["--reading", f"{k}={v}"])
    return args


def test_express_route_for_small_mapped_change(run_cli):
    """RS-SHAPE-003: small + contained + mapped == express."""
    r = run_cli("route", "evaluate", "--json",
                *_reading_args({"blast_radius": "contained",
                                "terrain": "brownfield-mapped",
                                "magnitude": "small",
                                "intent": "delivery"}))
    assert r.returncode == 0, r
    data = json.loads(r.stdout)
    assert data["route"] == "express"
    assert data["candidate_route"] == "express"


def test_standard_route_for_default_shape(run_cli):
    """RS-SHAPE-005: magnitude=standard == standard."""
    r = run_cli("route", "evaluate", "--json",
                *_reading_args({"blast_radius": "contained",
                                "terrain": "brownfield-mapped",
                                "magnitude": "standard",
                                "intent": "delivery"}))
    assert r.returncode == 0, r
    data = json.loads(r.stdout)
    assert data["route"] == "standard"


def test_expedition_route_for_large_magnitude(run_cli):
    """RS-SHAPE-004: magnitude=large == expedition."""
    r = run_cli("route", "evaluate", "--json",
                *_reading_args({"blast_radius": "contained",
                                "terrain": "brownfield-mapped",
                                "magnitude": "large",
                                "intent": "delivery"}))
    assert r.returncode == 0, r
    data = json.loads(r.stdout)
    assert data["route"] == "expedition"
    assert data["topology"] == "swarm"


def test_hotfix_route_for_live_defect(run_cli):
    """RS-SHAPE-002: urgency=live-defect + small magnitude == hotfix."""
    r = run_cli("route", "evaluate", "--json",
                *_reading_args({"blast_radius": "contained",
                                "terrain": "brownfield-mapped",
                                "magnitude": "small",
                                "intent": "delivery",
                                "urgency": "live-defect"}))
    assert r.returncode == 0, r
    data = json.loads(r.stdout)
    assert data["route"] == "hotfix"


def test_spike_route_for_exploration_intent(run_cli):
    """RS-SHAPE-001: intent=exploration on safe surface == spike."""
    r = run_cli("route", "evaluate", "--json",
                *_reading_args({"blast_radius": "contained",
                                "terrain": "brownfield-mapped",
                                "magnitude": "small",
                                "intent": "exploration"}))
    assert r.returncode == 0, r
    data = json.loads(r.stdout)
    assert data["route"] == "spike"
    assert data["topology"] == "solo"


# --- floors: a matching reading raises the route or forces a phase ---------


def test_floor_critical_blast_radius_forces_expedition(run_cli):
    """RG-FLOOR-001: blast_radius=critical forces at least expedition."""
    r = run_cli("route", "evaluate", "--json",
                *_reading_args({"blast_radius": "critical",
                                "terrain": "brownfield-mapped",
                                "magnitude": "small",
                                "intent": "delivery"}))
    assert r.returncode == 0, r
    data = json.loads(r.stdout)
    assert data["route"] == "expedition"
    fired = [f["id"] for f in data["fired_guardrails"]]
    assert "RG-FLOOR-001" in fired
    # candidate was lighter; the floor raised it
    assert data["candidate_route"] != data["route"]


@pytest.mark.parametrize("domain", ["auth", "payments", "personal-data", "migrations"])
def test_floor_g5_domains_force_expedition(run_cli, domain):
    """RG-FLOOR-003: touching any G5 domain forces at least expedition."""
    r = run_cli("route", "evaluate", "--json",
                *_reading_args({"blast_radius": "contained",
                                "terrain": "brownfield-mapped",
                                "magnitude": "small",
                                "intent": "delivery",
                                "touches": [domain]}))
    assert r.returncode == 0, r
    data = json.loads(r.stdout)
    assert data["route"] == "expedition", (
        f"touching {domain!r} should force expedition, got {data['route']!r}"
    )
    fired = [f["id"] for f in data["fired_guardrails"]]
    assert "RG-FLOOR-003" in fired


def test_floor_brownfield_unmapped_requires_specify(run_cli):
    """RG-FLOOR-002: brownfield-unmapped forces Specify phase to full and
    requires blueprint-distillation skill."""
    r = run_cli("route", "evaluate", "--json",
                *_reading_args({"blast_radius": "contained",
                                "terrain": "brownfield-unmapped",
                                "magnitude": "small",
                                "intent": "delivery"}))
    assert r.returncode == 0, r
    data = json.loads(r.stdout)
    fired = [f["id"] for f in data["fired_guardrails"]]
    assert "RG-FLOOR-002" in fired
    assert data["phases"].get("specify") == "full"
    assert "blueprint-distillation" in data["required_skills"]


# --- caps: critical blast radius caps worktrees to 1 ----------------------


def test_cap_critical_caps_worktrees_to_one(run_cli):
    """RG-CAP-001: critical blast radius => max_worktrees=1, topology forced solo."""
    r = run_cli("route", "evaluate", "--json",
                *_reading_args({"blast_radius": "critical",
                                "terrain": "brownfield-mapped",
                                "magnitude": "large",
                                "intent": "delivery"}))
    assert r.returncode == 0, r
    data = json.loads(r.stdout)
    assert data["route"] == "expedition"   # floor pushed it
    assert data["max_worktrees"] == 1
    assert "solo" in data["topology"]
    fired_ids = [f["id"] for f in data["fired_guardrails"]]
    assert "RG-CAP-001" in fired_ids


# --- candidate-vs-final is recorded in the output -------------------------


def test_candidate_and_final_route_both_recorded(run_cli):
    """The JSON output records both the composed candidate and the final
    route - the floor's effect must be visible, not hidden."""
    r = run_cli("route", "evaluate", "--json",
                *_reading_args({"blast_radius": "contained",
                                "terrain": "brownfield-mapped",
                                "magnitude": "small",
                                "intent": "delivery",
                                "touches": ["auth"]}))
    assert r.returncode == 0, r
    data = json.loads(r.stdout)
    assert data["candidate_route"] == "express"
    assert data["route"] == "expedition"
    assert data["candidate_via"], "candidate_via must say WHY the candidate was picked"


# --- TRC-F3: regression baseline - adaptive routing is unchanged ----------


def test_existing_combinations_unchanged(run_cli):
    """TRC-F3: The five reference routes still compose the same way.

    Loads tests/fixtures/route-baseline.yml (captured at HEAD fb092c0 before
    the cross-task-architectural-integrity work started) and asserts that for
    each reading combination, `compass route evaluate --json` still produces:
      - the same route name (expected_route)
      - the same topology (expected_topology)
      - the same per-phase weights (expected_phases)
      - the same gate set (expected_gates)

    A mismatch is a real regression: routing has drifted from the baseline.
    If that happens, this test must STOP and report - do not patch the
    fixture to make a regression pass.
    """
    import yaml

    baseline_path = (
        Path(__file__).resolve().parent / "fixtures" / "route-baseline.yml"
    )
    assert baseline_path.is_file(), f"Baseline fixture not found: {baseline_path}"

    baseline = yaml.safe_load(baseline_path.read_text(encoding="utf-8"))
    assert baseline, "Baseline fixture is empty - cannot verify routing"

    failures = []

    for entry in baseline:
        name = entry.get("name", "?")
        readings = entry["readings"]
        expected_route = entry["expected_route"]
        expected_topology = entry["expected_topology"]
        expected_phases = entry["expected_phases"]
        expected_gates = set(entry["expected_gates"])

        r = run_cli("route", "evaluate", "--json", *_reading_args(readings))

        if r.returncode != 0:
            failures.append(
                f"[{name}] compass route evaluate failed (exit {r.returncode}):\n"
                f"  stderr: {r.stderr}"
            )
            continue

        data = json.loads(r.stdout)

        actual_route = data.get("route")
        actual_topology = data.get("topology", "")
        actual_phases = data.get("phases", {})
        actual_gates = set(data.get("gates", []))

        if actual_route != expected_route:
            failures.append(
                f"[{name}] ROUTE DRIFT: expected '{expected_route}', "
                f"got '{actual_route}'"
            )
        if expected_topology not in actual_topology:
            failures.append(
                f"[{name}] TOPOLOGY DRIFT: expected '{expected_topology}' "
                f"(substring), got '{actual_topology}'"
            )
        if actual_phases != expected_phases:
            failures.append(
                f"[{name}] PHASE DRIFT:\n"
                f"  expected: {expected_phases}\n"
                f"  actual  : {actual_phases}"
            )
        if actual_gates != expected_gates:
            failures.append(
                f"[{name}] GATE DRIFT:\n"
                f"  expected: {sorted(expected_gates)}\n"
                f"  actual  : {sorted(actual_gates)}"
            )

    assert not failures, (
        "Adaptive routing has drifted from the baseline - these are REAL "
        "REGRESSIONS, not test-logic errors:\n\n" + "\n\n".join(failures)
    )


# --- the YAML fixtures: one parameterised test for the whole set ----------


@pytest.mark.parametrize("fixture", load_route_fixtures(),
                         ids=lambda f: f["__file__"])
def test_route_fixture(run_cli, fixture):
    """One row per YAML in tests/fixtures/routes/. Each declares readings +
    expected route/floors/conflict; the CLI's --json output must match."""
    args = _reading_args(fixture["readings"])
    r = run_cli("route", "evaluate", "--json", *args)
    expected = fixture["expected"]
    if expected.get("conflict"):
        assert r.returncode != 0, f"expected a conflict, got success:\n{r}"
        msg = expected.get("conflict_message_contains")
        if msg:
            assert msg.lower() in (r.stdout + r.stderr).lower(), r
        return
    assert r.returncode == 0, r
    data = json.loads(r.stdout)
    if "candidate_route" in expected:
        assert data["candidate_route"] == expected["candidate_route"]
    if "route" in expected:
        assert data["route"] == expected["route"]
    fired = [f["id"] for f in data.get("fired_guardrails", [])]
    for fid in expected.get("fired_guardrail_ids", []):
        assert fid in fired, f"expected {fid!r} fired, got {fired!r}"
    if "topology" in expected:
        assert expected["topology"] in data["topology"], (
            f"topology mismatch: {data['topology']!r} vs {expected['topology']!r}"
        )
    if "has_gate" in expected:
        assert expected["has_gate"] in data["gates"], (
            f"missing gate {expected['has_gate']!r} in {data['gates']!r}"
        )
