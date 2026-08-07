# Compass - Routing Deep Dive

`routes/router.md` is the Needle's rubric: the four dimensions, the scoring
tables, the four-step procedure. This document is the rubric *in motion*. It
takes a handful of realistic tasks and walks each one through scoring,
composition, routing-guardrail constraint, and the final `delivery-approach.md` - so that
the claim "Compass computes the process per task" stops being an assertion and
becomes something you can watch happen.

If `routes/router.md` is the law, this is the casebook.

---

## The shape of every routing decision

Every task, every time, the Needle runs the same four steps:

1. **Score the four dimensions** - blast radius, terrain, magnitude, intent &
   role - each with a one-line written justification. If a reading cannot be
   justified, the Needle asks rather than guesses.
2. **Compose the candidate route** - assemble per-phase weight from the
   dimension contributions, biased by the routing strategies, name the
   reference route for shared vocabulary, list any deviations.
3. **Constrain with the routing guardrails** - floors raise the candidate,
   caps limit it, immovable gates are stapled on, blocking role rules add
   artifacts and blocks. Every guardrail that fires is recorded with its
   rationale.
4. **Write `delivery-approach.md` and confirm** - including the de-scope ledger, where
   every collapsed or skipped phase carries an explicit "safe to skip
   because…" line.

The five reference routes - Express, Standard, Expedition, Hotfix, Spike - are
not a menu. They are the common shapes the composition lands near. A perfectly
normal output is "Standard, but Verify also runs the `security` dimension" -
that is the framework working, not an exception.

What follows is six cases. Read them in order; they build on each other.

---

## Case 1 - A typo fix in an auth module

> **Request:** "Fix the typo in the JWT refresh error message."

### Score

| Dimension | Reading | Justification |
|---|---|---|
| Blast radius | `trivial` | The wrong outcome is a misspelled word in an error string - cosmetic, instantly obvious, instantly reversible. No data, no money, no auth *behaviour* touched. |
| Terrain | `brownfield-mapped` | Existing code; the error path is trivially readable. |
| Magnitude | `atomic` | One file, one string, no design decision, well under thirty minutes. |
| Intent & role | `engineer` | Standard pipeline ownership; no brief, no other role. |

The Needle also assigns domain tags. The change is *in* the JWT module, so it
tags `touches: [auth]` - honestly, because the tag is about where the change
lives, not how scary it looks.

### Compose

Atomic magnitude, trivial blast radius, mapped terrain, engineer role. This is
the textbook Express case. The candidate route is **Express**: one scenario,
Clarify collapsed, Plan collapsed to a one-liner, Distribute skipped, full TDD
on a tiny surface, one light gate at Verify.

### Constrain

Now the routing guardrails run. The floor `when: { touches: [auth] }` matches
the `touches: [auth]` tag, and its action is `force_minimum_route: expedition`.
The candidate Express is raised to **Expedition**.

This is the single most important thing the routing system does, so it is
worth stating plainly: *a one-character change to an auth error message gets
the full Expedition treatment.* Not because the change is large - it is
atomic - but because the blast radius of the auth module is not a function of
line count. A floor is domain knowledge overriding the raw dimension readings.

### Final `delivery-approach.md`

The route is Expedition. The routing-guardrails section of `delivery-approach.md` records:

> **floor** · `touches: [auth]` · Candidate route Express was raised to
> Expedition · *"Domain risk overrides magnitude. A one-line auth change is
> not small."*

The engineer sees *why* a typo fix got the full treatment. Because routing is
advisory until confirmed, they can discuss it - but they cannot have it
silently routed light. A floor is governance speaking; overriding it would
mean amending `governance/routing-policy.md`, not overriding a route.

In practice the team might decide the policy is too blunt and narrow the floor
(`touches: [auth]` only when the change is to auth *logic*, not auth-adjacent
strings). That is a legitimate, logged amendment to
`governance/routing-policy.md` - not a convenience edit mid-task. Until then,
the typo fix runs Expedition, and that is the system being conservative on
purpose.

---

## Case 2 - A normal-sized new feature

> **Request:** "Add a saved-views feature to the dashboard - users can name a
> filter combination and recall it."

### Score

| Dimension | Reading | Justification |
|---|---|---|
| Blast radius | `contained` | A broken saved-view is annoying and bounded to the dashboard; recoverable, no data loss, no other surface affected. |
| Terrain | `brownfield-mapped` | The dashboard's filter behaviour is already captured in scenarios. |
| Magnitude | `standard` | Several files - a persistence layer, the filter serialisation, the UI - and one or two design decisions, 1–3 days. |
| Intent & role | `engineer` | No brief; an engineer is implementing a well-understood feature. |

