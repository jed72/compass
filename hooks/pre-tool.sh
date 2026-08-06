#!/usr/bin/env bash
# =============================================================================
# Compass hook: pre-tool.sh  -  THE RED-BEFORE-GREEN STRATEGY ENFORCER
# =============================================================================
# Enforces the TDD strategy (S2: red-green-refactor) mechanically - in service
# of guardrail G1 ("tested before it lands"). Note the distinction, because it
# is the whole point of Compass's governance model:
#
#   * G1 (a GUARDRAIL) is the hard line: no code lands without a passing test
#     it traces to. G1 is checked at Verify and Land, with evidence.
#   * Red-before-green (a STRATEGY) is the strong, shipped-on *way* to satisfy
#     G1. This hook enforces the strategy - and a strategy is route-aware.
#
# This hook therefore BLOCKS code edits with no failing test on record - EXCEPT
# on a Spike route, where the TDD strategy is deliberately suspended so
# exploration is not throttled. A Spike still cannot violate G1: nothing lands
# from a Spike without graduating (re-framing) into a real route first, where
# this hook applies in full.
#
# WHAT IT DOES
#   Runs as a Claude Code PreToolUse hook. On a tool call that edits or writes a
#   *code* file (not a test, not docs, not a Compass artifact):
#     - if the current task's route is Spike (a ".spike" marker exists) → ALLOW.
#     - else, require a recorded failing test - a ".red" marker file under
#       .compass/work/<task-slug>/. No .red marker → the edit is BLOCKED.
#
# THE MARKER CONVENTION  (this is the "not magic" part - read this)
#   .compass/work/<task-slug>/.red    "a failing test currently exists for this
#                                      task". It is NOT a bare `touch` - it is
#                                      written by `compass tdd-red <test-cmd>`,
#                                      which runs the test, confirms it really
#                                      fails, writes evidence/red.json with the
#                                      command + exit code + log, and only THEN
#                                      drops the .red marker. So the marker
#                                      means "a real, observed failure is on
#                                      record", not "someone touched a file".
#     1. Build: `compass tdd-red -- <your failing test command>`.
#     2. Edit the production code - this hook sees .red and allows it.
#     3. `compass tdd-green -- <test command>` confirms green, writes
#        evidence/green.json, and clears .red - the hand-off to Verify.
#   .compass/work/<task-slug>/.spike  "this task is on a Spike route - the TDD
#                                      strategy is suspended". /compass:frame
#                                      writes this when it composes a Spike.
#   Markers are deliberately plain files so they are inspectable and auditable;
#   the evidence/*.json records next to them are the audit trail.
#
# ESCAPE HATCH
#   Test files, docs, config, and .compass/ artifacts are never blocked - you
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
  COMMAND="$(printf '%s' "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null || true)"
else
  TARGET="$(printf '%s' "$INPUT" | grep -oE '"file_path"[[:space:]]*:[[:space:]]*"[^"]*"' | head -n1 | sed -E 's/.*:[[:space:]]*"([^"]*)"/\1/' || true)"
  TOOL="$(printf '%s' "$INPUT" | grep -oE '"tool_name"[[:space:]]*:[[:space:]]*"[^"]*"' | head -n1 | sed -E 's/.*:[[:space:]]*"([^"]*)"/\1/' || true)"
  COMMAND="$(printf '%s' "$INPUT" | grep -oE '"command"[[:space:]]*:[[:space:]]*"[^"]*"' | head -n1 | sed -E 's/.*:[[:space:]]*"([^"]*)"/\1/' || true)"
fi

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"

