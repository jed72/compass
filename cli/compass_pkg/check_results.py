#!/usr/bin/env python3
# =============================================================================
# compass - the check result sentinel
# =============================================================================
# One value, in its own module so that both the check registry (checks.py) and
# the checks split out of it can use it without importing each other.
#
# DEPENDENCY: standard library only.
# =============================================================================
"""The sentinel for a check that passed without checking anything."""
from __future__ import annotations


class _NothingToCheck(int):
    """A pass that checked nothing, distinguishable from one that did.

    A check passes without checking anything when the thing it inspects does not exist in
    this project - no BDD runner wired, no claims recorded, no project
    guardrails declared. That is a legitimate pass, but counting it beside a
    real one lets the summary overstate what was checked.

    It subclasses int and is truthy, so every existing `if not passed` and
    every caller that only cares pass/fail keeps working untouched; only the
    summary asks whether a result `is NOTHING_TO_CHECK`.
    """

    def __repr__(self):
        return "NOTHING_TO_CHECK"


NOTHING_TO_CHECK = _NothingToCheck(1)