Domain tags: `touches: [persistence]` perhaps, but nothing on the policy's
floor list (`auth`, `payments`, `personal-data`, `migrations`, `public-api`).

### Compose

Standard magnitude, contained blast radius, mapped terrain. The candidate is
**Standard**, plainly: a small feature set of scenarios, a light-to-full
Clarify pass, a real `design.md` with the design decisions recorded, solo or
pair topology, two gates at Verify. No deviation from the reference shape is
warranted - blast radius is only `contained`, so `security` stays scaled
rather than full and `clarity` and `regression` are on as Standard always has
them.

### Constrain

No floor matches - no domain tag on the floor list, blast radius is not
`critical`, terrain is mapped. No cap is relevant. The immovable gates
(`verify.correctness`, `verify.governance`, `verify.regression`,
`verify.claims`) are stapled on; `verify.claims` is `n/a` here because no
marketer is in play. No `role_rules` fire - only an engineer.

### Final `delivery-approach.md`

The routing-guardrails section reads, in full:

> No routing guardrail fired. Candidate route stands.

That line is itself the record - silence is not allowed; "nothing fired" is
written down. The route is Standard, unmodified. The de-scope ledger is short:
the dedicated orchestrator agent is skipped (≤3 streams, the lead builder
integrates) and the full distribution map is reduced to a short list. Both
carry their standing justifications.

This is the boring case, and the boring case matters: most work is Standard,
and Standard should feel like the default working shape, not a ceremony.

---

## Case 3 - A payments-touching migration

> **Request:** "Migrate the stored card-token format - one column, a backfill
> script, a read-path change."

### Score

| Dimension | Reading | Justification |
|---|---|---|
| Blast radius | `critical` | A wrong migration can corrupt stored payment tokens - data loss, money, and a path that does not cleanly roll back. |
| Terrain | `brownfield-mapped` | The token storage and read path are mapped. |
| Magnitude | `small` | Honestly: one column, one backfill script, one read-path change. 1–3 files, a known pattern. |
| Intent & role | `engineer` | An engineer running a contained migration. |

This is the case the methodology opens with: *a migration that touches one
file is small but not safe.* Magnitude and blast radius are different axes, and
here they point in opposite directions. The Needle scores them honestly -
magnitude `small`, blast radius `critical` - and does not let one launder the
other. Domain tags: `touches: [payments, migrations]` - two tags, both on the
floor list.

### Compose

If magnitude alone drove the route, this would compose toward Express or a
light Standard - `small` on mapped terrain. The Needle composes the candidate
from *all four* contributions, and `critical` blast radius pulls hard: full
test surface including adversarial and boundary inputs, the rollback path
exercised, every review dimension. The candidate already composes heavy -
toward **Expedition** - on blast radius alone.

### Constrain

Two floors fire, and they reinforce each other:

- `when: { blast_radius: critical }` → `force_minimum_route: expedition`,
  `never_skip: [clarify, verify, land]`. *"Critical changes coordinate or they
  break things quietly."*
- `when: { touches: [payments, migrations] }` → `force_minimum_route:
  expedition`. *"Domain risk overrides magnitude."*

Then a **cap** fires - and this is the subtle part. `when: { blast_radius:
critical }` → `max_worktrees: 1`. So this is an Expedition route that is
*capped to a single worktree*. It is heavy - full BDD discovery, full Clarify,
a full `design.md`, every gate - and **solo**. That is not a contradiction. The
cap encodes a real tradeoff: parallelism is speed, but a swarm has
coordination risk, and on a critical change the coordination risk costs more
than the speed saves.

An engineering strategy in `governance/strategies.md` (migrations are
reversible or come with a written, tested rollback) is checked during Plan by
`governance-check` - the route does not waive it. (If the team has hardened
that into a project guardrail, it is checked as a guardrail and blocks.)

### Final `delivery-approach.md`

Expedition, single worktree. The routing-guardrails section records both
floors and the cap, each with its rationale. The topology section (§4c of the
route template) records the worktree count as **cap-driven** - not as a
de-scope. This distinction matters: the de-scope ledger is for things the
route *chose* to skip; a cap removing a worktree is a routing guardrail, and
guardrail-driven reductions go in the topology section, never the ledger.
Expedition's de-scope ledger is empty by definition, and a capped Expedition
is still an Expedition.

A `distribution-map.md` is still written, even though the work runs solo. The
map is the record of *what could have been parallel and why it wasn't* - here,
"it wasn't, because the critical-blast-radius cap pinned it to one worktree."

