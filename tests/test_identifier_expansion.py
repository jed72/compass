"""An identifier never appears without its meaning on first use.

A maintainer using Compass for the first time was told "the G5 guard kicked
in" and had no idea what a G5 guard was. Nothing taught an agent that
phrasing: `governance/guardrails.yml` uses the id as each guardrail's primary
key, so an agent reading the file and using the key as the name is doing the
natural thing. No rule said otherwise and no test would have caught it.

`compass check` already gets this right - it prints
`G5 A human signs off on the irreversible`. The standard existed in the CLI
and never reached the agent's speech, so these tests hold the guidance and the
two renderers to the standard the CLI already sets.

The rule has two halves and both matter. Expand on first use; leave the bare
id everywhere after that. Always-expand would be its own readability defect,
and the ids carry the traceability the machine checks depend on.

Scenario ids: see .compass/work/identifiers-and-vocabulary-in-printed-output/
acceptance-criteria.md (group A).
"""
from __future__ import annotations

import pathlib
import re
import subprocess
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
CLI = ROOT / "cli" / "compass"
STRATEGIES = ROOT / "governance" / "strategies.md"
TERMINOLOGY = ROOT / "governance" / "terminology.yml"

# A spine carrying the shapes that matter: a scenario with a title, evidence
# bound to it, and an identifier far longer than the receipt's column budget.
LONG_ID = "EV-ANALYZE-signup-email-validation-20260813T194925Z"
SCENARIO_TITLE = "an invalid email is rejected at signup"

SPINE = {
    "schema_version": "2.0",
    "task": "demo",
    "created": "2026-08-13",
    "status": "landed",
    "assessment": {"risk": "critical", "familiarity": "brownfield-mapped",
                   "size": "small", "goal": "delivery", "role": "engineer",
                   "labels": ["auth"]},
    "delivery_approach": "expedition",
    "topology": "swarm",
    "policy_rules_fired": [],
    "stages": {},
    "gates": [{"id": "verify.correctness", "status": "pass",
               "evidence": ["EV-T-TRC-B1", LONG_ID]}],
    "evidence": [
        {"id": "EV-T-TRC-B1", "type": "test-run",
         "path": "evidence/green.json", "scenario": "TRC-B1"},
        {"id": LONG_ID, "type": "command-output",
         "path": "evidence/analyze.txt"},
    ],
    "scenarios": [{"id": "TRC-B1", "title": SCENARIO_TITLE,
                   "intent": "INT-1", "tests": ["t"]}],
    "changed_files": [], "claims": [], "follow_ups": [],
    "reassessments": [], "friction": [],
}


def _project(tmp_path, spine=None):
    root = tmp_path / "proj"
    (root / ".compass" / "work" / "demo").mkdir(parents=True)
    (root / ".compass" / "config.yml").write_text("version: 1.0.0\n")
    (root / ".compass" / "work" / "demo" / "task.yml").write_text(
        yaml.safe_dump(spine if spine is not None else SPINE, sort_keys=False))
    (root / ".compass" / "current-task").write_text("demo\n")
    return root


