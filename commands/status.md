---
description: Show current Compass tasks — route, phase, gate status, owed backfills
argument-hint: "[task-slug]"
allowed-tools: Read, Bash, Glob, Grep
---

# /compass:status

Report the state of Compass work on disk. Read-only — this changes nothing.

**Scope:** $ARGUMENTS — if a task slug is given, report just that task; if
empty, report every task under `.compass/work/`.

`/compass:status` looks *down* into a task (or lists them flat). For the
*managed* cross-task view — triage, blockers, owed-backfill aggregation, and
the periodic digest — use `/compass:flow`.

## Procedure

1. **Find the tasks.** List `.compass/work/*/`. Each subdirectory is a task,
   and `task.yml` is its machine-readable spine — read it alongside the prose
   artifacts.
2. **For each task, read the artifacts present** and report:
   - **Route** — from `route.md` / `task.yml`: the nearest reference route, the
     four dimension readings, and any routing guardrail that fired.
   - **Phase** — which pipeline phase the task is in. Infer from which
     artifacts exist: `route.md` → Frame done; `spec.feature.md` → Specify
     done; `clarifications.md` → Clarify done; `plan.md` → Plan done;
     `distribution-map.md` → Distribute set up; `verification-report.md` →
     Verify done. Cross-check against the route's de-scope ledger so a
     *collapsed* phase is not reported as *missing*.
   - **Gate status** — from `verification-report.md` and `task.yml`'s `gates:`
     if present: which gates are green, which are not. For the *mechanical*
     gate status you may run `compass check --task <slug>` — it reports the
     guardrail checks against `task.yml` and `evidence/`. (It is read-only here;
     it changes nothing.)
   - **Owed backfills** — scan `route.md`'s de-scope ledger and the route's
     standing obligations. Flag loudly:
     - an unpaid **Hotfix backfill** (route stub not completed, reproduction
       test not promoted to a scenario, no root-cause devlog line);
     - an **unbacked marketing claim** — a claim in `positioning.md` with no
       passing scenario behind it;
     - any de-scoped artifact still marked owed.
3. **Summarise.** A short table: task · route · phase · gate status · backfills
   owed. Put anything blocking a Land at the top.

## Note

If a `route.md` is missing for a directory under `work/`, that task was started
without Frame — flag it as a guardrail violation, not just an incomplete task.
