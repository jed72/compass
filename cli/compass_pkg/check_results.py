#!/usr/bin/env python3
# =============================================================================
# compass - the check result sentinel
# =============================================================================
# One value, in its own module so that both the check registry (checks.py) and
# the checks split out of it can use it without importing each other. It was
# defined in checks.py, which made any module holding a check unable to import
# it without a cycle.
#
# DEPENDENCY: PyYAML, bundled at cli/vendor/yaml/ and pinned in
# THIRD-PARTY-NOTICES.md. It is resolved by compass_pkg/__init__.py and is
# the only third-party code Compass ships; everything else is the Python 3
# standard library. This module uses none of it.
# =============================================================================
"""The sentinel for a check that passed without checking anything."""
from __future__ import annotations


class _NothingToCheck(int):
    """A pass that verified nothing, distinguishable from one that did.

    A check passes without checking anything when the thing it inspects does not exist in
    this project - no BDD runner wired, no claims recorded, no project
    guardrails declared. That is a legitimate pass, but counting it beside a
    real one lets the summary overstate what was verified.

    It subclasses int and is truthy, so every existing `if not passed` and
    every caller that only cares pass/fail keeps working untouched; only the
    summary asks whether a result `is NOTHING_TO_CHECK`.
    """

    def __repr__(self):
        return "NOTHING_TO_CHECK"


NOTHING_TO_CHECK = _NothingToCheck(1)
