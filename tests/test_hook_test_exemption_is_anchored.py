"""A production file is not exempt because its name contains "test".

The pre-tool hook exempts test files from the acceptance-before-code and
red-before-green checks - you must be able to write the failing test in the
first place. It decided that by matching `*test*` against the filename.

That is a substring match, so `latest.py`, `inspector.py` and `protest.py` are
all "tests". Both guardrail checks are skipped for them, silently, on the allow
path where the hook prints nothing.

An earlier fix narrowed this from the absolute path to the basename, after
anyone who cloned under `/Users/testuser/` found enforcement switched off
entirely. That narrowed the class without closing it.

Spec: .compass/work/pr-50-review-findings/acceptance-criteria.md.
"""
from __future__ import annotations

import json
import pathlib
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
HOOK = ROOT / "hooks" / "pre-tool.sh"
BLOCK = 2

SPINE = """schema_version: "2.0"
task: "demo"
created: "2026-08-13"
status: active
assessment: {risk: contained, familiarity: brownfield-mapped, size: small,
  goal: delivery, role: engineer, labels: []}
delivery_approach: feature
topology: solo
policy_rules_fired: []
stages: {frame: full, specify: full, clarify: light, plan: full,
  distribute: solo, build: full, verify: full, land: full}
evidence: []
gates: []
scenarios: []
changed_files: []
claims: []
follow_ups: []
reassessments: []
friction: []
"""


@pytest.fixture()
def project(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    work = tmp_path / ".compass" / "work" / "demo"
    work.mkdir(parents=True)
    (tmp_path / ".compass" / "config.yml").write_text("version: 1.0.0\n")
    (tmp_path / ".compass" / "current-task").write_text("demo\n")
    (work / "task.yml").write_text(SPINE)
    (work / "delivery-approach.md").write_text("# approach\n")
    return tmp_path


def _verdict(project, relpath):
    target = project / relpath
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("x = 1\n")
    payload = json.dumps({"tool_name": "Edit",
                          "tool_input": {"file_path": str(target)}})
    return subprocess.run(
        ["bash", str(HOOK)], input=payload, cwd=str(project),
        capture_output=True, text=True, timeout=120,
        env={"PATH": "/usr/bin:/bin:/usr/local/bin", "HOME": str(project),
             "CLAUDE_PROJECT_DIR": str(project)},
    ).returncode


# Production files whose names merely contain a test-ish substring. Every one
# of these was allowed through before the exemption was anchored.
@pytest.mark.parametrize("relpath", [
    "src/latest.py",
    "src/inspector.py",
    "src/protest.py",
    "src/greatest_hits.py",
    "src/respecify.py",
    "src/Testimonial.java",
])
def test_a_production_file_with_a_testish_name_is_still_guarded(project, relpath):
    assert _verdict(project, relpath) == BLOCK, (
        f"{relpath} was allowed through. Its name contains a test-ish "
        f"substring, so the exemption matched it and both guardrail checks "
        f"were skipped - silently, because the allow path prints nothing."
    )


# The control. Anchoring must not stop real tests being exempt: you have to be
# able to write the failing test before there is a failing test on record.
@pytest.mark.parametrize("relpath", [
    "tests/test_thing.py",
    "src/thing_test.py",
    "src/thing.test.ts",
    "src/thing.spec.js",
    "src/ThingTest.java",
    "src/ThingSpec.scala",
    "spec/thing_spec.rb",
])
def test_a_real_test_file_is_still_exempt(project, relpath):
    assert _verdict(project, relpath) != BLOCK, (
        f"{relpath} was blocked. It is a test file by any normal convention, "
        f"and blocking it makes writing the failing test impossible."
    )
