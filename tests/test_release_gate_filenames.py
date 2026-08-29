"""The release script greps for filenames that exist (issue
release-gate-greps-the-old-manifest-filename).

`scripts/release.sh` hard-fails the release if a worked example's issue record
is missing from the tarball. It greps the tarball listing for that record by
name - and the name was `task.yml` until the record was renamed to
`manifest.yml`. The rename commit touched this script, updated the check's
printed message, and left both greps on the old name.

The result is a gate that cannot pass. That is the mirror of the defect class
this repository usually chases: a check that cannot fail hides because nobody
sees a failure, and a check that cannot pass hides because a release-time gate
is only exercised at release time. Both look exactly like a check that ran.

Scenario ids: TRC-A1, TRC-F1 in
.compass/work/release-gate-greps-the-old-manifest-filename/acceptance-criteria.md
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RELEASE_SH = REPO_ROOT / "scripts" / "release.sh"

# Filenames the script may grep for inside the tarball listing. Each must be a
# real artifact name. `task.yml` is deliberately absent: it is the pre-rename
# spelling, and greping for it is the defect these scenarios cover.
CURRENT_RECORD = "manifest.yml"


def _release_sh() -> str:
    assert RELEASE_SH.is_file(), "scripts/release.sh is missing"
    return RELEASE_SH.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# TRC-A1 - the examples check names the file that exists
# ---------------------------------------------------------------------------

def test_the_examples_check_names_the_file_that_exists():
    body = _release_sh()

    # The check exists at all. Without this the two assertions below would
    # pass over a script that no longer verifies the examples.
    assert "examples integrity" in body, (
        "scripts/release.sh no longer carries the examples-integrity check, "
        "so nothing verifies that a worked example's issue record survives "
        "packaging - the bug that check was written for")

    greps = re.findall(r'grep [^\n]*examples/\$e[^\n]*', body)
    assert greps, (
        "the examples-integrity check no longer greps the tarball listing "
        "per example, so this check is reading a script that has changed "
        "shape and is asserting nothing")

    for line in greps:
        assert CURRENT_RECORD.replace(".", r"\.") in line or CURRENT_RECORD in line, (
            f"the examples check greps for something other than "
            f"{CURRENT_RECORD}:\n  {line.strip()}\n"
            f"A release-time gate that names a file which does not exist "
            f"fails every release, on a good tarball as readily as a bad one")
        assert "task.yml" not in line and r"task\.yml" not in line, (
            f"the examples check still greps for `task.yml`, the name the "
            f"issue record had before it was renamed to {CURRENT_RECORD}:\n"
            f"  {line.strip()}")

    # The exemption markers beside those greps state why naming a path there
    # is legitimate. A reason that describes a path which no longer exists is
    # a reason for something else.
    for n, line in enumerate(body.splitlines(), 1):
        if "vocabulary-scan: allow" in line and "tarball listing" in line:
            assert "task.yml" not in line, (
                f"scripts/release.sh:{n} - the exemption reason still "
                f"describes a grep for `task.yml`")


# ---------------------------------------------------------------------------
# TRC-F1 - a check that cannot pass is refused
# ---------------------------------------------------------------------------

def test_a_check_that_cannot_pass_is_refused():
    """Every repository path the release script greps for must exist.

    Generalised from the specific defect, because the specific defect is not
    interesting on its own: what matters is that a release gate never names a
    file the repository does not have. A release-time check is exercised once
    a release, so a wrong name survives until someone tries to ship.
    """
    body = _release_sh()

    # Paths the script names inside the repository, as opposed to inside the
    # tarball (which is prefixed with the release directory) or constructed
    # from shell variables.
    referenced = set()
    for m in re.finditer(r'(?<![\w/$."])((?:examples|governance|schemas|cli|'
                         r'docs|tests|skills|agents|commands|approaches|'
                         r'templates|hooks|scripts)/[\w./-]+)', body):
        path = m.group(1)
        if "$" in path or "*" in path:
            continue
        referenced.add(path)

    assert len(referenced) >= 3, (
        f"only {len(referenced)} repository paths were read out of "
        f"scripts/release.sh - the pattern has stopped matching and this "
        f"check is passing over almost nothing")

    missing = sorted(p for p in referenced
                     if not (REPO_ROOT / p).exists()
                     and not (REPO_ROOT / p.rstrip("/")).exists())
    assert not missing, (
        "scripts/release.sh names repository path(s) that do not exist:\n  "
        + "\n  ".join(missing)
        + "\nA release gate is run once a release, so a name that stopped "
          "resolving stays wrong until someone tries to ship.")
