"""Framework invariants for this task (executable-bdd-and-richer-plans).

Two properties that must hold across everything this task changed, and that no
single stream can prove on its own:

  * A project that opted into nothing sees no change (ADR-006). The BDD work
    adds a CLI verb and four config keys; none of them may alter behaviour for
    a project that does not set them.
  * The framework grew by artifacts and skills only (ADR-002). No new
    guardrail, no new gate, no fifth reading dimension.

Spec: .compass/work/executable-bdd-and-richer-plans/spec.feature.md
      (TRC-F5, TRC-F6).
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
CLI = ROOT / "cli" / "compass"
GOVERNANCE = ROOT / "governance"


# ---------------------------------------------------------------------------
# TRC-F5 - a project that opted into nothing sees no change
# ---------------------------------------------------------------------------

BDD_KEYS = ("bdd_runner", "bdd_features_dir", "bdd_steps_dir", "bdd_run_command")


def test_trc_f5_no_optin_means_no_change():
    # 1. the shipped config sets none of the bdd keys as live values
    cfg = yaml.safe_load((ROOT / ".compass" / "config.yml").read_text()) or {}
    project = cfg.get("project") or {}
    for key in BDD_KEYS:
        assert not project.get(key), (
            f"{key} ships with a live value; a project that edits nothing "
            f"would have opted in"
        )

    # 2. the whole mechanical gate suite passes with no bdd key set anywhere
    result = subprocess.run(
        [sys.executable, str(CLI), "ci"],
        cwd=str(ROOT), capture_output=True, text=True, timeout=300,
    )
    assert result.returncode == 0, (
        "compass ci fails on a project that opted into nothing:\n"
        f"{result.stdout[-3000:]}\n{result.stderr[-2000:]}"
    )

    # 3. no command requires a bdd key to be present. `bdd extract` is the one
    #    verb that reads them, and it must work with none of them set.
    assert "bdd_runner" not in CLI.read_text(encoding="utf-8"), (
        "the CLI branches on project.bdd_runner; extraction must not depend "
        "on a runner being declared"
    )


# ---------------------------------------------------------------------------
# TRC-F6 - the framework grew by artifacts and skills only (ADR-002)
# ---------------------------------------------------------------------------

EXPECTED_GUARDRAIL_IDS = {"G1", "G2", "G3", "G4", "G5", "S1", "S2"}

EXPECTED_GATE_IDS = {
    "verify.correctness", "verify.governance", "verify.traceability",
    "verify.regression", "verify.security", "verify.clarity", "verify.claims",
    "verify.analyze", "verify.fitness", "spike.conclude",
}

EXPECTED_READING_KEYS = {
    "blast_radius", "terrain", "magnitude", "intent", "urgency", "role",
    "touches_common",
}


def test_trc_f6_no_new_guardrail_gate_or_dimension():
    guardrails = yaml.safe_load((GOVERNANCE / "guardrails.yml").read_text())
    policy = yaml.safe_load((GOVERNANCE / "routing-policy.yml").read_text())

    # The guardrail id set is unchanged. Ids live under `defaults` (G1-G5) and
    # `spike_guardrails` (S1-S2); `checks` is a dict of named check functions,
    # which is a different thing and may legitimately grow.
    ids = {g["id"] for g in guardrails["defaults"]}
    ids |= {g["id"] for g in guardrails["spike_guardrails"]}
    ids |= {g["id"] for g in guardrails.get("project") or []}
    assert ids == EXPECTED_GUARDRAIL_IDS, (
        f"the guardrail id set changed.\n  unexpected: {sorted(ids - EXPECTED_GUARDRAIL_IDS)}"
        f"\n  missing   : {sorted(EXPECTED_GUARDRAIL_IDS - ids)}"
    )

    # the four reading dimensions plus urgency, role, touches - no fifth
    vocab = set(policy["reading_vocabulary"].keys())
    assert vocab == EXPECTED_READING_KEYS, (
        f"the reading vocabulary changed.\n  unexpected: "
        f"{sorted(vocab - EXPECTED_READING_KEYS)}\n"
        f"  missing   : {sorted(EXPECTED_READING_KEYS - vocab)}"
    )

    # no new gate id anywhere in the policy
    seen = set()
    for shape in policy["route_shapes"].values():
        seen.update(shape.get("gates", []))
    for group in ("floors", "immovable_gates", "role_rules"):
        for rule in policy["routing_guardrails"].get(group, []):
            for key in ("gate", "add_gate"):
                if rule.get(key):
                    seen.add(rule[key])
    assert seen <= EXPECTED_GATE_IDS, (
        f"new gate id(s) introduced: {sorted(seen - EXPECTED_GATE_IDS)}"
    )
