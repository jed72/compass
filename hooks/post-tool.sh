#!/usr/bin/env bash
# =============================================================================
# Compass hook: post-tool.sh  -  DEVLOG APPENDER
# =============================================================================
# Runs as a Claude Code PostToolUse hook, after an Edit/Write/MultiEdit tool
# call completes. It does ONE lightweight thing: appends a short line to the
# current issue's devlog.md, so "persistence over conversation" holds without
# the agent having to remember to log every touch.
#
# WHAT IT DOES NOT DO (any more)
#   It does not run the test suite, and it does not clear the .red marker. That
#   is now `compass tdd-green`'s job - and the CLI does it honestly: it runs the
#   test, confirms it passes, writes evidence/green.json, and only then clears
#   .red. A hook quietly running a discovered test command and clearing the
#   marker was the brittle, trust-based version; the CLI replaces it with an
#   evidence-backed one. This hook stays out of that.
#
# THE CURRENT ISSUE
#   Named by the .compass/current-task pointer (written by /compass:triage and
#   /compass:resume); most-recently-modified is only the fallback.
#
# WIRING  (.claude/settings.json)
#   {
#     "hooks": {
#       "PostToolUse": [
#         { "matcher": "Edit|Write|MultiEdit",
#           "hooks": [ { "type": "command",
#                        "command": "$CLAUDE_PROJECT_DIR/hooks/post-tool.sh" } ] }
#       ]
#     }
#   }
#   `scripts/install.sh` registers this for you.
#
# I/O CONTRACT
#   stdin : JSON describing the completed tool call.
#   exit  : always 0. This hook is advisory; it never blocks.
# =============================================================================

set -euo pipefail

INPUT="$(cat || true)"
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
COMPASS_DIR="$PROJECT_DIR/.compass"
WORK_DIR="$COMPASS_DIR/work"

# Nothing to do if Compass is not initialised for this project.
[ -d "$WORK_DIR" ] || exit 0

# --- extract the tool call details ------------------------------------------
if command -v jq >/dev/null 2>&1; then
  TARGET="$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // .tool_input.path // empty' 2>/dev/null || true)"
  TOOL="$(printf '%s' "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null || true)"
else
  TARGET="$(printf '%s' "$INPUT" | grep -oE '"file_path"[[:space:]]*:[[:space:]]*"[^"]*"' | head -n1 | sed -E 's/.*:[[:space:]]*"([^"]*)"/\1/' || true)"
  TOOL="$(printf '%s' "$INPUT" | grep -oE '"tool_name"[[:space:]]*:[[:space:]]*"[^"]*"' | head -n1 | sed -E 's/.*:[[:space:]]*"([^"]*)"/\1/' || true)"
fi
[ -z "${TARGET:-}" ] && exit 0

# Ignore edits to Compass's own artifacts - they are not "the work", they are
# the record of it, and the devlog logs the work.
case "$TARGET" in
  *.compass/*|*/.compass/*) exit 0 ;;
esac

# --- find the current issue (pointer first, most-recent as fallback) --------
TASK_DIR=""
POINTER="$COMPASS_DIR/current-task"
if [ -f "$POINTER" ]; then
  SLUG="$(tr -d '[:space:]' < "$POINTER" 2>/dev/null || true)"
  if [ -n "$SLUG" ] && [ -d "$WORK_DIR/$SLUG" ]; then
    TASK_DIR="$WORK_DIR/$SLUG"
  fi
fi
if [ -z "$TASK_DIR" ]; then
  TASK_DIR="$(ls -dt "$WORK_DIR"/*/ 2>/dev/null | head -n1 || true)"
  TASK_DIR="${TASK_DIR%/}"
fi
[ -z "${TASK_DIR:-}" ] && exit 0

DEVLOG="$TASK_DIR/devlog.md"
NOW="$(date '+%Y-%m-%d %H:%M')"

# --- append a devlog line ---------------------------------------------------
# devlog.md is append-only; we only ever add to the bottom.
if [ -f "$DEVLOG" ]; then
  {
    printf '\n## %s - edit: %s\n\n' "$NOW" "$TARGET"
    printf -- '- **Tool:** %s\n' "${TOOL:-edit}"
  } >> "$DEVLOG"
fi

exit 0
