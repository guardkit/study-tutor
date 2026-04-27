# Phase 0 Build Plan — Hackathon Floor + Parity Hygiene

## For: Weekend build (19–20 April 2026 + continuation through Friday 24 April)
## Date: 17 April 2026 (last updated 27 April 2026)
## Status: **In-flight — weekend code work complete; close-out gates pending. /arch-refine D2 closed 27 Apr (ADR-ARCH-017). Graphiti latency spike DONE 27 Apr — SR-08 elevated to CRITICAL; ARCH-017 sync classification confirmed with massive margin. SR-08 bundled `/arch-refine` DONE 27 Apr — ADR-ARCH-018 promotes SR-08 → CC-13 and SR-09 → CC-14 (six → fourteen parity surfaces); ADR-ARCH-019 broadens async write-back from session-end-only to every Graphiti write point. Both ADRs seeded into `architecture_decisions`.**
## Repo: `guardkit/study-tutor` (or equivalent — currently a near-empty repo at `/Users/richardwoollcott/Projects/appmilla_github/study-tutor`)
## Machine: MacBook Pro M2 Max (primary), GB10 over Tailscale (inference), Synology NAS over Tailscale (FalkorDB, Phase 1 only)
## Target completion: End of Friday 24 April 2026 (close of Week 1 of the 31-day burn)

---

## Current Status — 2026-04-23 (Thursday evening)

**Day-by-day progress against the original schedule:**

| Day | Planned | Actual |
|-----|---------|--------|
| Fri 18 Apr | Prereqs | ✅ Done |
| Sat 19 Apr | FEAT-PO-001 + FEAT-PO-002 kickoff | ✅ Done — GOAL.md drafted, scaffold + MCP server landed (commits `4d6610a`, `2b9ad15`, `94ee157`) |
| Sun 20 Apr | Parity surfaces + FEAT-PO-003 + FEAT-PO-005 | ✅ Done (closed-out 23 Apr evening) — parity surfaces green Sun; FEAT-PO-003 tail landed 23 Apr evening (`domains/gcse-english/sources/README.md`, `docs/licensing.md`, `.gitignore` hardening for PDFs / GGUF / ChromaDB / `train.jsonl` / model artefacts); FEAT-PO-005 `docs/submission/` stubs landed 23 Apr evening (technical-writeup, demo-script, video-outline) |
| Mon 21 Apr | FEAT-PO-004 Bedrock setup | ✅/🟡 Pivot — Bedrock placeholder in `.env.example`; actual S3 upload + import **deferred**. Unplanned work absorbed here instead: FEAT-PO-002 shipped end-to-end (commits `0acda09`, `15d4aa2`), Graphiti LLM switched to vLLM on GB10 (commit `bd74d43`), two post-smoke defects fixed (commits `7a8a3a3`, `14afc08`) |
| Tue 22 Apr | FEAT-PO-004 Bedrock validation | 🔲 Not done — instead, TASK-PO02F-001 scoped RAG grounding for quote fidelity (commit `b3c567f`) |
| Wed 23 Apr | Clean-machine walkthrough | 🔲 Not yet run |
| Thu 24 Apr (today) | Phase 1 prep | 🟡 Partial — unplanned empirical work on OpenWebUI+RAG interim deployment for Lilymay absorbed the evening; research captured in [openwebui-rag-empirical-findings-2026-04-23.md](./openwebui-rag-empirical-findings-2026-04-23.md); Phase 1 scope/build-plan docs still to draft |
| Fri 25 Apr | Buffer / rest | — |

**Feature-level status:**

| Feature | State | Evidence |
|---------|-------|----------|
| FEAT-PO-001 (domain contract) | ✅ Complete | `domains/gcse-english/GOAL.md`, `docs/gamification/` present |
| FEAT-PO-002 (tutoring runtime) | ✅ Complete + hardened | 7/7 core tasks done (`TASK-PO02-001..007`); 2/3 follow-up fixes landed (`TASK-PO02F-002`, `TASK-PO02F-003`); 1 follow-up scoped (`TASK-PO02F-001` — RAG grounding) with empirical validation session completed 23 Apr — see [openwebui-rag-empirical-findings-2026-04-23.md](./openwebui-rag-empirical-findings-2026-04-23.md) |
| FEAT-PO-003 (repo packaging) | ✅ Complete | `README.md`, `LICENSE` (MIT — plan called for Apache 2.0; see `docs/licensing.md §1`), `pyproject.toml`, `AGENTS.md`, `domains/gcse-english/sources/README.md`, `docs/licensing.md` all present; `.gitignore` hardened with study-tutor entries (PDFs under `domains/*/sources/`, `chroma/`, `train.jsonl`, `*.gguf`, `*.safetensors`, `models/`, `adapters/`, `merged-*/`). SR-06 placeholder hygiene passes; pre-commit PDF/GGUF scan clean; `git check-ignore` confirms dummy-PDF drop test |
| FEAT-PO-004 (Bedrock validation) | 🔲 Deferred | `BEDROCK_MODEL_ARN` placeholder in `.env.example`; no S3 upload or Bedrock import executed. Depends on AWS ops evening. |
| FEAT-PO-005 (write-up scaffolding) | ✅ Stubs landed | `docs/submission/technical-writeup.md` (13 section stubs per scope-doc outline), `docs/submission/demo-script.md` (5-scene skeleton, ~3.5min), `docs/submission/video-outline.md` (storyboard-lite + shot list + B-roll checklist) all present. Content populated incrementally through Phases 1–2; target feature-complete 10 May. |

**Smoke-test gate:** The end-of-Saturday gate (TASK-PO02-007) declared GREEN on 2026-04-21 — Phase 0 is functionally submittable on Ollama/GB10 today. The remaining work is Bedrock validation and the clean-machine walkthrough.

**Open punch-list to close Phase 0:**

