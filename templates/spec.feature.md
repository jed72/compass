<!--
TEMPLATE: spec.feature.md
Produced by: the Specify phase (`/compass:specify`); refined in Clarify.
Lives at:    .compass/work/<task-slug>/spec.feature.md
Role in the pipeline: THE shared artifact. One spec, many lenses. This is
the single file every role reads - each through their own lens - and it is
read twice: as the specification (Specify) and as the acceptance check
(Verify). It satisfies guardrail G2 (acceptance defined before it is built)
via the BDD strategy (S1): no code may exist that no scenario here describes.

Scenarios are grouped by independence - that grouping seeds the
distribution map in Plan. Every scenario carries a traceability id and a
link back to the intent it serves - that is guardrail G3 (traceability holds).

Fill every {{PLACEHOLDER}}. Keep the Gherkin clean: one behaviour per
scenario, concrete Given/When/Then, no implementation detail.
-->

# Spec - {{TASK_SLUG}}

> **Phase:** Specify · **Last updated:** {{DATE}} · **Owning agent:** spec-author
> **Terrain:** {{greenfield discovery \| brownfield blueprint-distillation then new scenarios}}

## How each role reads this file

<!-- Do not edit this block - it is the same on every spec. It is here so
     any role opening the file knows it is theirs too. -->

- **Product owner / manager** - reads for *intent fidelity*: do these scenarios deliver the outcome in `brief.md`?
- **Product marketer** - reads for *claims*: every line of launch copy must point at a scenario id here.
- **Engineer** - reads for *tests*: scenarios are the acceptance suite and seed the TDD red→green cycle.
- **QA** - reads for *coverage*: which scenarios are exercised, which edges are not.
- **Designer** - UI behaviour authored in `ui-contract.md` flows in here as scenarios.

---

## Intent links

<!-- The "→ intent" end of the traceability chain. Each id below is
     referenced by scenarios in the groups that follow. -->

| Intent id | Source | Statement |
|---|---|---|
| INT-1 | {{brief.md desired outcome \| ui-contract.md \| the task description}} | {{one line}} |
| INT-2 | {{…}} | {{…}} |

---

## Scenario group A - {{NAME, e.g. "Export generation"}}

<!-- A group is a set of scenarios that touch disjoint code/surface from the
     other groups. Independent groups can become parallel streams in the
     distribution map. If everything is one group, that is fine - say so. -->

**Independence note:** {{what makes this group separable from the others - or "single group, no parallelism expected"}}

### Scenario: {{SCENARIO TITLE}}
<!-- traceability id: TRC-A1 · serves: INT-1 -->

```gherkin
Scenario: {{scenario title}}
  Given {{the starting context}}
  When {{the action or event}}
  Then {{the observable outcome}}
  And {{any further observable outcome}}
```

### Scenario: {{SCENARIO TITLE - a realistic edge}}
<!-- traceability id: TRC-A2 · serves: INT-1 -->

```gherkin
Scenario: {{scenario title}}
  Given {{…}}
  When {{…}}
  Then {{…}}
```

---

## Scenario group B - {{NAME}}

**Independence note:** {{…}}

### Scenario: {{SCENARIO TITLE}}
<!-- traceability id: TRC-B1 · serves: INT-2 -->

```gherkin
Scenario: {{scenario title}}
  Given {{…}}
  When {{…}}
  Then {{…}}
```

---

## Failure-mode scenarios

<!-- The failure modes that matter, per the route's test-surface target.
     Express: the obvious edges only. Standard+: the failure modes that
     matter. Critical blast radius: adversarial and boundary inputs too. -->

### Scenario: {{FAILURE MODE TITLE}}
<!-- traceability id: TRC-F1 · serves: INT-1 -->

```gherkin
Scenario: {{scenario title}}
  Given {{…}}
  When {{the thing that goes wrong}}
  Then {{the system's correct, safe response}}
```

---

## Coverage ledger

<!-- Maintained continuously, not at the end. QA reads this at Verify. -->

| Traceability id | Serves intent | Has a failing test (Build) | Passes as acceptance (Verify) |
|---|---|---|---|
| TRC-A1 | INT-1 | {{[ ] / [x]}} | {{[ ] / [x]}} |
| TRC-A2 | INT-1 | {{[ ]}} | {{[ ]}} |
| TRC-B1 | INT-2 | {{[ ]}} | {{[ ]}} |
| TRC-F1 | INT-1 | {{[ ]}} | {{[ ]}} |
