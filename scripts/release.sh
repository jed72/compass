#!/usr/bin/env bash
# =============================================================================
# Compass - release packaging script
# =============================================================================
# Produces a clean tarball of the framework: `dist/compass-<version>.tar.gz`.
#
# What it does, in order:
#   1. Runs the self-check (validate.sh) - refuses to package a broken repo.
#   2. Runs `compass policy lint` - refuses to package broken governance.
#   3. Runs the test suite - refuses to package with a red CLI.
#   4. Confirms the worked examples are actually present (the v1 review caught
#      a packaging miss where examples/README.md shipped without the examples).
#   5. Builds the tarball, EXCLUDING noise (.DS_Store, __pycache__, *.bak,
#      .pytest_cache, __MACOSX, *.pyc) and dev-only state (.git, .compass/work).
#   6. Prints what is inside the tarball and its size, so the human can see.
#
# This script is the answer to the review's "release packaging hygiene"
# concern: users infer quality from the artifact, and a manual Finder zip
# carrying .DS_Store is not the artifact you want.
# =============================================================================

set -euo pipefail

# --- locate the repo --------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPASS_HOME="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$COMPASS_HOME"

# --- args -------------------------------------------------------------------
SKIP_TESTS=0
SKIP_LINT=0
while [ $# -gt 0 ]; do
  case "$1" in
    --skip-tests) SKIP_TESTS=1 ;;
    --skip-lint)  SKIP_LINT=1 ;;
    -h|--help)
      sed -n '2,18p' "$0" | sed 's/^# //; s/^#//'
      exit 0 ;;
    *) echo "release.sh: unknown argument: $1" >&2; exit 1 ;;
  esac
  shift
done

VERSION="$(tr -d '[:space:]' < VERSION)"
[ -n "$VERSION" ] || { echo "release.sh: VERSION file is empty" >&2; exit 1; }

echo "Compass release packager"
echo "  version  : $VERSION"
echo "  source   : $COMPASS_HOME"
echo ""

# --- 1. self-check ----------------------------------------------------------
echo "[1] scripts/validate.sh"
bash scripts/validate.sh >/dev/null
echo "    PASS"

# --- 2. policy lint ---------------------------------------------------------
echo "[2] compass policy lint"
if [ "$SKIP_LINT" -eq 0 ]; then
  python3 cli/compass policy lint >/dev/null
  echo "    PASS"
else
  echo "    skipped (--skip-lint)"
fi

# --- 3. test suite ----------------------------------------------------------
echo "[3] tests"
if [ "$SKIP_TESTS" -eq 0 ]; then
  if command -v python3 >/dev/null 2>&1 && [ -d tests ]; then
    PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest tests/ -q >/dev/null
    echo "    PASS"
  else
    echo "    skipped (no python3 or no tests/)"
  fi
else
  echo "    skipped (--skip-tests)"
fi