# --- classify a target file -------------------------------------------------
# A "code file" here means: a production-impacting file whose change must be
# preceded by a failing test. That is broader than application source - a
# Terraform file, a SQL migration, a Kubernetes manifest, or a CI workflow can
# be more dangerous than ordinary code. Test files, docs, and Compass's own
# artifacts are exempt.
#
# This is a function rather than a straight-line sequence because a single
# tool call can name more than one path: a Bash command may redirect into one
# file and copy over another. Both branches share this one implementation so
# the rules cannot drift apart - a path exempt for an Edit is exempt for a
# shell redirect, by construction.
#
# Returns 0 (true) if a change to $1 must be preceded by a failing test.
MATCHED_RULE=""
is_enforced_path() {
  local target="$1" rel base is_code=0

  # Always exempt: Compass artifacts, docs, lockfiles, the obvious non-code.
  case "$target" in
    *.compass/*|*/.compass/*) return 1 ;;
    *.md|*.markdown|*.txt|*.rst|*.adoc) return 1 ;;
    *.lock|*.gitignore|*.gitkeep|*.gitattributes|*.editorconfig) return 1 ;;
  esac

  # Exempt: test files - you have to be able to write the red. Tune these globs
  # to the project's test conventions.
  #
  # Matched against the BASENAME and the project-relative path, never the
  # absolute one. Matching `*test*` against an absolute path also matches every
  # ancestor directory, so a repository living under any path containing "test"
  # or "spec" - /Users/testuser/..., .../latest/... - had red-before-green
  # silently disabled for the entire tree. Enforcement that turns itself off
  # based on where you cloned the repo is worse than no enforcement, because it
  # still reports that it is on.
  rel="$target"
  case "$target" in
    "$PROJECT_DIR"/*) rel="${target#"$PROJECT_DIR"/}" ;;
  esac
  base="$(basename "$target")"
  case "$base" in
    *test*|*Test*|*spec*|*Spec*|*.test.*|*.spec.*|*_test.*) return 1 ;;
  esac
  case "$rel" in
    tests/*|*/tests/*|test/*|*/test/*|spec/*|*/spec/*|\
    __tests__/*|*/__tests__/*|testdata/*|*/testdata/*) return 1 ;;
  esac

  # (a) recognised application source extensions.
  case "$target" in
    *.ts|*.tsx|*.js|*.jsx|*.mjs|*.cjs) is_code=1 ;;
    *.py|*.rb|*.go|*.rs|*.java|*.kt|*.kts) is_code=1 ;;
    *.c|*.h|*.cc|*.cpp|*.hpp|*.cs|*.swift|*.m|*.mm) is_code=1 ;;
    *.php|*.scala|*.ex|*.exs|*.clj|*.elm|*.dart) is_code=1 ;;
  esac

  # (b) infrastructure / data / pipeline files - production-impacting even though
  #     they are not "application code". A SQL migration or a Terraform plan
  #     deserves a failing test (or a tested rollback) as much as a service does.
  case "$target" in
    *.tf|*.tfvars|*.hcl) is_code=1 ;;                       # Terraform / HCL
    *.sql) is_code=1 ;;                                     # SQL incl. migrations
    Dockerfile|*/Dockerfile|*.dockerfile) is_code=1 ;;      # container images
  esac

  # (c) path-scoped: YAML/JSON are exempt by default (config, data) - EXCEPT
  #     under infrastructure-ish paths, where a yaml IS the production change
  #     (k8s manifests, Helm charts, CI workflows, migrations, dbt models).
  #     Note: in a `case` glob, `*` also matches `/`, so `*migrations/*` catches
  #     both `migrations/x` and `db/migrations/x` - leading `*` with no slash.
  case "$target" in
    *migrations/*|*db/migrate/*) is_code=1 ;;
    *.github/workflows/*|*.gitlab-ci.yml) is_code=1 ;;
    *k8s/*|*kubernetes/*|*helm/*|*charts/*|*manifests/*|*deploy/*) is_code=1 ;;
    *terraform/*|*infra/*|*infrastructure/*) is_code=1 ;;
    *dbt/*|*models/*.sql) is_code=1 ;;
  esac

  if [ "$is_code" -eq 1 ]; then
    MATCHED_RULE="the built-in production-code set"
    return 0
  fi

  # (d) the project's own declaration. `.compass/config.yml`:
  #
  #     enforcement:
  #       code_globs: ["*.sh", "packaging/**"]
  #
  # This ADDS to the set above. There is deliberately no key that removes
  # framework enforcement: Compass's model is that project rules ratchet UP - a
  # project guardrail may exceed a floor, never fall short of one - and a key
  # that exempted `*.py` would be a disable switch wearing the clothes of
  # configuration. The first inconvenient red is when someone would reach for
  # it.
  #
  # Why this exists: the guarded surface was folklore. `.github/workflows/ci.yml`
  # was guarded and `docker-compose.yml` was not, with no visible rule, so an
  # author could not predict which edit would block and found out mid-change.
  if [ -f "$PROJECT_DIR/.compass/config.yml" ] && command -v python3 >/dev/null 2>&1; then
    local hit
    hit="$(python3 - "$PROJECT_DIR/.compass/config.yml" "$rel" <<'PYEOF' 2>/dev/null || true
import fnmatch, sys
try:
    import yaml
    with open(sys.argv[1], encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh) or {}
    globs = ((cfg.get("enforcement") or {}).get("code_globs")) or []
except Exception:
    sys.exit(0)                     # unreadable config -> built-in set only
path = sys.argv[2]
for g in globs:
    if fnmatch.fnmatch(path, g) or fnmatch.fnmatch(path, g.rstrip("/") + "/*") \
            or fnmatch.fnmatch("/" + path, "*/" + g.lstrip("/")):
        print(g)
        break