1. **Clean-machine walkthrough** (originally Wed 23 Apr) — run tonight or Thu evening; fresh-clone reproduces the tutor.
2. ~~**FEAT-PO-005 write-up stubs** — create `docs/submission/{technical-writeup,demo-script,video-outline}.md` shells.~~ ✅ Landed 23 Apr evening. All three stubs present; content filled incrementally through Phases 1–2.
3. ~~**FEAT-PO-003 tail** — `domains/gcse-english/sources/README.md`, `docs/licensing.md`.~~ ✅ Landed 23 Apr evening. Open sub-point: LICENSE is MIT but the plan specified Apache 2.0 — decision deferred until Kaggle IP rules read in full; `docs/licensing.md §1` documents the discrepancy so the swap is one edit when confirmed.
4. **FEAT-PO-004 Bedrock validation** — S3 upload + Custom Model Import + LLM client wiring. Contingency TASK-CDR-005 stands: if eu-west-2 lacks 31B import support, stay on Ollama/GB10 for demo.
5. **TASK-PO02F-001 RAG grounding** — scoped (will likely be promoted to FEAT-PO-006 in Phase 1) and now backed by empirical findings from the 23 Apr OpenWebUI session (R1–R6 recommendations captured in [openwebui-rag-empirical-findings-2026-04-23.md §4](./openwebui-rag-empirical-findings-2026-04-23.md)).
6. **Phase 1 scope + build-plan docs** — `phase-1-scope.md` exists; `phase-1-build-plan.md` exists but needs refresh against Phase 0 actuals and the new FEAT-PO-006 recommendations before next weekend.
7. **`/system-design` Phase 0 run (2026-04-26)** — scoped to the three implemented contexts (Tutoring, Inference Runtime, MCP Transport) plus Shared Kernel B event surface, bias-to-defaults. Knowledge & Curriculum, Student Model, and Gamification are deliberately deferred to per-phase `--focus` re-runs (see GuardKit Command Sequence below) so contracts are seeded into Graphiti only once the relevant runtime code lands. Rationale: P1/P2 contexts are doc-only today; designing now risks drift before implementation.

   **In-session decisions (2026-04-26):**
   - **D1 — Tutoring schema P0-only.** The `TutorSession` data model artefact documents the Phase-0 shape only (`session_id, subject, topic, status, turns, started_at, ended_at`). P1 fields (`student_id`, `grade_target`, `paper`, `aos_scaffolded`, `rag_chunks_used`, `TurnFeedback`, `SessionSummary`) are deferred to a `/system-design --focus="Tutoring"` re-run when P1 wires Graphiti + Coach. Rationale: matches what's true in `src/study_tutor/session/tutor_session.py` today; avoids contract-drift before P1 implementation.
   - **D2 — `tutor_start_session` classified `sync`.** ✅ **CLOSED 2026-04-27 by `/arch-refine` → ADR-ARCH-017** (partially supersedes ADR-ARCH-008 SR-07 classification table). The design artefact classifies `tutor_start_session` as **sync** (returns `session_id` synchronously; warm-up LLM call is opportunistic fire-and-forget, not a polled long-running task). Architecture set, scope/build-plan docs, and the runtime MCP tool description in `src/study_tutor/mcp/server.py` all aligned. Phase 1 reversion path documented and conditional on the Graphiti latency spike (`phase-1-scope.md §"Graphiti latency spike"`): if `search_nodes` median > ~3s for the student-model read at session start, reclassify back to long-running and add the `_status`/`_cancel` companion. Both ADRs seeded into Graphiti `architecture_decisions` group.

8. ~~**Phase 1 prep — Graphiti latency spike** (per `phase-1-scope.md §"Latency spike"`).~~ ✅ **DONE 2026-04-27** via `scripts/graphiti_latency_spike.py`. Three-hop stack measured: FalkorDB on whitestocks (Synology, Tailscale) + vLLM Qwen2.5-14B-FP8 on GB10:8000 (LLM extraction) + nomic-embed-text-v1.5 on GB10:8001 (embeddings). Full results in [graphiti-latency-spike-results.md](./graphiti-latency-spike-results.md).

   **Headline numbers (median over 3 timed runs after warm-up):**
   - `add_episode`: **78.98s** — dominated by LLM extraction; cold-start outlier of 134s on run 1.
   - `search_nodes`: **0.07s** — embedding + cypher only; no LLM call.
   - `search_memory_facts`: **0.08s** — same shape as search_nodes.

   **Decisions unblocked:**
   - **SR-08 (async write-back): CRITICAL, not defensive.** At 79s median per write, a synchronous `add_episode` at session-end would make the student wait over a minute for `tutor_session_end` to return. Pattern per `phase-1-scope.md` L83: fire-and-forget from multiple write points (session-end, misconception-observed during turns, Coach confidence-delta proposals), not a single session-end batch. ✅ **CLOSED 2026-04-27** — bundled `/arch-refine` ran in two passes: (a) ADR-ARCH-018 supersedes ADR-ARCH-009, promoting SR-08 → CC-13 and SR-09 → CC-14 (six → fourteen load-bearing CCs); (b) ADR-ARCH-019 supersedes ADR-ARCH-003, broadening async Graphiti write-back from session-end-only to every Graphiti write point in the tutor (session-end episode, mid-session misconception logs, Coach confidence-delta proposals, planner topic-confidence updates — all fire-and-forget; failures logged-only). Architecture artefacts (ARCHITECTURE.md, container.md, domain-model.md) updated in-place; design / planning artefacts flagged stale in ARCH-019's Downstream artefacts section for `/system-design` and `/feature-spec` to pick up. Both ADRs seeded into Graphiti `architecture_decisions` (live `add_episode` times: ARCH-003-superseded 113s; ARCH-019 153s — empirically reconfirms the 79s median's order of magnitude, in line with CC-13's premise).
   - **ADR-ARCH-017 / SR-07 (sync `tutor_start_session`): CONFIRMED with massive margin.** `search_nodes` at 0.07s is ~40× faster than the 3s reversion threshold in ARCH-017. The Phase-1 student-model read at session start costs ~70ms — completely negligible. No further refinement needed for ARCH-017; the reversion footnote stays as documented insurance against future stack changes.
   - **DEC-02 / DEC-08:** resolved.

   **Note on stack:** the spike measured the post-21-Apr vLLM-on-GB10 stack, not the original Gemini stack the spec assumed. The 1–3s / 5–8s expected ranges in `phase-1-scope.md:75` were calibrated for Gemini API latency; vLLM-on-Tailscale has a different shape (steadier per-call but slower per-token, dominated by 14B-parameter inference time).

**Unplanned strategic move (21 Apr):** Graphiti's LLM backend migrated from Gemini to vLLM on GB10 (`neuralmagic/Qwen2.5-14B-Instruct-FP8-dynamic`) — this is Phase 1 infrastructure landed early, with Ollama fallback kept for MacBook-only mode. Reduces dependency on external APIs ahead of the Phase 1 Graphiti spike.

