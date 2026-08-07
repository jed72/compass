"""Slice 5b of the v2 rename: the CLI speaks the v2 register.

The content specification is the ratified verb map in the slice's issue
archive: approach evaluate, follow-up resolve (states outstanding ->
resolved), retro, design lint, issue lint/receipt/set-status, ship-commit,
and the new terminology verb. Retired verbs fail machine-tolerably (exit 2,
one stderr line, empty stdout) with pointer text carried as data in the
scan-exempt cli/migrate-map.yml. The --task flag renames to --issue with
the old spelling tolerated for one major version. The cli/ scan surface is
enforced and widened to cli/compass_pkg/ string literals, and the receipt
speaks v2 change-type names and shows recorded topology overrides.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).parent.parent
CLI = REPO_ROOT / "cli" / "compass"

V2_SPINE = {
    "schema_version": "2.0", "task": "t", "created": "2026-08-07",
    "status": "active",
    "assessment": {"risk": "cross-cutting", "familiarity": "brownfield-mapped",
                   "size": "large", "goal": "delivery",
                   "role": "engineer", "labels": []},
    "delivery_approach": "expedition", "topology": "swarm",
    "policy_rules_fired": [],
    "stages": {}, "evidence": [], "gates": [], "scenarios": [],
    "changed_files": [], "claims": [],
    "follow_ups": [{"id": "BF-1", "description": "promote the test",
                    "status": "outstanding"}],
    "reassessments": [], "friction": [],
}


def _project(tmp_path, spine=None, approach_md="# Delivery approach\n"):
    root = tmp_path / "proj"
    shutil.copytree(REPO_ROOT / "governance", root / "governance")
    (root / ".compass").mkdir(parents=True)
    (root / ".compass" / "config.yml").write_text(
        "version: 1.0.0\nmode: enforced\n")
    d = root / ".compass" / "work" / "t"
    d.mkdir(parents=True)
    (d / "delivery-approach.md").write_text(approach_md)
    (d / "task.yml").write_text(
        yaml.safe_dump(spine or dict(V2_SPINE), sort_keys=False))
    (root / ".compass" / "current-task").write_text("t\n")
    return root


def _run(root, *args):
    return subprocess.run([sys.executable, str(CLI), *args], cwd=str(root),
                          capture_output=True, text=True, timeout=60)


def test_the_v2_verbs_exist_and_work(tmp_path):
    """TRC-1: each renamed verb performs its predecessor's behaviour, and
    terminology renders the vocabulary file."""
    root = _project(tmp_path)
    r = _run(root, "approach", "evaluate", "--issue", "t", "--write")
    assert r.returncode == 0, r.stderr[-400:]
    out = yaml.safe_load(
        (root / ".compass" / "work" / "t" / "task.yml").read_text())
    assert out.get("delivery_approach"), "approach evaluate wrote nothing"

    r = _run(root, "issue", "lint", "--issue", "t")
    assert r.returncode == 0, r.stderr[-400:]
    r = _run(root, "issue", "receipt", "--issue", "t")
    assert r.returncode == 0, r.stderr[-400:]
    r = _run(root, "design", "lint", "--help")
    assert r.returncode == 0
    r = _run(root, "retro")
    assert r.returncode == 0, r.stderr[-400:]
    r = _run(root, "follow-up", "resolve", "--issue", "t", "BF-1")
    assert r.returncode == 0, r.stderr[-400:]
    r = _run(root, "terminology", "receipt")
    assert r.returncode == 0, r.stderr[-400:]
    assert "receipt" in r.stdout.lower()
    r = _run(root, "ship-commit", "--help")
    assert r.returncode == 0
    assert "ship" in r.stdout.lower()


def test_a_retired_verb_fails_loudly_and_legibly(tmp_path):
    """TRC-2: a retired verb exits 2 with exactly one stderr line naming
    the replacement, and stdout stays empty - a script can never mistake
    the pointer for success."""
    root = _project(tmp_path)
    cases = {
        ("route", "evaluate"): "approach",
        ("backfill", "pay"): "follow-up",
        ("calibration",): "retro",
        ("land-commit",): "ship-commit",
        ("task", "lint"): "issue",
        ("plan", "lint"): "design",
    }
    for argv, replacement in cases.items():
        r = _run(root, *argv)
        assert r.returncode == 2, (
            f"compass {' '.join(argv)}: expected exit 2, got "
            f"{r.returncode}\nstdout: {r.stdout[:200]}\nstderr: {r.stderr[:200]}")
        assert r.stdout.strip() == "", (
            f"compass {' '.join(argv)}: pointer must not write stdout")
        lines = [l for l in r.stderr.splitlines() if l.strip()]
        assert len(lines) == 1, (
            f"compass {' '.join(argv)}: expected one stderr line, got "
            f"{len(lines)}: {r.stderr[:300]}")
        assert replacement in lines[0], (
            f"compass {' '.join(argv)}: pointer does not name "
            f"'{replacement}': {lines[0]}")


def test_the_issue_flag_with_task_tolerated(tmp_path):
    """TRC-3: --issue and --task resolve the same issue; the help text
    teaches --issue."""
    root = _project(tmp_path)
    r_issue = _run(root, "check", "--issue", "t")
    r_task = _run(root, "check", "--task", "t")
    assert r_issue.returncode == r_task.returncode, (
        "--issue and --task disagree:\n" + r_issue.stderr[-200:]
        + r_task.stderr[-200:])
    r = _run(root, "check", "--help")
    assert "--issue" in r.stdout, "check --help does not document --issue"


def test_follow_up_states_outstanding_resolved_with_1x_readable(tmp_path):
    """TRC-4: the resolver writes 'resolved'; a 1.x spine carrying
    owed/paid is normalised read-side so checks still see the truth."""
    root = _project(tmp_path)
    r = _run(root, "follow-up", "resolve", "--issue", "t", "BF-1")
    assert r.returncode == 0, r.stderr[-400:]
    out = yaml.safe_load(
        (root / ".compass" / "work" / "t" / "task.yml").read_text())
    assert out["follow_ups"][0]["status"] == "resolved", out["follow_ups"]

    sys.path.insert(0, str(REPO_ROOT / "cli"))
    from compass_pkg.core import normalize_spine
    old = dict(V2_SPINE)
    old["follow_ups"] = [
        {"id": "BF-1", "description": "d", "status": "owed"},
        {"id": "BF-2", "description": "d", "status": "paid"},
    ]
    norm = normalize_spine(old)
    states = [f["status"] for f in norm["follow_ups"]]
    assert states == ["outstanding", "resolved"], (
        f"1.x values not normalised: {states}")


OVERRIDE_MD = """# Delivery approach - t

