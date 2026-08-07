# Golden-quote fabrication eval — results

Input: `/tmp/claude-1000/-home-richardwoollcott-Projects-appmilla-github-study-tutor/2507fe29-6014-421a-bcb1-b35da7fa7860/scratchpad/smoke_results.jsonl`

**Frozen bar (pre-registered):** fabrication rate < 5% (Phase A) / < 1% (Phase B). Re-run on every Player-model change and every corpus ingest.

| text | items | quotes | fabricated | fabrication rate | citation coverage | strips | false-corr flags | verifier exc | verdict |
|---|---|---|---|---|---|---|---|---|---|
| macbeth | 4 | 4 | 1 | 25.0% | 0.0% | 2 | 1 | 0 | FAIL |
| **overall** | 4 | 4 | 1 | 25.0% | 0.0% | 2 | 1 | 0 | FAIL |

Fabrication-flagged items: `qf-macbeth-unsex`

_Citation coverage 0% is the shipped store's honest state: 581/581 chunks are anchorless (2026-05-10 docling ingest); verified quotes render uncited until Track B restores anchors._
