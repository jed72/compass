#!/usr/bin/env bash
# =============================================================================
# compass-python.sh - the shell face of the one YAML-resolution mechanism
# =============================================================================
# Every shell script that embeds a Python reader (hooks/pre-tool.sh,
# hooks/stop.sh, scripts/integrate.sh, scripts/multiagent.sh) sources this file and
# calls compass_python instead of python3 directly, for exactly one reason:
# the bundled PyYAML at cli/vendor/yaml/ has to be the copy every one of these
# readers resolves, not whatever (if anything) is ambient on the machine.
#
# This file does NOT know where cli/vendor/ is. It only knows the framework
# root, and puts cli/ on PYTHONPATH so `import compass_pkg` works - the vendor
# path itself is written down in exactly one place, cli/compass_pkg/__init__.py
# (DD-2). A future move of the vendored tree is a one-line edit there, not a
# search-and-replace across every script that reads YAML.
#
# CONTRACT for every caller: open with these two imports, in this order:
#   import compass_pkg   # side effect: puts cli/vendor at sys.path[0]
#   import yaml
#
# This forks python3 rather than `exec`-ing it. An earlier version used `exec`
# to save a fork, reasoning that every caller sat inside a command
# substitution and so already had its own subshell. That was wrong twice. One
# caller was a plain statement that needed its own `( ... )` wrapper to
# survive. And `exec` destroys the shell holding the caller's error guard, so
# a reader that could not start took the calling script down with it - which
# switched `hooks/pre-tool.sh` off, silently, on any install where the
# vendored copy was missing. A fork per YAML read does not cost that.
#
# EXIT STATUS 3 means the vendored PyYAML could not be resolved and the reader
# never ran, with the reason on stderr. Callers must tell that apart from a
# reader that ran and found nothing: one is a broken install and should be
# said out loud, the other is the ordinary absence of state.
# =============================================================================

compass_python() {
  local root
  root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
  PYTHONPATH="$root/cli${PYTHONPATH:+:$PYTHONPATH}" python3 "$@"
}