# --- 4. examples present ----------------------------------------------------
echo "[4] worked examples are actually present"
required_examples="express-typo standard-api-change hotfix-regression expedition-new-subsystem spike-technical-unknown"
missing=""
for e in $required_examples; do
  if [ ! -f "examples/$e/.compass/work"/*/task.yml ] 2>/dev/null; then
    # the glob expands; check more carefully
    if ! find "examples/$e" -name task.yml -type f 2>/dev/null | grep -q .; then
      missing="$missing $e"
    fi
  fi
done
if [ -n "$missing" ]; then
  echo "    FAIL - missing example task.yml(s):$missing"
  exit 1
fi
echo "    PASS - all 5 example task.yml(s) present"

# --- 5. clear stale artifacts and build the tarball -------------------------
echo "[5] building tarball"
mkdir -p dist
# Wipe any previous tarball - the v1 review caught a state where dist/
# carried both the rc and the final tarball, which is confusing. One
# artifact per build. (The || true handles read-only filesystems / sandbox
# locks gracefully - on a real machine this deletes cleanly.)
find dist -maxdepth 1 -type f \( -name '*.tar.gz' -o -name '*.zip' \) \
  -exec rm -f {} + 2>/dev/null || true
# If anything is still hanging around (sandbox-locked), refuse to ship -
# we will not publish a dist/ with multiple artifacts.
STALE="$(find dist -maxdepth 1 -type f \( -name '*.tar.gz' -o -name '*.zip' \) 2>/dev/null || true)"
if [ -n "$STALE" ]; then
  echo "release.sh: WARNING - dist/ still contains stale artifact(s):" >&2
  echo "$STALE" | sed 's/^/    /' >&2
  echo "    Remove them by hand and re-run \`make release\` so dist/ holds one tarball." >&2
fi
OUT="dist/compass-${VERSION}.tar.gz"

# Files that genuinely belong in the release. Tar excludes are listed
# explicitly - be conservative and visible about what we ship.
#
# CRITICAL: patterns with a leading `./` are ROOT-ANCHORED - they match
# only at the top of the archive. Without the `./`, tar matches the pattern
# ANYWHERE in the path, which is what previously dropped
# `examples/<x>/.compass/work/<slug>/task.yml` from the release. The repo's
# own .compass/work and the rest of the framework's dev state must be
# anchored; noise patterns that legitimately should match anywhere
# (__pycache__, .DS_Store, *.bak) stay un-anchored.
tar -czf "$OUT" \
  --exclude='./.git' \
  --exclude='./.git/*' \
  --exclude='./.gitignore' \
  --exclude='./.github' \
  --exclude='./.github/*' \
  --exclude='./dist' \
  --exclude='./dist/*' \
  --exclude='./build' \
  --exclude='./.compass/work' \
  --exclude='./.compass/work/*' \
  --exclude='./.compass/flow' \
  --exclude='./.compass/flow/*' \
  --exclude='./.compass/current-task' \
  --exclude='./_deltest' \
  --exclude='./_deltest/*' \
  --exclude='./commands/roles' \
  --exclude='./commands/roles/*' \
  --exclude='./pytest-cache-files-*' \
  --exclude='./pytest-cache-files-*/*' \
  --exclude='.DS_Store' \
  --exclude='__MACOSX' \
  --exclude='__MACOSX/*' \
  --exclude='__pycache__' \
  --exclude='__pycache__/*' \
  --exclude='*.pyc' \
  --exclude='*.pyo' \
  --exclude='.pytest_cache' \
  --exclude='.pytest_cache/*' \
  --exclude='.coverage' \
  --exclude='.mypy_cache' \
  --exclude='.mypy_cache/*' \
  --exclude='*.bak' \
  --exclude='node_modules' \
  --exclude='*.tar.gz' \
  --exclude='*.zip' \
  --exclude='.idea' \
  --exclude='.vscode' \
  --transform "s,^,compass-${VERSION}/," \
  .

echo "    wrote $OUT"
echo ""

# --- 6. report --------------------------------------------------------------
SIZE="$(du -h "$OUT" | cut -f1)"
FILES="$(tar -tzf "$OUT" | wc -l | tr -d ' ')"
echo "Tarball summary:"
echo "  path     : $OUT"
echo "  size     : $SIZE"
echo "  files    : $FILES"
echo ""
echo "  top-level entries:"
tar -tzf "$OUT" | awk -F/ 'NF<=2 && $2!=""' | sort -u | sed 's/^/    /'
echo ""
# Materialise the tarball listing once. The verification loops grep against
# this string rather than re-piping `tar | grep` per check - `tar | grep -q`
# under `set -o pipefail` triggers SIGPIPE in tar when grep exits on first
# match, which makes the pipeline status non-zero even though grep matched.
# Reading the listing into a variable side-steps that entirely.
TAR_LIST="$(tar -tzf "$OUT")"

# --- noise check (HARD FAIL) -----------------------------------------------
# The previous release printed noise but did not fail on it. The v1 review
# rightly called that out: a release script that *reports* dirt is not the
# same as a release script that *refuses to ship* dirt.
echo "  noise check (must be empty):"
NOISE="$(printf '%s\n' "$TAR_LIST" | grep -E '\.DS_Store$|__MACOSX|__pycache__|\.pytest_cache|\.bak$|_deltest|pytest-cache-files-' || true)"
if [ -n "$NOISE" ]; then
  echo "$NOISE" | sed 's/^/    !!  /' >&2
  echo "release.sh: FAIL - tarball contains noise files (see above). Fix the excludes in scripts/release.sh and rebuild." >&2
  exit 1
fi
echo "    (clean - none)"

# --- examples integrity check (HARD FAIL) ----------------------------------
# The previous tarball stripped `examples/<x>/.compass/work/<slug>/task.yml`
# because the .compass/work exclude was not root-anchored. Verify directly:
# every example must have its task.yml in the tarball.
echo "  examples integrity (every example must have its task.yml):"
required_examples="express-typo standard-api-change hotfix-regression expedition-new-subsystem spike-technical-unknown"
missing=""
for e in $required_examples; do
  if ! printf '%s\n' "$TAR_LIST" | grep -q "examples/$e/\.compass/work/.*/task\.yml"; then
    missing="$missing $e"
  fi
done
if [ -n "$missing" ]; then
  echo "    !!  missing example task.yml in tarball:$missing" >&2
  echo "release.sh: FAIL - examples were not packaged correctly. Check the .compass/work exclude is root-anchored (./.compass/work, not .compass/work)." >&2
  exit 1
fi
for e in $required_examples; do
  tf="$(printf '%s\n' "$TAR_LIST" | grep "examples/$e/\.compass/work/.*/task\.yml" | head -1)"
  echo "    OK $tf"
done

echo ""
echo "Done. Inspect the tarball before uploading:"
echo "  tar -tzf $OUT | less"
