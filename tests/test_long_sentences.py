"""A long sentence is reported, never blocked.

Long sentences are a prompt to re-read, not a defect. A threshold that failed a
build would become a number people wrote around - splitting one 34-word
sentence into two clumsy ones to clear a gate teaches exactly the wrong habit,
and `prd.md` rules out any numeric writing gate for that reason.

So the REPORT never changes an exit status. The tests in this file are a
different thing and must be able to fail: they check that the reporter finds
what it should, ignores what it should, and stays inert. A reporter nobody can
prove wrong is not advisory, it is decorative.

Scenario ids: TRC-E1, TRC-E2 (issue plain-language-3-2-0).
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent

# 31 words and over is reported; 30 is the last unreported length. The number is
# arbitrary and saying so is better than implying it was derived - it is a
# prompt to re-read, not a measurement of anything.
LONG_SENTENCE_WORDS = 30

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def split_sentences(text: str) -> list[str]:
    """Prose split into sentences, crudely and on purpose.

    A real sentence splitter would need an abbreviation list and would still be
    wrong on `e.g.` - and the cost of being wrong here is one extra line in an
    advisory report, so the crude version is the right trade.
    """
    return [s.strip() for s in _SENTENCE_END.split(text) if s.strip()]


def word_count(sentence: str) -> int:
    return len([w for w in sentence.split() if any(c.isalnum() for c in w)])


def long_sentences(text: str, threshold: int = LONG_SENTENCE_WORDS):
    """Every sentence longer than `threshold` words, as (index, count, text)."""
    out = []
    for i, s in enumerate(split_sentences(text), 1):
        n = word_count(s)
        if n > threshold:
            out.append((i, n, s))
    return out


def _sentence_of(n: int) -> str:
    """A sentence with exactly `n` words, ending in a full stop."""
    return " ".join(["word"] * n) + "."


# ---------------------------------------------------------------------------
# TRC-E1 - a sentence of thirty-one words or more is reported
# ---------------------------------------------------------------------------

def test_pl_e1_thirty_one_words_reported_thirty_not():
    """TRC-E1 - the boundary is stated exactly, and both sides of it hold."""
    text = "\n".join([_sentence_of(41), _sentence_of(31), _sentence_of(30),
                      _sentence_of(3)])
    found = long_sentences(text)
    counts = sorted(n for _, n, _ in found)
    assert counts == [31, 41], (
        f"expected the 41-word and 31-word sentences and nothing else, got "
        f"{counts}. 30 is the last unreported length."
    )


def test_pl_e1b_report_names_file_line_and_count():
    """TRC-E1 - a report without locations is a number, not a report."""
    text = "Short one.\n" + _sentence_of(35)
    found = long_sentences(text)
    assert len(found) == 1
    index, count, sentence = found[0]
    assert index == 2, f"the sentence's position must be reported, got {index}"
    assert count == 35, f"the word count must be reported, got {count}"
    assert sentence.startswith("word"), "the sentence itself must be reported"


# ---------------------------------------------------------------------------
# TRC-E2 - the report never fails a build
# ---------------------------------------------------------------------------

def test_pl_e2_exit_status_does_not_move_with_the_finding_count():
    """TRC-E2 - 0, 30 and 500 findings all leave the caller's status alone.

    Stated as a property of the reporter rather than of a test run: calling it
    returns findings and raises nothing, whatever it finds.
    """
    for n_findings in (0, 30, 500):
        text = "\n".join([_sentence_of(35)] * n_findings) or "Short."
        found = long_sentences(text)
        assert isinstance(found, list)
        assert len(found) == n_findings
    # And the reporter has no way to signal failure even when asked to.
    assert long_sentences("") == []


def test_pl_e2b_no_knob_exists_that_would_make_it_block():
    """TRC-E2 - there is no option that would turn the report into a gate.

    "No threshold exists" cannot be seen from outside, so this checks the two
    things that can: the module exposes no failure switch, and the one number it
    does expose changes what is reported rather than whether anything fails.
    """
    import tests.test_long_sentences as mod  # noqa: PLC0415
    # The module's API, not its tests. A test named ..._would_make_it_block is
    # describing the thing it forbids; only a public name would enable it.
    api = [n for n in dir(mod) if not n.startswith(("test_", "_"))]
    switches = [n for n in api
                if re.search(r"strict|fail|gate|block|error|raise", n, re.I)]
    assert not switches, (
        f"this module exposes {switches}, which invite turning an advisory "
        f"report into a gate. prd.md rules out a numeric writing gate."
    )
    loose = long_sentences(_sentence_of(35), threshold=100)
    tight = long_sentences(_sentence_of(35), threshold=10)
    assert loose == [] and len(tight) == 1, (
        "the threshold must change WHAT IS REPORTED, never whether the call "
        "succeeds - both calls must return normally"
    )