**Unplanned strategic move (23 Apr):** Interim OpenWebUI + RAG deployment hardened for Lilymay so she can start using the tutor for GCSE revision immediately while the Phase 1/2 deep-agents harness is built. Session produced ten empirical findings and a shippable three-persona configuration (Shakespeare / Modern Texts / General). Materially advances Success Criterion 6 ("Lilymay's experience unchanged or improved") — her experience is improved *today*. Findings validate and extend the pre-existing `rag-grounding-design.md` Phase A plan with six concrete recommendations feeding FEAT-PO-006. Full capture: [openwebui-rag-empirical-findings-2026-04-23.md](./openwebui-rag-empirical-findings-2026-04-23.md). Key headline: for primary texts the fine-tune has memorised (Shakespeare), direct Ollama beats RAG; retrieval must be selective, source-type-aware, and primary-text-inclusive to add value.

---

## What Phase 0 IS

Week 1 of the 31-day build to the Gemma 4 Good Hackathon submission deadline (18 May 2026, 23:59 UTC). Establishes a clean, public-repo-ready project skeleton that passes the six parity surfaces from LES1, wraps the existing Ollama deployment as a working MCP-accessible tutor, validates the AWS Bedrock Custom Model Import path so demo week doesn't depend on GB10, and ships the technical write-up scaffolding so the submission narrative starts polished.

## What Phase 0 IS NOT

- Not Graphiti (Phase 1)
- Not a Coach (Phase 1)
- Not gamification state (Phase 2)
- Not a dashboard (Phase 2)
- Not Reachy (gated, stretch phase)
- Not multi-subject (post-hackathon)
- Not Dockerfile (deferred; venv-only install documented)

## Success Criteria (reiterated from scope doc)

1. Clean-machine walkthrough reproduces the tutor
2. Six parity surfaces SR-01 through SR-07 all green
3. AWS Bedrock validation passes
4. Domain contract authoritative
5. Technical write-up scaffolding lands
6. Lilymay's experience unchanged or improved
7. Public repo passes human-review gate

---

## Prerequisites

Before Friday evening (18 April) — set these up so the weekend isn't blocked on admin:

