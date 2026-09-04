# HANDOFF — full estate pickup (written for Codex or any successor agent)

**Written:** 2026-09-04, by the Claude spark master session that ran the 2026-08-07 →
2026-08-14 arc, at the weekly usage limit. **State below was last VERIFIED 2026-08-14**
— weeks have passed; re-verify everything marked ⟲ before acting on it.
**Machine:** this file lives on the spark (`spark-fcf6`), the household DGX Spark that
serves the live tutor. Repos live under
`/home/richardwoollcott/Projects/appmilla_github/`.

---

## 0. Non-negotiable ground rules (read before any act)

1. **Two sources of truth** (root `CLAUDE.md` routes you): the mission
   (`docs/study-tutor-mission-statement-2026-08-01.md` — the laws S0–S4, binding) and
   THE PLAN (`docs/study-tutor-plan-of-record.md` — the current honest state, updated
   IN PLACE, never a new orphan planning doc). Sessions end by updating the plan cell
   they moved.
2. **The owner's acts are exactly three** — Rich's spec word, gate tap, merge word.
   **NEVER raise a PR — he works solo; merge word → direct merge to main + push**
   (he corrected this explicitly; it's in Claude's memory dir too).
3. **Frozen contract:** `docs/design/contracts/API-session-http-binding.md` §7 — the
   six session verbs are frozen; additive or re-pin, never silent edits.
4. **Broker isolation:** build lanes NEVER touch NATS (no `nats://`, no `:4222`).
5. **Secrets are BINDING** (`SECRETS.md`): no credential value ever enters a repo;
   env files are gitignored; the fleet vault is sops+age.
6. **Hermetic-first:** `uv run pytest -m "not integration and not live and not
   keycloak" -q` green before any deploy. Live surfaces are attended, human-gated.
7. **Receipts, not claims** (law 8). Evals are blind + pre-registered. AQA assessment
   material is excluded absolutely (law 4).
8. **Deploy ritual** (proven repeatedly): active-session psql check → hermetic green →
   image build + rollback tag → compose recreate both projects → healthz + boot-log
   events (`rag_wired`, `voice_services_wired`) → live probe as the `suite-runner`
   identity (token in `deploy/http/.env` — NOT shell-sourceable, parse with python).

## 1. What the 08-07 → 08-14 arc delivered (all merged + pushed; receipts named)

- **Verifier fail-open FIXED + DEPLOYED** (study-tutor merge `6b50821`, deploy
  2026-08-07, rollback tag `pre-track-a-20260807`): correct quotes no longer abort
  verification; streaming final pass fails closed; golden-quote fabrication harness
  at `scripts/eval/` + `RUNBOOK-golden-quote-fabrication-eval.md` (pre-registered
  <5% bar). Track B (restore citation anchors) DEFERRED with costs (runbook §6).
- **ADR-ARCH-033 (residency/governance, eu-west-2) + ADR-ARCH-034 (multi-user)
  RATIFIED** 2026-08-13 with all five rulings (UK-only; hold serving; sops; ≤6
  accounts on-demand; documented backup-roll). Supersession notes landed on
  ADR-015/028/014. Hand-check receipts: `docs/research/ICO/` (5 PDFs). S3 rung 2
  climbed. Hyper Backup was found NEVER INSTALLED — the durability gap + exit path is
  the known-issues "Durability" entry (STILL OPEN ⟲).
- **Robot re-pointed to the spark** (text path verified end-to-end on the Pi,
  2026-08-13). The GB10 speech unit is GONE and the **GB10 is ruled factory-only**;
  the robot speaks again only via the Scholar app build (brief ready, below).
- **Lane 6 gate CLOSED** (all seven E-rulings in the design doc §E) and **the upload
  vehicle RULED: minimal separate same-origin page** (ruling-queue item 5 fully
  discharged). Flutter-web boot claim banked (`RESULTS-mac-flutter-web-boot-2026-08-13.md`
  — works but needs server CORS; diagnostic only).
- **The three-instrument eval is FINAL** (spot-check ok, Rich 2026-08-14):
  `fleet-evals/multisubject/runs/2026-08-13-multisubject-v2/RESULTS-multisubject-2026-08-13.md`
  — **base beats the fine-tune on all three instruments** (pairwise 106/7/1;
  criterion 73.9% vs 67.0%; multi-turn 20/0 incl. the engagement dimension). Protocol
  v2+v3 registered; judges = fresh-context Claude subagents + local Qwen (zero API
  spend). The autopsy + comeback recipe: the STORY doc (below).
