# Devlog - pdf-export-library-viability

> **Task:** Is `weasyprint` a viable PDF engine for our report layouts? Timeboxed spike. · **Opened:** 2026-05-12
> Append-only. Newest at the bottom.

<!-- On a Spike, this devlog carries more weight than usual: there is no
     verification-report.md, no plan.md. The Conclude gate's evidence IS the
     conclusion entry below. A Spike that never reaches a written conclusion
     has not used the route - it has just avoided the framework. -->

---

## 2026-05-12 09:30 - Frame

- **Event:** Needle ran; route computed. `.spike` marker written - the pre-tool hook will suspend the TDD strategy.
- **Route:** Spike - see `route.md` revision 1. Selected by `intent: exploration` (RS-SHAPE-001).
- **Readings:** blast radius contained, terrain greenfield, magnitude small, intent & role engineer/exploration.
- **Routing guardrails fired:** none. (RG-FLOOR-003 did not fire - `touches:` is empty; that is what keeps Spike legitimately available here.)
- **Owed backfills:** none - a Spike owes nothing, it lands nothing.
- **Next:** Explore (Specify, Clarify, Plan all collapsed/skipped per the route).

## 2026-05-12 10:00 - Explore - begin

- **Event:** Explore phase started. Scratch branch `spike/pdf-export-weasyprint` created - NOT to be merged. TDD strategy suspended; writing rendering code freely to answer the question.
- **Detail:** Plan: render the three layout-demanding templates (financial summary, multi-page audit log, chart-heavy dashboard), eyeball fidelity against the HTML originals, measure render time and peak memory. Timebox: 2 days.

## 2026-05-13 14:00 - Explore - findings so far

- **Event:** All three templates rendered. Notes:
  - *Financial summary* - clean. Fidelity essentially perfect; tables, fonts, page breaks all correct. ~180ms, ~40MB peak.
  - *Multi-page audit log* - good. Repeating headers and page numbering work via CSS paged-media. ~600ms for 30 pages, ~70MB peak.
  - *Chart-heavy dashboard* - **the catch.** `weasyprint` does not run JavaScript, so our Chart.js charts render as blank boxes. They have to be pre-rendered to static SVG/PNG server-side before the HTML reaches `weasyprint`.
- **Detail:** The chart limitation is real but not fatal - we already have a server-side chart-rendering path for email reports that emits SVG. Reusing it is plausible, not a rewrite.

## 2026-05-13 16:30 - Conclude  ← the Conclude gate (spike.conclude)

- **Event:** The question is answered. **Conclusion: VIABLE WITH CAVEATS.**
- **Answer to the framed question:**
  - `weasyprint` is viable for our report PDF export. Fidelity on text-and-table
    layouts is excellent; CSS paged-media handles multi-page correctly.
  - **Caveat 1 - no JS:** charts must be pre-rendered to static SVG before
    `weasyprint` sees the HTML. The existing email-report SVG path can supply
    this; budget that integration into the real feature, do not assume charts
    "just work".
  - **Caveat 2 - speed:** ~20ms/page is fine for on-demand single reports;
    a future bulk-export feature would want a job queue, not a synchronous
    request. Not a v1 concern, but a known edge.
  - **Numbers:** 180ms–600ms render, 40–70MB peak memory across the three
    templates. Well within a request budget for single-report export.
  - A heavier headless-browser engine is **not** needed for the report
    layouts we have. Revisit only if a future template genuinely needs live JS.
- **Gate:** `spike.conclude` - PASS. The question is answered, the answer is
  written down (this entry). That is the whole Spike gate.
- **Next:** the graduate-or-discard decision.

## 2026-05-13 16:45 - Land - graduate

- **Event:** task closed. **Decision: GRADUATE.**
- **What happens to the code:** the scratch branch `spike/pdf-export-weasyprint`
  is **not merged.** Nothing lands from a Spike. The three render scripts stay
  on the branch as *reference inputs* to the next Frame - good inputs, because
  the terrain is now mapped.
- **Graduation:** a fresh `/compass:triage` has been run for the real delivery
  work - task `report-pdf-export`. That Frame inherits this spike's `route.md`,
  this conclusion, and the reference code. The new task will compose to a real
  route (likely Standard) where guardrails G1–G3 apply in full: the PDF export
  code will be written under TDD with real scenarios before anything lands. The
  chart-pre-rendering caveat is carried into that task's brief as a known
  constraint.
- **This spike's status:** graduated → task `report-pdf-export`. Closed.
- **Note on `compass check`:** running `compass check` against this task reports
  G1/G2 FAILs - no tested scenarios, no `green.json`. That is correct and
  expected: `compass check` asks "is this a landable delivery task?" and a
  Spike is honestly not one. A Spike passes its one Conclude gate (above), not
  the delivery guardrail set. The guardrails are not skipped - they moved with
  the code to `report-pdf-export`, where they apply in full.
