"""Fixes for the defects an independent review confirmed.

Eleven were returned at once. These tests pin the ones that had no test - each
should fail if its fix is reverted, which is the only thing that makes a fix
durable.

Spec: .compass/work/review-findings-2026-08/spec.feature.md
"""
from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
CLI = ROOT / "cli" / "compass"


def _proj(tmp_path, tasks=(), cfg="version: 1.0.0\nmode: enforced\n"):
    p = tmp_path / "p"
    (p / ".compass" / "work").mkdir(parents=True)
    shutil.copytree(ROOT / "governance", p / "governance")
    (p / ".compass" / "config.yml").write_text(cfg)
    for slug, body in tasks:
        d = p / ".compass" / "work" / slug
        d.mkdir()
        (d / "task.yml").write_text(body)
    return p


def _task(slug, route, landed, extra=""):
    return f"""schema_version: '1.1'
task: {slug}
created: '2026-01-01'
status: landed
land_timestamp: '{landed}'
readings: {{blast_radius: contained, terrain: greenfield, magnitude: small, intent: delivery, urgency: none, role: engineer, touches: []}}
route: {route}
topology: solo
fired_guardrails: []
phases: {{}}
evidence: []
gates: []
scenarios: []
changed_files: []
claims: []
backfills: []
reframes: []
friction: []
{extra}"""


def _impact(proj):
    return subprocess.run([sys.executable, str(CLI), "calibration", "--impact"],
                          cwd=str(proj), capture_output=True, text=True, timeout=90)


# --- group B: a check that verified nothing --------------------------------

def test_trc_b1_a_tag_that_binds_to_no_scenario_should_not_be_recorded_as_seen():
    """cucumber-js and behave exit 0 when a tag filter matches nothing, so a
    probe that trusted the exit code reported every scenario as bound."""
    sys.path.insert(0, str(ROOT / "cli"))
    try:
        from compass_pkg.bdd import _probe_collected
    finally:
        sys.path.remove(str(ROOT / "cli"))

    for out in ("0 scenarios\n0 steps\n", "0 scenarios (0 passed)\n",
                "no tests ran in 0.01s", "collected 0 items", ""):
        assert _probe_collected(out) is False, (
            f"a runner reporting {out!r} was read as having bound the tag")
    for out in ("3 scenarios (3 passed)\n12 steps", "collected 2 items",
                "1 scenario passed"):
        assert _probe_collected(out) is True, f"{out!r} was not read as bound"


def test_trc_b2_a_record_with_no_spec_hash_should_not_read_as_verified(tmp_path):
    proj = _proj(tmp_path, cfg="version: 1.0.0\nmode: enforced\n"
                               "project:\n  bdd_runner: pytest-bdd\n")
    d = proj / ".compass" / "work" / "t"
    d.mkdir(parents=True, exist_ok=True)
    # cross-cutting, so `blocking_when` promotes the check to blocking - at
    # `contained` it correctly reports the finding as advisory, which is a
    # different behaviour and not what this scenario is about.
    (d / "task.yml").write_text(_task("t", "standard", "2026-01-02T00:00:00Z")
                                .replace("blast_radius: contained",
                                         "blast_radius: cross-cutting")
                                .replace("scenarios: []",
                                         "scenarios:\n- {id: TRC-A1, title: x, "
                                         "intent: INT-1, tests: ['t.py::a']}"))
    (d / "spec.feature.md").write_text("# spec\n")
    (d / "evidence").mkdir()
    (d / "evidence" / "bdd-run.json").write_text(json.dumps(
        {"scenarios_seen": ["TRC-A1"], "spec_sha256": None}))
    (proj / ".compass" / "current-task").write_text("t\n")
    out = subprocess.run([sys.executable, str(CLI), "check", "--task", "t"],
                         cwd=str(proj), capture_output=True, text=True,
                         timeout=90).stdout
    line = next(l for l in out.splitlines() if "scenarios-are-executable" in l)
    assert line.strip().startswith("FAIL"), (
        f"a record with no spec hash was treated as verified:\n{line}")


# --- group C: a metric is correct or absent --------------------------------

def test_trc_c1_hotfixes_that_declare_no_target_should_not_produce_a_rate(tmp_path):
    proj = _proj(tmp_path, [
        ("d1", _task("d1", "standard", "2026-01-02T00:00:00Z")),
        ("h1", _task("h1", "hotfix", "2026-01-03T00:00:00Z")),
        ("h2", _task("h2", "hotfix", "2026-01-04T00:00:00Z"))])
    out = _impact(proj).stdout
    assert "%" not in out.split("by route")[0], (
        f"a change-fail percentage was printed when no hotfix declared a "
        f"target - that reads as perfect stability:\n{out}")
    assert "none declaring" in out, f"the reason is not stated:\n{out}"


