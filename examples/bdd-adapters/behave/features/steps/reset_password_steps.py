"""Step definitions for behave.

Only this file differs from the pytest-bdd adapter. The spec, the extract
command and the run command are the same four steps in a different language's
idiom - which is the claim the four adapters exist to demonstrate.
"""
from behave import given, when, then

TOKEN_LIFETIME_HOURS = 24


@given('a password reset token issued {hours:d} hours ago')
def step_token(context, hours):
    context.age_hours = hours
    context.changes = []


@when('the user sets the new password "{password}"')
def step_reset(context, password):
    if context.age_hours >= TOKEN_LIFETIME_HOURS:
        context.result = (False, "token expired")
    elif len(password) < 8:
        context.result = (False, "password too short")
    else:
        context.changes.append(password)
        context.result = (True, None)


@then('the reset succeeds')
def step_ok(context):
    assert context.result[0], context.result[1]


@then('the reset is refused with "{reason}"')
def step_refused(context, reason):
    assert not context.result[0], "expected the reset to be refused"
    assert context.result[1] == reason


@then('the password change is recorded')
def step_recorded(context):
    assert len(context.changes) == 1


@then('no password change is recorded')
def step_not_recorded(context):
    assert context.changes == []
