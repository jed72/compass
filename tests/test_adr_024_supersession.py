"""ADR-024 supersedes ADR-019 (issue what-compass-owes-an-unobserved-adopter).

ADR-019 carried redirects because it read publication to the plugin
marketplace as proof that the adopter population "is no longer empty".
Publication is not adoption: with no install telemetry the population is
*unknown*, and ADR-014 before it made the mirror-image error in the other
direction. 4.0.0 does the deleting; this record corrects the inference, so the
first rename inside 4.x does not rebuild the machinery on the same reasoning.

These scenarios check properties of the record and of the decision chain
around it. A scenario like "the reasoning is sound" would be unwritable, so
each one names something a reader could point at.

Scenario ids: TRC-A1..A4, B1..B3, C1..C3, F1..F3 in
.compass/work/what-compass-owes-an-unobserved-adopter/acceptance-criteria.md
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DECISIONS = REPO_ROOT / "architecture" / "decisions"
INDEX = DECISIONS / "README.md"


def _record(adr_id: str) -> Path:
    matches = sorted(DECISIONS.glob(f"{adr_id}-*.md"))
    assert len(matches) == 1, (
        f"expected exactly one {adr_id} record, found {[m.name for m in matches]}")
    return matches[0]


def _frontmatter(path: Path) -> dict:
    """The record's YAML header, read as simple `key: value` lines.

    Parsed by line rather than with a YAML loader: the header is a flat map
    of scalars by convention, and the bundled loader is not on the path for a
    test run. A header that stops being flat should fail here loudly rather
    than be half-read.
    """
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{path.name} has no frontmatter"
    header = text.split("---\n", 2)[1]
    out = {}
    for line in header.splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        assert ":" in line, f"{path.name}: frontmatter line is not `key: value`: {line!r}"
        key, _, value = line.partition(":")
        out[key.strip()] = value.strip().strip("'\"")
    return out


def _body(adr_id: str) -> str:
    return _record(adr_id).read_text(encoding="utf-8")


def _flat(text: str) -> str:
    """Whitespace collapsed, so an assertion is about what the prose says
    rather than where its lines happen to wrap."""
    return " ".join(text.split())


def _section(body: str, name: str) -> str:
    """One `## <name>` section of a record, up to the next `## `."""
    m = re.search(rf"(?m)^## {re.escape(name)}\s*$", body)
    assert m, f"the record has no `## {name}` section"
    rest = body[m.end():]
    nxt = re.search(r"(?m)^## ", rest)
    return rest[:nxt.start()] if nxt else rest


# ---------------------------------------------------------------------------
# Group A - what the decision says
# ---------------------------------------------------------------------------

def test_the_decision_names_an_observable_quantity():
    decision = _flat(_section(_body("ADR-024"), "Decision")).lower()

    assert "adopter" in decision, (
        "the Decision does not name the population the rule turns on")
    assert re.search(r"\b(observe|observed|observation|measure|measured|count|"
                     r"counted)\b", decision), (
        "the Decision names no observation. The whole defect in ADR-019 was "
        "inferring a quantity from a proxy, so a replacement that states no "
        "way of observing it repeats the error in a new place")
    # In one breath with the observation, not merely somewhere in the section:
    # "issue" and "install" both occur in the Decision for unrelated reasons
    # ("issue directory", "installs"), so a section-wide token check passed
    # after the sentence naming the means was deleted.
    assert re.search(r"observed[^.]*?(issue|report|pull request|message)",
                     decision), (
        "the Decision does not say by what means the population would be "
        "observed, so a reader cannot tell whether anyone could perform it")


def test_publication_is_refused_as_evidence_of_adoption():
    body = _flat(_body("ADR-024")).lower()

    assert "publication is not adoption" in body, (
        "the record does not state plainly that publication is not adoption, "
        "which is the single sentence ADR-019 needed and did not have")
    assert "unknown" in body, (
        "the record does not say the population is unknown. 'Empty' and "
        "'non-empty' are both claims; 'unknown' is the honest one")
    # Scoped to the Context and shaped as the claim. A bare "adr-014" is
    # satisfied by the References list at the foot of the record, so it
    # survived deleting the sentence this was written for.
    context = _flat(_section(_body("ADR-024"), "Context")).lower()
    assert re.search(r"adr-014[^.]*(empty|opposite|pre-publication)", context), (
        "the Context does not say ADR-014 made the same error in the opposite "
        "direction. Correcting one half leaves the record contradicting "
        "itself about the other")


def test_the_revival_condition_is_readable_from_the_record_alone():
    body = _flat(_body("ADR-024")).lower()

    # Anchored on the condition itself. `\bif\b|\bonce\b|\bwhen\b` over the
    # whole record was satisfied by any incidental "when" - one neutral
    # sentence elsewhere defeated it.
    assert re.search(r"if the population is observed[^.]*redirect", body), (
        "the record states no revival condition a reader can point at, so "
        "they cannot tell what would bring full migration compatibility back")
    assert "compass migrate" in body, (
        "the record does not say what an adopter can rely on today. The "
        "question this issue asked was what Compass owes them, and an answer "
        "that names nothing concrete has not answered it")


def test_the_record_says_what_it_adds_beyond_the_release():
    body = _flat(_body("ADR-024")).lower()

    assert "4.0.0" in body, (
        "the record does not name the release that carries the removal")

    # Scoped, and stated as a proposition. "inside a major" on its own also
    # occurs in the Decision, where it says a break there stays forbidden -
    # so a bare phrase check passed after this sentence was deleted.
    alts = _flat(_section(_body("ADR-024"), "Alternatives considered")).lower()
    assert re.search(r"what this record adds beyond[^.]*?rule", alts), (
        "the record never says, in one sentence a reviewer can point at, what "
        "it adds beyond scheduling 4.0.0. ADR-019 already authorised removal "
        "at a major version, so a record that only restates that is ceremony")


# ---------------------------------------------------------------------------
# Group B - the record's place in the chain
# ---------------------------------------------------------------------------

def test_the_supersession_is_navigable_in_both_directions():
    new = _frontmatter(_record("ADR-024"))
    old = _frontmatter(_record("ADR-019"))

    assert new.get("supersedes") == "ADR-019", (
        f"ADR-024's `supersedes` is {new.get('supersedes')!r}, not 'ADR-019'")
    assert old.get("superseded_by") == "ADR-024", (
        f"ADR-019's `superseded_by` is {old.get('superseded_by')!r}, not "
        f"'ADR-024'. A chain navigable in one direction only is how a reader "
        f"lands on a superseded record and acts on it")
    assert old.get("status") == "superseded", (
        f"ADR-019's status is {old.get('status')!r} - a record with a "
        f"`superseded_by` still reading `accepted` says two things at once")


def test_every_link_in_the_decisions_index_resolves():
    body = INDEX.read_text(encoding="utf-8")
    links = re.findall(r"\[([^\]]+)\]\((ADR-[^)]+\.md)\)", body)
    # A floor, because `broken` is empty both when every link resolves and
    # when the reader matched nothing at all - a change of link style would
    # otherwise pass this over an empty list.
    assert len(links) >= 15, (
        f"only {len(links)} ADR links were read from the index, which has far "
        f"more - the link pattern has stopped matching and this check is "
        f"passing over almost nothing")
    broken = []
    for _, target in links:
        if not (DECISIONS / target).is_file():
            broken.append(target)
    assert not broken, (
        "the decisions index links to record(s) that do not exist: "
        + ", ".join(sorted(set(broken))))

    assert "ADR-024" in body, (
        "ADR-024 has no row in architecture/decisions/README.md, so it is "
        "invisible to anyone reading the index rather than the directory")


def test_inv_8_resolves_to_a_record_that_is_not_superseded():
    index = INDEX.read_text(encoding="utf-8")
    citing = [line for line in index.splitlines() if "Inv-8" in line]
    assert citing, "no record in the index cites Inv-8, so this checks nothing"

    # Inv-8 is defined on ADR-006. If that record were ever superseded, every
    # citation above would resolve to a decision that no longer holds.
    home = _frontmatter(_record("ADR-006"))
    assert not home.get("superseded_by"), (
        f"ADR-006 defines Inv-8 and is superseded by "
        f"{home.get('superseded_by')!r}. {len(citing)} record(s) cite Inv-8 "
        f"and would now point at a decision that no longer stands")


# ---------------------------------------------------------------------------
# Group C - what must not change
# ---------------------------------------------------------------------------

def test_adr_006_is_not_superseded():
    front = _frontmatter(_record("ADR-006"))
    assert not front.get("superseded_by"), (
        "ADR-006 states the principle - backward compatibility is "
        "non-negotiable within a major version. ADR-019 was the "
        "interpretation that cost, and it is the interpretation this "
        "supersedes")

    body = _flat(_body("ADR-024")).lower()
    assert "adr-006" in body, (
        "the record does not mention ADR-006, so a reader cannot tell whether "
        "the principle survived the correction")


def test_inv_8_s_two_promises_are_stated_separately():
    body = _flat(_body("ADR-024"))
    lower = body.lower()

    assert "inv-8" in lower, "the record never addresses Inv-8"
    assert re.search(r"no-op|does nothing|not adopted|absent prerequisite",
                     lower), (
        "the record does not carry forward Inv-8's no-op promise - that a new "
        "mechanism does nothing to a project which has not adopted it")
    # "two promises" alone also occurs where the record describes ADR-019's
    # framing, so the loose alternation passed after both sentences asserting
    # the difference were deleted. Require the assertion itself.
    assert re.search(r"not the same claim", lower) and re.search(
            r"two different claims", lower), (
        "the record does not say the no-op promise and migration "
        "compatibility are different claims. ADR-019's framing ran them "
        "together, which is how one was used to justify the other")


def test_the_archive_rule_is_untouched():
    front = _frontmatter(_record("ADR-020"))
    assert not front.get("superseded_by"), (
        "ADR-020 says the archive is migrated, not frozen. Nothing in this "
        "issue changes that")

    decision = _flat(_section(_body("ADR-024"), "Decision")).lower()
    assert re.search(r"adr-020[^.]*(requir|because|reason)|"
                     r"(requir|because|reason)[^.]*adr-020", decision), (
        "the Decision does not cite ADR-020 as the reason the read-side "
        "rename tables stay. Without it the next reader supplies the wrong "
        "reason - the adopter promise - which is the inference this record "
        "corrects. (Naming ADR-020 elsewhere in the record does not do this: "
        "the reason has to sit with the decision it explains.)")


# ---------------------------------------------------------------------------
# Failure modes
# ---------------------------------------------------------------------------

def test_a_record_that_only_restates_the_existing_schedule_is_refused():
    alternatives = _flat(_section(_body("ADR-024"), "Alternatives considered"))
    lower = alternatives.lower()

    assert "4.0.0" in lower or "schedule" in lower, (
        "the Alternatives section does not consider simply cutting the "
        "release and writing nothing, which is the cheapest option and the "
        "one this record has to beat")
    # Not any of several near-synonyms scattered through the section: the
    # rejection has to name the thing the release cannot touch, which is
    # ADR-019's rule. A bare "future rename" matched the sentence next door.
    assert re.search(r"rule for renames", lower), (
        "the Alternatives section rejects the release-only option without "
        "saying what it fails to do. The answer is that it leaves ADR-019's "
        "rule for renames inside a major version standing")


def test_a_revival_condition_nobody_can_observe_is_refused():
    body = _flat(_body("ADR-024")).lower()

    assert "telemetry" in body, (
        "the record does not address install telemetry. The obvious way to "
        "count adopters does not exist here, and a record that names an "
        "observation without saying so leaves the reader to find out")
    # Both halves, in one sentence: the observation is absent, AND which kind
    # of absent it is. Checked together because either alone reads as covered
    # while the reader still cannot tell whether anyone could perform it.
    assert re.search(r"unperformed, not impossible|not impossible[^.]*"
                     r"unperformed", body), (
        "the record does not say which kind of absence this is. An "
        "observation nobody performs because nothing collects it can be "
        "built; one that is impossible cannot, and a reader deciding whether "
        "to revisit this needs to know which")


def test_orphaning_inv_8_fails_the_change():
    """The mechanical half: every ADR citing Inv-8 resolves to a live record.

    The scenario is written about re-homing Inv-8, which this change does not
    do. Checked anyway, because the failure it describes is silent - a
    citation to a superseded record reads exactly like a citation to a live
    one.
    """
    index = INDEX.read_text(encoding="utf-8")
    citing = []
    for line in index.splitlines():
        if "Inv-8" not in line:
            continue
        m = re.search(r"\[(ADR-\d+)\]", line)
        if m:
            citing.append(m.group(1))
    assert len(citing) >= 2, (
        f"only {len(citing)} record(s) found citing Inv-8 in the index - the "
        f"reader above has stopped matching the table, and this check is "
        f"passing over almost nothing")

    dangling = []
    for adr in citing:
        front = _frontmatter(_record(adr))
        # A record may itself be superseded; what must not happen is the
        # record DEFINING Inv-8 going away under it.
        if front.get("superseded_by") and adr == "ADR-006":
            dangling.append(adr)
    assert not dangling, (
        f"Inv-8's defining record is superseded, so these citations dangle: "
        f"{', '.join(dangling)}")
