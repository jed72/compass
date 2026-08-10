#!/usr/bin/env bash
# =============================================================================
# compass-python.sh - the shell face of the one YAML-resolution mechanism
# =============================================================================
# Every shell script that embeds a Python reader (hooks/pre-tool.sh,
# hooks/stop.sh, scripts/integrate.sh, scripts/swarm.sh) sources this file and
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
# `exec` replaces the current shell with python3 rather than forking a child -
# safe here because every caller invokes compass_python inside a command
# substitution `$(...)`, which is already its own subshell.
# =============================================================================

compass_python() {
  local root
  root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
  PYTHONPATH="$root/cli${PYTHONPATH:+:$PYTHONPATH}" exec python3 "$@"
}