def _receipt(root):
    r = subprocess.run(
        [sys.executable, str(CLI), "issue", "receipt", "--issue", "demo"],
        cwd=str(root), capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, f"receipt failed:\n{r.stdout}{r.stderr}"
    return r.stdout


# ---------------------------------------------------------------------------
# TRC-A1 - the rule is stated where agent speech is governed
# ---------------------------------------------------------------------------

def test_trc_a1_the_rule_is_stated():
    """The cold-reader strategy and the vocabulary agree on one rule.

    Checked in both places on purpose: `strategies.md` is what an agent
    reads, `terminology.yml` is what the scan reads, and before this issue
    they said different things - the vocabulary said to REPLACE the code with
    the plain statement, which would delete the traceability the machine
    checks run on.
    """
    text = STRATEGIES.read_text(encoding="utf-8")
    s7 = text.split("(`S7`)", 1)
    assert len(s7) == 2, "no S7 section found in strategies.md"
    body = s7[1].split("(`S8`)")[0]

    assert re.search(r"identifier", body, re.I), (
        "the cold-reader strategy says nothing about identifiers - the rule "
        "that a code carries its meaning on first use has no home")
    assert re.search(r"first use", body, re.I), (
        "the identifier rule does not say WHEN to expand. 'Always expand' is "
        "its own defect; the rule is first use, then the bare id")
    for surface in ("speech", "printed output", "generated artifact"):
        assert re.search(surface, body, re.I), (
            f"the rule does not name '{surface}' as a surface it governs")
    assert re.search(r"compass check", body), (
        "the rule does not point at `compass check`, which already prints "
        "the identifier and its plain statement together")

    doc = yaml.safe_load(TERMINOLOGY.read_text(encoding="utf-8"))
    entry = next((b for b in (doc.get("banned") or [])
                  if "G1" in str(b.get("term", ""))), None)
    assert entry, "the vocabulary no longer carries the guardrail-code entry"
    joined = f"{entry.get('replacement', '')} {entry.get('context', '')}"
    assert re.search(r"first use", joined, re.I), (
        f"the vocabulary entry still tells a writer to drop the code rather "
        f"than expand it on first use: {entry!r}")
    assert "S12" in str(entry.get("term", "")), (
        f"the entry still names S1..S7; the strategies run to S12: {entry!r}")


# ---------------------------------------------------------------------------
# TRC-A2 - the receipt names a scenario, not only its id
# ---------------------------------------------------------------------------

def test_trc_a2_scenario_title_beside_id(tmp_path):
    out = _receipt(_project(tmp_path))

    assert "TRC-B1" in out, "the receipt no longer prints the scenario id"
    assert SCENARIO_TITLE in out, (
        f"the receipt prints the scenario id with nothing beside it. The "
        f"spine holds its title ({SCENARIO_TITLE!r}) and the receipt is the "
        f"artifact captioned as proof:\n{out}")
    # The title must not be reachable by accident from the id itself.
    assert SCENARIO_TITLE not in "TRC-B1", "fixture error: title inside the id"


# ---------------------------------------------------------------------------
# TRC-A3 - a printed identifier is never truncated
# ---------------------------------------------------------------------------

def test_trc_a3_no_truncated_identifier(tmp_path):
    """A cut identifier is worse than a bare one: it identifies nothing.

    `EV-ANALYZE-signup-email-va...` cannot be matched to the entry that
    defines it further down the same receipt.
    """
    out = _receipt(_project(tmp_path))

    assert LONG_ID in out, (
        f"the long evidence id never appears in full - it is truncated "
        f"everywhere it is printed, so it cannot be matched to its own "
        f"registry entry:\n{out}")
    for line in out.splitlines():
        m = re.search(r"((?:EV|TRC|FU|RP|INT)-[A-Za-z0-9-]*)\.\.\.$", line)
        assert not m, (
            f"a line ends with an identifier cut mid-token ({m.group(1)}...): "
            f"{line!r}")


# ---------------------------------------------------------------------------
# TRC-A4 - the guard can fail
# ---------------------------------------------------------------------------

def test_trc_a4_the_check_can_fail(tmp_path):
    """The control for TRC-A2.

    Without it, TRC-A2 passes against a renderer that prints the whole spine,
    or one that prints nothing at all. Here the scenario has no title, so
    there is no meaning to print and the bare id is all the receipt can
    honestly show - and it must still render rather than crash.
    """
    spine = {**SPINE, "scenarios": [{"id": "TRC-B1", "intent": "INT-1",
                                     "tests": ["t"]}]}
    out = _receipt(_project(tmp_path, spine))

    assert "TRC-B1" in out, "the receipt dropped the id along with the title"
    assert SCENARIO_TITLE not in out, (
        "the receipt printed a scenario title that is not in the spine - it "
        "is inventing meaning at render time, which is worse than printing "
        "none")
