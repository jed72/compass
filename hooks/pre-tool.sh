#!/usr/bin/env bash
# =============================================================================
# Compass hook: pre-tool.sh  —  THE RED-BEFORE-GREEN STRATEGY ENFORCER
# =============================================================================
# Enforces the TDD strategy (S2: red-green-refactor) mechanically — in service
# of guardrail G1 ("tested before it lands"). Note the distinction, because it
# is the whole point of Compass's governance model:
#
#   * G1 (a GUARDRAIL) is the hard line: no code lands without a passing test
#     it traces to. G1 is checked at Verify and Land, with evidence.
#   * Red-before-green (a STRATEGY) is the strong, shipped-on *way* to satisfy
#     G1. This hook enforces the strategy — and a strategy is route-aware.
#
# This hook therefore BLOCKS code edits with no failing test on record — EXCEPT
# on a Spike route, where the TDD strategy is deliberately suspended so
# exploration is not throttled. A Spike still cannot violate G1: nothing lands
# from a Spike without graduating (re-framing) into a real route first, where
# this hook applies in full.
#
# WHAT IT DOES
#   Runs as a Claude Code PreToolUse hook. On a tool call that edits or writes a
#   *code* file (not a test, not docs, not a Compass artifact):
#     - if the current task's route is Spike (a ".spike" marker exists) → ALLOW.
#     - else, require a recorded failing test — a ".red" marker file under
#       .compass/work/<task-slug>/. No .red marker → the edit is BLOCKED.
#
# THE MARKER CONVENTION  (this is the "not magic" part — read this)
#   .compass/work/<task-slug>/.red    "a failing test currently exists for this
#                                      task". It is NOT a bare `touch` — it is
#                                      written by `compass tdd-red <test-cmd>`,
#                                      which runs the test, confirms it really
#                                      fails, writes evidence/red.json with the
#                                      command + exit code + log, and only THEN
#                                      drops the .red marker. So the marker
#                                      means "a real, observed failure is on
#                                      record", not "someone touched a file".
#     1. Build: `compass tdd-red -- <your failing test command>`.
#     2. Edit the production code — this hook sees .red and allows it.
#     3. `compass tdd-green -- <test command>` confirms green, writes
#        evidence/green.json, and clears .red — the hand-off to Verify.
#   .compass/work/<task-slug>/.spike  "this task is on a Spike route — the TDD
#                                      strategy is suspended". /compass:frame
#                                      writes this when it composes a Spike.
#   Markers are deliberately plain files so they are inspectable and auditable;
#   the evidence/*.json records next to them are the audit trail.
#
# ESCAPE HATCH
#   Test files, docs, config, and .compass/ artifacts are never blocked — you
#   must be able to write the failing test in the first place. The Spike route
#   is the *intentional* escape hatch for exploratory work. There is no env var
#   to disable the check on a delivery route: that would not be suspending a
#   strategy, it would be crossing guardrail G1.
#
# WIRING  (.claude/settings.json)
#   {
#     "hooks": {
#       "PreToolUse": [
#         { "matcher": "Edit|Write|MultiEdit",
#           "hooks": [ { "type": "command",
#                        "command": "$CLAUDE_PROJECT_DIR/hooks/pre-tool.sh" } ] }
#       ]
#     }
#   }
#   `scripts/install.sh` registers this for you.
#
# I/O CONTRACT  (Claude Code hook format)
#   stdin : JSON describing the tool call.
#   block : exit code 2  (Claude Code treats exit 2 on PreToolUse as "deny").
#   allow : exit code 0.
#   We also emit a short human-readable reason on stderr when blocking.
# =============================================================================

set -euo pipefail

# --- read the tool call from stdin ------------------------------------------
INPUT="$(cat || true)"

# Pull the target file path out of the JSON. Prefer jq; fall back to grep so the
# hook still works on a machine without jq installed.
if command -v jq >/dev/null 2>&1; then
  TARGET="$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // .tool_input.path // empty' 2>/dev/null || true)"
  TOOL="$(printf '%s' "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null || true)"
