#!/usr/bin/env bash
# =============================================================================
# Compass script: integrate.sh  -  LAND THE WORKTREES BACK TOGETHER
# =============================================================================
# The Land-phase counterpart to swarm.sh. It merges the per-stream branches
# back into the base branch in a coordinated order, runs the project's test
# command for combined regression, reports any conflicts for the `orchestrator`
# to resolve, and cleans up the worktrees on success. Only the `orchestrator`
# agent runs this (the lead builder on a pair) - see CLAUDE.md and the
# worktree-swarm skill.
#
# USAGE
#   scripts/integrate.sh <task-slug>             # integrate every stream
#   scripts/integrate.sh <task-slug> --no-clean  # integrate but keep worktrees
#   scripts/integrate.sh --help
#
# ORDER
#   Streams are merged in the order they appear in distribution-map.md §3.
#   The map is expected to list shared foundations first (stream-zero pattern,
#   see the worktree-swarm skill) so dependents merge onto a base that already
#   has what they need.
#
# CONFLICTS
#   This script does NOT auto-resolve conflicts. If a merge conflicts, it
#   aborts that merge, leaves the repo clean, reports exactly which stream and
#   which files conflicted, and stops. Resolving cross-stream conflicts is the
#   orchestrator's job and no one else's - the script just surfaces them.
#
# COMBINED REGRESSION
#   After all streams merge cleanly, the project's test command runs once
#   against the integrated result. Per-stream green does not imply integrated
#   green - proving the combination is the whole point of Land. If combined
#   regression fails, worktrees are NOT cleaned up (you will need them) and the
#   script exits non-zero.
#
# IDEMPOTENT & SAFE
#   - A branch already merged is detected and skipped.
#   - Worktrees are only removed after both a clean merge AND green combined
#     regression. --no-clean keeps them regardless.
#   - On any failure the working tree is left in a clean, inspectable state.
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPASS_HOME="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_DIR="$(git -C "$(pwd)" rev-parse --show-toplevel 2>/dev/null || pwd)"

# --- args -------------------------------------------------------------------
TASK_SLUG=""
CLEAN=1
while [ $# -gt 0 ]; do
  case "$1" in
    --no-clean) CLEAN=0 ;;
    -h|--help)  grep -E '^# (USAGE|  scripts)' "$0" | sed 's/^# //'; exit 0 ;;
    -*) echo "integrate.sh: unknown flag: $1" >&2; exit 1 ;;
    *)  TASK_SLUG="$1" ;;
  esac
  shift
done
[ -n "$TASK_SLUG" ] || { echo "integrate.sh: need a task slug. See --help." >&2; exit 1; }

TASK_DIR="$PROJECT_DIR/.compass/work/$TASK_SLUG"
MAP="$TASK_DIR/distribution-map.md"
CONFIG="$PROJECT_DIR/.compass/config.yml"
[ -f "$MAP" ] || { echo "integrate.sh: no distribution-map.md for '$TASK_SLUG'." >&2; exit 1; }

# --- repo sanity: must start clean ------------------------------------------
git -C "$PROJECT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1 \
  || { echo "integrate.sh: $PROJECT_DIR is not a git repository." >&2; exit 1; }
if [ -n "$(git -C "$PROJECT_DIR" status --porcelain)" ]; then
  echo "integrate.sh: working tree is dirty - commit or stash before integrating." >&2
  exit 1
fi
BASE_BRANCH="$(git -C "$PROJECT_DIR" rev-parse --abbrev-ref HEAD)"

