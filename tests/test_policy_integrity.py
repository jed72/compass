"""The integrity rule: a declared guardrail's check must be implemented in
the CLI's CHECK_FNS. The contract (guarantee 2 in safety-contract.md) says
this must fail in BOTH `compass policy lint` and `compass check` — otherwise
a team could believe they have a hard guardrail when in fact none runs.
"""
from __future__ import annotations


def test_policy_lint_passes_on_shipped_governance(run_cli):
    """The governance/ that ships should always lint clean."""
    r = run_cli("policy", "lint")
    assert r.returncode == 0, r
    assert "PASS" in r.stdout


def test_policy_lint_fails_on_missing_check_implementation(run_cli, edit_governance):
    """Add a guardrail that references a check name not in CHECK_FNS;
    `compass policy lint` must fail and the message must say WHY."""
    with edit_governance("guardrails.yml") as gr:
        gr.setdefault("checks", {})
        gr["checks"]["my-fake-check"] = {"description": "fake"}
        gr.setdefault("project", []).append({
            "id": "Q-FAKE",
            "name": "fake guardrail",
            "statement": "this references an unimplemented check",
            "checks": ["my-fake-check"],
            "checked_at": ["verify"],
        })
    r = run_cli("policy", "lint")
    assert r.returncode != 0, r
    assert "FAIL" in r.stdout, r
    combined = (r.stdout + r.stderr).lower()
    assert "my-fake-check" in combined, r
    assert "check_fns" in combined or "not implement" in combined, r


def test_check_fails_on_missing_check_implementation(run_cli, edit_governance, make_task):
    """The same defect must also be caught by `compass check` at run time —
    not just at lint. This is the integrity belt-and-braces."""
    with edit_governance("guardrails.yml") as gr:
        gr.setdefault("checks", {})
        gr["checks"]["my-fake-check"] = {"description": "fake"}
        gr.setdefault("project", []).append({
            "id": "Q-FAKE",
            "name": "fake guardrail",
            "statement": "no implementation",
            "checks": ["my-fake-check"],
            "checked_at": ["verify"],
        })
    # set up a minimum task so `compass check` has something to run against
    make_task("integrity-probe", {
        "readings": {
            "blast_radius": "contained",
            "terrain": "brownfield-mapped",
            "magnitude": "small",
            "intent": "delivery",
        },
        "route": "express",
        "scenarios": [{"id": "SCN-001", "intent": "INT-1",
                       "tests": ["tests/test_x.py::test_y"]}],
        "gates": [{"id": "verify.correctness", "status": "pending"}],
    })
    r = run_cli("check", "--task", "integrity-probe")
    # in enforced mode an unimplemented check is a hard fail
    assert r.returncode != 0, r
    combined = (r.stdout + r.stderr).lower()
    assert "my-fake-check" in combined, r
    assert "no cli implementation" in combined or "not implement" in combined, r


def test_policy_lint_jsonschema_validation_runs_when_installed(run_cli):
    """When jsonschema is installed (it is, in this test env), the policy
    lint command should not warn that it is not installed."""
    r = run_cli("policy", "lint")
    assert r.returncode == 0, r
    assert "jsonschema not installed" not in r.stdout, r


def test_policy_lint_fails_on_invalid_yaml_structure(run_cli, edit_governance):
    """A guardrail with no `checks:` list is not a guardrail (it is a
    strategy). policy lint must catch that."""
    with edit_governance("guardrails.yml") as gr:
        gr.setdefault("project", []).append({
            "id": "Q-BARE",
            "name": "guardrail without checks",
            "statement": "...",
            "checked_at": ["verify"],
        })
    r = run_cli("policy", "lint")
    assert r.returncode != 0, r
    assert "FAIL" in r.stdout, r


# ---------------------------------------------------------------------------
# TRC-E6 — guardrails.yml registers the new DoD check
# ---------------------------------------------------------------------------

def test_dod_check_registered(run_cli):
    """TRC-E6: governance/guardrails.yml must contain a check entry named
    'dod-evidence-typed', and the CLI must implement CHECK_FNS for that key.
    `compass policy lint` must still pass — the new entry is well-formed."""
    import yaml
    from pathlib import Path

    # Locate the shipped guardrails.yml (the one the CLI and tests use)
    framework_root = Path(__file__).resolve().parent.parent
    gr_path = framework_root / "governance" / "guardrails.yml"
    gr = yaml.safe_load(gr_path.read_text())

    # 1. The check entry must exist under `checks:`
    assert "dod-evidence-typed" in (gr.get("checks") or {}), (
        "guardrails.yml `checks:` must declare 'dod-evidence-typed'")

    # 2. It must be referenced by at least one guardrail (must be under G4)
    all_guardrails = (
        list(gr.get("defaults") or []) +
        list(gr.get("project") or [])
    )
    registered_guardrail_id = None
    for g in all_guardrails:
        if "dod-evidence-typed" in (g.get("checks") or []):
            registered_guardrail_id = g.get("id")
            break
    assert registered_guardrail_id is not None, (
        "dod-evidence-typed must be referenced in at least one guardrail in "
        "guardrails.yml `defaults:` or `project:`")
    assert registered_guardrail_id == "G4", (
        f"dod-evidence-typed must be registered under G4 (evidence, not "
        f"assertion), not under {registered_guardrail_id!r} — see B-Risk 4 "
        f"in architecture-notes.md")

    # 3. The CLI must implement CHECK_FNS for this key — `policy lint` verifies it
    r = run_cli("policy", "lint")
    assert r.returncode == 0, (
        f"policy lint must pass after adding dod-evidence-typed: {r}")