- **fleet-evals venue merged** to `guardkit/fleet-evals` main (`7cad33d` + later
  commits): n-way harness, 8-subject golden sets (136 items), 24 multi-turn
  scenarios, per-subject rubrics with real AQA AO structures (AO fact-check applied),
  criterion producer, local judges with the Qwen `--no-thinking` +
  LaTeX-backslash-repair + progressive-write lessons baked in.
- **Dataset factory Stages 1–2 MERGED** (`agentic-dataset-factory` merge `110120a`):
  two-window batched-legs batch mode (teacher window with the fleet DRAINED per the
  DeepSeek two-spark runbook → operator boundary → Coach window) + the per-sample
  fabrication gate (TASK-G4D-006's two real fabricated quotes are must-catch
  fixtures). Sequential mode byte-compatible; active coach/recruiter lanes untouched.
- **YouTube story source:**
  `fleet-evals/multisubject/docs/STORY-when-your-finetune-loses-2026-08-14.md`.
- **Scholar robot app build brief READY** (not started):
  `docs/runbooks/HANDOFF-fleet-gateway-scholar-app-build.md`.
- **Dataset regen brief** (Stages 3–4 remain):
  `docs/runbooks/HANDOFF-dataset-factory-gcse-regen.md` — Stage 3 is the
  MULTI-SUBJECT GOAL refresh; Stage 4 the attended 50-target pilot.
- **Base-in-loop trial runbook PREPARED, NOT RUN:**
  `docs/runbooks/RUNBOOK-base-in-loop-trial.md` (the one-line
  `TUTOR_LOCAL_MODEL=gemma4-base` flip; Rich pre-registers his feel criteria first).

## 2. ⚠ Loose ends from the interrupted last session (VERIFY FIRST on pickup)

1. **⟲ The llama-swap keepalive timer may still be STOPPED.** Rich chose "restore
   now" (2026-08-14) but the actual `sudo systemctl start llama-swap-keepalive.timer`
   was never confirmed executed — my last check showed the timer INACTIVE. I manually
   warmed `gemma4-tutor` (it answered), but without the timer the fleet does not
   self-heal. **Check:** `systemctl is-active llama-swap-keepalive.timer`; if
   inactive, Rich runs the start command; then `curl -s localhost:9000/running`
   should show the tutor set resident. This closes the eval runbook's Gate 5.1.
