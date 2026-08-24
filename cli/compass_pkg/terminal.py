#!/usr/bin/env python3
# =============================================================================
# compass - the terminal output contract
# =============================================================================
# Every line a person reads comes through here. A verb passes the PIECES of
# what it wants to say - the outcome, the artifact to read, the items, the
# concerns - and this module decides how they render in the mode the user
# asked for.
#
# WHY PIECES AND NOT STRINGS. A filter that wraps stdout and counts lines after
# the fact can only truncate. It cannot re-order, cap a list at three and say
# how many were hidden, move a line to --verbose, or emit JSON, because you
# cannot recover structure from prose that has already been flattened.
#
# TWO CONTRACTS, NOT ONE RULE.
#   hand-off - a verb that ends a stage or renders a verdict. One screen.
#   report   - a verb somebody runs deliberately to GET detail, like
#              `calibration` or `terminology`. Keeps every finding, but opens
#              with a summary they can stop at. Cutting a report to twelve
#              lines removes the reason to run it.
#
# DEPENDENCY: none. This module is Python 3 standard library only - json, os,
# sys and re. It is the one CLI module that touches no third-party code at all;
# the YAML parser the rest of the package uses travels inside the plugin, so
# there is nothing to install either way.
#
# ADR-017 IS ENFORCED STRUCTURALLY, NOT BY INSTRUCTION. An identifier is a key,
# not jargon: attach its meaning, never delete the id. A twelve-line budget
# creates constant pressure to drop "(RP-FLOOR-001, floor)" from a line to save
# room. So this module drops WHOLE LINES and has no code path that edits the
# interior of a line it keeps - the pressure has nowhere to act.
# =============================================================================
"""Rendering what a person reads, in the mode they asked for."""
from __future__ import annotations

import json
import os
import sys

# The budget, and why each number is what it is.
HANDOFF_LINES = 12       # the proposal's number - where a reader stops scrolling
QUIET_HANDOFF_LINES = 5  # a hand-off with nothing to decide
REPORT_SUMMARY_LINES = 5
MAX_WIDTH = 100          # a line budget alone is met by joining lines
MAX_ITEMS = 3            # "at most three key choices and three concerns"

MODES = ("quiet", "summary", "verbose", "json")
DEFAULT_MODE = "summary"

MODE_FLAGS = ("--quiet", "--summary", "--verbose", "--json", "--evidence-out")


class _NothingToCheck:
    """A guard that was handed nothing. Not a pass.

    Truthy would make an empty input clear the guard; falsey would make it read
    as a breach. It is neither, and callers compare against the sentinel.
    """

    def __bool__(self):
        return False

    def __repr__(self):
        return "NOTHING_TO_CHECK"


NOTHING_TO_CHECK = _NothingToCheck()


def add_mode_flags(parser):
    """Attach the five mode flags to one leaf parser.

    A flag the verb ALREADY declares is left alone. `approach evaluate --json`
    shipped before this contract existed and sets its own attribute; ADR-006
    makes that public surface, so the walk defers to it rather than colliding
    with it. `resolve_mode` reads both spellings, so the verb still ends up in
    JSON mode either way.
    """
    have = {o for a in parser._actions for o in a.option_strings}
    g = parser.add_argument_group("output")
    if "--quiet" not in have:
        g.add_argument("--quiet", dest="_mode", action="store_const", const="quiet",
                       help="errors and the decision hand-off only")
    if "--summary" not in have:
        g.add_argument("--summary", dest="_mode", action="store_const",
                       const="summary", help="the default human view")
    if "--verbose" not in have:
        g.add_argument("--verbose", dest="_mode", action="store_const",
                       const="verbose", help="diagnostic detail")
    if "--json" not in have:
        g.add_argument("--json", dest="_mode", action="store_const", const="json",
                       help="machine consumer")
    if "--evidence-out" not in have:
        g.add_argument("--evidence-out", metavar="PATH",
                       help="write raw capture to PATH instead of printing it")
    return parser


