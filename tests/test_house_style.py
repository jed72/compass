"""House style invariants over the framework's own source.

These are invariants of *this repository*, not framework guardrails. They run
in this repo's pytest suite alongside `test_release_invariants.py`, never
against an adopting project's task, and never as a `compass check` gate.
Strategy S7 in `governance/strategies.md` is the reasoning; this file is the
mechanical half of the one house-style rule that has a mechanical half.

Two rules are enforced here:

1. No em dash (U+2014). Where an em dash would go, Compass writes a plain
   hyphen with spaces around it. En dashes (U+2013) are deliberately left
   alone: they carry meaning in ranges such as `G1-G5` and `2-3 streams`.
2. No agent co-author trailer in any tracked file. The human author owns the
   change; `devlog.md` and `task.yml` already record provenance in a form the
   framework can read.

This file contains no literal em dash and no literal forbidden trailer. Every
needle is assembled from its parts at import time, so the scanners never have
to exempt themselves from their own rules.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent

# Assembled, never written literally - see the module docstring.
EM_DASH = chr(0x2014)
JSON_ESCAPED_EM_DASH = "\\u" + "2014"
FORBIDDEN_TRAILERS = (
    "Co-Authored-By: " + "Claude",
    "Co-authored-by: " + "Claude",
    "Generated with [" + "Claude Code]",
)

# `assets/` is binary; LICENSE is the verbatim Apache-2.0 text and is never
# edited for style.
SKIP_PREFIXES = ("assets/",)
SKIP_EXACT = {"LICENSE"}

# Only used by the os.walk fallback. Under git these are already invisible,
# because every one of them is in .gitignore.
WALK_PRUNE = {
    ".git", "__pycache__", ".ruff_cache", ".pytest_cache", ".mypy_cache",
    ".idea", ".vscode", "node_modules", "dist", "build", "assets",
}

MAX_REPORTED = 40


def _tracked_files(root: Path) -> list[Path]:
    """Every file the repository ships.

    Prefers `git ls-files`, which excludes build noise and the framework's own
    `.compass/work/` for free while still including the deliberately-tracked
    `examples/*/.compass/work/` fixtures. Falls back to a filesystem walk so
    the test still works from an extracted release tarball, which has no git
    metadata (see `scripts/release.sh`).
    """
    try:
        out = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=root, capture_output=True, text=True, timeout=30, check=True,
        ).stdout
        rels = [p for p in out.split("\0") if p]
    except (subprocess.SubprocessError, OSError):
        rels = _walk(root)
    return [root / rel for rel in rels if not _skipped(rel)]


def _walk(root: Path) -> list[str]:
    import os
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in WALK_PRUNE]
        rel_dir = Path(dirpath).relative_to(root)
        # The framework's own task state is gitignored; the examples' is not.
        if rel_dir.parts[:2] == (".compass", "work"):
            dirnames[:] = []
            continue
        for name in filenames:
            found.append(str(rel_dir / name) if str(rel_dir) != "." else name)
    return found


def _skipped(rel: str) -> bool:
    return rel in SKIP_EXACT or rel.startswith(SKIP_PREFIXES)


def _read(path: Path) -> str | None:
    """File text, or None when the file is binary or has gone away."""
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def _scan(needle: str, only_suffix: str | None = None) -> list[str]:
    """Every occurrence of `needle`, as `path:line:col: excerpt` strings."""
    hits: list[str] = []
    for path in _tracked_files(REPO_ROOT):
        if only_suffix and path.suffix != only_suffix:
            continue
        text = _read(path)
        if text is None or needle not in text:
            continue
        rel = path.relative_to(REPO_ROOT)
        for lineno, line in enumerate(text.splitlines(), 1):
            col = line.find(needle)
            while col >= 0:
                hits.append(f"{rel}:{lineno}:{col + 1}: {line.strip()[:100]}")
                col = line.find(needle, col + 1)
    return hits


def _report(hits: list[str], rule: str, fix: str) -> str:
    shown = "\n".join("  " + h for h in hits[:MAX_REPORTED])
    more = ""
    if len(hits) > MAX_REPORTED:
        more = f"\n  ... and {len(hits) - MAX_REPORTED} more"
    return f"{len(hits)} house-style violation(s).\n{rule}\n{shown}{more}\n{fix}"


def test_no_em_dash_in_tracked_files():
    """No U+2014 anywhere the repository ships.

    Note this deliberately does not scan U+2013. En dashes are correct in
    ranges and there are 53 of them doing real work.
    """
    hits = _scan(EM_DASH)
    assert not hits, _report(
        hits,
        "Rule: write a plain hyphen with spaces around it where an em dash "
        "would go (governance/strategies.md, Voice and writing strategies).",
        "Fix: replace the character with '-'. Do not touch U+2013 en dashes, "
        "which are correct in ranges.",
    )


def test_no_json_escaped_em_dash():
    """No em dash hiding inside a JSON string escape.

    A JSON encoder writes U+2014 as a six-character escape, which the byte
    scan above cannot see. Both plugin manifests carried one, and the
    marketplace description is the first prose an adopter ever reads.
    """
    hits = _scan(JSON_ESCAPED_EM_DASH, only_suffix=".json")
    assert not hits, _report(
        hits,
        "Rule: no em dash, including one encoded as a JSON escape sequence.",
        "Fix: replace the escape with '-' by string edit. Do not re-serialise "
        "the file, which would reflow it.",
    )


def test_no_agent_coauthor_trailer_in_tracked_files():
    """No commit or pull-request body in the repository credits an agent.

    This scans files rather than git history on purpose. CI checks out at
    depth 1, so a history scan would pass vacuously there and behave
    differently on a local clone - the kind of environment-dependent result
    strategy S5 (intermittency is failure) rules out. Enforcing the rule on
    commit messages themselves belongs in a commit-msg hook, not here.
    """
    hits: list[str] = []
    for trailer in FORBIDDEN_TRAILERS:
        hits.extend(_scan(trailer))
    assert not hits, _report(
        hits,
        "Rule: commit messages and pull-request bodies never carry a "
        "Co-Authored-By line naming an agent, and never a 'Generated with' "
        "footer (governance/strategies.md, strategy S7).",
        "Fix: remove the trailer. The human author owns the change.",
    )
