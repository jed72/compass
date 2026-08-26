"""Every verb says what it does when asked.

`compass check --help` printed a usage line and its flags and nothing else -
43 of 43 `add_parser` calls carried a one-line `help=` and no `description=`.
The answer existed the whole time, in `CHECK_GUIDANCE`, `guardrails.yml` and
the command files; it simply never reached the person or the agent asking the
tool what it was.

Anthropic's context-engineering guidance for Claude 5 models replaces "give
examples of tool usage" with "design better tool interfaces". This is the half
of that Compass can act on without guessing.

Scenario id: CLIV-A1 in
.compass/work/cli-verbs-do-not-describe-themselves/acceptance-criteria.md
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "cli"))

#: Groups exist to hold subverbs. `compass issue` is not a thing you run, so it
#: is described by its members rather than by itself.
_GROUPS_ONLY = set()

#: Retired spellings that still run but are hidden from `--help`, so requiring
#: them to describe themselves there would be asking for text nobody can reach.
#: Named individually so a third is a deliberate addition.
_NOT_ADVERTISED = {"design"}


def _is_internal(name):
    """Internal entry points, by the convention the parser itself uses.

    `build_parser` filters the advertised set with `not k.startswith("_")`.
    Deriving the rule here rather than listing the names means a new internal
    verb does not have to be added in two places - and a new PUBLIC one still
    has to describe itself.
    """
    return name.startswith("_")

#: Shorter than this and a "description" is the help line with more words.
_MIN_WORDS = 12


def _leaf_parsers():
    """Every parser a person can actually run, with its path."""
    import compass_pkg  # noqa: F401  - resolves the bundled yaml
    import importlib.util
    from importlib.machinery import SourceFileLoader

    # `cli/compass` has no .py suffix, so spec_from_file_location cannot pick a
    # loader for it and returns None. Naming the loader is what the rest of the
    # suite does for the same reason.
    path = str(REPO_ROOT / "cli" / "compass")
    spec = importlib.util.spec_from_loader(
        "compass_entry", SourceFileLoader("compass_entry", path))
    module = importlib.util.module_from_spec(spec)
    sys.argv = ["compass"]
    spec.loader.exec_module(module)
    root = module.build_parser()

    found = []

    def walk(parser, path_parts, help_text):
        subs = [a for a in parser._actions
                if isinstance(a, argparse._SubParsersAction)]
        if not subs:
            found.append((" ".join(path_parts), parser, help_text))
            return
        for action in subs:
            # The `help=` a group gave each child lives on the group's own
            # _choices_actions, not on the child parser - so it is carried down
            # rather than read off the child, which has no memory of it.
            helps = {c.dest: (c.help or "") for c in action._choices_actions}
            for name, child in action.choices.items():
                if name in _NOT_ADVERTISED or _is_internal(name):
                    continue
                walk(child, path_parts + [name], helps.get(name, ""))

    walk(root, [], "")
    return [(p, parser, h) for p, parser, h in found if p]


def test_cliv_a1_every_verb_describes_itself():
    """Asking the tool what it is must answer."""
    missing = []
    for path, parser, _help in _leaf_parsers():
        text = (parser.description or "").strip()
        if len(text.split()) < _MIN_WORDS:
            missing.append("compass %s (%d words)" % (path, len(text.split())))
    assert not missing, (
        "%d verb(s) do not say what they do when asked. The content for most "
        "of them already exists in CHECK_GUIDANCE, guardrails.yml or "
        "commands/ - it just has to reach argparse:\n  %s"
        % (len(missing), "\n  ".join(missing)))


def test_cliv_a1b_a_description_is_not_the_help_line_again():
    """The control, and the reason this is not satisfied by 43 restatements.

    Without it, pasting each `help=` into `description=` would turn this green
    while a reader learned nothing new - which is the shape of a check that
    cannot fail.
    """
    echoes = []
    for path, parser, raw_help in _leaf_parsers():
        desc = " ".join((parser.description or "").split()).lower()
        help_text = " ".join((raw_help or "").split()).lower()
        if help_text and desc.startswith(help_text) and len(desc) < len(help_text) * 1.6:
            echoes.append("compass %s" % path)
    assert not echoes, (
        "these descriptions are the one-line help with little added, so the "
        "reader learns nothing they did not already see in the group listing:"
        "\n  %s" % "\n  ".join(echoes))
