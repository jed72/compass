# Spec - notifications-subsystem

> **Phase:** define · **Last updated:** 2026-03-05 · **Owning agent:** spec-author
> **Familiarity:** greenfield discovery - there is no notifications capability today; these scenarios are discovered from `intent.md`, not distilled from existing behaviour.

## How each role reads this file

- **Product owner / manager** - reads for *intent fidelity*: do these scenarios deliver the outcome in `intent.md`?
- **Product marketer** - reads for *claims*: every line of launch copy must point at a scenario id here.
- **Engineer** - reads for *tests*: scenarios are the acceptance suite and seed the TDD red→green cycle.
- **QA** - reads for *coverage*: which scenarios are exercised, which edges are not.
- **Designer** - UI behaviour authored in `ui-contract.md` flows in here as scenarios.

---

## Intent links

| Intent id | Source | Statement |
|---|---|---|
| INT-1 | `intent.md` desired outcome | A user is reliably told about events that affect them, in-app, within seconds. |
| INT-2 | `intent.md` constraint | Notifications are durable - a worker restart or brief outage does not lose one a user should have received. |
| INT-3 | `intent.md` desired outcome | A user can tune what they hear about, with safe defaults, but cannot mute what they must not miss. |

---

## Scenario group A - Delivery & dispatch

**Independence note:** group A owns the dispatch pipeline and the durable store -
`dispatch.py`, `store.py`. It is separable from group B: a notification can
be created, stored, and delivered without any preference logic (the default is
"deliver"). Group A became swarm **stream-1**.

### Scenario: An in-app event produces a notification for the target user
<!-- traceability id: TRC-001 · serves: INT-1 -->

```gherkin
Scenario: An in-app event produces a notification for the target user
  Given user "mara" is a member of workspace "atlas"
  When a teammate comments on a document "mara" owns in "atlas"
  Then a notification is created for "mara"
  And "mara" sees it in-app within 5 seconds without navigating to the document
```

### Scenario: A notification is delivered once, even if the event is retried
<!-- traceability id: TRC-002 · serves: INT-1 -->

```gherkin
Scenario: A notification is delivered once, even if the event is retried
  Given an event "export-ready" for user "mara" has been dispatched
  When the same event is dispatched again because the producer retried
  Then "mara" has exactly one "export-ready" notification
  And the duplicate dispatch is recorded as a no-op
```

### Scenario: Notifications survive a worker restart
<!-- traceability id: TRC-003 · serves: INT-2 -->

```gherkin
Scenario: Notifications survive a worker restart
  Given three notifications for user "mara" have been created and stored
  And none have been marked delivered yet
  When the notification worker restarts
  Then all three notifications are still present
  And "mara" receives all three after the restart
```

---

## Scenario group B - User preferences

**Independence note:** group B owns the preference model - `preferences.py`. It
is separable from group A: preference resolution is a pure decision ("should
this category reach this user?") that group A *calls*, but does not implement.
The two groups share only `migrations/0042` (the table both read) and `api.py`
(the surface) - that shared surface is what the orchestrator polices. Group B
became swarm **stream-2**.

### Scenario: A user mutes a category and stops receiving that category
<!-- traceability id: TRC-004 · serves: INT-3 -->

```gherkin
Scenario: A user mutes a category and stops receiving that category
  Given user "mara" has muted the "comments" category
  When a teammate comments on a document "mara" owns
  Then no "comments" notification is created for "mara"
  And the mute is still in effect after "mara" signs out and back in
```

### Scenario: A user with no saved preferences gets the safe defaults
<!-- traceability id: TRC-005 · serves: INT-3 -->

```gherkin
Scenario: A user with no saved preferences gets the safe defaults
  Given user "devin" has never opened notification settings
  When any notifiable event occurs for "devin"
  Then "devin" receives the notification
  And the default for every category is "deliver"
```

---

## Failure-mode scenarios

### Scenario: A muted category does not suppress a security notification
<!-- traceability id: TRC-006 · serves: INT-3 -->

```gherkin
Scenario: A muted category does not suppress a security notification
  Given user "mara" has muted every category, including "security"
  When "mara"'s password is changed from a new device
  Then "mara" still receives the "security" notification
  And the mute on "security" is treated as not applicable
```

<!-- This is the brief's hardest constraint made into a scenario: mute must not
     be able to suppress the things a user must not miss. It sits in group B's
     surface (preferences.py) - stream-2 owns it. -->

---

## Coverage ledger

| Traceability id | Serves intent | Has a failing test (Build) | Passes as acceptance (Verify) |
|---|---|---|---|
| TRC-001 | INT-1 | [x] | [x] |
| TRC-002 | INT-1 | [x] | [x] |
| TRC-003 | INT-2 | [x] | [x] |
| TRC-004 | INT-3 | [x] | [x] |
| TRC-005 | INT-3 | [x] | [x] |
| TRC-006 | INT-3 | [x] | [x] |