---

## Case 4 - A greenfield subsystem

> **Request:** "Build the notifications subsystem - email, in-app, and webhook
> delivery, with user preferences and a delivery log."

### Score

| Dimension | Reading | Justification |
|---|---|---|
| Blast radius | `cross-cutting` | Notifications touch many features; a delivery failure degrades something many users see. Recovery needs coordination, but it is not data-loss or money - not `critical`. |
| Terrain | `greenfield` | Net-new code; no existing behaviour to preserve. |
| Magnitude | `product` | A new subsystem - three delivery channels, a preferences model, a delivery log. 2+ weeks, many independent work streams. |
| Intent & role | `engineer` | An engineering lead, though a designer and a product owner may well join (preferences are a user-facing surface; the subsystem serves a stated outcome). |

Domain tags: possibly `touches: [personal-data]` if the preferences or
delivery log store anything personal - the Needle tags honestly and that tag
would add a floor; assume here it does not.

### Compose

`product` magnitude with `cross-cutting` blast radius and `greenfield` terrain
is the textbook **Expedition** case, and it composes there with no help from
the routing guardrails. Full BDD discovery from the brief; scenarios grouped by
independence - email delivery, in-app delivery, webhook delivery, preferences,
the delivery log are plausibly disjoint surfaces; a full `design.md` plus a real
`distribution-map.md`; a swarm across git worktrees, one `builder` per stream,
an `orchestrator` that writes no feature code; all gates, all dimensions, plus
a per-worktree mid-route checkpoint.

### Constrain

The `blast_radius: critical` floor does *not* fire - this is `cross-cutting`,
not `critical`. So the critical-blast-radius cap does *not* apply either: the
swarm is not pinned to one worktree. Stream count comes from the distribution
map, bounded by `.compass/config.yml`'s `max_worktrees` (default 6). If the
map identifies five independent streams, the swarm runs five worktrees.

This is the contrast with Case 3 worth holding onto: Case 3 was *heavy and
solo* (critical blast radius, capped); Case 4 is *heavy and parallel*
(cross-cutting blast radius, uncapped). Same Expedition reference route,
genuinely different topology - because the dimensions read differently.

### Final `delivery-approach.md`

Expedition at full weight, swarm topology, empty de-scope ledger (Expedition's
ledger is empty by definition - it is what the other routes are measured
against). If a designer and product owner did join, their `role_rules` would
fire: `prd.md` required and the intent-fidelity gate before Plan; the
designer's `ui-contract.md` flowing into Specify as scenarios. Each would be
recorded in the routing-guardrails section.

---

## Case 5 - A production hotfix

> **Request:** "Checkout is returning 500s for any cart with a discount code -
> happening now."

### Score

The Needle still scores all four dimensions - they shape the mandatory
backfill - but Hotfix is the one route selected by *urgency* rather than by
the magnitude / blast-radius / terrain composition.

| Dimension | Reading | Justification |
|---|---|---|
| Blast radius | `critical` | Checkout is down for a class of carts - lost revenue, happening live. |
| Terrain | `brownfield-mapped` | The checkout and discount paths are mapped. |
| Magnitude | `small` | The defect is bounded; the fix is expected to be 1–3 files once the cause is found. |
| Intent & role | `engineer`, often paired with `qa` | An engineer fixing a live defect, QA verifying. |

### Compose

A live defect with user impact happening *now*, small magnitude, critical
blast radius - the Needle composes toward **Hotfix**. The shape: Frame is fast
but real (`delivery-approach.md` is written even under time pressure - the audit trail
starts here); Specify is **reproduce-first** (the spec *is* a failing
regression test that reproduces the 500 - simultaneously the BDD scenario and
the TDD red); Clarify collapsed (the reproduction *is* the clarification);
Plan collapsed to a one-line root-cause note; Distribute skipped; Build
expedited; Verify **at full weight, not compressed**; Land ships the fix and
then requires the mandatory backfill.

### Constrain

The `blast_radius: critical` floor's `force_minimum_route: expedition` would
seem to apply - but Hotfix's gate set is *already* at full Verify weight, and
`never_skip: [clarify, verify, land]` is honoured by Hotfix's structure
(Clarify is collapsed *into* the reproduction, not skipped; Verify and Land
run full). Hotfix is the route that compresses the phases *before* Verify and
never Verify itself, which is exactly what the critical floor's rationale -
"critical changes coordinate or they break things quietly" - is protecting.
The critical-blast-radius cap (`max_worktrees: 1`) is moot: Hotfix is solo
anyway.