def attach_mode_flags(parser):
    """Add the five flags to every LEAF parser in the tree, recursively.

    Recursion is the whole job. The tree has thirteen nested subparser groups -
    `issue`, `bdd`, `gate`, `evidence`, `adr` and eight more - under 47
    `add_parser` calls. A walk that handles only the top level attaches the
    flags to `issue` and misses `issue dashboard` entirely, which is how a
    guard over this tree passes while checking a fraction of it.

    Returns the number of leaves reached, so a caller can tell "walked the
    tree" from "found nothing".

    THE OUTPUT KIND IS NOT SET HERE, and that asymmetry is deliberate. A flag
    must arrive without the verb's author doing anything, because forgetting it
    would make the flag silently useless on that verb. The hand-off/report
    declaration is the opposite: it is written at each `set_defaults(func=...)`
    so that a new verb which forgets it FAILS, rather than being defaulted into
    whichever contract was easiest. Deriving it from a list here would mean no
    verb could ever lack one, and the guard that checks for it could never
    fail - which is a check that cannot fail wearing the shape of convenience.
    """
    import argparse

    reached = 0

    def walk(p):
        nonlocal reached
        subs = [a for a in p._actions
                if isinstance(a, argparse._SubParsersAction)]
        if not subs:
            add_mode_flags(p)
            reached += 1
            return
        for action in subs:
            for child in action.choices.values():
                walk(child)

    walk(parser)
    return reached


def resolve_mode(args):
    """The mode a verb should render in, from the parsed arguments.

    Reads the verb's own `--json` too, for the one verb that shipped with it
    before this contract existed. Its attribute is `json`, not `_mode`.
    """
    mode = getattr(args, "_mode", None)
    if mode in MODES:
        return mode
    if getattr(args, "json", False):
        return "json"
    return DEFAULT_MODE


def emitter_for(args):
    """The Emitter a verb should use, built from its own parsed arguments."""
    return Emitter(mode=resolve_mode(args),
                   evidence_out=getattr(args, "evidence_out", None))


_ID_TAIL = __import__("re").compile(r"\s*\(([A-Z][A-Z0-9-]*[0-9][^)]*)\)\s*$")


def _path_line(prefix, path):
    """A path is printed WHOLE, however long it is.

    Shortening a path makes it unopenable, and a link a reader cannot follow is
    worse than a line that is merely wide - one fails at the thing it exists
    for, the other is untidy. The width guard knows about this and exempts a
    line whose overflow is a single unbreakable token.
    """
    return "%s%s" % (prefix, str(path).strip())


def _fit(text, prefix=""):
    """One line, never wider than the budget, with its identifier kept.

    Shortening happens to a single field's VALUE as it becomes a line, before
    anything is assembled - the compression step never edits a line it keeps.

    ADR-017 applies here too, and this is where it would quietly break. A rule
    line carries its id at the end - "Large work - full weight, plausibly
    parallel (RP-SHAPE-004, shape)". Cutting that to fit would drop the id and
    keep the prose, which is exactly the deletion the decision forbids. So a
    trailing identifier is lifted off, the prose is shortened, and the id is
    put back.
    """
    text = " ".join(str(text).split())
    room = MAX_WIDTH - len(prefix)
    if len(text) <= room:
        return prefix + text

    m = _ID_TAIL.search(text)
    if m:
        tail = " (%s)" % m.group(1)
        body = text[:m.start()].rstrip()
        keep = room - len(tail) - 1
        if keep > 8:
            return prefix + body[:keep] + "…" + tail
    return prefix + text[:max(1, room - 1)] + "…"


def _capped(values, label):
    """At most three, plus a line saying how many were not shown.

    The count line is not decoration. A silent truncation reads as "there were
    three", which is a claim the command never checked.
    """
    values = [v for v in (values or [])]
    shown = values[:MAX_ITEMS]
    lines = [_fit(v, "  - ") for v in shown]
    hidden = len(values) - len(shown)
    if hidden:
        lines.append(_fit("... and %d more %s - see the artifact above"
                          % (hidden, label), "  "))
    return lines


