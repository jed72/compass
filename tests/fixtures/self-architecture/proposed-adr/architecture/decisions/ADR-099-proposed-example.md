---
id: ADR-099
title: Proposed example ADR for mechanism testing
status: proposed
date: 2026-05-24
supersedes: ''
superseded_by: ''
---

## Context

This is a synthetic fixture ADR for testing the `frame_load_architecture`
mechanism's handling of proposed-status ADRs. It lives in
`tests/fixtures/self-architecture/proposed-adr/` and is never part of
Compass's own `architecture/decisions/` tree.

This fixture exists to check that the load mechanism correctly preserves the
`proposed` status rather than normalising everything to `accepted`.

## Decision

This ADR is not a real decision. It is a fixture for the proposed-status
scenario (`TRC-X2`).

## Alternatives considered

| Alternative | Why considered | Why rejected |
|---|---|---|
| Use a real proposed ADR in Compass's architecture/ | More realistic test | Would ship a fake "open decision" as part of Compass's own record, which is misleading |

## Consequences

**Positive:**
- The mechanism is tested against both `accepted` and `proposed` status values.

**Negative:**
- None (this is a test fixture, not a production ADR).

**Neutral / follow-on:**
- Real proposed ADRs for Compass live in `architecture/decisions/` with the
  next sequential number.

## References

No test reads this fixture (checked by grep over tests/ and cli/). It is
kept for a future proposed-status scenario (`TRC-X2`).