- [ ] AWS account with billing enabled, Bedrock Custom Model Import available in your selected region (check region availability — likely `us-east-1` or `us-west-2` for earliest Gemma 4 import support)
- [ ] IAM user with `bedrock:*` + `s3:*` limited to a specific bucket; access keys generated
- [ ] S3 bucket created for model artefacts (name suggestion: `appmilla-study-tutor-bedrock-models`)
- [ ] `claude_desktop_config.json` backup taken (we'll be editing this repeatedly)
- [ ] Confirm current state of `~/fine-tuning/output/gcse-tutor-gemma4-31b/` on GB10 — merged 16-bit weights present, GGUF Q4_K_M present (per memory, both already persisted)
- [ ] Confirm Tailscale paths: MacBook → GB10 (Ollama), MacBook → Synology (Phase 1 only, noop here)
- [ ] Pick the exact study-tutor Python package name: `study_tutor` (hyphen-to-underscore convention matches `specialist_agent`)
- [ ] Decide LiteLLM vs OpenRouter for Bedrock proxy — my recommendation: LiteLLM, self-hosted on GB10 alongside Ollama, simplest for OpenAI-compatible routing
- [ ] Confirm Kaggle hackathon rules readable — register + accept T&Cs so there are no surprises blocking submission on 17 May

---

## Feature Summary (from Phase 0 Scope)

| # | Feature | Depends On | Complexity | Wave |
|---|---------|------------|------------|------|
| **SR-01 to SR-07** | Structural requirements — six parity surfaces | — | baked into every feature | all |
| FEAT-PO-001 | GCSE English domain configuration + tutoring contract | — | 3/10 (doc-heavy, no code) | 1 |
| FEAT-PO-002 | Fine-tuned tutoring runtime + MCP transport | FEAT-PO-001 (for domain anchor) | 6/10 | 2 |
| FEAT-PO-003 | Bring-your-own-sources public repo packaging | FEAT-PO-001, FEAT-PO-002 | 3/10 (doc-heavy) | 3 |
| FEAT-PO-004 | AWS Bedrock Custom Model Import validation | FEAT-PO-002 | 5/10 (ops work) | 3 |
| FEAT-PO-005 | Technical write-up scaffolding | — (runs in parallel) | 2/10 | 1 |

**Dependency chain (critical path):**

```
FEAT-PO-001 (domain) ──► FEAT-PO-002 (runtime + MCP) ──► FEAT-PO-003 (repo packaging) ──► FEAT-PO-004 (Bedrock)
                                                     ──► clean-machine walkthrough gate

FEAT-PO-005 (write-up) runs in parallel across the whole week
```

Features FEAT-PO-001 and FEAT-PO-005 can run in parallel — both doc-heavy, no code dependency on each other. FEAT-PO-002 is the single largest feature and the critical path.

---

## Day-by-Day Plan

This is the weekend-first, "like we did last weekend for the specialist agent" plan. Front-loads the code work onto the two uninterrupted weekend days and reserves weekday evenings for the lower-energy doc work and the Bedrock ops work.

### Saturday 19 April (weekend day 1) — FEAT-PO-001 + FEAT-PO-002 kickoff ✅ DONE

**Target:** Domain contract complete. Project scaffolded. MCP server returning a real response from Ollama by end of day.

#### Morning (3 hours) — FEAT-PO-001

Write the GCSE English domain contract and gamification economy doc. These are the anchor documents every subsequent feature references; they must be right before code starts.

Work in Claude Desktop (not Claude Code — this is synthesis work, not implementation):

1. **Draft `domains/gcse-english/GOAL.md`** — use the scope doc's required sections as the outline. Pull AO content directly from `GCSE_English_AI_Tutor_Proposal.md` Assessment Objectives table. Pull tutoring style and boundaries from the proposal and copyright doc. Target length: 8–15KB, comparable to `specialist-agent/roles/product-owner/prompts/*.md`.

2. **Draft `docs/gamification/design.md`** — synthesise from `GCSE_Gamification_Research.md` and `gemma4-hackathon-submission-plan.md §5`. Include every concrete number: XP values, level titles, unlock gates, achievement names, confidence thresholds, streak milestones. No abstraction.

3. **Draft Coach criteria skeleton** — `roles/tutor/criteria/definitions.yaml`. Reference AOs by name. Leave the scoring weights TBD (Phase 1 work).

**Copy-paste-ready command for /system-arch later in the week:**
```
/system-arch \
  --from docs/research/ideas/phase-0-scope.md \
  --context docs/research/ideas/phase-0-build-plan.md \
  --context docs/research/ideas/decisions-log-2026-04-17.md \
  --context docs/research/ideas/state-of-the-project-and-phase-recommendation.md \
  --context docs/research/ideas/deepagents-patterns-review.md \
  --context /Users/richardwoollcott/Projects/appmilla_github/specialist-agent/docs/reference/cross-agent-lessons-from-specialist-agent.md
```

Don't run it yet — want domain docs drafted first.

#### Afternoon (4 hours) — FEAT-PO-002 scaffolding

Switch to Claude Code. Set up the repo structure.

1. **Initialise the Python package.** Copy `pyproject.toml` from `specialist-agent` as a starting point. Rename package to `study_tutor`. Set `[providers]` extra listing `langchain-openai`, `langchain-anthropic`, `langchain-google-genai`, `langchain-aws` (for Bedrock later), and `langchain-ollama` or direct Ollama HTTP.

   ```bash
   cd /Users/richardwoollcott/Projects/appmilla_github/study-tutor
   cp ../specialist-agent/pyproject.toml ./pyproject.toml.reference
   # Edit by hand, don't copy wholesale
   python3.11 -m venv .venv
   .venv/bin/pip install -e '.[providers]'
   ```

2. **Copy scaffolding directories.** `AGENTS.md`, `.env.example`, `.gitignore`, `.mcp.json` template — copy from specialist-agent, strip architect/PO-specific content, keep the patterns.

3. **Create the `src/study_tutor/` skeleton.** Directory layout:
   ```
   src/study_tutor/
   ├── __init__.py
   ├── __main__.py
   ├── cli/
   │   └── main.py          # serve command entrypoint
   ├── llm/
   │   └── client.py        # provider-routing LLM client
   ├── mcp/
   │   └── adapter.py       # MCP tool handlers
   ├── session/
   │   └── tutor_session.py # in-memory session state for Phase 0
   └── roles/
       └── tutor/
           └── role.yaml    # role config (minimal for Phase 0)
   ```
   Copy `llm/client.py` structure from specialist-agent. Adapt provider map so `"local"` → Ollama endpoint on GB10 by default. Stub `"bedrock"` to raise NotImplementedError (Phase 0 FEAT-PO-004 fills it in).

4. **Initialise `command_history.md`** at the repo root. First entry is the `/system-arch` invocation (not run yet, but capture the plan).

5. **First commit.** "Phase 0 kickoff: scaffold package, copy patterns from specialist-agent." Do not commit `.env`. Do commit `.env.example` with `<placeholder>` values per SR-06.

#### Evening (2 hours) — FEAT-PO-002 MCP skeleton

6. **Implement `src/study_tutor/mcp/adapter.py` at minimal shape.** Four tools registered per scope-doc SR-07 classification. `tutor_start_session` returns session_id immediately; `tutor_turn` is synchronous; status + end are trivial.

   Copy the fire-and-forget pattern from `specialist-agent/src/specialist_agent/mcp/adapter.py` `_start_po_session()` / `_run_po_session()`. Adapt for tutor-session semantics.

7. **Implement `_run_tutor_session()` as a single Ollama call per turn.** No Graphiti, no Coach, no gamification. Input: session_id, latest user turn. Output: tutor response from the fine-tuned model via Ollama.

8. **Stream-split stdio test per SR-01.** Wrap `click.echo` calls with `err=True`. Test:
   ```bash
   .venv/bin/study-tutor serve --role tutor --transport stdio < /dev/null > stdout.log 2> stderr.log &
   sleep 3; kill %1
   test ! -s stdout.log   # stdout must be empty before MCP handshake
   cat stderr.log          # banner should be here
   ```
   If stdout has content before handshake, fix before committing. This is the SR-01 gate.

9. **Write the bash wrapper.** `scripts/mcp-wrapper.sh` per SR-02.

10. **Add to `claude_desktop_config.json`.** Use the bash wrapper pattern, `cd` to absolute path, `. .env && export AGENT_MODELS__REASONING_MODEL=local && exec serve`.

11. **Restart Claude Desktop, verify green.** Expect a `study-tutor` server in the MCP list, 4 tools registered (`tutor_start_session`, `tutor_turn`, `tutor_session_status`, `tutor_session_end`).

12. **First real invocation.** From a Claude Desktop chat: "Use tutor_start_session with subject English Literature, topic Macbeth." Then "Use tutor_turn to ask about the significance of the witches in Act 1 Scene 1." Expect a response from the fine-tuned model.

**End-of-Saturday state:** domain contract written, MCP server running, first tutor_turn call succeeds against the fine-tuned Gemma 4. This is genuinely submittable as-is if everything else slips.

---

### Sunday 20 April (weekend day 2) — FEAT-PO-002 hardening + FEAT-PO-003 + FEAT-PO-005 start ✅ DONE (closed-out 23 Apr evening: PO-002 hardening Sun; FEAT-PO-003 doc tail 23 Apr; FEAT-PO-005 stubs 23 Apr)

**Target:** All six parity surfaces green. Public repo packaging done. Technical write-up stub in place. Clean-machine walkthrough achievable.

#### Morning (3 hours) — Parity surface hardening

The Saturday work was end-to-end-first. Sunday morning goes back over it and verifies each structural requirement formally.

1. **SR-01 (stdio discipline).** Re-run stream-split test. Add a unit test to `tests/unit/mcp/test_stdio_discipline.py` per the specialist-agent `TASK-MDF-MCPB` pattern.

2. **SR-02 (CWD absolute path).** Verify bash wrapper uses absolute path. Document in README. Add check to clean-machine walkthrough script.

3. **SR-03 (provider resolution at factory).** Add `_default_player_model()` helper to `src/study_tutor/llm/client.py`. Implement from `AGENT_MODELS__REASONING_MODEL` env var with `local` as fallback. Every MCP handler that takes a model param reads `params.get("player_model") or _default_player_model()`. Write unit tests that verify env-var flow end-to-end.

4. **SR-04 (providers extra completeness).** `pip show` each declared provider in the venv. Verify each can be imported without error. If any fail, either add the missing package or remove from extras.

5. **SR-05 (Dockerfile parity).** No Dockerfile in Phase 0, requirement is effectively pass-through. Add a note to the scope doc's "re-activate in Phase 1" row.

6. **SR-06 (.env hygiene).** `grep -r '=sk-' .env.example || echo "clean"`. `grep -r '=AIza' .env.example`. Verify placeholder values are `<your-openai-key-here>`-style, unambiguous.

7. **SR-07 (tool description ≡ behaviour).** Read the four MCP tool descriptions. Verify each is consistent with handler behaviour — by SR-07 acceptance, a description without the word "long-running" implies sync (< 30s). Per ADR-ARCH-017, all four Phase-0 tools are sync; `tutor_start_session` description says "Sync; returns session_id immediately; LLM model is warmed up in the background as fire-and-forget"; implementation returns session_id in < 1s with `asyncio.create_task` warm-up.

#### Afternoon (3 hours) — FEAT-PO-003

Public repo packaging — the document-heavy feature. Most of this is writing, not coding.

1. **Draft `README.md` at repo root.** Full version per scope doc. Judges will read this; it's the submission narrative's front door. Sections: what this is, why it exists, architecture (with the three-layer diagram), pipeline overview, bring-your-own-sources section, provenance, public vs private table, quick start, roadmap, status.

2. **Draft `domains/gcse-english/sources/README.md`.** Explicit bring-your-own-sources instructions. List what to acquire (Mr Bruff PDFs tested, CGP/York Notes alternatives), how to place them, how to run ingestion (commands that will work once the ingestion pipeline is reused from `agentic-dataset-factory` in a later phase).

3. **Choose and add LICENSE.** Apache 2.0 at repo root. Add a `docs/licensing.md` explaining that Gemma 4 base weights are Apache 2.0, our LoRA adapter is not distributed, and the fine-tuned merged weights are not distributed either.

4. **Harden `.gitignore`.** Explicit entries for `domains/*/sources/*.pdf`, `chroma/`, `chroma_data*/`, `output/train.jsonl`, `*.gguf`, `models/`, `~/fine-tuning/`, `.env`. Verify: `git status` after adding a dummy PDF to `domains/gcse-english/sources/` does not list it as a new file.

5. **Pre-commit sanity check.** `find . -name '*.pdf' | grep -v .venv` should return nothing. `find . -name '*.gguf'` should return nothing. If either returns files, scrub them before any commit.

#### Evening (2 hours) — FEAT-PO-005 kickoff

The technical write-up scaffolding. Doc stubs that will be filled as the build progresses.

1. **Create `docs/submission/technical-writeup.md`.** Every required section titled with a one-line description. No content yet beyond the outline.

2. **Create `docs/submission/demo-script.md`.** Skeleton: 30s working-today, 60s architecture reveal, 60s gamification, 30s Reachy or vision, 30s roadmap. Empty content under each scene.

3. **Create `docs/submission/video-outline.md`.** Storyboard-lite. Empty shell.

4. **Commit.** "Phase 0 Sunday: parity surfaces green, repo packaging complete, submission doc stubs."

**End-of-Sunday state:** Six parity surfaces green. Public repo looks serious. Submission narrative has an outline. MCP server works. Only Bedrock remains for the weekend — that's a weekday evening task since it's mostly ops, not code.

---

### Monday 21 April (evening, ~2 hours) — FEAT-PO-004 Bedrock setup 🔲 DEFERRED (FEAT-PO-002 shipped end-to-end this evening instead; Bedrock S3 upload + import not yet executed)

Ops work. Low code content. Good for a tired weekday evening.

> **Bedrock-out contingency (decided 19 Apr 2026, TASK-CDR-005).** If
> FEAT-PO-004 fails on 22 Apr (eu-west-2 lacks Gemma 4 31B Custom Model
> Import support, or fallback regions also fail) and demo-week inference
> must run on Ollama/GB10, the three DEC-07 GB10 training workloads are
> sequenced as: (1) **non-negotiable** — architect-agent training +
> fine-tune for DDD Southwest 16 May; (2) **squeezed if needed** —
> study-tutor re-fine-tune (the 18 Apr checkpoint is shippable as-is);
> (3) **squeezed first** — study-tutor training-dataset expansion
> (waiting on more GCSE subject books anyway). Captured here so the call
> is already made if Tuesday's smoke test goes south. Hosting order on
> Bedrock if it works: study-tutor first, architect second.

1. **Enable Bedrock Custom Model Import in AWS console.** Confirm region. Accept terms.

2. **Upload the existing merged 16-bit weights to S3.** From GB10:
   ```bash
   # On GB10
   aws configure  # set credentials
   aws s3 cp ~/fine-tuning/output/gcse-tutor-gemma4-31b/merged-16bit/ \
       s3://appmilla-study-tutor-bedrock-models/gemma4-31b-gcse-tutor/ \
       --recursive
   ```

3. **Import model into Bedrock.** Via AWS console or CLI. Configure with Gemma 4 31B base model selector. Name: `gcse-english-tutor-v1`. Wait for import to complete (can take 30–60min for a 31B model).

4. **Note the Bedrock model ARN.** Add to `.env.example` as `BEDROCK_MODEL_ARN=<placeholder>`.

**End-of-Monday state:** Bedrock import job kicked off. Check status in the morning.

---

### Tuesday 22 April (evening, ~2 hours) — FEAT-PO-004 Bedrock validation 🔲 DEFERRED (TASK-PO02F-001 RAG grounding scoped instead — `b3c567f`)

1. **Verify Bedrock import completed.** Model status = "Active". Test via AWS CLI:
   ```bash
   aws bedrock-runtime invoke-model \
       --model-id <arn> \
       --body '{"prompt":"Explain Macbeth Act 1 Scene 1 briefly.","max_tokens":200}' \
       --cli-binary-format raw-in-base64-out \
       bedrock-response.json
   cat bedrock-response.json
   ```

2. **Extend `src/study_tutor/llm/client.py` for Bedrock.** Route `AGENT_MODELS__REASONING_MODEL=bedrock` to Bedrock via `langchain-aws` or direct boto3. Keep the interface identical to the Ollama path.

3. **Smoke test via MCP.** Set `AGENT_MODELS__REASONING_MODEL=bedrock` in `.env`, restart the MCP server, call `tutor_turn` from Claude Desktop. Compare response coherence to the Ollama path.

4. **LiteLLM on GB10 for OpenWebUI.** Install LiteLLM on GB10, configure it with Bedrock as a backend and an OpenAI-compatible endpoint. Point OpenWebUI's OpenAI-compatible provider config at `http://localhost:4000` (LiteLLM's default). Verify Lilymay's existing chat interface works against Bedrock.

