#!/usr/bin/env bash
# =============================================================================
# Compass hook: stop.sh  -  END-OF-SESSION GATE-STATE WARNER
# =============================================================================
# Runs as a Claude Code Stop hook, when a session ends. It does not block - a
# session is allowed to end. It exists to make sure a half-finished issue is
# LOUD on the way out, so the next session (or a human) does not have to
# rediscover that something was left dangling.
#
# WHAT IT CHECKS, per issue under .compass/work/
#   1. the delivery-approach record missing on in-progress work
#        => an issue directory exists but has no delivery-approach.md.
#           CLAUDE.md's one rule is "Never skip triage" - work with no
#           computed approach is unaccountable, warned loudly.
#   2. a stage left mid-gate
#        => a still-present .red marker means implementation is unfinished (a
#           failing test is on record and was never taken green). The
#           test-and-review stage cannot have passed cleanly.
#        => artifacts present out of order, or a verification-report.md whose
#           gate decision is RED / blank, mean test-and-review was entered and
#           not cleared.
#   3. a hotfix with an outstanding follow-up
#        => the delivery-approach record names a hotfix and its outstanding
#           follow-ups section still has an unchecked item, or
#           acceptance-criteria.md still lacks the promoted reproduction
#           scenario.
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

# shellcheck source=../scripts/lib/compass-python.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/lib/compass-python.sh"

cat >/dev/null || true   # drain stdin; we do not need it

# A warner that cannot read has nothing to warn about.
#
# `set -e` above means any failing `compass_python` in a command substitution
# takes this script down with its status - so a machine with no python3 got
# exit 127 at the end of every session. That is a crash, not a warning, and a
# crash at session end is noise nobody can act on.
#
# Note the asymmetry with hooks/pre-tool.sh, which is deliberate: a hook that
# cannot CHECK must not permit, so it refuses; a warner that cannot READ has
# nothing to say, so it stands down. Same missing interpreter, opposite
# correct answers.
if ! compass_python -c "pass" >/dev/null 2>&1; then
  echo "Compass: python3 is not available, so the end-of-session check did not run." >&2
  exit 0
fi

# Same ancestor walk as hooks/pre-tool.sh. A bare $(pwd) assumed the session
# started at the repository root; started anywhere else this hook found no
# .compass/work/, exited 0, and a silent warner is exactly what a clean
# session looks like. Every gate-state warning disappeared with no trace.
#
# A warner must not refuse - it says so rather than blocking - but it says so.
INVOKED_FROM="$(pwd)"
if [ -n "${CLAUDE_PROJECT_DIR:-}" ]; then
  PROJECT_DIR="$CLAUDE_PROJECT_DIR"
else
  PROJECT_DIR=""
  _search="$INVOKED_FROM"
  while [ -n "$_search" ]; do
    [ -d "$_search/.compass" ] && { PROJECT_DIR="$_search"; break; }
    [ -e "$_search/.git" ] && break
    [ "$_search" = "/" ] && break
    _search="$(dirname "$_search")"
  done
  if [ -z "$PROJECT_DIR" ]; then
    # A repository that never opted into Compass hears nothing. This hook is
    # installed at user scope, so it runs at the end of every session on the
    # machine, and a warner with nothing to warn about should be silent.
    # It never blocked - it always exits 0 - but it spoke, which is enough to
    # make Compass look like it has installed itself into someone's unrelated
    # work.
    exit 0
  fi
fi
COMPASS_DIR="$PROJECT_DIR/.compass"
WORK_DIR="$COMPASS_DIR/work"
[ -d "$WORK_DIR" ] || exit 0

WARNINGS=()

# --- 0. the current-task pointer should resolve -----------------------------
# The hooks and the CLI rely on .compass/current-task. A dangling pointer is a
# quiet way for the wrong issue to be acted on next session.
POINTER="$COMPASS_DIR/current-task"
if [ -f "$POINTER" ]; then
  PSLUG="$(tr -d '[:space:]' < "$POINTER" 2>/dev/null || true)"
  if [ -n "$PSLUG" ] && [ ! -d "$WORK_DIR/$PSLUG" ]; then
    WARNINGS+=(".compass/current-task points at '$PSLUG' but no such issue directory exists - fix or clear the pointer.")
  fi
fi

