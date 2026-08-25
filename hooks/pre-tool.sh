#!/usr/bin/env bash
# =============================================================================
# Compass hook: pre-tool.sh  -  THE RED-BEFORE-GREEN STRATEGY ENFORCER
# =============================================================================
# Enforces the red-before-green strategy mechanically - in service of the
# guardrail that every change lands with a passing automated test covering it.
# Note the distinction, because it is the whole point of Compass's governance
# model:
#
#   * The GUARDRAIL is the hard line: no code ships without a passing test it
#     traces to. It is checked at the test-and-review stage and at ship time,
#     with evidence.
#   * Red-before-green is a STRATEGY - the strong, shipped-on *way* to satisfy
#     that guardrail. This hook enforces the strategy, and a strategy is aware
#     of the delivery approach.
#
# This hook therefore BLOCKS code edits with no failing test on record - EXCEPT
# on a spike, where the strategy is deliberately suspended so exploration is
# not throttled. A spike still cannot cross the guardrail: nothing ships from a
# spike without graduating (re-assessing) into a real delivery approach first,
# where this hook applies in full.
#
# WHAT IT DOES
#   Runs as a Claude Code PreToolUse hook. On a tool call that edits or writes a
#   *code* file (not a test, not docs, not a Compass artifact):
#     - if the current issue is a spike (a ".spike" marker exists) → ALLOW.
#     - else, require a recorded failing test - a ".red" marker file under
#       .compass/work/<task-slug>/. No .red marker → the edit is BLOCKED.
#
# THE MARKER CONVENTION  (this is the "not magic" part - read this)
#   .compass/work/<task-slug>/.red    "a failing test currently exists for this
#                                      issue". It is NOT a bare `touch` - it is
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
#   .compass/work/<task-slug>/.spike  "this issue is a spike - the red-
#                                      before-green strategy is suspended".
#                                      /compass:assess
#                                      writes this when it composes a Spike.
#   Markers are deliberately plain files so they are inspectable and auditable;
#   the evidence/*.json records next to them are the audit trail.
#
# ESCAPE HATCH
#   Test files, docs, config, and .compass/ artifacts are never blocked - you
#   must be able to write the failing test in the first place. A spike
#   is the *intentional* escape hatch for exploratory work. There is no env var
#   to disable the check on delivery work: that would not be suspending a
#   strategy, it would be crossing the tested-before-ship guardrail.
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

# shellcheck source=../scripts/lib/compass-python.sh
# The one shared mechanism (DD-2): compass_python() below reaches the bundled
# PyYAML the same way cli/compass does, rather than this hook inventing its
# own answer to "where is the vendored copy".
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/lib/compass-python.sh"

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

# --- resolve the project this hook is enforcing -----------------------------
# CLAUDE_PROJECT_DIR is authoritative when the host sets it. When it does not
# - and it does not always - fall back to the nearest ancestor of the working
# directory that contains a .compass/ directory, the way git finds its repo.
#
# The previous fallback was a bare $(pwd), which assumed the session started
# at the repository root. Started anywhere else, the hook looked for .compass/
# in the wrong place, found none, and blocked every edit while reporting that
# triage had not run - when it had. Two faults: the resolution, and a
# diagnostic naming a cause that was not the cause.
#
# Deliberately NOT resolved from this script's own location: the hook is
# installed from the plugin cache, and Compass self-hosts, so its own tree has
# a .compass/ of its own. That would enforce the framework's issue against the
# user's edits.
INVOKED_FROM="$(pwd)"
if [ -n "${CLAUDE_PROJECT_DIR:-}" ]; then
  PROJECT_DIR="$CLAUDE_PROJECT_DIR"
else
  PROJECT_DIR=""
  _search="$INVOKED_FROM"
  while [ -n "$_search" ]; do
    if [ -d "$_search/.compass" ]; then
      PROJECT_DIR="$_search"
      break
    fi
    # The repository is the outer bound of a project. A directory holding
    # .git and no .compass/ has not been triaged, and the honest answer is
    # to refuse rather than borrow a parent's answer: an unbounded walk
    # would resolve a stranger's issue - a monorepo sibling, or a stray
    # .compass/ in $HOME - and if that issue happened to be mid-red, ALLOW
    # the edit. A fail-open path inside the fix that exists to close one.
    #
    # -e, not -d: in a git worktree .git is a file, and Compass creates
    # worktrees itself for swarm topologies.
    [ -e "$_search/.git" ] && break
    [ "$_search" = "/" ] && break
    _search="$(dirname "$_search")"
  done
