"""Acceptance tests for task release-guide-rewrite.

The release-checklist file at v1.2.0 was the rc.1 → 1.0.0 historical
checklist. The release-checklist-disposition Spike (F) decided to
rewrite it as a generic release guide: keep the durable operational
content (the make-based release procedure, the tarball-hygiene lesson,
cross-references to the test surfaces that defend each invariant),
drop the resolved rc.1 history.

These tests assert the post-rewrite content (presence of the durable
steps, presence of the cross-references) and the absence of the
rc.1-specific content (no readiness table, no rc.1-specific owed
items, no "1.0.0-rc.1 → 1.0.0" framing).

The drift-guard pattern from `tests/test_cli_surface_drift.py` applies
here too: tests bind to executable-artifact references (the test file
paths, the security doc path, the release script path), so the
release guide stays current as those defenders evolve.
"""
import re
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _release_guide_path():
    """Resolve the rewritten release guide. Build may keep the original
    filename (`docs/release-checklist.md`) or rename to `docs/releasing.md`.
    Either is acceptable; the test finds whichever exists.
    """
    candidates = [
        ROOT / "docs" / "releasing.md",
        ROOT / "docs" / "release-checklist.md",
    ]
    found = [p for p in candidates if p.exists()]
    assert found, (
        f"Neither {candidates[0]} nor {candidates[1]} exists. "
        f"The release guide must live at one of these paths."
    )
    return found[0]


def _release_guide_text():
    return _release_guide_path().read_text()


def test_trc_a1_release_guide_contains_durable_operational_steps():
    """The release guide names each step of the make-based release procedure
    and preserves the tarball-hygiene lesson."""
    text = _release_guide_text()

    # The numbered operational steps (or their substance - the test is
    # forgiving about heading shape but firm about what's named).
    must_have_steps = [
        ("VERSION bump", r"\bVERSION\b"),
        ("make clean", r"make clean"),
        ("make test", r"make test"),
        ("make ci", r"make ci"),
        ("make release", r"make release"),
        ("tarball verification step (out of source tree)", r"(?is)(out\s+of\s+(?:the\s+)?source\s+tree|extracted\s+(?:the\s+)?(?:release|tarball)|tar\s+-xzf)"),
    ]
    missing = [name for name, pat in must_have_steps if not re.search(pat, text)]
    assert not missing, (
        f"Release guide is missing operational step(s): {missing}. Per the "
        f"F Spike's decision, the durable procedure must survive the rewrite."
    )

    # The tarball-hygiene lesson - the "do not zip from Finder / Download
    # ZIP" rule. Forgiving about exact wording; firm about the substance.
    has_tarball_hygiene = bool(
        re.search(r"(?is)(don'?t|do\s+not|never).{0,80}zip", text)
        or re.search(r"(?is)download\s+zip", text)
    )
    assert has_tarball_hygiene, (
        "Release guide is missing the tarball-hygiene lesson - the rule "
        "that the distributed artifact must be the `make release` tarball, "
        "not a zip from Finder or 'Download ZIP'. That lesson was earned "
        "the hard way by a v1 reviewer; the rewrite must preserve it."
    )


def test_trc_a2_release_guide_cross_references_the_defenders():
    """The release guide points at the test surfaces / scripts / docs that
    defend each invariant."""
    text = _release_guide_text()

    must_reference = [
        "scripts/release.sh",
        "docs/security.md",
        "tests/test_release_invariants.py",
        "tests/test_cli_surface_drift.py",
    ]
    missing = [ref for ref in must_reference if ref not in text]
    assert not missing, (
        f"Release guide does not cross-reference {missing}. A future reader "
        f"following the guide must reach the test surface and security "
        f"guidance that defends each release invariant."
    )


def test_trc_b1_release_guide_does_not_carry_rc1_specific_history():
    """The rewrite drops the rc.1 readiness table, the rc.1-specific owed
    items, and the rc.1-only framing."""
    text = _release_guide_text()

    # The "1.0.0-rc.1 → 1.0.0" framing must be gone from title/opening.
    # (The string may still appear in a "history" note if there's one, but
    # it must not be in the title.)
    first_chunk = text[:400]
    assert not re.search(r"1\.0\.0-rc\.1\s*[→-]\s*1\.0\.0", first_chunk), (
        "The release guide's opening still frames it as the rc.1 → 1.0.0 "
        "checklist. The rewrite was supposed to drop that framing."
    )

    # The v1 readiness table - 13 rows about whether v1 items were Done -
    # must be gone. We look for the distinctive header phrase.
    assert "Status of the v1 checklist" not in text, (
        "The release guide still contains the 'Status of the v1 checklist' "
        "readiness table. That's resolved rc.1 history; it should be gone."
    )

    # The rc.1-specific owed items must be gone. We check for distinctive
    # phrases that only appeared in the rc.1 list.
    rc1_specific_phrases = [
        "Pilot Compass on at least one real task per category",
        # The "<YOUR-ORG-OR-FORK>" placeholder is from the rc.1 era.
        "YOUR-ORG-OR-FORK",
    ]
    leftover = [phrase for phrase in rc1_specific_phrases if phrase in text]
    assert not leftover, (
        f"Release guide still carries rc.1-specific content: {leftover}. "
        f"Those items were resolved before/with the 1.0.0 release; they "
        f"don't belong in a generic release guide."
    )


