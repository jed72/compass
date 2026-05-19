#!/usr/bin/env bash
# =============================================================================
# Compass hook: stop.sh  —  END-OF-SESSION GATE-STATE WARNER
# =============================================================================
# Runs as a Claude Code Stop hook, when a session ends. It does not block — a
# session is allowed to end. It exists to make sure a half-finished task is
# LOUD on the way out, so the next session (or a human) does not have to
# rediscover that something was left dangling.
#
# WHAT IT CHECKS, per task under .compass/work/
#   1. route.md missing on in-progress work
#        => a task directory exists but has no route.md. CLAUDE.md's one rule
#           is "Never skip Frame" — work with no computed route is
#           unaccountable, warned loudly.
#   2. a phase left mid-gate
#        => a still-present .red marker means Build is unfinished (a failing
#           test is on record and was never paid off green). Verify cannot
#           have passed cleanly.
#        => artifacts present out of order, or a verification-report.md whose
#           gate decision is RED / blank, mean Verify was entered and not
#           cleared.
#   3. a Hotfix with an unpaid backfill
#        => route.md names the route Hotfix and its "Owed backfills" section
#           still has an unchecked item, or spec.feature.md still lacks the
#           promoted reproduction scenario.
#
# This mirrors what /compass:status reports, but fires automatically at session
# end so nothing silently rots.
#
# WIRING  (.claude/settings.json)
#   {
#     "hooks": {
#       "Stop": [
#         { "hooks": [ { "type": "command",
#                        "command": "$CLAUDE_PROJECT_DIR/hooks/stop.sh" } ] }
#       ]
#     }
#   }
#   `scripts/install.sh` registers this for you.
#
# I/O CONTRACT
#   stdin : JSON session-stop payload (unused — we inspect disk state).
#   exit  : always 0. Warnings go to stderr. This hook never blocks a stop.
# =============================================================================

set -euo pipefail

cat >/dev/null || true   # drain stdin; we do not need it

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
COMPASS_DIR="$PROJECT_DIR/.compass"
WORK_DIR="$COMPASS_DIR/work"
[ -d "$WORK_DIR" ] || exit 0

WARNINGS=()

# --- 0. the current-task pointer should resolve -----------------------------
# The hooks and the CLI rely on .compass/current-task. A dangling pointer is a
# quiet way for the wrong task to be acted on next session.
POINTER="$COMPASS_DIR/current-task"
if [ -f "$POINTER" ]; then
  PSLUG="$(tr -d '[:space:]' < "$POINTER" 2>/dev/null || true)"
  if [ -n "$PSLUG" ] && [ ! -d "$WORK_DIR/$PSLUG" ]; then
    WARNINGS+=(".compass/current-task points at '$PSLUG' but no such task directory exists — fix or clear the pointer.")
  fi
fi

for TASK_DIR in "$WORK_DIR"/*/; do
  [ -d "$TASK_DIR" ] || continue
  TASK_DIR="${TASK_DIR%/}"
  SLUG="$(basename "$TASK_DIR")"

  ROUTE="$TASK_DIR/route.md"
  SPEC="$TASK_DIR/spec.feature.md"
  VREPORT="$TASK_DIR/verification-report.md"
  RED_MARKER="$TASK_DIR/.red"

  # --- 1. route.md missing on in-progress work ------------------------------
  if [ ! -f "$ROUTE" ]; then
    # A work dir with no route.md and no other artifacts may just be an empty
    # scaffold; but if anything else is in it, work started without Frame.
    if [ -n "$(ls -A "$TASK_DIR" 2>/dev/null)" ]; then
      WARNINGS+=("[$SLUG] route.md is MISSING but the task has artifacts — work started without Frame. Run /compass:frame.")
    fi
    continue
  fi

  # --- 2. a phase left mid-gate --------------------------------------------
  # Unpaid red: Build never closed.
  if [ -f "$RED_MARKER" ]; then
    WARNINGS+=("[$SLUG] .red marker still present — a failing test is on record and was never paid off green. Build is mid-gate.")
  fi

  # Verify entered but not cleared.
  if [ -f "$VREPORT" ]; then
    if grep -qiE 'Overall:.*\bRED\b|Overall:.*FAIL|FAIL — task does not advance' "$VREPORT" 2>/dev/null; then
      WARNINGS+=("[$SLUG] verification-report.md records a FAILING gate decision — Verify did not pass. Task is mid-gate.")
    elif ! grep -qiE 'Overall:.*PASS' "$VREPORT" 2>/dev/null; then
      WARNINGS+=("[$SLUG] verification-report.md exists but its gate decision is blank — Verify was entered and not completed.")
    fi
  fi

  # --- 3. a Hotfix with an unpaid backfill ---------------------------------
  if grep -qiE 'reference route:.*hotfix|Route — .*[Hh]otfix|nearest reference route.*[Hh]otfix' "$ROUTE" 2>/dev/null \
     || grep -qiE '^\s*Route — Hotfix' "$ROUTE" 2>/dev/null; then

    # An unchecked item in the "Owed backfills" section is an unpaid backfill.
    # We scan the section for "- [ ]" lines that are not the "none owed" line.
    if awk '
        /^##? *.*[Oo]wed [Bb]ackfills/ { insec=1; next }
        /^##? / && insec { insec=0 }
        insec && /- \[ \]/ && tolower($0) !~ /none owed/ { found=1 }
        END { exit(found?0:1) }
      ' "$ROUTE" 2>/dev/null; then
      WARNINGS+=("[$SLUG] HOTFIX with an UNPAID BACKFILL — route.md's Owed backfills section has an unchecked item. The task is not closeable until the backfill is paid.")
    fi

    # The reproduction test must have been promoted into a real scenario.
    if [ -f "$SPEC" ]; then
      if ! grep -qiE 'reproduc|regression|defect|incident' "$SPEC" 2>/dev/null; then
        WARNINGS+=("[$SLUG] HOTFIX backfill incomplete — spec.feature.md has no promoted reproduction scenario yet.")
      fi
    else
      WARNINGS+=("[$SLUG] HOTFIX backfill incomplete — spec.feature.md does not exist; the reproduction test was never promoted to a scenario.")
    fi
  fi
done

# --- emit ---------------------------------------------------------------------
if [ "${#WARNINGS[@]}" -gt 0 ]; then
  {
    echo ""
    echo "================================================================"
    echo " COMPASS — SESSION ENDING WITH OPEN GATE STATE"
    echo "================================================================"
    for w in "${WARNINGS[@]}"; do
      echo "  ! $w"
    done
    echo "----------------------------------------------------------------"
    echo "  Run /compass:status next session to pick these up cleanly."
    echo "  Nothing here blocked the stop — but nothing here is finished."
    echo "================================================================"
    echo ""
  } >&2
fi

exit 0
