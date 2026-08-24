"""The terminal output contract - what a person reads when they run a verb.

The terminal is a notification surface, not the artifact. A verb that ends a
stage or renders a verdict is a HAND-OFF and fits one screen; a verb somebody
runs deliberately to get detail is a REPORT and keeps its detail, but opens with
a summary they can stop at. Five flags choose how much they get.

Measured before any threshold here was written, on 2026-08-23:
  compass check          45 lines, 14 of them PASS lines, longest line 252 chars
  compass flow           156 lines
  compass approach evaluate   4 lines, one a raw Python dict
  208 print calls inside verb bodies, across 34 verbs
  37 test files asserting a literal string in stdout - 130 assertions

Scenario ids trace to
.compass/work/the-terminal-output-contract/acceptance-criteria.md.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "cli"))
CLI = REPO_ROOT / "cli" / "compass"

# The budget, and the reason each number is what it is.
HANDOFF_LINES = 12      # the proposal's number - where a reader stops scrolling
QUIET_HANDOFF_LINES = 5  # a hand-off with nothing to decide
REPORT_SUMMARY_LINES = 5
MAX_WIDTH = 100         # a line budget alone is met by joining lines


def _leaf_parsers():
    """Every leaf parser in the CLI tree, by its full command path.

    Recursive on purpose. The tree has 13 nested subparser groups under 47
    `add_parser` calls, so anything that walks only the top level reaches
    `issue` and misses `issue dashboard` entirely - which is exactly how a
    guard over this tree passes without checking most of it.
    """
    import argparse
    import importlib.util

    # `build_parser` lives in the `cli/compass` entry point, which has no .py
    # extension and is not importable by name. Loading it by path is how the
    # test reaches the real tree rather than a copy that could drift from it.
    spec = importlib.util.spec_from_loader(
        "compass_cli", importlib.machinery.SourceFileLoader("compass_cli", str(CLI)))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    build_parser = mod.build_parser

    out = {}

    def walk(parser, path):
        subs = [a for a in parser._actions
                if isinstance(a, argparse._SubParsersAction)]
        if not subs:
            out[" ".join(path)] = parser
            return
        for action in subs:
            for name, child in action.choices.items():
                walk(child, path + [name])

    walk(build_parser(), [])
    return out


# ---------------------------------------------------------------------------
# Group C - the modes
# ---------------------------------------------------------------------------

def test_trc_c1_every_verb_accepts_every_mode_flag():
    """TRC-C1: the five mode flags reach every leaf verb.

    The failure this prevents: a flag that works on four verbs and is silently
    ignored on the other thirty, which is worse than not having it.
    """
    flags = ["--quiet", "--summary", "--verbose", "--json", "--evidence-out"]
    leaves = _leaf_parsers()
    # A non-recursive walk reaches the thirteen group parsers by name and
    # stops, so it never sees anything nested. Naming a nested verb catches
    # that directly and does not rot as verbs are added, which a bare count
    # would. The floor is a second, cruder net.
    for nested in ("issue dashboard", "gate pass", "evidence add", "bdd verify"):
        assert nested in leaves, (
            "%r was not reached, so the walk over the parser tree is not "
            "recursing into nested subcommand groups. Found: %s"
            % (nested, sorted(leaves)))
    assert len(leaves) >= 30, (
        "only %d leaf verbs were found: %s" % (len(leaves), sorted(leaves)))

    missing = []
    for path, parser in sorted(leaves.items()):
        opts = {o for a in parser._actions for o in a.option_strings}
        for f in flags:
            if f not in opts:
                missing.append("%s: %s" % (path, f))
    assert not missing, (
        "these verbs do not accept a mode flag, so passing it there is either "
        "an error or silently ignored:\n  " + "\n  ".join(missing[:30]))


def test_trc_c6_every_verb_declares_which_contract_it_is_under():
    """TRC-C6: each verb declares hand-off or report; neither is not allowed.

    A default is how the 35th verb quietly becomes whatever was easiest.
    """
    undeclared = []
    for path, parser in sorted(_leaf_parsers().items()):
        kind = parser.get_default("output_kind")
        if kind not in ("hand-off", "report"):
            undeclared.append("%s: %r" % (path, kind))
    assert not undeclared, (
        "these verbs do not declare an output kind beside their `func=`, so "
        "nothing says which contract binds them:\n  "
        + "\n  ".join(undeclared[:30]))


def test_trc_c2_quiet_prints_nothing_on_success():
    """TRC-C2: --quiet is silent on an uneventful success; the exit code carries it."""
    from compass_pkg.terminal import Emitter

    e = Emitter(mode="quiet")
    e.hand_off(outcome="the policy was applied", read="design.md")
    assert e.rendered() == "", (
        "--quiet printed on a plain success:\n" + e.rendered())

    e = Emitter(mode="quiet")
    e.hand_off(outcome="4 checks failed", read="verification-report.md",
               reply="approve | request changes", failed=True)
    assert e.rendered(), (
        "--quiet swallowed a failure, so a script's only signal is an exit "
        "code with no message")


def test_trc_c3_json_is_machine_only():
    """TRC-C3: --json emits one JSON document and no prose."""
    from compass_pkg.terminal import Emitter

    e = Emitter(mode="json")
    e.hand_off(outcome="initiative", read="delivery-approach.md",
               items=["eight gates", "every stage full weight"])
    out = e.rendered()
    doc = json.loads(out)
    assert doc["outcome"] == "initiative"
    assert "eight gates" in doc["items"]


def test_trc_c3_existing_json_verb_keeps_its_keys(tmp_path):
    """TRC-C3, the compatibility half: `approach evaluate --json` already ships.

    ADR-006 makes backward compatibility non-negotiable within a major version,
    so this verb's existing keys are public surface. New keys may appear; none
    of these may be renamed or removed.
    """
    import yaml
    proj = tmp_path / "p"
    (proj / "governance").mkdir(parents=True)
    for f in ("routing-policy.yml", "guardrails.yml"):
        (proj / "governance" / f).write_text(
            (REPO_ROOT / "governance" / f).read_text())
    td = proj / ".compass" / "work" / "t"
    td.mkdir(parents=True)
    (proj / ".compass" / "current-task").write_text("t\n")
    (proj / ".compass" / "config.yml").write_text("version: 1.0.0\nmode: enforced\n")
    (td / "task.yml").write_text(yaml.safe_dump({
        "schema_version": "2.0", "task": "t", "created": "2026-08-23",
        "status": "active",
        "assessment": {"risk": "contained", "familiarity": "brownfield-mapped",
                       "size": "standard", "goal": "delivery", "role": "engineer",
                       "labels": []},
        "delivery_approach": None, "stages": {}, "gates": [], "evidence": [],
        "scenarios": [], "changed_files": []}, sort_keys=False))

    r = subprocess.run([sys.executable, str(CLI), "approach", "evaluate", "--json"],
                       cwd=str(proj), capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    doc = json.loads(r.stdout)
    # Taken from what the verb actually emitted before this change, not from
    # what a compatibility test would like the keys to be called. The first
    # version of this list guessed `final_route` and `phases`, which have
    # never existed - a compatibility assertion against invented names checks
    # nothing and would have failed for the wrong reason.
    for key in ("candidate_route", "candidate_via", "delivery_approach",
                "gates", "stages", "policy_rules_fired", "stream_ceiling"):
        assert key in doc, (
            "`approach evaluate --json` lost the key %r, which shipped before "
            "this change and is public surface (ADR-006). Keys present: %s"
            % (key, sorted(doc)))


def test_trc_c5_verbose_adds_detail_without_relaxing_the_default():
    """TRC-C5: --verbose is where detail goes, not where the contract is escaped."""
    from compass_pkg.terminal import Emitter

    def build(mode):
        e = Emitter(mode=mode)
        e.hand_off(outcome="4 checks failed", read="verification-report.md",
                   items=["a", "b", "c", "d", "e"],
                   detail=["why a matters", "why b matters"])
        return e.rendered()

    default, verbose = build("summary"), build("verbose")
    assert "why a matters" not in default, (
        "the default mode printed detail meant for --verbose")
    assert "why a matters" in verbose, ("--verbose did not add the detail")
    assert len(default.splitlines()) <= HANDOFF_LINES, (
        "the default mode broke its own budget:\n" + default)


def test_trc_c7_evidence_out_with_nothing_to_capture(tmp_path):
    """TRC-C7: accepted everywhere; writes nothing where there is nothing.

    Not an error - a script passing the flag uniformly across a pipeline should
    not break on the verbs that happen to have nothing to say.
    """
    from compass_pkg.terminal import Emitter

    path = tmp_path / "capture.txt"
    e = Emitter(mode="summary", evidence_out=str(path))
    e.hand_off(outcome="nothing changed", read=None)
    assert not path.exists(), "a file was written for a verb that captured nothing"
    assert "nothing to capture" in e.rendered().lower(), (
        "the reader is not told why no file appeared:\n" + e.rendered())

    quiet = Emitter(mode="quiet", evidence_out=str(path))
    quiet.hand_off(outcome="nothing changed", read=None)
    assert quiet.rendered() == "", "--quiet printed the nothing-to-capture line"


def test_trc_c4_evidence_out_writes_the_capture(tmp_path):
    """TRC-C4: raw output is written and linked, never printed."""
    from compass_pkg.terminal import Emitter

    path = tmp_path / "capture.txt"
    raw = "===== 1283 passed, 7 skipped in 208.07s =====\n" + ("x" * 400)
    e = Emitter(mode="summary", evidence_out=str(path))
    e.report(summary=["the suite is green"], detail=["1283 passed"], capture=raw)

    assert path.read_text() == raw, "the capture was not written to the path"
    out = e.rendered()
    assert raw not in out, "the raw capture was printed as well as written"
    assert str(path) in out, (
        "the capture was written and not linked, so a reader cannot find it")


# ---------------------------------------------------------------------------
# Group A - the hand-off contract
# ---------------------------------------------------------------------------

def test_trc_a2_hand_off_states_outcome_artifact_and_reply():
    """TRC-A2: twelve lines of the wrong twelve things is not an improvement."""
    from compass_pkg.terminal import Emitter

    e = Emitter(mode="summary")
    e.hand_off(outcome="design ready for review",
               read=".compass/work/x/design.md",
               reply="approve | request changes | ask a question")
    lines = e.rendered().splitlines()
    assert "design ready for review" in lines[0], (
        "the first line does not state the outcome:\n" + lines[0])
    body = "\n".join(lines)
    assert ".compass/work/x/design.md" in body, "the artifact to read is missing"
    assert "approve" in body, "the reply being asked for is missing"


def test_trc_a3_hand_off_with_nothing_to_decide_is_shorter():
    """TRC-A3: the common case - no invented decision, concern or reply."""
    from compass_pkg.terminal import Emitter

    e = Emitter(mode="summary")
    e.hand_off(outcome="the red is on record", read="evidence/red-TRC-A1.json")
    out = e.rendered()
    assert len(out.splitlines()) <= QUIET_HANDOFF_LINES, (
        "a hand-off with nothing to decide ran to %d lines:\n%s"
        % (len(out.splitlines()), out))
    assert "reply" not in out.lower(), (
        "a reply prompt was invented where nothing is being asked:\n" + out)


def test_trc_a4_three_items_and_the_count_of_what_was_hidden():
    """TRC-A4: a silent truncation reads as 'there were three'.

    That is a claim the command never checked, and this repository has already
    found four checks that cleared by not looking.
    """
    from compass_pkg.terminal import Emitter

    e = Emitter(mode="summary")
    e.hand_off(outcome="7 findings", read="requirements-review.md",
               items=["one", "two", "three", "four", "five"],
               concerns=["c1", "c2", "c3", "c4"])
    out = e.rendered()
    assert "four" not in out.split("more")[0], "more than three items were shown"
    assert "2 more" in out or "and 2" in out, (
        "five items were cut to three and the reader is not told two were "
        "hidden, so the output claims there were three:\n" + out)
    assert "1 more" in out or "and 1" in out, (
        "four concerns were cut to three with no count of what was hidden:\n"
        + out)


def test_trc_a1_and_a5_a_hand_off_fits_one_screen_and_is_not_widened():
    """TRC-A1 and TRC-A5 together: a line budget alone is met by joining lines.

    Measured rather than supposed - `compass check`'s longest line today is 252
    characters, so 45 lines reflowed into 12 would satisfy a line count exactly
    and improve nothing.
    """
    from compass_pkg.terminal import Emitter

    long_path = ".compass/work/" + "a-long-directory-name/" * 8 + "design.md"
    e = Emitter(mode="summary")
    e.hand_off(outcome="x" * 300, read=long_path,
               items=["z" * 300] * 5, concerns=["w" * 300] * 5,
               reply="approve | request changes")
    out = e.rendered()
    lines = out.splitlines()
    assert len(lines) <= HANDOFF_LINES, (
        "a hand-off ran to %d lines against a budget of %d:\n%s"
        % (len(lines), HANDOFF_LINES, out))

    # The path is exempt, and asserted rather than assumed - shortening a path
    # makes it unopenable, which fails at the thing the line exists for.
    assert long_path in out, (
        "the path was shortened to fit the width bound, so the reader cannot "
        "open it:\n" + out)

    prose = [l for l in lines if long_path not in l]
    too_wide = [l for l in prose if len(l) > MAX_WIDTH]
    assert not too_wide, (
        "%d prose line(s) exceed %d characters, so the line budget was met by "
        "making the lines longer:\n  %s"
        % (len(too_wide), MAX_WIDTH, "\n  ".join(l[:120] for l in too_wide)))


# ---------------------------------------------------------------------------
# Group B - the report contract
# ---------------------------------------------------------------------------

def test_trc_b1_report_opens_with_a_summary_and_b2_keeps_its_detail():
    """TRC-B1 and TRC-B2: a report is not a hand-off.

    `compass calibration` and `compass terminology` exist to give detail.
    Cutting them to twelve lines would remove the reason to run them, so the
    hand-off budget must not reach them - and that has to be asserted, not
    assumed, because "twelve lines" is the kind of rule that spreads.
    """
    from compass_pkg.terminal import Emitter

    findings = ["finding %d" % i for i in range(40)]
    e = Emitter(mode="summary")
    e.report(summary=["40 findings across 12 files", "9 are new"],
             detail=findings)
    out = e.rendered()
    lines = out.splitlines()

    head = "\n".join(lines[:REPORT_SUMMARY_LINES])
    assert "40 findings" in head, (
        "the first %d lines do not state the finding, so a reader cannot stop "
        "there:\n%s" % (REPORT_SUMMARY_LINES, head))
    for f in findings:
        assert f in out, (
            "%r was dropped - the hand-off budget was applied to a report, "
            "which removes the reason to run it" % f)


# ---------------------------------------------------------------------------
# Group D - what compression must not cost
# ---------------------------------------------------------------------------

def test_trc_d1_compression_never_edits_the_inside_of_a_line():
    """TRC-D1: ADR-017 - an identifier is a key; attach its meaning, never
    delete the id.

    A twelve-line budget creates constant pressure to drop `(RP-FLOOR-001,
    floor)` from a line to save room. The emitter drops whole lines and never
    edits the interior of one it keeps, so the pressure has nowhere to act.
    """
    from compass_pkg.terminal import Emitter

    # The fourth item is deliberately too long to fit. That is where the
    # pressure actually is: a short line keeps its id for free, and a line that
    # must be shortened is the one where dropping the trailing "(RP-...)" is
    # the tempting saving. A guard that only tests short lines never reaches
    # the case ADR-017 is about.
    items = ["Large work - full weight (RP-SHAPE-004, shape)",
             "Critical changes coordinate (RP-FLOOR-001, floor)",
             "Fitness checked before landing " + "and more " * 20
             + "(RP-REQUIRE-003, requirement)",
             "A fourth that will be cut (RP-ADV-001, advisory)"]
    e = Emitter(mode="summary")
    e.hand_off(outcome="initiative", read="delivery-approach.md", items=items)
    out = e.rendered()

    # A line is "kept" if any recognisable part of its prose reached the
    # output - the opening words, which shortening never touches.
    kept = [i for i in items if i.split(" (")[0][:25] in out]
    assert kept, "every item was dropped"
    assert any(len(i) > MAX_WIDTH for i in kept), (
        "every kept item was short enough to fit, so this ran without ever "
        "reaching the case it exists to check")

    for item in kept:
        rule_id = item.split("(")[-1].split(",")[0]
        assert rule_id in out, (
            "the line for %r was kept but its identifier %r was stripped to "
            "save room, which is the deletion ADR-017 forbids:\n%s"
            % (item.split(" (")[0][:40], rule_id, out))
        assert item.split(" (")[0][:25] in out, (
            "the identifier %r was kept but its meaning was stripped:\n%s"
            % (rule_id, out))


# ---------------------------------------------------------------------------
# Group E - the guard on the guard
# ---------------------------------------------------------------------------

def test_trc_e1_the_budget_guard_names_the_verb_it_caught():
    """TRC-E1: an unactionable failure gets suppressed rather than fixed."""
    from compass_pkg.terminal import over_budget

    findings = over_budget({"issue dashboard": "\n".join("x" * 3 for _ in range(20))})
    assert findings, "a 20-line hand-off was not reported as over budget"
    text = " ".join(findings)
    assert "issue dashboard" in text, "the finding does not name the verb"
    assert "20" in text, "the finding does not give the actual line count"
    assert str(HANDOFF_LINES) in text, "the finding does not give the budget"


def test_trc_e2_the_budget_guard_can_fail_and_declines_an_empty_input():
    """TRC-E2: the two ways a line-count check passes without looking.

    A budget so high nothing breaches it, and an empty input that passes by
    having nothing to check. Both are asserted here because both have happened
    in this repository.
    """
    from compass_pkg.terminal import NOTHING_TO_CHECK, over_budget

    assert over_budget({"a verb": "\n".join(["line"] * (HANDOFF_LINES + 1))}), (
        "one line over the budget was not caught, so the budget is not being "
        "applied")
    assert not over_budget({"a verb": "\n".join(["line"] * HANDOFF_LINES)}), (
        "exactly the budget was reported as a breach")
    assert over_budget({"a verb": "x" * (MAX_WIDTH + 1)}), (
        "a single line of %d characters was not caught, so the width bound is "
        "not being applied and the budget can be met by joining lines"
        % (MAX_WIDTH + 1))
    assert over_budget({}) is NOTHING_TO_CHECK, (
        "an empty verb list reported a clean pass. A guard that is handed "
        "nothing and says 'all good' is how four checks in one release cleared "
        "without reading anything")
