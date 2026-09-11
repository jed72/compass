# Brief - notifications-subsystem

> **Author:** S. Voss (product manager) · **Date:** 2026-03-01
> **Governance owner check:** this brief is consistent with the product strategies in `governance/strategies.md` - in particular "depth for existing users over breadth".

---

## Problem

Users have no way to know something happened in the product unless they are
looking at the exact screen where it happened. A teammate comments on their
document, a long export finishes, their access to a workspace changes - all of
it is invisible unless they happen to be there. Support sees the cost daily:
"I didn't know my export was ready", "nobody told me I was removed". There is
no notifications capability at all today - this is a missing subsystem, not a
weak one.

## Desired outcome

A user is reliably told about the events that affect them - in-app to start -
and can tune what they hear about, without being able to mute the things they
must not miss.

## Success signals

- A user sees a notification for a relevant event within seconds of it
  happening, without being on the originating screen.
- A user who mutes a category stops seeing it - and the mute survives sessions.
- Security-relevant notifications reach the user even if they have muted
  everything else.
- Support tickets of the form "nobody told me…" drop noticeably the cycle after
  launch.

## Constraints

- In-app delivery only for v1. No email, no push, no SMS - those are a later
  channel layer, and the v1 design must not make them harder.
- Notifications must be durable: a worker restart or a brief outage must not
  lose a notification a user should have received.
- The data model is a new table - it ships as a migration, reviewed forward
  *and* rollback.

## Non-goals

- We are NOT building email/push/SMS channels in this issue.
- We are NOT building a notification *digest* or batching/quiet-hours logic.
- We are NOT building an admin console for notification templates.

## Internal FAQ

**Why now?**
Support load from "I wasn't told" tickets has been the top non-bug theme for
two quarters, and three separate features on this cycle's roadmap (comments,
exports, access changes) each independently wanted to "tell the user" - building
that three times, three ways, is the waste this subsystem prevents. Building it
now means those features build *on* it instead of around it.

**What is in v1, and what is explicitly later?**
v1: in-app notifications for a fixed set of event types, per-user per-category
preferences, durable delivery, a security-category override that mute cannot
suppress. Later: other delivery channels, digests/batching, user-authored
rules.

**How will we know it worked?**
The deciding signal is the "nobody told me…" support theme dropping the cycle
after launch. Secondary: the three roadmap features ship on the subsystem
rather than reinventing delivery.

**What could make this fail?**
- *Technical:* delivery that is not genuinely durable - looks fine in dev,
  loses notifications under real restart/outage conditions. Mitigation: TRC-003
  makes durability an explicit, tested scenario.
- *Product:* the preference model is too coarse (users mute everything because
  the only knob is too blunt) or too fine (nobody configures it). Mitigation:
  category-level granularity for v1, safe defaults, revisit with usage data.
- *Adoption:* the security-override is wrong in either direction - too broad
  (everything claims to be security and mute is meaningless) or too narrow (a
  real security event is missed). Mitigation: a fixed, small security category,
  not a per-notification flag.

## Affected roles

- product-owner - this brief; reviews the spec for intent fidelity before Plan.
- engineer - owns the build (multiagent across two subtasks).
- *Not* product-marketer on this issue - the external launch is a separate,
  later issue; this one ships the capability.

---

## Intent-fidelity check (filled at the pre-Plan gate - RP-ROLE-002)

The product-owner role rule (RP-ROLE-002) blocks Plan until the spec is checked
against this brief.

- [x] Every success signal above maps to at least one scenario in
  `acceptance-criteria.md` - delivery-within-seconds → TRC-001; durability → TRC-003;
  mute survives sessions → TRC-004; security reaches through mute → TRC-006.
  (The "support tickets drop" signal is an outcome metric, tracked post-launch,
  not a scenario - noted, not orphaned.)
- [x] No scenario contradicts a constraint, pursues a non-goal, or runs against
  a product strategy. No scenario touches email/push/SMS or digests; the spec
  stays inside the v1 cut.
- [x] Checked by: S. Voss on 2026-03-06. Plan unblocked.