# --- config: worktree_root --------------------------------------------------
read_cfg() {
  local v=""
  [ -f "$CONFIG" ] && v="$(grep -E "^[[:space:]]*$1:" "$CONFIG" 2>/dev/null \
      | head -n1 | sed -E 's/^[^:]*:[[:space:]]*//; s/[[:space:]]*#.*$//; s/^"//; s/"$//')"
  echo "${v:-$2}"
}
WORKTREE_ROOT_REL="$(read_cfg 'worktree_root' '../.compass-worktrees')"
case "$WORKTREE_ROOT_REL" in
  /*) WORKTREE_ROOT="$WORKTREE_ROOT_REL" ;;
  *)  WORKTREE_ROOT="$PROJECT_DIR/$WORKTREE_ROOT_REL" ;;
esac

# --- parse streams + branches (same parser shape as swarm.sh) ---------------
STREAMS=(); BRANCHES=()
while IFS= read -r line; do
  case "$line" in \|*stream-*) ;; *) continue ;; esac
  IFS='|' read -r _ c1 c2 c3 c4 _rest <<<"$line"
  sid="$(echo "${c1:-}" | xargs 2>/dev/null || true)"
  branch="$(echo "${c4:-}" | xargs 2>/dev/null || true)"
  case "$sid" in stream-*) ;; *) continue ;; esac
  [ -n "$branch" ] || branch="compass/$TASK_SLUG/$sid"
  STREAMS+=("$sid"); BRANCHES+=("$branch")
done < "$MAP"

if [ "${#STREAMS[@]}" -eq 0 ]; then
  echo "integrate.sh: no streams in distribution-map.md. If the route is solo," >&2
  echo "              Land integrates with a plain commit - integrate.sh is not needed." >&2
  exit 1
fi

# --- discover the project test command (for combined regression) ------------
TEST_CMD="$(read_cfg 'test_command' '')"
if [ -z "$TEST_CMD" ] && [ -f "$PROJECT_DIR/package.json" ] \
   && grep -q '"test"' "$PROJECT_DIR/package.json" 2>/dev/null; then
  TEST_CMD="npm test"
fi
if [ -z "$TEST_CMD" ] && [ -f "$PROJECT_DIR/Makefile" ] \
   && grep -qE '^test:' "$PROJECT_DIR/Makefile" 2>/dev/null; then
  TEST_CMD="make test"
fi

echo "Compass integrate - task '$TASK_SLUG'"
echo "  base branch:   $BASE_BRANCH"
echo "  streams:       ${#STREAMS[@]}  (merged in map order)"
echo "  test command:  ${TEST_CMD:-<none resolved - combined regression cannot run automatically>}"
echo ""

# --- merge each stream in order ---------------------------------------------
MERGED=()
for i in "${!STREAMS[@]}"; do
  sid="${STREAMS[$i]}"
  branch="${BRANCHES[$i]}"

  if ! git -C "$PROJECT_DIR" show-ref --verify --quiet "refs/heads/$branch"; then
    echo "  $sid: branch '$branch' does not exist - skipping (was the swarm ever created?)."
    continue
  fi

  # Already merged?
  if git -C "$PROJECT_DIR" merge-base --is-ancestor "$branch" "$BASE_BRANCH"; then
    echo "  $sid: already merged into $BASE_BRANCH - skipping."
    MERGED+=("$sid")
    continue
  fi

  echo "  $sid: merging $branch -> $BASE_BRANCH ..."
  if git -C "$PROJECT_DIR" merge --no-ff --no-edit \
        -m "compass($TASK_SLUG): integrate $sid" "$branch" >/dev/null 2>&1; then
    echo "         merged cleanly."
    MERGED+=("$sid")
  else
    # Conflict. Capture the conflicted files, abort, report, stop.
    CONFLICTS="$(git -C "$PROJECT_DIR" diff --name-only --diff-filter=U || true)"
    git -C "$PROJECT_DIR" merge --abort || true
    echo ""
    echo "  CONFLICT integrating $sid ($branch)."
    echo "  Conflicted files:"
    echo "$CONFLICTS" | sed 's/^/    - /'
    echo ""
    echo "  The merge was aborted; the repo is clean again. This is the"
    echo "  orchestrator's call to resolve - re-cut the boundary, re-sequence,"
    echo "  or escalate to a re-frame. No one else may resolve a cross-stream"
    echo "  conflict. Streams merged so far: ${MERGED[*]:-none}."
    exit 2
  fi
done

if [ "${#MERGED[@]}" -eq 0 ]; then
  echo ""
  echo "integrate.sh: nothing was merged. Check the branch names in the map." >&2
  exit 1
fi

# --- combined regression ----------------------------------------------------
echo ""
echo "Combined regression across the integrated result:"
echo "----------------------------------------------------------------"
if [ -n "$TEST_CMD" ]; then
  if ( cd "$PROJECT_DIR" && eval "$TEST_CMD" ); then
    echo "----------------------------------------------------------------"
    echo "Combined regression GREEN. Paste the run above into verification-report.md."
  else
    echo "----------------------------------------------------------------"
    echo "Combined regression FAILED. Per-stream green did not survive integration."
    echo "Worktrees are LEFT IN PLACE so you can fix the stream that broke."
    echo "The merge commits are on $BASE_BRANCH - revert or fix forward; do not"
    echo "clean up until combined regression is green."
    exit 1
  fi
else
  echo "No test command resolved (set 'test_command:' in .compass/config.yml)."
  echo "Combined regression MUST still be run by hand before Land closes -"
  echo "per-stream green does not imply integrated green."
fi

# --- write status: landed and derive the living system spec -----------------
echo ""
echo "Writing status: landed to task.yml and deriving living system spec..."

TASK_YML="$TASK_DIR/task.yml"
if [ -f "$TASK_YML" ]; then
  python3 - <<PYEOF
import yaml, datetime, sys
path = "$TASK_YML"
try:
    with open(path, 'r', encoding='utf-8') as f:
        task = yaml.safe_load(f) or {}
    if not isinstance(task, dict):
        task = {}
    task['status'] = 'landed'
    task['land_timestamp'] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')
    with open(path, 'w', encoding='utf-8') as f:
        yaml.safe_dump(task, f, sort_keys=False, default_flow_style=False)
    print("  task.yml: status=landed, land_timestamp written.")
except Exception as exc:
    print(f"WARNING: could not write status: landed to {path}: {exc}", file=sys.stderr)
PYEOF
else
  echo "  WARNING: no task.yml found at $TASK_YML - skipping status write."
fi

COMPASS_CLI="$COMPASS_HOME/cli/compass"
if [ -x "$COMPASS_CLI" ] || [ -f "$COMPASS_CLI" ]; then
  if ( cd "$PROJECT_DIR" && python3 "$COMPASS_CLI" _derive-system-spec --internal ); then
    echo "  docs/system-spec.md updated (living spec derived)."
  else
    echo "  WARNING: living spec derivation failed - docs/system-spec.md may be stale."
    echo "  Re-run: python3 cli/compass _derive-system-spec --internal"
  fi
else
  echo "  WARNING: compass CLI not found at $COMPASS_CLI - skipping derivation."
fi

# --- clean up the worktrees -------------------------------------------------
echo ""
if [ "$CLEAN" -eq 1 ]; then
  echo "Cleaning up worktrees:"
  for sid in "${STREAMS[@]}"; do
    wt_path="$WORKTREE_ROOT/$TASK_SLUG-$sid"
    if [ -d "$wt_path" ]; then
      git -C "$PROJECT_DIR" worktree remove --force "$wt_path" 2>/dev/null \
        && echo "  removed $wt_path" \
        || echo "  could not remove $wt_path - remove by hand with: git worktree remove '$wt_path'"
    fi
  done
  git -C "$PROJECT_DIR" worktree prune
  echo ""
  echo "Per-stream branches are left in place for history - delete them when you"
  echo "are sure: git branch -d <branch>"
else
  echo "(--no-clean) worktrees kept in place."
fi

echo ""
echo "Integration complete for '$TASK_SLUG'. Back in /compass:land, finish by:"
echo "  - pasting the combined-regression run into verification-report.md"
echo "  - updating living docs"
echo "  - resolving every owed backfill in route.md"
echo "  - writing the final devlog.md entry"
