# Phase 0 Scope — Hackathon Floor + Parity Hygiene

## For: Claude Code `/system-arch` → `/system-design` → `/system-plan` → `/feature-spec` → `/feature-plan` → AutoBuild
## Date: 17 April 2026
## Status: Ready to consume
## Context: Week 1 of the 31-day build to Gemma 4 Good Hackathon submission (18 May 2026). Establishes a clean, public-repo-ready project skeleton that passes the six parity surfaces from `cross-agent-lessons-from-specialist-agent.md` (LES1), wraps the existing Ollama deployment as a working MCP-accessible tutor, and documents the provenance and architecture in a way that could be submitted on its own if Phases 1–2 slip.

---

## Motivation

Study Tutor is not a greenfield project. The fine-tuned Gemma 4 31B, the ChromaDB curriculum layer, Docling ingestion, and the Ollama deployment all exist and are working for Lilymay today. The 13-feature roadmap exists. The gamification design is specified in concrete mechanics. The cross-agent lessons doc tells us which pitfalls to avoid structurally. What's missing for a credible hackathon submission is Layer 3 (Graphiti student model), the DeepAgents harness that orchestrates all three layers in a live interactive session, and the gamification engine that makes the experience retention-worthy — plus the packaging hygiene that lets the public repo walkthrough pass on a clean machine.

Phase 0 is the floor below which no submission is credible: a public repo that passes the six parity surfaces on a fresh MacBook, a working fine-tuned tutor Lilymay can still use, an MCP-accessible interface for the architecture demo, an AWS Bedrock Custom Model Import path validated so demo week doesn't depend on GB10 availability, and the technical write-up started early so it's polished rather than panicked by 17 May.

Phase 0 deliberately does **not** include Graphiti, gamification state, the full DeepAgents tutoring loop, or the dashboard — those are Phase 1 and Phase 2. Phase 0 is the minimum self-sufficient submission if everything that follows goes wrong.

The cross-agent lessons doc (`specialist-agent/docs/reference/cross-agent-lessons-from-specialist-agent.md`) is a first-class input to this scope. Every item in its pre-implementation checklist that applies to study-tutor (MCP-only, short-latency, no NATS) is load-bearing. Two rows are marked ⚠️ for study-tutor specifically — rows 10 and 19 (fire-and-forget above 30s and latency classification) — and Phase 0 must resolve the ambiguity for our session shape before committing code.

---

## Scope: Five Features + Structural Requirements

The structural requirements are not features. They are cross-cutting non-functional properties of the Phase 0 codebase that must be structurally true from the first commit, not retrofitted later. They are listed before the features because they shape how every feature is built.

### Structural Requirements (six parity surfaces from LES1, scoped to Study Tutor)

These requirements apply to every feature in Phase 0 and every feature after it. They are the definition-of-done gate before the Phase 0 walkthrough can be declared canonical.

#### SR-01: MCP transport discipline

**Requirement.** `serve --transport stdio` emits MCP JSON-RPC to stdout only. Every banner, diagnostic, warning, log line, or status message goes to stderr via `click.echo(..., err=True)` or `print(..., file=sys.stderr)`. Stream-split test must pass: `stdout.log` empty before handshake, `stderr.log` contains banner.

**Evidence from LES1.** TASK-MDF-MCPB — specialist-agent had 4 JSON-parse toasts per agent in Claude Desktop until `err=True` landed.

**Acceptance.** Running the MCP server against `/dev/null` stdin with 5-second timeout produces zero bytes on stdout before the handshake would begin; `stderr` contains the "MCP server starting..." banner.

#### SR-02: Launcher CWD absolute path

**Requirement.** The bash wrapper used by Claude Desktop (or any MCP client) `cd`s to an absolute repo path before `exec`ing the serve command. Relative-path resolution in the agent code is acceptable only if it resolves from the explicit repo root.

**Evidence from LES1.** TASK-MDF-MCPB iteration 1 — `serve` resolved `roles/<role>/` relative to CWD; Claude Desktop launched MCP from an unspecified CWD.

