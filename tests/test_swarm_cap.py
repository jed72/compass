"""R4 - multiagent.sh derives the worktree cap from structured manifest.yml truth
(readings.blast_radius + fired_guardrails), not by grepping route.md prose
(which false-positives on 'did-not-fire' audit notes), and counts only
worktree-provisioning streams.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent
SWARM = FRAMEWORK_ROOT / "scripts" / "multiagent.sh"


def _git(cwd, *a):
    return subprocess.run(["git", *a], cwd=str(cwd), capture_output=True, text=True)


def _repo(tmp_path):
    d = tmp_path / "repo"
    d.mkdir()
    _git(d, "init", "-q")
    _git(d, "config", "user.email", "t@e")
    _git(d, "config", "user.name", "t")
    (d / "f").write_text("x")
    _git(d, "add", "-A")
    _git(d, "commit", "-q", "-m", "init")
    cfg = d / ".compass"
    (cfg / "work").mkdir(parents=True)
    (cfg / "config.yml").write_text(
        "version: 1.0.0\nmode: enforced\nswarm:\n  worktree_root: ../wt\n  max_worktrees: 6\n")
    return d


def _task(d, slug, *, risk=None, capped=False, readings=True):
    td = d / ".compass" / "work" / slug
    td.mkdir(parents=True, exist_ok=True)
    body = {"task": slug}
    if readings:
        rd = {"familiarity": "brownfield-mapped", "size": "large", "intent": "delivery"}
        if risk:
            rd["risk"] = risk
        body["assessment"] = rd
    fired = ("- id: RP-CAP-001\n  kind: cap\n" if capped else "")
    import yaml
    (td / "manifest.yml").write_text(yaml.safe_dump(body, sort_keys=False) +
                                 ("fired_guardrails:\n" + fired if fired else "fired_guardrails: []\n"))
    return td


def _route(td, prose=""):
    (td / "delivery-approach.md").write_text("# Route\n\n" + prose + "\n")


def _map(td, slug, n_streams, *, extra_nonworktree=False):
    rows = ["# Distribution Map", "", "## 3. mapping", ""]
    for i in range(1, n_streams + 1):
        rows.append(f"| stream-{i} | U{i} | TRC-{i} | compass/{slug}/stream-{i} |")
    if extra_nonworktree:
        rows.append(f"| stream-int | integration/verify - not a parallel worktree | - | n/a |")
    (td / "distribution-map.md").write_text("\n".join(rows) + "\n")


def _run(repo, slug):
    return subprocess.run(["bash", str(SWARM), slug, "--dry-run"],
                          cwd=str(repo), capture_output=True, text=True)


# did-not-fire prose that the OLD grep false-positived on:
_PROSE = "RP-CAP-001 (`blast_radius: critical`) - not matched; blast radius is contained."


def test_did_not_fire_note_caps_to_one_today(tmp_path):
    """TRC-R4-1 (regression guard): a route.md 'did-not-fire' note quoting
    `blast_radius: critical` no longer collapses the cap - the reading is
    contained, so the swarm provisions."""
    repo = _repo(tmp_path)
    td = _task(repo, "t1", risk="contained")
    _route(td, _PROSE)
    _map(td, "t1", 5)
    r = _run(repo, "t1")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "but the cap is 1" not in (r.stdout + r.stderr), r.stdout + r.stderr


def test_cap_from_readings_ignores_prose(tmp_path):
    """TRC-R4-2: the cap honours readings.blast_radius (contained → full cap),
    not the critical token in route.md prose."""
    repo = _repo(tmp_path)
    td = _task(repo, "t2", risk="contained")
    _route(td, _PROSE)
    _map(td, "t2", 5)
    r = _run(repo, "t2")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "route cap 6" in (r.stdout + r.stderr), r.stdout + r.stderr


def test_critical_reading_caps_to_one(tmp_path):
    """TRC-R4-3: a genuinely critical task (RP-CAP-001 fired) still caps to 1."""
    repo = _repo(tmp_path)
    td = _task(repo, "t3", risk="critical", capped=True)
    _route(td, "blast radius is critical")
    _map(td, "t3", 4)
    r = _run(repo, "t3")
    assert r.returncode != 0, r.stdout + r.stderr
    assert "4 subtasks but the cap is 1" in (r.stdout + r.stderr), r.stdout + r.stderr


def test_non_worktree_stream_excluded_from_count(tmp_path):
    """TRC-R4-4: a stream marked 'not a parallel worktree' is not counted toward
    the cap."""
    repo = _repo(tmp_path)
    td = _task(repo, "t4", risk="critical", capped=True)   # cap = 1
    _route(td, "critical")
    _map(td, "t4", 1, extra_nonworktree=True)   # 1 worktree + 1 integration row
    r = _run(repo, "t4")
    assert r.returncode == 0, r.stdout + r.stderr   # counted worktrees = 1 <= cap 1


def test_missing_readings_errors_not_silent_cap(tmp_path):
    """TRC-R4-F1: absent readings.blast_radius is a hard error - never a silent
    cap=1 and never a fall back to grepping route.md prose."""
    repo = _repo(tmp_path)
    td = _task(repo, "t5", risk=None)   # readings present but no blast_radius
    _route(td, _PROSE)
    _map(td, "t5", 3)
    r = _run(repo, "t5")
    assert r.returncode != 0, r.stdout + r.stderr
    combined = r.stdout + r.stderr
    assert "blast_radius" in combined or "manifest.yml" in combined, combined