else
  TARGET="$(printf '%s' "$INPUT" | grep -oE '"file_path"[[:space:]]*:[[:space:]]*"[^"]*"' | head -n1 | sed -E 's/.*:[[:space:]]*"([^"]*)"/\1/' || true)"
  TOOL="$(printf '%s' "$INPUT" | grep -oE '"tool_name"[[:space:]]*:[[:space:]]*"[^"]*"' | head -n1 | sed -E 's/.*:[[:space:]]*"([^"]*)"/\1/' || true)"
fi

# No file path → nothing to enforce (e.g. a non-file tool). Allow.
[ -z "${TARGET:-}" ] && exit 0

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"

# --- classify the target file -----------------------------------------------
# A "code file" here means: a production-impacting file whose change must be
# preceded by a failing test. That is broader than application source — a
# Terraform file, a SQL migration, a Kubernetes manifest, or a CI workflow can
# be more dangerous than ordinary code. Test files, docs, and Compass's own
# artifacts are exempt.

# Always exempt: Compass artifacts, docs, lockfiles, the obvious non-code.
case "$TARGET" in
  *.compass/*|*/.compass/*) exit 0 ;;
  *.md|*.markdown|*.txt|*.rst|*.adoc) exit 0 ;;
  *.lock|*.gitignore|*.gitkeep|*.gitattributes|*.editorconfig) exit 0 ;;
esac

# Exempt: test files — you have to be able to write the red. Tune these globs
# to the project's test conventions.
case "$TARGET" in
  *test*|*Test*|*spec*|*Spec*|*__tests__*|*.test.*|*.spec.*|*_test.*|*/tests/*) exit 0 ;;
esac

IS_CODE=0

# (a) recognised application source extensions.
case "$TARGET" in
  *.ts|*.tsx|*.js|*.jsx|*.mjs|*.cjs) IS_CODE=1 ;;
  *.py|*.rb|*.go|*.rs|*.java|*.kt|*.kts) IS_CODE=1 ;;
  *.c|*.h|*.cc|*.cpp|*.hpp|*.cs|*.swift|*.m|*.mm) IS_CODE=1 ;;
  *.php|*.scala|*.ex|*.exs|*.clj|*.elm|*.dart) IS_CODE=1 ;;
esac

# (b) infrastructure / data / pipeline files — production-impacting even though
#     they are not "application code". A SQL migration or a Terraform plan
#     deserves a failing test (or a tested rollback) as much as a service does.
case "$TARGET" in
  *.tf|*.tfvars|*.hcl) IS_CODE=1 ;;                       # Terraform / HCL
  *.sql) IS_CODE=1 ;;                                     # SQL incl. migrations
  Dockerfile|*/Dockerfile|*.dockerfile) IS_CODE=1 ;;      # container images
esac

