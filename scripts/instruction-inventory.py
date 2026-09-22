#!/usr/bin/env python3
"""Maps every sentence of a rewritten instruction file at the merge base to a
sentence in the rewrite, or to a row saying which sentence absorbed it.

`skills/`, `agents/`, `commands/` and `templates/` are what every adopter's
session reads, so a clearer sentence that says something different changes
what those sessions do. This command checks completeness only - every
merge-base sentence has a mapped row or an absorbed-into row - and leaves
whether the meaning held to a person reading its output; `PBW-F7` is explicit
that the exit code means exactly this one thing, not that nothing changed.

An absorbed-into row is a declaration, not a discovery: the author marks it
with `<!-- absorbed: "the exact merge-base sentence" -->` in the rewritten
file, one per line, wherever it reads naturally. The tool cannot judge that
the marked sentence's meaning really survived - only a reader can - so an
absorbed-into row is recorded exactly as declared.
"""
from __future__ import annotations

import argparse
import difflib
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INSTRUCTION_DIRS = ("skills/", "agents/", "commands/", "templates/")

_FENCE_RE = re.compile(r"^(`{3,}|~{3,})")
_HEADING_RE = re.compile(r"^#{1,6}\s+.+$")
_TABLE_ROW_RE = re.compile(r"^\s*\|.*\|\s*$")
_ABSORBED_RE = re.compile(r'<!--\s*absorbed:\s*"((?:[^"\\]|\\.)*)"\s*-->')

# The leading-verb whitelist that marks an imperative sentence when "must",
# "can" or "do not" is absent - the shape the design calls "telling the
# reader to do something, not do something, or be able to do something".
_IMPERATIVE_VERBS = (
    "run", "write", "read", "use", "check", "add", "remove", "keep", "load",
    "say", "do", "avoid", "never", "always", "call", "return", "name",
    "state", "record", "give", "make", "put", "set", "stop", "start",
)


def _git(args: list[str], cwd: Path) -> str:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True,
                           text=True, check=True).stdout


def _merge_base(cwd: Path) -> str:
    try:
        return _git(["merge-base", "HEAD", "origin/main"], cwd).strip()
    except subprocess.CalledProcessError:
        return _git(["rev-parse", "HEAD~1"], cwd).strip()


def _show(cwd: Path, rev: str, path: str) -> str | None:
    result = subprocess.run(["git", "show", f"{rev}:{path}"], cwd=cwd,
                             capture_output=True, text=True)
    if result.returncode != 0:
        return None
    return result.stdout


def _changed_instruction_files(cwd: Path, base: str) -> list[str]:
    out = _git(["diff", "--name-only", "--diff-filter=ACMR", f"{base}...HEAD"], cwd)
    return [line for line in out.splitlines()
            if line and line.startswith(INSTRUCTION_DIRS)
            and line.endswith(".md")]


def _blank_fences(text: str) -> str:
    lines = []
    in_fence = False
    for line in text.splitlines():
        if _FENCE_RE.match(line.strip()):
            in_fence = not in_fence
            lines.append("")
            continue
        lines.append("" if in_fence else line)
    return "\n".join(lines)


