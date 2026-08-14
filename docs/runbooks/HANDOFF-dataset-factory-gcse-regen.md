# HANDOFF — the GCSE dataset regeneration lane (agentic-dataset-factory)

**Date:** 2026-08-14 · **From:** the spark master session · **For:** whichever session
runs the factory lane (the repo is `/home/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory`,
clean on `main`, no GCSE work active — the hot lanes there are coach-agent/recruiter-agent;
this brief is scoped not to collide with them).
**Feeds:** study-tutor plan-of-record **Lane 7** (the re-train). **Why now:** the
2026-08-13 three-instrument eval proved the current self-distilled dataset HURT the
fine-tune (autopsy + story:
`fleet-evals/multisubject/docs/STORY-when-your-finetune-loses-2026-08-14.md`).

## Rich's directives (2026-08-14 — binding)

1. **Batch mode in the factory** ("which we have previously discussed").
2. **DeepSeek v4 Flash 0731 as the teacher** ("as we have previously discussed").
3. Plus the eval-derived recipe: fabrication gate on every sample; visible-answer
   pedagogy/AO framing; mixed answer lengths; direct-answers-allowed; eval-in-the-loop
   with the beats-base-on-all-three bar (the training side of that bar lands with the
   fine-tune run itself, not this lane — this lane delivers the machinery + dataset).

## What the recon established (receipts in the factory repo)

- **The live pipeline** is the DeepAgents Player-Coach loop: `agent.py` →
  `entrypoint/generation_loop.py::run_generation_loop()` (sequential per ADR-ARCH-006),
  config via the top-level `agent-config.yaml` (`config/loader.py:35` — no `--config`
  flag), Player/Coach models purely YAML-configured (`config/models.py:37-94`,
  provider local/anthropic/openai + endpoint — no code assumes model names). The legacy
  `synthesis/synthesise.py` path is superseded; its `DuplicateDetector` is NOT wired
  into the live loop.
- **"Batch mode" prior art:** never pipeline machinery. The precedent is the
  qa-verifier lane's serving-posture fork (`domains/qa-verifier/RUNBOOK-qav-generation.md:156-173`):
  **"Batched legs"** (all teacher calls, then all coach calls — one cold-load per seat
  per run) vs **"co-residency"** (a llama-swap matrix set keeping both resident).
  Measured motivation: alternating seats cost 82.3s + 22.5s cold loads PER ROW
  (15–24h run floor); qa-verifier cured it with a co-resident alias
  (`domains/qa-verifier/agent-config.yaml:22-25`). ADR-ARCH-006 explicitly deferred
  batch-parallel to "v2 if throughput becomes a concern" — it now is.
- **The teacher seam already exists as a concept**: qa-verifier reuses the `player:`
  block as a rationale "teacher" role (its `agent-config.yaml:13-19`; the
  injector-is-the-boss pattern). DeepSeek v4 Flash 0731 slots in via config alone.
- **The quote-gate plug point:** `entrypoint/generation_loop.py:1240-1260` — the
  orchestrator choke point between Coach acceptance (`validate_post_generation`) and
  `write_tool.invoke()` at :1263; a rejection there already routes back into the
  revise loop via `coach_feedback`. **Motivating precedent already in the repo:**
  `tasks/backlog/gemma4-moe-deploy/TASK-G4D-006-quote-factuality-eval.md` documents two
  REAL fabricated set-text quotes from GCSE smoke testing ("screw your courage to the
  hope of belief"; a mangled Inspector speech) — cite it; those two become test
  fixtures.
- **Stale things this lane must fix, not inherit:** `domains/gcse-english-tutor/GOAL.md`
  names the wrong target base (Nemotron line — the real fine-tune was Gemma-4-26B-A4B);
  five GOAL variants litter the dir; `sources/` is empty; the fine-tune recipe's
  RUNBOOK never existed in this repo (the real recipe is recoverable from
  `docs/research/train_gemma4_moe.py` — note max_seq was 4096, lr 2e-4, LoRA 16,
  1 epoch); `docs/deployment/gb10-setup.md` still describes the retired vLLM:8002
  serving — the current convention is llama-swap `:9000`.
- **Three old GCSE output dirs** (`output_backup_pre_rerun/`, `output_backup_run1/`,
  `output_gcse_rerun/`, ~1716-1736 accepted rows each, ~70% accept rate) sit at the
  repo top level — DO NOT touch; Rich rules baseline-vs-archive (his Q below).

## Build order (coach-gated stages; local commits; no pushes without the merge word)

### Stage 1 — batch mode (the machinery, additive)
An explicit, additive batching layer in the live loop — NOT a rewrite:
- A `batch:` config block + `--batch` flag: the driver collects N generation targets,
  runs **all Player/teacher legs** for the window, then **all Coach legs** (batched
  legs at the orchestration level), with per-row state checkpointing so the run is
  resumable mid-window (the existing `--resume` semantics extended, not replaced).
- Optionally emit a recommended llama-swap matrix-set stanza (co-residency) in the
  runbook rather than config-editing llama-swap from this repo (serving edits are
  operator acts).
- Sequential mode stays the default — active lanes (coach/recruiter) must be entirely
  unaffected; their configs untouched.
- A dated note onto ADR-ARCH-006 recording that its named v2 revisit condition has
  arrived and what shipped.
- Hermetic tests: window collection, leg ordering, checkpoint/resume, sequential-mode
  regression. *Gate: full factory test suite green + a dry batched run against a mock
  endpoint.*

### Stage 2 — the fabrication gate (per-sample quote verification)
- New module (e.g. `src/gates/quote_gate.py`): extract quoted spans from each
  ACCEPTED sample's assistant turns (double quotes + block quotes + the `/` verse
  convention — lift the extraction/metric approach from fleet-evals
  `multisubject/harness/... run_fabrication_eval.py`, windowed similarity ≥0.95),
  verify against the real subject corpora (read-only sqlite `immutable=1` on the
  study-tutor store, or a corpus-snapshot the runbook pins — never a live service).
