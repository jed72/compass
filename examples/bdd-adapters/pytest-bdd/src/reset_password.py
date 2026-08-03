"""A deliberately small password-reset rule, so the wiring is what you read.

The point of this example is the path from a Compass scenario to a passing
test, not the domain. Everything here is in memory.
"""
from __future__ import annotations

from dataclasses import dataclass, field

TOKEN_LIFETIME_HOURS = 24


@dataclass
class Token:
    value: str
    age_hours: float


@dataclass
class ResetResult:
    ok: bool
    error: str | None = None


@dataclass
class PasswordStore:
    """Records every accepted password change, so a scenario can assert that
    a rejected reset wrote nothing."""
    changes: list = field(default_factory=list)

    def reset(self, token: Token, new_password: str) -> ResetResult:
        if token.age_hours >= TOKEN_LIFETIME_HOURS:
            return ResetResult(ok=False, error="token expired")
        if len(new_password) < 8:
            return ResetResult(ok=False, error="password too short")
        self.changes.append(new_password)
        return ResetResult(ok=True)