**Acceptance.** The reference `claude_desktop_config.json` entry for study-tutor uses a bash wrapper with `cd /absolute/path/to/study-tutor &&` before `exec`.

#### SR-03: Provider resolution at the factory

**Requirement.** The model factory reads provider from `AGENT_MODELS__REASONING_MODEL` env var at instantiation. No handler hard-codes `player_model="claude"` or any other provider. Every MCP handler receives `player_model=request.get("player_model") or _default_player_model()`.

**Evidence from LES1.** TASK-MDF-PMEV + TASK-MDF-CRMV — specialist-agent hard-coded `"claude"` in MCP handlers; same bug recurred in CommandRouter for NATS path.

**Acceptance.** Setting `AGENT_MODELS__REASONING_MODEL=openai` in `.env` or shell and making an MCP tool call results in an OpenAI API call, verifiable in logs. Setting `local` results in a call to the Ollama endpoint. Setting `bedrock` (after Phase 1) results in a Bedrock call.

#### SR-04: `[providers]` extra completeness

**Requirement.** `pyproject.toml` declares a `[providers]` optional-dependency group listing every LangChain integration the code imports. `langchain-openai`, `langchain-google-genai`, `langchain-anthropic` all explicit (even if not all are actively used) so provider switches don't require pyproject edits.

**Evidence from LES1.** TASK-MDF-LCOI — `langchain-openai` was pulled transitively by `deepagents` but not declared, so it was missing from the Docker image build.

**Acceptance.** `pip install -e '.[providers]'` installs all three LangChain integrations. A smoke test exercises each declared provider once (at least `local` for Ollama and `openai` for GPT-5.4).

#### SR-05: Dockerfile install parity

**Requirement.** If a Dockerfile ships in Phase 0, its `pip install` command is a literal-match for the documented venv install, including extras. `RUN pip install --no-cache-dir -e '.[providers]'` matches the guide's `.venv/bin/pip install -e '.[providers]'`.

**Evidence from LES1.** TASK-MDF-DKRX — specialist-agent's Dockerfile ran `pip install .` while the guide prescribed `.[providers]`. Providers were missing at runtime.

**Acceptance.** If Phase 0 ships a Dockerfile, `grep 'pip install' Dockerfile` output matches the guide's install instruction. If Phase 0 does not ship a Dockerfile, this requirement re-activates for Phase 1 / 2 when one is added.

**Phase 0 decision.** No Dockerfile in Phase 0. Venv-only install documented. Dockerfile deferred.

#### SR-06: `.env` hygiene

**Requirement.** No real-looking provider keys in any `.env` file committed to the repo. `.env.example` only, with `<placeholder>` values that cannot be mistaken for real keys (never `not_needed`, `sk-test-xxxx`, or similar — use literal `<your-openai-key-here>`). CI pre-merge check rejects any commit that adds a non-placeholder value to `.env.example`.

**Evidence from LES1.** §retest-env — `OPENAI_API_KEY=not_needed` in `specialist-agent/.env` silently overrode the operator's real shell-env key during Compose variable interpolation, producing HTTP 401.

**Acceptance.** `grep -r '=sk-' .env.example` returns no matches. `git log --all -- .env` shows no real-looking values ever committed.

#### SR-07: Tool description ≡ implementation contract

**Requirement.** Every MCP tool's description field matches its implementation behaviour. If a tool description says "long-running — session tracked", the handler returns a session_id immediately and exposes a `_status`/`_cancel` companion tool. If a tool description does not say long-running, the handler completes synchronously within 30 seconds.

**Evidence from LES1.** TASK-MDF-POLR — `po_idea` description said "long-running" but handler awaited synchronously, producing a 4-minute timeout on Claude Desktop's 240-second MCP limit.

**Acceptance.** Every MCP tool in Phase 0 classified as either "sync" (< 30s bound) or "long-running" (returns session_id immediately, poll via companion). No tool in the undefined middle.

