---
description: Retired name for /compass:design - a redirect stub, removed at the next major version
argument-hint: "<the arguments you meant for /compass:design>"
allowed-tools: Read
---

# /compass:wireframe (retired)

This command is now **`/compass:design`**. Run that instead, with the same
arguments.

It is kept as a pointer rather than removed so a session or a script that
still names the old command gets told where it went, rather than an unknown-command
error. `governance/terminology.yml` records the rename; ADR-014 removes this
stub at the next major version.

Do not do the work here. Tell the invoker the command's new name and stop.
