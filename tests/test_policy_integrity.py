"""The integrity rule: a declared guardrail's check must be implemented in
the CLI's CHECK_FNS. The contract (guarantee 2 in safety-contract.md) says
this must fail in BOTH `compass policy lint` and `compass check` - otherwise
a team could believe they have a hard guardrail when in fact none runs.
"""
from __future__ import annotations

from pathlib import Path

import yaml


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
    """The same defect must also be caught by `compass check` at run time -
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
        "assessment": {
            "risk": "contained",
            "familiarity": "brownfield-mapped",
            "size": "small",
            "intent": "delivery",
        },
        "delivery_approach": "express",
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
# TRC-E6 - guardrails.yml registers the new DoD check
# ---------------------------------------------------------------------------

def test_dod_check_registered(run_cli):
    """TRC-E6: governance/guardrails.yml must contain a check entry named
    'dod-evidence-typed', and the CLI must implement CHECK_FNS for that key.
    `compass policy lint` must still pass - the new entry is well-formed."""
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
        f"assertion), not under {registered_guardrail_id!r} - a check belongs "
        f"in architecture-notes.md")

    # 3. The CLI must implement CHECK_FNS for this key - `policy lint` verifies it
    r = run_cli("policy", "lint")
    assert r.returncode == 0, (
        f"policy lint must pass after adding dod-evidence-typed: {r}")


# ---------------------------------------------------------------------------
# TRC-F2 - Guardrail count is still five
# ---------------------------------------------------------------------------

def test_guardrail_count_unchanged():
    """TRC-F2: No sixth guardrail has been added.

    governance/guardrails.md must list exactly five guardrails (G1..G5).
    governance/guardrails.yml must have no guardrail entries beyond G1..G5
    in its `defaults:` block.

    This is a regression test over the framework's shipped content - it
    verifies Inv-2 (defined in architecture/decisions/README.md) is preserved.
    """
    import re

    framework_root = Path(__file__).resolve().parent.parent
    guardrails_md = framework_root / "governance" / "guardrails.md"
    guardrails_yml = framework_root / "governance" / "guardrails.yml"

    assert guardrails_md.is_file(), f"not found: {guardrails_md}"
    assert guardrails_yml.is_file(), f"not found: {guardrails_yml}"

    # --- guardrails.md: parse the canonical G<N> headings -------------------
    # The canonical guardrails use H3 headings "### G<N> - <name>".
    md_text = guardrails_md.read_text(encoding="utf-8")
    g_headings = re.findall(r"^###\s+(G\d+)", md_text, re.MULTILINE)
    assert len(g_headings) == 5, (
        f"Expected exactly 5 guardrail headings (G1..G5) in guardrails.md, "
        f"found {len(g_headings)}: {g_headings}. "
        f"Inv-2: the principle is 'few guardrails'; "
        f"adding a sixth requires explicit review."
    )
    assert sorted(g_headings) == ["G1", "G2", "G3", "G4", "G5"], (
        f"Guardrail headings must be G1..G5, got: {g_headings}"
    )

    # --- guardrails.yml: assert defaults block has exactly G1..G5 -----------
    yml_data = yaml.safe_load(guardrails_yml.read_text(encoding="utf-8"))
    defaults = yml_data.get("defaults", [])
    default_ids = [g.get("id") for g in defaults]
    assert len(default_ids) == 5, (
        f"Expected exactly 5 entries in guardrails.yml `defaults:`, "
        f"found {len(default_ids)}: {default_ids}"
    )
    assert sorted(default_ids) == ["G1", "G2", "G3", "G4", "G5"], (
        f"guardrails.yml `defaults:` must have G1..G5, got: {default_ids}"
    )

    # --- guardrails.yml: no project guardrail id collides with G1..G5 ------
    project_gs = yml_data.get("project", []) or []
    project_ids = [g.get("id") for g in project_gs]
    g_pattern = re.compile(r"^G\d+$")
    for pid in project_ids:
        assert not g_pattern.match(str(pid)), (
            f"Project guardrail '{pid}' uses the G<N> namespace reserved for "
            f"the five defaults. Use a different prefix (e.g. Q1, P1)."
        )


def test_guardrail_ids_in_yml_match_md():
    """TRC-F2 (supplementary): the five G-ids in guardrails.yml match those
    in guardrails.md - no silent split between the prose and the machine file.
    """
    import re

    framework_root = Path(__file__).resolve().parent.parent
    guardrails_md = framework_root / "governance" / "guardrails.md"
    guardrails_yml = framework_root / "governance" / "guardrails.yml"

    md_text = guardrails_md.read_text(encoding="utf-8")
    g_headings = set(re.findall(r"^###\s+(G\d+)", md_text, re.MULTILINE))

    yml_data = yaml.safe_load(guardrails_yml.read_text(encoding="utf-8"))
    defaults = yml_data.get("defaults", [])
    yml_ids = {g.get("id") for g in defaults}

    assert g_headings == yml_ids, (
        f"Mismatch between guardrails.md headings {sorted(g_headings)} "
        f"and guardrails.yml defaults ids {sorted(yml_ids)}"
    )
