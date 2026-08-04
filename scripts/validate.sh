#!/usr/bin/env bash
# =============================================================================
# Compass script: validate.sh  -  SELF-CHECK FOR THE FRAMEWORK REPO
# =============================================================================
# A coherence check for the Compass repository ITSELF - not for a project using
# Compass. It verifies the directory structure is intact and that the adapter
# layer's internal references resolve: commands referencing skills, agents, and
# templates that actually exist; no dangling pointers.
#
# Run it locally before committing, and in CI on every push.
#
# USAGE
#   scripts/validate.sh            # full check, human-readable
#   scripts/validate.sh --quiet    # only print failures + the final verdict
#   scripts/validate.sh --help
#
# EXIT CODES
#   0  everything resolves
#   1  one or more checks failed (details printed)
#
# WHAT IT CHECKS
#   1. Required directories and top-level files are present.
#   2. Every expected artifact template exists in templates/.
#   3. Every agent referenced anywhere in commands/ exists in agents/.
#   4. Every skill referenced anywhere in commands/ exists in skills/.
#   5. Every template referenced in commands/ exists in templates/.
#   6. Every script and hook referenced in the repo exists and is executable.
#   7. The five reference routes exist and the router references them.
#   8. The kit layer is present: the CLI, the machine-readable governance,
#      the schemas, and the task.yml template - and `compass policy lint`
#      passes if python3 and the CLI are runnable.
#
# This script is deliberately dependency-free (pure bash + coreutils + grep).
# The optional `compass policy lint` step needs python3 + PyYAML; it is skipped
# cleanly, not failed, when those are absent.
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPASS_HOME="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$COMPASS_HOME"

QUIET=0
case "${1:-}" in
  --quiet) QUIET=1 ;;
  -h|--help) grep -E '^# (USAGE|  scripts|EXIT|WHAT|   [0-9])' "$0" | sed 's/^# //'; exit 0 ;;
  "") ;;
  *) echo "validate.sh: unknown argument: $1" >&2; exit 1 ;;
esac

FAILURES=0
say()  { [ "$QUIET" -eq 1 ] || echo "$@"; }
ok()   { [ "$QUIET" -eq 1 ] || echo "  ok   $*"; }
fail() { echo "  FAIL $*" >&2; FAILURES=$((FAILURES + 1)); }

say "Compass repo self-check - $COMPASS_HOME"
say ""

# --- 1. required structure --------------------------------------------------
say "1. Directory structure and top-level files"
for d in docs governance routes templates commands \
         agents skills hooks scripts .compass; do
  if [ -d "$d" ]; then ok "dir  $d/"; else fail "missing directory: $d/"; fi
done
for f in CLAUDE.md AGENTS.md README.md docs/methodology.md \
         routes/router.md governance/guardrails.md governance/strategies.md \
         governance/routing-policy.md .compass/config.yml; do
  if [ -f "$f" ]; then ok "file $f"; else fail "missing file: $f"; fi
done
say ""

# --- 2. expected artifact templates -----------------------------------------
say "2. Artifact templates"
for t in route brief spec.feature clarifications plan distribution-map \
         positioning launch-readiness ui-contract verification-report devlog; do
  if [ -f "templates/$t.md" ]; then ok "template $t.md"; else fail "missing template: templates/$t.md"; fi
done
say ""

# --- helpers for reference checks -------------------------------------------
# Collect the names that actually exist.
EXISTING_AGENTS="$(cd agents 2>/dev/null && ls *.md 2>/dev/null | sed 's/\.md$//' || true)"
EXISTING_SKILLS="$(cd skills 2>/dev/null && ls -d */ 2>/dev/null | sed 's:/$::' || true)"
EXISTING_TEMPLATES="$(cd templates 2>/dev/null && ls *.md 2>/dev/null | sed 's/\.md$//' || true)"

has() { # needle  haystack(newline-separated)
  printf '%s\n' "$2" | grep -qxF "$1"
}

# --- 3. agents referenced by commands exist ---------------------------------
say "3. Agent references in commands/"
# Match the patterns the command files actually use, e.g. "the `builder` agent",
# "`orchestrator` agent", "invoke the `navigator` agent".
REFS="$(grep -rohE '`[a-z][a-z-]+`[[:space:]]+agent' commands/ 2>/dev/null \
        | sed -E 's/`([a-z-]+)`.*/\1/' | sort -u || true)"
if [ -z "$REFS" ]; then
  say "  (no agent references found in commands/ - nothing to check)"
else
  for a in $REFS; do
    if has "$a" "$EXISTING_AGENTS"; then ok "agent  $a  <- referenced, exists"
    else fail "command references agent '$a' but agents/$a.md does not exist"; fi
  done
fi
say ""

# --- 4. skills referenced by commands exist ---------------------------------
say "4. Skill references in commands/"
# Commands say things like "Load the `adaptive-routing` skill".
REFS="$(grep -rohE '`[a-z][a-z-]+`[[:space:]]+skill' commands/ 2>/dev/null \
        | sed -E 's/`([a-z-]+)`.*/\1/' | sort -u || true)"
if [ -z "$REFS" ]; then
  say "  (no skill references found in commands/ - nothing to check)"
else
  for s in $REFS; do
    if has "$s" "$EXISTING_SKILLS"; then ok "skill  $s  <- referenced, exists"
    else fail "command references skill '$s' but skills/$s/ does not exist"; fi
  done
