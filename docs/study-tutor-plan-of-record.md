# Study Tutor — PLAN OF RECORD (source of truth #2; the concrete roadmap)
## 2026-08-01 · living · DRAFT until Rich ratifies the lane order (ruling-queue item 1) · pairs with the mission ([`study-tutor-mission-statement-2026-08-01.md`](study-tutor-mission-statement-2026-08-01.md))

> **This is THE plan for the product. When something is decided or moves state, update THIS
> doc — do not write a new orphan doc the next session overlooks. ADRs, contracts, runbooks,
> RESULTS and research docs are INPUT; they get folded here. The software-factory programme
> plan lives in ai-transition (`software-factory-plan-of-record.md`); factory lane claims go
> there, product state lives here. Lane steps carry a status convention: mark a finished
> step `✅ DONE <date> (<receipt>)` in place.**

## The north star

**Lilymay — and then her close friends — really studying, across their subjects, grounded in
their own books, on a system whose privacy and legal posture is written down and true**
(mission S0 with S1–S3 behind it). Rich's framing on 2026-08-01: once multi-subject works
well, RAG is bottomed out subject-scoped, the AWS pilot with uploads exists, and the
copyright position is settled, "we have probably most of the MVP/v1 ready."

## Current state — the honest map (verified 2026-08-01, receipts named)

Hosts, cashed out once: **the spark** = the household DGX Spark inference/app box
(`spark-fcf6`); **the GB10** = the Dell DGX box, now returned to the software factory; **the
NAS** = the Synology box (`whitestocks`) holding durable state. All tailnet-only today.