class Emitter:
    """Collects what a verb wants to say, and renders it in one mode."""

    def __init__(self, mode=DEFAULT_MODE, evidence_out=None, stream=None):
        self.mode = mode if mode in MODES else DEFAULT_MODE
        self.evidence_out = evidence_out
        self._out = []
        self._doc = None
        self._stream = stream

    # -- the two contracts --------------------------------------------------

    def hand_off(self, outcome, read=None, items=None, concerns=None,
                 reply=None, detail=None, failed=False):
        """A verb that ends a stage or renders a verdict. One screen."""
        if self.mode == "json":
            self._doc = {"outcome": outcome, "read": read,
                         "items": list(items or []),
                         "concerns": list(concerns or []),
                         "reply": reply, "failed": bool(failed)}
            return self

        if self.mode == "quiet" and not failed and not reply:
            # Nothing to decide and nothing went wrong. The exit code carries
            # it. This is the case the proposal left unstated, and an unstated
            # case in a mode flag becomes each verb's own guess.
            self._note_no_capture(silent=True)
            return self

        lines = [_fit(outcome)]
        if read:
            lines.append(_path_line("Read: ", read))
        if items:
            lines.append("")
            lines.append("Key choices:")
            lines += _capped(items, "choices")
        if concerns:
            lines.append("")
            lines.append("Pay attention to:")
            lines += _capped(concerns, "concerns")
        if detail and self.mode == "verbose":
            lines.append("")
            lines += [_fit(d, "  ") for d in detail]
        if reply:
            lines.append("")
            lines.append(_fit(reply, "Reply: "))

        if self.mode != "verbose":
            lines = _within(lines, HANDOFF_LINES)
        self._out = lines
        self._note_no_capture()
        return self

    def report(self, summary, detail=None, capture=None):
        """A verb somebody runs to GET detail. Summary first, detail in full.

        The hand-off budget is deliberately NOT applied here. Cutting a report
        to twelve lines removes the reason to run it.
        """
        if self.mode == "json":
            self._doc = {"summary": list(summary or []),
                         "detail": list(detail or [])}
            if capture is not None and self.evidence_out:
                self._write_capture(capture)
                self._doc["capture"] = self.evidence_out
            return self

        lines = [_fit(s) for s in (summary or [])][:REPORT_SUMMARY_LINES]
        if detail and self.mode != "quiet":
            lines.append("")
            lines += [_fit(d) for d in detail]

        if capture is not None:
            if self.evidence_out:
                self._write_capture(capture)
                lines.append("")
                lines.append(_path_line("Raw output: ", self.evidence_out))
            else:
                lines.append("")
                lines.append("Raw output not captured - pass --evidence-out "
                             "PATH to write it")
        self._out = lines
        return self

    # -- capture ------------------------------------------------------------

    def _write_capture(self, capture):
        d = os.path.dirname(os.path.abspath(self.evidence_out))
        if d and not os.path.isdir(d):
            os.makedirs(d, exist_ok=True)
        with open(self.evidence_out, "w", encoding="utf-8") as fh:
            fh.write(capture)

    def _note_no_capture(self, silent=False):
        """`--evidence-out` on a verb with nothing to capture.

        Not an error: a script that passes the flag uniformly across a pipeline
        should not break on the verbs that happen to have nothing to say.
        """
        if not self.evidence_out or silent or self.mode in ("quiet", "json"):
            return
        self._out.append(_path_line(
            "There was nothing to capture, so no file was written to ",
            self.evidence_out))

    # -- rendering ----------------------------------------------------------

    def rendered(self):
        if self.mode == "json":
            return json.dumps(self._doc or {}, indent=2)
        return "\n".join(self._out)

    def flush(self):
        text = self.rendered()
        if text:
            print(text, file=self._stream or sys.stdout)
        return text


def _within(lines, budget):
    """Fit to the budget by dropping WHOLE lines from the end.

    Never by editing a line it keeps - that is the ADR-017 rule made
    structural. Blank separators go first, because they cost a line and carry
    no meaning.
    """
    if len(lines) <= budget:
        return lines
    kept = [l for l in lines if l.strip()]
    if len(kept) <= budget:
        return kept
    return kept[:budget - 1] + ["... %d more line(s) not shown - run with "
                                "--verbose" % (len(kept) - budget + 1)]


