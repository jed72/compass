---
name: worktree-multiagent
description: How parallel streams are created, isolated and integrated across git worktrees. Load at breakdown on a swarm topology.
---

# Worktree Swarm

Parallelism in Compass is **decided in Plan** (the distribution map) and
**executed in breakdown** (the worktree topology). This skill covers both
halves: how to decompose work correctly, and how to run and land the swarm
without the parallelism costing more than it saves.

## Topology - what runs when

| Topology | Streams | Setup | Who integrates |
|---|---|---|---|
| **Solo** | 1 | No worktree; current branch. Breakdown is a no-op. | The builder, trivially. |
| **Pair** | 2–3 | One worktree per stream; one `builder` each; no dedicated orchestrator. | The lead builder. |
| **Swarm** | 4+ | One worktree per stream; one `builder` each; plus one `orchestrator`. | The orchestrator. |

Assess's size and risk assessment set the default topology; the
distribution map sets the stream count; `.compass/config.yml` thresholds and the
routing-guardrail caps bound it.

## The critical-risk cap

The standing cap: **`critical` risk pins `max_worktrees` to 1.** A
critical change runs solo even on initiative. This is deliberate - a swarm buys
speed but carries coordination risk, and on a critical change the coordination
risk costs more than the speed saves. An initiative that is heavy *and* solo is
not a contradiction; it is the cap working. The initiative still writes a
`distribution-map.md` - it is the record of what could have been parallel and
why it wasn't.

## Decomposing work into independent streams (Plan)

A stream is a unit of work that can run start-to-finish without waiting on,
colliding with, or reaching into another stream. Independence has two tests,
and both must hold:

1. **Disjoint code.** The streams touch non-overlapping files and interfaces.
2. **Disjoint scenarios.** The streams satisfy non-overlapping scenario groups
   from `acceptance-criteria.md`.

Independence is *determined*, not guessed - you derive it from the scenario
file and the technical plan. The scenario grouping done at the define stage
(initiative's "group scenarios by independence") is the seed; the distribution
map is where you confirm it against the plan.

Practical decomposition heuristics:

- **Cut along boundaries the architecture already has** - module boundaries,
  service boundaries, layers. Cutting across one of them creates a shared
  surface and a guaranteed collision.
- **Shared surface = shared stream, or sequenced streams.** If two units both
  need to change the same interface, either fold them into one stream or
  sequence them (one lands, then the other branches from the result). Do not
  pretend they are parallel.
- **Pull shared foundations forward.** If three streams all need a new shared
  type or utility, that is a stream-zero that lands first, not a thing three
  streams each invent.
- **Be honest about the count.** Four shaky streams are worse than two clean
  ones. The map records *what could be parallel* - if the honest answer is
  "less than it looks," that is the map's job to say.

## Git worktree mechanics

A git worktree is a second working directory backed by the same repository -
its own checked-out branch, its own files, sharing one `.git`. That isolation
is what lets a builder run a full red→green TDD cycle, including a failing
suite, without destabilising siblings.

- `scripts/swarm.sh` creates one worktree per stream and launches one `builder`
  agent in each. Only the `orchestrator` runs it.
- `scripts/integrate.sh` lands the worktrees back together. Only the
  `orchestrator` runs it.
- A builder lives inside exactly one worktree for the life of the stream.

## The orchestrator / builder protocol

**The orchestrator** writes no feature code. Its job is coordination, collision
detection, and integration:

- Hands each builder a charter: its worktree, its scenario group, its slice of
  the plan.
- Monitors streams during Build for convergence on shared surface - shared
  files, shared interfaces, a scenario whose implementation reaches outside its
  group.
- Intervenes *before* a collision: re-sequences streams, re-cuts a boundary, or
  escalates to a re-assess if the distribution map was wrong.
- Is the **only** agent permitted to make a cross-stream change.

**A builder** owns its stream and nothing else:

- Works only inside its assigned worktree. Never touches a sibling's.
- Routes every cross-stream need through the orchestrator - "I need to change
  an interface another stream owns" is an orchestrator message, never a reach
  across.
- Runs full TDD inside its worktree (see `tdd-discipline`).

## Integration discipline (ship)

1. Confirm every stream is independently green - the `verifier` has per-stream
   evidence.
2. The orchestrator runs `scripts/integrate.sh` to merge worktrees in a
   coordinated order (foundations first, dependents after).
3. The orchestrator resolves any merge conflicts - no one else may.
4. **Run combined regression across the integrated result.** This is
   non-negotiable on initiative. Per-stream green does not imply integrated
   green; proving the combination is the entire reason the orchestrator owns
   ship. Record the run and link the record.
5. Resolve every owed follow-up, update living docs, write the integration
   devlog entry.

## Never stash across a worktree hop

Never stash in one worktree and pop in another - and never stash at all
inside a temporary worktree. A stash lives in the shared repository, but
the working state it captures belongs to one checkout: a stash popped
inside a temporary worktree that is then removed
destroys the stashed work along with the worktree. Learned the hard way during a CI fix - the
change survived only because it had been committed elsewhere first. If
work must move between worktrees, commit it (a WIP commit on the
stream's branch is fine and can be amended); the branch is durable, the
stash is not.

## Anti-patterns

- **Optimistic decomposition** - declaring streams independent because you want
  parallelism, not because the code and scenarios are disjoint. The collision
  surfaces at integration, where it is most expensive.
- **The reaching builder** - a builder editing a sibling's worktree "just to
  unblock myself." It destroys the isolation guarantee for everyone.
- **The coding orchestrator** - an orchestrator writing feature code. If it is
  tempted to, the decomposition was wrong; fix the decomposition.
- **Skipping combined regression** - trusting per-stream green. The integration
  is exactly where the untested interactions live.
- **Swarming a critical change** - ignoring the cap. The cap is a routing
  guardrail; honour it.
