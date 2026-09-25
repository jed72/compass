"""The printed strings in `scripts/` and `hooks/` are unchanged by
`prose-breaks-the-writing-style`.

The issue's central claim is that a prose rewrite changed no behaviour, and
for a shell script the sharpest form of that is: a person running the command
sees exactly the same words. `scripts/compare-behaviour.py` reads a diff and
is only ever run over one, so nothing held the claim once a batch had landed.

This holds it. Every `echo` and `printf` line in `scripts/` and `hooks/` must
match the pre-issue base byte for byte. It caught one real change: batch 4's
clarity fixups reworded a `release.sh` failure message, whose old advice is
stale but whose correction changes printed output and so belongs with the
other printed-output fixes in their own issue.

Comments are not read here, which is the point - the comment above that
message was rewritten and should have been.

The comparison is between the commit before the issue and the commit that
landed it, not the working tree. The claim is about what that issue changed,
and that is a fixed fact about a fixed range. Comparing against the working
tree turned it into a freeze on every later printed string, so an issue whose
job is to change a message - `hook-failure-matrix`, which retires "triage"
from the hook's refusals - could not land.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# The branch tip immediately before this issue's first commit.
PRE_ISSUE_BASE = "89cf5ef"
# The merge that landed it: pull request #155.
LANDED = "b3b35c0"

_SURFACES = ("scripts", "hooks")
_PRINTS_RE = re.compile(r"^\s*(?:echo|printf)\b.*$", re.M)


def _printed_lines(text: str) -> list[str]:
    """Every `echo` or `printf` line, with surrounding whitespace dropped.

    Read as lines rather than parsed: the question is what a person sees, and
    a changed line is a changed message whether or not a shell parser agrees
    about the quoting.
    """
    return [m.group(0).strip() for m in _PRINTS_RE.finditer(text)]


def _at(commit: str, rel: str) -> str | None:
    result = subprocess.run(
        ["git", "show", f"{commit}:{rel}"],
        cwd=str(ROOT), capture_output=True, text=True)
    return result.stdout if result.returncode == 0 else None


def _shell_files() -> list[str]:
    out = subprocess.run(["git", "ls-tree", "-r", "--name-only", LANDED,
                          *_SURFACES],
                         cwd=str(ROOT), capture_output=True, text=True,
                         check=True)
    return [p for p in out.stdout.split()
            if p.endswith(".sh") or "/" not in p.removeprefix("scripts/")
            and p.startswith(("scripts/", "hooks/"))]


def test_pbw_f1_no_printed_string_in_scripts_or_hooks_changed():
    """`PBW-F1`: a prose edit that changes behaviour is refused, and a
    changed printed string is a changed behaviour."""
    drift = []
    checked = 0
    for rel in sorted(_shell_files()):
        before = _at(PRE_ISSUE_BASE, rel)
        if before is None:
            continue  # added by this issue, so nothing to preserve
        now = _at(LANDED, rel) or ""
        checked += 1
        was, is_now = _printed_lines(before), _printed_lines(now)
        if was != is_now:
            only_before = [l for l in was if l not in is_now]
            only_now = [l for l in is_now if l not in was]
            for line in only_before:
                drift.append(f"{rel}: gone   {line[:120]}")
            for line in only_now:
                drift.append(f"{rel}: added  {line[:120]}")

    assert checked > 0, "no shell file was compared - the file list is wrong"
    assert not drift, (
        f"{len(drift)} printed line(s) differ between {PRE_ISSUE_BASE} and "
        f"{LANDED}. This "
        f"issue claims no printed string changed, so a correction here "
        f"belongs in the printed-output issue instead:\n  "
        + "\n  ".join(drift))
