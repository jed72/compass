"""Register the traceability tags as pytest marks.

`compass bdd extract` tags every scenario with its traceability id (`@TRC-A1`),
which is what lets a per-scenario runner result map back to `task.yml`.
pytest-bdd turns each tag into a pytest mark - and pytest warns about any mark
it has not been told about, so without this an adopter's first green run is
buried in `PytestUnknownMarkWarning` noise.

Registering them dynamically, by reading the tags out of the extracted feature
file, means this never needs updating when a scenario is added. Copy this file
alongside the wiring; it is the one piece of glue that is not obvious.
"""
from __future__ import annotations

import pathlib
import re

FEATURE = (pathlib.Path(__file__).resolve().parent
           / ".compass" / "work" / "reset-password" / "acceptance-criteria.feature")


def pytest_configure(config):
    if not FEATURE.is_file():
        # Extraction has not run yet. Not an error here - the run that follows
        # will fail on the missing feature file with a clearer message.
        return
    for tag in sorted(set(re.findall(r"^\s*@(\S+)", FEATURE.read_text(),
                                     re.MULTILINE))):
        config.addinivalue_line(
            "markers",
            f"{tag}: Compass traceability id, from the extracted feature file",
        )
