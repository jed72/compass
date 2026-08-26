"""The fresh-eyes practice becomes a standing strategy (issue fresh-eyes-verify-sweeps).

The maintainer's instruction: after a sweep, rename, or cleanup that touches
many files, verification is done by a fresh agent that has not seen the
change - not by the one that made it. The author of a sweep checks their own
work against a mental list of what they changed, not against the goal, so
the files they forgot are exactly the files they do not think to look for.
Two cleanups leaked in this repository's own history, both reported complete
by the agent that made them - that is the evidence this strategy exists to
act on.

This file pins the strategy entry in `governance/strategies.md` and the
pointer from the verify stage guidance (`commands/verify.md`,
`skills/evidence-gates/SKILL.md`) that names where it lives without
repeating it.

Criteria: docs/system-spec.md
(Requirements review and design collapsed on this quick fix - see
`.compass/work/fresh-eyes-verify-sweeps/delivery-approach.md` §5.)
"""

# The vocabulary rename landed on 2026-08-25: the assess and plan stages took
# the names their machine keys, skills and agents already used; `design` went
# back to the designer; design.md became technical-design.md and prd.md became
# intent.md. Spines and documents written before still load and resolve
# (ADR-006), so what moved is the CANONICAL spelling these tests assert - not
# what the framework computes. Re-pointed, not relaxed.
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent

STRATEGIES = REPO_ROOT / "governance" / "strategies.md"
VERIFY_CMD = REPO_ROOT / "commands" / "verify.md"
EVIDENCE_GATES = REPO_ROOT / "skills" / "evidence-gates" / "SKILL.md"


def _flat(text: str) -> str:
    """Collapse every run of whitespace to one space.

    Phrase assertions here are about what the prose says, not about where
    its lines happen to wrap - `tests/test_voice_audition_standing.py`
    already learned this the hard way, so the fix is reused rather than
    re-broken.
    """
    return " ".join(text.split())


def _strategies_text() -> str:
    assert STRATEGIES.is_file(), "governance/strategies.md must exist"
    return STRATEGIES.read_text(encoding="utf-8")


def _strategy_entry() -> str:
    """The new strategy's own section, isolated from the rest of the file.

    Found by its heading naming "fresh eyes" rather than by body text, so a
    coincidental match elsewhere in the file cannot grab the wrong section.
    """
    text = _strategies_text()
    sections = re.split(r"(?m)^### ", text)
    for section in sections[1:]:
        heading = section.split("\n", 1)[0]
        if "fresh eyes" in heading.lower():
            return "### " + section
    return ""


# ---------------------------------------------------------------------------
# TRC-A1 - the strategy states the trigger, the staffing rule, and the method
# ---------------------------------------------------------------------------

def test_trc_a1_strategy_states_trigger_staffing_rule_and_method():
    entry = _strategy_entry()
    assert entry, (
        "no strategy entry in governance/strategies.md names the fresh-eyes "
        "sweep-verification practice"
    )
    flat = _flat(entry)
    flat_lower = flat.lower()

    assert re.search(r"\bS\d+\b", entry.split("\n", 1)[0]), (
        "the strategy heading must carry an S-number, matching the file's "
        "existing numbering convention"
    )

    # The trigger: a sweep, rename, or cleanup across many files.
    assert "sweep" in flat_lower, "the strategy must name a sweep as a trigger"
    assert "rename" in flat_lower, "the strategy must name a rename as a trigger"
    assert "cleanup" in flat_lower, "the strategy must name a cleanup as a trigger"
    assert "many files" in flat_lower, (
        "the strategy must say the trigger is a change that touches many files"
    )

    # The staffing rule: a fresh agent that has not seen the changes.
    assert "fresh agent" in flat_lower, (
        "the strategy must state the staffing rule: a fresh agent verifies"
    )
    assert "has not seen" in flat_lower, (
        "the strategy must say the fresh agent has not seen the change"
    )

    # The method: given only the goal, greps independently, file:line residuals.
    assert "goal" in flat_lower, (
        "the strategy must say the fresh agent is given only the goal"
    )
    assert "greps" in flat_lower or "grep" in flat_lower, (
        "the strategy must say the fresh agent greps independently"
    )
    assert "independently" in flat_lower, (
        "the strategy must say the grep is independent, not guided by the author"
    )
    assert "residuals" in flat_lower, (
        "the strategy must say the fresh agent reports residuals"
    )
    assert "file and line" in flat_lower or "file:line" in flat_lower, (
        "the strategy must say residuals are reported with file and line"
    )


# ---------------------------------------------------------------------------
# TRC-A2 - the strategy states the prohibition, the evidence, and carries
# the file's own "Why a strategy" / "Cross-reference" conventions.
# ---------------------------------------------------------------------------

