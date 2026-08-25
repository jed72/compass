---
description: Ship - integrate worktrees, run regression, update living docs, settle owed follow-ups
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# /compass:ship

Ship closes the issue: integrate the work, prove the combination, update the
living docs, and pay back every borrowed bit of ceremony. An issue with an
unsettled follow-up is an open issue - ship refuses to close it.

## Setup

- Read `delivery-approach.md` for the topology and the list of owed
  follow-ups.
- Read `verification-report.md` - shipping does not run on unverified work.

## Spike note

On a spike, ship is **graduate or discard** - never "merge to main". Nothing
ships from a spike. Either the findings feed a fresh `/compass:assess` for
real delivery work (graduation - see `approaches/spike.md`), or the spike is
discarded with its learnings recorded in `devlog.md`. The procedure below is
for delivery work; on a spike, follow the graduate-or-discard step in
`approaches/spike.md` instead.

## Procedure

1. **Integrate.** Solo topology: commit on the current branch with
   `compass ship-commit -m "<message>"` - it is robust to auto-fixing
   pre-commit hooks (which otherwise silently no-op the commit and leave
   HEAD unmoved), retries once after re-staging the hooks' fixes, and
   **errors if HEAD did not advance** so shipping can never falsely believe
   it happened. Pass `--issue <slug>` to mark the issue shipped only on a
   verified commit. The message follows the cold-reader strategy: say what
   changed and why, for someone who was not in the conversation; no
   `Co-Authored-By:` trailer for any agent and no "Generated with" footer.
   The same applies to a pull-request body.
   Pair or swarm: the `orchestrator` (or lead builder on a pair) runs
   `scripts/integrate.sh` - an orchestrated merge of all worktrees. The
   orchestrator is the only agent allowed to resolve cross-stream conflicts.
2. **Combined regression.** Run regression across the *combined* result. On
   a swarm this is non-negotiable - per-stream green does not imply
   integrated green. Record the run and link the record.
3. **Update living docs.** Bring READMEs, architecture notes, and any docs
   the change touched in line with reality. If the change is launch-visible
   (the product-marketer role is in play), draft the release notes here
   too - pulled from `positioning.md`, so every line in the notes is already
   a scenario-backed claim. `marketing-lens` owns their wording.
4. **Settle owed follow-ups.** Check `delivery-approach.md`'s de-scope
   ledger, `task.yml`'s `follow_ups:` and `claims:` lists, and the
   approach's standing obligations:
   - **Hotfix follow-up** (mandatory): `delivery-approach.md` completed
     properly (not the urgent stub); the reproduction test promoted into a
     real Given/When/Then scenario in `acceptance-criteria.md` *and*
     `task.yml`'s `scenarios:`, traceable to the defect; a root-cause line
     in the `devlog.md`. Mark the matching `follow_ups:` entry `paid` -
     `compass check` fails at ship while any is owed.
   - **Marketer claims gate** (when the product-marketer role is in play):
     every claim in `task.yml`'s `claims:` traces to a passing scenario id.
     Invoke `marketing-lens` to confirm; `compass check`'s
     `claim-traces-to-scenario` check is the mechanical backing. This gate
     blocks shipping per the routing policy's `role_rules`.
   - Any other de-scoped artifact the ledger marked as owed.
5. **Run `compass check` as the final mechanical gate.** It runs every
   `guardrails.yml` check against `task.yml` and `evidence/` - suite
   passed, traceability holds, every `pass` gate has evidence, no owed
   follow-up unpaid, and (where a human sign-off applies) the approval is
   on record. It exits non-zero on any failure; record its output and link
   the record. This is
   the checkable backbone of shipping.

   **Typed Definition of Done (evidence, not assertion):** `compass check`
   also parses the `### Definition of Done` section of
   `verification-report.md` and enforces the inline-tag rule. Every
   unchecked DoD box must carry one of:

   - `- [ ] (evidence: EV-<id>) <description>` - passes if `EV-<id>` is in
     `task.yml`'s evidence registry with an accepted type (`test-run`,
     `command-output`, `manual-review`, `human-approval`, `artifact`, etc.).
   - `- [ ] (follow-up: FU-<id>) <description>` - passes if `FU-<id>` is in
     `task.yml`'s `follow_ups:` with `status: owed`. The follow-up can
     carry an optional `target_task: <slug>` field; when set, the named
     issue's ship check fails until this entry is paid
     (`compass follow-up resolve --issue <slug> <FU-id>` - the CLI verb renames
     with the CLI-voice slice).
   - `- [x] <description>` - a human-ticked box passes unconditionally.
   - `- [ ] <bare description>` - **fails**. Narrative notes in `devlog.md`
     (e.g. "USER TO APPLY") never clear a DoD item - evidence, not
     assertion.

   Cross-issue blocking: if another issue's `follow_ups:` has `target_task`
   pointing at the issue being shipped, and that follow-up is still
   `status: owed`, `compass check` fails at ship even if this issue's own
   DoD section is clean. Pay the upstream follow-up first.
6. **Capture process friction (advisory - never a gate).** With the gate
   already cleared in step 5, record where Compass's *own* ceremony cost
   more than it returned between triage and ship. Run
   `compass _friction-capture --internal` - it assembles a draft
   `friction:` list from signals the CLI already computed (recorded
   re-assessments, absorbed assessment-debt) and writes it into `task.yml`.
   Then offer the author **one optional line**: *"anything the framework
   made harder than it should have been?"* - pass it with `--note "..."
   --note-category <over-ceremony|tooling|...> --note-phase <stage>`.
   **Recording nothing is a valid, common outcome.** This step never blocks
   shipping: it runs after the gate, writes only the `friction:` section
   (no follow-up, no gate), and `compass retro --friction` later
   aggregates it across issues as advice, never as a gate (Flow advises
   but never gates).
7. **Final devlog entry.** One entry: what shipped, how it was verified,
   what follow-ups were settled.

## Gate - ship refuses to close the issue unless

- integration is complete and combined regression is green (evidence recorded
  and linked);
- living docs are updated;
- `compass check` passes (its output recorded and linked);
- **every owed follow-up is settled** - no unsettled hotfix follow-up, no
  unbacked marketing claim, no de-scoped artifact left owed.

If a follow-up cannot be completed now, the issue stays open and
`/compass:status` keeps flagging it. Borrowed ceremony is a debt with a due
date, and the due date is "before the issue closes."