PYEOF
)"
    if [ -n "${hit:-}" ]; then
      MATCHED_RULE="enforcement.code_globs pattern '$hit' in .compass/config.yml"
      return 0
    fi
  fi

  # Anything still unrecognised is allowed - the enforcer blocks KNOWN
  # production-impacting files; it does not block the unknown. If a project has
  # a production-impacting file type that slips through, declare it above.
  return 1
}

# --- what a shell command can be known to write ------------------------------
# A shell command is arbitrary: `bash deploy.sh` may rewrite the whole repo and
# nothing in the string says so. So detection here recognises a fixed set of
# write shapes and lets everything else through. That is deliberate - blocking
# on suspicion would block `make`, `npm test`, and every unrecognised command,
# and enforcement that people switch off protects nothing. The limit is written
# down in docs/safety-contract.md rather than left to be discovered.
#
# Being generous is safe: every candidate goes through is_enforced_path(),
# which allows anything it does not recognise as production code. A token that
# is not a path simply falls through.
bash_write_targets() {
  local cmd="$1"
  {
    # Redirects into a file: `> f`, `>> f`, `1> f`, and the `cat > f <<EOF`
    # heredoc form. `2>&1` and `>&2` duplicate a file descriptor rather than
    # write a file, so `&` is excluded from the target.
    printf '%s\n' "$cmd" \
      | grep -oE '[0-9]?>>?[[:space:]]*[^&<>|;()[:space:]]+' \
      | sed -E 's/^[0-9]?>>?[[:space:]]*//' || true

    # In-place editors and explicit writers: hand over every argument and let
    # the classifier decide which of them is a production file.
    case "$cmd" in
      *"sed -i"*|*"perl -i"*|*"tee "*)
        printf '%s\n' "$cmd" | tr ' \t' '\n\n' | grep -vE '^-' || true ;;
    esac

    # Copy and move write to their LAST argument. Only the destination counts -
    # reading a source file is not a change to it.
    case "$cmd" in
      cp\ *|mv\ *|*[\;\&\|]\ *cp\ *|*[\;\&\|]\ *mv\ *)
        printf '%s\n' "$cmd" | awk '{print $NF}' || true ;;
    esac

    # An inline interpreter script that opens a file FOR WRITING - the shape
    # this whole branch exists for, since `python3 -c` and a `python3 - <<PY`
    # heredoc are the easiest way to edit a file without an Edit tool call.
    #
    # Two things this deliberately does NOT do, both reported from the field
    # within hours of shipping the looser version:
    #   - `open(path)` with no mode is a READ. Treating it as a write blocked
    #     read-only verification commands - the hook stopping an author from
    #     checking their own work, which inverts what it is for.
    #   - The path must come from the write call itself. Scanning the whole
    #     command lifted paths out of heredoc bodies, so writing a document
    #     that merely *named* a migration demanded a failing test for the
    #     migration. Every artifact that discusses code paths hit this.
    # A missed write is recoverable; a false block trains people to bypass the
    # hook, and nothing recovers from that.

    # open(PATH, "w"|"a"|"x"|"r+"|"wb"…) - a mode containing w, a, x or + .
    printf '%s\n' "$cmd" \
      | grep -oE "open\([[:space:]]*['\"][^'\"]+['\"][[:space:]]*,[[:space:]]*['\"][^'\"]*[waxWAX+][^'\"]*['\"]" \
      | sed -E "s/^open\([[:space:]]*['\"]([^'\"]+)['\"].*/\1/" || true

    # pathlib. Covers both `Path(PATH).write_text(...)` and the commoner
    # two-step form, where the write happens on a variable:
    #     p = pathlib.Path(PATH)
    #     p.write_text(...)
    # So when the command contains a pathlib write at all, every Path(...)
    # argument in it is a candidate - except one used immediately for a read,
    # which keeps "read a source file, generate a doc from it" from being
    # blocked on the file it only read.
    case "$cmd" in
      *write_text\(*|*write_bytes\(*)
        printf '%s\n' "$cmd" \
          | grep -oE "Path\([[:space:]]*['\"][^'\"]+['\"][[:space:]]*\)(\.[a-z_]+)?" \
          | grep -v "\.read_" \
          | sed -E "s/^Path\([[:space:]]*['\"]([^'\"]+)['\"].*/\1/" || true ;;
    esac

    # node / ruby equivalents, where the path is the first argument.
    printf '%s\n' "$cmd" \
      | grep -oE "(writeFileSync|appendFileSync|File\.write)\([[:space:]]*['\"][^'\"]+['\"]" \
      | sed -E "s/^[A-Za-z_.]+\([[:space:]]*['\"]([^'\"]+)['\"].*/\1/" || true
  } | grep -vE '^[[:space:]]*$' || true
}

