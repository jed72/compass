#!/usr/bin/env python3
"""Compares a batch's changed files against its merge base, to show that a
prose rewrite changed no behaviour: no printed string, no asserted string
and no code body. `prose-breaks-the-writing-style` needs this because
`verify.architecture` accepts only a `test-run` or a `command-output`
(`governance/guardrails.yml:182`), and this is the command that produces one.

Comparison, per file type:

- Python: the abstract syntax tree at both revisions, with a leading
  docstring stripped from every module, class and function body. Comments
  never enter an abstract syntax tree, so stripping the docstring is the
  whole of the work.
- Shell: the file with `#` comment text removed.
- YAML: every line with a `PROSE_KEYS` key's value blanked and every comment
  removed - the same key list the writing-style sweeps treat as prose, so the
  two halves cannot disagree about what prose is. Read as text, not parsed:
  `import yaml` outside `cli/compass_pkg/`, `cli/compass` or a
  `compass_python` heredoc does not resolve through this repository's one
  shared PyYAML mechanism (`tests/test_bundled_pyyaml.py`), and this script is
  none of those three.
- JSON: parsed structure, with `description` values blanked.
- Markdown: the contents of every fenced code block and every link target.
  A markdown file has no other behaviour.

The shell and YAML readers empty a line to remove prose from it, so they
compare the sequence of non-empty lines rather than the joined text. See
`_significant_lines`. The markdown and JSON readers cannot carry that
defect and do not use it: markdown collects the fenced lines and link
targets it cares about instead of blanking what it does not, and JSON
compares parsed structures, where neither formatting nor a line count
exists. `tests/test_writing_style.py` holds a case for each of the four, so
the two that are immune are recorded as checked rather than assumed.

`--allow-pinned-test PATH=REASON` excuses one test file entirely. The reason
is required and is printed beside the path, because an allowance nobody
explained is the same defect as a loosened matcher. The path must sit under
`tests/`, so the flag can never excuse a production file.

Exactly two things qualify, and nothing else:

1. A test whose assertion pinned wording this issue rewrites (`PBW-D6`). The
   prose and the assertion change in one commit, so the assertion change is
   not a behaviour change to find.
2. `tests/test_writing_style.py`, the mechanism file this issue's plan
   needs every batch to edit. Each batch deletes its own pending list and
   lowers `PENDING_PATHS_HIGH_WATER`, so every batch changes it. It is not
   audited surface: this issue introduced it and it has its own tests.

A production file, a test this issue merely happens to touch, or a real
behaviour change someone would rather not explain are all outside the flag.

WHAT THIS TOOL CANNOT SEE
=========================

The exit code is not a proof of no behaviour change; it is the result of the
comparisons below. `verify.architecture` rests on an architect's judgement of
the remaining differences (`DD-4`), and these are the gaps that judgement has
to cover.

- **Shell, across lines.** The comment scan reads one line at a time, so a
  quoted string or a here-document body spanning several lines is read as
  unquoted. A `#` inside such a body is taken for a comment and the text
  after it is dropped from the comparison.
- **Shell, beyond comments.** Two scripts with identical non-comment lines
  are called equal. Nothing checks that a command means what it did: a
  changed file mode, a renamed function used only by name, or a behaviour
  that depends on line numbers is invisible here.
- **YAML, three deliberate blind spots.** A trailing comment on a line that
  quotes anything is left in place, a prose key with an empty value keeps
  whatever follows it, and a plain scalar continued over several lines is not
  recognised. Each errs towards reporting a difference that is not one, which
  costs a second look rather than a missed change.
- **YAML, read as text.** Values are compared as written, so a rewrite that
  turns a block scalar into a flow scalar reads as a change even when a
  parser would call the two identical.
- **Markdown.** Only fenced code blocks and link targets are compared. An
  indented code block, a reference-style link definition and an HTML block
  are not read at all.
- **Python.** Only the abstract syntax tree is compared, with leading
  docstrings removed. A changed comment is invisible, which is intended, but
  so is a change that changes behaviour without changing the tree.
- **Any other file type** is reported as changed and left to the architect,
  because guessing would be worse.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

PROSE_KEYS = frozenset({"description", "statement", "rationale", "name", "help"})
_YAML_KEY_RE = re.compile(r"^(\s*-?\s*)([\w.\-]+)\s*:\s?(.*)$")


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


def _changed_files(cwd: Path, base: str) -> list[str]:
    out = _git(["diff", "--name-only", "--diff-filter=ACMR", f"{base}...HEAD"], cwd)
    return [line for line in out.splitlines() if line]


def _strip_python_docstrings(text: str) -> str | None:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if (isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                               ast.ClassDef))
                and body and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)):
            body.pop(0)
    return ast.dump(tree)


def _significant_lines(text: str) -> list[str]:
    """The lines that carry something, with trailing whitespace dropped.

    Both strippers below remove prose by emptying the line that held it, so
    the count of empty lines is a count of removed prose and says nothing
    about behaviour. Comparing joined text counted them, and a rewrite that
    changed how many lines a comment block occupied therefore read as a
    behaviour change with no behaviour changed. Almost every rewrite moves a
    comment's line count, so that comparison reported on almost every file.

    A blank line already in the source is dropped for the same reason: it
    separates prose, and neither shell nor YAML gives it meaning. The
    remaining lines are still compared as an ordered sequence, so a command
    line that changes, moves or disappears is still a difference.
    """
    return [stripped for stripped in
            (line.rstrip() for line in text.splitlines()) if stripped]


def _strip_one_shell_comment(line: str) -> str:
    """One line, with a trailing comment removed and quoted text kept.

    A `#` opens a comment only when it starts a word and no quote is open.
    Matching ` #` by pattern instead cut `echo "tag #alpha"` down to
    `echo "tag`, so a change to the part after the hash compared equal and
    the tool missed a changed command. That is a false negative in the one
    tool whose purpose is proving no behaviour changed, which is the
    direction that costs something.

    The scan tracks single quotes, double quotes and backslash escapes, which
    is what distinguishes a comment from `$#`, `${#var}`, a hash inside a
    `sed` expression and a quoted literal. It reads one line at a time and so
    does not track a quote or a here-document body that spans lines - see the
    module docstring for what that means.
    """
    in_single = False
    in_double = False
    at_word_start = True
    i = 0
    while i < len(line):
        char = line[i]
        if in_single:
            # Nothing escapes inside single quotes, not even a backslash.
            if char == "'":
                in_single = False
            at_word_start = False
        elif in_double:
            if char == "\\" and i + 1 < len(line):
                i += 2
                at_word_start = False
                continue
            if char == '"':
                in_double = False
            at_word_start = False
        else:
            if char == "\\" and i + 1 < len(line):
                i += 2
                at_word_start = False
                continue
            if char == "#" and at_word_start:
                return line[:i].rstrip()
            if char == "'":
                in_single = True
            elif char == '"':
                in_double = True
            at_word_start = char.isspace()
        i += 1
    return line


def _strip_shell_comments(text: str) -> str:
    return "\n".join(_strip_one_shell_comment(line)
                     for line in text.splitlines())


_YAML_TRAILING_COMMENT_RE = re.compile(r"^([^#'\"]*\S)\s+#.*$")
_YAML_BLOCK_SCALAR_RE = re.compile(r"^[>|][0-9]*[-+]?$")


def _blank_yaml_prose(text: str) -> str:
    """Every line, with a `PROSE_KEYS` key's value blanked and comments
    removed. Read as text rather than parsed - see the module docstring for
    why - so a folded or literal block scalar's continuation lines are not
    distinguished from an ordinary value. A prose key's continuation lines are
    therefore kept as they are, and `_significant_lines` is what stops a
    rewrap of them reading as a change.

    Two comment forms, handled differently, because YAML gives `#` two
    meanings:

    - A line whose first non-space character is `#` is always a comment, so it
      goes.
    - A trailing `#` is a comment only outside a quoted scalar. This drops one
      only when no quote character appears before it, which is where the
      reading is certain. A line that quotes anything is kept whole, so a
      reworded trailing comment there still reads as a change. That is the
      conservative direction: over-reporting costs a second look, while
      under-reporting means shipping the behaviour change this tool was run to
      catch.

    A prose key introducing a block scalar - `description: >`, `statement: |`
    and the chomped forms - takes its indented continuation lines with it,
    because those lines are the prose the key holds and rewrapping them is
    the commonest edit this issue makes. The value must be an explicit block
    indicator for that to happen. A prose key with an empty value is left
    alone, because what follows it could be a nested mapping rather than
    prose, and dropping real values would make this tool miss the change it
    exists to find. A plain scalar continued over several lines is not
    recognised either, so rewrapping one still reads as a change; the
    repository's YAML uses block scalars for prose, so that case does not
    arise here.
    """
    lines = []
    block_key_indent: int | None = None
    for line in text.splitlines():
        if block_key_indent is not None:
            if not line.strip():
                continue
            if len(line) - len(line.lstrip()) > block_key_indent:
                continue
            block_key_indent = None
        if line.lstrip().startswith("#"):
            continue
        trailing = _YAML_TRAILING_COMMENT_RE.match(line)
        if trailing:
            line = trailing.group(1)
        match = _YAML_KEY_RE.match(line)
        if match and match.group(2) in PROSE_KEYS:
            lines.append(f"{match.group(1)}{match.group(2)}:")
            if _YAML_BLOCK_SCALAR_RE.match(match.group(3).strip()):
                block_key_indent = len(match.group(1))
        else:
            lines.append(line)
    return "\n".join(lines)


def _blank_json_descriptions(node):
    if isinstance(node, dict):
        return {k: ("" if k == "description" else _blank_json_descriptions(v))
                for k, v in node.items()}
    if isinstance(node, list):
        return [_blank_json_descriptions(v) for v in node]
    return node


_FENCE_RE = re.compile(r"^(`{3,}|~{3,})(.*)$")
_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def _markdown_behaviour(text: str) -> str:
    fenced: list[str] = []
    in_fence = False
    for line in text.splitlines():
        if _FENCE_RE.match(line.strip()):
            in_fence = not in_fence
            continue
        if in_fence:
            fenced.append(line)
    links = _LINK_RE.findall(text)
    return "\n".join(fenced) + "\n" + "\n".join(links)


def _compare_file(cwd: Path, base: str, path: str) -> str | None:
    """None if the two revisions have equal behaviour, else a reason."""
    old = _show(cwd, base, path)
    new = _show(cwd, "HEAD", path)
    if old is None:
        return None  # new file - nothing existed before it to preserve
    if new is None:
        return "deleted"
    if old == new:
        return None
    suffix = Path(path).suffix
    if suffix == ".py":
        old_ast = _strip_python_docstrings(old)
        new_ast = _strip_python_docstrings(new)
        if old_ast is None or new_ast is None:
            return "does not parse as Python"
        if old_ast != new_ast:
            return "code body changed"
        return None
    if suffix == ".sh" or suffix == "":
        if (_significant_lines(_strip_shell_comments(old))
                != _significant_lines(_strip_shell_comments(new))):
            return "a command line changed"
        return None
    if suffix in (".yml", ".yaml"):
        if (_significant_lines(_blank_yaml_prose(old))
                != _significant_lines(_blank_yaml_prose(new))):
            return "a non-prose value changed"
        return None
    if suffix == ".json":
        try:
            old_data = _blank_json_descriptions(json.loads(old))
            new_data = _blank_json_descriptions(json.loads(new))
        except json.JSONDecodeError:
            return "does not parse as JSON"
        if old_data != new_data:
            return "a non-description value changed"
        return None
    if suffix == ".md":
        if _markdown_behaviour(old) != _markdown_behaviour(new):
            return "a fenced code block or a link target changed"
        return None
    return "changed, and this tool does not know how to read this file type"


def _parse_allowances(raw: list[str]) -> tuple[dict[str, str], str | None]:
    """`PATH=REASON` pairs, or an error message naming what was wrong.

    A reason is required, and it is printed beside the path in the run's
    output. An allowance nobody explained is the same defect as a loosened
    matcher: the report goes quiet and the record does not say why.
    """
    allowances: dict[str, str] = {}
    for entry in raw:
        path, separator, reason = entry.partition("=")
        path = path.strip()
        reason = reason.strip()
        if not separator or not reason:
            return {}, (
                f"--allow-pinned-test {entry!r} states no reason - refused. "
                "Use --allow-pinned-test PATH=REASON. An allowance with no "
                "reason hides a change instead of explaining it.")
        if not path.startswith("tests/"):
            return {}, (
                f"--allow-pinned-test {path} is not under tests/ - refused.")
        allowances[path] = reason
    return allowances, None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default=None)
    parser.add_argument("--allow-pinned-test", action="append", default=[],
                         dest="allowed", metavar="PATH=REASON")
    args = parser.parse_args(argv)

    cwd = Path.cwd()
    allowances, error = _parse_allowances(args.allowed)
    if error is not None:
        print(error)
        return 1

    base = args.base or _merge_base(cwd)
    head = _git(["rev-parse", "HEAD"], cwd).strip()
    changed = _changed_files(cwd, base)
    print(f"base: {base}")
    print(f"head: {head}")
    print(f"files compared: {len(changed)}")

    exit_code = 0
    for path in changed:
        if path in allowances:
            print(f"  {path}: allowed - {allowances[path]}")
            continue
        reason = _compare_file(cwd, base, path)
        if reason is not None:
            print(f"  {path}: {reason}")
            exit_code = 1
    unused = sorted(set(allowances) - set(changed))
    for path in unused:
        print(f"  {path}: allowed but not in the diff - the allowance did "
              f"nothing")
    if exit_code == 0:
        print("no changed file altered behaviour")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
