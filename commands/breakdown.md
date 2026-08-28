---
description: Break the work into independent subtasks and set up a worktree for each
allowed-tools: Read, Write, Edit, Bash, Glob
---

# /compass:breakdown

Breakdown executes the orchestration that the design decided. It creates the
worktrees and assigns the agent multiagent.

## First: is breakdown in play?

Read `delivery-approach.md`. Breakdown is **skipped on solo work** - quick
fixes, hotfixes, spikes, and most features work on the current branch with no
worktree. If `delivery-approach.md` says solo, stop: confirm the de-scope
reason, and point the user to `/compass:implement`. Breakdown is a no-op
there, not a stage to invent.

It runs when the distribution map shows genuinely independent units. The
pair/multiagent boundaries are framework constants (methodology §7); the orchestration
and the worktree cap come from `delivery-approach.md` - which the CLI
computed from `governance/routing-policy.yml` (the shapes' `orchestration`, the
policy `caps`):
- **pair** (2-3 subtasks) - larger features. One worktree per subtask, one
  `builder` agent each, no dedicated orchestrator - the lead builder
  integrates.
- **multiagent** (4+ subtasks) - initiatives. One worktree per subtask, one
  `builder` per worktree, plus an `orchestrator` agent that writes no
  feature code.

## Setup

- Read `distribution-map.md` - it is the source of truth for subtask count
  and which scenarios each subtask owns.
- Load the `worktree-multiagent` skill.
- Invoke the `orchestrator` agent. **Only the orchestrator** creates
  worktrees and integrates them.

## Procedure

1. **Verify the count.** Cross-check the map's subtask count against the
   orchestration and any policy `cap` recorded in `delivery-approach.md` (the CLI
   computed both from `routing-policy.yml`). Note: `critical` risk caps
   worktrees at 1 - an initiative can be heavy *and* solo. If the cap and
   the map disagree, the cap wins; record it as cap-driven.
2. **Create the worktrees.** Run `scripts/multiagent.sh` - it creates one git
   worktree per subtask under the configured `worktree_root` and launches a
   `builder` agent in each. Each worktree is an isolated checkout so a
   builder can run a full red-to-green cycle without destabilising siblings.
3. **Assign.** Give each builder its scenario set from the distribution map.
   A builder works *only* inside its assigned worktree and never touches a
   sibling's.
4. **Record** the orchestration - subtask-to-worktree-to-scenario assignment - in
   the `devlog.md`.

## Gate

Worktrees exist and match the distribution map; every subtask has a builder
and an assigned scenario set; the orchestrator is in place (multiagent). Next:
`/compass:implement`.
