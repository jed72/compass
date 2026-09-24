"""The one definition of the per-line scan exemption marker.

`governance/terminology.yml` argues that a per-line marker beats a path prefix
because it is countable: `grep -rn "vocabulary-scan: allow" .` enumerates every
exemption with the reason someone wrote for it. That argument only holds while
the reason is real.

**A LETTER after the dash, not merely a non-space.** In markdown the marker is
written inside an HTML comment, and the `-->` that closes the comment gives
both a dash and a non-space character - so a pattern asking for
`allow\\s*-\\s*\\S` read `<!-- vocabulary-scan: allow -->` as reasoned while it
gave nothing. Nine markers in scanned markdown are HTML comments, so that is
the normal shape in prose rather than an edge case.

**One definition, three readers.** `tests/test_terminology.py`,
`tests/test_docs_prose.py` and `tests/test_documented_commands_exist.py` all
import this one definition, so they cannot disagree about what counts as a
reason.
"""
from __future__ import annotations

import re

ALLOW_MARKER_RE = re.compile(r"vocabulary-scan:\s*allow\s*-\s*[A-Za-z]")