fi

# Whether the walk found anything is recorded, not acted on yet. The refusal
# lives further down, at the point the hook actually needs issue state - a
# read-only Bash call is allowed without a project at all, and refusing here
# would make the cheap path expensive and wrong.
# An EXPLICIT root is taken at its word. `.compass/` does not exist until
# triage runs, so treating its absence as "I could not find your project"
# tells the author on their very first edit to fix a working directory that
# is already correct - the same misdiagnosis this resolution work exists to
# remove, one branch earlier. Only the walk failing means the project is
# genuinely unfindable; the missing-.compass/work/ branch further down says
# the useful thing.
PROJECT_RESOLVED=1
if [ -z "$PROJECT_DIR" ]; then
  PROJECT_RESOLVED=0
  # Provisional, so path classification below still has something to compare
  # against. Nothing is permitted on the strength of it.
  PROJECT_DIR="$INVOKED_FROM"
fi

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
  local target="$1" rel base is_code=0 abs

  # CONTAINMENT FIRST: only guard what is inside the project Compass governs.
  #
  # Without this, the extension rules below fired on any .py/.ts/.go file
  # anywhere on the machine - a scratch file in a session temp directory, a
  # throwaway script in a detached worktree. Neither can reach `main` by any
  # path, and the refusal told the author to write a failing test or re-run
  # triage as a spike, neither of which is a coherent action for such a file.
  # A guardrail issuing unactionable instructions teaches people to look for
  # the bypass. Reported from the field.
  #
  # The target is resolved first, because a Bash redirect yields a RELATIVE
  # path: comparing `src/app.py` against an absolute project directory would
  # answer "outside" and switch enforcement off for exactly the writes the
  # hook is here for.
  # Resolved against PROJECT_DIR, not the hook's own working directory. The
  # hook cannot know the shell's cwd, and guessing wrong in that direction
  # fails OPEN - a relative write would be judged outside the project and
  # allowed. A relative path in an agent's command is against the project root
  # in practice, and being wrong the other way costs only a visible refusal.
  abs="$target"
  case "$abs" in
    /*) ;;
    *) abs="$PROJECT_DIR/$abs" ;;
  esac
  case "$abs" in
    "$PROJECT_DIR"/*) ;;
    *) return 1 ;;
  esac

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
  # ANCHORED, not a substring match. `*test*` called latest.py, inspector.py
  # and protest.py tests, and silently skipped both guardrail checks for them -
  # on the allow path, which prints nothing. An earlier fix narrowed this from
  # the absolute path to the basename after a clone under /Users/testuser/
  # switched enforcement off entirely; that narrowed the class without closing
  # it.
  #
  # The conventions covered: pytest/go (test_x, x_test), jest/vitest
  # (x.test.ts, x.spec.js), JUnit/RSpec class names (XTest.java, XSpec.rb),
  # and Ruby's x_spec.rb. Directory rules below catch the rest.
  case "$base" in
    test_*|spec_*) return 1 ;;
    *_test.*|*_spec.*|*.test.*|*.spec.*) return 1 ;;
    *Test.*|*Spec.*|*Tests.*|*Specs.*) return 1 ;;
    conftest.py) return 1 ;;
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
    local hit glob_status glob_err
    # Same two-failures-look-alike problem as the spine read below. A reader
    # that ran and matched nothing means the path is not project-guarded. A
    # reader that could not start means we do not know whether it is - and
    # answering "not guarded" to a question we could not ask is how a broken
    # install quietly stops guarding the very scripts that broke it.
    glob_err="$(mktemp)"
    set +e
    hit="$(compass_python - "$PROJECT_DIR/.compass/config.yml" "$rel" 2>"$glob_err" <<'PYEOF'
import fnmatch, sys
import compass_pkg
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
    glob_status=$?
    set -e
    if [ "$glob_status" -eq 3 ]; then
      # Treat the path as guarded. The spine read that follows will refuse
      # with the install's own diagnostics, so the person gets one clear
      # message rather than a silent pass here and a puzzle later.
      MATCHED_RULE="unknown - the project's declared paths could not be read ($(head -1 "$glob_err"))"
      rm -f "$glob_err"
      return 0
    fi
    rm -f "$glob_err"
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

# --- find the current issue -------------------------------------------------
# The current issue is named by the .compass/current-task pointer (written by
# /compass:assess and /compass:resume). The pointer is what makes this reliable
# when more than one issue is in flight - "most recently modified directory"
# is only the fallback, and it is ambiguous, so it warns. If there is no issue
# all, triage has not run - CLAUDE.md's one rule is "Never skip triage".
# This is the first point that needs issue state, so it is the first point at
# which an unresolved project matters. Unresolved means the hook cannot tell
# what it is enforcing, so it refuses: an enforcement path that answers
# "allow" to a question it could not ask is a guardrail switched off
# silently. That is the same failure fixed one layer down in 2.1.0, where a
# missing vendored library made this hook exit 3 and the runtime read it as
# permission.
if [ "$PROJECT_RESOLVED" -eq 0 ]; then
  echo "Compass: could not locate a Compass project - no .compass/ directory at or above $INVOKED_FROM" >&2
  echo "  Start Claude Code inside the project, or set CLAUDE_PROJECT_DIR to its root." >&2
  echo "  Refusing this edit rather than allowing it unchecked." >&2
  exit 2
fi

COMPASS_DIR="$PROJECT_DIR/.compass"
WORK_DIR="$COMPASS_DIR/work"
if [ ! -d "$WORK_DIR" ]; then
  echo "Compass: no .compass/work/ in $PROJECT_DIR - triage has not run. Run /compass:assess before changing code." >&2
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
  [ -n "$TASK_DIR" ] && echo "Compass: no .compass/current-task pointer - falling back to the most recently modified issue ($(basename "$TASK_DIR")). Write .compass/current-task to be unambiguous." >&2
fi

if [ -z "${TASK_DIR:-}" ]; then
  echo "Compass: no issue under $PROJECT_DIR/.compass/work/ - triage has not run for this change." >&2
  exit 2
fi

TASK_SLUG="$(basename "$TASK_DIR")"

# The delivery-approach record must exist - code work without a computed
# approach is process laundering. Both filename generations are accepted:
# the archive predating the artifact rename still uses the retired filename.
# An issue directory written before the artifact rename still resolves here.
# vocabulary-scan: allow - names the retired filename on purpose
if [ ! -f "$TASK_DIR/delivery-approach.md" ] && [ ! -f "$TASK_DIR/route.md" ]; then
  echo "Compass: issue '$TASK_SLUG' has no delivery-approach.md - triage did not complete. Run /compass:assess." >&2
  exit 2
fi

# --- approach-aware: red-before-green is suspended on a spike ----------------
# /compass:assess writes a .spike marker when it computes a spike. On a
# spike, exploration is not throttled - the red-before-green strategy is
# suspended. The tested-before-ship guardrail is NOT: nothing ships from a
# spike without graduating into a real delivery approach, where this hook
# applies in full.
if [ -f "$TASK_DIR/.spike" ]; then
  exit 0
fi

# --- the guardrail: acceptance defined before it is built --------------------
# The check below enforces red-before-green, which serves the guardrail that
# every change lands with a passing test. Nothing enforced the OTHER guardrail
# - acceptance stated and checkable before the code - at the point where it can
# still be true. So an approach asking for full acceptance criteria could go
# straight from triage to implementation with no spec at all: every edit
# allowed, because a red was on record and red-before-green was satisfied.
# `compass check` catches it at the test-and-review stage, after the code
# exists, which is the ordering the acceptance guardrail exists to prevent.
#
# A guardrail beats a strategy, so this runs BEFORE the red check: you cannot
# write a red for a scenario that does not exist yet.
#
# Only `specify: full` triggers it, which routing-policy.yml gives to feature
# and initiative work. A hotfix (reproduce-first) and a spike (collapsed) are
# exempt by construction, and the .spike early exit above suspends this the
# same way it suspends red-before-green.
#
# If the spine cannot be read - no task.yml, unparseable YAML, no python3, no
# PyYAML - this stays silent and the prior behaviour applies. A false block on
# unreadable state is how a hook teaches people to bypass it.
if [ -f "$TASK_DIR/task.yml" ] && command -v python3 >/dev/null 2>&1; then
  # Two failures look alike from here and must not be treated alike. A reader
  # that RAN and found nothing is ordinary - stay quiet, as below. A reader
  # that could not START means the install is broken, and a guardrail that
  # cannot read its own state must refuse rather than wave the edit through.
  # compass_python exits 3 for exactly that, with the reason on stderr.
  G2_ERR="$(mktemp)"
  set +e
  G2_VERDICT="$(compass_python - "$TASK_DIR/task.yml" 2>"$G2_ERR" <<'PYEOF'
import sys
import compass_pkg
try:
    import yaml
    with open(sys.argv[1], encoding="utf-8") as fh:
        task = yaml.safe_load(fh) or {}
    if not isinstance(task, dict):
        raise ValueError
except Exception:
    # Exit 0 means ALLOW, and that is deliberate: an unreadable or missing
    # spine falls back to the behaviour this hook had before the check
    # existed, rather than inventing a block. A false block on unreadable
    # state trains people to bypass the hook, which costs more than the case
    # it would catch. Pinned by test_scn_f1. The separate status-3 path below
    # is for the check being unable to RUN (a broken install), which is a
    # different thing from the spine being unreadable.
    sys.exit(0)
stages = task.get("stages") or task.get("phases") or {}
# BOTH spellings. `define` is the key this framework writes; `specify` is the
# one it wrote before the v2 vocabulary freeze, and 107 archived spines still
# say it. Reading only `specify` - which this did until 2026-08-25 - meant
# `compass migrate --apply` silently switched the guardrail OFF for every
# directory it converted, because the migrated spine no longer used the word
# the guardrail was looking for.
if isinstance(stages, dict):
    weight = stages.get("define", stages.get("specify"))
    if weight == "full" and not (task.get("scenarios") or []):
        print("block")
PYEOF
)"
  G2_STATUS=$?
  set -e
  if [ "$G2_STATUS" -eq 3 ]; then
    cat >&2 <<EOF
Compass: BLOCKED - the enforcement check could not run.

$(cat "$G2_ERR")
  This hook cannot read the issue spine, so it cannot tell whether the
  acceptance criteria exist. It refuses rather than allowing an edit it was
  unable to check - a guardrail that cannot read its own state must fail
  closed, or it is not a guardrail.
  Edit target: $TARGET  (tool: ${TOOL:-?})

  Fix the install and re-try. Nothing about this issue is wrong.
EOF
    rm -f "$G2_ERR"
    exit 2
  fi
  rm -f "$G2_ERR"
  if [ "${G2_VERDICT:-}" = "block" ]; then
    cat >&2 <<EOF
Compass: BLOCKED - the delivery approach says specify: full, but task.yml has no scenarios.

  The acceptance-before-code guardrail. No code is written that no stated,
  checkable acceptance criterion describes - and a guardrail beats a
  strategy, so this is checked before the red.
  Edit target: $TARGET  (tool: ${TOOL:-?})
  Guarded by  : ${MATCHED_RULE:-the built-in production-code set}

  To proceed the Compass way:
    1. Write the scenarios into .compass/work/$TASK_SLUG/acceptance-criteria.md.
    2. Mirror them into task.yml's \`scenarios:\` block - each with an id, a
       linked intent, and the test(s) that will exercise it:
         compass scenario add SCN-001 --title "..." --intent INT-1
    3. Re-try this edit.

  If this is genuinely exploratory work it should be a spike, where this is
  suspended - re-run /compass:assess. The fix is to state the acceptance or
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

# --- the red-before-green check (delivery work) -----------------------------
if [ -f "$TASK_DIR/.red" ]; then
  # A failing test is on record for this issue. Red came before green. Allow.
  exit 0
fi

# No .red marker → no failing test on record → block the code edit.
cat >&2 <<EOF
Compass: BLOCKED - no failing test on record for issue '$TASK_SLUG'.

  The red-before-green strategy applies on this delivery approach, in
  service of the guardrail that a change ships only with a passing test.
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

  If this is genuinely exploratory work, it should be a spike - re-run
  /compass:assess. The fix is to write the test or re-frame, not to route
  around the hook.
EOF
exit 2
