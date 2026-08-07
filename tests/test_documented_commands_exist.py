"""Every `compass <subcommand>` shown in the docs must be a real subcommand.

Two skills told the reader to run `compass frame --reassess`. There is no
`frame` subcommand - re-framing is the slash command `/compass:frame
--reassess`. The instruction was followed-shaped and unrunnable, which is worse
than no instruction: the reader tries it, gets an argparse error, and loses
confidence in the rest of the page.

This scans code spans and fenced blocks (not prose, where "compass" is the
framework's name rather than a command) across every documented surface.
"""
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
COMPASS_CLI = ROOT / "cli" / "compass"

SEARCH_DIRS = ("skills", "commands", "docs", "routes", "governance", "templates")

# Proposals and analyses argue for commands that do not exist yet, or compare
# Compass to other tools - naming a hypothetical command is the point there.
# This test covers the surfaces that tell a reader what to run *today*.
EXCLUDED_DIRS = ("docs/proposals", "docs/analysis")

# `compass --help` renders positional choices as {a,b,c}; anything else after
# `compass` in a code span is either a global flag or a typo.
GLOBAL_FLAGS = {"--help", "-h", "--version"}

INVOCATION_RE = re.compile(r"\bcompass\s+(--?[a-zA-Z-]+|[a-z][a-z0-9-]*)")
CODE_SPAN_RE = re.compile(r"`([^`\n]+)`")
FENCE_RE = re.compile(r"^```.*?^```", re.M | re.S)


def _subcommands():
    out = subprocess.run(
        [sys.executable, str(COMPASS_CLI), "--help"],
        capture_output=True, text=True, check=True, timeout=30,
    ).stdout
    m = re.search(r"\{([a-zA-Z0-9_,\-]+)\}", out)
    assert m, f"could not parse subcommands from --help:\n{out}"
    return set(m.group(1).split(","))


def _markdown_files():
    files = [ROOT / "CLAUDE.md", ROOT / "README.md"]
    for d in SEARCH_DIRS:
        files += sorted((ROOT / d).rglob("*.md"))
    return [
        f for f in files
        if f.exists()
        and not any(f.relative_to(ROOT).as_posix().startswith(d) for d in EXCLUDED_DIRS)
    ]


def _invocations(text):
    """Yield every `compass <word>` inside a code span or fenced block."""
    for fence in FENCE_RE.findall(text):
        for line in fence.splitlines():
            line = line.lstrip("$ ").strip()
            if line.startswith("compass "):
                yield from INVOCATION_RE.findall(line)[:1]
    for span in CODE_SPAN_RE.findall(FENCE_RE.sub("", text)):
        span = span.strip()
        if span.startswith("compass "):
            yield from INVOCATION_RE.findall(span)[:1]


def test_every_documented_compass_invocation_is_a_real_subcommand():
    known = _subcommands() | GLOBAL_FLAGS
    bad = []
    for path in _markdown_files():
        for word in _invocations(path.read_text(encoding="utf-8")):
            if word not in known:
                bad.append(f"{path.relative_to(ROOT)}: `compass {word}`")
    assert not bad, (
        "These docs tell the reader to run a subcommand that does not exist:\n  "
        + "\n  ".join(sorted(set(bad)))
        + f"\n\nReal subcommands: {', '.join(sorted(_subcommands()))}"
    )
