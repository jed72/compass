# Delivery approach - hypothetical-framework-task (fixture)

> No test reads this directory (checked by grep over tests/, cli/, scripts/
> and hooks/). It represents a hypothetical framework issue that touches the
> public-api surface, which would trigger architect consultation citing
> Compass's own ADRs, if anything read it.

## 1. The assessment

| Dimension | Value | Justification |
|---|---|---|
| **Risk** | cross-cutting | Changes to the public API affect all callers |
| **Familiarity** | brownfield-mapped | The public API shape is documented |
| **Size** | standard | Moderate scope of change |
| **Goal & role** | delivery · engineer | Feature delivery |

**Labels (`labels:`):** public-api
