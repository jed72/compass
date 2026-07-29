---
description: Set up git worktrees and the agent swarm, one stream per independent unit
allowed-tools: Read, Write, Edit, Bash, Glob
---

# /compass:distribute

Distribute executes the topology that Plan decided. It creates the worktrees
and assigns the agent swarm.

## First: is Distribute in play?

Read `route.md`. Distribute is **skipped on solo routes** - Express, Hotfix,
Spike, and most Standard routes work on the current branch with no worktree. If
`route.md` says solo, stop: confirm the de-scope reason, and point the user to
`/compass:build`. Distribute is a no-op there, not a phase to invent.

It runs when the distribution map shows genuinely independent units. The
pair/swarm boundaries are framework constants (methodology §7); the topology
and the worktree cap come from `route.md` - which the CLI computed from
`governance/routing-policy.yml` (`route_shapes.topology`, the
`routing_guardrails.caps`):
- **pair** (2–3 streams) - larger Standard routes. One worktree per stream, one
  `builder` agent each, no dedicated orchestrator - the lead builder integrates.
- **swarm** (4+ streams) - Expedition. One worktree per stream, one `builder`
  per worktree, plus an `orchestrator` agent that writes no feature code.

## Setup

- Read `distribution-map.md` - it is the source of truth for stream count and
  which scenarios each stream owns.
- Load the `worktree-swarm` skill.
- Invoke the `orchestrator` agent. **Only the orchestrator** creates worktrees
  and lands them.

## Procedure

1. **Verify the count.** Cross-check the map's stream count against the
   topology and any routing-guardrail `cap` recorded in `route.md` (the CLI
   computed both from `routing-policy.yml`). Note: `critical` blast radius caps
   worktrees at 1 - an Expedition can be heavy *and* solo. If the cap and the
   map disagree, the cap wins; record it as cap-driven.
2. **Create the worktrees.** Run `scripts/swarm.sh` - it creates one git
   worktree per stream under the configured `worktree_root` and launches a
   `builder` agent in each. Each worktree is an isolated checkout so a builder
   can run a full red→green cycle without destabilising siblings.
3. **Assign.** Give each builder its scenario set from the distribution map.
   A builder works *only* inside its assigned worktree and never touches a
   sibling's.
4. **Record** the topology - stream-to-worktree-to-scenario assignment - in
   the `devlog.md`.

## Gate

Worktrees exist and match the distribution map; every stream has a builder and
an assigned scenario set; the orchestrator is in place (swarm). Next:
`/compass:build`.
