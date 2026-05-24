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

Compass's own ADRs (ADR-001..ADR-006) all ship with `status: accepted`.
This fixture exists solely to verify that the load mechanism correctly
preserves the `proposed` status rather than normalising everything to
`accepted`.

## Decision

This ADR is not a real decision. It is a fixture for TRC-X2.

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
- Real proposed ADRs for Compass will live in `architecture/decisions/` with
  the next sequential number after ADR-006, when a genuine decision is in
  flight.

## References

- `tests/test_self_architecture.py::test_proposed_adr_loaded_with_status` (TRC-X2)
- `spec.feature.md` §"Failure-mode scenarios" (TRC-X2)
