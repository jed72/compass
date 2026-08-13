# Route - notifications-subsystem

> **Task:** Build the in-app notifications subsystem from the brief - durable delivery, per-category user preferences, a security override that mute cannot suppress.
> **Framed:** 2026-03-02 by S. Voss (product manager) with R. Okafor (engineer) · **Revision:** 1
> **Reference route:** Expedition

---

## 1. The four dimension readings

| Dimension | Reading | One-line justification |
|---|---|---|
| **Blast radius** | contained | A new, self-contained subsystem with its own table and module tree. Other code calls *into* it; it does not reach back into theirs. If it misbehaves, notifications are wrong - the rest of the product is not. |
| **Terrain** | greenfield | There is no notifications capability today (`brief.md` Problem). Nothing to distil - the scenarios are discovered from the brief, not reverse-engineered. |
| **Magnitude** | standard | On its own, the *code* is standard-sized - a module tree, an API surface, one new table, ~a week. **The route is not standard, though** - see §3. |
| **Intent & role** | product-owner | A product manager invoked this with a `brief.md`. The intent is the outcome in that brief, not just "add notifications" - and the role pulls RG-ROLE-002 into play. |

**Domain tags (`touches:`):** `migrations` - the subsystem ships a new table as a schema migration. This tag is honest and load-bearing: it is what fires RG-FLOOR-003.

---

## 2. The composed candidate route

Candidate route: **Standard** - `magnitude: standard` matched routing strategy
RS-SHAPE-005 ("the default working shape"). On the magnitude/blast/terrain
composition *alone*, this would have been a Standard task.

It is not a Standard task. §3 is why.

Candidate review dimensions, after the guardrails in §3 apply: correctness,
governance, traceability, regression, security (full), clarity, claims - the
full Expedition set.

---

## 3. Routing guardrails that fired

This is the section that decides the route. Two routing guardrails fired -
`compass route evaluate` is the source of record for both.

| Rule type | Rule | What it changed | Rationale (quoted from the policy) |
|---|---|---|---|
| floor | RG-FLOOR-003 - `touches_any: [migrations]` | **Candidate route raised: standard → expedition.** | "Domain risk overrides magnitude. A one-line auth change is not small." |
| role_rule | RG-ROLE-002 - `role: product-owner` | `brief.md` required as an artifact; **Plan blocked** until the spec is checked against the brief for intent fidelity. | "Built-the-thing-right and built-the-right-thing are different checks." |

**Why RG-FLOOR-003 is the right call here, not bureaucracy:** a migration is
irreversible in the way that matters - a forward migration that runs in
production cannot be wished away, only migrated past. The brief's own
constraint says the table ships "reviewed forward *and* rollback". That is
Expedition-shaped care, and the floor is what guarantees the route delivers it
regardless of how small the surrounding code looks. The same tag also makes
**guardrail G5** apply: a human signs off the irreversible change before Land
(see §6 and `task.yml` `approvals:`).

**Why RG-ROLE-002 fired:** a product manager wrote `brief.md`. The rule blocks
Plan until the spec has been checked back against the brief - built-the-thing-
right (the gates) and built-the-right-thing (intent fidelity) are different
checks, and Expedition runs both. That check is recorded at the foot of
`brief.md`; it passed on 2026-03-06 and Plan was unblocked.

---

## 4. The final route

### 4a. Per-phase weight

| Phase | Weight | Notes |
|---|---|---|
| Frame | Full | This document, with explicit `touches:` tagging - Expedition is where domain floors most often fire, and one did. |
| Specify | Full BDD discovery | Greenfield - six scenarios discovered from `brief.md`, grouped by independence into two groups (A: delivery & dispatch, B: preferences). The grouping seeds the distribution map. |
| Clarify | Full pass | Self-QA, governance QA, explicit ambiguity ledger. The product owner reviewed here. See `clarifications.md`. |
| Plan | Full `plan.md` + `distribution-map.md` | Architecture, every design decision as an ADR note, governance check, scenario-group → stream mapping. **Was blocked** by RG-ROLE-002 until the intent-fidelity check passed. |
| Distribute | Swarm | `scripts/swarm.sh` created two worktrees from `distribution-map.md` - stream-1 (dispatch/store), stream-2 (preferences). One `builder` each, plus an `orchestrator`. |
| Build | Full TDD per stream | Two builders, parallel, red→green→refactor in their own worktrees. The orchestrator watched the shared `migrations/0042` and `api.py` surface. |
| Verify | All gates, all dimensions | Per-stream verification, then combined verification after integration. See `verification-report.md`. |
| Land | Full | `scripts/integrate.sh` - orchestrated merge, full combined regression, living docs, G5 human sign-off on the migration. |

### 4b. Gate set

- Number of gates: all - the full Expedition set, plus the mid-route per-worktree checkpoint.
- Review dimensions applied: correctness, governance, traceability, regression, security (full, not scaled - it is greenfield code with a new table), clarity, claims.
- Immovable gates stapled on: verify.correctness, verify.governance, verify.traceability - all already in Expedition's shape. `verify.claims` is in Expedition's shape too; no marketer was in play, so it is satisfied trivially (no claims to back), but the gate still exists.

### 4c. Swarm topology

- Topology: swarm (2 streams)
- Stream count: 2 - from `distribution-map.md`. Two genuinely independent scenario groups; below the 4+ that "swarm" usually implies, but it runs the swarm machinery (worktrees + orchestrator) because the two streams share the migration and the API surface and need the orchestrator to police that.
- Worktree root: `../.compass-worktrees` (from `.compass/config.yml`)
- Cap in effect: none - blast radius is `contained`, so the `critical → max_worktrees: 1` cap does not apply. `config.yml` `max_worktrees` is 6; 2 is well under it.
- Orchestrator agent: yes - owns the shared migration/API surface during Build and the integration at Land.

---

## 5. The de-scope ledger

**Empty by definition.** Expedition is the route the others are measured
against - it collapses and skips nothing. There is no "safe to skip because…"
line here because nothing is skipped.

The only reduction in play is *cap-driven*, and there isn't even one of those:
no cap applied (§4c). The stream count is 2 not 4+ because the *work* only
decomposes into two independent groups (`distribution-map.md` §2) - that is the
honest decomposition, not a de-scope.

---

## 6. Owed backfills

- [x] None owed. Expedition borrows no ceremony from the front of the pipeline -
  it runs every phase at full weight in order, so there is nothing to pay back.

Note - not a backfill, but a Land obligation: guardrail **G5** applies because
the task `touches: [migrations]`. A human signs off the irreversible schema
change before Land. That sign-off is recorded in `task.yml` `approvals:` and
`compass check` requires it; it is a *gate*, not a borrowed-and-owed item.

---

## 7. Human overrides

No human overrides. Route confirmed as composed. (The product manager could
have argued the magnitude reading down - but RG-FLOOR-003 is a routing
guardrail, and a human cannot override a routing guardrail per-task. The route
would have stayed Expedition regardless. That is the floor doing its job.)

---

## 8. Confirmation

- [x] Route presented to the invoker and confirmed.
- [x] Every dimension in §1 has a justification.
- [x] §5 de-scope ledger is empty - Expedition skips nothing.
- [x] Not a Spike route - no `.spike` marker needed.
- [x] `devlog.md` opened with the Frame entry.

Next phase: **Specify** (`/compass:define`) - full BDD discovery from `brief.md`.
