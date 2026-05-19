#!/usr/bin/env bash
# =============================================================================
# Compass script: install.sh  —  WIRE COMPASS INTO CLAUDE CODE
# =============================================================================
# Installs the Claude Code adapter layer (commands/, agents/, skills/, hooks/)
# into the right Claude Code locations and registers the hooks in settings.
#
# The methodology layer (docs/, governance/, routes/, templates/) is NOT
# installed anywhere — it is read in place from this repo. What this script
# wires up is only the runtime adapter.
#
# USAGE
#   scripts/install.sh                 # project-local install (default)
#   scripts/install.sh --global        # user-global install (~/.claude)
#   scripts/install.sh --project DIR   # project-local into a specific project
#   scripts/install.sh --copy          # copy instead of symlink
#   scripts/install.sh --uninstall     # remove what a previous run installed
#
# DESTINATIONS
#   --global  : ~/.claude/{commands,agents,skills}/  + ~/.claude/settings.json
#   project   : <project>/.claude/{commands,agents,skills}/
#                                     + <project>/.claude/settings.json
#   hooks are referenced in place from this repo (COMPASS_HOME/hooks/), so the
#   settings.json entries point at absolute paths under this repo.
#
# IDEMPOTENT: re-running is safe. Existing Compass symlinks are refreshed;
# existing non-Compass files are never clobbered (the script stops and tells
# you). Hook registration is keyed by a marker so it is added exactly once.
# =============================================================================

set -euo pipefail

# --- locate this repo (COMPASS_HOME) ----------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPASS_HOME="$(cd "$SCRIPT_DIR/.." && pwd)"

# --- parse args -------------------------------------------------------------
MODE="project"          # project | global
PROJECT_DIR="$(pwd)"
LINK_MODE="symlink"     # symlink | copy
ACTION="install"        # install | uninstall

while [ $# -gt 0 ]; do
  case "$1" in
    --global)     MODE="global" ;;
    --project)    MODE="project"; PROJECT_DIR="$(cd "$2" && pwd)"; shift ;;
    --copy)       LINK_MODE="copy" ;;
    --uninstall)  ACTION="uninstall" ;;
    -h|--help)
      grep -E '^# (USAGE|  scripts)' "$0" | sed 's/^# //'
      exit 0 ;;
    *) echo "install.sh: unknown argument: $1" >&2; exit 1 ;;
  esac
  shift
done

# --- resolve the Claude Code destination root -------------------------------
if [ "$MODE" = "global" ]; then
  CLAUDE_ROOT="$HOME/.claude"
else
  CLAUDE_ROOT="$PROJECT_DIR/.claude"
fi
SETTINGS="$CLAUDE_ROOT/settings.json"

echo "Compass installer"
echo "  source (COMPASS_HOME): $COMPASS_HOME"
echo "  mode:                  $MODE"
echo "  destination:           $CLAUDE_ROOT"
echo "  link mode:             $LINK_MODE"
echo ""

# --- helper: link or copy one component directory ---------------------------
# Each of commands/agents/skills is installed as a subdirectory named
# "compass" so it cannot collide with anything else the user has — the
# resolved Claude Code path is ~/.claude/<name>/compass/<file>.
#
# NOTE the asymmetry in the repo layout: command files live in
# commands/compass/*.md (the slash-command namespace dir), but agent and skill
# files live directly in agents/*.md and skills/*/SKILL.md. So for commands we
# take the src one level deeper — otherwise the install double-nests and the
# commands resolve as /compass:compass:frame instead of /compass:frame.
install_component() {
  local name="$1"                      # commands | agents | skills
  local src="$COMPASS_HOME/$name"
  [ "$name" = "commands" ] && src="$COMPASS_HOME/commands/compass"
  local dest_parent="$CLAUDE_ROOT/$name"
  local dest="$dest_parent/compass"

  [ -d "$src" ] || { echo "  skip $name (not present in repo)"; return 0; }
  mkdir -p "$dest_parent"

  if [ -e "$dest" ] || [ -L "$dest" ]; then
    # Only refresh something we own — a symlink, or a dir we previously copied
    # (marked with .compass-installed). Never clobber the user's own files.
    if [ -L "$dest" ] || [ -f "$dest/.compass-installed" ]; then
      rm -rf "$dest"
    else
      echo "  ERROR: $dest exists and was not created by Compass — refusing to overwrite." >&2
      echo "         Move it aside and re-run." >&2
      exit 1
    fi
  fi

  if [ "$LINK_MODE" = "symlink" ]; then
    ln -s "$src" "$dest"
    echo "  linked  $name/compass -> $src"
  else
    cp -R "$src" "$dest"
    touch "$dest/.compass-installed"
    echo "  copied  $name/compass <- $src"
  fi
}

uninstall_component() {
  local name="$1"
  local dest="$CLAUDE_ROOT/$name/compass"
  if [ -L "$dest" ] || { [ -d "$dest" ] && [ -f "$dest/.compass-installed" ]; }; then
    rm -rf "$dest"
    echo "  removed $name/compass"
  fi
}

# --- helper: ensure a settings.json exists ----------------------------------
ensure_settings() {
  mkdir -p "$CLAUDE_ROOT"
  [ -f "$SETTINGS" ] || echo '{}' > "$SETTINGS"
}

