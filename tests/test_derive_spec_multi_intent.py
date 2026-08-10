"""The system-spec deriver honours a scenario that serves several intents.

`schemas/task.schema.json` says a scenario's `intent` may be "a string or a
list of strings (a scenario may serve more than one intent)". The deriver
used the value directly as a dictionary key, so the list form crashed it with
`TypeError: unhashable type: 'list'`. Nothing hit it until an issue actually
wrote the list form.

Spec: .compass/work/derive-spec-multi-intent/acceptance-criteria.md (TRC-1).
"""
from __future__ import annotations

import importlib.machinery
import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _flow_module():
    sys.path.insert(0, str(ROOT / "cli"))
    loader = importlib.machinery.SourceFileLoader(
        "compass_flow_multi_intent", str(ROOT / "cli" / "compass_pkg" / "flow.py"))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def _project(tmp_path, intent):
    """A project with one landed issue whose single scenario carries `intent`."""
    work = tmp_path / ".compass" / "work" / "an-issue"
    work.mkdir(parents=True)
    (tmp_path / ".compass" / "config.yml").write_text(
        "version: 1.0.0\n", encoding="utf-8")
    intent_yaml = (
        "[" + ", ".join(intent) + "]" if isinstance(intent, list) else intent
    )
    (work / "task.yml").write_text(
        "schema_version: '2.0'\n"
        "task: an-issue\n"
        "created: '2026-08-10'\n"
        "status: landed\n"
        "scenarios:\n"
        "- id: TRC-1\n"
        "  title: the behaviour this scenario states\n"
        f"  intent: {intent_yaml}\n",
        encoding="utf-8",
    )
    return tmp_path


def test_a_scenario_serving_two_intents_answers_for_both(tmp_path):
    """A list intent derives, and the scenario is current behaviour for each id.

    Keying on the whole list would invent a composite intent that supersedes
    neither of the two real ones, so the assertion is per id, not on the pair.
    """
    flow = _flow_module()
    project = _project(tmp_path, ["INT-1", "INT-2"])

    flow.derive_system_spec(str(project))

    spec = (project / "docs" / "system-spec.md").read_text(encoding="utf-8")
    assert "INT-1" in spec, "the scenario does not answer for its first intent"
    assert "INT-2" in spec, "the scenario does not answer for its second intent"
    assert "TRC-1" in spec


def test_a_scenario_serving_one_intent_still_derives(tmp_path):
    """The scalar form is unchanged - this fix must not trade one for the other."""
    flow = _flow_module()
    project = _project(tmp_path, "INT-9")

    flow.derive_system_spec(str(project))

    spec = (project / "docs" / "system-spec.md").read_text(encoding="utf-8")
    assert "INT-9" in spec
    assert "TRC-1" in spec
