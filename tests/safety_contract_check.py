"""Does the safety contract name a real mechanism behind every guarantee?

Issue: claims-match-what-is-proved. Backs scenarios TRC-B4, TRC-D1 and TRC-D2.

Why this exists. An outside review of 3.2.0 found several public promises
stronger than the code behind them. Repairing the wording without a check buys
one release: the next person to add a guarantee has nothing stopping them
adding one nothing backs, and a table row can go on naming a file that was
renamed years ago.

Why it is built the way it is. The obvious version of this check parses two
markdown sections, compares them, and passes. Fed a file it cannot parse it
finds no guarantees, compares two empty sets, and reports success having
inspected nothing. Four checks have shipped in this project that failed exactly
that way. So an empty parse raises here rather than passing - see EmptyContract.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass


class EmptyContract(RuntimeError):
    """A section of the contract came back empty.

    Raised rather than tolerated. With no guarantees parsed nothing can be
    found unbacked, the problem count is zero, and that zero is
    indistinguishable from a contract in perfect order. Zero is the answer this
    check exists to produce, so a zero meaning "nothing was inspected" is the
    worst one available.
    """


#: A guarantee is a numbered list item whose first bold run is its title.
#: DOTALL matters: several titles wrap across a line, and without it this
#: silently skipped them - the rows were then reported as orphans while the
#: guarantees themselves went uninspected.
#: Two shapes, because the contract carries its guarantees as `### 5. Title`
#: headings and carried them as `5. **Title**` list items before the docs were
#: slimmed on 2026-08-26. Reading both means the check follows the document
#: rather than the document being held to a layout to keep a regex happy.
_GUARANTEE = re.compile(
    r"^(?:###\s+(\d+)\.\s+(.+?)$|(\d+)\.\s+\*\*(.+?)\*\*)", re.M)

#: A backing row opens with the guarantee's number, then a parenthesised
#: shorthand, then the mechanism cell: `| 3 (typed evidence) | ... |`
_BACKING_ROW = re.compile(r"^\|\s*(\d+)\s*\(([^)]*)\)\s*\|(.+?)\|\s*$", re.M)

#: Anything in backticks. Only the ones that look like a path or a compass
#: command are resolved; a term of art such as `human-approval` is left alone.
_TOKEN = re.compile(r"`([^`]+)`")


def _section(text: str, heading_contains: str) -> str:
    """The body under the first `##` heading containing `heading_contains`."""
    parts = re.split(r"^## ", text, flags=re.M)
    for part in parts:
        head = part.split("\n", 1)[0]
        if heading_contains.lower() in head.lower():
            return part
    return ""


def parse_guarantees(text: str) -> dict[int, str]:
    """Guarantee number -> title, from the guarantees section."""
    body = _section(text, "guarantees")
    found = {}
    for h_num, h_title, l_num, l_title in _GUARANTEE.findall(body):
        num, title = (h_num, h_title) if h_num else (l_num, l_title)
        found[int(num)] = title.strip()
    if not found:
        raise EmptyContract(
            "no numbered guarantees were parsed from the contract. Either the "
            "guarantees section is missing, or its shape changed and this "
            "check can no longer read it. Refusing to report a clean result "
            "from a file that was never inspected.")
    return found


def parse_backing(text: str) -> dict[int, str]:
    """Guarantee number -> the mechanism cell that says how it is honoured."""
    body = _section(text, "honoured mechanically") or _section(
        text, "mechanical enforcement")
    found = {int(n): cell.strip() for n, _short, cell in _BACKING_ROW.findall(body)}
    if not found:
        raise EmptyContract(
            "no backing rows were parsed from the contract. Either the table "
            "saying how each guarantee is honoured is missing, or its shape "
            "changed and this check can no longer read it.")
    return found


def named_mechanisms(cell: str) -> list[str]:
    """The backticked tokens in a mechanism cell that claim something exists.

    A path is anything containing a separator or a known suffix. A command is
    anything starting `compass `. Everything else - `human-approval`,
    `advisory`, a schema key - is a term rather than an artifact, and this
    check has no business asserting it is on disk.
    """
    out = []
    for tok in _TOKEN.findall(cell):
        tok = tok.strip()
        if tok.startswith("compass "):
            out.append(tok)
        elif "/" in tok or tok.endswith((".md", ".yml", ".yaml", ".json", ".py", ".sh")):
            out.append(tok)
    return out


@dataclass(frozen=True)
class Problem:
    guarantee: int
    detail: str

    def __str__(self) -> str:      # pragma: no cover - formatting only
        return f"guarantee {self.guarantee}: {self.detail}"


def _command_exists(command: str, repo_root: str) -> bool:
    """Is `compass <verb>` a real subcommand of the CLI in this repository?"""
    verb = command.split()[1] if len(command.split()) > 1 else ""
    if not verb:
        return False
    src = os.path.join(repo_root, "cli", "compass")
    try:
        with open(src, encoding="utf-8") as fh:
            body = fh.read()
    except OSError:
        return False
    return f'"{verb}"' in body or f"'{verb}'" in body


def check(text: str, repo_root: str) -> list[Problem]:
    """Every guarantee has a backing row, and every named artifact exists."""
    guarantees = parse_guarantees(text)
    backing = parse_backing(text)
    problems: list[Problem] = []

    for n in sorted(guarantees):
        if n not in backing:
            problems.append(Problem(n, (
                f"'{guarantees[n]}' has no row in the table saying how it is "
                f"honoured. A guarantee nothing backs is a promise with no "
                f"mechanism behind it.")))

    for n in sorted(backing):
        if n not in guarantees:
            problems.append(Problem(n, (
                "a backing row names a guarantee that is not in the list. "
                "Either the guarantee was removed and its row left behind, or "
                "the numbering has drifted.")))
            continue
        for tok in named_mechanisms(backing[n]):
            if tok.startswith("compass "):
                if not _command_exists(tok, repo_root):
                    problems.append(Problem(n, (
                        f"names the command `{tok}`, which the CLI does not "
                        f"provide.")))
            elif not os.path.exists(os.path.join(repo_root, tok)):
                problems.append(Problem(n, (
                    f"names `{tok}`, which is not in the repository.")))

    return problems
