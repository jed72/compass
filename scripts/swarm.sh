#!/usr/bin/env bash
# =============================================================================
# Compass script: swarm.sh  -  CREATE WORKTREES, ONE PER INDEPENDENT STREAM
# =============================================================================
# The Distribute-phase tool. Given an issue's distribution-map.md, it creates one
# git worktree per independent stream under the configured worktree_root, one
# branch per stream, and prints the launch plan - one `builder` agent per
# worktree. Only the `orchestrator` agent runs this (see CLAUDE.md, the
# worktree-swarm skill).
#
# USAGE
#   scripts/swarm.sh <task-slug>            # read .compass/work/<slug>/distribution-map.md
#   scripts/swarm.sh <task-slug> --dry-run  # show the plan, create nothing
#   scripts/swarm.sh --help
#
# WHAT IT RESPECTS
#   - .compass/config.yml  swarm.worktree_root   (default ../.compass-worktrees)
#   - .compass/config.yml  swarm.max_worktrees   (default 6) - hard ceiling
#   - any adaptivity `cap` recorded in delivery-approach.md, in particular the STANDING CAP:
#       critical risk => max_worktrees: 1.
#     If the cap is below the stream count, the cap WINS and swarm.sh refuses to
#     over-provision - it tells you to fold/sequence streams in the map first.
#
# IDEMPOTENT & SAFE
#   - A worktree/branch that already exists for a stream is left as-is (reported
#     as "exists"), not recreated.
#   - It never deletes anything - teardown is integrate.sh's job on success.
#   - On any inconsistency (map missing, count over cap, dirty repo) it stops
#     with a clear message and changes nothing.
# =============================================================================

set -euo pipefail

# --- locate repo + project --------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPASS_HOME="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_DIR="$(git -C "$(pwd)" rev-parse --show-toplevel 2>/dev/null || pwd)"

# shellcheck source=lib/compass-python.sh
source "$SCRIPT_DIR/lib/compass-python.sh"

# --- args -------------------------------------------------------------------
TASK_SLUG=""
DRY_RUN=0
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY_RUN=1 ;;
    -h|--help) grep -E '^# (USAGE|  scripts)' "$0" | sed 's/^# //'; exit 0 ;;
    -*) echo "swarm.sh: unknown flag: $1" >&2; exit 1 ;;
    *)  TASK_SLUG="$1" ;;
  esac
  shift
done
[ -n "$TASK_SLUG" ] || { echo "swarm.sh: need a issue slug. See --help." >&2; exit 1; }

TASK_DIR="$PROJECT_DIR/.compass/work/$TASK_SLUG"
MAP="$TASK_DIR/distribution-map.md"
ROUTE="$TASK_DIR/delivery-approach.md"
# vocabulary-scan: allow - reads the retired artifact name for old archives
[ -f "$ROUTE" ] || ROUTE="$TASK_DIR/route.md"
TASK_YML="$TASK_DIR/task.yml"
CONFIG="$PROJECT_DIR/.compass/config.yml"

[ -f "$MAP" ]   || { echo "swarm.sh: no distribution-map.md for issue '$TASK_SLUG' - Plan must produce it first." >&2; exit 1; }
[ -f "$ROUTE" ] || { echo "swarm.sh: no delivery-approach.md for issue '$TASK_SLUG' - triage must run first." >&2; exit 1; }
[ -f "$TASK_YML" ] || { echo "swarm.sh: no task.yml for issue '$TASK_SLUG' - the worktree cap is read from structured assessment, not delivery-approach.md prose. Run Frame." >&2; exit 1; }

# --- config: worktree_root + max_worktrees ----------------------------------
# Minimal YAML reads - these keys are simple scalars in .compass/config.yml.
read_cfg() { # key default
  local v=""
  [ -f "$CONFIG" ] && v="$(grep -E "^[[:space:]]*$1:" "$CONFIG" 2>/dev/null \
      | head -n1 | sed -E 's/^[^:]*:[[:space:]]*//; s/[[:space:]]*#.*$//; s/^"//; s/"$//')"
  echo "${v:-$2}"
}
WORKTREE_ROOT_REL="$(read_cfg 'worktree_root' '../.compass-worktrees')"
MAX_WORKTREES="$(read_cfg 'max_worktrees' '6')"

