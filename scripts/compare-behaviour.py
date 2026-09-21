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
- YAML: every line with a `PROSE_KEYS` key's value blanked - the same key
  list the writing-style sweeps treat as prose, so the two halves cannot
  disagree about what prose is. Read as text, not parsed: `import yaml`
  outside `cli/compass_pkg/`, `cli/compass` or a `compass_python` heredoc
  does not resolve through this repository's one shared PyYAML mechanism
  (`tests/test_bundled_pyyaml.py`), and this script is none of those three.
- JSON: parsed structure, with `description` values blanked.
- Markdown: the contents of every fenced code block and every link target.
  A markdown file has no other behaviour.

`--allow-pinned-test PATH` excuses one test file entirely - the one
exception this tool allows, for a test whose assertion pinned wording this
issue rewrites (`PBW-D6`). The path must sit under `tests/`, so the flag can
never excuse a production file.
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


def _strip_shell_comments(text: str) -> str:
    lines = []
    for line in text.splitlines():
        lines.append(re.sub(r"(?:^|\s)#.*$", "", line))
    return "\n".join(lines)


def _blank_yaml_prose(text: str) -> str:
    """Every line, with a `PROSE_KEYS` key's value blanked. Read as text
    rather than parsed - see the module docstring for why - so a folded or
    literal block scalar's continuation lines are not distinguished from an
    ordinary value; a rewrite that turns a block scalar into a flow scalar,
    or the reverse, is read as a behaviour change here even when the prose
    sweeps would call it identical. That is the conservative direction: a
    difference this misses would be the more expensive event."""
    lines = []
    for line in text.splitlines():
        match = _YAML_KEY_RE.match(line)
        if match and match.group(2) in PROSE_KEYS:
            lines.append(f"{match.group(1)}{match.group(2)}:")
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
        return None  # new file - nothing prior to preserve
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
        if _strip_shell_comments(old) != _strip_shell_comments(new):
            return "a command line changed"
        return None
    if suffix in (".yml", ".yaml"):
        if _blank_yaml_prose(old) != _blank_yaml_prose(new):
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default=None)
    parser.add_argument("--allow-pinned-test", action="append", default=[],
                         dest="allowed")
    args = parser.parse_args(argv)

    cwd = Path.cwd()
    for allowed in args.allowed:
        if not allowed.startswith("tests/"):
            print(f"--allow-pinned-test {allowed} is not under tests/ - refused.")
            return 1

    base = args.base or _merge_base(cwd)
    head = _git(["rev-parse", "HEAD"], cwd).strip()
    changed = _changed_files(cwd, base)
    print(f"base: {base}")
    print(f"head: {head}")
    print(f"files compared: {len(changed)}")

    exit_code = 0
    for path in changed:
        if path in args.allowed:
            print(f"  {path}: skipped, --allow-pinned-test")
            continue
        reason = _compare_file(cwd, base, path)
        if reason is not None:
            print(f"  {path}: {reason}")
            exit_code = 1
    if exit_code == 0:
        print("no changed file altered behaviour")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
