"""Invariants for the phase-2 additions (task phase-2-skills-check-and-cli-split).

Two skills and one check were added. The properties that must survive that:
a project which opted into nothing sees no change, every task already on disk
returns what it returned before, and the framework grew by artifacts and checks
only - no guardrail, gate, reading dimension, or top-level CLI verb.

Spec: .compass/work/phase-2-skills-check-and-cli-split/acceptance-criteria.md (TRC-F1..F3).
"""

# These tests read `compass check`'s PER-CHECK detail - a check's name,
# its PASS/FAIL and the reason it gave. That detail moved to --verbose on
# 2026-08-24 when the gate verdict came under the terminal output contract;
# the checks themselves are unchanged. The assertions are re-pointed rather
# than rewritten, because what they assert still holds - only where it is
# printed changed.
from __future__ import annotations

import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
CLI = ROOT / "cli" / "compass"
GOVERNANCE = ROOT / "governance"


def test_trc_f1_a_project_that_opted_into_nothing_should_see_no_change():
    proj = pathlib.Path(tempfile.mkdtemp(prefix="compass-phase2-"))
    try:
        shutil.copytree(GOVERNANCE, proj / "governance")
        (proj / ".compass" / "work").mkdir(parents=True)
        shutil.copyfile(ROOT / ".compass" / "config.yml",
                        proj / ".compass" / "config.yml")
        r = subprocess.run([sys.executable, str(CLI), "ci"], cwd=str(proj),
                           capture_output=True, text=True, timeout=300)
        assert r.returncode == 0, (
            f"a project that opted into nothing fails compass ci:\n{r.stdout[-2500:]}")
        lowered = r.stdout.lower()
        for word in ("bdd runner", "executable", "scenarios-are-executable"):
            assert word not in lowered, (
                f"compass ci mentions {word!r} for a project that wired no "
                f"runner:\n{r.stdout[-1500:]}")
    finally:
        shutil.rmtree(proj, ignore_errors=True)


def test_trc_f2_adding_the_check_should_not_change_any_existing_tasks_result():
    """Every task already on disk must still check the way it did.

    The new check runs inside G1, which is always active - so a bug in it would
    change the result for every task in the repository at once. This is the
    guard on that.
    """
    work = ROOT / ".compass" / "work"
    if not work.is_dir():
        return
    slugs = sorted(p.name for p in work.iterdir() if (p / "manifest.yml").is_file())
    assert slugs, "no tasks on disk - this guard would be empty"

    # A Spike runs `spike_guardrails`, not G1-G5 - the BDD and TDD strategies
    # are suspended there by design, so a check about executable scenarios
    # correctly never fires. Excluded rather than asserted over.
    spikes = set()
    for slug in slugs:
        data = yaml.safe_load((work / slug / "manifest.yml").read_text()) or {}
        if data.get("delivery_approach") == "spike":
            spikes.add(slug)
    slugs = [s for s in slugs if s not in spikes]

    checked = 0
    for slug in slugs:
        r = subprocess.run(
            [sys.executable, str(CLI), "check", "--verbose", "--issue", slug],
            cwd=str(ROOT), capture_output=True, text=True, timeout=180)
        line = next((l for l in r.stdout.splitlines()
                     if "scenarios-are-executable" in l), "")
        # No task in this repository has wired a runner, so every one of them
        # must take the no-op path. A FAIL here would mean the check is
        # penalising projects for not having opted in.
        if line:
            checked += 1
            assert line.strip().startswith("PASS"), (
                f"{slug}: the new check fails a task that wired no runner:\n{line}")
            assert "runner" in line.lower(), (
                f"{slug}: the no-op pass gives no reason:\n{line}")
    assert checked == len(slugs), (
        f"the check ran for only {checked} of {len(slugs)} non-Spike tasks - "
        f"it is registered under G1, which is always active on a delivery "
        f"route, so it should run for all of them")
    assert spikes, (
        "no Spike task on disk, so the exclusion above is untested - if every "
        "Spike has been archived, simplify this test rather than leaving a "
        "branch nothing exercises")