5. **Cost check.** Record the cost of the smoke-test calls. Back-of-envelope: a 5-minute session budget per DEC-07 memory is ~$1.50–$3.00. Verify observed cost is in range.

**End-of-Tuesday state:** Bedrock validated. OpenWebUI pointed at Bedrock (or reverted to Ollama if issues). Tutor works via both paths.

---

### Wednesday 23 April (evening, ~2 hours) — Clean-machine walkthrough 🔲 NOT YET RUN

This is the canonical-gate for Phase 0. Everything green, ready for submission if nothing else ships.

1. **Prepare a walkthrough log file.** Mirror `specialist-agent/.claude/reviews/TASK-REV-B8E4-walkthrough-log.md` shape. Target: `study-tutor/.claude/reviews/TASK-REV-PH0-walkthrough-log.md`. Document versions, .env drift, commands run, observations.

2. **Clone the repo to a fresh location.**
   ```bash
   cd /tmp
   git clone /Users/richardwoollcott/Projects/appmilla_github/study-tutor study-tutor-walkthrough
   cd study-tutor-walkthrough
   ```

3. **Execute the README quick-start verbatim.** Time each step. Note every deviation.

4. **Test the MCP path.** Point a second Claude Desktop instance (or tmp config) at the fresh clone's bash wrapper. Verify four tools, successful `tutor_turn`.