**Phase 0 decision — classification (provisional, to be confirmed by the Graphiti latency spike in Phase 1):**

| Tool | Class | Rationale |
|---|---|---|
| `tutor_start_session` | long-running (session_id returned, poll via `tutor_session_status`) | Includes Graphiti read of student model (three-hop: MacBook → Synology → Gemini → GB10 embeddings); could exceed 10s |
| `tutor_turn` | sync (< 30s) | Single LLM inference via Ollama; target p95 < 10s |
| `tutor_session_status` | sync | Quick read |
| `tutor_session_end` | sync | Triggers Graphiti write-back which is async to the caller |

If Phase 1 spike shows `tutor_start_session` consistently < 10s end-to-end, reclassify as sync. If `tutor_turn` exceeds 30s due to session-accumulated context, reclassify as long-running.

---

### FEAT-PO-001: GCSE English Domain Configuration and Tutoring Contract

**Problem.** The fine-tuned model knows how to tutor in the abstract. There's no declarative statement of what GCSE English tutoring means behaviourally. Without this, the Phase 1 Coach has no rubric to evaluate against and the public repo has no anchor for "what does this tutor actually do."

**Changes required.**

#### 1. `domains/gcse-english/GOAL.md`

Create the GOAL.md that defines the tutor's behavioural contract. Structure follows `agentic-dataset-factory`'s GOAL.md pattern, adapted from training-data-generation semantics to live-tutoring semantics.

**Required sections:**
- **Subject and specification.** AQA English Language (8700) and English Literature (8702). Year 10 target. Lilymay as the reference student.
- **Assessment objectives.** Full table matching the proposal's AO1–AO6, with one-paragraph behavioural guidance per AO. AO1: how the tutor scaffolds explicit vs implicit reading; AO2: how it guides language-and-structure analysis; AO3: how it supports comparative essays; AO4: how it handles evaluation with textual references; AO5: how it supports communication clarity; AO6: how it addresses technical accuracy without turning every turn into a grammar correction.
- **Texts and topics.** Literature components (Shakespeare, 19th C novel, modern drama, poetry anthology) and Language components (reading, writing, speaking). Named texts where relevant (Macbeth, Power & Conflict Poetry, etc.) — these are factual curriculum references, not AQA assessment content.
- **Tutoring style.** Socratic questioning, scaffolded rather than given, constructive feedback that names the AO being addressed, Year-10-appropriate language.
- **Content boundaries.** What the tutor will not do: reproduce copyrighted texts, quote past-paper questions, claim certainty about exam grades, replace the teacher. What it will do: help with understanding, structure, evidence use, practice answers.
- **Grade-level calibration.** How the tutor handles Grade 4 vs Grade 7 vs Grade 9 targets — scaffolding depth, vocabulary expected, example complexity.

**Decision inputs:**
- DEC-04 — explicit per-AO scaffolding is mandatory
- Copyright policy from `copyright-training-data-analysis.md` §2, §6 — AQA specification references acceptable, AQA assessment materials prohibited

#### 2. `docs/gamification/design.md`

Publish the full gamification economy per DEC-03. Single authoritative document for XP values, levels, achievements, and unlock gates. This document is referenced by the GOAL.md and by every Phase 2 gamification feature.

**Required content:**
- XP economy table (session values, daily challenge values, achievement bonuses, Boss Battle rewards)
- 15-level progression with named titles (Beginner → Novice → Apprentice → Student → Learner → Scholar → Academic → Intellectual → Expert → Master → Sage → Virtuoso → Luminary → Prodigy → Grandmaster) and per-level unlock gates (daily challenges at L2, exam questions at L6, Boss Battle at L8, Teaching Mode at L10)
- 6 achievement categories (Consistency, Mastery, Growth, Exploration, Challenge, Milestone) with category definitions
- Named achievements with criteria (Quote Champion, Macbeth Master at 80% confidence, Fortnight Force at 14 consecutive days, Poetry Pioneer, Exam Ready)
- Topic mastery confidence taxonomy (Struggling → Developing → Secure → Mastered) with percentage bands
- Daily challenge shapes (rotating mini-goals with XP values)
- Boss Battle mode definition (unlock gate, timing, scoring, reward)

