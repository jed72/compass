"""cli/compass is a package, and nothing observable changed by making it one.

A pure refactor: 6,201 lines in one file become a thin entry point plus modules.
The contract is that an adopter cannot tell. These tests are the contract.

The equivalence assertions (group B, F2) compare against
tests/fixtures/cli-surface-baseline.json, captured from the UNSPLIT file before
any code moved. That ordering matters: a baseline captured afterwards would
describe whatever the refactor happened to produce, and would prove nothing.

Spec: .compass/work/cli-module-split/spec.feature.md (TRC-A1..A3, B1..B4, F1, F2).
"""
from __future__ import annotations

import ast
import importlib.machinery
import importlib.util
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CLI = ROOT / "cli" / "compass"
PKG = ROOT / "cli" / "compass_pkg"
BASELINE = json.loads((ROOT / "tests" / "fixtures" /
                       "cli-surface-baseline.json").read_text())


def _modules():
    return sorted(p for p in PKG.glob("*.py") if p.name != "__init__.py")


def _top_level_functions(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {n.name for n in tree.body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


def _imports_of(path):
    """Which compass_pkg modules does this file import?"""
    out = set()
    for m in re.finditer(r"^\s*(?:from|import)\s+([\w.]+)",
                         path.read_text(encoding="utf-8"), re.M):
        name = m.group(1)
        if name.startswith("compass_pkg."):
            out.add(name.split(".", 1)[1].split(".")[0])
    return out


# --- group A: the structure ------------------------------------------------

def test_trc_a1_the_entry_point_should_be_thin():
    assert PKG.is_dir(), "cli/compass_pkg does not exist"
    lines = len(CLI.read_text(encoding="utf-8").splitlines())
    # 500, not the 400 this scenario first said. That number was invented
    # without measuring; the argparse tree alone is ~380 lines and is
    # irreducibly one thing, so 400 would have forced splitting the parser
    # for no reason but the threshold. 454 from 6,201 is a 93% reduction,
    # which is what "thin" was reaching for. Relaxed again to 560 at the
    # CLI-voice slice, and saying so: the parser gained the terminology verb
    # and the issue-flag registration (--issue; the tolerated --task spelling
    # was removed at the major version by ADR-014)
    # on every issue-scoped verb - all irreducibly parser. Still 91% below
    # the pre-split file.
    #
    # RAISED 560 -> 575 on 2026-08-23 by James Edwards, adding `compass issue
    # dashboard`. A new public verb costs about four lines of parser
    # registration, and registering parsers is what this file is FOR - the cap
    # exists to keep *logic* out, not to cap the verb count.
    #
    # It was not raised before looking for slack. The cap surfaced eighteen
    # copies of one identical `--issue` line, which is real duplication and is
    # now `issue_arg()` in core.py. That was worth doing on its own and bought
    # no lines: a helper call and an add_argument call are one line each, so
    # deduplicating a one-liner cannot shrink the file. Recorded because the
    # obvious assumption - dedupe to get under a line cap - is wrong here, and
    # the next person will reach for it too.
    #
    # RAISED 575 -> 620 on 2026-08-23, adding the terminal output contract: one
    # call that attaches five flags to every verb, and an `output_kind=` on
    # each of the 34 `set_defaults` registrations. The declaration is per-verb
    # ON PURPOSE - deriving it centrally would mean no verb could ever lack
    # one, and the guard that checks for it could never fail.
    #
    # Recorded because the raise before this one was three days ago and left
    # exactly THREE lines of headroom: the file was at 572 against a cap of
    # 575. A cap that is re-raised every time a verb is added is measuring
    # something other than what it means to measure - it says "the entry point
    # should hold the shebang, the parser and main()", and 47 parser
    # registrations ARE the parser. Filed as
    # `entry-point-cap-measures-the-wrong-thing` rather than nudged again.
    assert lines < 620, (
        f"cli/compass is still {lines} lines (was {BASELINE['line_count']}). "
        f"The entry point should hold the shebang, the parser and main().")
    src = CLI.read_text(encoding="utf-8")
    assert src.startswith("#!"), "the entry point lost its shebang"
    assert "def main(" in src, "main() left the entry point"
    assert "add_subparsers" in src, "the argument parser left the entry point"


def test_trc_a2_the_modules_should_follow_the_groupings_the_code_already_had():
    mods = _modules()
    assert mods, "no modules under cli/compass_pkg"
    for m in mods:
        n = len(m.read_text(encoding="utf-8").splitlines())
        assert n <= 1200, f"{m.name} is {n} lines - split it further"


def test_trc_a3_the_package_should_import_cleanly_on_its_own():
    sys.path.insert(0, str(ROOT / "cli"))
    try:
        for m in _modules():
            name = f"compass_pkg.{m.stem}"
            __import__(name)
        # the dependency runs one way: no module imports the entry point
        for m in _modules():
            text = m.read_text(encoding="utf-8")
            assert not re.search(r"^\s*(from|import)\s+compass\b", text, re.M), (
                f"{m.name} imports the entry point - the dependency must run "
                f"one way, or a cycle is one edit away")
        # CHECK_FNS still resolves, wherever in the package it landed
        found = None
        for m in _modules():
            mod = __import__(f"compass_pkg.{m.stem}", fromlist=["CHECK_FNS"])
            if hasattr(mod, "CHECK_FNS"):
                found = mod.CHECK_FNS
                break
        assert isinstance(found, dict) and found, (
            "CHECK_FNS is not defined anywhere in the package")
    finally:
        sys.path.remove(str(ROOT / "cli"))


# --- group B: nothing changed ----------------------------------------------

def test_trc_b1_the_public_verb_surface_should_be_identical():
    """The verb surface matches the recorded baseline.

    The baseline was captured at the module split to prove that refactor moved
    no verb. It is not frozen for ever: a slice that deliberately adds or
    renames a verb updates it in the same commit, so the diff shows the
    decision. `plan` was added on 2026-08-25 when the planning verb took the
    name its machine key already used; `design` stays beside it as the retired
    spelling until the next major version.
    """
    out = subprocess.run([sys.executable, str(CLI), "--help"],
                         capture_output=True, text=True, check=True).stdout
    subs = sorted(re.search(r"\{([a-zA-Z0-9_,\-]+)\}", out).group(1).split(","))
    assert subs == BASELINE["subcommands"], (
        f"the verb surface changed.\n  before: {BASELINE['subcommands']}\n"
        f"  after : {subs}")
    for sub in subs:
        r = subprocess.run([sys.executable, str(CLI), sub, "--help"],
                           capture_output=True, text=True)
        assert r.returncode == 0, f"`compass {sub} --help` broke: {r.stderr[-400:]}"


def test_trc_b2_the_whole_test_suite_should_pass_unchanged():
    """Asserted by the suite this test is part of.

    RETIRED as a live guard. It diffed `main...HEAD` for edited test files,
    which was the right question while the split was in flight and the wrong
    one afterwards: every later branch that adds a test file trips it. The
    split has landed, so the diff it wants no longer exists. Kept as a
    documented no-op rather than deleted, so the scenario it serves still has
    a test and the reason is on record.
    """
    return
    r = subprocess.run(["git", "diff", "--name-only",
                        "origin/main...HEAD" if False else "main...HEAD"],
                       cwd=str(ROOT), capture_output=True, text=True)
    if r.returncode != 0:
        return  # no main to compare against
    edited = [f for f in r.stdout.split()
              if f.startswith("tests/") and "cli_module_split" not in f
              and "fixtures/cli-surface-baseline" not in f]
    assert not edited, (
        f"existing test files were edited by a refactor that is supposed to "
        f"change nothing: {edited}")


def test_trc_b3_loading_the_cli_by_file_path_should_still_work():
    """A test already loads cli/compass via SourceFileLoader to call a function
    directly. That must keep working - otherwise a passing test starts failing
    for a reason unrelated to what it tests, and someone 'fixes' the test."""
    spec = importlib.util.spec_from_loader(
        "compass_cli_probe",
        importlib.machinery.SourceFileLoader("compass_cli_probe", str(CLI)))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for name in ("governance_drift", "reading_matches", "CHECK_FNS"):
        assert hasattr(mod, name), (
            f"{name} is no longer reachable from a path-loaded cli/compass; "
            f"the entry point must re-export what it moved")


def test_trc_b4_every_command_should_still_run_end_to_end(tmp_path):
    import shutil
    proj = tmp_path / "p"
    (proj / ".compass" / "work").mkdir(parents=True)
    shutil.copytree(ROOT / "governance", proj / "governance")
    (proj / ".compass" / "config.yml").write_text("version: 1.0.0\nmode: enforced\n")
    for args in (["policy", "lint"],
                 ["approach", "evaluate", "--assessment", "risk=contained",
                  "--assessment", "familiarity=greenfield", "--assessment",
                  "size=small", "--assessment", "intent=delivery",
                  "--assessment", "role=engineer"]):
        r = subprocess.run([sys.executable, str(CLI), *args], cwd=str(proj),
                           capture_output=True, text=True, timeout=60)
        assert r.returncode == 0, f"`compass {' '.join(args)}` broke:\n{r.stderr[-600:]}"


# --- failure modes ----------------------------------------------------------

def test_trc_f1_a_circular_import_should_be_impossible_by_construction():
    graph = {m.stem: _imports_of(m) for m in _modules()}
    seen, stack = set(), set()

    def visit(node, path):
        if node in stack:
            raise AssertionError(f"import cycle: {' -> '.join(path + [node])}")
        if node in seen:
            return
        stack.add(node); seen.add(node)
        for dep in graph.get(node, ()):
            visit(dep, path + [node])
        stack.remove(node)

    for node in graph:
        visit(node, [])


def test_trc_f2_no_function_should_be_renamed_merged_or_split_by_this_task():
    """Compares the top-level function set against a baseline captured before
    the split.

    Scoped to the functions that existed THEN. A later task legitimately adds
    functions - process-impact added five - and asserting an exact set makes
    every future branch fail. What this task promised was that it renamed,
    merged or split nothing, and that is what a subset check asserts.
    """
    after = _top_level_functions(CLI)
    for m in _modules():
        after |= _top_level_functions(m)
    before = set(BASELINE["functions"])

    # Functions a LATER issue deleted on purpose, each with the reason. The
    # baseline is a snapshot of what existed before the split; a later issue is
    # allowed to remove genuinely dead code, but it has to say so here rather
    # than have this guard quietly relaxed into a warning.
    DELIBERATELY_REMOVED = {
        # Left with no callers when `compass check` moved to the terminal
        # output contract (2026-08-24) and the rendering moved into
        # _verbose_lines. Its formatting had already drifted from the live
        # renderer, so keeping it meant keeping dead code that disagreed with
        # the code that replaced it.
        "_print_check_result",
    }
    before -= DELIBERATELY_REMOVED

    assert before <= after, (
        "this task moves code and does nothing else, but functions that "
        "existed before the split are missing.\n"
        f"  removed: {sorted(before - after)}\n"
        "A rename is a behaviour change to any importer, and it makes the diff "
        "unreadable. Do it in a follow-up task, against a smaller file.")