for TASK_DIR in "$WORK_DIR"/*/; do
  [ -d "$TASK_DIR" ] || continue
  TASK_DIR="${TASK_DIR%/}"
  SLUG="$(basename "$TASK_DIR")"

  ROUTE="$TASK_DIR/delivery-approach.md"
  # An archive written before the artifact rename still uses the old name.
  # vocabulary-scan: allow - names the retired filename on purpose
  [ -f "$ROUTE" ] || ROUTE="$TASK_DIR/route.md"
  SPEC="$TASK_DIR/acceptance-criteria.md"
  # An archive written before the artifact rename still uses the old name.
  # vocabulary-scan: allow - names the retired filename on purpose
  [ -f "$SPEC" ] || SPEC="$TASK_DIR/spec.feature.md"
  VREPORT="$TASK_DIR/verification-report.md"
  RED_MARKER="$TASK_DIR/.red"

  # --- 1. the delivery-approach record missing on in-progress work ----------
  if [ ! -f "$ROUTE" ]; then
    # A work dir with no delivery-approach record and no other artifacts may
    # just be an empty scaffold; but if anything else is in it, work started
    # without triage.
    if [ -n "$(ls -A "$TASK_DIR" 2>/dev/null)" ]; then
      WARNINGS+=("[$SLUG] the delivery-approach record is MISSING but the issue has artifacts - work started without triage. Run /compass:assess.")
    fi
    continue
  fi

  # --- 2. a phase left mid-gate --------------------------------------------
  # An unresolved red: implementation never closed.
  if [ -f "$RED_MARKER" ]; then
    WARNINGS+=("[$SLUG] .red marker still present - a failing test is on record and was never paid off green. implementation is mid-gate.")
  fi

  # Verify entered but not cleared.
  #
  # The separator between "FAIL" and the phrase after it is matched as
  # "one or more non-alphanumeric characters" rather than a literal dash.
  # Reports written before this repo swapped em dashes for hyphens are still
  # on disk in projects using Compass, and both spellings must be recognised.
  # POSIX character classes rather than \s, so this also runs under BSD grep.
  if [ -f "$VREPORT" ]; then
    # vocabulary-scan: allow - matches the retired wording in older reports too
    if grep -qiE 'Overall:.*\bRED\b|Overall:.*FAIL|FAIL[^[:alnum:]]+(issue|task) does not advance' "$VREPORT" 2>/dev/null; then
      WARNINGS+=("[$SLUG] verification-report.md records a FAILING gate decision - test-and-review did not pass. The issue is mid-gate.")
    elif ! grep -qiE 'Overall:.*PASS' "$VREPORT" 2>/dev/null; then
      WARNINGS+=("[$SLUG] verification-report.md exists but its gate decision is blank - test-and-review was entered and not completed.")
    fi
  fi

  # --- 3. a hotfix with an outstanding follow-up ---------------------------
  #
  # Both facts come from manifest.yml, not from the prose record. Grepping the
  # record for a heading is how this check died twice: it looked for
  # a heading the template had already replaced, and a
  # later repair pointed it at "Outstanding follow-ups" while the template
  # writes "Owed follow-ups". Neither failure was visible - the block simply
  # stopped firing. scripts/swarm.sh makes the same argument about the
  # worktree cap and refuses to fall back to prose for exactly this reason.
  HOTFIX_STATE="$(compass_python - "$TASK_DIR/manifest.yml" 2>/dev/null <<'PYSTOP'
import sys
import compass_pkg          # side effect: the bundled PyYAML resolves first
import yaml
try:
    with open(sys.argv[1], encoding="utf-8") as fh:
        task = yaml.safe_load(fh) or {}
except OSError:
    raise SystemExit(0)
if not isinstance(task, dict):
    raise SystemExit(0)
approach = str(task.get("delivery_approach") or "")
outstanding = [
    f for f in (task.get("follow_ups") or [])
    if isinstance(f, dict) and str(f.get("status", "")) in ("outstanding", "owed")
]
print(approach + "|" + str(len(outstanding)))
PYSTOP
)"
  if [ "${HOTFIX_STATE%%|*}" = "hotfix" ]; then

    if [ "${HOTFIX_STATE#*|}" != "0" ]; then
      WARNINGS+=("[$SLUG] HOTFIX with ${HOTFIX_STATE#*|} OUTSTANDING FOLLOW-UP(S) recorded in manifest.yml. The issue is not closeable until they are resolved.")
    fi

    # The reproduction test must have been promoted into a real scenario.
    if [ -f "$SPEC" ]; then
      if ! grep -qiE 'reproduc|regression|defect|incident' "$SPEC" 2>/dev/null; then
        WARNINGS+=("[$SLUG] HOTFIX follow-up incomplete - acceptance-criteria.md has no promoted reproduction scenario yet.")
      fi
    else
      WARNINGS+=("[$SLUG] HOTFIX follow-up incomplete - acceptance-criteria.md does not exist; the reproduction test was never promoted to a scenario.")
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
# For each scope_bloat_phrase, greps the current issue's devlog.md.
# The regex anchors the phrase at the start of the line (no leading whitespace
# beyond the line start) - this prevents false positives when the phrase
# appears inside a block-quote (`> "..."`) or inside backtick code context,
# where the line begins with whitespace or special characters (TRC-X3).
#
# Suppression rule: if manifest.yml contains a `reframes:` entry whose `date`
# field sorts lexicographically after the date prefix of the matching devlog
# line, the nudge is suppressed - the reframe was already filed (TRC-C3).
#
# This block is NON-BLOCKING: it always exits 0.
_nudge_scope_bloat() {
  local task_dir="$1"
  local slug
  slug="$(basename "$task_dir")"
  local devlog="$task_dir/devlog.md"
  local task_yml="$task_dir/manifest.yml"

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
  phrases="$(compass_python - "$signals" <<'PYEOF'
import sys
import compass_pkg
import yaml
sig = yaml.safe_load(open(sys.argv[1]))
phrases = sig.get("scope_bloat_phrases") or []
for p in phrases:
    print(p)
PYEOF
)" || return 0

  # Extract the latest reframe date from manifest.yml (if any).
  local latest_reframe_date
  latest_reframe_date="$(compass_python - "$task_yml" <<'PYEOF'
import sys
import compass_pkg
import yaml
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
      echo "    /compass:assess --reassess --reason \"<what changed and why>\""
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
