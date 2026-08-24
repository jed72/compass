"""The vocabulary rename: assess, plan, intent, technical-design.

Five words in this framework named more than one thing, or named a thing whose
own output disagreed with them:

  the stage that produces an `assessment:` block was called `triage`
  the stage whose key, skill and agent all say `plan` was commanded as `design`
  `design` named a command, an artifact, an artifact kind, a CLI verb and a
      role, and was the only overloaded word with no glossary entry
  `/compass:intent` wrote a file called `prd.md`
  `frame` was banned as a phase name and survived as a live machine key,
      because governance/*.yml is not a scanned surface

THE ORDER IS THE DESIGN. Every new spelling is accepted before any caller
switches to it - see design.md D2. These tests are written so the accept phase
can be green on its own.

Scenario ids trace to
.compass/work/the-vocabulary-rename/acceptance-criteria.md.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "cli"))

MAP = REPO_ROOT / "cli" / "migrate-map.yml"

# The six that move. `plan` and `verify` are deliberately absent: `plan` stays
# because the command moves TO it, and `verify` already agrees.
STAGE_RENAMES = {
    "frame": "assess",
    "specify": "define",
    "clarify": "refine",
    "distribute": "breakdown",
    "build": "implement",
    "land": "ship",
}
STAGE_UNCHANGED = {"plan", "verify"}


def _map():
    import compass_pkg  # resolves the bundled yaml
    import yaml
    return yaml.safe_load(MAP.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Group C - the map, and any copy of it
# ---------------------------------------------------------------------------

def test_trc_c1():
    """TRC-C1: the map carries the stage keys, and any copy is proven to match.

    The second half is the point. The guard that existed before this asserted
    `migrate.artifact_name_map() == artifacts` - and that function reads the
    map file whenever it can, so it compared the file to itself and the
    in-module fallback was never exercised. They agreed, all six entries; but
    this change adds to both, which is when such a guard gets relied on.
    """
    import compass_pkg  # noqa: F401
    from compass_pkg import migrate

    data = _map()
    keys = data.get("stage_keys")
    assert keys, (
        "cli/migrate-map.yml has no `stage_keys:` section. The stage keys are "
        "the one set of renames the map never covered, which is why they were "
        "never migrated. Sections present: %s" % sorted(data))
    assert keys == STAGE_RENAMES, (
        "the stage-key map is not the six renames this issue makes:\n"
        "  expected: %s\n  found:    %s" % (STAGE_RENAMES, keys))
    for k in STAGE_UNCHANGED:
        assert k not in keys, (
            "%r is in the rename map and must not be. `plan` stays because the "
            "command moves TO it - migrate-map.yml records that the artifact "
            "was `plan.md` in v1, so a later reader may take the key for a "
            "vestige and 'fix' it. `verify` already agrees." % k)

    # THE FALLBACK, EXERCISED. Point the reader at a path that is not there so
    # the in-module copy is what answers. Patching `_map_path` rather than
    # `os.path.join` on purpose: a mock that matches on argument shape is one
    # more thing that can silently stop matching, and then this guard goes back
    # to comparing the file with itself - which is the defect it exists for.
    real_artifacts = migrate.artifact_name_map()
    real_stages = migrate.stage_key_map()
    original = migrate._map_path
    try:
        migrate._map_path = lambda: "/nonexistent/migrate-map.yml"
        assert not Path(migrate._map_path()).exists(), (
            "the path meant to be unreadable exists, so the fallback was never "
            "reached and this compares the file with itself")
        fb_artifacts = migrate.artifact_name_map()
        fb_stages = migrate.stage_key_map()
    finally:
        migrate._map_path = original

    for name, from_file, from_code in (("artifacts", real_artifacts, fb_artifacts),
                                       ("stage_keys", real_stages, fb_stages)):
        assert from_code == from_file, (
            "the in-module fallback for `%s` has drifted from "
            "cli/migrate-map.yml, so a bare checkout would migrate differently "
            "from an installed one:\n  only in the file: %s\n"
            "  only in the code: %s"
            % (name, sorted(set(from_file) - set(from_code)),
               sorted(set(from_code) - set(from_file))))


def test_trc_e2_map_guard_declines_an_empty_input():
    """TRC-E2 for the map: a scan handed nothing does not report a pass."""
    from compass_pkg import migrate

    assert migrate.artifact_name_map(), (
        "the artifact map is empty, so every assertion about it above compares "
        "two empty things and passes")
    assert _map().get("stage_keys"), "the stage-key map is empty"


# ---------------------------------------------------------------------------
# Group B - nothing already written breaks
# ---------------------------------------------------------------------------

def test_trc_b1():
    """TRC-B1: a spine written before the rename still reads.

    94 landed issues carry the retired keys. ADR-006 makes this
    non-negotiable inside a major version.
    """
    from compass_pkg.core import normalize_spine

    old = {"schema_version": "2.0", "task": "t",
           "stages": {k: "full" for k in STAGE_RENAMES} | {"plan": "full",
                                                           "verify": "full"}}
    got = normalize_spine(old)["stages"]
    for retired, current in STAGE_RENAMES.items():
        assert current in got, (
            "a spine holding the retired stage key %r did not resolve to %r - "
            "94 landed issues carry these:\n  %s" % (retired, current, got))
        assert retired not in got, (
            "%r survived normalisation alongside %r" % (retired, current))
    for k in STAGE_UNCHANGED:
        assert k in got, "%r must survive normalisation unchanged" % k

    # A spine already speaking the new keys normalises to itself.
    new = {"schema_version": "2.0", "task": "t",
           "stages": {v: "full" for v in STAGE_RENAMES.values()}}
    assert normalize_spine(new)["stages"] == new["stages"], (
        "a spine holding the current keys did not survive normalisation")


def test_trc_b2():
    """TRC-B2: a document written before the rename still resolves."""
    import tempfile
    from compass_pkg.core import FOUND, resolve_artifact

    tmp = Path(tempfile.mkdtemp(prefix="compass-rename-"))
    (tmp / "design.md").write_text("# old name\n")
    (tmp / "prd.md").write_text("# old name\n")

    for kind, flat in (("technical-design", "design.md"), ("intent", "prd.md")):
        state, path, reason = resolve_artifact(str(tmp), kind)
        assert state == FOUND, (
            "asking for %r did not find the file a landed issue actually holds "
            "(%s): %s" % (kind, flat, reason))
        assert Path(path).name == flat, (
            "resolved to %s rather than the file on disk, %s"
            % (Path(path).name, flat))
        assert flat in reason or "flat" in reason, (
            "the reason does not say which route found it: " + reason)