# --- helper: register the three hooks in settings.json ----------------------
# Compass needs PreToolUse (pre-tool.sh), PostToolUse (post-tool.sh), and Stop
# (stop.sh). We splice them in with jq, keyed so re-running does not duplicate.
register_hooks() {
  ensure_settings
  local pre="$COMPASS_HOME/hooks/pre-tool.sh"
  local post="$COMPASS_HOME/hooks/post-tool.sh"
  local stop="$COMPASS_HOME/hooks/stop.sh"

  if ! command -v jq >/dev/null 2>&1; then
    echo ""
    echo "  NOTE: jq is not installed — cannot auto-register hooks."
    echo "        Add these to $SETTINGS by hand:"
    cat <<EOF
        "hooks": {
          "PreToolUse":  [ { "matcher": "Edit|Write|MultiEdit",
                             "hooks": [ { "type": "command", "command": "$pre" } ] } ],
          "PostToolUse": [ { "matcher": "Edit|Write|MultiEdit",
                             "hooks": [ { "type": "command", "command": "$post" } ] } ],
          "Stop":        [ { "hooks": [ { "type": "command", "command": "$stop" } ] } ]
        }
EOF
    return 0
  fi

  # Build the Compass hook block, then merge it in. We first strip any existing
  # Compass-owned entries (identified by the command path containing
  # "/hooks/pre-tool.sh" etc. under COMPASS_HOME) so the merge is idempotent.
  local tmp
  tmp="$(mktemp)"
  jq \
    --arg pre "$pre" --arg post "$post" --arg stop "$stop" '
    # drop any prior Compass entries so re-running does not duplicate
    def notcompass($paths): [ .hooks[]?.command ] as $cmds
      | ($cmds | map(. as $c | $paths | index($c)) | all(. == null));
    .hooks //= {} |
    .hooks.PreToolUse  = ( (.hooks.PreToolUse  // []) | map(select(notcompass([$pre])))  )
      + [ { matcher: "Edit|Write|MultiEdit", hooks: [ { type: "command", command: $pre } ] } ] |
    .hooks.PostToolUse = ( (.hooks.PostToolUse // []) | map(select(notcompass([$post]))) )
      + [ { matcher: "Edit|Write|MultiEdit", hooks: [ { type: "command", command: $post } ] } ] |
    .hooks.Stop        = ( (.hooks.Stop        // []) | map(select(notcompass([$stop]))) )
      + [ { hooks: [ { type: "command", command: $stop } ] } ]
  ' "$SETTINGS" > "$tmp"
  mv "$tmp" "$SETTINGS"
  echo "  registered hooks in $SETTINGS (PreToolUse, PostToolUse, Stop)"
}

unregister_hooks() {
  [ -f "$SETTINGS" ] || return 0
  command -v jq >/dev/null 2>&1 || { echo "  NOTE: jq missing — remove Compass hooks from $SETTINGS by hand."; return 0; }
  local pre="$COMPASS_HOME/hooks/pre-tool.sh"
  local post="$COMPASS_HOME/hooks/post-tool.sh"
  local stop="$COMPASS_HOME/hooks/stop.sh"
  local tmp; tmp="$(mktemp)"
  jq --arg pre "$pre" --arg post "$post" --arg stop "$stop" '
    def strip($p): map(select(([ .hooks[]?.command ] | index($p)) == null));
    if .hooks then
      .hooks.PreToolUse  = ((.hooks.PreToolUse  // []) | strip($pre)) |
      .hooks.PostToolUse = ((.hooks.PostToolUse // []) | strip($post)) |
      .hooks.Stop        = ((.hooks.Stop        // []) | strip($stop))
    else . end
  ' "$SETTINGS" > "$tmp"
  mv "$tmp" "$SETTINGS"
  echo "  unregistered Compass hooks from $SETTINGS"
}

# --- make the hooks executable (no-op if already) ---------------------------
chmod +x "$COMPASS_HOME"/hooks/*.sh 2>/dev/null || true
chmod +x "$COMPASS_HOME"/scripts/*.sh 2>/dev/null || true

# --- run ---------------------------------------------------------------------
if [ "$ACTION" = "uninstall" ]; then
  echo "Uninstalling..."
  uninstall_component commands
  uninstall_component agents
  uninstall_component skills
  unregister_hooks
  echo ""
  echo "Compass adapter layer removed. The methodology layer in $COMPASS_HOME is untouched."
  exit 0
fi

echo "Installing adapter layer..."
install_component commands
install_component agents
install_component skills
register_hooks

echo ""
echo "Done. Compass is wired into Claude Code ($MODE)."
echo ""
echo "Next steps:"
echo "  1. cd into the project you want to use Compass in."
echo "  2. Run  /compass:frame \"<your task>\"  — that's it. The default guardrails"
echo "     and strategies ship active, so the Needle computes a route with zero setup."
echo "  3. Optional, whenever you have governance to encode:  /compass:init  —"
echo "     it copies governance/ into the project so you can add project-specific"
echo "     guardrails and strategies. It is accretion, not a prerequisite."
echo ""
if [ "$MODE" = "global" ]; then
  echo "Note: a global install makes the /compass: commands available everywhere."
  echo "No per-project setup is required — /compass:frame works immediately; run"
  echo "/compass:init only when a project wants its own governance."
fi