def _split_sentences(text: str) -> list[str]:
    """Every sentence, a heading counted as one, a table row counted as
    one, after fenced code blocks are blanked."""
    sentences: list[str] = []
    for line in _blank_fences(text).splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if _HEADING_RE.match(stripped) or _TABLE_ROW_RE.match(stripped):
            sentences.append(stripped)
            continue
        for piece in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9`\"'])", stripped):
            piece = piece.strip()
            if piece:
                sentences.append(piece)
    return sentences


def _is_instruction(sentence: str) -> bool:
    lowered = sentence.lower()
    if re.search(r"\bmust\b|\bcan\b|\bdo not\b", lowered):
        return True
    first_word = re.match(r"[A-Za-z']+", sentence)
    if first_word and first_word.group(0).lower() in _IMPERATIVE_VERBS:
        return True
    return False


def _unescape_marker(quoted: str) -> str:
    r"""The sentence a marker names, with its escapes resolved.

    `\>` stands for `>`, so a sentence containing `-->` is written `--\>`.
    Without that, such a sentence could not be named at all. The natural form
    satisfies this module's own pattern but holds two `-->`, which makes it a
    malformed HTML comment: it closes at the first one and leaves `" -->`
    visible in the rendered file. Two template sentences have that shape,
    being the tail of a multi-line comment split on its full stop, and both
    left the command at exit 1 with no way to clear them.

    `\"` stands for `"`, which the pattern already allowed through and which
    is resolved here for the same reason. Any other backslash pair is left
    exactly as written, so a sentence that really contains a backslash still
    matches itself.
    """
    out, i = [], 0
    while i < len(quoted):
        if quoted[i] == "\\" and i + 1 < len(quoted) and quoted[i + 1] in '>"':
            out.append(quoted[i + 1])
            i += 2
            continue
        out.append(quoted[i])
        i += 1
    return "".join(out)


def _absorbed_sentences(text: str) -> set[str]:
    return {_unescape_marker(m.group(1)) for m in _ABSORBED_RE.finditer(text)}


def _best_match(sentence: str, candidates: list[str]) -> tuple[str | None, float]:
    best, best_ratio = None, 0.0
    for candidate in candidates:
        ratio = difflib.SequenceMatcher(None, sentence, candidate).ratio()
        if ratio > best_ratio:
            best, best_ratio = candidate, ratio
    return best, best_ratio


def _inventory_for(cwd: Path, base: str, path: str, similarity: float,
                    out_dir: Path) -> tuple[int, int, int, list[str]]:
    old_text = _show(cwd, base, path)
    new_text = _show(cwd, "HEAD", path)
    old_sentences = _split_sentences(old_text) if old_text else []
    new_sentences = _split_sentences(new_text) if new_text else []
    absorbed = _absorbed_sentences(new_text or "")

    rows = []
    unmapped: list[str] = []
    mapped_count = absorbed_count = 0
    for sentence in old_sentences:
        match, ratio = _best_match(sentence, new_sentences)
        if ratio >= similarity:
            mapped_count += 1
            rows.append((sentence, _is_instruction(sentence), "mapped", match, ratio))
        elif sentence in absorbed:
            absorbed_count += 1
            rows.append((sentence, _is_instruction(sentence), "absorbed", "", 0.0))
        else:
            unmapped.append(sentence)
            rows.append((sentence, _is_instruction(sentence), "UNMAPPED", "", 0.0))

    out_dir.mkdir(parents=True, exist_ok=True)
    slug = path.replace("/", "__")
    table = ["# Instruction inventory - " + path, "",
             "| merge-base sentence | instruction | status | matched | similarity |",
             "|---|---|---|---|---|"]
    for sentence, is_instr, status, match, ratio in rows:
        table.append(f"| {sentence} | {is_instr} | {status} | {match or ''} | "
                      f"{ratio:.2f} |")
    (out_dir / f"{slug}.md").write_text("\n".join(table) + "\n")

    return len(old_sentences), mapped_count, absorbed_count, unmapped


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--base", default=None)
    parser.add_argument("--similarity", type=float, default=0.6)
    args = parser.parse_args(argv)

    cwd = Path.cwd()
    out_dir = Path(args.out)
    base = args.base or _merge_base(cwd)
    head = _git(["rev-parse", "HEAD"], cwd).strip()
    files = _changed_instruction_files(cwd, base)

    print(f"base: {base}")
    print(f"head: {head}")
    print(f"similarity threshold: {args.similarity}")
    print(f"files: {len(files)}")

    exit_code = 0
    for path in files:
        sentences, mapped, absorbed, unmapped = _inventory_for(
            cwd, base, path, args.similarity, out_dir)
        print(f"  {path}: {sentences} sentence(s), {mapped} mapped, "
              f"{absorbed} absorbed, {len(unmapped)} unmapped")
        for sentence in unmapped:
            print(f"    unmapped: {sentence}")
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