def test_trc_c2_repeated_hotfixes_against_one_task_should_count_it_once(tmp_path):
    proj = _proj(tmp_path, [
        ("d1", _task("d1", "standard", "2026-01-02T00:00:00Z")),
        ("d2", _task("d2", "standard", "2026-01-03T00:00:00Z")),
        ("h1", _task("h1", "hotfix", "2026-01-04T00:00:00Z", "repairs: d1\n")),
        ("h2", _task("h2", "hotfix", "2026-01-05T00:00:00Z", "repairs: d1\n")),
        ("h3", _task("h3", "hotfix", "2026-01-06T00:00:00Z", "repairs: d1\n"))])
    out = _impact(proj).stdout
    assert "50.0%" in out, (
        f"three hotfixes against one of two delivery tasks is 50%, not a count "
        f"of hotfixes:\n{out}")
    import re
    for pct in re.findall(r"(\d+(?:\.\d+)?)%", out):
        assert float(pct) <= 100.0, f"a rate above 100% was printed: {pct}%"


def test_trc_c3_a_project_of_hotfixes_alone_should_not_crash(tmp_path):
    proj = _proj(tmp_path, [
        ("h1", _task("h1", "hotfix", "2026-01-04T00:00:00Z", "repairs: gone\n"))])
    r = _impact(proj)
    assert r.returncode == 0, (
        f"an advisory report exited {r.returncode}:\n{r.stdout}\n{r.stderr[-600:]}")
    assert "Traceback" not in r.stderr


def test_trc_c4_the_repairs_key_should_be_accepted_by_the_task_schema(tmp_path):
    schema = json.loads((ROOT / "schemas" / "task.schema.json").read_text())
    assert "repairs" in schema["properties"], (
        "task.schema.json is additionalProperties:false and does not declare "
        "`repairs`, so declaring it breaks compass task lint - which makes the "
        "change-fail metric unusable")
    assert "repairs:" in (ROOT / "templates" / "task.yml").read_text(), (
        "the key is not documented in the shipped task template")
    proj = _proj(tmp_path, [
        ("h1", _task("h1", "hotfix", "2026-01-04T00:00:00Z", "repairs: d1\n"))])
    r = subprocess.run([sys.executable, str(CLI), "task", "lint", "--task", "h1"],
                       cwd=str(proj), capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, f"a task declaring repairs fails lint:\n{r.stdout}"


# --- group D: malformed input is reported ----------------------------------

def test_trc_d1_a_malformed_rule_id_should_not_crash_the_router(tmp_path):
    proj = _proj(tmp_path)
    rp = proj / "governance" / "routing-policy.yml"
    d = yaml.safe_load(rp.read_text())
    d["routing_guardrails"]["floors"].append(
        {"id": ["a", "b"], "when": {"blast_radius": "critical"},
         "rationale": "malformed on purpose"})
    rp.write_text(yaml.safe_dump(d, sort_keys=False))
    r = subprocess.run(
        [sys.executable, str(CLI), "route", "evaluate",
         "--reading", "blast_radius=contained", "--reading", "terrain=greenfield",
         "--reading", "magnitude=small", "--reading", "intent=delivery",
         "--reading", "role=engineer"],
        cwd=str(proj), capture_output=True, text=True, timeout=60)
    assert "Traceback" not in r.stderr, (
        f"a malformed rule id crashed the router:\n{r.stderr[-800:]}")
    assert "FINAL ROUTE" in r.stdout, f"the route was not computed:\n{r.stdout}"


def test_trc_d2_waiving_a_framework_check_by_name_should_be_accepted(tmp_path):
    proj = _proj(tmp_path)
    gp = proj / "governance" / "guardrails.yml"
    g = yaml.safe_load(gp.read_text())
    g["checks"].pop("no-trusted-rerun", None)
    for entry in g["defaults"]:
        entry["checks"] = [c for c in entry.get("checks", [])
                           if c != "no-trusted-rerun"]
    gp.write_text(yaml.safe_dump(g, sort_keys=False))
    rp = proj / "governance" / "routing-policy.yml"
    d = yaml.safe_load(rp.read_text())
    d["routing_guardrails"]["waived"] = [
        {"id": "no-trusted-rerun", "reason": "this project reruns nothing"}]
    rp.write_text(yaml.safe_dump(d, sort_keys=False))

    r = subprocess.run([sys.executable, str(CLI), "policy", "lint"],
                       cwd=str(proj), capture_output=True, text=True, timeout=60)
    assert "does not exist" not in r.stdout, (
        f"a legitimate waiver for a framework CHECK was rejected as naming a "
        f"nonexistent rule:\n{r.stdout}")
    assert r.returncode == 0, f"a valid waiver failed the lint:\n{r.stdout}"


def test_trc_d3_normalisation_should_not_rewrite_unrelated_content(tmp_path):
    sys.path.insert(0, str(ROOT / "cli"))
    try:
        from compass_pkg import flow
    finally:
        sys.path.remove(str(ROOT / "cli"))

    proj = tmp_path / "n"
    (proj / "docs").mkdir(parents=True)
    tdir = proj / ".compass" / "work" / "t"
    tdir.mkdir(parents=True)
    (tdir / "task.yml").write_text(_task("t", "standard", "2026-01-02T00:00:00Z")
        .replace("scenarios: []",
                 "scenarios:\n- {id: SCN-1, title: 'budget  -  actual variance "
                 "is reported', intent: INT-1, tests: ['t.py::a']}"))
    flow.derive_system_spec(str(proj))
    text = (proj / "docs" / "system-spec.md").read_text()
    assert "budget  -  actual variance" in text, (
        "a title containing a padded hyphen and NO em dash was rewritten by the "
        f"house-style pass:\n{text[:600]}")
