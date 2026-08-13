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
