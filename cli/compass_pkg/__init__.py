"""The Compass CLI, as modules. `cli/compass` is the entry point."""
import os
import sys

# Compass ships its own copy of PyYAML so a machine with only python3 can run
# it. The copy wins over any system-installed PyYAML, deliberately and
# unconditionally: position 0 beats PYTHONPATH and site-packages both, so the
# parser Compass runs is the same one everywhere Compass runs. Importing any
# module in this package runs this first, which is what stops a caller
# resolving YAML some other way - see cli/vendor/README.md and
# THIRD-PARTY-NOTICES.md for what is vendored and why.
_VENDOR = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, "vendor")
_VENDOR = os.path.normpath(_VENDOR)
_VENDOR_YAML = os.path.join(_VENDOR, "yaml")
if _VENDOR not in sys.path:
    sys.path.insert(0, _VENDOR)


def _incomplete_install(detail):
    """Print the same "this install is incomplete" message every entry point
    already shows on a missing PyYAML, then exit 3. Centralised here so the
    message and the exit code are one fact this module owns, not something
    duplicated - and drifting - per caller."""
    sys.stderr.write(
        "compass: this install is incomplete - PyYAML did not resolve from "
        f"the bundled copy at {_VENDOR_YAML}.\n"
        f"  {detail}\n"
        "  Compass ships its own copy; there is no package to install.\n"
        "  Reinstall the plugin so cli/vendor/yaml/ is present and intact.\n"
    )
    sys.exit(3)


# Inserting a path at sys.path[0] that does not exist is a silent no-op:
# Python just keeps looking further down sys.path, and on a machine that also
# has a system PyYAML - exactly the population that followed the old
# instruction to install it by hand - `import yaml` below would succeed
# against THAT copy instead, with no warning at all. That is the opposite of
# "the bundled copy always wins, unconditionally" (DD-3, ADR-013 Decision 3),
# so absence is checked explicitly, before any import is attempted, rather
# than inferred from whether an import happens to fail.
if not os.path.isdir(_VENDOR_YAML):
    _incomplete_install(
        f"{_VENDOR_YAML} does not exist - the vendored directory is absent.")

try:
    import yaml as _compass_vendor_check
except ImportError as _exc:
    # The directory is there, but `import yaml` still failed - a source file
    # is missing or unreadable. This is a different failure from absence, and
    # the message has to say so: "could not be found" sends someone looking
    # for a directory that already exists.
    _incomplete_install(
        f"the directory exists but 'import yaml' still failed ({_exc}) - "
        f"the vendored source is present but damaged or incomplete.")
else:
    # The import succeeded, but from where? Nothing above guarantees it was
    # the bundled copy - only that Python found *a* module named `yaml`
    # somewhere on sys.path. Compare the file it actually loaded against the
    # directory this module just inserted; if they disagree, some other
    # PyYAML on the machine answered first, and running against an
    # undocumented copy at an undocumented version is not what "the bundled
    # copy always wins" means.
    _resolved_dir = os.path.dirname(
        os.path.realpath(os.path.abspath(_compass_vendor_check.__file__)))
    _vendor_real = os.path.realpath(_VENDOR_YAML)
    if _resolved_dir != _vendor_real:
        _incomplete_install(
            f"PyYAML resolved from {_resolved_dir} instead - a different "
            f"copy on this machine answered ahead of the bundled one, which "
            f"should never happen.")
    del _resolved_dir, _vendor_real, _compass_vendor_check