def test_trc_a2_strategy_states_prohibition_evidence_and_cross_references_s8():
    entry = _strategy_entry()
    assert entry, "TRC-A1 must land before this scenario can"
    flat = _flat(entry)
    flat_lower = flat.lower()

    # The prohibition: does not read or trust the implementer's summary.
    assert "does not read" in flat_lower or "not read" in flat_lower, (
        "the strategy must say the fresh agent does not read the implementer's summary"
    )
    assert "does not trust" in flat_lower or "not trust" in flat_lower, (
        "the strategy must say the fresh agent does not trust the implementer's summary"
    )
    assert "summary" in flat_lower, (
        "the strategy must name the implementer's summary as the thing not trusted"
    )

    # The evidence: two leaked cleanups here, both reported complete by their author.
    assert "two" in flat_lower and "leak" in flat_lower, (
        "the strategy must name two leaked cleanups as its evidence"
    )
    assert "reported complete" in flat_lower or "reported it complete" in flat_lower, (
        "the strategy must say both leaks were reported complete by the agent that made them"
    )

    # The file's own conventions.
    assert "*Why a strategy and not a guardrail:*" in entry, (
        "the entry must carry the file's own 'Why a strategy and not a "
        "guardrail' convention"
    )
    assert "*Cross-reference:" in entry, (
        "the entry must carry the file's own cross-reference convention"
    )
    assert "`S8`" in entry, (
        "the entry must cross-reference S8 (the voice audition) as the "
        "sibling practice about who judges"
    )


# ---------------------------------------------------------------------------
# TRC-B1 - the verify stage guidance points at the strategy, not repeat it
# ---------------------------------------------------------------------------

def test_trc_b1_verify_guidance_points_at_the_strategy_not_repeat_it():
    verify_cmd = VERIFY_CMD.read_text(encoding="utf-8")
    gates = EVIDENCE_GATES.read_text(encoding="utf-8")

    strategy_heading = _strategy_entry().split("\n", 1)[0].strip()
    match = re.search(r"`(S\d+)`", strategy_heading)
    assert match, "TRC-A1 must land before this scenario can"
    s_number = match.group(1)

    for name, text in (("commands/verify.md", verify_cmd),
                        ("skills/evidence-gates/SKILL.md", gates)):
        assert "governance/strategies.md" in text, (
            f"{name} must point at governance/strategies.md"
        )
        assert s_number in text, (
            f"{name} must name the strategy's own number ({s_number}) so a "
            f"reader can find it without already knowing it exists"
        )
        flat_lower = _flat(text).lower()
        assert "sweep" in flat_lower, (
            f"{name} must mention the sweep trigger, so the pointer is findable"
        )
        # A pointer, not a restatement: neither surface should repeat the
        # strategy's own prohibition or evidence sentences in full.
        assert "reported complete" not in text.lower(), (
            f"{name} must not repeat the strategy's own evidence sentence"
        )
        assert "does not read" not in text.lower(), (
            f"{name} must not repeat the strategy's own prohibition sentence"
        )


# ---------------------------------------------------------------------------
# TRC-C1 - the amendment states the primary-record rule and defines what a
# primary record is (issue s9-primary-record)
# ---------------------------------------------------------------------------

def test_trc_c1_strategy_states_primary_record_rule_and_definition():
    entry = _strategy_entry()
    assert entry, "TRC-A1 must land before this scenario can"
    flat = _flat(entry)
    flat_lower = flat.lower()

    # The rule: verify against the primary record, not the nearest mention.
    assert "primary record" in flat_lower, (
        "the strategy must name 'primary record' as the thing verified against"
    )
    assert "nearest document" in flat_lower, (
        "the strategy must contrast the primary record with the nearest "
        "document that mentions the claim"
    )

    # The definition: what makes a record "primary" for a given claim.
    assert "would be wrong if the claim were false" in flat_lower, (
        "the strategy must define a primary record as the artifact that "
        "would be wrong if the claim were false"
    )

    # The named examples: a PR's file list, a commit, the code.
    assert "pull request" in flat_lower and "file list" in flat_lower, (
        "the strategy must name a pull request's file list as the primary "
        "record for what a change touched"
    )
    assert "commit" in flat_lower, (
        "the strategy must name a commit as the primary record for what a "
        "commit says"
    )
    assert "the code for what the code does" in flat_lower, (
        "the strategy must name the code as the primary record for what "
        "the code does"
    )


# ---------------------------------------------------------------------------
# TRC-C2 - the amendment carries the ADR-013 worked example and warns that
# the nearest document is often a summary (issue s9-primary-record)
# ---------------------------------------------------------------------------

