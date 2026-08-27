#!/usr/bin/env bash
# =============================================================================
# Compass hook: session-start.sh  -  PUT THE OPERATING CONTRACT IN THE SESSION
# =============================================================================
# Runs as a Claude Code SessionStart hook, on startup, clear and compact.
#
# WHY IT EXISTS
#   The contract only ever reached a session if the model chose to load the
#   `compass-runtime` skill from its description. CLAUDE.md applies inside the
#   Compass repository and nowhere else, so an adopter's session got nothing
#   and Compass's own rules were invisible to the model meant to follow them.
#
# WHAT IT DOES
#   Prints a JSON object carrying the contract as `additionalContext`, which
#   Claude Code adds to the session. It never blocks - a SessionStart hook has
#   nothing to refuse - so every path here exits 0.
#
# THE BOUNDARY
#   A repository with no .compass/ has never opted into Compass, and this hook
#   is installed at user scope: it starts in every session on the machine.
#   There it prints nothing at all. Same rule as hooks/pre-tool.sh, minus the
#   half that cannot apply - there is no fail-closed case here, because there
#   is no gate to close.
#
# WHERE THE CONTRACT LIVES
#   compass-contract.md at the framework root, and only there. CLAUDE.md and
#   skills/compass-runtime/SKILL.md point at it. Before this, those two
#   restated it: 46 sentences appeared verbatim in both, and they had already
#   drifted - the skill named nine agents, having lost `architect`.
# =============================================================================
set -uo pipefail

# The contract ships with the framework, so it is found from this script's own
# location. That is right here and wrong in pre-tool.sh: this hook reads a file
# the PLUGIN owns, where that one resolves a project the USER owns and must
# never reach for its own tree instead.
FRAMEWORK_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONTRACT="$FRAMEWORK_ROOT/compass-contract.md"

INVOKED_FROM="$(pwd)"
if [ -n "${CLAUDE_PROJECT_DIR:-}" ]; then
  PROJECT_DIR="$CLAUDE_PROJECT_DIR"
else
  PROJECT_DIR=""
  _search="$INVOKED_FROM"
  while [ -n "$_search" ]; do
    [ -d "$_search/.compass" ] && { PROJECT_DIR="$_search"; break; }
    # The repository is the outer bound. Walking past it would inject the
    # contract because a stranger's project happens to sit above this one.
    [ -e "$_search/.git" ] && break
    [ "$_search" = "/" ] && break
    _search="$(dirname "$_search")"
  done
  [ -n "$PROJECT_DIR" ] || exit 0
fi

# Not a Compass project: say nothing. An explicit CLAUDE_PROJECT_DIR is the
# runtime naming a directory, not a statement that Compass lives in it - the
# runtime sets it for every repository, which is what made the pre-tool hook
# refuse edits everywhere before hook-as-guest.
[ -d "$PROJECT_DIR/.compass" ] || exit 0

[ -f "$CONTRACT" ] || exit 0

# Emitted as JSON by python3, which is how the rest of the kit reads and writes
# JSON. A hand-rolled escape here would break on the first apostrophe in the
# contract. With no python3 the session simply starts without it: degrading
# quietly is right for a hook that only ever ADDS context, and is the opposite
# of the rule in pre-tool.sh, where a hook that cannot check must not permit.
command -v python3 >/dev/null 2>&1 || exit 0

python3 - "$CONTRACT" <<'PY' 2>/dev/null || exit 0
import json
import sys

with open(sys.argv[1], encoding="utf-8") as fh:
    contract = fh.read()

print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": contract,
    }
}))
PY
