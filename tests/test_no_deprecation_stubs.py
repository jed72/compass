"""No deprecation stub survives the major version.

The v2 vocabulary freeze renamed the pipeline's commands and verbs, leaving a
redirect behind each one for "one major version". That window was written for
adopters, and there are none - so every redirect was a promise kept to nobody,
and the window would have closed the moment someone installed from the
marketplace.

ADR-014 removes them at 3.0.0 while the cost is zero. What stays is the
migrator's v1-to-v2 mapping, which is a translation table rather than a
redirect: a stub answers a caller who used the old name, a mapping reads a
file that used it.

The removal is also what makes ADR-015 possible - a scan cannot ban a name
the machinery still answers to.

Spec: .compass/work/rehearsal-cli-defects/acceptance-criteria.md (group F).
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CLI = ROOT / "cli" / "compass"
COMMANDS = ROOT / "commands"

# The seven retired pipeline commands, by the file that would redirect them.
RETIRED_COMMANDS = (
    "build.md", "clarify.md", "distribute.md", "frame.md",
    "land.md", "plan.md", "specify.md",
)

# The retired verbs and verb pairs. Each used to exit 2 with a one-line
# pointer naming its replacement. The full set is carried here because this
# file replaces the test that used to assert the pointer contract - dropping
# a spelling in the handover would retire a check silently.
RETIRED_VERBS = (
    ("route", "evaluate"),
    ("backfill", "pay"),
    ("calibration",),
    ("land-commit",),
    ("task", "lint"),
    ("plan", "lint"),
)


def test_rcd_f1_no_retired_slash_commands():
    """No command file exists whose only content is a redirect."""
    present = [name for name in RETIRED_COMMANDS if (COMMANDS / name).is_file()]
    assert not present, (
        f"retired slash-command stubs are still shipped: {', '.join(present)}. "
        f"ADR-014 removes them at the major version."
    )

    # And nothing new has quietly taken their place: no shipped command may
    # describe itself as a retired name. Checked by content as well as by
    # filename, so a rename of the stub file does not slip past.
    redirects = [
        p.name for p in COMMANDS.glob("*.md")
        if "retired name" in p.read_text(encoding="utf-8").lower()
    ]
    assert not redirects, (
        f"command file(s) still describe themselves as a retired name: "
        f"{', '.join(redirects)}"
    )


def test_rcd_f2_retired_verb_is_unknown():
    """A retired verb fails the way any unrecognised verb fails.

    Distinguished from the old behaviour by the pointer's own wording, not by
    the exit code: the pointer exited 2 and so does argparse on an unknown
    verb, so an exit-code assertion alone would pass against the stub.
    """
    for argv in RETIRED_VERBS:
        spelling = " ".join(argv)
        result = subprocess.run(
            [sys.executable, str(CLI), *argv],
            cwd=str(ROOT), capture_output=True, text=True, timeout=60,
        )
        combined = (result.stdout + result.stderr).lower()

        assert result.returncode != 0, (
            f"`compass {spelling}` succeeded - a retired verb must fail"
        )
        assert "renamed" not in combined, (
            f"`compass {spelling}` still prints the retired-spelling "
            f"pointer:\n{combined}"
        )
        assert "for one major version" not in combined, (
            f"`compass {spelling}` still promises the retired spelling is "
            f"kept:\n{combined}"
        )


def test_rcd_f2b_the_live_verb_still_works():
    """The control: removing the pointer must not remove the replacement.

    Without this, F2 passes against a CLI where `approach` was deleted too.
    """
    result = subprocess.run(
        [sys.executable, str(CLI), "approach", "evaluate", "--help"],
        cwd=str(ROOT), capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, (
        f"`compass approach evaluate` - the live spelling - does not work:\n"
        f"{result.stdout}{result.stderr}"
    )


def test_rcd_f2c_the_pointer_machinery_is_gone():
    """The data that fed the pointer goes with it.

    Leaving `verbs:`/`subverbs:` in migrate-map.yml would be dead data that
    reads like a live contract to the next person who opens the file.
    """
    import yaml
    sys.path.insert(0, str(ROOT / "cli"))
    import compass_pkg                                   # noqa: F401

    data = yaml.safe_load((ROOT / "cli" / "migrate-map.yml").read_text()) or {}
    for section in ("verbs", "subverbs"):
        assert section not in data, (
            f"migrate-map.yml still carries `{section}:`, which existed only "
            f"to feed the retired-verb pointer that ADR-014 removes"
        )
