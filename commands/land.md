---
description: Integrate worktrees, run regression, update living docs, resolve owed backfills
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# /compass:land

Land closes the task: integrate the work, prove the combination, update the
living docs, and pay back every borrowed bit of ceremony. A task with an unpaid
backfill is an open task - Land refuses to close it.

## Setup

- Read `delivery-approach.md` for the topology and the list of owed backfills.
- Read `verification-report.md` - Land does not run on unverified work.

## Spike note

On a Spike route Land is **Graduate or Discard** - never "merge to main".
Nothing lands from a Spike. Either the findings feed a fresh `/compass:frame`
for real delivery work (graduation - see `routes/spike.md`), or the spike is
discarded with its learnings recorded in `devlog.md`. The procedure below is
for delivery routes; on a Spike, follow the graduate-or-discard step in
`routes/spike.md` instead.

## Procedure

1. **Integrate.** Solo route: commit on the current branch with
   `compass land-commit -m "<message>"` - it is robust to auto-fixing
   pre-commit hooks (which otherwise silently no-op the commit and leave HEAD
   unmoved), retries once after re-staging the hooks' fixes, and **errors if
   HEAD did not advance** so a Land can never falsely believe it landed.
   Pass `--task <slug>` to mark the task landed only on a verified commit.
   The message follows strategy S7 (write for a cold reader): say what changed
   and why, for someone who was not in the conversation; no `Co-Authored-By:`
   trailer for any agent and no "Generated with" footer. The same applies to a
   pull-request body.
   Pair or swarm: the `orchestrator` (or lead builder on a pair) runs
   `scripts/integrate.sh` - an orchestrated merge of all worktrees. The
   orchestrator is the only agent allowed to resolve cross-stream conflicts.
2. **Combined regression.** Run regression across the *combined* result. On a
   swarm this is non-negotiable - per-stream green does not imply integrated
   green. Paste the output.
3. **Update living docs.** Bring READMEs, architecture notes, and any docs the
   change touched in line with reality. If the change is launch-visible (the
   product-marketer role is in play), draft the release notes here too -
   pulled from `positioning.md`, so every line in the notes is already a
   scenario-backed claim. `marketing-lens` owns their wording.
4. **Resolve owed backfills.** Check `delivery-approach.md`'s de-scope ledger, `task.yml`'s
   `backfills:` and `claims:` lists, and the route's standing obligations:
   - **Hotfix backfill** (mandatory): `delivery-approach.md` completed properly (not the
     urgent stub); the reproduction test promoted into a real Given/When/Then
     scenario in `acceptance-criteria.md` *and* `task.yml`'s `scenarios:`, traceable to
     the defect; a root-cause line in the `devlog.md`. Mark the matching
     `task.yml` `backfills:` entry `paid` - `compass check`'s `backfills-paid`
     check fails Land while any is unpaid.
   - **Marketer claims gate** (when the product-marketer role is in play):
     every claim in `task.yml`'s `claims:` traces to a passing scenario id.
     Invoke `marketing-lens` to confirm; `compass check`'s
     `claim-traces-to-scenario` check is the mechanical backing. This gate
     blocks Land per the routing policy's `role_rules`.
   - Any other de-scoped artifact the ledger marked for backfill.
5. **Run `compass check` as the final mechanical gate.** It runs every
   `guardrails.yml` check against `task.yml` and `evidence/` - suite passed,
   traceability holds, every `pass` gate has evidence, no unpaid backfill, and
   (when G5 applies) a human approval is on record. It exits non-zero on any
   failure; paste its output. This is the checkable backbone of Land.

   **Typed Definition of Done (G4 - evidence, not assertion):** `compass check`
   also parses the `### Definition of Done` section of `verification-report.md`
   and enforces the inline-tag rule. Every unchecked DoD box must carry one of:

   - `- [ ] (evidence: EV-<id>) <description>` - passes if `EV-<id>` is in
     `task.yml`'s evidence registry with an accepted type (`test-run`,
     `command-output`, `manual-review`, `human-approval`, `artifact`, etc.).
   - `- [ ] (backfill: BF-<id>) <description>` - passes if `BF-<id>` is in
     `task.yml`'s `backfills:` with `status: owed`. The backfill can carry an
     optional `target_task: <slug>` field; when set, the named task's Land check
     fails until this entry is paid (`compass backfill pay --task <slug> <BF-id>`).
   - `- [x] <description>` - a human-ticked box passes unconditionally.
   - `- [ ] <bare description>` - **fails**. Narrative notes in `devlog.md`
     (e.g. "USER TO APPLY") never clear a DoD item (G4: evidence, not assertion).

   Cross-task blocking: if another task's `backfills:` has `target_task` pointing
   at the task being landed, and that backfill is still `status: owed`, `compass
   check` fails at Land even if this task's own DoD section is clean. Pay the
   upstream backfill first.
6. **Capture process friction (advisory - never a gate).** With the gate
   already cleared in step 5, record where Compass's *own* ceremony cost more
   than it returned between Frame and Land. Run
   `compass _friction-capture --internal` - it assembles a draft `friction:`
   list from signals the CLI already computed (recorded `reframes`, absorbed
   reframe-debt) and writes it into `task.yml`. Then offer the author **one
   optional line**: *"anything the framework made harder than it should have
   been?"* - pass it with `--note "…" --note-category <over-ceremony|tooling|…>
   --note-phase <phase>`. **Recording nothing is a valid, common outcome.**
   This step never blocks Land: it runs after the gate, writes only the
   `friction:` section (no backfill, no gate), and `compass calibration
   --friction` later aggregates it across tasks as advice, never as a gate
   (ADR-003: Flow advises but never gates).
7. **Final devlog entry.** One entry: what landed, how it was verified, what
   backfills were paid.

## Gate - Land refuses to close the task unless

- integration is complete and combined regression is green (evidence pasted);
- living docs are updated;
- `compass check` passes (its output pasted);
- **every owed backfill is paid** - no unpaid Hotfix backfill, no unbacked
  marketing claim, no de-scoped artifact left owed.

If a backfill cannot be completed now, the task stays open and
`/compass:status` keeps flagging it. Borrowed ceremony is a debt with a due
date, and the due date is "before the task closes."