The methodology's own guard applies here: a fix that turns out to be
`standard`+ in magnitude is *not* a Hotfix - it is an incident. Route it
Expedition, put someone in incident command, use the swarm if it helps. The
Needle scores magnitude precisely so that distinction holds.

### Final `delivery-approach.md`

Hotfix. The §6 "Owed backfills" section of `delivery-approach.md` carries an unchecked
item - the mandatory backfill - and the task is not closeable until it is
paid: `delivery-approach.md` completed properly (not just the urgent stub), the
reproduction test promoted into a real Given/When/Then scenario in
`acceptance-criteria.md` traceable to the defect, and a root-cause line in the
`devlog.md`. `/compass:status` flags the unpaid backfill; `/compass:land`
refuses to close the task; the `stop.sh` hook makes it loud at session end.
Borrowed ceremony is a debt with a due date, and the due date is "before the
task closes."

---

## Case 6 - A task that cannot be framed yet

> **Request:** "Our background job queue is dropping ~2% of jobs under load and
> nobody knows why. Find out."

### Score

The Needle still scores all four dimensions - but this request is not a known
change, it is a *question*. There are no acceptance criteria to state because
the behaviour to fix is the unknown. That is the signal for **exploration**
intent.

| Dimension | Reading | Justification |
|---|---|---|
| Blast radius | `contained` | The investigation itself touches nothing irreversible - reading logs, adding instrumentation behind a flag, reproducing in a sandbox. |
| Terrain | `brownfield-unmapped` | The queue's behaviour under load is exactly what is *not* written down. |
| Magnitude | `small` | The investigation is timeboxed; the eventual fix is unknown and not in scope here. |
| Intent & role | `exploration` (engineer) | "I need to understand this before I can frame it" - not a delivery request. |

### Compose

Exploration intent composes toward **Spike**, the way live-defect urgency
composes toward Hotfix - the routing strategy `reading: { intent: exploration }
→ lean_toward: spike` is the bias. Frame is light but real: `delivery-approach.md` records
the **question** ("what is dropping ~2% of jobs under load?") and a **timebox**.
Specify collapses to that question. Clarify is skipped - there is nothing to QA
against, the behaviour is the unknown. Plan collapses to a timebox and an
approach sketch. Build becomes **Explore**: the engineer instruments and
reproduces freely, and the **TDD strategy is suspended** - the pre-tool hook is
route-aware and does not block, because red-before-green is the wrong
discipline for throwaway diagnostic code. The Needle also writes a `.spike`
marker file in the task directory so the hook knows.

### Constrain

The routing guardrails still apply - and one matters here. If the question
could only be answered by touching `auth`, `payments`, `personal-data`, or
`migrations`, the floor would fire and this would *not* be a Spike; it would be
an Expedition with a discovery-heavy Specify. Here the investigation stays
clear of irreversible surface, so Spike stands. Nothing is floored.

### Final `delivery-approach.md` - and the exit

Spike. Verify becomes **Conclude**: not a test gate, a findings check - *was
the question answered?* The one gate is "the question is answered (or
explicitly answered with 'inconclusive - here is why'), and the finding is
written down." Land becomes **Graduate or Discard**:

- **Graduate** - the spike found the cause (say, a connection-pool exhaustion
  under a specific retry storm). The finding feeds a fresh `/compass:frame` for
  the real fix. That re-frame is a normal route - Standard, probably - and
  guardrails G1–G3 apply to the fix in full. Any diagnostic code carried over
  is now subject to that route's guardrails; in practice most is rewritten
  under TDD. The spike's `delivery-approach.md` records "graduated → task `<slug>`".
- **Discard** - the spike concluded "this is environmental, not our code" or
  "inconclusive within the timebox." The finding goes in `devlog.md`, any
  follow-up is filed, and the spike closes. A discarded spike with a clear
  answer succeeded.

Nothing landed from the Spike itself. That is the whole safety model: the
de-scopes (Clarify skipped, TDD strategy suspended) are safe *because* there is
no delivery output to protect - the only path from spike code to `main` runs
through a real route. See `routes/spike.md`.

---

## The same request, four routes

The cases above are six different requests. Here is one *literal* request -
**"add a CSV export"** - routed four ways, because who asks and what it touches
changes everything. This is the clearest demonstration that Compass routes the
*terrain*, not the words.

### "Add a CSV export" - engineer, internal admin tool

