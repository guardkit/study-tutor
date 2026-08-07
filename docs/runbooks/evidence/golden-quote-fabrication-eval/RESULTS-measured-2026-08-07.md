# Golden-quote fabrication eval — results

Input: `docs/runbooks/evidence/golden-quote-fabrication-eval/measured-2026-08-07.jsonl`

**Frozen bar (pre-registered):** fabrication rate < 5% (Phase A) / < 1% (Phase B). Re-run on every Player-model change and every corpus ingest.

| text | items | quotes | fabricated | fabrication rate | citation coverage | strips | false-corr flags | verifier exc | verdict |
|---|---|---|---|---|---|---|---|---|---|
| an_inspector_calls | 8 | 0 | 0 | n/a | n/a | 0 | 0 | 0 | no quotes |
| macbeth | 12 | 1 | 1 | 100.0% | n/a | 1 | 0 | 0 | FAIL |
| power_and_conflict_poems | 9 | 2 | 0 | 0.0% | 0.0% | 0 | 1 | 0 | PASS (Phase B) |
| **overall** | 29 | 3 | 1 | 33.3% | 0.0% | 1 | 1 | 0 | FAIL |

Fabrication-flagged items: `qf-macbeth-unsex`

_Citation coverage 0% is the shipped store's honest state: 581/581 chunks are anchorless (2026-05-10 docling ingest); verified quotes render uncited until Track B restores anchors._

---

## Coordinator postscript (2026-08-07, the per-class read the pre-registration requires)

- **Only 3 quotes in 29 responses.** The Socratic fine-tune rarely emits ≥4-word quotes —
  it asks questions instead (consistent with the 2026-05-18 eval's short-visible-answer
  finding). n=3 is far too small to treat 33.3% as a rate against the frozen 5% bar; the
  FAIL verdict is recorded, not walked back, but the honest next step is **quote-eliciting
  prompts** so the denominator becomes meaningful.
- **The one fabrication is REAL and is the designed bait working:** on `qf-macbeth-unsex`
  (category `fabrication_bait`) the model reproduced its known 2026-04-21 misquote —
  "mortal **coats**" for "mortal **thoughts**" (best ratio 0.49) — and the runtime
  verifier **STRIPPED it** (`no_match_strips=1`): the learner was protected; mission law 3
  held on the measured path. Not a store_gap misread.
- **The Track A fix is visible in the measured run:** `qf-poems-lone-level` returned an
  **anchorless primary match** (verified, uncited, not stripped, no exception) — the exact
  degraded-citation behaviour built today, on the production closure.
- **Store isolation note:** the run used a sha256-verified scratch copy; the working
  tree's `data/chroma/chroma.sqlite3` nonetheless gained 5 rows in chroma's internal
  `acquire_write` bookkeeping table during the day's runs (content proven identical,
  table-by-table). Original bytes restored from the pristine copy; the opener is
  unattributed (suspects: a chromadb-collected hermetic test now that the `[rag]` extra is
  installed, or a second client open in the T2 path) — ledgered in known-issues.
