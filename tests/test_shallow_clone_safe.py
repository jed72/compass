"""The suite means the same thing on a shallow clone as on a full one.

Two tests assert what their own issue did by diffing a pinned commit range.
`actions/checkout` fetches shallow history by default, so those objects are
absent in continuous integration and `git diff` exits 128 - green on every
developer machine, red on the one nobody watches.

The range check may degrade when the history genuinely is not there. What may
not degrade is the content assertion beside it, which needs no history and
carries the invariant that matters now.

Spec: .compass/work/tests-survive-shallow-clone/acceptance-criteria.md (TRC-1).
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

# The two assertions that pin a commit range.
SHA_PINNED = [
    ("tests/test_human_voice.py", "trc_f3"),
    ("tests/test_voice_audition_standing.py", "trc_f1"),
]


@pytest.fixture(scope="module")
def shallow_clone(tmp_path_factory):
    """A depth-1 clone of the current branch - the shape CI checks out.

    Fails rather than skips if the clone cannot be made: a test that quietly
    stops proving the thing it exists to prove is how this defect reached CI
    in the first place.
    """
    dest = tmp_path_factory.mktemp("shallow") / "repo"
    branch = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True,
    ).stdout.strip()
    result = subprocess.run(
        ["git", "clone", "--depth", "1", "-b", branch,
         f"file://{REPO_ROOT}", str(dest)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, (
        f"could not build a shallow clone, so the shallow-clone claim is "
        f"unproven:\n{result.stderr}"
    )
    # Precondition: it really is shallow. A full clone here would make every
    # assertion below vacuous.
    assert (dest / ".git" / "shallow").exists(), (
        "the clone is not shallow - nothing below proves anything"
    )

    # Overlay the working tree's tests over the clone's committed ones. The
    # clone can only carry what is committed, so without this the test would
    # report on the last commit rather than on the code in front of us - it
    # could never go green before the fix was committed, which is the wrong
    # way round. The shallow *history* is what matters here, not the
    # committed test bodies.
    for src in (REPO_ROOT / "tests").glob("*.py"):
        shutil.copyfile(src, dest / "tests" / src.name)
    return dest


@pytest.mark.parametrize("test_file,selector", SHA_PINNED)
def test_the_pinned_assertions_run_on_a_shallow_clone(shallow_clone, test_file, selector):
    """They may skip their range check; they may not die on a missing object."""
    result = subprocess.run(
        ["python3", "-m", "pytest", test_file, "-k", selector, "-q"],
        cwd=str(shallow_clone), capture_output=True, text=True, timeout=300,
    )
    combined = result.stdout + result.stderr
    assert "CalledProcessError" not in combined, (
        f"{test_file} died on a missing git object instead of degrading:\n"
        f"{combined[-2000:]}"
    )
    assert result.returncode == 0, (
        f"{test_file} -k {selector} failed on a shallow clone:\n"
        f"{combined[-2000:]}"
    )
