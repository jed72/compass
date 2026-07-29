# Route - hypothetical-framework-task (fixture)

> This is a minimal fixture for TRC-C3 testing. It represents a hypothetical
> framework task that touches the public-api surface, which should trigger
> architect-lens consultation citing Compass's own ADRs.

## 1. The four dimension readings

| Dimension | Reading | Justification |
|---|---|---|
| **Blast radius** | cross-cutting | Changes to the public API affect all callers |
| **Terrain** | brownfield-mapped | The public API shape is documented |
| **Magnitude** | standard | Moderate scope of change |
| **Intent & role** | engineer · delivery | Feature delivery |

**Domain tags (`touches:`):** public-api
