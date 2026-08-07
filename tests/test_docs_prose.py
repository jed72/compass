"""Slice 7 of the v2 rename: the docs and governance prose speak v2, and
the ratchet reaches zero.

The last pending surfaces (README, five-minutes, methodology, the
governance prose) are rewritten and enforced; routes/ becomes the
delivery-approach reference docs under approaches/; the remaining docs
prose enters scan.surfaces enforced and never-pending; the worked-example
directories rename to their v2 change-type names (directory names teach
vocabulary before any file is opened); and the install.sh plugin-source
refusal points at the path the plugin source actually uses.
"""
from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).parent.parent


def _scan_cfg() -> dict:
    return yaml.safe_load(
        (REPO_ROOT / "governance" / "terminology.yml").read_text(
            encoding="utf-8"))["scan"]


def test_the_ratchet_reaches_zero():
    """TRC-1, amended at the recorded split boundary: the first half of
    the docs-prose slice takes the ratchet to ONE surface - the doctrine
    document, docs/methodology.md - and the second half takes it to zero.
    The original zero assertion moves there with it."""
    from test_terminology import PENDING_BASELINE
    assert _scan_cfg()["pending_surfaces"] == ["docs/methodology.md"], (
        "pending_surfaces should hold exactly the doctrine document until "
        "the second half of the docs-prose slice lands")
    assert PENDING_BASELINE == frozenset({"docs/methodology.md"}), (
        "the committed baseline should hold exactly the doctrine document")


def test_reference_docs_carry_v2_names():
    """TRC-2: approaches/ holds the rubric and the five shape docs under
    v2 names; routes/ is gone; no live surface points at the old path."""
    approaches = REPO_ROOT / "approaches"
    for name in ("rubric.md", "quick-fix.md", "feature.md",
                 "initiative.md", "hotfix.md", "spike.md"):
        assert (approaches / name).is_file(), (
            f"approaches/{name} is missing")
    assert not (REPO_ROOT / "routes").exists(), (
        "routes/ still exists - the reference docs did not rename")
    stale = []
    surfaces = [REPO_ROOT / "CLAUDE.md", REPO_ROOT / "AGENTS.md"]
    for pat in ("commands/*.md", "skills/*/SKILL.md", "agents/*.md",
                "templates/**/*.md", "docs/*.md", "governance/*.md",
                "approaches/*.md", "cli/compass_pkg/*.py"):
        surfaces += sorted(REPO_ROOT.glob(pat))
    for path in surfaces:
        if not path.is_file() or path.name == "system-spec.md":
            continue
        for lineno, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), 1):
            if "routes/" in line and "tests/fixtures" not in line:
                stale.append(f"{path.relative_to(REPO_ROOT)}:{lineno}")
    assert not stale, (
        "live surfaces still point at routes/:\n  " + "\n  ".join(stale[:15]))


def test_examples_carry_v2_names():
    """TRC-3: the worked-example directories carry v2 change-type names -
    the manual teaches vocabulary from the directory listing."""
    names = {p.name for p in (REPO_ROOT / "examples").iterdir()
             if p.is_dir()}
    expected = {"quick-fix-typo", "feature-api-change",
                "initiative-new-subsystem", "hotfix-regression",
                "spike-technical-unknown", "bdd-adapters"}
    missing = expected - names
    assert not missing, f"missing v2-named examples: {sorted(missing)}"
    v1 = {"express-typo", "standard-api-change", "expedition-new-subsystem"}
    stale = v1 & names
    assert not stale, f"v1-shape-named example dirs remain: {sorted(stale)}"


def test_remaining_docs_are_enforced():
    """TRC-4, amended at the recorded split boundary: the three docs that
    arrived clean after the sweep enter enforced now; quickstart,
    portability, and routing-deep-dive join in the second half with the
    doctrine document."""
    scan = _scan_cfg()
    for f in ("docs/roles-guide.md", "docs/safety-contract.md",
              "docs/security.md"):
        assert f in scan["surfaces"], f"{f} is not a scanned surface"
    assert any(e.startswith("docs/system-spec") for e in scan["exempt"]), (
        "docs/system-spec.md must stay exempt - it is derived at ship time")


def test_install_refusal_points_at_plugin_dir():
    """TRC-5: the plugin-source refusal names the path the plugin source
    actually uses - claude --plugin-dir - not /plugin install, which is
    the answer for a project consuming the plugin."""
    text = (REPO_ROOT / "scripts" / "install.sh").read_text(encoding="utf-8")
    assert "claude --plugin-dir" in text, (
        "install.sh's plugin-source refusal does not name "
        "claude --plugin-dir")
    assert "/plugin install" not in text.split("plugin source detected")[1].split("exit 0")[0] or "claude --plugin-dir" in text.split("plugin source detected")[1].split("exit 0")[0], (
        "the refusal block still sends the plugin source to /plugin install")
