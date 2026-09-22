"""Where a registered document is, and what happens when the entry is wrong.

Scenario group A of `docs-compass-artifacts`, plus three of its failure modes.

A path in the manifest's `artifacts:` registry is measured from the PROJECT
ROOT, not from the issue directory. That is what lets a document live under
`docs/compass/<date>-<slug>/` while the manifest still names it. A bare
filename such as `verification-report.md` does not resolve from the
registry; the flat-filename fallback finds it beside the manifest.

The `evidence:` registry is a different key read by different code and is NOT
affected: evidence stays under `.compass/work/<slug>/evidence/`.
"""

import os

import pytest
import yaml

from compass_pkg import core
from compass_pkg.core import (
    ABSENT,
    FOUND,
    OMITTED,
    UNRESOLVABLE,
    artifact_path,
    resolve_artifact,
)

# Read through getattr on purpose. Importing a name that does not exist yet is
# a collection error, and a collection error is indistinguishable from a broken
# test file - `compass tdd-red` refuses one as evidence for exactly that
# reason. This way the red is an assertion that failed, which is what a red is
# supposed to be.
REFUSED = getattr(core, "REFUSED", "refused")


def _issue(project, slug="an-issue", artifacts=None):
    """An issue directory with a manifest, and nothing else."""
    task_dir = project / ".compass" / "work" / slug
    task_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": "2.0",
        "issue": slug,
        "created": "2026-09-08",
        "status": "active",
    }
    if artifacts is not None:
        manifest["artifacts"] = artifacts
    (task_dir / "manifest.yml").write_text(
        yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    return task_dir


def _doc(project, relpath, text="# a document\n"):
    """A file at a project-relative path, with its parents."""
    path = project / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


# --- `TRC-A1` ------------------------------------------------------------------

def test_trc_a1_a_registered_document_outside_the_issue_directory_resolves(
        project):
    """A registered path names a place outside .compass/work/ and is found."""
    registered = "docs/compass/2026-09-08-an-issue/technical-design.md"
    task_dir = _issue(project, artifacts=[{
        "id": "ART-TECHNICAL_DESIGN",
        "kind": "technical-design",
        "status": "draft",
        "reason": "every initiative carries one",
        "path": registered,
    }])
    written = _doc(project, registered)

    found = artifact_path(str(task_dir), "technical-design.md")

    assert os.path.realpath(found) == os.path.realpath(str(written))
    assert ".compass/work" not in found, (
        "a registered path outside the issue directory resolved back into it: "
        f"{found}")


# --- `TRC-A2` ------------------------------------------------------------------

def test_trc_a2_a_registered_path_is_anchored_to_the_project(
        project, monkeypatch, tmp_path):
    """The answer does not depend on where the caller happens to be."""
    registered = "docs/compass/2026-09-08-an-issue/acceptance-criteria.md"
    task_dir = _issue(project, artifacts=[{
        "id": "ART-ACCEPTANCE_CRITERIA",
        "kind": "acceptance-criteria",
        "status": "draft",
        "reason": "every initiative carries one",
        "path": registered,
    }])
    written = _doc(project, registered)

    monkeypatch.chdir(project)
    from_root = artifact_path(str(task_dir), "acceptance-criteria.md")

    elsewhere = project / "cli"
    elsewhere.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(elsewhere)
    from_subdir = artifact_path(str(task_dir), "acceptance-criteria.md")

    assert os.path.realpath(from_root) == os.path.realpath(str(written))
    assert os.path.realpath(from_subdir) == os.path.realpath(from_root), (
        "the resolved path moved when the working directory did")


# --- `TRC-A3` ------------------------------------------------------------------

def test_trc_a3_an_issue_with_no_registry_resolves_as_today(project):
    """No registry at all: the flat filename beside the manifest still wins."""
    task_dir = _issue(project)          # no artifacts key
    beside = task_dir / "acceptance-criteria.md"
    beside.write_text("# beside the manifest\n", encoding="utf-8")

    state, path, reason = resolve_artifact(str(task_dir),
                                           "acceptance-criteria")

    assert state == FOUND
    assert os.path.realpath(path) == os.path.realpath(str(beside))
    assert reason == "the flat filename"


def test_trc_a3_an_unmigrated_entry_still_finds_its_document(project):
    """The breaking half, stated as behaviour.

    A bare filename such as `verification-report.md` does not resolve from
    the registry; the flat-filename fallback finds it beside the manifest -
    and the reason says the registered path was not there, which is what
    makes an unmigrated registry visible rather than silent.
    """
    task_dir = _issue(project, artifacts=[{
        "id": "ART-VERIFICATION_REPORT",
        "kind": "verification-report",
        "status": "draft",
        "reason": "every initiative carries one",
        "path": "verification-report.md",      # a bare, unregistered path
    }])
    beside = task_dir / "verification-report.md"
    beside.write_text("# beside the manifest\n", encoding="utf-8")

    state, path, reason = resolve_artifact(str(task_dir),
                                           "verification-report")

    assert state == FOUND
    assert os.path.realpath(path) == os.path.realpath(str(beside))
    assert "verification-report.md" in reason and "not there" in reason, (
        "an unmigrated entry resolved silently; the reason must say the "
        f"registered path missed. Got: {reason!r}")


# --- `TRC-A4` ------------------------------------------------------------------

def test_trc_a4_the_schema_says_what_the_path_is_relative_to():
    """The schema is where a reader finds out, so it has to say."""
    import json
    import pathlib

    root = pathlib.Path(__file__).resolve().parent.parent
    schema = json.loads(
        (root / "schemas" / "manifest.schema.json").read_text(encoding="utf-8"))
    desc = (schema["properties"]["artifacts"]["items"]["properties"]["path"]
            ["description"])

    assert "project root" in desc.lower(), (
        "the artifacts registry's `path` description does not say it is "
        f"measured from the project root. Got: {desc!r}")

    # The claim, not the phrase. The description legitimately mentions the
    # issue directory when contrasting this registry with the evidence one, so
    # a bare substring search would fail on a correct sentence. What must not
    # survive is the OPENING claim about this field, which is where a reader
    # stops.
    first_sentence = desc.split(".")[0].lower()
    assert "relative to the issue directory" not in first_sentence, (
        "the schema still opens by saying a registered path is relative to the "
        f"issue directory. Got: {first_sentence!r}")


# --- `TRC-G1` ------------------------------------------------------------------

def test_trc_g1_a_registered_path_with_no_file_reports_not_written(project):
    """Entry points somewhere, nothing there, nothing beside the manifest."""
    task_dir = _issue(project, artifacts=[{
        "id": "ART-TECHNICAL_DESIGN",
        "kind": "technical-design",
        "status": "draft",
        "reason": "every initiative carries one",
        "path": "docs/compass/2026-09-08-an-issue/technical-design.md",
    }])

    state, path, reason = resolve_artifact(str(task_dir), "technical-design")

    assert state == UNRESOLVABLE
    assert path is None
    assert "docs/compass/2026-09-08-an-issue/technical-design.md" in reason, (
        f"the refusal does not name the registered path it tried: {reason!r}")


# --- `TRC-G3` ------------------------------------------------------------------

def test_trc_g3_the_registered_copy_wins_and_the_stale_one_is_reported(
        project):
    """Same kind in both places: the registry decides, and says so."""
    registered = "docs/compass/2026-09-08-an-issue/technical-design.md"
    task_dir = _issue(project, artifacts=[{
        "id": "ART-TECHNICAL_DESIGN",
        "kind": "technical-design",
        "status": "draft",
        "reason": "every initiative carries one",
        "path": registered,
    }])
    current = _doc(project, registered, "# the current one\n")
    stale = task_dir / "technical-design.md"
    stale.write_text("# the stale one\n", encoding="utf-8")

    state, path, reason = resolve_artifact(str(task_dir), "technical-design")

    assert state == FOUND
    assert os.path.realpath(path) == os.path.realpath(str(current)), (
        "the stale copy beside the manifest won over the registered one")
    assert "also" in reason.lower() or "stale" in reason.lower(), (
        "a second copy of the same document exists and the reason does not "
        f"mention it, so nobody will delete it. Got: {reason!r}")


# --- `TRC-G4` ------------------------------------------------------------------

@pytest.mark.parametrize("escape", [
    "../outside.md",
    "docs/../../outside.md",
    "/etc/hosts",
])
def test_trc_g4_a_path_outside_the_project_is_refused(project, escape):
    """A registered path is data. It does not get to name anything it likes."""
    task_dir = _issue(project, artifacts=[{
        "id": "ART-TECHNICAL_DESIGN",
        "kind": "technical-design",
        "status": "draft",
        "reason": "every initiative carries one",
        "path": escape,
    }])

    state, path, reason = resolve_artifact(str(task_dir), "technical-design")

    assert state == REFUSED, (
        f"a path escaping the project root was not refused: {escape!r} "
        f"gave {state}")
    assert path is None
    assert escape in reason, (
        f"the refusal does not name the path it refused: {reason!r}")


def test_trc_g4_the_refusal_does_not_fall_back_to_the_flat_filename(project):
    """The fallback must not override a refusal.

    Without this, an escaping path plus a file beside the manifest reads as a
    clean FOUND and the refusal never fires - the check would pass on the
    fallback rather than on the rule.
    """
    task_dir = _issue(project, artifacts=[{
        "id": "ART-TECHNICAL_DESIGN",
        "kind": "technical-design",
        "status": "draft",
        "reason": "every initiative carries one",
        "path": "../outside.md",
    }])
    (task_dir / "technical-design.md").write_text("# beside\n",
                                                  encoding="utf-8")

    state, path, _ = resolve_artifact(str(task_dir), "technical-design")

    assert state == REFUSED
    assert path is None


# --- the evidence registry is not affected ------------------------------------

def test_the_artifact_registry_does_not_swallow_evidence_entries(project):
    """Evidence does not move, so its paths do not change meaning.

    Named here rather than in the evidence tests because reading `evidence:`
    paths from the project root would break every gate in the repository at
    once, so that is the boundary the artifact resolver must stop at. The
    two registries are separate keys, and the artifact resolver must not see
    into the other one.
    """
    task_dir = _issue(project)
    manifest = yaml.safe_load(
        (task_dir / "manifest.yml").read_text(encoding="utf-8"))
    manifest["evidence"] = [{
        "id": "EV-GREEN",
        "type": "test-run",
        "path": "evidence/green-TRC-A1.json",
    }]
    (task_dir / "manifest.yml").write_text(
        yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")

    evidence = task_dir / "evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / "green-TRC-A1.json").write_text('{"passed": true}',
                                                encoding="utf-8")

    # No artifacts entry of any kind, so the artifact resolver has nothing to
    # find - it must not reach into `evidence:` and answer from there.
    state, path, _ = resolve_artifact(str(task_dir), "test-run")
    assert state == ABSENT, (
        f"the artifact resolver answered from the evidence registry: {path}")


# --- ABSENT and OMITTED are unchanged -----------------------------------------

def test_absent_and_omitted_are_unchanged(project):
    """The two states that never consult a path keep their behaviour."""
    absent_dir = _issue(project, slug="nothing-written")
    state, path, _ = resolve_artifact(str(absent_dir), "technical-design")
    assert state == ABSENT
    assert path is None

    omitted_dir = _issue(project, slug="deliberately-omitted", artifacts=[{
        "id": "ART-THREAT_MODEL",
        "kind": "threat-model",
        "status": "omitted",
        "reason": "no trust boundary is crossed",
    }])
    state, path, reason = resolve_artifact(str(omitted_dir), "threat-model")
    assert state == OMITTED
    assert path is None
    assert reason == "no trust boundary is crossed"
