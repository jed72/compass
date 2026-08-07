"""`compass terminology [term]` - render the v2 vocabulary.

`governance/terminology.yml` is the single source of truth for what every
v2 word means; this verb renders it at the terminal so the answer to any
vocabulary question is one command away. Read-only.
"""
import os
import sys

import yaml

from compass_pkg.core import CompassError, find_governance, load_yaml


def _load_terms():
    path = os.path.join(find_governance(), "terminology.yml")
    doc = load_yaml(path)
    if not isinstance(doc, dict) or not isinstance(doc.get("terms"), dict):
        raise CompassError(
            f"{path}: no `terms:` section - the vocabulary file is the "
            "single source of truth, and it is unreadable.")
    return doc


def cmd_terminology(args):
    doc = _load_terms()
    terms = doc["terms"]
    version = doc.get("version", "?")
    if not args.term:
        print(f"The v2 vocabulary ({version}) - "
              f"{len(terms)} terms. Ask for one with "
              "`compass terminology <term>`.")
        for name in sorted(terms):
            means = str(terms[name].get("means", "")).strip().split("\n")[0]
            print(f"  {name:<24} {means[:70]}")
        return 0
    key = args.term.strip().lower().replace(" ", "-")
    entry = terms.get(key)
    if entry is None:
        near = [n for n in sorted(terms) if key in n or n in key]
        hint = f" Did you mean: {', '.join(near)}?" if near else ""
        raise CompassError(
            f"'{args.term}' is not in the vocabulary.{hint} "
            "Run `compass terminology` to list every term.")
    print(f"{key}  (vocabulary {version})")
    means = " ".join(str(entry.get("means", "")).split())
    print(f"  means:   {means}")
    if entry.get("github"):
        print(f"  github:  {entry['github']}")
    if entry.get("also"):
        print(f"  also:    {entry['also']}")
    if entry.get("not"):
        print(f"  not:     {' '.join(str(entry['not']).split())}")
    if entry.get("related"):
        print(f"  related: {', '.join(entry['related'])}")
    return 0


def retired_verb_pointer(argv):
    """A retired v1 verb fails machine-tolerably: exit 2, exactly one line
    on stderr naming the replacement, empty stdout - a hook or CI script
    hitting a retired verb can never mistake the pointer for success. The
    retired spellings live in cli/migrate-map.yml (scan-exempt data), so
    this file never carries one in a string literal. Returns the exit code
    to use, or None when argv starts with a live verb."""
    if not argv or argv[0].startswith("-"):
        return None
    map_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "migrate-map.yml")
    try:
        with open(map_path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
    except OSError:
        return None
    verbs = data.get("verbs") or {}
    if argv[0] not in verbs:
        return None
    subverbs = data.get("subverbs") or {}
    pair = " ".join(argv[:2]) if len(argv) > 1 else None
    replacement = subverbs.get(pair) or verbs[argv[0]]
    sys.stderr.write(
        f"compass {argv[0]}: renamed - run `compass {replacement}` "
        "instead (the retired spelling is kept as this pointer for one "
        "major version).\n")
    return 2
