#!/usr/bin/env python3
# =============================================================================
# scripts/verify-archive-quotes.py - catch a fabricated archive quote even
# where the archive itself cannot be checked.
# =============================================================================
# skills/compass-runtime/writing-voice.md quotes the real project archive
# verbatim, citing the archive path for every pair, and invites a reader to
# check each quote against that path. But the archive lives under
# .compass/work/, which is permanently gitignored (along with docs/proposals/
# and docs/analysis/) - so continuous integration never has it, and a naive
# check that compares a quote against its cited file has nothing to compare
# against there. Silently skipping in that case (the original design) means
# a fabricated or altered quote passes the build every time continuous
# integration runs it - the one place the check actually needs to hold.
#
# This script closes that gap in two parts:
#
#   1. A committed manifest (skills/compass-runtime/archive-quote-manifest.json)
#      records, per quoted span, its source path and a sha256 of the exact
#      quoted text - a fingerprint, not a copy of the text. verify() always
#      checks a span's live text against its manifest hash, in every
#      environment, archive or no archive. A changed hash is a hard failure:
#      this is what catches drift after the archive was last checked,
#      without needing the archive itself.
#   2. Where the archive IS present, verify() also compares the quote
#      directly against the real file - the strongest check there is, and
#      the one the manifest can never fully replace (S9: verify against the
#      primary record, not the nearest thing that mentions it). A mismatch
#      there is also a hard failure, never a skip.
#
# The only case that is not a hard failure is a hash that still matches with
# no file to check it against directly - the manifest has confirmed the
# quote is unchanged since someone with the archive last verified it, but
# this run could not re-confirm that itself. That case is returned as
# `unverified`, named by span id, so a caller (a pytest test, typically)
# can report it loudly rather than pass in silence.
#
# USAGE
#   scripts/verify-archive-quotes.py            verify every quoted span in
#                                                the real writing-voice.md
#                                                against the real manifest;
#                                                exit 1 on any failure.
#   scripts/verify-archive-quotes.py --update    regenerate the manifest from
#                                                the real archive. Refuses -
#                                                and writes nothing - if any
#                                                span's quoted text is not
#                                                verbatim in its cited file,
#                                                because a hash recorded
#                                                without checking the real
#                                                file first is exactly the
#                                                hand-edit this manifest
#                                                exists to rule out. Only
#                                                works on a machine where
#                                                .compass/work/ is checked
#                                                out.
# =============================================================================
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REFERENCE = REPO_ROOT / "skills" / "compass-runtime" / "writing-voice.md"
MANIFEST = REPO_ROOT / "skills" / "compass-runtime" / "archive-quote-manifest.json"

# The two literal spans test_trc_c2 in tests/test_human_voice.py checks:
# that the worked example's rewrite left the original file it rewrote
# untouched. These are not "### Pair N" blocks in writing-voice.md - they
# are fixed strings the test already asserts against the original file
# directly - so they are named here rather than parsed from anywhere.
WORKED_EXAMPLE_SOURCE = ".compass/work/make-receipt-render/requirements-review.md"
WORKED_EXAMPLE_SPANS = [
    {
        "id": "worked-example-original-heading",
        "source": WORKED_EXAMPLE_SOURCE,
        "quoted": "# Clarifications",
        "mode": "first-line-prefix",
    },
    {
        "id": "worked-example-original-decided-by",
        "source": WORKED_EXAMPLE_SOURCE,
        # The retired name below is what the archived file actually says.
        # Rewriting it would have this script verify a sentence nobody wrote,
        # which is the failure the whole guard exists to catch.
        "quoted": "**Decided by:** James (engineer) via Clarify reasoning",
        "mode": "substring",
    },
]
WORKED_EXAMPLE_SPAN_IDS = [s["id"] for s in WORKED_EXAMPLE_SPANS]

_README_LINES = [
    "Hash manifest for archive-quote-verification. DO NOT hand-edit this",
    "file. A hash typed in by hand - rather than computed from the real",
    "archive file - defeats the one thing this file proves: that a quoted",
    "passage still matches what it hashed to the last time someone with the",
    "archive checked it. Regenerate it with:",
    "",
    "    python3 scripts/verify-archive-quotes.py --update",
    "",
    "which only works on a machine where .compass/work/ is checked out (the",
    "archive is gitignored there permanently), and refuses to record a hash",
    "for any span it cannot find, verbatim, in the file it cites.",
    "",
    "What this proves: the quoted span still hashes to the value below, so",
    "any edit to the quote after the last --update run is caught, even",
    "where the archive is absent (as it always is in continuous",
    "integration). It does NOT prove the quote was ever real - only",
    "--update, run against the real file, showed that.",
]


