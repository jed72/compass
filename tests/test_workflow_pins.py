"""The framework's own CI workflow must SHA-pin third-party actions — the
same supply-chain stance `docs/security.md` asks Compass consumers to take.

Traces to: .compass/work/sha-pin-workflow-actions/spec.feature.md SCN-001.
"""
from __future__ import annotations

import re
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "compass.yml"
USES_LINE = re.compile(r"uses:\s+([^\s@]+)@(\S+)")
SHA = re.compile(r"^[0-9a-f]{40}$")


def test_third_party_actions_are_sha_pinned():
    unpinned: list[str] = []
    for line in WORKFLOW.read_text().splitlines():
        match = USES_LINE.search(line)
        if match and not SHA.match(match.group(2)):
            unpinned.append(line.strip())
    assert not unpinned, (
        "third-party actions in .github/workflows/compass.yml are not "
        "SHA-pinned; each `uses:` ref must be a 40-char hex SHA:\n  "
        + "\n  ".join(unpinned)
    )