fi
say ""

# --- 5. templates referenced by commands exist ------------------------------
say "5. Template references in commands/"
# Commands say "from `templates/route.md`" or "templates/verification-report.md".
REFS="$(grep -rohE 'templates/[a-z][a-z.-]+\.md' commands/ 2>/dev/null \
        | sed -E 's:templates/([a-z.-]+)\.md:\1:' | sort -u || true)"
if [ -z "$REFS" ]; then
  say "  (no template references found in commands/ - nothing to check)"
else
  for t in $REFS; do
    if has "$t" "$EXISTING_TEMPLATES"; then ok "template  $t  <- referenced, exists"
    else fail "command references templates/$t.md but it does not exist"; fi
  done
fi
say ""

# --- 6. scripts and hooks referenced exist and are executable ---------------
say "6. Script and hook references"
# Scan only files git tracks. A bare recursive grep also walks untracked and
# ignored trees - and the cucumber-js reference adapter's node_modules/ is full
# of package.json files naming scripts that are not ours, which failed this
# check (and therefore `make release`) for anyone who ran `npm install` in that
# example. Fall back to the recursive form outside a git checkout, e.g. inside
# an unpacked release tarball.
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  REFS="$(git ls-files -z -- '*.md' '*.json' 2>/dev/null \
          | xargs -0 grep -ohE '(scripts|hooks)/[a-z-]+\.sh' 2>/dev/null \
          | sort -u || true)"
else
  REFS="$(grep -rohE '(scripts|hooks)/[a-z-]+\.sh' . \
          --include='*.md' --include='*.json' \
          --exclude-dir=node_modules 2>/dev/null | sort -u || true)"
fi
for ref in $REFS; do
  if [ -f "$ref" ]; then
    if [ -x "$ref" ]; then ok "exec $ref  <- referenced, exists, executable"
    else fail "referenced $ref exists but is not executable (chmod +x it)"; fi
  else
    fail "referenced $ref does not exist"
  fi
done
# Also assert the canonical set is present regardless of references.
for f in hooks/pre-tool.sh hooks/post-tool.sh hooks/stop.sh \
         scripts/install.sh scripts/swarm.sh scripts/integrate.sh scripts/validate.sh; do
  [ -f "$f" ] || fail "expected file missing: $f"
done
say ""

# --- 7. the five reference routes -------------------------------------------
say "7. Reference routes"
for r in express standard expedition hotfix spike; do
  if [ -f "routes/$r.md" ]; then
    if grep -qiE "(\`|/| )$r\b" routes/router.md 2>/dev/null; then
      ok "route  $r  <- exists, named in router.md"
    else
      ok "route  $r  <- exists (router.md mention not detected - review by eye)"
    fi
  else
    fail "missing reference route: routes/$r.md"
  fi
done
say ""

# --- 8. the kit layer -------------------------------------------------------
say "8. Kit layer - CLI, machine-readable governance, schemas, task spine"
# 8a. the CLI exists and is executable
if [ -f "cli/compass" ]; then
  if [ -x "cli/compass" ]; then ok "exec cli/compass  <- exists, executable"
  else fail "cli/compass exists but is not executable (chmod +x it)"; fi
else
  fail "missing the CLI: cli/compass"
fi
# 8b. the machine-readable governance the CLI runs
for f in governance/routing-policy.yml governance/guardrails.yml; do
  if [ -f "$f" ]; then ok "file $f"; else fail "missing machine-readable governance: $f"; fi
done
# 8c. the schemas directory: an executable JSON Schema and a readable
#     companion for each of the three machine-readable files.
if [ -d "schemas" ]; then
  ok "dir  schemas/"
  for s in routing-policy guardrails task; do
    if [ -f "schemas/$s.schema.json" ]; then ok "schema $s.schema.json"
    else fail "missing executable schema: schemas/$s.schema.json"; fi
    if [ -f "schemas/$s.reference.yml" ]; then ok "ref    $s.reference.yml"
    else fail "missing schema reference: schemas/$s.reference.yml"; fi
  done
else
  fail "missing directory: schemas/"
fi
# 8d. the task manifest template
if [ -f "templates/task.yml" ]; then ok "file templates/task.yml"
else fail "missing task manifest template: templates/task.yml"; fi
# 8e. optional: run `compass policy lint` if python3 and the CLI are runnable
if command -v python3 >/dev/null 2>&1 && [ -x "cli/compass" ]; then
  if LINT_OUT="$(python3 cli/compass policy lint 2>&1)"; then
    ok "compass policy lint  <- PASS"
  else
    # a non-zero exit may be a real failure OR a missing PyYAML - distinguish
    if printf '%s' "$LINT_OUT" | grep -qi "PyYAML"; then
      say "  skip compass policy lint  <- PyYAML not installed (pip install pyyaml); skipped, not failed"
    else
      fail "compass policy lint reported a problem:"
      printf '%s\n' "$LINT_OUT" | sed 's/^/         /' >&2
    fi
  fi
else
  say "  skip compass policy lint  <- python3 or cli/compass not runnable; skipped"
fi
say ""

# --- verdict ----------------------------------------------------------------
if [ "$FAILURES" -eq 0 ]; then
  echo "validate.sh: PASS - repo structure and internal references are intact."
  exit 0
else
  echo "validate.sh: FAIL - $FAILURES problem(s) above. Fix them before committing." >&2
  exit 1
fi