Magnitude `small`, blast radius `contained` (an admin tool, bounded), terrain
`brownfield-mapped`, role `engineer`, no domain tags. Composes to **Express**:
one scenario ("given a filtered table, when the user exports, then a CSV with
those rows downloads"), Clarify collapsed, Plan a one-liner, full TDD on a
small surface, one gate. Done in an afternoon. The Needle stays out of the way -
correctly.

### "Add a CSV export" - product owner, "let finance self-serve"

Same three words, but a `prd.md` sits behind them, and the brief's outcome
is "let finance self-serve their month-end numbers." The Needle reads intent
as the *actual outcome wanted*, not the literal request - and "self-serve"
implies filters that match what finance actually needs, perhaps scheduling,
perhaps permissions. Magnitude is no longer `small`; it is `standard` or
larger. The `product-owner` role rule fires: `prd.md` required, the
intent-fidelity gate before Plan. Composes to **Standard or heavier**, with a
gate that checks the export scenarios actually deliver "self-serve" and not
just "a button that produces a file." Same words, a genuinely bigger route -
because the intent under them is bigger.

### "Add a CSV export" - engineer, export of the payments ledger

Same three words again, but the table is the payments ledger. The Needle tags
`touches: [payments, personal-data]`. Magnitude might still be `small`. It does
not matter: the routing guardrail (floor) `when: { touches: [payments,
personal-data] }` → `force_minimum_route: expedition` fires. Composes to
**Expedition** - full
discovery (what exactly is in this export? what must *not* be?), full Clarify,
a `design.md` with the data-handling decisions recorded, every gate, `security`
full. A "small" feature, the full treatment, because of what it touches.

### "Add a CSV export" - product marketer, a launch feature

A marketer invokes `/compass:position` for an export feature being launched.
The `product-marketer` role rule fires: `positioning.md` and
`launch-readiness.md` required, the `claims` review dimension on, and **Land
blocked** until every claim ("export your data in one click", "works with
spreadsheets you already use") traces to a passing scenario. The engineering
work might be Express-sized, but the route carries the claims gate to Land
regardless - `verify.claims` is immovable. Same three words; an extra gate
that did not exist in the other three readings.

Four routes, one request. The request did not change. The terrain did - and
Compass routes the terrain.

---

## Re-framing - when the terrain was misread

Routing happens at Frame, but the terrain reading can turn out wrong, and the
honest response is not to push on with a route you no longer believe.

`/compass:frame --reframe` re-scores the four dimensions mid-task, writes a
**new revision** of `delivery-approach.md` (the prior revision is kept visible under a
"Superseded" heading), and records what changed and why. A re-frame is a
normal event, not a failure. *A route quietly outgrown is the failure.*

A re-frame is also *recorded as data*. `/compass:frame --reframe` re-runs
`compass route evaluate --write`, which detects that the route changed and
appends an entry to `task.yml`'s `reframes` log - `from_route`, `to_route`, the
date, and the `--reason`. One entry is an anecdote; the log across every task
is the framework's feedback signal. `compass calibration` reads it and reports
the pattern: are re-frames mostly *up* (the Needle is under-sizing) or *down*
(over-sizing)? The triggers below are the individual events; calibration is how
the framework notices when they add up to a systematic mis-read of the terrain -
see `docs/methodology.md` §6.

The triggers are concrete:

- **Build reveals under-read magnitude.** A "small" change is unspooling into a
  multi-module refactor. The `builder` agent stops and flags it; the Navigator
  re-scores. This is why the routing skill says, when magnitude is genuinely
  unclear, estimate *up* - collapsing a phase that turned out easy is cheap;
  discovering mid-Build that the route was too light is expensive.
- **Clarify finds the spec is bigger than the route assumed.** More scenarios,
  more ambiguity than a Standard route's Clarify pass can absorb. Do not push a
  Standard route through an Expedition-shaped problem.
- **A `touches:` tag surfaces late.** You discover mid-Build that the change
  reaches auth after all. Re-frame, the floor fires, the route is raised - and
  it is recorded, not silent.
- **A roundtable changes scope.** `/compass:roundtable` decides to cut or
  expand scope; if the decision touches the route, the roundtable's own gate
  says to follow it with a re-frame.

The re-framed `delivery-approach.md` is the contract again - the next session reads the
latest revision and knows exactly where the task stands.

---

## What the routing system is really for

Every case above ends in a `delivery-approach.md` that a human can read and a later
session can resume from. That is the deliverable. The Needle does not just
classify the task - it explains the classification, records every guardrail
that fired, and writes down every skip with the reason it is safe. The
adaptivity is real, and it is *bounded*: bounded by the four-dimension rubric,
bounded by the routing guardrails in `governance/routing-policy.md`, bounded by
the rule that an unjustified skip is not a skip. That is what keeps "adaptive"
from sliding into "arbitrary."