EXPECTED_GUARDRAIL_IDS = {"G1", "G2", "G3", "G4", "G5", "S1", "S2"}
# The CLI-voice slice renamed the banned-word verbs (route -> approach,
# plan -> design, task -> issue, backfill -> follow-up) and added
# terminology; the set below is the surface after that deliberate move.
# The vocabulary rename moved the planning verb BACK to `plan` on
# 2026-08-25: `design` now means the designer's stage everywhere else,
# and one word cannot mean two stages in one release. `design` is kept
# alongside it - it shipped in 3.3.0, so it keeps working until the next
# major version (ADR-006, ADR-019). Both spellings, one handler.
# `intent` added 2026-08-25: `compass intent ingest` reads a brief that
# already exists, by path or https URL, so a team arriving with one does
# not retype it. A new top-level group rather than a subverb - there was
# no `intent` verb before, only the slash command.
EXPECTED_SUBCOMMANDS = {
    "approach", "bdd", "check", "analyze", "retro", "ci", "tdd-red",
    "tdd-green", "policy", "plan", "intent", "issue", "adr", "rework-scan", "flow",
    "next", "follow-up", "ship-commit", "gate", "scenario", "changed-file",
    "evidence", "terminology",
    "migrate",                    # slice 8: the 1.x-to-2.0 tree migrator
    # `init` added 2026-08-26: `compass init` creates .compass/ - the config
    # and the work directory - and is safe to run twice. It exists because
    # nothing owned initialisation: /compass:init created the directories at
    # the end of a governance conversation, /compass:assess created them as a
    # side effect of writing a manifest, and four of the five role entry points
    # wrote into .compass/work/<slug>/ assuming somebody else had. A verb
    # rather than a subcommand because there is no group it belongs under, and
    # because the five entry points call it directly.
    "init",
    # `acceptance` (R13) is the one honest path for a change with no natural
    # behavioural red - config, docs, a behaviour-preserving refactor. It is a
    # GROUP (`start`, `record`), so later kinds add a subcommand rather than a
    # verb. Added deliberately: the alternative was leaving authors to fake a
    # red that greps a file for a string, which is what the field reported.
    "acceptance",
}
EXPECTED_READING_KEYS = {
    "risk", "familiarity", "size", "goal", "urgency", "role",
    "labels_common",
}


def test_trc_f3_the_framework_should_grow_by_artifacts_and_checks_only():
    g = yaml.safe_load((GOVERNANCE / "guardrails.yml").read_text())
    ids = {x["id"] for x in g["defaults"]} | {x["id"] for x in g["spike_guardrails"]}
    ids |= {x["id"] for x in (g.get("project") or [])}
    assert ids == EXPECTED_GUARDRAIL_IDS, (
        f"the guardrail id set changed: {sorted(ids ^ EXPECTED_GUARDRAIL_IDS)}")

    policy = yaml.safe_load((GOVERNANCE / "routing-policy.yml").read_text())
    assert set(policy["assessment_vocabulary"]) == EXPECTED_READING_KEYS, (
        "the reading vocabulary changed")

    gates = set()
    for shape in policy["route_shapes"].values():
        gates.update(shape.get("gates", []))
    known = {"verify.correctness", "verify.governance", "verify.traceability",
             "verify.regression", "verify.security", "verify.clarity",
             "verify.claims", "verify.analyze", "verify.fitness",
             "spike.conclude"}
    assert gates <= known, f"new gate id(s): {sorted(gates - known)}"

    out = subprocess.run([sys.executable, str(CLI), "--help"],
                         capture_output=True, text=True, check=True).stdout
    m = re.search(r"\{([a-zA-Z0-9_,\-]+)\}", out)
    assert m, out
    assert set(m.group(1).split(",")) == EXPECTED_SUBCOMMANDS, (
        "a new top-level CLI verb appeared. `compass bdd verify` is a "
        "subcommand of the existing `bdd` group, which is exactly why that "
        "group was created rather than a flat verb.")

    # and the additions really are two skills plus one check
    skills = {p.name for p in (ROOT / "skills").iterdir()
              if p.is_dir() and (p / "SKILL.md").is_file()}
    assert {"systematic-debugging", "receiving-code-review"} <= skills
    assert "scenarios-are-executable" in g["checks"]
