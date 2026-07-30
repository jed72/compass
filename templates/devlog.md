<!--
TEMPLATE: devlog.md
Produced by: opened at Frame, appended to at every phase transition and
             notable event, closed at Land. Hooks write to it too -
             `hooks/post-tool.sh` appends entries after code edits.
Lives at:    .compass/work/<task-slug>/devlog.md
Role in the pipeline: the append-only running log. Persistence over
conversation - if it isn't on disk, it didn't happen. A later session, or
a different agent, reconstructs the task's history from this file plus
route.md.

APPEND-ONLY. Never edit or delete a past entry. Newest entries go at the
bottom. One entry per phase transition or notable event. Keep each entry
short - what happened, evidence pointer, what's next.
-->

# Devlog - {{TASK_SLUG}}

> **Task:** {{ONE-LINE DESCRIPTION}} · **Opened:** {{DATE}}
> Append-only. Newest at the bottom.

---

## {{YYYY-MM-DD HH:MM}} - Frame

- **Event:** Needle ran; route computed.
- **Route:** {{reference route - Express/Standard/Expedition/Hotfix/Spike}} - see `route.md` revision {{N}}.
- **Readings:** blast radius {{…}}, terrain {{…}}, magnitude {{…}}, intent & role {{…}}.
- **Routing guardrails fired:** {{list - or "none"}}.
- **Owed backfills:** {{list - or "none" (a Spike owes none)}}.
- **Next:** Specify {{or Explore on a Spike route}}.

## {{YYYY-MM-DD HH:MM}} - Specify

- **Event:** {{scenarios authored \| brownfield behaviour distilled then new scenarios authored}}.
- **Artifact:** `spec.feature.md` - {{N}} scenarios in {{M}} groups.
- **Next:** {{Clarify \| Plan if Clarify collapsed}}.

## {{YYYY-MM-DD HH:MM}} - {{Clarify | Plan | Distribute | Build | Verify}}

- **Event:** {{what happened}}.
- **Artifact:** {{which file written/updated}}.
- **Evidence:** {{pointer to pasted output, e.g. "test run in verification-report.md §2"}}.
- **Next:** {{next phase}}.

<!-- Notable-event entries (not phase transitions) look like this: -->
## {{YYYY-MM-DD HH:MM}} - note: {{SHORT TITLE}}

- **Event:** {{e.g. "re-frame triggered - Build revealed magnitude was small, not atomic"}}.
- **Detail:** {{what changed and why}}.

<!-- Hook-written entries (post-tool.sh) look like this: -->
## {{YYYY-MM-DD HH:MM}} - edit: {{path/to/file}}

- **Tool:** {{Edit \| Write}} · **Red marker:** {{present \| cleared - tests now pass}}.

## {{YYYY-MM-DD HH:MM}} - Land

- **Event:** task closed.
- **What landed:** {{summary}}.
- **How verified:** {{pointer to verification-report.md gate decision}}.
- **Backfills paid:** {{list - for Hotfix, the root-cause line goes here}}.
- **Follow-ups filed:** {{task ids - or "none"}}.
