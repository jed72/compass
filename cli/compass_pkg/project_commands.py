#!/usr/bin/env python3
# =============================================================================
# compass - project command policy
# =============================================================================
# Whether Compass runs a command a project guardrail declared, and where that
# command's script is allowed to live. Split out of checks.py, which is the
# check registry: this is the policy those checks apply, and it is easier to
# read - and to argue with - on its own.
#
# This module reads the PROJECT's own configuration, which means everything it
# decides is repository-controlled. That is fine for what it does: it is a
# defence against accidents and defaults, not against an attacker. The security
# decision lives in trust.py, is read first, and reads nothing from here.
#
# DEPENDENCY: PyYAML, bundled at cli/vendor/yaml/ and pinned in
# THIRD-PARTY-NOTICES.md. It is resolved by compass_pkg/__init__.py and is
# the only third-party code Compass ships; everything else is the Python 3
# standard library. This module reaches it only indirectly, through the shared
# config reader in compass_pkg.tdd.
# =============================================================================
"""Policy for running commands a project guardrail declares."""
from __future__ import annotations

import os

from compass_pkg.tdd import _read_config


def _project_commands_allowed(task_dir):
    """Has this project opted in to running commands its guardrails declare?

    Default false. Lives in .compass/config.yml rather than in
    governance/guardrails.yml, because that file is the thing being constrained
    and a declaration should not be able to authorise itself.

    This is NOT a security control: the file is in the repository, so a
    contribution can set it. It defends against accidents and defaults. The
    security control is the trust decision in cli/compass_pkg/trust.py, which
    is read first and reads nothing this file could influence.
    """
    value = _read_config(task_dir).get("allow_project_commands", False)
    if isinstance(value, str):
        return value.strip().lower() in ("true", "yes", "1", "on")
    return bool(value)


def _contained_script(script, project_root):
    """Resolve a declared script path, or None if it escapes the project.

    The comparison is made on the REAL path - symlinks resolved - because a
    symlink sitting inside the project and pointing out of it satisfies any
    check made on the string as written. A path check a symlink defeats is not
    a boundary.
    """
    if not isinstance(script, str) or not script.strip():
        return None
    root = os.path.realpath(project_root)
    candidate = os.path.realpath(os.path.join(root, script))
    if candidate != root and not candidate.startswith(root + os.sep):
        return None
    if not os.path.isfile(candidate):
        return None
    return candidate