# (c) path-scoped: YAML/JSON are exempt by default (config, data) — EXCEPT
#     under infrastructure-ish paths, where a yaml IS the production change
#     (k8s manifests, Helm charts, CI workflows, migrations, dbt models).
#     Note: in a `case` glob, `*` also matches `/`, so `*migrations/*` catches
#     both `migrations/x` and `db/migrations/x` — leading `*` with no slash.
case "$TARGET" in
  *migrations/*|*db/migrate/*) IS_CODE=1 ;;
  *.github/workflows/*|*.gitlab-ci.yml) IS_CODE=1 ;;
  *k8s/*|*kubernetes/*|*helm/*|*charts/*|*manifests/*|*deploy/*) IS_CODE=1 ;;
  *terraform/*|*infra/*|*infrastructure/*) IS_CODE=1 ;;
  *dbt/*|*models/*.sql) IS_CODE=1 ;;
esac

# Anything still unrecognised is allowed — the enforcer blocks KNOWN
# production-impacting files; it does not block the unknown. If a project has
# a production-impacting file type that slips through, add it above.
[ "$IS_CODE" -eq 0 ] && exit 0

# --- find the current task --------------------------------------------------
# The current task is named by the .compass/current-task pointer (written by
# /compass:frame and /compass:resume). The pointer is what makes this reliable
# when more than one task is in flight — "most recently modified directory" is
# only the fallback, and it is ambiguous, so it warns. If there is no task at
# all, Frame has not run — CLAUDE.md's one rule is "Never skip Frame".
COMPASS_DIR="$PROJECT_DIR/.compass"
WORK_DIR="$COMPASS_DIR/work"
if [ ! -d "$WORK_DIR" ]; then
  echo "Compass: no .compass/work/ — Frame has not run. Run /compass:frame before changing code." >&2
  exit 2
fi

TASK_DIR=""
POINTER="$COMPASS_DIR/current-task"
if [ -f "$POINTER" ]; then
  SLUG="$(tr -d '[:space:]' < "$POINTER" 2>/dev/null || true)"
  if [ -n "$SLUG" ] && [ -d "$WORK_DIR/$SLUG" ]; then
    TASK_DIR="$WORK_DIR/$SLUG"
  fi
fi
if [ -z "$TASK_DIR" ]; then
  # fallback: most recently modified — ambiguous, so say so.
  TASK_DIR="$(ls -dt "$WORK_DIR"/*/ 2>/dev/null | head -n1 || true)"
  TASK_DIR="${TASK_DIR%/}"
  [ -n "$TASK_DIR" ] && echo "Compass: no .compass/current-task pointer — falling back to the most recently modified task ($(basename "$TASK_DIR")). Write .compass/current-task to be unambiguous." >&2
fi

if [ -z "${TASK_DIR:-}" ]; then
  echo "Compass: no task under .compass/work/ — Frame has not run for this change." >&2
  exit 2
fi

TASK_SLUG="$(basename "$TASK_DIR")"

# A route.md must exist — code work without a computed route is route laundering.
if [ ! -f "$TASK_DIR/route.md" ]; then
  echo "Compass: task '$TASK_SLUG' has no route.md — Frame did not complete. Run /compass:frame." >&2
  exit 2
fi

# --- route-aware: the TDD strategy is suspended on a Spike route -------------
# /compass:frame writes a .spike marker when it composes a Spike route. On a
# Spike, exploration is not throttled — the red-before-green strategy is
# suspended. Guardrail G1 is NOT suspended: nothing lands from a Spike without
# graduating into a real route, where this hook applies in full.
if [ -f "$TASK_DIR/.spike" ]; then
  exit 0
fi

# --- the red-before-green check (delivery routes) ---------------------------
if [ -f "$TASK_DIR/.red" ]; then
  # A failing test is on record for this task. Red came before green. Allow.
  exit 0
fi

# No .red marker → no failing test on record → block the code edit.
cat >&2 <<EOF
Compass: BLOCKED — no failing test on record for task '$TASK_SLUG'.

  Strategy S2 (red-before-green) applies on this route, in service of
  guardrail G1 (tested before it lands).
  Edit target: $TARGET  (tool: ${TOOL:-?})

  To proceed the Compass way:
    1. Write the failing test for the scenario you are implementing.
    2. Record the red — run it through the CLI so the failure is observed
       and the evidence is captured:
         compass tdd-red -- <your failing test command>
       (this runs the test, confirms it fails, writes evidence/red.json,
        and drops the .red marker this hook checks for).
    3. Re-try this edit.

  Later, \`compass tdd-green -- <test command>\` confirms green, writes
  evidence/green.json, and clears the .red marker — the hand-off to Verify.

  If this is genuinely exploratory work, it should be a Spike route — re-run
  /compass:frame. The fix is to write the test or re-frame, not to route
  around the hook.
EOF
exit 2