5. **Test the Bedrock path.** Set `AGENT_MODELS__REASONING_MODEL=bedrock`, run a `tutor_turn`, verify response.

6. **Test the provider-switch.** Set `AGENT_MODELS__REASONING_MODEL=local`, restart, verify Ollama path still works.

7. **Fix every deviation found.** Commit each fix with a clear message. Re-run the walkthrough after fixes.

8. **Declare Phase 0 canonical.** Update `command_history.md` with the walkthrough results. Update the technical write-up's "status" section.

**End-of-Wednesday state:** Phase 0 submission-ready. If everything else slips, what shipped on Wednesday is enough.

---

### Thursday 24 April (evening, ~2 hours) — Phase 1 kickoff prep 🔲 PENDING (tonight)

Phase 0 done. Phase 1 (Graphiti + DeepAgents + session lifecycle) starts next weekend. Thursday evening preps for that weekend.

1. **Draft `phase-1-scope.md` and `phase-1-build-plan.md`.** Copy the shape from Phase 0 docs. Core features: FEAT-PO-004 roadmap (Graphiti student model), FEAT-PO-005 roadmap (session planner), FEAT-PO-006 roadmap (DeepAgents tutoring loop + Coach).

2. **Run the Graphiti spike plan.** Day 1 of Phase 1 weekend is a latency-measurement spike per DEC-02 and DEC-08. Prep: ensure FalkorDB on Synology NAS is reachable from MacBook; ensure Gemini API key configured for Graphiti entity extraction; ensure nomic-embed-text-v1.5 is serving on GB10 port 8001 per `specialist-agent/.claude/reviews/TASK-REV-B8E4-walkthrough-log.md §6`.

3. **Commit the Phase 1 scaffolding docs.** This keeps momentum: next weekend's work is already scoped when you wake up Saturday.

---

### Friday 25 April — soft buffer day

Intentionally unscheduled. Any Phase 0 slips land here. If Phase 0 shipped cleanly, Friday is rest or YouTube content capture.

---

## GuardKit Command Sequence

After Saturday's domain docs are drafted (FEAT-PO-001 morning), kick off the GuardKit pipeline. Don't run these before the domain docs are written — `/system-arch` needs something to reference.