| Piece | State | Receipt |
|---|---|---|
| Tutoring core (Player + async Coach + planner + quote verifier) | **LIVE** on the spark `:8100` (static-token "table" auth mode, voice ON) and `:8101` (Keycloak auth mode, voice OFF pending the Keycloak phone-flow proof) | `HANDOFF-study-tutor-full-encapsulation-spark.md` (2026-07-26) |
| Model serving | **LIVE** — `gemma4-tutor` (fine-tuned Gemma 4 26B-A4B) + coach + speech models + embedder on the spark's llama-swap `:9000`; the GB10 handed back to the factory (Reachy speech unit `:8765` excepted) | same handoff; `/opt/llama-swap/config/config.yaml` |
| Student model + gamification | **LIVE** — Postgres on the NAS `:5434`, nightly dumps; W1+W2 economy (33 achievements) settling per ADR-ARCH-030; real session receipted 2026-07-26 (`904ad0f`) | ADR-ARCH-030; `docs/gamification/design.md` §13.1 |
| App (Flutter, monorepo `app/`) | **Android device-walked** (sessions, voice tap-to-talk, streaming, sign-in, history, live robot mirror, gamification UI, settings). **iOS: compiles + hermetic-suite green only** (live walk pending). **Web: no boot claim** | `RESULTS-study-tutor-p2-live-acceptance-2026-07-05.md`; `app/README.md`; honest-iOS commit `29a320f` |
| Auth | **LIVE end-to-end** — Keycloak on the NAS `:8443`; server gate (KC-G2) and real-device gate (KC-G3) passed 2026-07-19; interim table mode retained for the robot | `HANDOFF-weekend-auth-voice-fable-window.md` §11 |
| Robot (Reachy "Scholar") | **⚠ CONFIRMED NOT re-pointed (Rich, 2026-08-01)** — the robot still targets the GB10, whose tutor stack was retired 2026-07-26, so the robot's `ask_tutor`/student-model path is presumed DOWN until the fleet-gateway URL flips to the spark `:8100` (same static bearer). The re-point is an operator act in the fleet-gateway repo/robot host | `HANDOFF-study-tutor-full-encapsulation-spark.md` operator item 3; Rich in-session 2026-08-01 |
| Live robot-session mirror | **SHIPPED 2026-07-31** — `turns?since=` delta read + SSE stream; `resume` stays active-only ("one verb per job"; the mirror lane's Stage-0 resume widening was reverted, `96baad2`) | `RESULTS-spark-live-robot-session-mirror-2026-07-31.md` |
| RAG / retrieval | **Code-complete, DEAD in prod** — the image lacks the `[rag]` optional dependency ⇒ `rag_disabled reason=chromadb_missing`; the English corpus (`gcse-english-v1`, 581 chunks, 3 texts) ships unused in the image; retrieval-off also idles the Coach revise loop | `Dockerfile:70`; `cli/rag_wiring.py`; TASK-RVP-001 |
| Multi-subject | **Mechanism decided + informally validated, not built**: ADR-TUTOR-MULTI-SUBJECT (Accepted 2026-05-05) — ONE fine-tune + per-subject prompts + per-subject corpora; 17/17 Open WebUI probes (raw transcript, unscored); ratified load-bearing 2026-07-19 (Rich — `study-room-cosy-progression.md` §2 line 32). Everything behavioural is English-only today | the ADR; `multi-subject-validation-{prompts,results}.md` |
| Contracts | Six verbs frozen (Rev 2); additive addenda through 2026-07-31; `SUBJECT_DEFAULT='english'` (a default, not a pin) | `API-session-http-binding.md`; `SUBJECT_DEFAULT.md` |
| Suites | 1634 hermetic python tests green (+1 named pre-existing failure: the `whitestocks`-string scope guard), 386 dart tests; the 35-test live contract suite last receipted green 2026-07-05 (re-run due — the app's 2026-08-01 `turnsSince` change realigned it) | mirror-lane run records 2026-07-31/08-01; p2 acceptance 2026-07-05 |

**Known contradictions to burn down (Lane 5):**
- `licensing.md` says the fine-tuned weights are "not distributed" but the Hugging Face
  upload happened (AWS research §1 License row / §6c); model identity also stale ("31B
  Dense" vs the real 26B-A4B).
- `docs/submission/technical-writeup.md` claims AQA mark schemes/examiner reports are in the
  RAG store — **false** (the corpus is primary texts only; `corpus.py`'s AQA refusal gate
  forbids exactly that) and law-4-violating as written; correct the writeup.
- **The multi-subject ADR's own RAG-source table lists mark schemes/past papers per subject**
  — it predates the hardened law 4 and must be amended to exclude assessment material;
  French/Spanish (specimen-paper-only specs) consequently have **no compliant corpus path**
  until other materials are acquired.
- `sources/README.md` §3.2 still documents the in-copyright deny-list dropped 2026-05-09
  (`1f728bf`).
- MCP adapter writes `subject=student_id` ('lilymay') while HTTP writes 'english' (or `''`
  when the client omits it) — parallel-session divergence between front doors.
- Root README + pyproject still describe an MCP-only English runtime.
- The 15s→90s turn-deadline change was never ratified against the contract's latency section.
- Citation anchors broken on 581/581 corpus chunks since 2026-05-10.

## The lanes

*Numbered by Rich's 2026-08-01 asks; ordered by execution priority. Each names the
measurable it moves and Rich's gate.*

### Lane 2 first — RAG bottomed out, subject-scoped *(moves S2; enables Lane 1's quality bar)*
The recorded sequencing rule stands: *grounding before subject expansion* (rag-grounding §5 —
"every subject added without grounding multiplies the hallucination surface").
1. **(1a — ungated, the plan's FIRST action)** Build the `--extra rag` image variant on a
   branch, measure the image-size delta and spark memory/cost, run the golden-quote smoke
   against it locally, and attach the receipt to ruling-queue item 2.
   **(1b — gated on Rich's go)** Redeploy with the extra; prove `event=rag_enabled` live +
   the smoke on the deployed host.
2. **Subject-scope the layer** — per-subject collections via the reserved `role_config` seam
   in `build_rag_providers` (or a subject metadata field — one design decision), subject-keyed
   primary-text registry, `session.subject` threaded into the coach-handover closure,
   per-subject ingest roots (`domains/<subject>/sources/`).
3. **Honesty constraints carried in:** selective retrieval stays (ADR-FLEET-002 — always-on
   RAG degrades the tutor); a **corpus-coverage check per subject** is mandatory (the
   partial-corpus degradation finding); AQA refusal patterns inherited at ingest AND
   retrieval; fix or explicitly defer the citation-anchor break.
   *Receipt: fabrication <5% on the golden-quote eval (the S2 frozen bar), per subject with
   a corpus.*

### Lane 1 — multiple subjects working well *(moves S1; Rich's ask #1)*
Eval-first, then plumbing, then content packs:
1. **Subject-suitability evals** (Rich, 2026-08-01: "we could do some further evals?" — yes):
   re-run the 17-prompt protocol **scored** (fix the Chemistry-preset labeling), and extend
   the existing blind eval harness (`scripts/eval/`, the 2026-05-18 runbook pattern) with
   per-subject golden sets — serving fine-tune vs base under subject prompts. This doubles
   as the overdue revisit of the 2026-05-18 result (base won 15–1 single-turn AND 2–0–1
   multi-turn, the fine-tune ahead only on the Socratic-stance dimension — yet the fine-tune
   serves). *Gate: Rich rules the serving story on the receipts, per subject.*
2. **Close the subject seams**: app subject picker (`SUBJECT_DEFAULT` becomes the fallback,
   as its §4 designed); server normalises omitted subject (today persists `''`); fix the MCP
   `subject=student_id` quirk or mark MCP superseded; `student-model` actually filters by
   its subject param; subject dimension on `topic_confidence`/chests/catalogs from the first
   migration (study-room §14: "a schema-day-one concern").
3. **Per-subject content packs**: prompts + Coach rubric + curriculum seed + assessment-
   objective framework per subject (only English AO1–AO6 is documented today). Pick the
   first second subject by **compliant corpus availability** (History if suitable guides are
   owned — operator-confirmed only, no repo receipt names them; French/Spanish are blocked
   by the specimen-paper-only gap noted above).
   *Receipt per subject: the S1 parity definition, ending in a real session.*

### Lane 4 — the copyright/fair-use posture *(gates Lane 3's uploads; S3 rung 1 — ratifies before the residency rung)*
A decision doc, not code. Update `copyright-training-data-analysis.md` (2026-04-12 — UK-only,
purchased-materials + household-deployment only; silent on uploads, cloud hosting, and
multi-account tenancy) into a **posture ADR covering the pilot**: user-uploaded scans of
user-owned books, per-account private retrieval, cloud hosting — noting the US fair-use
ruling Rich cites while being honest that **UK law governs a UK pilot** (no fair-use
doctrine; s29A is non-commercial text/data-mining; the private-copying exception was quashed
in 2015), so the posture leans on per-account privacy, no redistribution, and
user-owns-the-source — the same shape as `rag-grounding-design` §1a posture 2, deliberately
deferred then. Resolve the standing contradictions in the same pass (HF weights vs
licensing.md; the deny-list docs; the technical-writeup false claim; the multi-subject ADR's
RAG-source table). AQA exclusion is untouchable (mission law 4). *Gate: Rich ratifies the
posture ADR.*

### Lane 3 — AWS deployment + the friends pilot with uploads *(moves S3; Rich's ask #3)*
The spine is ADR-ARCH-029 (Phase 3 = same stack, AWS eu-west-2) + the costed 2026-07-06
research (Bedrock Custom Model Import dead ×3; default = EC2 g6.xlarge London + llama-swap,
~$70–75/mo, spot ~$30; first move = the ~$5 one-evening spike). Order:
1. **The residency/governance ADR** (supersedes ADR-ARCH-015's household scope): eu-west-2,
   encryption, parental-consent record, erasure path — "this surface IS the portfolio
   artifact" (ADR-029 D4). *Gate: Rich ratifies — minors' data is the whole question. Per
   the S3 ladder, this ratifies only after Lane 4's posture ADR has.*
2. **The multi-user ADR**: pilot accounts on the existing `student_id` partition + Keycloak
   provisioning (both already multi-user-shaped); concurrency posture (the spark cannot
   serve a concurrent cohort — cloud sizing is part of this); voice-on-Keycloak-mode flip.
3. **The spike → deploy**: reuse is high (stateless app container, compose, alembic
   migrations, realm-as-code, the model file + llama-swap config verbatim); new =
   TLS/domain (app base-URL rebuild, cleartext-HTTP fix), hosted Postgres/Keycloak, secrets
   (extend the `sops` encrypted-config pattern), and the fine-tune-vs-stock serving decision
   from Lane 1's evals (it swings pilot economics).
4. **The upload surface** (after Lane 4 ratifies): a page — vehicle to decide: Flutter web
   (currently no boot claim) vs a minimal separate web page — for scanned study
   guides/books; the proven docling scan→markdown pipeline (standard + vision modes) becomes
   a service instead of an operator ritual; **per-account corpus tenancy** (per-user
   collections; the global primary-text registry gets user/subject keying); quota + format
   guards.
5. **The pilot**: friends provisioned (runbook exists), first external session = S3 top rung.

### Lane 6 — robot app distribution & switching *(moves S0's robot leg; added by Rich 2026-08-01)*
Rich's ask, same day as this plan: the **Reachy Mini desktop or mobile app should be able to
download the study-tutor custom app onto the robot, so the user can switch between the study
tutor and other robot apps** — the tutor becomes one installable app among several rather
than a hand-deployed integration.
1. **Immediate, independent of the rest:** execute the GB10→spark re-point (the robot's
   tutor path is down until then — see the state map) and smoke `ask_tutor` live.
2. **Investigation/design pass first, build second:** how Pollen's Reachy Mini app
   packaging/distribution actually works (the app hub/store mechanism and its
   install-from-companion-app flow); what the Scholar integration in fleet-gateway must
   become to be a switchable, installable app (clean install/uninstall, config carried with
   the app — backend URL + bearer, voice pins); where the work lands (mostly the
   fleet-gateway repo + robot host, with study-tutor's surface unchanged — the contracts
   already serve any client that authenticates). *Gate: the design pass comes back to Rich
   before any build.*

### Lane 5 — truth & hygiene *(moves S4; cheap, continuous)*
1. **✅ DONE 2026-08-01**: root `CLAUDE.md` now routes every session to the two sources of
   truth (this was the pair's own enforcement gap — closed the day the pair was drafted).
2. Burn down the Known-contradictions list above, plus: known-issues.md (stale at
   2026-05-18 — adopt the `whitestocks`-string suite failure, the fixture-ordering artifact,
   the mirror advisories); ARCHITECTURE.md model identity + the missing ADR-ARCH-030 index
   row; the voice wave/gate ledger's formal closure; app/README's stale `voiceTurnStream`
   note. Re-run the live contract suite against the spark (the 35-green receipt is from
   2026-07-05, pre-`turnsSince`).
3. **Push the local Stage-0-revert commits** (`96baad2` + successors — origin is
   self-contradictory until then). The fleet-gateway re-point moved to Lane 6 step 1
   (confirmed outstanding, Rich 2026-08-01).

## Sequencing, in one line

Lane 2 step 1a (the RAG image receipt — ungated), Lane 1 step 1 (evals), and Lane 6 step 1
(the robot re-point — the one thing currently *broken*) start immediately and in parallel;
Lane 4 (a writing lane) runs alongside and **its ADR ratifies before Lane 3's residency ADR
does**; Lane 3 must not touch student data in the cloud before both are ratified; Lane 6's
app-distribution work waits on its design pass; Lane 5 runs continuously.

## Rich's open ruling queue (the genuine owner acts, consolidated)

1. ~~Ratify the mission~~ **✅ RATIFIED 2026-08-01 (Rich, in-session)**; ratify this plan's
   lane order — the plan flips from DRAFT on his word.
2. Lane 2: the `[rag]` extra go (the 1a receipt arrives attached).
3. Lane 1: the serving ruling once the subject evals land (fine-tune vs base, per subject).
4. Lane 4: the copyright posture ADR.
5. Lane 3: the residency/governance ADR + multi-user scope + upload vehicle (web vs in-app).
6. Lane 6: the robot app-distribution design pass (comes back to him before build).
7. Housekeeping: push the Stage-0-revert commits (GitKraken or register the spark's SSH
   key); execute the fleet-gateway re-point (Lane 6 step 1); ratify-or-revert the 90s
   deadlines.

## Standing rules (how work runs here — already the convention, now written)

Orchestrated-build-playbook lanes with the owner's three acts (spec word / gate tap / merge
word); the builders' PREFLIGHT names the binding docs + fences verbatim; broker isolation
standing (build lanes never touch the NATS message broker — operators running runbooks may);
coaches verify by driving; coordinator review before anything is pushed; frozen-contract
discipline for anything app-facing (additive or re-pin, nothing else); evals blind and
pre-registered; claims carry receipts; sessions end by updating THIS doc.

## Named deferrals (parked on purpose — not silently)

The Study Room (Lilymay's own design — coins/rooms/pets/shop; needs contract Rev 3, a
navigation shell, and the art pipeline; build order coins+shop+bedroom per the designer);
Boss Battles / daily challenges / weekly quests (designed, promised by live unlock gates,
unbuilt) and the 7 content-gated achievements behind them; the ~150-word voice-mode reply
cap (Option C of the TTS investigation) + the 1.7B TTS trial; the iOS attended walk;
token-streaming ledger closure (voiceTurnStream is wired — close TASK-STREAM-001's record);
Reachy `celebrate_achievement` conformance confirmation; NATS fleet surface disposition
(live transport or formally dormant); the hackathon-era FEAT-PO roadmap IDs (historical
numbering only).

---

*Update rule: edit the lane step or cell in place, not the chat history. If this document is
stale at a session start, that is itself a Lane 5 finding. Grounded in a 2026-08-01
eight-area receipted review of this repo (docs, git history, code), adversarially critiqued
before commit; the named receipts above are the evidence trail.*
