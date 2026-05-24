---
STATUS: ACCEPTED
date: 2026-05-24
---

# Compass — Service Ownership

<!-- Frame reads this file and includes it in architecture-loaded.yml as a
     narrative artifact. The architect-lens uses ownership information to
     flag when a proposed change crosses component boundaries — a common source
     of undetected coupling and rework.

     Keep this file current. Stale ownership is worse than no ownership file:
     the lens will flag risks against the wrong surface. -->

## Component ownership

Compass is a single-maintainer framework. All components are owned by the
framework maintainer. The table below names the component, what it owns
exclusively, and what it must not do.

| Component | Owns | Must own exclusively |
|---|---|---|
| `cli/compass` | Route evaluation, gate checking, tdd-red/green evidence, rework-scan, calibration, ADR helpers | All mechanism-produced writes to task spines and evidence directories |
| `hooks/pre-tool.sh` | `.red` marker gate enforcement | The decision of whether to block a tool call |
| `hooks/stop.sh` | Session-end signal scanning, rework nudge | Detection of scope-bloat and rework signals |
| `commands/*.md` | Phase slash-command definitions | The user-facing pipeline protocol |
| `agents/*.md` | Role and lens agent definitions | Agent instructions and hard boundary statements |
| `governance/` | Routing policy, guardrails, strategies, signals | The machine-readable governance files that the CLI runs |
| `architecture/` (this tree) | Compass's own architectural record | The ADRs, narrative files, and invariants that describe the framework itself |
| `templates/` | Worked examples for adopters | The template shapes adopters copy; not consumed by the CLI |

---

## Must own — per component

### Pipeline (commands/ + phases)

**Must own:**
- The authoritative definition of what each phase produces (the phase-artifact
  contract).
- The gate set for each route (as computed by the router and encoded in
  `task.yml.gates`).
- The Definition of Ready (Clarify → Plan gate) and Definition of Done
  (Verify → Land gate).

### Router (governance/routing-policy.yml + `compass route evaluate`)

**Must own:**
- The deterministic computation of route, phase weights, and gate set from
  the four context-dimension readings.
- The routing guardrail logic (floors, caps, immovable gates).
- The `routing-policy.yml` schema and its validation.

### Guardrails (governance/guardrails.yml + `compass check`)

**Must own:**
- The five hard guardrail definitions (G1–G5) and their check logic.
- The typed gate evidence schema (`{type, path}` — not bare paths).
- The mechanical pass/fail determination for each gate.

### Strategies (governance/strategies.md + hooks/pre-tool.sh)

**Must own:**
- The BDD strategy (G/W/T as spec and acceptance check).
- The TDD strategy (red → green → refactor cycle and `.red` marker protocol).
- The route-awareness of strategy enforcement (the Spike route suspends TDD;
  other delivery routes do not).

### Role Pipeline (agents/*.md + commands/roundtable.md)

**Must own:**
- Each role's entry-point command and the artifact it produces.
- The `architect-lens` agent's annotation protocol (`architecture-notes.md`
  with five headed sections, no Given/When/Then).
- The lens-first / planner-second order of operations.

---

## Must not do — boundary rules (citing B-Risk references from Inv-1..Inv-8)

The following rules are the boundary risks identified in the prior task's
`architecture-notes.md` (B-Risk 1..6 and the invariants they protect).
They are the most likely places where a future change could violate an
invariant.

### calibration must not mutate task.yml

`compass calibration` is read-only over all task spines. It aggregates reframe
data to produce a calibration report but never writes back to any
`.compass/work/*/task.yml`. Mutation would violate **Inv-4** (Flow advises,
never gates) and **B-Risk 5** (calibration reframe-debt mutating task.yml).

### rework-scan must not exit non-zero on detection

`compass rework-scan` exits 0 whether or not rework signals are detected.
Detection is advisory — it writes a report to `.compass/flow/rework-<date>.md`
and continues. Exiting non-zero would make rework-scan a blocking gate,
violating **Inv-4** and **B-Risk 3** (rework-scan blocking on detection).

### architect-lens must not emit Gherkin scenarios

`architecture-notes.md` contains annotations, candidate ADR titles, and
boundary-risk flags. It never contains Given/When/Then scenarios. Scenarios live
in `spec.feature.md` exclusively. Emitting scenarios from the lens would violate
**Inv-5** (one spec, many lenses) and **B-Risk 2** (architect-lens producing
scenarios).

### No mechanism may write into task.yml.readings

`task.yml.readings` is the sole field the human fills with judgement (blast
radius, terrain, magnitude, intent, role, touches). Every mechanism-produced
load record (`architecture-loaded.yml`, `architecture-notes.md`, `evidence/`,
etc.) lives in its own named file outside `task.yml.readings`. Violating this
would cross **Inv-1** and **B-Risk 1** (loading architecture content into
readings).

### The guardrail count stays at five (G1–G5)

No new guardrail may be added without a deliberate framework change. Mechanisms
that extend gate checks (typed DoD, architectural-integrity checks) register as
CHECK\_FN entries under an existing guardrail (typically G4), not as new G-N
entries. This protects **Inv-2** (five guardrails) and guards against **B-Risk 4**
(a DoD check piggy-backing on G1 rather than G4).

### No mechanism may hard-code governance/signals.yml content

`hooks/stop.sh` and `compass rework-scan` must read `governance/signals.yml` at
runtime, not replicate its patterns in Python or shell code. Hard-coding the
patterns defeats the Q9 extensibility design and violates **Inv-7**
(deterministic mechanism — the CLI must read the file) and **B-Risk 6**
(hand-writing signals.yml patterns into the CLI).

---

## Cross-component dependency rules

A change that affects any of the following cross-component pairs must trigger
an architect-lens consultation (via `/compass:roundtable architect-lens`) or
explicitly note why the consultation is not needed:

| Caller component | Callee component | Risk |
|---|---|---|
| Any agent (`agents/*.md`) | `spec.feature.md` | Agents must not write scenarios; annotation only |
| `compass route evaluate` | `governance/routing-policy.yml` | Schema changes require a routing-policy ADR |
| `compass check` | `governance/guardrails.yml` | Adding a check requires a guardrail-count check |
| `hooks/pre-tool.sh` | `.compass/work/<task>/.red` | Any change to the marker protocol requires updating both sides |
| `frame_load_architecture` | `architecture/decisions/ADR-*.md` | ADR parsing logic change requires TRC-X1/X2 regression tests |