def _reference_text() -> str:
    return REFERENCE.read_text(encoding="utf-8")


_PAIR_HEADING_RE = re.compile(r"(?m)^### Pair (\d+).*$")


def _unquote_blockquote(quoted: str) -> str:
    lines = []
    for line in quoted.strip("\n").splitlines():
        lines.append(line[2:] if line.startswith("> ") else line)
    return "\n".join(lines)


def parse_pairs(text: str) -> list[dict]:
    """Every '### Pair N' block in writing-voice.md, as a list of
    {id, source, before, after, what_changed}.

    The one parser both this script and tests/test_human_voice.py use, so
    the two halves of quote verification - what the reference states and
    what gets hashed - can never disagree about what a pair's Source: and
    Before: lines say.
    """
    headings = list(_PAIR_HEADING_RE.finditer(text))
    pairs = []
    for i, match in enumerate(headings):
        start = match.end()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
        block = text[start:end]
        source_m = re.search(r"Source:\s*`([^`]+)`", block)
        before_m = re.search(r"Before:\s*\n+((?:> .*\n?)+)", block)
        after_m = re.search(r"After:\s*\n+((?:> .*\n?)+)", block)
        what_m = re.search(r"What changed:\s*(.+)", block)
        pairs.append({
            "id": f"pair-{match.group(1)}",
            "source": source_m.group(1) if source_m else None,
            "before": _unquote_blockquote(before_m.group(1)) if before_m else None,
            "after": _unquote_blockquote(after_m.group(1)) if after_m else None,
            "what_changed": what_m.group(1).strip() if what_m else None,
        })
    return pairs


def pair_span_ids(reference_text: str | None = None) -> list[str]:
    text = reference_text if reference_text is not None else _reference_text()
    return [p["id"] for p in parse_pairs(text)]


def current_spans(reference_text: str | None = None) -> list[dict]:
    """Every quoted span this script knows how to check: one per
    '### Pair N' block in the given reference text, plus - only when no
    override is given, i.e. this is the real writing-voice.md - the two
    fixed worked-example spans above. Those two are not parsed from any
    reference text (there is nothing to parse them from); they name real
    repository paths, so a fixture reference used to test the pair-parsing
    path in isolation must not pick them up too.
    """
    spans = [
        {"id": p["id"], "source": p["source"], "quoted": p["before"], "mode": "substring"}
        for p in parse_pairs(reference_text if reference_text is not None else _reference_text())
    ]
    if reference_text is None:
        spans.extend(WORKED_EXAMPLE_SPANS)
    return spans


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_manifest(manifest_path: Path | None = None) -> dict:
    """{span id: {"source": ..., "sha256": ...}}, read from the manifest
    file. An absent file reads as an empty manifest - every span then fails
    with "no manifest entry", which is the honest outcome: nothing has ever
    verified it."""
    path = manifest_path if manifest_path is not None else MANIFEST
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {entry["id"]: entry for entry in data.get("entries", [])}


def _matches_archive(mode: str, quoted: str, archive_text: str) -> bool:
    if mode == "first-line-prefix":
        first_line = archive_text.splitlines()[0] if archive_text else ""
        return first_line.startswith(quoted)
    return quoted in archive_text


def verify(
    archive_root: Path = REPO_ROOT,
    span_ids: list[str] | None = None,
    reference_text: str | None = None,
    manifest: dict | None = None,
) -> tuple[list[str], list[str]]:
    """Verify every current quoted span (or only those in `span_ids`)
    against the manifest, and against the real archive file where present.

    Returns (failures, unverified):
      failures    human-readable strings, each naming the span and exactly
                  what did not match. Any failure is a hard failure - the
                  caller should not treat it as a pass.
      unverified  span ids that matched their manifest hash but could not
                  be checked directly, because the archive file is not
                  present at `archive_root`. Not a failure - the manifest
                  is what confirmed these; name them so a caller can say so.
    """
    manifest = manifest if manifest is not None else load_manifest()
    spans = current_spans(reference_text)
    if span_ids is not None:
        spans = [s for s in spans if s["id"] in span_ids]

    failures: list[str] = []
    unverified: list[str] = []

    for span in spans:
        entry = manifest.get(span["id"])
        if entry is None:
            failures.append(
                f"{span['id']}: no manifest entry - run "
                f"scripts/verify-archive-quotes.py --update with the "
                f"archive present"
            )
            continue
        if entry.get("source") != span["source"]:
            failures.append(
                f"{span['id']}: manifest source {entry.get('source')!r} "
                f"does not match the reference's current Source: "
                f"{span['source']!r}"
            )
            continue

        # A span whose quoted block did not parse has no text to verify.
        # Coercing it to "" made the hash the hash of nothing and the
        # substring check without checking anything true, so an unreadable quote reported
        # clean - in the one script whose job is proving quotes are real.
        if not span.get("quoted"):
            failures.append(
                f"{span['id']}: the reference's Before: block did not parse, "
                f"so there is no quoted text to verify. A blockquote line "
                f"must begin '> '. Fix the reference; a quote that cannot be "
                f"read is not a quote that is fine."
            )
            continue

        computed = sha256_text(span["quoted"])
        if computed != entry.get("sha256"):
            failures.append(
                f"{span['id']}: the quoted text no longer matches the "
                f"manifest's recorded hash for {span['source']} - it was "
                f"edited or fabricated after it was last verified against "
                f"the real file. If this edit is legitimate, re-verify it "
                f"and regenerate the manifest: "
                f"scripts/verify-archive-quotes.py --update"
            )
            continue

        cited = archive_root / span["source"]
        if not cited.is_file():
            unverified.append(span["id"])
            continue

        archive_text = cited.read_text(encoding="utf-8")
        if not _matches_archive(span["mode"], span["quoted"], archive_text):
            failures.append(
                f"{span['id']}: the quoted text is not present in "
                f"{span['source']} as cited - the manifest hash matched, "
                f"but the archive file itself does not contain it"
            )

    return failures, unverified


