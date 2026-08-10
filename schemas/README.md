# Schemas

Schemas for the three machine-readable Compass files. Each one comes in two
forms:

| File | Executable schema | Readable companion |
|---|---|---|
| `governance/routing-policy.yml` | `routing-policy.schema.json` | `routing-policy.reference.yml` |
| `governance/guardrails.yml` | `guardrails.schema.json` | `guardrails.reference.yml` |
| `.compass/work/<task>/task.yml` | `task.schema.json` | `task.reference.yml` |

**The `.schema.json` files are real, executable JSON Schema** (draft-07) and
are the authority for structure. **The `.reference.yml` files are the
human-readable companions** - JSON Schema is precise but hard to read at a
glance, so each field is also documented in a plain annotated YAML file. Where
the two could be read to differ, the `.schema.json` wins.

## How validation works

`compass policy lint` and `compass task lint` validate in two layers:

1. **The built-in structural linter - always runs.** No dependencies. It is
   the floor, and it does the one thing JSON Schema *cannot*: cross-check that
   every guardrail's declared `checks` is actually implemented in the CLI's
   `CHECK_FNS`. A declared check with no implementation is the integrity hole
   the linter exists to close - see `governance/guardrails.md`.
2. **JSON Schema validation - runs when `jsonschema` is installed.** Fuller
   structural coverage (required keys, enums, nested shapes) against the
   `.schema.json` files. `jsonschema` is an *optional* dependency Compass does
   not bundle; PyYAML, the CLI's one hard dependency, travels inside the
   plugin (`cli/vendor/yaml/`) instead. If `jsonschema` is absent, the lint
   commands say so and run on the built-in linter alone.

So: `pip install jsonschema` for the full check; the CLI is still useful and
honest without it.

If you extend a policy file, keep it consistent with both forms and re-run the
linter.