# worktree_root is relative to the project root.
case "$WORKTREE_ROOT_REL" in
  /*) WORKTREE_ROOT="$WORKTREE_ROOT_REL" ;;
  *)  WORKTREE_ROOT="$(cd "$PROJECT_DIR" && cd "$(dirname "$WORKTREE_ROOT_REL")" 2>/dev/null && pwd || echo "$PROJECT_DIR/$WORKTREE_ROOT_REL")/$(basename "$WORKTREE_ROOT_REL")" ;;
esac

# --- the cap from task.yml (R4) ---------------------------------------------
# The cap is a MACHINE FACT and must come from the structured assessment, not from
# grepping delivery-approach.md prose - a well-formed delivery-approach.md quotes 'risk: critical'
# and 'RG-CAP-001' in its "guardrails that did NOT fire" audit notes, and the old
# prose grep false-positived on exactly those, capping a non-critical swarm to 1.
# The standing cap (RG-CAP-001): critical risk => max_worktrees 1. We read
# it from assessment.risk and fired_guardrails. Absent assessment is a hard
# error - never a silent cap, never a fall back to prose.
CAP_INFO="$(compass_python - "$TASK_YML" <<'PY'
import sys
import compass_pkg
try:
    import yaml
    d = yaml.safe_load(open(sys.argv[1]))
except Exception as e:
    print("ERR:" + str(e)); sys.exit(0)
if not isinstance(d, dict):
    print("ERR:task.yml is not a mapping"); sys.exit(0)
assessment = d.get("assessment") or d.get("readings") or {}
br = assessment.get("risk") or assessment.get("blast_radius")
if not br:
    print("ERR:no assessment.risk in task.yml"); sys.exit(0)
fired = d.get("policy_rules_fired") or d.get("fired_guardrails") or []
capped = (br == "critical") or any(
    isinstance(f, dict) and f.get("id") == "RG-CAP-001" for f in fired)
print("OK:" + ("1" if capped else "0"))
PY
)"
case "$CAP_INFO" in
  OK:1) CAP=1 ;;
  OK:0) CAP="$MAX_WORKTREES" ;;
  *)    echo "swarm.sh: cannot read the cap from task.yml (${CAP_INFO#ERR:})." >&2
        echo "          The worktree cap is a machine fact in assessment.risk +" >&2
        echo "          fired_guardrails - fix task.yml. swarm.sh does NOT fall back to" >&2
        echo "          grepping delivery-approach.md prose (that was the R4 false-positive)." >&2
        exit 1 ;;
esac
# Never exceed the config ceiling regardless.
[ "$CAP" -gt "$MAX_WORKTREES" ] && CAP="$MAX_WORKTREES"

# --- parse streams from the distribution map --------------------------------
# The map's §3 table has rows like:
#   | stream-1 | U1 | TRC-A1, TRC-A2 | compass/<slug>/stream-1 |
# We pull (stream id, branch name) pairs from any table row whose first cell
# starts with "stream-". This is intentionally forgiving so a hand-filled map
# still parses.
STREAMS=()
BRANCHES=()
while IFS= read -r line; do
  # row must look like a markdown table row mentioning a stream id
  case "$line" in
    \|*stream-*) ;;
    *) continue ;;
  esac
  # R4: count only worktree-provisioning streams. A map may mark an
  # integration/verify stream as non-provisioning - exclude it from the cap
  # arithmetic and from worktree creation.
  case "$line" in
    *"not a parallel worktree"*|*"not a worktree"*|*"non-provisioning"*|*"integration/verify"*) continue ;;
  esac
  # split on '|', trim each cell
  IFS='|' read -r _ c1 c2 c3 c4 _rest <<<"$line"
  sid="$(echo "${c1:-}" | xargs 2>/dev/null || true)"
  # Trim whitespace AND strip leading/trailing markdown punctuation (`, *).
  # The map's branch-name cell is often wrapped in backticks for readability
  # (`compass/<slug>/stream-N`) or bold (**...**); the parser must treat the
  # cell as a clean git ref, not the literal-with-markdown string. Bare names
  # round-trip unchanged. Markdown *inside* a ref name is out of scope -
  # git ref-validation rejects such names anyway.
  branch="$(echo "${c4:-}" | xargs 2>/dev/null | sed -E 's/^[`*]+//; s/[`*]+$//' || true)"
  case "$sid" in stream-*) ;; *) continue ;; esac
  # default branch name if the map left it blank
  [ -n "$branch" ] || branch="compass/$TASK_SLUG/$sid"
  STREAMS+=("$sid")
  BRANCHES+=("$branch")
done < "$MAP"

STREAM_COUNT="${#STREAMS[@]}"
if [ "$STREAM_COUNT" -eq 0 ]; then
  echo "swarm.sh: distribution-map.md lists no streams (no 'stream-N' rows in §3)." >&2
  echo "          If the route is solo, Distribute is a no-op - do not run swarm.sh." >&2
  exit 1
fi

# --- enforce the cap --------------------------------------------------------
if [ "$STREAM_COUNT" -gt "$CAP" ]; then
  echo "swarm.sh: the distribution map has $STREAM_COUNT streams but the cap is $CAP." >&2
  echo "          The cap wins. Do not over-provision worktrees - go back to" >&2
  echo "          distribution-map.md and fold or sequence streams down to $CAP," >&2
  echo "          recording it as cap-driven (not as a de-scope). Then re-run." >&2
  exit 1
fi

# --- repo sanity ------------------------------------------------------------
git -C "$PROJECT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1 \
  || { echo "swarm.sh: $PROJECT_DIR is not a git repository." >&2; exit 1; }
BASE_BRANCH="$(git -C "$PROJECT_DIR" rev-parse --abbrev-ref HEAD)"

echo "Compass swarm - issue '$TASK_SLUG'"
echo "  base branch:    $BASE_BRANCH"
echo "  worktree root:  $WORKTREE_ROOT"
echo "  streams:        $STREAM_COUNT   (config max $MAX_WORKTREES, route cap $CAP)"
echo ""

# --- create the worktrees ---------------------------------------------------
mkdir -p "$WORKTREE_ROOT"
LAUNCH_PLAN=()

for i in "${!STREAMS[@]}"; do
  sid="${STREAMS[$i]}"
  branch="${BRANCHES[$i]}"
  wt_path="$WORKTREE_ROOT/$TASK_SLUG-$sid"

  if [ -d "$wt_path" ]; then
    echo "  $sid: worktree exists -> $wt_path"
  elif [ "$DRY_RUN" -eq 1 ]; then
    echo "  $sid: WOULD create worktree $wt_path on branch $branch"
  else
    # Create the branch if it does not exist, then the worktree on it.
    if git -C "$PROJECT_DIR" show-ref --verify --quiet "refs/heads/$branch"; then
      git -C "$PROJECT_DIR" worktree add "$wt_path" "$branch" >/dev/null
    else
      git -C "$PROJECT_DIR" worktree add -b "$branch" "$wt_path" "$BASE_BRANCH" >/dev/null
    fi
    echo "  $sid: created worktree $wt_path on branch $branch"
  fi

  # --- seed the worktree with the issue's artifacts --------------------------
  # `git worktree add` brings across only what git TRACKS. A project that
  # commits .compass/work/ gets the issue directory for free; one that treats
  # issue state as local - as this framework repo does, see .gitignore - does
  # not, and its builder lands in a worktree with no spec, no plan, and no
  # charter. `compass next`, `compass check`, and `compass tdd-red` all fail
  # there, because resolve_task_dir has no work directory to resolve against.
  #
  # NON-DESTRUCTIVE ON PURPOSE. swarm.sh is documented as idempotent, and the
  # second run is the one where a builder has work to lose - a devlog entry, a
  # recorded red. An existing issue directory is left exactly as it is.
  if [ "$DRY_RUN" -eq 0 ] && [ -d "$wt_path" ]; then
    wt_task_dir="$wt_path/.compass/work/$TASK_SLUG"
    if [ -d "$wt_task_dir" ]; then
      echo "      issue dir already present - left as-is"
    else
      mkdir -p "$wt_task_dir"
      # Copy the ARTIFACTS a builder needs to work - and nothing that would
      # hand them credit they did not earn. `.red` is the marker
      # hooks/pre-tool.sh reads to permit a production-code edit, and it means
      # "a real failure was observed HERE". Copying it lets a builder edit
      # production code on a red someone else recorded in another worktree.
      # `evidence/` is the same argument: a green run belongs to the run that
      # produced it.
      for _f in "$TASK_DIR"/*; do
        case "$(basename "$_f")" in
          evidence) continue ;;
          *) cp -R "$_f" "$wt_task_dir/" ;;
        esac
      done
      echo "      seeded issue dir -> .compass/work/$TASK_SLUG"
    fi
    # The pointer every `compass` call resolves "the current issue" through.
    # Written unconditionally: it is one line naming this issue, so there is no
    # builder work in it to lose, and a stale pointer is worse than none.
    mkdir -p "$wt_path/.compass"
    printf '%s\n' "$TASK_SLUG" > "$wt_path/.compass/current-task"
  fi

  LAUNCH_PLAN+=("$sid|$branch|$wt_path")
done

# --- print the launch plan --------------------------------------------------
echo ""
echo "Launch plan - one 'builder' agent per worktree:"
echo "----------------------------------------------------------------"
for entry in "${LAUNCH_PLAN[@]}"; do
  IFS='|' read -r sid branch wt_path <<<"$entry"
  echo "  builder for $sid"
  echo "    worktree : $wt_path"
  echo "    branch   : $branch"
  echo "    charter  : owns the scenario set assigned to $sid in distribution-map.md"
  echo "    rule     : works ONLY inside this worktree; cross-stream needs go via the orchestrator"
  echo ""
done
echo "----------------------------------------------------------------"
if [ "$STREAM_COUNT" -ge 4 ]; then
  echo "Topology is a SWARM (4+ streams): an 'orchestrator' agent must also run -"
  echo "it writes no feature code, watches for streams converging on shared surface,"
  echo "and owns integration at ship via scripts/integrate.sh."
else
  echo "Topology is a PAIR (2-3 streams): no dedicated orchestrator - the lead"
  echo "builder integrates at ship via scripts/integrate.sh."
fi
echo ""
[ "$DRY_RUN" -eq 1 ] && echo "(dry run - nothing was created)"
echo "When every stream is independently green, land them with:"
echo "  scripts/integrate.sh $TASK_SLUG"
