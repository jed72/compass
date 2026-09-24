"""The vocabulary scan scans every position unless something says otherwise.

Every position is scanned unless an exemption names the positions it covers
and says why a string there cannot reach a user. A string that gets printed
is prose wherever it lives: a YAML `rationale:` value is printed verbatim by
`compass approach evaluate`; a Python literal is printed by every command; a
fenced block is read by whoever opens the file. Markdown fenced blocks,
Python string literals and YAML values were each excluded from the scan in
turn, and each exclusion turned out wrong for that reason, so the scan now
defaults to scanning rather than to excluding.

Scenario ids: see dry-run-2-rulings/acceptance-criteria.md.
"""
from __future__ import annotations

import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))


def _scan(path):
    import test_terminology as T
    return T._scan_units(path)


def _hits(path):
    import test_terminology as T
    out = []
    for lineno, line in T._scan_units(path):
        for term, patterns in T.BAN_PATTERNS.items():
            if any(p.search(line) for p in patterns):
                out.append((lineno, term))
                break
    return out


# ---------------------------------------------------------------------------
# A YAML value is scanned (TRC-D1)
# ---------------------------------------------------------------------------

def test_trc_d1_yaml_values_are_scanned(tmp_path):
    """`routing-policy.yml`'s `rationale:` values print to the terminal, so
    a YAML value must be scanned."""
    f = tmp_path / "policy.yml"
    f.write_text('rationale: "checked before Land."\n', encoding="utf-8")

    assert _hits(f), (
        "a retired name in a YAML value is not reported. Values on this "
        "surface are printed to users verbatim")


# ---------------------------------------------------------------------------
# Every exemption names its positions and its reason (TRC-D2)
# ---------------------------------------------------------------------------

def test_trc_d2_every_exemption_states_a_reason():
    doc = yaml.safe_load(
        (ROOT / "governance" / "terminology.yml").read_text(encoding="utf-8"))
    exemptions = (doc.get("scan") or {}).get("position_exemptions")

    assert exemptions, (
        "the scan declares no position exemptions. After the inversion an "
        "excluded position must be declared, not left as a silent default")
    for ex in exemptions:
        assert ex.get("id"), f"an exemption has no id: {ex!r}"
        assert ex.get("positions"), (
            f"{ex.get('id')} does not name the positions it covers: {ex!r}")
        reason = str(ex.get("reason") or "")
        assert len(reason) > 40, (
            f"{ex.get('id')} carries no real reason. The reason must say why "
            f"a string in that position cannot reach a user: {reason!r}")


# ---------------------------------------------------------------------------
# The widened scan can fail, and does not fire on the exempt position (TRC-D3)
# ---------------------------------------------------------------------------

def test_trc_d3_the_widened_scan_can_fail(tmp_path):
    """Mutation proof plus its control.

    The first half proves the scan reaches the newly covered position. The
    second is what stops "scan everything" from meaning "report everything":
    a comment is exempt, with a stated reason, and must stay quiet.
    """
    # The real defect string, quoted from routing-policy.yml as it shipped.
    # Not a paraphrase: the prose patterns are capitalisation-scoped on
    # purpose ("changes land" is ordinary English), so a fixture inventing a
    # lowercase machine value would prove the scan reaches the position while
    # testing a pattern that was never meant to fire there.
    value = tmp_path / "value.yml"
    value.write_text(
        'rationale: "Irreversible-surface issues have fitness checked before '
        'Land."\n', encoding="utf-8")
    assert _hits(value), "the scan does not reach a YAML value"

    comment = tmp_path / "comment.yml"
    comment.write_text(
        'key: 1   # this was checked before Land, kept for the record\n',
        encoding="utf-8")
    assert not _hits(comment), (
        "the scan reports a retired name inside a comment. Comments are "
        "exempt by a declared exemption - the parser discards them, so no "
        "string there can reach a user")


def test_trc_d3b_an_unknown_file_type_is_scanned_whole(tmp_path):
    """A file type with no rule is scanned whole, so a new position must be
    excluded on purpose."""
    f = tmp_path / "notes.txt"
    f.write_text("the expedition route was raised\n", encoding="utf-8")
    assert _scan(f), "an unrecognised file type contributes no scanned lines"