def test_trc_c2_strategy_carries_adr_013_worked_example_and_summary_caution():
    entry = _strategy_entry()
    assert entry, "TRC-A1 must land before this scenario can"
    flat = _flat(entry)
    flat_lower = flat.lower()

    # The caution: the nearest document is often a summary of the fact,
    # one step removed from the thing itself.
    assert "often a summary" in flat_lower, (
        "the strategy must say the nearest document that mentions a fact "
        "is often a summary of it"
    )

    # The worked example: ADR-013's Context, checked against technical-design.md
    # (the nearest document) rather than a primary record that does not
    # exist because the claimed event never happened.
    assert "adr-013" in flat_lower, (
        "the strategy must name ADR-013 as the worked example"
    )
    assert "timing figure" in flat_lower, (
        "the strategy must say ADR-013's Context carried a timing figure - "
        "concrete about what was wrong, without reproducing the exact "
        "flagged phrase tests/test_public_copy_claims.py scans public copy "
        "for, which this file is not exempt from"
    )
    assert "technical-design.md" in flat_lower, (
        "the strategy must name technical-design.md as the nearest document ADR-013 "
        "was checked against"
    )
    assert "did not happen" in flat_lower, (
        "the strategy must say the claimed event did not happen, which is "
        "why no primary record for it exists"
    )


# ---------------------------------------------------------------------------
# TRC-F1 - no new mechanism (no natural red - see acceptance-criteria.md's
# note; recorded via `compass acceptance start` / `record`)
# ---------------------------------------------------------------------------

def test_trc_f1_no_new_gate_guardrail_check_cli_verb_or_vocabulary():
    import subprocess
    import sys

    import yaml

    guardrails = yaml.safe_load(
        (REPO_ROOT / "governance" / "guardrails.yml").read_text(encoding="utf-8")
    )
    assert len(guardrails["defaults"]) == 5

    terminology = yaml.safe_load(
        (REPO_ROOT / "governance" / "terminology.yml").read_text(encoding="utf-8")
    )
    # The count is a ratchet against a sweep quietly widening the vocabulary,
    # not a ban on ever defining a word. Raising it is the deliberate act that
    # says a vocabulary change was intended - the same shape as
    # EXPECTED_VERSION in test_version_consistency.
    #
    # 53 -> 57 at 3.0.0: traceability, intent, navigator and assessment. Each
    # named something already load-bearing and undefined - the most-used id
    # prefix in the repository, a live command, a live agent, and the only
    # judgement field in the spine. ADR-016 records the decision.
    #
    # 58 -> 57 on 2026-08-25, the vocabulary rename. `triage` was renamed to
    # `assess` (net zero) and `prd` was DROPPED: both were defined as live
    # vocabulary while the same file banned them, so the generated glossary
    # published two retired words as current. What `prd` described - the
    # intake document - is what the `intent` entry describes, which is why it
    # is one entry fewer rather than a replacement.
    #
    # 57 -> 59 on 2026-08-25: `design` and `plan`. `design` is the word this
    # whole rename existed for - it named a command, an artifact, an artifact
    # kind, a CLI verb and a role, and was the only overloaded word here with
    # no entry, which is how it stayed ambiguous. `plan` took the engineering
    # half. TRC-A3 requires both.
    assert len(terminology["terms"]) == 59, (
        "governance/terminology.yml gained or lost a term without this count "
        "moving. A vocabulary change is a decision (ADR-012); make it one."
    )

    result = subprocess.run(
        [sys.executable, "cli/compass", "--help"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True,
    )
    known_verbs = {
        "approach", "bdd", "check", "analyze", "retro", "ci", "tdd-red",
        # `plan` is the planning verb again. `design` still works but is
        # hidden from `--help`, so it is not in the advertised set.
        # `intent` added 2026-08-25 - `compass intent ingest`.
        "tdd-green", "policy", "plan", "intent", "issue", "acceptance", "adr",
        "rework-scan", "flow", "next", "follow-up", "ship-commit", "gate",
        "scenario", "changed-file", "evidence", "migrate", "terminology",
        # `init` added 2026-08-26 - see tests/test_phase2_invariants.py for
        # why it is a verb rather than a subcommand.
        "init",
    }
    line = next(l for l in result.stdout.splitlines() if l.strip().startswith("{"))
    verbs = set(line.strip().strip("{}").split(","))
    assert verbs == known_verbs, (
        f"cli/compass gained or lost a top-level verb: {verbs ^ known_verbs}"
    )

    # The reviewer's governance dimension stays the home for this - no new
    # gate id is introduced anywhere the pointer lives.
    gates = EVIDENCE_GATES.read_text(encoding="utf-8")
    assert "**governance**" in gates, (
        "the governance dimension (where this is assessed) must still exist "
        "in skills/evidence-gates/SKILL.md"
    )