```bash
# Recommended timing: Saturday evening or Sunday morning, after domain docs drafted

/system-arch \
  --from docs/research/ideas/phase-0-scope.md \
  --context docs/research/ideas/phase-0-build-plan.md \
  --context docs/research/ideas/decisions-log-2026-04-17.md \
  --context docs/research/ideas/state-of-the-project-and-phase-recommendation.md \
  --context docs/research/ideas/deepagents-patterns-review.md \
  --context /Users/richardwoollcott/Projects/appmilla_github/specialist-agent/docs/reference/cross-agent-lessons-from-specialist-agent.md \
  --context domains/gcse-english/GOAL.md \
  --context docs/gamification/design.md

# After ARCHITECTURE.md is produced:
#
# /system-design is staged by phase (decision 2026-04-26):
#   - Phase 0 run: scope to the three implemented contexts + Shared Kernel B
#     event surface only, bias-to-defaults (propose contracts/data models from
#     existing docs, ask only on genuine open questions).
#   - Phase 1 / Phase 2: re-run --focus per context as those contexts gain
#     runtime code (Knowledge & Curriculum, Student Model, then Gamification).
# Rationale: 3 of 6 contexts have shipped code today (Tutoring, Inference
# Runtime, MCP Transport); P1/P2 contexts are still doc-only. Designing them
# now risks contracts that drift before implementation. Per-phase --focus
# re-runs keep the design context Graphiti-seeded with what's actually true.

# Phase 0 invocation (run 2026-04-26):
/system-design \
  --from docs/architecture/ARCHITECTURE.md \
  --context docs/research/ideas/phase-0-scope.md \
  --context docs/research/ideas/phase-0-build-plan.md
# Inside the session, scope to: Tutoring, Inference Runtime, MCP Transport,
# plus the Shared Kernel B (Events) surface. Skip Knowledge & Curriculum,
# Student Model, Gamification at the [S]kip checkpoint.

# Phase 1 re-runs (recommended Sat 26 Apr morning, after phase-1-scope.md is
# drafted and the Graphiti spike has produced latency numbers — DEC-02/DEC-08):
/system-design --focus="Knowledge & Curriculum" \
  --from docs/architecture/ARCHITECTURE.md \
  --context docs/research/ideas/phase-1-scope.md \
  --context docs/research/ideas/rag-grounding-design.md \
  --context docs/research/ideas/openwebui-rag-empirical-findings-2026-04-23.md
/system-design --focus="Student Model" \
  --from docs/architecture/ARCHITECTURE.md \
  --context docs/research/ideas/phase-1-scope.md \
  --context docs/architecture/decisions/ADR-ARCH-019-async-graphiti-writeback-every-write-point.md \
  --context docs/architecture/decisions/ADR-ARCH-018-extend-cross-cutting-concerns-sr08-sr09.md \
  --context docs/architecture/decisions/ADR-ARCH-007-graphiti-split-topology.md

# Phase 2 re-run (recommended once gamification engine moves from docs to
# runtime code per ADR-ARCH-013):
/system-design --focus="Gamification" \
  --from docs/architecture/ARCHITECTURE.md \
  --context docs/research/ideas/phase-2-scope.md \
  --context docs/gamification/design.md \
  --context docs/architecture/decisions/ADR-ARCH-013-middleware-level-gamification-engine-future.md

/system-plan \
  --from docs/design/DESIGN.md \
  --context docs/architecture/ARCHITECTURE.md \
  --context docs/research/ideas/phase-0-scope.md \
  --context docs/research/ideas/phase-0-build-plan.md

# Then per-feature spec-and-plan. One command per feature, in dependency order:

/feature-spec "GCSE English Domain Configuration — GOAL.md, AOs, gamification economy reference, Coach criteria skeleton" \
  --context docs/research/ideas/phase-0-scope.md \
  --context docs/research/ideas/phase-0-build-plan.md \
  --context domains/gcse-english/GOAL.md \
  --context docs/gamification/design.md \
  --context /Users/richardwoollcott/Projects/appmilla_github/specialist-agent/roles/product-owner/role.yaml

/feature-plan "GCSE English Domain Configuration" \
  --context features/gcse-english-domain-config/gcse-english-domain-config_summary.md

/feature-spec "Fine-Tuned Tutoring Runtime and MCP Transport — package scaffolding, LLM client, MCP adapter with 4 tools, bash wrapper, CLI entrypoint, six parity surfaces structural requirements" \
  --context docs/research/ideas/phase-0-scope.md \
  --context docs/research/ideas/phase-0-build-plan.md \
  --context /Users/richardwoollcott/Projects/appmilla_github/specialist-agent/src/specialist_agent/mcp/adapter.py \
  --context /Users/richardwoollcott/Projects/appmilla_github/specialist-agent/src/specialist_agent/llm/client.py \
  --context /Users/richardwoollcott/Projects/appmilla_github/specialist-agent/docs/reference/cross-agent-lessons-from-specialist-agent.md

/feature-plan "Fine-Tuned Tutoring Runtime and MCP Transport" \
  --context features/fine-tuned-tutoring-runtime/fine-tuned-tutoring-runtime_summary.md

/feature-spec "Bring-Your-Own-Sources Public Repo Packaging — README, domains/sources README, LICENSE, .gitignore hardening" \
  --context docs/research/ideas/phase-0-scope.md \
  --context docs/research/ideas/copyright-training-data-analysis.md \
  --context README.md \
  --context .gitignore

/feature-plan "BYOS Public Repo Packaging" \
  --context features/byos-public-repo-packaging/byos-public-repo-packaging_summary.md

/feature-spec "AWS Bedrock Custom Model Import Path — S3 upload, model import, provider integration in LLM client, LiteLLM proxy for OpenWebUI, validation smoke test" \
  --context docs/research/ideas/phase-0-scope.md \
  --context docs/research/ideas/decisions-log-2026-04-17.md \
  --context src/study_tutor/llm/client.py

/feature-plan "AWS Bedrock Custom Model Import Path" \
  --context features/aws-bedrock-custom-model-import/aws-bedrock-custom-model-import_summary.md

/feature-spec "Technical Write-Up Scaffolding — technical-writeup.md, demo-script.md, video-outline.md section stubs" \
  --context docs/research/ideas/phase-0-scope.md \
  --context docs/research/ideas/state-of-the-project-and-phase-recommendation.md \
  --context docs/research/ideas/gemma4-hackathon-submission-plan.md

/feature-plan "Technical Write-Up Scaffolding" \
  --context features/technical-write-up-scaffolding/technical-write-up-scaffolding_summary.md

# After each /feature-plan, either:
# - /feature-build FEAT-XXXX  (autonomous build)
# - /task-work TASK-YYYY-001  (one task at a time, reviewer in the loop)
#
# Recommended: autonomous build for FEAT-PO-001 (doc-heavy), FEAT-PO-003 (doc-heavy), FEAT-PO-005 (doc-heavy)
# Reviewer-in-loop for FEAT-PO-002 (critical path, parity surfaces) and FEAT-PO-004 (ops work, needs human for AWS)
```

---

## Files That Will Change

### New files in study-tutor

| File | Feature | Change type |
|------|---------|-------------|
| `pyproject.toml` | FEAT-PO-002 | NEW |
| `AGENTS.md` | FEAT-PO-002 | NEW |
| `.env.example` | FEAT-PO-002 + SR-06 | NEW |
| `.gitignore` | FEAT-PO-003 | EXTEND |
| `.mcp.json` | FEAT-PO-002 | NEW |
| `README.md` | FEAT-PO-003 | REPLACE (currently a stub) |
| `LICENSE` | FEAT-PO-003 | NEW (Apache 2.0) |
| `command_history.md` | all | NEW |
| `src/study_tutor/cli/main.py` | FEAT-PO-002 | NEW |
| `src/study_tutor/llm/client.py` | FEAT-PO-002 + FEAT-PO-004 | NEW |
| `src/study_tutor/mcp/adapter.py` | FEAT-PO-002 | NEW |
| `src/study_tutor/session/tutor_session.py` | FEAT-PO-002 | NEW |
| `roles/tutor/role.yaml` | FEAT-PO-001 + FEAT-PO-002 | NEW |
| `roles/tutor/criteria/definitions.yaml` | FEAT-PO-001 | NEW (skeleton only) |
| `roles/tutor/prompts/player.md` | FEAT-PO-002 | NEW |
| `domains/gcse-english/GOAL.md` | FEAT-PO-001 | NEW |
| `domains/gcse-english/sources/README.md` | FEAT-PO-003 | NEW |
| `docs/gamification/design.md` | FEAT-PO-001 | NEW |
| `docs/licensing.md` | FEAT-PO-003 | NEW |
| `docs/submission/technical-writeup.md` | FEAT-PO-005 | NEW (stub) |
| `docs/submission/demo-script.md` | FEAT-PO-005 | NEW (stub) |
| `docs/submission/video-outline.md` | FEAT-PO-005 | NEW (stub) |
| `scripts/mcp-wrapper.sh` | FEAT-PO-002 | NEW |
| `tests/unit/mcp/test_stdio_discipline.py` | FEAT-PO-002 + SR-01 | NEW |
| `tests/unit/llm/test_provider_resolution.py` | FEAT-PO-002 + SR-03 | NEW |
| `.claude/reviews/TASK-REV-PH0-walkthrough-log.md` | Wednesday walkthrough | NEW |