2. **⟲ Three questions were put to Rich and never answered** (the session was
   interrupted mid-ask): (a) the **spec word for the Scholar app build**; (b) **which
   subject to scan first** (each scan lights that subject's RAG corpus AND unlocks
   its dataset generation — plan rule: scan effort × Lilymay's need); (c) the
   **Hyper Backup walk-through** (~15 min with the T5 SSD; the exit path is written
   in the known-issues Durability entry). Re-ask or take his words directly.
3. **⟲ The base-in-loop trial** — prepared, awaiting Rich filling §0 criteria and
   running 3–4 attended sessions. Its outcome + the final eval = the **serving
   ruling** (ruling-queue item 3), the oldest open question. If base serves, the
   ADR-031 D4.2 licence conflict becomes moot FOR SERVING.
4. **⟲ Whether the fleet-gateway session ever committed its re-point changes**
   (4 files/7 lines, tests green — Rich was to relay "commit"). Check that repo's
   git log on its host (NOT clonable from here; the Pi holds the deployed copy).
5. **⟲ fleet-memory debt:** the `fleet_memory` MCP door was OFFLINE the whole arc
   (declared per playbook amendment 8) and came online only at the very end. NONE of
   the arc's decisions/build_outcomes were written to fleet-memory. If your harness
   has the door (`mcp__fleet_memory__memory_write_payload`, project id underscored:
   `study_tutor`), write `adr` payloads for: ADR-033/034 ratification + rulings, the
   GB10-factory-only ruling, the upload-vehicle ruling, the Lane 6 E1–E7 rulings, the
   serving-eval verdict, the Lane 7 teacher/batch directives. Otherwise note the debt
   forward.
6. **Claude-side memory** (`~/.claude/projects/-...-study-tutor/memory/`) holds the
   no-PRs rule and spark operational gotchas — Codex should mirror what it needs into
   its own memory system.

## 3. Priority queue for the next sessions (my recommendation, highest leverage first)

1. **Fleet restore check** (item 2.1 — five minutes, closes a dangling gate).
2. **The base-in-loop trial → the serving ruling.** Cheapest decisive evidence in the
   programme. Then fold the ruling into the plan (ruling-queue item 3) and, if base
   wins, flip the serving default permanently (env line + plan + a dated note).
3. **Scholar app build** (fleet-gateway lane; brief self-contained). The robot is
   MUTE until stage 2 lands. Needs Rich's spec word only.
4. **Scans → ingest per subject** (Lane 1 step 3): each scan = docling (standard +
   vision modes, proven) → `domains/gcse-<subject>/sources/` →
   `uv run python scripts/ingest_corpus.py --subject <slug>` → redeploy for RAG.
   English's store exists; every other subject unlocks on its scan.
5. **Dataset factory Stages 3–4** (brief §Stage 3–4): the multi-subject GOAL refresh
   is buildable NOW; the pilot needs scans + a scheduled DeepSeek window
   (`dgx-spark/RUNBOOK-deepseek-v4-flash-0731-two-spark.md` — NOTE: that runbook
   DRAINS the fleet, the live tutor is DOWN during teacher windows; schedule around
   Lilymay). Also run the one-off fabrication-gate census over the three old GCSE
   output dirs (ruled: census then archive).
6. **Hyper Backup** (known-issues Durability — Rich's 15 minutes).
7. Then the wider plan: Lane 3's cloud spike (~$5, unblocked since ratification),
   the upload page build (ruled vehicle), Lane 7's fine-tune re-run once the dataset
   exists (bar: beats base on all three instruments AND in the loop).

## 4. Operational gotchas a new agent WILL hit (learned the hard way)

- **Test counts move with the `[rag]` extra**: the ingest-corpus test module only
  collects when chromadb is importable. 1733/0 without, 1749/0 with (both green,
  post-arc). Don't chase the delta.
- **`data/chroma/` is a REAL production build input** (gitignored, in-repo). Never
  write to it; read via sqlite `immutable=1`; serve-boot tests are guarded by a
  conftest `CHROMA_PERSIST_DIR` backfill (a caught leak — see known-issues, closed).
- **Worktrees:** factory `tests/test_dcl_prepare_sft.py` fails from worktree
  locations (sibling-path resolution) — environmental, not a regression.
- **deploy env files are docker-format, NOT shell-sourceable** (unquoted JSON values)
  — parse with python.
- **llama-swap:** `-watch-config` hot-reloads config (no restart needed for new
  seats); the `tutor` matrix set is the preload default; requesting `workhorse`/
  `coach`/`gemma4-base` EVICTS the tutor pair; keepalive revives it (when the timer
  runs). `gpt-oss-120b` is a GHOST seat (config exists, weights deleted).
- **Qwen as a judge/producer:** thinking starves the content channel — send
  `chat_template_kwargs: {"enable_thinking": false}`; repair LaTeX backslashes before
  `json.loads`; ALWAYS write progressively (append per item) so crashes lose nothing.
- **Provenance:** the served `gemma4-tutor` GGUF is byte-verified as the 2026-04-18
  fine-tune (GB10 sha `675424b0…3144`); `gemma4-base` download sha-verified
  (`f2c28b3d…`); five different fine-tunes on the GB10 share the same filename —
  ONLY checksums identify these artefacts.
- **The GB10 is factory-only** (ruled): no study-tutor anything on it, ever again.
- **Live probes** use the `suite-runner` identity (never `token-lilymay`); end any
  session you start.

## 5. Rich's standing words still owed (ask, don't assume)

Spec word (Scholar app) · first-scan choice · Hyper Backup quarter-hour · base-trial
criteria + sessions → the serving ruling · Stage-4 pilot gate tap (factory) · merge
words as lanes complete. All of his ruling-queue history is in the plan's "Rich's open
ruling queue" section — keep it current.

---

*Everything in this handoff has a receipt in git. When in doubt: `git log --oneline`
across study-tutor, fleet-evals, and agentic-dataset-factory for 2026-08-07..14 tells
the whole story, and the plan of record is the map. Leave it truer than you found it.*
