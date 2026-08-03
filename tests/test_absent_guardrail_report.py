"""An omitted guardrail is reported, not silent (task governance-drift-detection).

The field report said `compass check` prints "not applicable for these readings
- skipped" both when a guardrail genuinely does not apply and when the floor
that would have triggered it is missing. That premise is wrong: G5's
`applies_when` keys on the READINGS, not on any floor, so no missing floor can
change its applicability, and the message is correct where it is printed.

The real defect is worse. A guardrail ABSENT from the project's file produced no
output at all. Reproduced: on a task reading `touches: [auth]`, against a
guardrails.yml with G5 removed, `compass check` printed G1 through G4 and
returned its normal result. Not an ambiguous label - silence, on the exact
surface G5 exists to guard.

Spec: .compass/work/governance-drift-detection/spec.feature.md (TRC-D1, D2).
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
CLI = ROOT / "cli" / "compass"
GOVERNANCE = ROOT / "governance"

TASK = """schema_version: '1.1'
task: t
created: '2026-08-03'
status: active
readings:
  blast_radius: contained
  terrain: greenfield
  magnitude: small
  intent: delivery
  urgency: none
  role: engineer
  touches: [{touches}]
route: standard
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
"""


def _project(tmp_path, *, touches="", drop_g5=False):
    proj = tmp_path / "proj"
    (proj / ".compass" / "work" / "t").mkdir(parents=True)
    shutil.copytree(GOVERNANCE, proj / "governance")
    (proj / ".compass" / "config.yml").write_text("version: 1.0.0\nmode: enforced\n")
    (proj / ".compass" / "work" / "t" / "task.yml").write_text(
        TASK.format(touches=touches))
    (proj / ".compass" / "current-task").write_text("t\n")
    if drop_g5:
        gp = proj / "governance" / "guardrails.yml"
        g = yaml.safe_load(gp.read_text())
        g["defaults"] = [x for x in g["defaults"] if x["id"] != "G5"]
        gp.write_text(yaml.safe_dump(g, sort_keys=False))
    return proj


def _check(proj):
    return subprocess.run(
        [sys.executable, str(CLI), "check", "--task", "t"],
        cwd=str(proj), capture_output=True, text=True, timeout=120,
    ).stdout


# ---------------------------------------------------------------------------
# TRC-D1 - a guardrail the project omits is reported
# ---------------------------------------------------------------------------

def test_trc_d1_a_guardrail_the_project_omits_should_be_reported():
    import tempfile
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="compass-absent-"))
    try:
        out = _check(_project(tmp, touches="auth", drop_g5=True))
        assert "G5" in out, (
            "G5 is absent from the project's governance and the task touches "
            f"auth - the surface G5 guards - yet check never mentions it:\n{out}")
        lowered = out.lower()
        assert "absent" in lowered or "not declared" in lowered, (
            f"the wording does not distinguish absent from not-applicable:\n{out}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# TRC-D2 - a guardrail that genuinely does not apply still reads as skipped
# ---------------------------------------------------------------------------

def test_trc_d2_a_guardrail_that_genuinely_does_not_apply_should_still_read_as_skipped():
    import tempfile
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="compass-skip-"))
    try:
        out = _check(_project(tmp, touches=""))
        assert "G5" in out, f"G5 is not reported at all:\n{out}"
        g5_line = next(l for l in out.splitlines() if "G5" in l)
        assert "not applicable" in g5_line.lower(), (
            f"a guardrail that genuinely does not apply no longer reads as "
            f"skipped:\n{g5_line}")
        assert "absent" not in g5_line.lower(), (
            f"a present-but-inapplicable guardrail is being called absent - the "
            f"fix has overshot:\n{g5_line}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
