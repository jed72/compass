---
description: Retired - use /compass:consult
argument-hint: "<arguments for /compass:consult>"
allowed-tools: Read
---

# /compass:roundtable (retired)

This command is now **`/compass:consult`**. Run that instead, with the same
arguments.

The new name is the word Anthropic's platform documentation uses for the same
act: an advisor agent is one the coordinator "consults mid-turn". `roundtable`
was a Compass-only metaphor for it, and a reader had to be taught what it
meant.

It is kept as a pointer rather than removed so a session or a script that still
names the old command gets told where it went, rather than an unknown-command
error. `governance/terminology.yml` records the rename, ADR-023 records why,
and ADR-014 removes this stub at the next major version.

Do not do the work here. Tell the invoker the command's new name and stop.