# --- decide whether this tool call needs a red on record ---------------------
if [ "${TOOL:-}" = "Bash" ]; then
  [ -z "${COMMAND:-}" ] && exit 0

  # Cheap pre-filter, before any filesystem work: this hook now runs on every
  # Bash call in the session, and most of them write nothing.
  case "$COMMAND" in
    *">"*|*"sed -i"*|*"perl -i"*|*"tee "*|*cp\ *|*mv\ *|\
    *patch\ -p*|*"git apply"*|*open\(*|*write_text*|*writeFileSync*|*File.write*) ;;
    *) exit 0 ;;
  esac

  DETECTED=""

  # `patch` and `git apply` name their targets inside the diff, not on the
  # command line. They are known writers with an unknowable target, so they are
  # treated as enforced - the escape is the same as any other: record the red.
  case "$COMMAND" in
    *patch\ -p*|*"git apply"*) DETECTED="(the files named in the patch)" ;;
  esac

  if [ -z "$DETECTED" ]; then
    while IFS= read -r candidate; do
      [ -z "$candidate" ] && continue
      if is_enforced_path "$candidate"; then
        DETECTED="$candidate"
        break
      fi
    done <<CANDIDATES
$(bash_write_targets "$COMMAND")
CANDIDATES
  fi

  # Nothing recognisable is written → allow. See docs/safety-contract.md.
  [ -z "$DETECTED" ] && exit 0
  TARGET="$DETECTED"
else
  # No file path → nothing to enforce (e.g. a non-file tool). Allow.
  [ -z "${TARGET:-}" ] && exit 0
  is_enforced_path "$TARGET" || exit 0
fi

# --- find the current task --------------------------------------------------
# The current task is named by the .compass/current-task pointer (written by
# /compass:frame and /compass:resume). The pointer is what makes this reliable
# when more than one task is in flight - "most recently modified directory" is
# only the fallback, and it is ambiguous, so it warns. If there is no task at
# all, Frame has not run - CLAUDE.md's one rule is "Never skip Frame".
COMPASS_DIR="$PROJECT_DIR/.compass"
WORK_DIR="$COMPASS_DIR/work"
if [ ! -d "$WORK_DIR" ]; then
  echo "Compass: no .compass/work/ - Frame has not run. Run /compass:frame before changing code." >&2
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
  # fallback: most recently modified - ambiguous, so say so.
  TASK_DIR="$(ls -dt "$WORK_DIR"/*/ 2>/dev/null | head -n1 || true)"
  TASK_DIR="${TASK_DIR%/}"
  [ -n "$TASK_DIR" ] && echo "Compass: no .compass/current-task pointer - falling back to the most recently modified task ($(basename "$TASK_DIR")). Write .compass/current-task to be unambiguous." >&2
fi

if [ -z "${TASK_DIR:-}" ]; then
  echo "Compass: no task under .compass/work/ - Frame has not run for this change." >&2
  exit 2
fi

TASK_SLUG="$(basename "$TASK_DIR")"

# A route.md must exist - code work without a computed route is route laundering.
if [ ! -f "$TASK_DIR/route.md" ]; then
  echo "Compass: task '$TASK_SLUG' has no route.md - Frame did not complete. Run /compass:frame." >&2
  exit 2
fi

# --- route-aware: the TDD strategy is suspended on a Spike route -------------
# /compass:frame writes a .spike marker when it composes a Spike route. On a
# Spike, exploration is not throttled - the red-before-green strategy is
# suspended. Guardrail G1 is NOT suspended: nothing lands from a Spike without
# graduating into a real route, where this hook applies in full.
if [ -f "$TASK_DIR/.spike" ]; then
  exit 0
fi