def over_budget(outputs, budget=HANDOFF_LINES, width=MAX_WIDTH):
    """Which verbs printed past the contract, and by how much.

    `outputs` maps a verb's command path to what it actually printed. Returns a
    list of findings, each naming the verb, its count and its budget - an
    unactionable failure gets suppressed rather than fixed.

    An EMPTY input returns the sentinel, not an empty list. A guard handed
    nothing that answers "all good" is how four checks in one release cleared
    without reading anything.
    """
    if not outputs:
        return NOTHING_TO_CHECK
    findings = []
    for verb, text in sorted(outputs.items()):
        lines = text.splitlines() or [text]
        if len(lines) > budget:
            findings.append("%s printed %d lines against a budget of %d"
                            % (verb, len(lines), budget))
        # A line is only "too wide" if it could have been narrower. One that
        # is long because it carries a whole path is exempt: shortening a path
        # makes it unopenable, which fails at the thing the line exists for.
        wide = [l for l in lines
                if len(l) > width and not _is_unbreakable(l, width)]
        if wide:
            findings.append(
                "%s printed %d line(s) wider than %d characters (longest %d), "
                "so a line budget alone would be met by joining lines"
                % (verb, len(wide), width, max(len(l) for l in wide)))
    return findings


def _is_unbreakable(line, width):
    """Is this line long only because of one token that cannot be broken?

    A path or a URL. Everything before it must still fit the budget, so this
    exempts `Read: /very/long/path` and not a paragraph with a path in it.
    """
    parts = line.split()
    if not parts:
        return False
    longest = max(parts, key=len)
    if len(longest) <= 20:
        return False
    rest = len(line) - len(longest)
    return rest <= width and ("/" in longest or "://" in longest)


# =============================================================================
# Reports
# =============================================================================

class Report:
    """A verb that is run deliberately to GET detail.

    It collects a SUMMARY - what was found, in a few lines a reader can stop at
    - and named SECTIONS of rows. The hand-off budget is never applied: cutting
    a report to twelve lines removes the reason to run it.

    Rows may be plain strings or dicts. Dicts are what make `--json` a machine
    mode rather than prose in a wrapper, so a verb that has structure should
    pass it rather than pre-formatted lines.
    """

    def __init__(self, args, title=None):
        self.mode = resolve_mode(args)
        self.evidence_out = getattr(args, "evidence_out", None)
        self.title = title
        self._summary = []
        self._sections = []
        self._body = []
        self._extra = {}

    def summary(self, *lines):
        for l in lines:
            if l is not None:
                self._summary.append(str(l))
        return self

    def section(self, name, rows, render=None):
        """One named group. `render` turns a row into its display line."""
        self._sections.append((name, list(rows or []), render))
        return self

    def body(self, text):
        """Prose a verb already renders itself, kept as the report's detail.

        For a verb whose rendering is not worth restructuring yet: it still
        gets the right behaviour in every mode, and `data()` is what carries
        the machine-readable half. Prefer `section()` with dict rows where the
        structure already exists - a report whose JSON is only prose is a
        wrapper, not a machine mode.
        """
        self._body = [l for l in str(text).splitlines()]
        return self

    def data(self, **kw):
        """Extra machine-only fields for --json."""
        self._extra.update(kw)
        return self

    def _row_line(self, row, render):
        if render is not None:
            return render(row)
        if isinstance(row, dict):
            return "  ".join("%s=%s" % (k, v) for k, v in row.items())
        return str(row)

    def emit(self):
        if self.mode == "json":
            doc = {"summary": list(self._summary),
                   "sections": {name: rows for name, rows, _ in self._sections}}
            if self._body:
                doc["body"] = list(self._body)
            doc.update(self._extra)
            if self.title:
                doc["title"] = self.title
            print(json.dumps(doc, indent=2, default=str))
            return 0

        # A summary line carrying a path is printed WHOLE. Shortening it makes
        # the link unopenable, which fails at the thing the line exists for -
        # the same rule the hand-off applies, and the same mistake made twice
        # before it was written down here.
        head = [l if _is_unbreakable(l, MAX_WIDTH) else _fit(l)
                for l in self._summary][:REPORT_SUMMARY_LINES]
        if self.mode == "quiet":
            # NOT silence. Somebody who asked for a report asked for an answer;
            # --quiet says they want it short, not that they want nothing.
            if head:
                print("\n".join(head))
            return 0

        out = list(head)
        if self._body:
            out.append("")
            out += self._body
        for name, rows, render in self._sections:
            if not rows:
                continue
            out.append("")
            out.append("  %s (%d)" % (name, len(rows)))
            for row in rows:
                out.append("    %s" % self._row_line(row, render))
        print("\n".join(out))
        return 0