### Files changed in other repos

**None in Phase 0.** Specialist-agent, nats-core, nats-infrastructure, agentic-dataset-factory all unchanged.

### AWS resources created

| Resource | Phase | Notes |
|----------|-------|-------|
| S3 bucket `appmilla-study-tutor-bedrock-models` | FEAT-PO-004 | Private, used for model artefact upload |
| Bedrock Custom Model Import `gcse-english-tutor-v1` | FEAT-PO-004 | Imported from merged 16-bit weights |
| IAM user with scoped bedrock+s3 permissions | Prerequisite | For programmatic access |

### Claude Desktop config

| File | Change |
|------|--------|
| `~/Library/Application Support/Claude/claude_desktop_config.json` | Add `study-tutor` MCP server entry with bash wrapper |
| `~/Library/Application Support/Claude/claude_desktop_config.json.bak-PH0-<date>` | Backup taken before edit |

---

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Parity surface check reveals Saturday code violates SR-01/03 | Medium | Low | Sunday morning dedicated to this exact verification; fix-as-found with unit tests |
| Bedrock model import takes longer than expected (>2h) | Medium | Low | Import is async, started Monday evening; even a 4h import completes overnight |
| Bedrock response incoherent vs Ollama output | Low | Medium | If Bedrock output is materially worse, revert to Ollama-primary, Bedrock-as-backup; note as open question for Phase 1 |
| LiteLLM proxy for OpenWebUI breaks Lilymay's existing chat | Medium | **High — breaks Lilymay's daily use** | Do LiteLLM setup in a separate GB10 port, switch OpenWebUI's provider config only after validation; keep the existing Ollama-direct config as a one-click fallback |
| Clean-machine walkthrough on Wednesday exposes drift | High (this is the point) | Low | This is the design — Wednesday is the gate, Thursday is the buffer |
| Kaggle rules (read late) impose an unexpected constraint | Medium | Variable | Read them Friday evening before weekend; Phase 0 has enough flexibility in FEAT-PO-003 to accommodate most constraints |
| GB10 needed for specialist-agent architect training at the same time as study-tutor Phase 1 work | Low in Phase 0 (no GB10 training in Phase 0) | Medium in later phases | Bedrock validated in Phase 0 means Phase 1–2 demo doesn't need GB10 at all |
| Claude Desktop MCP wrapper pattern breaks on OS X 15.6 | Low (proven on TASK-REV-B8E4) | Low | Pattern literally copy-pasted from working specialist-agent wrapper; minimal deviation risk |

---

## Review Gates

### End of Saturday — mid-weekend review

**Hard question:** Does `tutor_turn` return a real response from the fine-tuned Gemma 4 model via MCP?

- Yes → on track, Sunday is polish
- No → stop, diagnose. If Ollama-side issue, fix directly. If MCP-side issue, compare to `specialist-agent/src/specialist_agent/mcp/adapter.py` handler pattern.

### End of Sunday — end-of-weekend review

**Hard question:** Are the six parity surfaces green? Can the README stand on its own as a submission if Phase 1 slips?

- Both yes → Phase 0 is two days ahead of schedule; Tuesday Bedrock work is ops-only
- Either no → Monday–Tuesday evenings absorb the slip

### End of Wednesday — clean-machine walkthrough gate

**Hard question:** Can a fresh MacBook follow the README and produce a working tutor?

- Yes → Phase 0 canonical, Thursday is Phase 1 prep
- No → Thursday is slip absorption, Friday is Phase 1 prep. Phase 1 weekend still starts on time.

### End of Friday — Phase 0 close-out

**Hard question:** Are Phase 1 scope + build plan drafted and committed?

- Yes → Phase 1 weekend (26–27 April) starts with zero setup time
- No → Phase 1 Saturday morning absorbs the planning; code work starts Saturday afternoon instead of Saturday morning

---

## YouTube Content from Phase 0

Captured in passing for the content strategy; not a Phase 0 deliverable:

- "Bootstrapping an AI tutor in a weekend: lessons from my last agent build"
- "The six parity surfaces I learned the hard way — applied fresh"
- "Why I'm moving inference off my GB10 two weeks before a hackathon"
- "Bring-your-own-sources: open-sourcing the pipeline, not the data"

Short-form clips from the Wednesday walkthrough are particularly good: "fresh machine, one README, one working tutor" in 60 seconds. File these as recording opportunities during the walkthrough itself; don't try to produce during the build.

---

## Expected Timeline (summary)

| Day | Work | Hours | End-of-day state |
|-----|------|-------|------------------|
| Fri 18 Apr | Prereqs (AWS, Kaggle, config backups) | 1 | Ready for weekend |
| Sat 19 Apr | FEAT-PO-001 + FEAT-PO-002 kickoff | 9 | MCP server working, domain docs done |
| Sun 20 Apr | Parity surfaces + FEAT-PO-003 + FEAT-PO-005 start | 8 | Public repo packaging done, submission stubs |
| Mon 21 Apr | FEAT-PO-004 Bedrock setup | 2 | Import running overnight |
| Tue 22 Apr | FEAT-PO-004 Bedrock validation | 2 | Bedrock path working |
| Wed 23 Apr | Clean-machine walkthrough | 2 | Phase 0 canonical |
| Thu 24 Apr | Phase 1 prep | 2 | Phase 1 docs drafted |
| Fri 25 Apr | Buffer / slip absorption / rest | 0–2 | Ready for Phase 1 weekend |

**Total: ~26 hours over 8 days**, weekend-weighted 17h vs weekday-evening 9h. Comparable to the specialist-agent weekend build cadence.

---

*Phase 0 build plan: 17 April 2026*
*Consuming: `phase-0-scope.md`, `decisions-log-2026-04-17.md`, `state-of-the-project-and-phase-recommendation.md`, `cross-agent-lessons-from-specialist-agent.md`*
*Predecessor: specialist-agent Phase 1–G pattern*
*Target: submittable-on-its-own end-of-Week-1 baseline, built over one weekend + four weekday evenings*