**Source material:** `GCSE_Gamification_Research.md` (full content), `gemma4-hackathon-submission-plan.md §5` (the 15-level progression specifically).

#### 3. Coach rubric skeleton

Coach prompt and criteria file stub living in `roles/tutor/criteria/definitions.yaml` (per the specialist-agent role.yaml pattern). The criteria reference the AOs from GOAL.md by name. Full Coach implementation is Phase 1 (FEAT-PO-006); Phase 0 only creates the skeleton so the domain contract is complete at the spec level.

---

### FEAT-PO-002: Fine-Tuned Tutoring Runtime and MCP Transport

**Problem.** The fine-tuned Gemma 4 31B is accessible today via Ollama over Tailscale. It is not wrapped in any transport an architecturally credible demo can point at. The hackathon judges need to see the tutor as a system, not as a chat box.

**Changes required.**

#### 1. Python package scaffolding

`src/study_tutor/` package. `pyproject.toml` with `[providers]` extra per SR-04. `uv`-based install. AGENTS.md at repo root declaring boundaries (ALWAYS/NEVER/ASK). `.env.example` per SR-06. `.mcp.json` pattern copied from specialist-agent. `roles/tutor/role.yaml` defining the tutor role (single role; multi-role dispatch is Phase 3 — see DEC-05 on multi-subject as post-hackathon).

**Scaffolding reuse source.** Copy directly from `specialist-agent/`: `pyproject.toml` shape, `src/` layout, `roles/` directory, `.env.example`, `AGENTS.md`, `.mcp.json`. Adapt names (study-tutor, tutor role), strip architect/product-owner-specific content.

#### 2. Ollama-backed LLM client

