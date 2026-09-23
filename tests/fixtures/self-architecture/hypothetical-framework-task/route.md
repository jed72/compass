# Delivery approach - hypothetical-framework-task (fixture)

> `tests/test_writing_style.py` reads this file - its directory name is
> exempted there as the real, on-disk path, not a retired-vocabulary use of
> the word. It represents a hypothetical framework issue that touches the
> public-api surface, which would trigger architect consultation citing
> Compass's own ADRs, if a scenario ran against it.

## 1. The assessment

| Dimension | Value | Justification |
|---|---|---|
| **Risk** | cross-cutting | Changes to the public API affect all callers |
| **Familiarity** | brownfield-mapped | The public API shape is documented |
| **Size** | standard | Moderate scope of change |
| **Goal & role** | delivery · engineer | Feature delivery |

**Labels (`labels:`):** public-api