- Plug in at `generation_loop.py:1240-1260`: a failed sample routes to the revise loop
  with the fabricated span named in `coach_feedback` (the same pattern as the existing
  validation failure), with a per-run gate report (checked/passed/revised/dropped).
- Also wire the orphaned `DuplicateDetector` into the live path while at that choke
  point (it exists, tested, unwired — cheap win; keep it behind config).
- Tests: the two TASK-G4D-006 real fabrications as fixtures (must be caught), a
  verbatim quote (must pass), the store-absent edge (analysis-mode sample: no quotes,
  passes). *Gate: suite green + gate report on a replayed sample set.*

### Stage 3 — the GCSE domain refresh
- Rewrite `domains/gcse-english-tutor/GOAL.md` (9-section format enforced by
  `domain_config/parser.py:142-159`) to the current truth: target = the Lane 7
  candidate (updated Gemma 4 base; Qwen 3.6 rides the bake-off), **teacher =
  DeepSeek v4 Flash 0731 in the `player:` seat**, and the style targets from the
  autopsy: pedagogy/AO framing IN THE VISIBLE ANSWER (think-blocks may exist but the
  visible answer must stand alone), mixed full-scaffold and conversational lengths,
  direct questions answered directly, set-text factual reinforcement, NO AQA
  assessment material (law 4 inherited).
- Clean the GOAL variant litter (archive to a dated subdir, don't delete).
- `agent-config.gcse.yaml` (domain-local, per the qa-verifier pattern) with the
  DeepSeek teacher block + llama-swap `:9000` convention; the stale vLLM:8002 doc gets
  a dated correction note.
- *Gate: parser accepts the GOAL; config loads; a 3-target smoke generation runs
  end-to-end through batch mode + the gate (teacher serving permitting — see
  preconditions).*

### Stage 4 — the pilot batch (attended)
- A small pre-registered pilot (e.g. 50 targets) through the full path: batched legs →
  Coach → fabrication gate → dataset. Report: accept rate, gate catches, sample
  quality vs the old corpus (spot-read), throughput vs the qa-verifier baseline.
- *Gate: Rich reads the pilot report and gives the full-run word. The full ~2,500-target
  run and the fine-tune itself are the NEXT lane (training venue + eval-in-the-loop),
  not this one.*

## Preconditions and Rich's asks (kept short)

1. **Where does DeepSeek v4 Flash 0731 serve?** The prior framing was the 2×Spark
   standup (in prospect). The GB10 is busy with product-owner work; the spark serves
   the live tutor. Options: the 2×Spark when stood up / a temporary seat somewhere
   Rich names / a hosted API (would be paid frontier usage — only on an explicitly
   priced word, per the Judge-B precedent). **The lane can build Stages 1–2 fully and
   Stage 3 except the smoke without the teacher being live.**
2. **The three old GCSE output dirs:** reference baselines to diff against, or archive?
3. Spec word on this brief; pilot gate tap at Stage 4; merge word at the end.

## Fences (standing)

Broker isolation (no NATS anywhere); study-tutor + fleet-evals are READ-ONLY sources
(lift code patterns, never couple imports across repos); no llama-swap/serving edits
(emit runbook stanzas instead); the coach-agent/recruiter-agent lanes' domains and the
old output dirs untouched; law 4 absolute in the GOAL and in generated content;
sequential mode's behaviour byte-compatible for existing domains.