def update_manifest(
    archive_root: Path = REPO_ROOT,
    reference_text: str | None = None,
    manifest_path: Path | None = None,
    span_ids: list[str] | None = None,
) -> list[dict]:
    """Recompute every span's hash directly from the real archive file and
    write the manifest. Refuses - and writes nothing at all - if any span's
    archive file is missing or does not contain the quoted text verbatim:
    recording a hash without checking the real file first is exactly the
    hand-edit this manifest exists to rule out.

    Returns the written entries on success. Raises SystemExit(1) and
    leaves any existing manifest file untouched otherwise.
    """
    path = manifest_path if manifest_path is not None else MANIFEST
    spans = current_spans(reference_text)
    if span_ids is not None:
        spans = [s for s in spans if s["id"] in span_ids]

    entries = []
    problems = []
    for span in spans:
        # Same rule as verify(): a span that did not parse has no text to
        # record a hash for. Coercing it to "" wrote sha256("") into the
        # manifest against a file the quote was never matched in, which is
        # precisely the hand-edit this manifest exists to rule out.
        if not span.get("quoted"):
            problems.append(
                f"{span['id']}: the reference's Before: block did not parse, "
                f"so there is nothing to record a hash for. A blockquote "
                f"line must begin '> '."
            )
            continue
        if not span.get("source"):
            problems.append(
                f"{span['id']}: the reference names no Source: path, so "
                f"there is no file to verify the quote against."
            )
            continue
        cited = archive_root / span["source"]
        if not cited.is_file():
            problems.append(f"{span['id']}: archive file not found: {span['source']}")
            continue
        archive_text = cited.read_text(encoding="utf-8")
        if not _matches_archive(span["mode"], span["quoted"] or "", archive_text):
            problems.append(
                f"{span['id']}: quoted text is not present in "
                f"{span['source']} - fix the reference before updating "
                f"the manifest"
            )
            continue
        entries.append({
            "id": span["id"],
            "source": span["source"],
            "sha256": sha256_text(span["quoted"]),
        })

    if problems:
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        raise SystemExit(
            "verify-archive-quotes --update: refusing to write a manifest "
            "that would record a hash for a span the archive could not "
            "verify - see the problem(s) above"
        )

    path.write_text(
        json.dumps({"_readme": _README_LINES, "version": 1, "entries": entries}, indent=2)
        + "\n",
        encoding="utf-8",
    )
    return entries


def main(argv: list[str]) -> int:
    if argv and argv[0] == "--update":
        entries = update_manifest()
        print(f"updated {MANIFEST.relative_to(REPO_ROOT)} - {len(entries)} span(s)")
        return 0

    failures, unverified = verify()

    if failures:
        print(f"archive quote verification: {len(failures)} failure(s)")
        for failure in failures:
            print(f"  {failure}")
        return 1

    if unverified:
        print(
            f"archive quote verification: {len(unverified)} span(s) could "
            f"not be checked directly - the archive is not present on this "
            f"machine (expected in continuous integration: .compass/work/ "
            f"is gitignored there permanently). The hash manifest already "
            f"confirmed each is unchanged since it was last checked "
            f"against the real file:"
        )
        for span_id in unverified:
            print(f"  {span_id}")
    else:
        print(
            "archive quote verification: every quoted span checked "
            "directly against the real archive - clean"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
