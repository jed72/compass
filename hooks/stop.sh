#!/usr/bin/env bash
# =============================================================================
# Compass hook: stop.sh  -  END-OF-SESSION GATE-STATE WARNER
# =============================================================================
# Runs as a Claude Code Stop hook, when a session ends. It does not block - a
# session is allowed to end. It exists to make sure a half-finished task is
# LOUD on the way out, so the next session (or a human) does not have to
# rediscover that something was left dangling.
#
# WHAT IT CHECKS, per task under .compass/work/
#   1. route.md missing on in-progress work
#        => a task directory exists but has no route.md. CLAUDE.md's one rule
#           is "Never skip Frame" - work with no computed route is
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
#   stdin : JSON session-stop payload (unused - we inspect disk state).
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
    WARNINGS+=(".compass/current-task points at '$PSLUG' but no such task directory exists - fix or clear the pointer.")
  fi
fi

for TASK_DIR in "$WORK_DIR"/*/; do
  [ -d "$TASK_DIR" ] || continue
  TASK_DIR="${TASK_DIR%/}"
  SLUG="$(basename "$TASK_DIR")"

  ROUTE="$TASK_DIR/delivery-approach.md"
  [ -f "$ROUTE" ] || ROUTE="$TASK_DIR/route.md"
  SPEC="$TASK_DIR/spec.feature.md"
  VREPORT="$TASK_DIR/verification-report.md"
  RED_MARKER="$TASK_DIR/.red"

  # --- 1. route.md missing on in-progress work ------------------------------
  if [ ! -f "$ROUTE" ]; then
    # A work dir with no route.md and no other artifacts may just be an empty
    # scaffold; but if anything else is in it, work started without Frame.
    if [ -n "$(ls -A "$TASK_DIR" 2>/dev/null)" ]; then
      WARNINGS+=("[$SLUG] route.md is MISSING but the task has artifacts - work started without Frame. Run /compass:triage.")
    fi
    continue
  fi

  # --- 2. a phase left mid-gate --------------------------------------------
  # Unpaid red: Build never closed.
  if [ -f "$RED_MARKER" ]; then
    WARNINGS+=("[$SLUG] .red marker still present - a failing test is on record and was never paid off green. Build is mid-gate.")
  fi

  # Verify entered but not cleared.
  #
  # The separator between "FAIL" and "task does not advance" is matched as
  # "one or more non-alphanumeric characters" rather than a literal dash.
  # Reports written before this repo swapped em dashes for hyphens are still
  # on disk in projects using Compass, and both spellings must be recognised.
  # POSIX character classes rather than \s, so this also runs under BSD grep.
  if [ -f "$VREPORT" ]; then
    if grep -qiE 'Overall:.*\bRED\b|Overall:.*FAIL|FAIL[^[:alnum:]]+task does not advance' "$VREPORT" 2>/dev/null; then
      WARNINGS+=("[$SLUG] verification-report.md records a FAILING gate decision - Verify did not pass. Task is mid-gate.")
    elif ! grep -qiE 'Overall:.*PASS' "$VREPORT" 2>/dev/null; then
      WARNINGS+=("[$SLUG] verification-report.md exists but its gate decision is blank - Verify was entered and not completed.")
    fi
  fi

  # --- 3. a Hotfix with an unpaid backfill ---------------------------------
  #
  # Same reasoning as above: a route.md heading is "Route <sep> Hotfix", and
  # the separator is matched loosely so route files written with an em dash
  # (every one produced before this repo's style sweep) still match.
  if grep -qiE 'reference route:.*hotfix|Route[^[:alnum:]]+.*[Hh]otfix|nearest reference route.*[Hh]otfix' "$ROUTE" 2>/dev/null \
     || grep -qiE '^[[:space:]]*Route[^[:alnum:]]+Hotfix' "$ROUTE" 2>/dev/null; then

    # An unchecked item in the "Owed backfills" section is an unpaid backfill.
    # We scan the section for "- [ ]" lines that are not the "none owed" line.
    if awk '
        /^##? *.*[Oo]wed [Bb]ackfills/ { insec=1; next }
        /^##? / && insec { insec=0 }
        insec && /- \[ \]/ && tolower($0) !~ /none owed/ { found=1 }
        END { exit(found?0:1) }
      ' "$ROUTE" 2>/dev/null; then
      WARNINGS+=("[$SLUG] HOTFIX with an UNPAID BACKFILL - route.md's Owed backfills section has an unchecked item. The task is not closeable until the backfill is paid.")
    fi

    # The reproduction test must have been promoted into a real scenario.
    if [ -f "$SPEC" ]; then
      if ! grep -qiE 'reproduc|regression|defect|incident' "$SPEC" 2>/dev/null; then
        WARNINGS+=("[$SLUG] HOTFIX backfill incomplete - spec.feature.md has no promoted reproduction scenario yet.")
      fi
    else
      WARNINGS+=("[$SLUG] HOTFIX backfill incomplete - spec.feature.md does not exist; the reproduction test was never promoted to a scenario.")
    fi
  fi
done

# --- emit gate-state warnings ------------------------------------------------
if [ "${#WARNINGS[@]}" -gt 0 ]; then
  {
    echo ""
    echo "================================================================"
    echo " COMPASS - SESSION ENDING WITH OPEN GATE STATE"
    echo "================================================================"
    for w in "${WARNINGS[@]}"; do
      echo "  ! $w"
    done
    echo "----------------------------------------------------------------"
    echo "  Run /compass:status next session to pick these up cleanly."
    echo "  Nothing here blocked the stop - but nothing here is finished."
    echo "================================================================"
    echo ""
  } >&2
fi

# --- 4. scope-bloat reframe nudge -------------------------------------------
# Reads governance/signals.yml at runtime; the patterns are never hardcoded.
# For each scope_bloat_phrase, greps the current task's devlog.md.
# The regex anchors the phrase at the start of the line (no leading whitespace
# beyond the line start) - this prevents false positives when the phrase
# appears inside a block-quote (`> "..."`) or inside backtick code context,
# where the line begins with whitespace or special characters (TRC-X3).
#
# Suppression rule: if task.yml contains a `reframes:` entry whose `date`
# field sorts lexicographically after the date prefix of the matching devlog
# line, the nudge is suppressed - the reframe was already filed (TRC-C3).
#
# This block is NON-BLOCKING: it always exits 0.
_nudge_scope_bloat() {
  local task_dir="$1"
  local slug
  slug="$(basename "$task_dir")"
  local devlog="$task_dir/devlog.md"
  local task_yml="$task_dir/task.yml"

  [ -f "$devlog" ] || return 0
  [ -f "$task_yml" ] || return 0

  # Locate governance/signals.yml - project-local first, then framework default.
  local signals=""
  if [ -f "$PROJECT_DIR/governance/signals.yml" ]; then
    signals="$PROJECT_DIR/governance/signals.yml"
  else
    # Walk up from the hook's own directory to find the framework's shipped copy.
    local hook_dir
    hook_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local fw_root
    fw_root="$(dirname "$hook_dir")"
    if [ -f "$fw_root/governance/signals.yml" ]; then
      signals="$fw_root/governance/signals.yml"
    fi
  fi
  [ -n "$signals" ] || return 0

  # Extract scope_bloat_phrases using Python (lightest dependency - already
  # required by the CLI for PyYAML). Python is guaranteed present if the
  # Compass CLI has ever run.
  local phrases
  phrases="$(python3 - "$signals" <<'PYEOF'
import sys, yaml
sig = yaml.safe_load(open(sys.argv[1]))
phrases = sig.get("scope_bloat_phrases") or []
for p in phrases:
    print(p)
PYEOF
)" || return 0

  # Extract the latest reframe date from task.yml (if any).
  local latest_reframe_date
  latest_reframe_date="$(python3 - "$task_yml" <<'PYEOF'
import sys, yaml
task = yaml.safe_load(open(sys.argv[1])) or {}
entries = (task.get("reassessments") or task.get("reframes") or [])
dates = [r.get("date","") for r in entries if r.get("date")]
print(max(dates) if dates else "")
PYEOF
)" || latest_reframe_date=""

  local nudges=()
  while IFS= read -r phrase; do
    [ -n "$phrase" ] || continue

    # Anchor: phrase must appear as a top-level statement - either at column 0
    # or immediately after an optional YYYY-MM-DD[: ] date prefix at column 0.
    # Lines starting with whitespace are excluded (they are indented/quoted
    # context that must not fire - TRC-X3).
    #
    # We use Python for the regex so that the pattern is applied uniformly with
    # the calibration CLI (both use the same anchoring rule).
    local matched_line
    matched_line="$(python3 - "$devlog" "$phrase" <<'PYEOF'
import sys, re
devlog, phrase = sys.argv[1], sys.argv[2]
pat = re.compile(r'^(?:\d{4}-\d{2}-\d{2}[: ]+)?' + re.escape(phrase))
with open(devlog) as fh:
    for line in fh:
        stripped = line.rstrip('\n')
        if stripped and stripped[0].isspace():
            continue  # leading whitespace = quoted/indented context
        if pat.match(stripped):
            print(stripped)
            break
PYEOF
)" || true
    [ -n "$matched_line" ] || continue

    # Extract a date from the matched line (YYYY-MM-DD at line start, if present).
    local line_date
    line_date="$(echo "$matched_line" | grep -oE '^[0-9]{4}-[0-9]{2}-[0-9]{2}' || true)"

    # Suppression: if there is a reframe dated >= the line date, skip.
    if [ -n "$latest_reframe_date" ] && [ -n "$line_date" ]; then
      if [[ "$latest_reframe_date" > "$line_date" ]] || [[ "$latest_reframe_date" == "$line_date" ]]; then
        continue
      fi
    elif [ -n "$latest_reframe_date" ] && [ -z "$line_date" ]; then
      # Can't compare - a reframe exists and the line has no date; suppress.
      continue
    fi

    nudges+=("[$slug] Scope-bloat signal detected in devlog: \"$matched_line\"")
  done <<< "$phrases"

  if [ "${#nudges[@]}" -gt 0 ]; then
    {
      echo ""
      echo "================================================================"
      echo " COMPASS - REFRAME NUDGE"
      echo "================================================================"
      echo "  The following scope-bloat signals were found in devlog.md"
      echo "  but no reframe has been filed after them:"
      echo ""
      for n in "${nudges[@]}"; do
        echo "  ! $n"
      done
      echo ""
      echo "  If the scope grew during Build, file a reframe now:"
      echo "    /compass:triage --reassess --reason \"<what changed and why>\""
      echo ""
      echo "  This preserves the calibration signal (compass retro)."
      echo "  The nudge is non-blocking - the session ends regardless."
      echo "================================================================"
      echo ""
    } >&2
  fi
}

for TASK_DIR in "$WORK_DIR"/*/; do
  [ -d "$TASK_DIR" ] || continue
  TASK_DIR="${TASK_DIR%/}"
  _nudge_scope_bloat "$TASK_DIR"
done

exit 0
