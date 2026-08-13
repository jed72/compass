# Spec - reset-password

> **Phase:** Specify · **Last updated:** 2026-08-03 · **Owning agent:** spec-author
> **Familiarity:** greenfield

## Summary

**Goal:** A user with a valid reset link can set a new password, and a user
whose link has gone stale cannot.

**Approach:** One rule object holds the token lifetime and the password floor.
Every rejected reset must leave the store untouched, which is what makes the
failure scenarios worth writing.

**Why now / what changes:** This is the worked example for the pytest-bdd
adapter. The scenarios below are extracted by `compass bdd extract` and run as
the acceptance suite - they are the same text in both roles.

---

## Intent links

| Intent id | Source | Statement |
|---|---|---|
| INT-1 | the issue description | A user can complete a password reset from a valid link. |
| INT-2 | the issue description | A reset that must be refused changes nothing. |

---

## Scenario group A - resetting a password

**Independence note:** single group; this example does not parallelise.

### Scenario: a valid token should let the user set a new password
<!-- traceability id: TRC-A1 · serves: INT-1 -->

```gherkin
Scenario: a valid token should let the user set a new password
  Given a password reset token issued 1 hours ago
  When the user sets the new password "correct horse battery"
  Then the reset succeeds
  And the password change is recorded
```

### Scenario: an expired token should be rejected
<!-- traceability id: TRC-A2 · serves: INT-2 -->

```gherkin
Scenario: an expired token should be rejected
  Given a password reset token issued 25 hours ago
  When the user sets the new password "correct horse battery"
  Then the reset is refused with "token expired"
  And no password change is recorded
```

### Scenario: a password below the length floor should be rejected
<!-- traceability id: TRC-A3 · serves: INT-2 -->

```gherkin
Scenario: a password below the length floor should be rejected
  Given a password reset token issued 1 hours ago
  When the user sets the new password "short"
  Then the reset is refused with "password too short"
  And no password change is recorded
```

---

## Coverage ledger

| Traceability id | Serves intent | Has a failing test (Build) | Passes as acceptance (Verify) |
|---|---|---|---|
| TRC-A1 | INT-1 | [x] | [x] |
| TRC-A2 | INT-2 | [x] | [x] |
| TRC-A3 | INT-2 | [x] | [x] |