`src/study_tutor/llm/client.py` that routes based on `AGENT_MODELS__REASONING_MODEL` per SR-03:
- `local` → Ollama endpoint on GB10 (existing, default for Phase 0)
- `bedrock` → AWS Bedrock Custom Model Import (Phase 1 addition; Phase 0 stub that raises NotImplementedError)
- `openai`, `anthropic`, `gemini` → API providers (present in pyproject extras but not expected on the tutor's critical path; available for Coach if it runs on a different provider than the Player)

**Reuse source.** `specialist-agent/src/specialist_agent/llm/client.py` provider map, adapted for Ollama as primary target.

#### 3. MCP adapter

`src/study_tutor/mcp/adapter.py` exposing four MCP tools per SR-07 classification:
- `tutor_start_session` (long-running, returns session_id)
- `tutor_turn` (sync, < 30s target)
- `tutor_session_status` (sync, polls session state)
- `tutor_session_end` (sync, triggers async Graphiti write in Phase 1)

Phase 0 implementation is a thin harness over a single Ollama call per turn. No Graphiti (Phase 1), no Coach (Phase 1), no gamification (Phase 2). The session is an in-memory dict keyed by session_id; session state does not persist across MCP server restarts in Phase 0.

**Reuse source.** `specialist-agent/src/specialist_agent/mcp/adapter.py` — the `_start_po_session()` / `_run_po_session()` fire-and-forget pattern maps directly to `_start_tutor_session()` / `_run_tutor_session()`.

#### 4. Bash MCP wrapper

Bash wrapper at `scripts/mcp-wrapper.sh` following the specialist-agent pattern: `set -a && . /absolute/path/.env && set +a && export AGENT_MODELS__REASONING_MODEL=local && exec /absolute/path/.venv/bin/study-tutor serve --role tutor --transport stdio`. Reference `claude_desktop_config.json` snippet in README per SR-02.

#### 5. CLI entrypoint

`study-tutor serve --role tutor --transport stdio` and `study-tutor serve --role tutor --transport http` (http deferred to Phase 1 or later). Minimal `--help` output, banner to stderr per SR-01.

---

### FEAT-PO-003: Bring-Your-Own-Sources Public Repo Packaging

**Problem.** The fine-tuning training data was generated from commercially purchased Mr Bruff PDFs; those cannot ship in the public repo. The AQA past papers / mark schemes / examiner reports that have been downloaded cannot ship either (explicit AQA prohibition). The ChromaDB collection, `train.jsonl`, and fine-tuned adapter also cannot ship. But the hackathon requires a public code repository. The pipeline has to be open while the data stays private.

This is the "pipeline is open, data is private" strategy articulated in `copyright-training-data-analysis.md` §4.

**Changes required.**

#### 1. `README.md` that carries the submission narrative

Not a stub. The Phase 0 README is the primary document a hackathon judge reads. Structure:
- **What this is** — one-paragraph product description
- **Why it exists** — Lilymay, Year 10, real GCSE English prep, on-device privacy
- **Architecture in one diagram** — three-layer architecture (fine-tuned behaviour + RAG knowledge + student model), with Phase 1 and Phase 2 pieces labelled
- **Pipeline overview** — training data generation (agentic-dataset-factory), fine-tuning (Unsloth + GB10), deployment (Ollama + MCP + Bedrock as Phase 1 target)
- **Bring your own sources** — explicit section explaining what goes in `domains/gcse-english/sources/` and why the repo doesn't include them
- **Provenance and copyright posture** — summary of the copyright policy: AQA specifications acceptable, assessment materials not, Mr Bruff purchased and transformed through three layers, no redistribution of any copyrighted source
- **What's public vs private** — table matching `copyright-training-data-analysis.md §4.1` and §4.2
- **Quick start** — clean-machine walkthrough (venv install with `[providers]` extra, `.env.example` copy, ChromaDB seed from user-provided sources, Ollama serve the fine-tuned model if available locally OR point at Bedrock once Phase 1 adds that path, claude_desktop_config.json snippet, smoke-test MCP tool call)
- **Roadmap** — Phase 1 and 2 summary (Graphiti student model, DeepAgents harness with Coach, gamification engine, dashboard, Reachy integration)
- **Status** — what's working today vs what's roadmap

#### 2. `domains/gcse-english/sources/README.md`

The "bring your own sources" instructions. Explicit list of what to purchase or download (Mr Bruff PDFs as the tested path; CGP, York Notes as alternatives), how to place them, how to run ingestion. Acknowledges that the first fine-tuning run used Mr Bruff specifically.

#### 3. LICENSE decisions

`LICENSE` file at repo root. Apache 2.0 for the code (matches the hackathon's Gemma 4 Apache 2.0 base model licensing and most of the ecosystem). Documentation at repo root explaining that the fine-tuned model weights are NOT covered by this repo license and are not distributed.

#### 4. `.gitignore` hardening

Explicit `.gitignore` entries for `domains/*/sources/*.pdf`, `chroma/`, `chroma_data*/`, `output/train.jsonl`, `*.gguf`, `models/`, `~/fine-tuning/`. CI-enforceable if a pre-commit hook is added (nice-to-have, not required for Phase 0).

---

### FEAT-PO-004: AWS Bedrock Custom Model Import Path (validation only)

**Problem.** GB10 has a sequential workload queue during the build (study-tutor subject expansion → study-tutor re-fine-tune → architect-agent fine-tune for DDD). The tutor cannot depend on GB10 availability for demo week. Moving inference to AWS Bedrock Custom Model Import — already flagged in Rich's memory as a Phase 2 deliverable — validates an inference path that scales to zero, removes the GB10 dependency, and de-risks 16 May DDD overlap entirely.

Per DEC-07, this moves from Phase 2 to **the end of Phase 0 or early Phase 1** to free GB10 for the training sequence. Including it in Phase 0 scope here because the infrastructure setup (AWS account, IAM, Bedrock model import) is Phase 0 work; the actual validation test runs at the Phase 0 / Phase 1 boundary.

**Changes required.**

#### 1. AWS account and Bedrock enablement

AWS account with Bedrock Custom Model Import enabled in a region that supports it. IAM user or role with `bedrock:*` and `s3:*` on the specific bucket used for model upload. S3 bucket for model artefacts.

#### 2. Model upload

Upload the existing GCSE English tutor's merged 16-bit weights (per memory: at `~/fine-tuning/output/gcse-tutor-gemma4-31b/`) to S3, then import into Bedrock as a custom model. Bedrock's Gemma 4 31B import path should work natively.

**Not in scope.** Training a new model for Bedrock. The existing model is sufficient for validation.

#### 3. Provider integration in the LLM client

Extend `src/study_tutor/llm/client.py` to route `AGENT_MODELS__REASONING_MODEL=bedrock` to the Bedrock custom-model endpoint using `langchain-aws` or direct boto3. Add `langchain-aws` to the `[providers]` extra per SR-04.

#### 4. Validation smoke test

A scripted test that makes a single inference request through each provider path (`local`, `bedrock`) and compares outputs for coherence. Not an A/B quality test — just "does the pipe connect."

#### 5. OpenWebUI pointed at Bedrock

Configure OpenWebUI on GB10 to point at Bedrock via an OpenAI-compatible proxy (LiteLLM is the simplest; OpenRouter if it lists Bedrock custom imports). One evening's configuration, not code. Lilymay's primary interface continues to work even when GB10 is training.

**Deferred to Phase 1.** Full A/B quality testing of Ollama vs Bedrock output. Cost monitoring and budget alerts.

---

### FEAT-PO-005: Technical Write-Up Scaffolding

**Problem.** The technical write-up is a required submission deliverable per the hackathon rules. Writing it in the final 48 hours is how submissions end up weak. Starting the write-up in Phase 0 with a living document, added to incrementally as each phase lands, produces a polished submission.

**Changes required.**

#### 1. `docs/submission/technical-writeup.md`

Living document with stubs for every section the final submission needs. Stubs are populated as the build progresses; by 10 May the document is feature-complete and only needs polish.

**Required section stubs (empty but titled, with one-line notes):**
- Problem statement (Lilymay, AI tutors, teenage engagement, privacy)
- Solution overview (three-layer architecture)
- Pipeline methodology (agentic dataset factory, Player-Coach, Unsloth)
- Fine-tuning specifics (Gemma 4 31B, LoRA, training data provenance)
- Architecture (Phase 1 Ollama + Phase 2 Graphiti + gamification)
- Gamification design (references `docs/gamification/design.md`)
- On-device deployment (GB10, Ollama, privacy story)
- Bedrock migration path (scale to zero, cost profile, demo-week reliability)
- Multi-subject expansion (architecture, not implementation)
- Copyright and provenance (references `copyright-training-data-analysis.md`)
- Evaluation (what we measured, what we didn't)
- Roadmap (Reachy, mobile, multi-subject)
- Acknowledgements (Pollen, Unsloth, Ollama, Anthropic for Claude, Google for Gemma, etc.)

#### 2. `docs/submission/demo-script.md`

Skeleton for the demo video script. Populated during Phase 2. Phase 0 stub captures the shape: 30s Open WebUI working today, 60s architecture reveal via MCP, 60s gamification story, 30s Reachy (live or pre-recorded depending on DEC-06 gate), 30s vision and roadmap. Total ~3.5 minutes.

#### 3. `docs/submission/video-outline.md`

Storyboard-lite. Scene by scene. Empty shell in Phase 0.

---

## Do-Not-Change

The following decisions are closed for Phase 0. They may be reopened only on material evidence per `decisions-log-2026-04-17.md §Revision policy`.

- **The six parity surfaces from LES1 are load-bearing.** No feature skips SR-01 through SR-07.
- **No Dockerfile in Phase 0.** Venv-only install documented. SR-05 reactivates for Phase 1 or later.
- **No custom UI in Phase 0.** Open WebUI remains Lilymay's interface. Dashboard is Phase 2, generated via Claude Design, static HTML.
- **No Graphiti in Phase 0.** Student model is Phase 1 (FEAT-PO-004 in the roadmap; NOT the same numbering as Phase 0 FEAT-PO-004 Bedrock path).
- **No Coach in Phase 0.** Phase 0 MCP tutor_turn is a single LLM call; Phase 1 adds Coach quality monitoring.
- **No gamification state in Phase 0.** Economy is documented in `docs/gamification/design.md`; state engine is Phase 2.
- **No Reachy work in Phase 0.** Separate conversation starter drafted. Scheduled work gated to 4 May per DEC-06.
- **Single role (tutor) only.** Multi-role dispatch infrastructure present (copied from specialist-agent) but unused. Multi-subject expansion is Phase 3 / post-hackathon.
- **Ollama as primary Phase 0 runtime.** Bedrock is validation in parallel; not a Phase 0 cutover.
- **Provider resolution at the factory per SR-03.** No handler hard-codes a provider.

---

## Success Criteria

Phase 0 is complete when all of the following are true:

1. **Clean-machine walkthrough succeeds.** A fresh MacBook (or a clone of the test VM) can clone the repo, follow the README quick-start, bring their own sources, seed ChromaDB, point at an available fine-tuned model (Ollama or Bedrock), install study-tutor via `pip install -e '.[providers]'`, add the MCP server to Claude Desktop via the bash wrapper, and make a successful `tutor_turn` MCP tool call.
2. **Six parity surfaces green.** SR-01 through SR-07 all pass their acceptance criteria. Stream-split stdio test passes. Provider resolution via env var verified for at least two providers. `.env.example` contains no real-looking values. Every MCP tool's description matches its behaviour.
3. **AWS Bedrock validation passes.** A single `study-tutor` MCP `tutor_turn` call routes to Bedrock Custom Model Import and returns a coherent response, within 5× the latency of the Ollama path. OpenWebUI on GB10 configured to point at Bedrock via proxy; Lilymay's interface continues to work.
4. **Domain contract is authoritative.** `domains/gcse-english/GOAL.md` exists, covers AO1–AO6 with behavioural guidance, enumerates texts, specifies tutoring style, defines content boundaries. `docs/gamification/design.md` exists and publishes the full economy.
5. **Technical write-up scaffolding lands.** All three `docs/submission/*.md` files exist with stubbed sections.
6. **Lilymay's experience is unchanged or improved.** The existing Ollama + Open WebUI path continues to work throughout Phase 0. No regression in her ability to use the tutor for daily revision.
7. **Public repo passes human-review gate.** Rich can look at the repo cold and answer "would a judge take this seriously?" with yes. Specifically: README reads as a product pitch not a code dump, LICENSE clear, `.gitignore` hardens against accidental copyrighted-content commits, `.env.example` is safe to commit.

---

## Knock-on to Phase 1 and 2

Recording decisions here so they don't have to be re-made in Phase 1:

- **Graphiti student model** (FEAT-PO-004 roadmap) depends on the GOAL.md from Phase 0 FEAT-PO-001. Entity types will be `Student`, `Subject`, `Text`, `Topic`, `AssessmentObjective`, `Misconception`, `TopicConfidence` plus session episodes. Group IDs: `student:{id}`, `subject:gcse-english`.
- **DeepAgents tutoring loop** (FEAT-PO-006) upgrades Phase 0's single-LLM `tutor_turn` into a Player-Coach loop. The Coach uses the criteria skeleton laid down in Phase 0 FEAT-PO-001 item 3.
- **Session planner** (FEAT-PO-005 roadmap) reads from Graphiti (Phase 1) and writes back the planned session into the `tutor_start_session` handler created in Phase 0 FEAT-PO-002.
- **Gamification state engine** (FEAT-PO-007) consumes `docs/gamification/design.md` (Phase 0) and reacts to events emitted by the DeepAgents harness (Phase 1).
- **Dashboard** (FEAT-PO-009) consumes the session-export JSON produced by Phase 1 session-end handlers. Generated via Claude Design, static HTML, one evening in Phase 2.
