"""The cucumber-js reference adapter ships no vulnerable dependency.

`uuid@10.0.0` arrived as a transitive dependency of `@cucumber/cucumber@11`
and carries a moderate advisory. An example is copied, so an adopter who
follows this adapter copies the advisory with it - which makes a dependency in
an example a shipped surface rather than test scaffolding.

Cucumber 13 does not depend on `uuid` at all, so the dependency is removed
rather than pinned to a patched version.

Read from the lockfile rather than by running `npm audit`: the check has to
work in a clean checkout with no network and no `node_modules`, which is where
CI and every contributor start.

Scenario ids: see .compass/work/cucumber-13-drops-vulnerable-uuid/
acceptance-criteria.md.
"""
from __future__ import annotations

import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
ADAPTER = ROOT / "examples" / "bdd-adapters" / "cucumber-js"


def test_cu_1_no_vulnerable_uuid():
    lock = ADAPTER / "package-lock.json"
    manifest = ADAPTER / "package.json"
    assert lock.is_file(), f"the adapter has no lockfile: {lock}"

    packages = json.loads(lock.read_text(encoding="utf-8")).get("packages", {})
    uuid_entries = sorted(
        name for name in packages
        if name.split("node_modules/")[-1] == "uuid"
    )
    assert not uuid_entries, (
        f"the cucumber-js adapter still resolves `uuid`, which carries a "
        f"moderate advisory at 10.0.0: {uuid_entries}. Cucumber 13 does not "
        f"depend on it, so the fix is to remove the dependency rather than "
        f"pin it."
    )

    declared = json.loads(manifest.read_text(encoding="utf-8"))
    spec = (declared.get("devDependencies") or {}).get("@cucumber/cucumber", "")
    major = re.search(r"(\d+)", spec)
    assert major and int(major.group(1)) >= 13, (
        f"the adapter declares @cucumber/cucumber {spec!r}. Below 13 it pulls "
        f"`uuid` back in, so the removal above would not survive the next "
        f"`npm install`."
    )


def test_cu_1b_the_adapter_still_declares_a_runnable_suite():
    """The control.

    Deleting the dependency block entirely would satisfy the assertions above
    while destroying the thing the example exists for. The end-to-end proof
    that it still runs is `tests/test_bdd_adapters_all.py`, which executes the
    documented commands and requires three passing scenarios; this is the
    cheap structural half that runs without npm installed.
    """
    manifest = json.loads(
        (ADAPTER / "package.json").read_text(encoding="utf-8"))
    assert (manifest.get("devDependencies") or {}).get("@cucumber/cucumber"), (
        "the adapter declares no cucumber dependency at all - the example "
        "cannot run"
    )
    assert (manifest.get("scripts") or {}).get("test"), (
        "the adapter declares no test script, so the README's documented "
        "command has nothing to invoke"
    )
