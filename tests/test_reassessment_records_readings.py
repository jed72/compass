"""A corrected reading is recorded even when the approach absorbs it (issue
reassessment-log-drops-reading-only-changes).

`compass approach evaluate --write --reason "..."` logged a re-assessment only
when the COMPUTED outputs changed - approach, stages, ceiling, gates, fired
rules. The four readings were not in that snapshot, so correcting size from
`small` to `standard` was discarded, along with the reason, whenever the route
absorbed it.

That is the cheapest evidence there is that sizing was wrong: the reading moved
and someone noticed. `compass retro` reads this log to report whether
assessment systematically over- or under-sizes work, so dropping exactly those
biases the aggregate toward corrections large enough to change the route -
which are the ones already visible.

Scenario ids: TRC-A1, TRC-A2, TRC-B1 in
.compass/work/reassessment-log-drops-reading-only-changes/acceptance-criteria.md
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CLI = REPO_ROOT / "cli" / "compass"

BASE = """schema_version: "2.0"
issue: sample
created: "2026-08-30"
status: active
assessment:
  risk: contained
  familiarity: brownfield-mapped
  size: %s
  goal: delivery
  urgency: none
  role: engineer
  labels: []
evidence: []
gates: []
scenarios: []
changed_files: []
claims: []
follow_ups: []
reassessments: []
"""


def _project(tmp: Path, size: str = "small") -> Path:
    work = tmp / ".compass" / "work" / "sample"
    work.mkdir(parents=True)
    (tmp / ".compass" / "config.yml").write_text("version: 1.0.0\n", encoding="utf-8")
    (work / "manifest.yml").write_text(BASE % size, encoding="utf-8")
    return tmp


def _run(project: Path, *args):
    r = subprocess.run([sys.executable, str(CLI), *args],
                       cwd=str(project), capture_output=True, text=True, timeout=60)
    return r.returncode, r.stdout + r.stderr


def _manifest(project: Path) -> str:
    return (project / ".compass" / "work" / "sample" / "manifest.yml").read_text(
        encoding="utf-8")


def _set_size(project: Path, size: str) -> None:
    p = project / ".compass" / "work" / "sample" / "manifest.yml"
    body = p.read_text(encoding="utf-8")
    for old in ("size: small", "size: standard", "size: atomic"):
        if old in body:
            p.write_text(body.replace(old, f"size: {size}", 1), encoding="utf-8")
            return
    raise AssertionError(f"no size line found in:\n{body}")


# ---------------------------------------------------------------------------
# TRC-A1 - a corrected reading is logged when the approach does not move
# ---------------------------------------------------------------------------

def test_a_corrected_reading_is_logged_when_the_approach_does_not_move():
    with tempfile.TemporaryDirectory() as raw:
        project = _project(Path(raw), size="atomic")

        code, out = _run(project, "approach", "evaluate", "--issue", "sample", "--write")
        assert code == 0, out
        first = _manifest(project)

        # atomic -> small is absorbed: both compute `quick-fix`. That is the
        # case this scenario is about; a change that moves the route already
        # logged.
        _set_size(project, "small")
        code, out = _run(project, "approach", "evaluate", "--issue", "sample",
                         "--write", "--reason", "the work is three files, not one")
        assert code == 0, out
        after = _manifest(project)

    # The approach itself must not have moved, or this scenario is testing the
    # case that already worked.
    def route(body):
        return [l for l in body.splitlines() if l.startswith("delivery_approach:")]
    assert route(first) == route(after), (
        f"the computed approach changed between the two runs, so this "
        f"scenario is exercising the case that already logged: "
        f"{route(first)} -> {route(after)}")

    assert "reassessments: []" not in after, (
        "the re-assessment log is still empty after a reading was corrected. "
        "A correction the route absorbed is still a correction, and it is the "
        "cheapest evidence there is that sizing was wrong")
    assert "the work is three files, not one" in after, (
        f"the reason was discarded:\n{after}")
    assert "atomic" in after and "small" in after, (
        "the entry does not say which reading changed and from what to what")


# ---------------------------------------------------------------------------
# TRC-A2 - the reason is not discarded
# ---------------------------------------------------------------------------

def test_the_reason_is_not_discarded():
    with tempfile.TemporaryDirectory() as raw:
        project = _project(Path(raw), size="atomic")
        _run(project, "approach", "evaluate", "--issue", "sample", "--write")
        _set_size(project, "small")
        code, out = _run(project, "approach", "evaluate", "--issue", "sample",
                         "--write", "--reason", "corrected after reading the files")

    assert code == 0, out
    assert "was NOT recorded" not in out, (
        f"the CLI still reports the reason as discarded:\n{out}")


# ---------------------------------------------------------------------------
# TRC-B1 - a first write records no re-assessment
# ---------------------------------------------------------------------------

def test_a_first_write_records_no_re_assessment():
    """Materialising an approach is not a re-assessment.

    The guard this replaces got that right and must keep getting it right: a
    first `--write` fills in phases and gates that were never there, and
    logging it would put noise into the signal the log exists to sharpen.
    """
    with tempfile.TemporaryDirectory() as raw:
        project = _project(Path(raw), size="small")
        code, out = _run(project, "approach", "evaluate", "--issue", "sample", "--write")
        assert code == 0, out
        after = _manifest(project)

    assert "reassessments: []" in after, (
        f"a first write recorded a re-assessment. There is no earlier reading "
        f"for it to differ from:\n{after}")
