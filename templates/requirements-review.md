<!--
TEMPLATE: requirements-review.md
Produced by: the requirements-review stage (`/compass:refine`).
Lives at:    .compass/work/<issue-slug>/requirements-review.md
Role in the pipeline: the ambiguity ledger. The review QAs the criteria
against themselves and against governance; every ambiguity found, every
question asked, and every resolution is recorded here. Collapsed on a
quick fix when the criteria are a single scenario certified unambiguous
at triage (and no policy rule requires the review), and on a hotfix where
the reproduction is the
clarification. Skipped entirely on Spike - the behaviour is the unknown,
so there is nothing to QA. On Standard+ this file always exists.

Fill every {{PLACEHOLDER}}. Each entry is a closed loop: question →
resolution → who decided → what it changed.
-->

# Clarifications - {{ISSUE_SLUG}}

> **Phase:** refine · **Date:** {{DATE}} · **Owning agent:** spec-author
> **Requirements review weight (from delivery-approach.md):** {{light pass \| full pass}}

---

## Self-QA of the spec

<!-- Did the spec contradict itself? Are there scenarios with no observable
     Then? Untestable language? Record what the QA pass of acceptance-criteria.md
     against itself turned up. -->

- {{finding - or "spec is internally consistent; no self-contradictions found"}}

## Governance QA of the spec

<!-- Does any scenario cross a guardrail (governance/guardrails.md) or run
     against a strategy (governance/strategies.md), or push a non-goal from
     intent.md? Cite the guardrail or strategy. -->

- {{finding with governance reference - or "no governance conflict found"}}

---

## Ambiguity ledger

<!-- One entry per ambiguity. An open entry blocks the Plan phase - refine
     does not hand a question downstream. -->

### Q1 - {{SHORT TITLE}}

- **Question:** {{the ambiguity, stated precisely}}
- **Resolution:** {{the decision made}}
- **Decided by:** {{NAME / role}}
- **Governance reference:** {{e.g. "product strategy: depth for existing users" - or "n/a"}}
- **Spec change:** {{which scenario id in acceptance-criteria.md was added/edited/removed - or "no spec change, clarification only"}}
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

## Worked example

A decision recorded in the target register, not as a label stack - see
`skills/compass-runtime/writing-voice-worked-example.md` for a full
requirements review rewritten this way. One entry, in the same continuous
prose every entry above should aim for:

> The receipt's line cap was unclear - a defensible default, or something a
> project should be able to configure? jed72 kept it fixed at fifty lines, a
> hundred columns wide: a standard terminal shows that much without
> scrolling, and a receipt that cannot fit needs a less verbose renderer, not
> a knob.

That one paragraph carries what was unclear, the call, whose call it was,
and what the call rests on - the same four things each `{{PLACEHOLDER}}`
entry above owes, said as a colleague would say them rather than filled into
a form.

---

## Gate

- [ ] No ambiguity left `open` - every entry is `resolved`.
- [ ] `acceptance-criteria.md` updated to reflect every resolution.
- [ ] Non-engineering roles in play have reviewed (initiative-scale work: required at this stage).

### Definition of Ready

<!-- The crisp check that the spec is ready to LEAVE refine and enter Plan.
     If any box is unchecked, Plan does not start. This is the entry gate;
     the Definition of Done in verification-report.md is the exit gate. -->

- [ ] **Summary is filled** - `acceptance-criteria.md` opens with a Summary whose
      three fields (Goal, Approach, Why now / what changes) are written, not
      left as template placeholders. This is where the requirement is enforced:
      the CLI never inspects the spec's prose, so an empty Summary is caught
      here or not at all.
- [ ] **Problem traces up** - the spec serves the Problem and Desired outcome
      in `intent.md` (or the triage request, if no brief). No scenario is
      orphaned from intent.
- [ ] **Behaviour is Given/When/Then** - every scenario has an observable
      `Then`. No scenario is a wish.
- [ ] **Traceability ids assigned** - every scenario has a TRC-id so code and
      claims can point back to it.
- [ ] **Affected surface named** - the spec or `delivery-approach.md` identifies what code
      and which components this touches.
- [ ] **No open questions** - the ambiguity ledger above is fully resolved.
- [ ] **Route still fits** - nothing found in refine makes `delivery-approach.md` wrong;
      if it does, re-frame before Plan.

Next stage: **plan** (`/compass:plan`).
