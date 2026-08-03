<!--
TEMPLATE: clarifications.md
Produced by: the Clarify phase (`/compass:clarify`).
Lives at:    .compass/work/<task-slug>/clarifications.md
Role in the pipeline: the ambiguity ledger. Clarify QAs the spec against
itself and against governance; every ambiguity found, every question
asked, and every resolution is recorded here. Collapsed on Express when
the spec is a single Needle-certified-unambiguous scenario (and no routing
guardrail requires Clarify), and on Hotfix where the reproduction is the
clarification. Skipped entirely on Spike - the behaviour is the unknown,
so there is nothing to QA. On Standard+ this file always exists.

Fill every {{PLACEHOLDER}}. Each entry is a closed loop: question →
resolution → who decided → what it changed.
-->

# Clarifications - {{TASK_SLUG}}

> **Phase:** Clarify · **Date:** {{DATE}} · **Owning agent:** spec-author
> **Clarify weight (from route.md):** {{light pass \| full pass}}

---

## Self-QA of the spec

<!-- Did the spec contradict itself? Are there scenarios with no observable
     Then? Untestable language? Record what the QA pass of spec.feature.md
     against itself turned up. -->

- {{finding - or "spec is internally consistent; no self-contradictions found"}}

## Governance QA of the spec

<!-- Does any scenario cross a guardrail (governance/guardrails.md) or run
     against a strategy (governance/strategies.md), or push a non-goal from
     brief.md? Cite the guardrail or strategy. -->

- {{finding with governance reference - or "no governance conflict found"}}

---

## Ambiguity ledger

<!-- One entry per ambiguity. An open entry blocks the Plan phase - Clarify
     does not hand a question downstream. -->

### Q1 - {{SHORT TITLE}}

- **Question:** {{the ambiguity, stated precisely}}
- **Resolution:** {{the decision made}}
- **Decided by:** {{NAME / role}}
- **Governance reference:** {{e.g. "product strategy: depth for existing users" - or "n/a"}}
- **Spec change:** {{which scenario id in spec.feature.md was added/edited/removed - or "no spec change, clarification only"}}
- **Status:** {{resolved \| open (blocks Plan)}}

### Q2 - {{SHORT TITLE}}

- **Question:** {{…}}
- **Resolution:** {{…}}
- **Decided by:** {{…}}
- **Governance reference:** {{…}}
- **Spec change:** {{…}}
- **Status:** {{resolved \| open}}

<!-- Add Q3, Q4, … as needed. -->

---

## Gate

- [ ] No ambiguity left `open` - every entry is `resolved`.
- [ ] `spec.feature.md` updated to reflect every resolution.
- [ ] Non-engineering roles in play have reviewed (Expedition: required at this phase).

### Definition of Ready

<!-- The crisp check that the spec is ready to LEAVE Clarify and enter Plan.
     If any box is unchecked, Plan does not start. This is the entry gate;
     the Definition of Done in verification-report.md is the exit gate. -->

- [ ] **Summary is filled** - `spec.feature.md` opens with a Summary whose
      three fields (Goal, Approach, Why now / what changes) are written, not
      left as template placeholders. This is where the requirement is enforced:
      the CLI never inspects the spec's prose, so an empty Summary is caught
      here or not at all.
- [ ] **Problem traces up** - the spec serves the Problem and Desired outcome
      in `brief.md` (or the Frame request, if no brief). No scenario is
      orphaned from intent.
- [ ] **Behaviour is Given/When/Then** - every scenario has an observable
      `Then`. No scenario is a wish.
- [ ] **Traceability ids assigned** - every scenario has a TRC-id so code and
      claims can point back to it.
- [ ] **Affected surface named** - the spec or `route.md` identifies what code
      and which components this touches.
- [ ] **No open questions** - the ambiguity ledger above is fully resolved.
- [ ] **Route still fits** - nothing found in Clarify makes `route.md` wrong;
      if it does, re-frame before Plan.

Next phase: **Plan** (`/compass:plan`).