# ---------------------------------------------------------------------------
# Task release-script-portable-tar, SCN-001
# ---------------------------------------------------------------------------

def test_release_script_packages_on_this_platform(tmp_path):
    """The packaging step must work with whichever tar this machine has.

    `scripts/release.sh` prefixed every archive entry with the version
    directory using GNU tar's `--transform`. macOS ships bsdtar, which spells
    the same operation `-s` and rejects `--transform` outright, so the script
    ran all four pre-flight checks, passed them, and then exited 1 having
    produced nothing.

    This runs the script's own flag-selection helper against a fixture tree and
    inspects the result with `tar -tzf`, so it exercises the branch matching the
    tar on the running machine - meaningful on a macOS laptop and on Linux CI
    rather than passing without checking anything on one of them.
    """
    import subprocess

    script = ROOT / "scripts" / "release.sh"
    text = script.read_text()

    # The script must not hard-code the GNU-only spelling.
    assert '--transform "s,^,compass-' not in text, (
        "scripts/release.sh still uses GNU tar's --transform unconditionally; "
        "bsdtar rejects it and the packaging step cannot run on macOS."
    )
    assert "tar_prefix_flags" in text, (
        "scripts/release.sh should select its prefix flag through a named "
        "helper so this test can exercise the same logic the release uses."
    )

    # Build a fixture tree and package it using the script's own helper.
    src = tmp_path / "src"
    (src / "sub").mkdir(parents=True)
    (src / "f.txt").write_text("a\n")
    (src / "sub" / "g.txt").write_text("b\n")
    out = tmp_path / "out.tar.gz"

    driver = (
        f'set -eu\n'
        f'. "{script}" --source-only\n'
        f'cd "{src}"\n'
        f'tar -czf "{out}" $(tar_prefix_flags "1.8.0") .\n'
    )
    r = subprocess.run(["bash", "-c", driver], capture_output=True, text=True)
    assert r.returncode == 0, f"packaging failed:\n{r.stdout}\n{r.stderr}"

    listing = subprocess.run(["tar", "-tzf", str(out)],
                             capture_output=True, text=True, check=True).stdout
    entries = [e for e in listing.splitlines() if e.strip() not in ("./", ".")]
    assert entries, "the tarball is empty"

    prefix = "compass-1.8.0/"
    unprefixed = [e for e in entries if not e.startswith(prefix)]
    assert not unprefixed, (
        f"entries not prefixed with {prefix!r}: {unprefixed}")

    escaping = [e for e in entries if e.startswith("/") or ".." in e.split("/")]
    assert not escaping, f"entries escape the version directory: {escaping}"


def _release_file_list():
    """The list of paths the release script will package, via its own helper."""
    import subprocess

    script = ROOT / "scripts" / "release.sh"
    driver = (
        f'set -eu\n'
        f'. "{script}" --source-only\n'
        f'cd "{ROOT}"\n'
        f'release_file_list\n'
    )
    r = subprocess.run(["bash", "-c", driver], capture_output=True, text=True)
    assert r.returncode == 0, f"release_file_list failed:\n{r.stdout}\n{r.stderr}"
    return [l.strip() for l in r.stdout.splitlines() if l.strip()]


def test_release_file_list_keeps_examples_and_drops_repo_work(tmp_path):
    """SCN-002. BSD tar has no --anchored, so the script's `./`-prefixed
    exclude patterns matched at any depth and stripped
    `examples/*/.compass/work/<slug>/manifest.yml` along with the repo's own
    dev state."""
    paths = _release_file_list()

    own_work = [p for p in paths if p.lstrip("./").startswith(".compass/work")]
    assert not own_work, (
        f"the repository's own .compass/work must not ship: {own_work[:5]}")

    example_tasks = [p for p in paths
                     if "examples/" in p and "/.compass/work/" in p
                     and p.endswith("manifest.yml")]
    assert len(example_tasks) >= 5, (
        "every worked example must keep its .compass/work/<slug>/manifest.yml; "
        f"found {len(example_tasks)}: {example_tasks}")


def test_release_file_list_excludes_untracked_files(tmp_path):
    """SCN-003. The script archived the working tree, so an untracked local
    file shipped to whoever downloaded the release - and the noise check
    reported clean, because an untracked config file matches no noise pattern."""
    import subprocess

    marker = ROOT / "_release_untracked_probe.txt"
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", marker.name],
                             capture_output=True, text=True, cwd=str(ROOT))
    assert tracked.returncode != 0, "probe file is tracked; choose another name"

    marker.write_text("this file is untracked and must never ship\n")
    try:
        paths = _release_file_list()
    finally:
        marker.unlink(missing_ok=True)

    leaked = [p for p in paths if marker.name in p]
    assert not leaked, f"untracked file shipped in the release: {leaked}"
