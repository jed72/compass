"""Policy provenance in the audit trail (task governance-drift-detection).

`route.md` records which guardrails fired and why. It said nothing about WHICH
POLICY produced those answers - so a reader six months later could not tell
whether a light route reflected the terrain or stale governance.

Spec: .compass/work/governance-drift-detection/spec.feature.md (TRC-C1..C3).
"""
from __future__ import annotations

import pathlib
import re
import shutil
import subprocess
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
CLI = ROOT / "cli" / "compass"
GOVERNANCE = ROOT / "governance"
ROUTE_TEMPLATE = ROOT / "templates" / "route.md"

READINGS = ["--reading", "blast_radius=cross-cutting", "--reading",
            "terrain=brownfield-mapped", "--reading", "magnitude=standard",
            "--reading", "intent=delivery", "--reading", "role=engineer"]


def _project(tmp_path, stale=False):
    proj = tmp_path / "proj"
    (proj / ".compass" / "work").mkdir(parents=True)
    shutil.copytree(GOVERNANCE, proj / "governance")
    (proj / ".compass" / "config.yml").write_text("version: 1.0.0\nmode: enforced\n")
    if stale:
        rp = proj / "governance" / "routing-policy.yml"
        d = yaml.safe_load(rp.read_text())
        rg = d["routing_guardrails"]
        rg["floors"] = [f for f in rg["floors"]
                        if f["id"] not in ("RG-FLOOR-004", "RG-FLOOR-006")]
        d["version"] = "1.0.0"
        rp.write_text(yaml.safe_dump(d, sort_keys=False))
    return proj


def _evaluate(proj):
    return subprocess.run(
        [sys.executable, str(CLI), "route", "evaluate", *READINGS],
        cwd=str(proj), capture_output=True, text=True, timeout=60,
    )


# ---------------------------------------------------------------------------
# TRC-C1 - route evaluate reports which policy it read
# ---------------------------------------------------------------------------

def test_trc_c1_route_evaluate_should_report_which_policy_it_read(tmp_path):
    proj = _project(tmp_path)
    result = _evaluate(proj)
    assert result.returncode == 0, result.stderr

    out = result.stdout
    assert "routing-policy.yml" in out, f"the policy file is not named:\n{out}"
    version = str(yaml.safe_load((GOVERNANCE / "routing-policy.yml").read_text())["version"])
    assert version in out, f"the policy version {version} is not reported:\n{out}"


# ---------------------------------------------------------------------------
# TRC-C2 - a drifted project's route output says so
# ---------------------------------------------------------------------------

def test_trc_c2_a_drifted_projects_route_output_should_say_so(tmp_path):
    out = _evaluate(_project(tmp_path, stale=True)).stdout
    assert re.search(r"\b2\b", out), f"the count of missing rules is absent:\n{out}"
    framework_version = str(
        yaml.safe_load((GOVERNANCE / "routing-policy.yml").read_text())["version"])
    assert framework_version in out, (
        f"the framework version compared against is not named:\n{out}")
    assert "drift" in out.lower() or "missing" in out.lower(), (
        f"the output does not say the project's policy lacks rules:\n{out}")


# ---------------------------------------------------------------------------
# TRC-C3 - the route template carries a provenance field
# ---------------------------------------------------------------------------

def test_trc_c3_the_route_template_should_carry_a_provenance_field():
    text = ROUTE_TEMPLATE.read_text(encoding="utf-8")
    assert re.search(r"provenance", text, re.I), (
        "templates/route.md has no provenance field, so the audit trail cannot "
        "record which policy produced the route")
    section = text[text.lower().index("provenance"):][:1200]
    assert "routing-policy.yml" in section, (
        "the provenance field does not name the policy file")
    assert re.search(r"version", section, re.I), (
        "the provenance field does not record a version")
    assert re.search(r"drift|missing", section, re.I), (
        "the provenance field does not tell the author to record drift the CLI "
        "reported")
