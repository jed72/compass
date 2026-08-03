"""Step definitions binding the reset-password scenarios to the code.

`scenarios(...)` points at the file `compass bdd extract` produced, NOT at
spec.feature.md. The extracted file is derived and regenerated; the markdown
spec stays the source of truth. Run the extract before the tests - the README
shows the two commands together.

Each scenario in the extracted feature carries its traceability id as a tag
(@TRC-A1 and so on), so a pytest-bdd result maps straight back to task.yml.
Select one with: pytest -m "" -k TRC-A2, or `pytest --tags TRC-A2` on runners
that support tag expressions.
"""
from __future__ import annotations

import pathlib
import sys

import pytest
from pytest_bdd import scenarios, given, when, then, parsers

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

from reset_password import PasswordStore, Token  # noqa: E402

FEATURE = (pathlib.Path(__file__).resolve().parents[2]
           / ".compass" / "work" / "reset-password" / "spec.feature")

scenarios(str(FEATURE))


@pytest.fixture
def store():
    return PasswordStore()


@pytest.fixture
def outcome():
    """A one-slot box for the result, so `when` can hand it to `then`."""
    return {}


@given(parsers.parse("a password reset token issued {hours:d} hours ago"),
       target_fixture="token")
def issued_token(hours):
    return Token(value="tok-123", age_hours=hours)


@when(parsers.parse('the user sets the new password "{password}"'))
def set_password(store, token, outcome, password):
    outcome["result"] = store.reset(token, password)


@then("the reset succeeds")
def reset_succeeds(outcome):
    assert outcome["result"].ok, outcome["result"].error


@then(parsers.parse('the reset is refused with "{reason}"'))
def reset_refused(outcome, reason):
    assert not outcome["result"].ok, "expected the reset to be refused"
    assert outcome["result"].error == reason


@then("the password change is recorded")
def change_recorded(store):
    assert len(store.changes) == 1


@then("no password change is recorded")
def no_change_recorded(store):
    assert store.changes == []