# --- guardrail G2: acceptance defined before it is built ---------------------
# The check below enforces strategy S2 (red before green). S2 serves guardrail
# G1. Nothing enforced G2 - acceptance stated and checkable BEFORE the code -
# at the point where it can still be true, so a route asking for a full Specify
# could go Frame -> Build with no spec at all: every edit allowed, because a red
# was on record and S2 was satisfied. `compass check` catches it at Verify,
# after the code exists, which is the ordering G2 exists to prevent.
#
# A guardrail beats a strategy, so this runs BEFORE the red check: you cannot
# write a red for a scenario that does not exist yet.
#
# Only `specify: full` triggers it, which routing-policy.yml gives to standard
# and expedition. Hotfix (reproduce-first) and Spike (collapsed) are exempt by
# construction, and the .spike early exit above suspends this the same way it
# suspends S2.
#
# If the spine cannot be read - no task.yml, unparseable YAML, no python3, no
# PyYAML - this stays silent and the prior behaviour applies. A false block on
# unreadable state is how a hook teaches people to bypass it.
if [ -f "$TASK_DIR/task.yml" ] && command -v python3 >/dev/null 2>&1; then
  G2_VERDICT="$(python3 - "$TASK_DIR/task.yml" <<'PYEOF' 2>/dev/null || true
import sys
try:
    import yaml
    with open(sys.argv[1], encoding="utf-8") as fh:
        task = yaml.safe_load(fh) or {}
    if not isinstance(task, dict):
        raise ValueError
except Exception:
    sys.exit(0)
phases = task.get("phases") or {}
if isinstance(phases, dict) and phases.get("specify") == "full":
    if not (task.get("scenarios") or []):
        print("block")
PYEOF
)"
  if [ "${G2_VERDICT:-}" = "block" ]; then
    cat >&2 <<EOF
Compass: BLOCKED - route says specify: full, but task.yml has no scenarios.

  Guardrail G2 (acceptance defined before it is built). No code is written
  that no stated, checkable acceptance criterion describes - and a guardrail
  beats a strategy, so this is checked before the red.
  Edit target: $TARGET  (tool: ${TOOL:-?})
  Guarded by  : ${MATCHED_RULE:-the built-in production-code set}

  To proceed the Compass way:
    1. Write the scenarios into .compass/work/$TASK_SLUG/spec.feature.md.
    2. Mirror them into task.yml's \`scenarios:\` block - each with an id, a
       linked intent, and the test(s) that will exercise it:
         compass scenario add SCN-001 --title "..." --intent INT-1
    3. Re-try this edit.

  If this is genuinely exploratory work it should be a Spike, where G2 is
  suspended - re-run /compass:frame. The fix is to state the acceptance or
  re-frame, not to route around the hook.
EOF
    exit 2
  fi
fi

# --- a declared acceptance (config / docs / behaviour-preserving refactor) ---
# Some legitimate changes have no natural behavioural red - a compose limit, a
# Prometheus rule, a runbook, a dead-code removal. `compass acceptance start`
# declares what the acceptance IS before the change (a validator that must pass,
# or a green suite that must stay green) and writes this marker. Without it,
# authors satisfied this hook by faking reds that grep a file for a string,
# which is worse than either alternative.
#
# It is a SEPARATE marker on purpose. `.red` means "a real failure was observed
# here"; overloading it would make the framework's most honest artifact
# ambiguous. `compass acceptance record` clears this one.
if [ -f "$TASK_DIR/.acceptance" ]; then
  exit 0
fi

# --- the red-before-green check (delivery routes) ---------------------------
if [ -f "$TASK_DIR/.red" ]; then
  # A failing test is on record for this task. Red came before green. Allow.
  exit 0
fi

# No .red marker → no failing test on record → block the code edit.
cat >&2 <<EOF
Compass: BLOCKED - no failing test on record for task '$TASK_SLUG'.

  Strategy S2 (red-before-green) applies on this route, in service of
  guardrail G1 (tested before it lands).
  Edit target: $TARGET  (tool: ${TOOL:-?})
  Guarded by  : ${MATCHED_RULE:-the built-in production-code set}

  To proceed the Compass way:
    1. Write the failing test for the scenario you are implementing.
    2. Record the red - run it through the CLI so the failure is observed
       and the evidence is captured:
         compass tdd-red -- <your failing test command>
       (this runs the test, confirms it fails, writes evidence/red.json,
        and drops the .red marker this hook checks for).
    3. Re-try this edit.

  Later, \`compass tdd-green -- <test command>\` confirms green, writes
  evidence/green.json, and clears the .red marker - the hand-off to Verify.

  If this is genuinely exploratory work, it should be a Spike route - re-run
  /compass:frame. The fix is to write the test or re-frame, not to route
  around the hook.
EOF
exit 2
