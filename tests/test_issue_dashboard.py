"""The per-issue README - the page a reviewer opens first.

An issue directory answers "what files exist". It does not answer the questions
a reviewer actually has: what am I being asked to approve, what should I read,
and what was deliberately left out. Those live in the registry, and this page
renders them.

WHAT THIS PAGE IS NOT. It carries no raw evidence. Command output and test runs
are linked, not reproduced - a review page that reproduces its evidence stops
being two screens and stops being read.

It is generated, never hand-edited, and guarded for staleness the way
`docs/system-spec.md` is. That guard exists because this repository's own
derived spec went stale twice on 2026-08-23; a generated page nobody checks is
trusted anyway, which is worse than no page.

Scenario ids trace to .compass/work/the-human-front-door/acceptance-criteria.md.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "cli"))

INSTRUCTION_SURFACES = [REPO_ROOT / "commands", REPO_ROOT / "skills",
                        REPO_ROOT / "templates"]


def _issue(tmp_path: Path, artifacts: Optional[List[Dict[str, Any]]] = None,
           **spine_extra: Any) -> Path:
    task_dir = tmp_path / "work" / "export-portfolio-data"
    task_dir.mkdir(parents=True, exist_ok=True)
    spine: Dict[str, Any] = {
        "schema_version": "2.0", "task": "export-portfolio-data",
        "created": "2026-08-23", "status": "active",
        "assessment": {"risk": "cross-cutting", "familiarity": "brownfield-mapped",
                       "size": "large", "goal": "delivery"},
        "delivery_approach": "initiative", "scenarios": [], "changed_files": [],
        "evidence": [], "gates": [],
    }
    if artifacts is not None:
        spine["artifacts"] = artifacts
    spine.update(spine_extra)
    (task_dir / "task.yml").write_text(yaml.safe_dump(spine, sort_keys=False))
    return task_dir


PACK = [
    {"id": "ART-HLD", "kind": "design", "path": "design.md",
     "status": "awaiting-approval",
     "reason": "new service, queue and storage boundaries"},
    {"id": "ART-AC", "kind": "acceptance-criteria", "path": "acceptance-criteria.md",
     "status": "approved",
     "reason": "14 scenarios across export, permissions and failure recovery"},
    {"id": "ART-THREAT", "kind": "threat-model", "status": "omitted",
     "reason": "no auth, privacy or trust-boundary surface changes here"},
]


# ---------------------------------------------------------------------------
# Group C - the dashboard
# ---------------------------------------------------------------------------

def test_c1_dashboard_names_decision_and_start(tmp_path):
    """TRC-C1: the first screen states what is being asked and what to read.

    A reviewer who has to work out what they are approving has already been
    failed by the page.
    """
    from compass_pkg.dashboard import render_dashboard
    task_dir = _issue(tmp_path, artifacts=PACK)
    page = render_dashboard(str(task_dir))

    first_screen = "\n".join(page.splitlines()[:25]).lower()
    assert "decision" in first_screen, (
        "the first screen does not say what the reviewer is being asked to "
        "decide:\n" + first_screen)
    assert "design.md" in "\n".join(page.splitlines()[:25]), (
        "the first screen does not name the one document to read")


def test_c2_dashboard_lists_registered_artifacts(tmp_path):
    """TRC-C2: each document appears with its status and the reason it exists."""
    from compass_pkg.dashboard import render_dashboard
    task_dir = _issue(tmp_path, artifacts=PACK)
    # The documents have to EXIST for their registry status to mean anything -
    # `awaiting-approval` on a file nobody wrote is not a state a reviewer can
    # act on, and the page reports absence instead. This fixture used to skip
    # writing them and so asserted a status that could never really occur.
    for e in PACK:
        if e.get("path"):
            (task_dir / e["path"]).write_text("# %s\n" % e["kind"])
    page = render_dashboard(str(task_dir))

    for entry in PACK:
        if entry["status"] == "omitted":
            continue
        assert entry["kind"] in page, f"{entry['kind']} is missing from the pack"
        # The reason has to travel with the ROW - and it has to be the table
        # row, not the first line that happens to mention the kind. The
        # decision sentence names the same document, so an unscoped match read
        # that instead and reported a missing status that was never missing.
        row = next((l for l in page.splitlines()
                    if entry["kind"] in l and l.lstrip().startswith("|")), "")
        assert entry["status"] in row, (
            f"{entry['kind']} appears without its status:\n  {row}")
        assert entry["reason"][:24] in row, (
            f"{entry['kind']} appears without the reason it exists:\n  {row}")


def test_c3_dashboard_lists_omissions(tmp_path):
    """TRC-C3: each omission appears with the reason it was omitted.

    The proposal's phrase for why this matters: it "makes omission visible
    without making the reviewer read the routing algorithm".
    """
    from compass_pkg.dashboard import render_dashboard
    page = render_dashboard(str(_issue(tmp_path, artifacts=PACK)))

    omitted = [e for e in PACK if e["status"] == "omitted"][0]
    row = next((l for l in page.splitlines()
                if omitted["kind"] in l and "trust-boundary" in l), "")
    assert row, (
        "the omitted document does not appear with its reason, so a reader "
        "cannot tell a decision from a gap:\n" + page)


def test_c4_dashboard_carries_no_raw_evidence(tmp_path):
    """TRC-C4: evidence is linked, not reproduced.

    Asserts an ABSENCE, which is the easiest thing to satisfy without checking
    anything - so the fixture plants real captured output in the spine and the
    assertion looks for it. A page that renders nothing would pass a test that
    only searched for a marker.
    """
    from compass_pkg.dashboard import render_dashboard
    captured = "===== 1268 passed, 7 skipped in 209.93s ====="
    task_dir = _issue(tmp_path, artifacts=PACK, evidence=[
        {"id": "EV-T", "type": "test-run", "path": "evidence/green.json"}])
    (task_dir / "evidence").mkdir(exist_ok=True)
    (task_dir / "evidence" / "green.json").write_text(
        '{"command": "pytest", "exit_code": 0, "log_excerpt": "%s"}' % captured)

    page = render_dashboard(str(task_dir))

    assert captured not in page, (
        "captured command output was reproduced in the review page")
    assert "log_excerpt" not in page, (
        "a raw evidence field was rendered into the review page")
    assert "evidence/green.json" in page or "EV-T" in page, (
        "the evidence is neither pasted nor linked - it has vanished from the "
        "page entirely, which is not what 'linked, not pasted' means")


# ---------------------------------------------------------------------------
# Group D - a generated page that has drifted
# ---------------------------------------------------------------------------

def test_d1_stale_dashboard_is_reported(tmp_path):
    """TRC-D1: a dashboard that no longer matches its spine says so.

    Not in the proposal. It is here because `docs/system-spec.md` is the worked
    precedent for a generated artifact in this repository, and its currency
    guard fired twice on 2026-08-23.
    """
    from compass_pkg.dashboard import render_dashboard, dashboard_is_current
    task_dir = _issue(tmp_path, artifacts=PACK)
    (task_dir / "README.md").write_text(render_dashboard(str(task_dir)))
    assert dashboard_is_current(str(task_dir))[0], (
        "a freshly generated dashboard reported itself stale")

    # The spine changes and nobody regenerates.
    spine = yaml.safe_load((task_dir / "task.yml").read_text())
    spine["artifacts"].append(
        {"id": "ART-ROLL", "kind": "rollback-plan", "path": "rollback-plan.md",
         "status": "draft", "reason": "an irreversible migration is in scope"})
    (task_dir / "task.yml").write_text(yaml.safe_dump(spine, sort_keys=False))

    current, detail = dashboard_is_current(str(task_dir))
    assert not current, (
        "the spine gained a document and the dashboard still reported itself "
        "current - so the page can disagree with its source and nothing says so")
    assert "regenerate" in detail.lower() or "compass" in detail.lower(), (
        "the report does not name how to fix it:\n" + detail)


# ---------------------------------------------------------------------------
# Group E - evidence is linked, not pasted
# ---------------------------------------------------------------------------

def test_e1_instructions_say_link_not_paste():
    """TRC-E1: no instruction asks for raw output to be pasted into a document
    a person reads.

    Reads each instruction's own sentence rather than the whole file: three
    empty checks in this session were whole-file searches satisfied by
    unrelated text.
    """
    offenders = []
    pattern = re.compile(r"\bpaste[sd]?\b[^.\n]{0,80}", re.IGNORECASE)
    for root in INSTRUCTION_SURFACES:
        if not root.is_dir():
            continue
        for path in root.rglob("*.md"):
            for m in pattern.finditer(path.read_text(encoding="utf-8")):
                sentence = " ".join(m.group(0).split())
                # Pasting INTO evidence is fine; pasting into a human document
                # is what this forbids.
                # PLURALS TOO. The first version of this list was singular
                # only, so `\bartifact\b` did not match "artifacts" and the
                # check read a tree with real offenders in it and reported
                # clean. Found on 2026-08-23 by grepping the same tree by hand
                # and getting a different answer from the test.
                if re.search(r"\b(reports?|documents?|artifacts?|verification|"
                             r"devlogs?|reviews?)\b", sentence, re.IGNORECASE):
                    offenders.append("%s: %s"
                                     % (path.relative_to(REPO_ROOT), sentence))
    assert not offenders, (
        "these instructions ask for raw output to be pasted into a document a "
        "person reads - write the evidence file and link it:\n  "
        + "\n  ".join(offenders))


def test_c5_dashboard_verb_generates_and_checks(tmp_path):
    """TRC-C5: the page can be generated, and checked, from the CLI.

    Added during implementation. The spec covered what the page says and never
    covered how it comes to exist - a renderer nobody can invoke is a function,
    not a front door. `--check` writes nothing and reports drift, which is the
    mode the currency guard calls.
    """
    import subprocess
    cli = REPO_ROOT / "cli" / "compass"
    proj = tmp_path / "project"
    (proj / ".compass").mkdir(parents=True)
    (proj / ".compass" / "current-task").write_text("export-portfolio-data\n")
    (proj / ".compass" / "config.yml").write_text("version: 1.0.0\nmode: enforced\n")
    task_dir = _issue(proj / ".compass", artifacts=PACK)

    gen = subprocess.run([sys.executable, str(cli), "issue", "dashboard"],
                         cwd=str(proj), capture_output=True, text=True, timeout=60)
    assert gen.returncode == 0, gen.stdout + gen.stderr
    readme = task_dir / "README.md"
    assert readme.is_file(), "the verb reported success and wrote no page"

    ok = subprocess.run([sys.executable, str(cli), "issue", "dashboard", "--check"],
                        cwd=str(proj), capture_output=True, text=True, timeout=60)
    assert ok.returncode == 0, (
        "a freshly generated page was reported stale:\n" + ok.stdout + ok.stderr)

    readme.write_text(readme.read_text() + "\nhand-edited\n")
    drifted = subprocess.run([sys.executable, str(cli), "issue", "dashboard", "--check"],
                             cwd=str(proj), capture_output=True, text=True, timeout=60)
    assert drifted.returncode != 0, (
        "an edited page was reported current, so --check cannot detect drift")


# ---------------------------------------------------------------------------
# Group D, second half - the currency guard as a real check
# ---------------------------------------------------------------------------

def test_d2_stale_dashboard_fails_a_guardrail_check(tmp_path):
    """TRC-D2: a drifted dashboard fails `compass check`, it does not merely warn.

    `dashboard_is_current` is a function nobody has to call. The complaint this
    issue answers is that a reviewer trusts what is in front of them, so the
    guard has to sit where the reviewer's approval is gated - which is the
    check, under the evidence-not-assertion guardrail. A drifted page is an
    assertion the record contradicts.

    Its three outcomes are all asserted, because two of them are the ones that
    would quietly make it a check that cannot fail: no page and a hand-written
    page must BOTH decline to check rather than pass.
    """
    from compass_pkg.check_results import NOTHING_TO_CHECK
    from compass_pkg.dashboard import (_check_dashboard_current,
                                       render_dashboard)
    task_dir = _issue(tmp_path, artifacts=PACK)
    spine = yaml.safe_load((task_dir / "task.yml").read_text())

    # 1. No page. Nothing on disk is claiming anything, so there is nothing to
    #    check - and that is NOT a pass.
    ok, detail = _check_dashboard_current(spine, str(task_dir))
    assert ok is NOTHING_TO_CHECK, (
        "an issue with no dashboard reported a real pass, so this check would "
        "clear the guardrail on 88 landed issues without reading anything:\n"
        + str(detail))

    # 2. A hand-written page. Not Compass's to police, and again not a pass.
    (task_dir / "README.md").write_text("# notes I keep by hand\n")
    ok, detail = _check_dashboard_current(spine, str(task_dir))
    assert ok is NOTHING_TO_CHECK, (
        "a hand-written README was judged as a generated one:\n" + str(detail))

    # 3. Generated and current.
    (task_dir / "README.md").write_text(render_dashboard(str(task_dir)))
    ok, detail = _check_dashboard_current(spine, str(task_dir))
    assert ok is True, ("a freshly generated dashboard failed the check:\n"
                        + str(detail))

    # 4. Generated, then the spine moved underneath it.
    spine["artifacts"] = PACK + [
        {"id": "ART-ROLL", "kind": "rollback-plan", "path": "rollback-plan.md",
         "status": "draft", "reason": "an irreversible migration is in scope"}]
    (task_dir / "task.yml").write_text(yaml.safe_dump(spine, sort_keys=False))
    ok, detail = _check_dashboard_current(spine, str(task_dir))
    assert ok is False, (
        "the spine gained a document the page does not show, and the check "
        "still cleared - so the review page can disagree with the record and "
        "nothing blocks on it")
    assert "compass issue dashboard" in detail, (
        "the failure does not name the command that fixes it:\n" + detail)


def test_d3_currency_check_is_registered_under_a_guardrail():
    """TRC-D3: the check is wired into `compass check`, not just importable.

    A check function that no guardrail lists never runs. Compass grows by
    adding checks under the five existing guardrails, never a sixth letter
    (ADR-002), so this asserts both the registration and the guardrail it
    joined.
    """
    sys.path.insert(0, str(REPO_ROOT / "cli"))
    from compass_pkg.check_cmd import CHECK_FNS, CHECK_GUIDANCE

    assert "dashboard-current" in CHECK_FNS, (
        "the currency check is not in CHECK_FNS, so naming it in guardrails.yml "
        "would make `compass check` fail with an unknown-check error")
    assert "dashboard-current" in CHECK_GUIDANCE, (
        "the check has no guidance entry, so its failure reads as bureaucracy "
        "rather than telling the reader why it matters and how to fix it")

    guardrails = yaml.safe_load(
        (REPO_ROOT / "governance" / "guardrails.yml").read_text())
    g4 = next(g for g in guardrails["defaults"] if g["id"] == "G4")
    assert "dashboard-current" in g4["checks"], (
        "the check is registered in code but no guardrail lists it, so it "
        "never runs:\n" + str(g4["checks"]))
    assert "dashboard-current" in guardrails["checks"], (
        "the check has no description in guardrails.yml's `checks:` catalogue")


def test_c6_dashboard_separates_written_from_still_owed(tmp_path):
    """TRC-C6: the pack distinguishes a document that exists from one that does not.

    Added during implementation, after reading this issue's own generated page.
    It listed seven documents as `draft` when three of them had never been
    written and four were finished - because `draft` is the status the routing
    seeds, and nothing moves it. A reviewer reading that page would go looking
    for files that are not there, which is a worse failure than no page: it is
    a page that is confidently wrong.

    The resolver already knows the difference. The page just was not asking it.
    """
    from compass_pkg.dashboard import render_dashboard
    task_dir = _issue(tmp_path, artifacts=[
        {"id": "ART-AC", "kind": "acceptance-criteria",
         "path": "acceptance-criteria.md", "status": "draft",
         "reason": "every initiative carries one"},
        {"id": "ART-HLD", "kind": "hld", "path": "hld.md", "status": "draft",
         "reason": "every initiative carries one"},
    ])
    (task_dir / "acceptance-criteria.md").write_text("# criteria\n")

    page = render_dashboard(str(task_dir))
    rows = {l.split("|")[1].strip(): l for l in page.splitlines()
            if l.lstrip().startswith("|") and "---" not in l}

    assert "acceptance-criteria" in rows and "hld" in rows, (
        "the pack lost a document:\n" + page)
    written, owed = rows["acceptance-criteria"], rows["hld"]

    assert "not written" in owed.lower() or "owed" in owed.lower(), (
        "a document that does not exist on disk is shown the same way as one "
        "that does, so the page sends a reviewer looking for a missing "
        "file:\n  " + owed)
    assert "not written" not in written.lower(), (
        "a document that DOES exist was reported as missing - the check now "
        "fails in the opposite direction, which is just as wrong:\n  " + written)


def test_c7_artifact_status_can_be_moved_from_the_cli(tmp_path):
    """TRC-C7: a document's status can be changed, and an omission recorded.

    Added during implementation, from reading this issue's own page. Routing
    seeds every earned document as `draft` and nothing could move it, so
    `omitted`, `awaiting-approval` and `approved` were all unreachable - which
    made the page's two headline sections, "Decision required" and
    "Deliberately omitted", permanently empty. TRC-A2 and TRC-C3 were testing
    behaviour the framework had no way to produce.

    An omission MUST carry a reason. A document dropped without one is
    indistinguishable from one nobody got to, which is the distinction the
    whole registry exists to make.
    """
    import subprocess
    cli = REPO_ROOT / "cli" / "compass"
    proj = tmp_path / "project"
    (proj / ".compass").mkdir(parents=True)
    (proj / ".compass" / "current-task").write_text("export-portfolio-data\n")
    (proj / ".compass" / "config.yml").write_text("version: 1.0.0\nmode: enforced\n")
    task_dir = _issue(proj / ".compass", artifacts=[
        {"id": "ART-PRD", "kind": "prd", "path": "prd.md", "status": "draft",
         "reason": "every initiative carries one"},
        {"id": "ART-HLD", "kind": "design", "path": "design.md",
         "status": "draft", "reason": "every initiative carries one"}])

    def run(*a):
        return subprocess.run([sys.executable, str(cli), "issue", "artifact", *a],
                              cwd=str(proj), capture_output=True, text=True,
                              timeout=60)

    # An omission with no reason is refused.
    bad = run("prd", "--status", "omitted")
    assert bad.returncode != 0, (
        "a document was omitted with no reason recorded, so a deliberate "
        "decision and a gap nobody noticed now look identical")
    assert "reason" in (bad.stdout + bad.stderr).lower()

    ok = run("prd", "--status", "omitted", "--reason",
             "no product owner on this issue - the intent is in the bug report")
    assert ok.returncode == 0, ok.stdout + ok.stderr
    assert run("design", "--status", "awaiting-approval").returncode == 0

    # An unknown kind is refused rather than silently added, the way
    # `tdd-red --scenario` refuses an id that is not in the spine.
    assert run("no-such-doc", "--status", "approved").returncode != 0, (
        "a status was set on a document this issue never earned")

    spine = yaml.safe_load((task_dir / "task.yml").read_text())
    by_kind = {a["kind"]: a for a in spine["artifacts"]}
    assert by_kind["prd"]["status"] == "omitted"
    assert "product owner" in by_kind["prd"]["reason"]
    assert by_kind["design"]["status"] == "awaiting-approval"

    from compass_pkg.dashboard import render_dashboard
    page = render_dashboard(str(task_dir))
    assert "No decision required" not in page, (
        "a document is awaiting approval and the page still says there is no "
        "decision to make")
    assert "Nothing recorded as omitted" not in page, (
        "an omission was recorded and the page still reports none")
    assert "no product owner" in page, (
        "the omission is listed without the reason it was omitted")