## Topology: human override recorded

| What was overridden | From -> To | Who | Why |
|---|---|---|---|
| Topology | swarm -> solo | maintainer, 2026-08-07 | interlocked rename |
"""


def test_output_speaks_v2_shape_names_and_receipt_shows_overrides(tmp_path):
    """TRC-5: the receipt prints 'initiative' for the machine value
    'expedition' and shows the recorded topology override; the evaluator's
    output uses v2 shape names too."""
    root = _project(tmp_path, approach_md=OVERRIDE_MD)
    r = _run(root, "issue", "receipt", "--issue", "t")
    assert r.returncode == 0, r.stderr[-400:]
    assert "initiative" in r.stdout, (
        "receipt does not translate 'expedition' to 'initiative':\n"
        + r.stdout)
    assert "expedition" not in r.stdout.lower(), (
        "receipt still prints the machine value 'expedition':\n" + r.stdout)
    assert re.search(r"overridden:?\s+solo", r.stdout), (
        "receipt does not show the recorded topology override:\n" + r.stdout)

    r = _run(root, "approach", "evaluate", "--issue", "t")
    assert r.returncode == 0, r.stderr[-400:]
    assert "expedition" not in r.stdout.lower(), (
        "the evaluator still prints v1 shape names:\n" + r.stdout)


def test_vocabulary_carries_receipt_follow_up_and_bump():
    """TRC-6: version past 2.0.0-pre6; a receipt term with the evidence
    disambiguation; the follow-up entry speaks outstanding/resolved."""
    doc = yaml.safe_load(
        (REPO_ROOT / "governance" / "terminology.yml").read_text())
    m = re.fullmatch(r"2\.0\.0-pre(\d+)", str(doc["version"]))
    assert m and int(m.group(1)) > 6, (
        f"version is {doc['version']} - this diff carries a bump past pre6")
    receipt = doc["terms"].get("receipt")
    assert receipt, "no receipt term in the vocabulary"
    assert "evidence" in str(receipt.get("not", "")), (
        "the receipt term lacks the evidence disambiguation")
    follow_up = doc["terms"]["follow-up"]
    joined = str(follow_up)
    assert "outstanding" in joined and "resolved" in joined, (
        "the follow-up entry does not speak outstanding/resolved")


def test_cli_surface_enforced_and_widened():
    """TRC-7: cli/compass left pending (file and baseline);
    cli/compass_pkg/ is a scanned surface; the migrate map is exempt."""
    from test_terminology import PENDING_BASELINE
    scan = yaml.safe_load(
        (REPO_ROOT / "governance" / "terminology.yml").read_text())["scan"]
    assert "cli/compass" not in scan["pending_surfaces"], (
        "cli/compass is still pending in terminology.yml")
    assert "cli/compass" not in PENDING_BASELINE, (
        "cli/compass is still in the committed baseline")
    assert "cli/compass_pkg/" in scan["surfaces"], (
        "the scan surface was not widened to cli/compass_pkg/")
    assert any(e.startswith("cli/migrate-map") for e in scan["exempt"]), (
        "cli/migrate-map.yml is not exempt - the pointer data would be "
        "scanned")
    assert (REPO_ROOT / "cli" / "migrate-map.yml").is_file(), (
        "cli/migrate-map.yml does not exist")


def test_compass_backfill_tolerance_re_tightened():
    """TRC-8: 'compass backfill' in prose is flagged like any other use -
    the lookbehind tolerance ended with the verb rename."""
    from test_terminology import BAN_PATTERNS
    line = "settle it with compass " + "backfill pay before shipping"
    hits = [p for p in BAN_PATTERNS["backfill"] if p.search(line)]
    assert hits, (
        "'compass backfill' in prose is still tolerated - the CLI-voice "
        "slice ends that tolerance")
