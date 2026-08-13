"""Schema 2.0 - the machine spine speaks the frozen v2 vocabulary.

The machine-spine slice of the v2 plan: the issue spine's keys take their
v2 names (assessment/risk/familiarity/size/goal, labels, delivery_approach,
stages, policy_rules_fired, follow_ups, reassessments), writers emit
schema_version "2.0", readers accept a 1.x spine by normalising its keys on
load (the substrate the full migration tool wraps in its own slice), and
the repository's own work archive - plus the example work dirs - migrates
in the same change. Two transition aids retire with the archive migration:
the artifact-name v1 fallback in the runtime resolver, and the
templates/task.yml scan exemption.

No behaviour change: same spine, new names, the suite moved in lockstep.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "cli"))
CLI = REPO_ROOT / "cli" / "compass"

V1_TOP_KEYS = {"readings", "route", "phases", "fired_guardrails",
               "backfills", "reframes"}
V1_ASSESSMENT_KEYS = {"blast_radius", "terrain", "magnitude", "intent",
                      "touches"}

V2_SPINE = {
    "schema_version": "2.0", "task": "t", "created": "2026-08-07",
    "status": "active",
    "assessment": {"risk": "contained", "familiarity": "greenfield",
                   "size": "small", "goal": "delivery",
                   "role": "engineer", "labels": []},
    "delivery_approach": None, "topology": None, "policy_rules_fired": [],
    "stages": {}, "evidence": [], "gates": [], "scenarios": [],
    "changed_files": [], "claims": [], "follow_ups": [],
    "reassessments": [], "friction": [],
}

V1_SPINE = {
    "schema_version": "1.1", "task": "t", "created": "2026-08-07",
    "status": "active",
    "readings": {"blast_radius": "contained", "terrain": "greenfield",
                 "magnitude": "small", "intent": "delivery",
                 "role": "engineer", "touches": []},
    "route": None, "topology": None, "fired_guardrails": [],
    "phases": {}, "evidence": [], "gates": [], "scenarios": [],
    "changed_files": [], "claims": [], "backfills": [],
    "reframes": [], "friction": [],
}


def _project(tmp_path, spine):
    import shutil
    root = tmp_path / "proj"
    shutil.copytree(REPO_ROOT / "governance", root / "governance")
    (root / ".compass").mkdir(parents=True)
    (root / ".compass" / "config.yml").write_text("version: 1.0.0\nmode: enforced\n")
    d = root / ".compass" / "work" / "t"
    d.mkdir(parents=True)
    (d / "delivery-approach.md").write_text("# Delivery approach\n")
    (d / "task.yml").write_text(yaml.safe_dump(spine, sort_keys=False))
    (root / ".compass" / "current-task").write_text("t\n")
    return root


def _run(root, *args):
    return subprocess.run([sys.executable, str(CLI), *args], cwd=str(root),
                          capture_output=True, text=True, timeout=60)


def test_route_evaluate_writes_a_v2_spine(tmp_path):
    """TRC-A1: the evaluator reads a v2 spine and folds its results back
    under the v2 keys, stamping schema 2.0 - no v1 key appears in what it
    writes."""
    root = _project(tmp_path, dict(V2_SPINE))
    r = _run(root, "approach", "evaluate", "--issue", "t", "--write")
    assert r.returncode == 0, r.stderr[-500:] + r.stdout[-500:]
    out = yaml.safe_load((root / ".compass" / "work" / "t" / "task.yml").read_text())
    assert str(out.get("schema_version")) == "2.0"
    assert out.get("delivery_approach"), "no delivery_approach recorded"
    assert out.get("stages"), "no stages recorded"
    assert "policy_rules_fired" in out
    leaked = (V1_TOP_KEYS & set(out)) | (V1_ASSESSMENT_KEYS & set(out.get("assessment", {})))
    assert not leaked, f"v1 keys leaked into a written spine: {sorted(leaked)}"


def test_a_v1_spine_is_still_readable(tmp_path):
    """TRC-A2: a 1.x spine loads by key normalisation - the evaluator works,
    and what it writes back is a v2 spine. This is the substrate the full
    migration tool wraps; an un-migrated tree degrades gracefully instead
    of crashing."""
    root = _project(tmp_path, dict(V1_SPINE))
    r = _run(root, "approach", "evaluate", "--issue", "t", "--write")
    assert r.returncode == 0, r.stderr[-500:] + r.stdout[-500:]
    out = yaml.safe_load((root / ".compass" / "work" / "t" / "task.yml").read_text())
    assert str(out.get("schema_version")) == "2.0"
    assert out.get("assessment", {}).get("risk") == "contained"
    assert not (V1_TOP_KEYS & set(out)), "normalisation left v1 top-level keys"


def test_the_repository_archive_speaks_schema_2():
    """TRC-A3: every spine in the repository's own work archive and in the
    example work dirs carries v2 keys - the repo is a migration fixture,
    and the migration ran."""
    stale = []
    for pattern in [".compass/work/*/task.yml",
                    "examples/*/.compass/work/*/task.yml",
                    "examples/bdd-adapters/*/.compass/work/*/task.yml"]:
        for p in REPO_ROOT.glob(pattern):
            d = yaml.safe_load(p.read_text()) or {}
            bad = (V1_TOP_KEYS & set(d)) | (V1_ASSESSMENT_KEYS & set(d.get("assessment", {})))
            if "readings" in d or bad:
                stale.append(f"{p.relative_to(REPO_ROOT)}: {sorted(bad) or 'readings block'}")
    assert not stale, "un-migrated spines:\n  " + "\n  ".join(stale[:12])


def test_the_archive_carries_v2_artifact_names():
    """TRC-A4: the archive migration renamed the per-issue artifact files
    too - no route.md, spec.feature.md, brief.md, clarifications.md, or
    plan.md remains in any work dir."""
    old_names = {"route.md", "spec.feature.md", "brief.md",
                 "clarifications.md", "plan.md", "spec.feature"}
    stale = []
    for pattern in [".compass/work/*", "examples/*/.compass/work/*",
                    "examples/bdd-adapters/*/.compass/work/*"]:
        for d in REPO_ROOT.glob(pattern):
            if not d.is_dir():
                continue
            for f in d.iterdir():
                if f.name in old_names:
                    stale.append(str(f.relative_to(REPO_ROOT)))
    assert not stale, "un-renamed artifacts:\n  " + "\n  ".join(stale[:12])


def test_the_artifact_name_fallback_is_retired():
    """TRC-A5: with the archive migrated, the runtime resolver no longer
    consults v1 filenames - the migration module owns the old-name map
    now, and the resolver resolves v2 names only."""
    from compass_pkg import core
    assert not hasattr(core, "ARTIFACT_FALLBACKS"), (
        "core still carries the v1 filename fallback map; it moved to the "
        "migration module when the archive migrated"
    )


def test_templates_task_yml_speaks_v2_and_is_scanned():
    """TRC-A6: the spine template carries v2 keys, and its scan exemption
    is retired - the vocabulary scan covers it like any other template."""
    t = yaml.safe_load((REPO_ROOT / "templates" / "task.yml").read_text())
    assert "assessment" in t and "readings" not in t, (
        "templates/task.yml still carries the v1 assessment block"
    )
    scan = yaml.safe_load(
        (REPO_ROOT / "governance" / "terminology.yml").read_text())["scan"]
    assert "templates/task.yml" not in scan.get("exempt", []), (
        "the templates/task.yml scan exemption should retire with schema 2.0"
    )


def test_policy_keys_speak_v2():
    """TRC-A7: the routing policy's machine keys follow the spine - the
    dimension keys in shapes and rules use risk/familiarity/size/goal and
    labels, not the v1 names."""
    text = (REPO_ROOT / "governance" / "routing-policy.yml").read_text()
    for stale in ("blast_radius", "terrain:", "magnitude", "touches_any",
                  "touches_common"):
        assert stale not in text, f"routing-policy.yml still says {stale!r}"
