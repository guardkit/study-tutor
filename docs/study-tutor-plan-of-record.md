# Study Tutor — PLAN OF RECORD (source of truth #2; the concrete roadmap)
## 2026-08-01 · living · **RATIFIED — Rich, 2026-08-01 ("approved", in-session): the lane order is the plan of record** · pairs with the mission ([`study-tutor-mission-statement-2026-08-01.md`](study-tutor-mission-statement-2026-08-01.md))

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

**Lilymay is the primary use case** — the win is her achieving better results and actually
enjoying her final school year with it (Rich, 2026-08-01). **Dulcie** (her sister, Year 8
from September 2026, own phone + own Reachy Mini) is the second in-house student — KS3-level
content, so subject packs carry a level dimension when hers land (mission dated note 1).

## Current state — the honest map (verified 2026-08-04, receipts named)

Hosts, cashed out once: **the spark** = the household DGX Spark inference/app box
(`spark-fcf6`); **the GB10** = the Dell DGX box, now returned to the software factory; **the
NAS** = the Synology box (`whitestocks`) holding durable state. All tailnet-only today.

| Piece | State | Receipt |
|---|---|---|
| Tutoring core (Player + async Coach + planner + quote verifier) | **LIVE** on the spark `:8100` (table auth) and `:8101` (Keycloak; voice OFF pending the Keycloak phone-flow proof). `:8100` capabilities, each live-proven: **verified streaming voice** (ADR-ARCH-027 as ratified — per-sentence quote-verification before tokens are shown/spoken/persisted, streamed TTS; transcript ~0.2s, first spoken sentence ~3s), **one-active (b) session semantics** (`resume_if_active:false` = end-then-create with settlement; structural via partial unique index `session_one_active_idx`, migration head `346cd366b66e`; the MCP door RESUMES — this and the concurrency-test rewrite were the build's two flagged judgment calls, **both BLESSED by Rich 2026-08-04**), and the **incremental think-filter** (reasoning can never stream to the learner). The 2026-07-26→08-03 silent voice outage (empty `STT_MODEL`/`TTS_MODEL` falling back to dead GB10-era aliases) was found by the live suite and fixed same day; `VoiceConfig` now fails loud at boot on empty model names | `HANDOFF-study-tutor-full-encapsulation-spark.md` (2026-07-26); verified-streaming deploy `513bc70` + prod WS smoke 2026-08-03; (b) build `19a0211` + `HANDOFF-spark-double-active-server-build.md` (2026-08-04); voice env fix `1595b68`; fail-loud + scoped-reset `6d1c8e5`; verifier fail-closed deploy 2026-08-07 (merge `6b50821`, rollback `pre-track-a-20260807`, live probe 0 exceptions) |
| Model serving | **LIVE** — `gemma4-tutor` (fine-tuned Gemma 4 26B-A4B) + coach + speech models + embedder on the spark's llama-swap `:9000`; the GB10 handed back to the factory (Reachy speech unit `:8765` excepted) | same handoff; `/opt/llama-swap/config/config.yaml` |
| Student model + gamification | **LIVE** — Postgres on the NAS `:5434`, nightly dumps; W1+W2 economy (33 achievements) settling per ADR-ARCH-030; real session receipted 2026-07-26 (`904ad0f`) | ADR-ARCH-030; `docs/gamification/design.md` §13.1 |
| App (Flutter, monorepo `app/`) | **Android device-walked end-to-end against the LIVE spark (2026-08-03, Rich attended)**: sign-in, subject picker (visible-at-one), real tutor turns, **verified streaming signed off by ear** — sentence-by-sentence text with CONTINUOUS serialized audio, grounded turns on both `macbeth` and `an_inspector_calls` — history, live robot mirror, gamification UI, settings. Client hardening, all hermetically pinned: §7-conformant wire vocabulary + strand-proof batch fallback (`fa8d95b`), WS `/ws` path pin (`049f17c`), serialized stream-audio queue (`ffc83c9`), and **never-a-silent-resume** (Lilymay's 2026-08-03 finding; Rich's ruling shipped `69d7d5f` — topic disclosure card + Continue-vs-start-fresh sheet with chips + free text, server-truth gate, `resumed` backstop). **iOS: slice SIMULATOR-WALKED 2026-08-02** (iPhone 17 / iOS 26.2 — `integration_test/slice_walk_test.dart` drives the real composition root; **voice walk still pending**: mic permission + TTS audibility need human attendance). **Web: COMPILES + BOOTS, text walk PASSES against the LIVE spark (2026-08-13, headless Chromium 141)** — `flutter build web` needs no source change; sign-in (table flavour) → gamification card → start/resume → **one real tutor turn** → end/settlement all 200, no page errors. **But blocked in any real browser by one server-side gap: `:8100` serves no CORS** (preflight `OPTIONS` → 405, no `Access-Control-Allow-Origin`) — the walk required `--disable-web-security` to pass, so this is a **diagnostic** claim, not a shipping one; the app degrades gracefully ("Connection problem", no crash). **Voice broken on web** (blocked at `record.hasPermission()`; `dart:io`/`path_provider` in the voice/audio adapters compile to stubs and would fail at *runtime*, so "compiles" ≠ web-safe). **No wasm build** (`flutter_secure_storage_web` uses `dart:html`/`package:js`); **`flutter_appauth` has no web platform at all** (android/ios/macos only — the real Keycloak flavour cannot run on web as built) | `RESULTS-study-tutor-p2-live-acceptance-2026-07-05.md`; **web boot claim: `RESULTS-mac-flutter-web-boot-2026-08-13.md`**; `app/README.md`; honest-iOS `29a320f`; iOS walk `dd4bbed`; streaming sign-off + fix SHAs named in-cell (2026-08-03/04) |
| Auth | **LIVE end-to-end** — Keycloak on the NAS `:8443`; server gate (KC-G2) and real-device gate (KC-G3) passed 2026-07-19; interim table mode retained for the robot | `HANDOFF-weekend-auth-voice-fable-window.md` §11 |
| Robot (Reachy "Scholar") | **⚠ CONFIRMED NOT re-pointed (Rich, 2026-08-01)** — the robot still targets the GB10, whose tutor stack was retired 2026-07-26, so the robot's `ask_tutor`/student-model path is presumed DOWN until the fleet-gateway URL flips to the spark `:8100` (same static bearer). The re-point is an operator act in the fleet-gateway repo/robot host. **2026-08-04 made the flip safer**: the MCP door now resumes (a robot start joins — never ends — the learner's active session, blessed), and the voice model pins are explicit + fail-loud | `HANDOFF-study-tutor-full-encapsulation-spark.md` operator item 3; Rich in-session 2026-08-01; MCP resume `19a0211` |
| Live robot-session mirror | **SHIPPED 2026-07-31** — `turns?since=` delta read + SSE stream; `resume` stays active-only ("one verb per job"; the mirror lane's Stage-0 resume widening was reverted, `96baad2`) | `RESULTS-spark-live-robot-session-mirror-2026-07-31.md` |
| RAG / retrieval | **LIVE in prod as of 2026-08-02** (Rich's 1b go, executed same session): both spark containers boot with `event=rag_wired` (581-chunk `gcse-english-v1` re-embedded at 1024-dim to match llama-swap's `embed`, baked into the 1.4GB CPU-torch image); quote-retrieval smoke PASS 3/3 **inside the deployed container**; reranker instance-cached (~5.3s warm retrieval); rollback tags `pre-rag-20260802` kept. The Coach revise loop is un-idled. **2026-08-07 (Lane 2 step 3):** the golden-quote fabrication harness is **BUILT + first measured run executed** (29 generated responses through the real closure; receipt in `evidence/golden-quote-fabrication-eval/`); the step-3 design pass found the citation-anchor break had been failing the verifier **OPEN** since 2026-05-10 (a CORRECT quote raised inside the verifier and the whole turn released UNVERIFIED — law 3 unenforced on its own path) — **fixed in code** (merge `6b50821`: anchorless primaries degrade to verified-uncited, streaming final pass fails closed), **⚠ deploy pending Rich's word — prod still runs the fail-open build**; citation anchors themselves (Track B) explicitly deferred with costed options (fabrication runbook §6); subject-scoping done 2026-08-02 (step 2) | `RESULTS-lane2-rag-image-1a-2026-08-01.md` incl. the 1b postscript; deploy/http compose |
| Multi-subject | **Retrieval layer BUILT + LIVE 2026-08-02** (ADR-ARCH-032: per-subject collections, subject-keyed wiring/registry, closure coverage check, `--subject` ingest — deployed, `rag_subject_coverage` in prod boot logs); mechanism stays ADR-TUTOR-MULTI-SUBJECT (ONE fine-tune + per-subject prompts + corpora; 17/17 informal probes). **App picker + seams CLOSED 2026-08-02** (Lane 1 step 2 — `3a08bfa`: visible picker, `defaultSubject` now the fallback per SUBJECT_DEFAULT §4). **Still open for a real second subject:** content packs (Lane 1 step 3 — scans!), subject evals (Lane 1 step 1) | ADR-ARCH-032; the ADR; `multi-subject-validation-{prompts,results}.md` |
| Contracts | Six verbs frozen (Rev 2); additive addenda through 2026-07-31; `SUBJECT_DEFAULT='english'` (a default, not a pin) | `API-session-http-binding.md`; `SUBJECT_DEFAULT.md` |
| Suites | **Python hermetic 1749 passed / 0 failed (2026-08-07, post-Lane-5-wave** — the count includes the ingest-corpus module, which only collects when the `[rag]` extra is installed; one transient 11-error run under concurrent deploy load did not reproduce across two consecutive clean runs**)**; **dart 424 / 424 (2026-08-04)**; **live contract suite 49/49 (2026-08-04) — and ISOLATED**: it runs as the dedicated `suite-runner` identity with scoped authenticated resets and zero-leftover per-file cleanup (lilymay's rows byte-identical across a full run), and the promoted (b) end-then-create pin lives in the shared s5 body, asserting against BOTH the fake (hermetic) and the deployed `19a0211` build — fake and server agree by test. Grown 35→49 since 2026-07-05. The 2026-08-03 diagnostic arc (40/47 → 47/47 → 48/48) found-and-fixed voice dead-since-the-spark-move (`1595b68`), the WAV-declared-as-mp4 live fixture (`049f17c`), and the suite's own store pollution + whole-store reset wipe (isolation: server `6d1c8e5`, Mac `bb5a4fa`). Pre-2026-08-03 transcripts wiped by the old reset: **ACCEPTED LOSS** (Rich, 2026-08-04 — learner state untouched). **Lane 5's suite debt is CLOSED** | suite runs 2026-08-04 (spark 1709; Mac 424 + live 49/49); p2 acceptance 2026-07-05 |

**Known contradictions to burn down (Lane 5) — six of eight burned down
(five on 2026-08-01: the Lane 4 pass `5c1ddaa` + hygiene commits `5102874`/`10cc802`;
the sixth on 2026-08-02 via ADR-ARCH-032 D4):**
- ~~`licensing.md` weights claim + stale model identity~~ **✅ FIXED 2026-08-01** — §3/§4
  now record the deliberate HF upload + the Kaggle reason (per ADR-ARCH-031 D4); "31B
  Dense" → 26B-A4B with dated corrections; the dead Bedrock-CMI destination removed.
- ~~`docs/submission/technical-writeup.md` false RAG-store claim~~ **✅ FIXED 2026-08-01** —
  dated correction blockquote (store = 581 chunks of the three primary set texts only;
  AQA material never in any pipeline, refused by named code gates); original preserved as
  the historical submission.
- ~~The multi-subject ADR's RAG-source table~~ **✅ AMENDED 2026-08-01** — dated amendment
  section striking assessment material per law 4, naming the compliant source set
  (school-bought guides → docling). The French/Spanish no-compliant-corpus worry stays
  resolved in prospect (Rich, 2026-08-01: the family owns school-bought printed study
  guides across all Lilymay's subjects — scan → docling → corpora, Lane 1 step 3).
- ~~`sources/README.md` §3.2 deny-list ghost~~ **✅ FIXED 2026-08-01** — rewritten as
  "deny-list REMOVED 2026-05-09 (`1f728bf`)".
- ~~Root README + pyproject describe an MCP-only English runtime~~ **✅ FIXED 2026-08-01**
  (`5102874`) — README leads with the monorepo/HTTP reality, MCP demoted to a legacy
  section.
- ~~MCP adapter `subject=student_id` quirk + server persisting `''`~~ **✅ FIXED
  2026-08-02** (ADR-ARCH-032 D4, annexed into Lane 2 step 2 as load-bearing): the MCP
  door sends the shared default and the service normalises empty subjects at the
  boundary — all front doors now share one `(student, subject)` resume key. Six of
  eight contradictions burned down.
- ~~The 15s→90s turn-deadline change was never ratified against the contract's latency
  section~~ **✅ RULED: RATIFY (Rich, 2026-08-07, in-session)** — dated annotation on the
  binding (no re-pin); the binding never had a latency section, SR-07's 30s survives only
  as the orchestrator's log-only budget; full archaeology in
  [`BRIEF-90s-deadline-ratify-or-revert.md`](runbooks/BRIEF-90s-deadline-ratify-or-revert.md).
  **All eight contradictions are now burned down.**
- ~~Citation anchors broken on 581/581 corpus chunks since 2026-05-10~~ **RULED
  2026-08-07 (Lane 2 step 3):** the break's hidden consequence — the verifier failing
  OPEN on correct quotes — is **fixed in code** (deploy pending Rich's word); the
  anchors themselves stay **explicitly deferred as Track B** with costed options
  (`RUNBOOK-golden-quote-fabrication-eval.md` §6; B1 Standard-Ebooks Macbeth is the
  cheapest next win). Citation coverage reads an honest 0% until Track B lands.

## The lanes

*Numbered by Rich's 2026-08-01 asks; ordered by execution priority. Each names the
measurable it moves and Rich's gate.*

### Lane 2 first — RAG bottomed out, subject-scoped *(moves S2; enables Lane 1's quality bar)*
The recorded sequencing rule stands: *grounding before subject expansion* (rag-grounding §5 —
"every subject added without grounding multiplies the hallucination surface").
1. **(1a — ungated, the plan's FIRST action) ✅ DONE 2026-08-01**
   (`RESULTS-lane2-rag-image-1a-2026-08-01.md` in runbooks — attached to ruling-queue
   item 2). Built on branch `lane2/rag-image-1a`; quote-retrieval smoke PASS 3/3 on the
   full runtime path (there is no golden-quote harness to run — ADR-ARCH-022's
   fabrication eval was never built; the receipt defines the smoke it ran instead).
   Found: the extra alone would NOT light RAG in prod (768-dim shipped store vs the
   spark's 1024-dim `embed`; re-embed demonstrated, 581/581 in ~2 min); image cost
   measured at three points — naive 10.3GB → 5.28GB (cache-mount fix) → **1.4GB with
   the CPU-torch pin** (the CUDA wheels were dead weight; smoke passes on the CPU
   image) vs 443MB deployed; and the reranker is re-constructed per call (~6.6–9s/turn
   warm — a named pre-1b fix).
   **(1b) ✅ DONE 2026-08-02** (Rich's go given + executed same session — receipt
   postscript in the 1a RESULTS doc): store decision = bake (1024-dim re-embed in the
   image); reranker instance cache landed with tests (suite 1642 green); compose gained
   the RAG env block + persistent pre-warmed HF cache volume; both containers recreated
   on the 1.4GB image; `event=rag_wired` proven in both deployed logs; smoke PASS 3/3
   inside the deployed `:8100` container; rollback tags kept (`pre-rag-20260802`).
2. **Subject-scope the layer** — **✅ DONE 2026-08-02** (Rich's spec word in-session;
   ADR-ARCH-032; merge on main; suite 1666 green, 24 new tests). The design decision:
   **per-subject collections** (`gcse-<subject>-v1`; `gcse-english-v1` grandfathered — no
   re-ingest), discovered at boot with per-subject sidecars + a `rag_subject_coverage`
   boot log; `session.subject` threaded into the closure with the mandatory coverage
   check (`no_corpus_for_subject` — never cross-subject fallback); ingest gained
   `--subject` (derives root/collection/sidecar). Two Lane 1 seams annexed as
   load-bearing (ADR-032 D4): the MCP `subject=student_id` quirk fixed (all front doors
   now share one `(student, subject)` resume key) and server-boundary subject
   normalisation (`''` never persists). New-subject path is now content-only: docling →
   `domains/gcse-<subject>/sources/` → `ingest_corpus.py --subject <slug>` → redeploy.
3. **Honesty constraints carried in:** selective retrieval stays (ADR-FLEET-002 — always-on
   RAG degrades the tutor); a **corpus-coverage check per subject** is mandatory (the
   partial-corpus degradation finding); AQA refusal patterns inherited at ingest AND
   retrieval; fix or explicitly defer the citation-anchor break.
   *Receipt: fabrication <5% on the golden-quote eval (the S2 frozen bar), per subject with
   a corpus.*
   **Step-3 build ✅ DONE 2026-08-07** (merge `6b50821` + fix `fb325cf`; coach-gated
   workflow, adversarial revert-verify; hermetic 1747/0): the fail-open fix (Track A —
   anchorless-degradation + streaming fail-closed + ingest anchor gate, 11 regression
   pins), the harness (29 store-verified golden items incl. the four spec seeds verbatim,
   T1/T2 tiers, pre-registered runbook with the frozen <5% bar), and the **first measured
   run** (generated by the live `gemma4-tutor`): 3 quotes across 29 Socratic responses —
   n far too small for a rate claim; the one fabrication was the DESIGNED BAIT working
   (the model reproduced its known 2026-04-21 "mortal coats" misquote and the runtime
   verifier STRIPPED it — law 3 held); the Track A degraded-citation path proven live
   (`qf-poems-lone-level`). Next for a meaningful denominator: quote-eliciting prompts.
   **Deploy of the fix awaits Rich's word** (prod still fail-open). Track B (real
   anchors) deferred with costs (runbook §6).

### Lane 1 — multiple subjects working well *(moves S1; Rich's ask #1)*
Eval-first, then plumbing, then content packs:
1. **Subject-suitability evals** (Rich, 2026-08-01: "we could do some further evals?" — yes):
   re-run the 17-prompt protocol **scored** (fix the Chemistry-preset labeling), and build
   per-subject golden sets — serving fine-tune vs base under subject prompts, blind-judged.
   **Venue ruled 2026-08-01 (Rich): the multi-subject eval harness lands in the sibling
   `fleet-evals` repo** (the factory's judging estate), seeded from this repo's
   `scripts/eval/` + the 2026-05-18 runbook pattern — and doubles as YouTube content. This
   is also the overdue revisit of the 2026-05-18 result (base won 15–1 single-turn AND
   2–0–1 multi-turn, the fine-tune ahead only on the Socratic-stance dimension — yet the
   fine-tune serves). *Gate: Rich rules the serving story on the receipts, per subject —
   with Lane 7's refreshed candidates in the field.*
   **Seed ✅ BUILT 2026-08-07** (local sibling repo `fleet-evals`, 6 commits, 29 tests
   green, coach-gated; **no GitHub repo yet — creation is Rich's flag, no remote exists
   by fence**): the 10 scripts lifted with the five generalisations (n-way candidates
   for Lane 7, per-subject rubrics, run manifests stamping subject+preset+prompt-SHA,
   code-enforced pre-registration — runs REFUSE to start without a ratified PROTOCOL),
   the 7 subject prompts extracted byte-verbatim from the OWUI runbook heredocs with
   sha256 provenance, the 17 probes as data with **the Chemistry defect annotated**
   (both C1/C2 ran under the Biology preset — the ADR's 17/17 is honestly 15/17; dated
   amendment on ADR-TUTOR-MULTI-SUBJECT 2026-08-07), 2026-05-18 evidence as
   golden-master fixtures (published tables reproduced exactly), and 136 golden items
   across 8 subjects (english 24 + 7×16), each adversarially reviewed. **Scored run
   still blocked on:** the base-model seat on llama-swap (operator act), the served-GGUF
   provenance (no HF GGUF comparator exists — local sha256 pinned), and Rich's gate tap
   on the DRAFT protocol.
2. **Close the subject seams — ✅ DONE 2026-08-02 (backend on the spark, app leg on
   the Mac; all seams closed):**
   ~~server normalisation~~ + ~~MCP quirk~~ (ADR-ARCH-032 D4, via Lane 2 step 2);
   ~~subject dimension on the mastery schema~~ **✅ DONE** — migration `d5a9c2e7f814`
   run against the LIVE NAS store (safety dump first; backfill verified:
   `topic_confidence` keyed `(student, subject, topic)`, history/misconception
   subject-stamped, achievement NULLable per §14's W1-whole-student rule; future
   chest/catalog tables inherit the dimension from their own first migration, as §14
   wrote); settlement + completion bank mastery writes under the session's subject;
   ~~`student-model` filters by its subject param~~ **✅ DONE + LIVE-PROVEN** (english
   → real rows, french → `{}`, whole-student XP identical; binding §2.2 carries a
   dated in-place annotation, no re-pin). Suite 1671 green.
   ~~the app subject picker~~ **✅ DONE 2026-08-02** (the Mac session, per
   [`HANDOFF-mac-app-subject-picker.md`](runbooks/HANDOFF-mac-app-subject-picker.md)):
   `SubjectStore` (ChangeNotifier, AppScope-composed, session-scoped — Rich's call)
   with `defaultSubject` now the *fallback* exactly as SUBJECT_DEFAULT §4 designed;
   Home renders a **visible** SegmentedButton picker even at one subject (Rich's
   call 2026-08-02, overriding the handoff's hidden-at-one default) over the
   client-side `availableSubjects` const (`['english']` — a server-listed offer
   stays a later additive contract decision, once content packs exist); selection
   threads to `startSession` + the session screen + the progress read
   (`ProgressStore.updateSubject`, stale snapshot dropped so one subject's mastery
   never shows under another's selection); resume keeps each session's own subject.
   Receipts: commit `3a08bfa` on main (pushed); gates analyze clean + dart suite
   **400/400** (was 386; +14 hermetic tests — fallback, selection threading through
   the REAL AppScope composition [mutation-verified: an adversarial review caught
   the production path unpinned by the first pass], picker at one and two
   subjects) + `flutter build apk --debug` ✓; python seam
   `test_subject_default.py` 2/2 (`defaultSubject = 'english'` verbatim); zero
   contract-file edits. A French selection today honestly yields an empty mastery
   map and a no-corpus session — correct until Lane 1 step 3's content packs.
   Of the Mac-only extras: **the iOS walk RAN 2026-08-02 on Rich's word** (see the
   App row — slice walked on the iPhone 17 simulator via `integration_test`, picker
   visible and threading; voice remains the pending human-attended piece);
   **the device install + attended walk RAN 2026-08-03** (Rich's Samsung dev
   phone standing in for Lilymay's — real-transport APK, picker + real replies +
   audible voice against the live spark; her own phone still needs the install
   when she's back); **the live contract suite re-run RAN 2026-08-03 — 47/47**
   (see the Suites row; the two red runs before it surfaced and fixed real
   deployment/app defects — voice env, WS path, lying fixture).
   Still open: subject on `topic_confidence` *reads* the planner ranks over
   (deliberately unfiltered — whole-student until the content-pack lane decides
   per-subject planning).
3. **Per-subject content packs**: prompts + Coach rubric + curriculum seed + assessment-
   objective framework per subject (only English AO1–AO6 is documented today).
   **Corpus source ruled 2026-08-01 (Rich): the family owns printed study guides, bought
   from the school, across ALL Lilymay's subjects** — scan → docling (standard/vision
   modes, the architect-fine-tune precedent) → per-subject corpora. Every subject now has a
   law-4-compliant corpus path; pick the first second subject by scan effort + Lilymay's
   need. *Receipt per subject: the S1 parity definition, ending in a real session.*

### Lane 4 — the copyright/fair-use posture *(gated Lane 3's uploads; S3 rung 1)* — **✅ LANE DONE: RATIFIED 2026-08-02 (Rich)**
The ADR below is Accepted; Lane 3's residency ADR may now draft and ratify (rung 2).
**Draft delivered 2026-08-01; ratified 2026-08-02:**
[`ADR-ARCH-031-pilot-uploads-copyright-posture.md`](architecture/decisions/ADR-ARCH-031-pilot-uploads-copyright-posture.md)
(merge `5c1ddaa`) — honest UK-law framing (no fair-use doctrine; s29A non-commercial
TDM only; private-copying quashed 2015; the US Bartz/Kadrey rulings recorded as
persuasive context that does not govern), five enforced posture legs
(user-owns-the-source attestation in onboarding, per-account private retrieval, no
redistribution, AQA gates inherited per account, non-commercial/small/removable), the
HF-upload fact + Kaggle reason recorded (D4), the Apache-2.0-vs-Gemma-ToU licence
conflict carried as a named open item (D4.2), and an explicit "what would change this
posture" list. The four standing contradictions were burned down in the same pass
(see the list above). Remaining lane work: Rich's red pen + ratification word.
The original brief, for reference:
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
   **✅ DRAFTED 2026-08-07** —
   [`ADR-ARCH-033-pilot-residency-governance-eu-west-2.md`](architecture/decisions/ADR-ARCH-033-pilot-residency-governance-eu-west-2.md)
   (merge `5d2d849`; 3-lens adversarial verify — 20+ receipts per draft re-checked,
   UK-law claims re-confirmed incl. DUAA s81 in force since 2026-02-05). Decides the 11
   record-supported items (supersession map, UK-only recommendation, net-new encryption
   at rest, consent-in-onboarding regardless of age, the one-statement erasure cascade
   + ≤30-day SLA, DPIA commissioned, AWS DPA satisfied); carries ruling asks Q1/Q3/Q5.
   **✅ RATIFIED 2026-08-13 (Rich: "ratify")** — hand-check done against Rich's
   primary-source exports (`docs/research/ICO/`, five PDFs; 4 of 5 claims confirmed
   verbatim from the originals, the DPIA leg accepted knowingly on secondary sources);
   dated supersession notes landed on ADR-015 + ADR-028; the S3 ladder's rung 2 is
   CLIMBED. ~~Pending line: the Hyper Backup retention number (Q5)~~ **RESOLVED
   2026-08-13: Hyper Backup was never installed — the Q5 residual is nil (erasure =
   the 14-day dump roll, full stop); the durability gap this exposed (no off-box copy
   of learner data) is ledgered in known-issues with its exit path.**
2. **The multi-user ADR**: pilot accounts on the existing `student_id` partition + Keycloak
   provisioning (both already multi-user-shaped); concurrency posture (the spark cannot
   serve a concurrent cohort — cloud sizing is part of this); voice-on-Keycloak-mode flip.
   **Consent is part of onboarding (Rich's 2026-08-01 direction):** the parental-consent
   record ADR-029 D4 names is captured in the pilot onboarding flow itself — a signed step
   before a friend's first session, not paperwork on the side — so the pilot is covered for
   friends' usage by construction.
   **✅ DRAFTED 2026-08-07** —
   [`ADR-ARCH-034-pilot-multi-user-accounts.md`](architecture/decisions/ADR-ARCH-034-pilot-multi-user-accounts.md)
   (same merge + verify pass as 033): pilot rides the `student_id` partition unchanged;
   ONE provisioning/deprovisioning runbook to be written (**the step-5 "runbook exists"
   claim below is corrected — it does not exist**; three partial pieces named); the
   pilot does NOT run on the spark (measured memory law) — priced default EC2 g6.xlarge
   London with a ~6-account ceiling stated as arithmetic; voice-on-Keycloak ruled IN
   gated on one attended walk; consent = one onboarding step, two records, additive
   contract change only; erasure = attended runbook, not an API verb. Carries ruling
   asks Q2/Q4. **✅ RATIFIED 2026-08-13 (Rich: "ratify", the pair together)** — dated
   supersession note landed on ADR-ARCH-014 (runtime clause + dead Bedrock hatch;
   schema posture vindicated).
3. **The spike → deploy**: reuse is high (stateless app container, compose, alembic
   migrations, realm-as-code, the model file + llama-swap config verbatim); new =
   TLS/domain (app base-URL rebuild, cleartext-HTTP fix), hosted Postgres/Keycloak, secrets
   (extend the `sops` encrypted-config pattern), and the fine-tune-vs-stock serving decision
   from Lane 1's evals (it swings pilot economics).
4. **The upload surface** (after Lane 4 ratifies): a page — vehicle **now evidenced, Rich's
   call outstanding**: Flutter web (boot claim ESTABLISHED 2026-08-13 — compiles, boots,
   full text walk passes; blocked only by the missing server CORS) vs a minimal separate web
   page. **The Mac leg's recommendation is the separate page, served same-origin**: it
   deletes the CORS problem rather than solving it, avoids the ~5 MB CanvasKit boot for what
   is a file picker, and dodges the verified `flutter_appauth`-has-no-web hole (the walk
   passed on the *table-auth dev flavour*; the pilot's Keycloak flavour would need a second
   OIDC implementation written for web). Full evidence + the four-point argument:
   `RESULTS-mac-flutter-web-boot-2026-08-13.md` — for scanned study
   guides/books; the proven docling scan→markdown pipeline (standard + vision modes) becomes
   a service instead of an operator ritual; **per-account corpus tenancy** (per-user
   collections; the global primary-text registry gets user/subject keying); quota + format
   guards.
5. **The pilot**: friends provisioned (**runbook to be WRITTEN — ADR-ARCH-034 D3
   corrected this cell's former "runbook exists" claim, 2026-08-13**: one attended
   procedure doing Keycloak user + `student_id` attribute + role + `seed-students` row +
   consent record, with the deprovisioning half; modelled on `provision-live-suite.sh`),
   first external session = S3 top rung.

### Lane 6 — robot app distribution & switching *(moves S0's robot leg; added by Rich 2026-08-01)*
Rich's ask, same day as this plan: the **Reachy Mini desktop or mobile app should be able to
download the study-tutor custom app onto the robot, so the user can switch between the study
tutor and other robot apps** — the tutor becomes one installable app among several rather
than a hand-deployed integration.
1. **Immediate, independent of the rest:** execute the GB10→spark re-point (the robot's
   tutor path is down until then — see the state map) and smoke `ask_tutor` live.
   **Runbook written 2026-08-01:** [`RUNBOOK-reachy-repoint-spark.md`](runbooks/RUNBOOK-reachy-repoint-spark.md)
   — preflight from the gateway host, the one URL change (same bearer), the three-part
   smoke (student-model read / spoken ask_tutor / mirror cross-check), rollback, and the
   completion ticks. Runs on the fleet-gateway host, not from here.
2. **Investigation/design pass first, build second:** how Pollen's Reachy Mini app
   packaging/distribution actually works (the app hub/store mechanism and its
   install-from-companion-app flow); what the Scholar integration in fleet-gateway must
   become to be a switchable, installable app (clean install/uninstall, config carried with
   the app — backend URL + bearer, voice pins); where the work lands (mostly the
   fleet-gateway repo + robot host, with study-tutor's surface unchanged — the contracts
   already serve any client that authenticates). *Gate: the design pass comes back to Rich
   before any build.*
   **✅ DESIGN PASS DELIVERED 2026-08-07** —
   [`robot-app-distribution-design-pass-2026-08-07.md`](design/robot-app-distribution-design-pass-2026-08-07.md)
   (merge `bda0705`; citations verified to source incl. the desktop app's code). The
   platform fits the ask: Reachy Mini apps are pip-installable Hugging Face Spaces,
   daemon-managed one-app-at-a-time switching, documented settings-UI pattern for
   exactly our config (backend URL, bearer, voice pins); all build work lands in
   fleet-gateway + a Space, study-tutor contracts untouched. **Seven gate questions
   E1–E7 await Rich** (ruling-queue item 6); headline recommendation: option (c) —
   standalone app on study-tutor's server-side verified streaming voice, dropping the
   GB10 dependency. Step 1 (the re-point) still precedes or rides with any build.

### Lane 7 — model refresh & bake-off *(feeds Lane 1's serving ruling; added by Rich 2026-08-01)*
**Ruled IN (Rich, 2026-08-01: "we should definitely re-run the fine-tune"):** re-run the
fine-tune on Google's **updated Gemma 4 base** (better tool-call handling + other fixes).
Options riding with it, assessed on receipts:
1. **Dataset re-creation from a stronger teacher** — DeepSeek v4 Flash in a teacher role on
   the 2×Spark (standup in prospect); do it if the eval receipts say it helps.
2. **Side-by-side bake-off**: fine-tune the updated Gemma 4 AND Qwen 3.6 on the same
   dataset, judge blind via `fleet-evals` — the winner enters Lane 1's serving ruling, and
   the run makes good YouTube content either way.
Venue: `agentic-dataset-factory` (pipeline) + `fleet-evals` (judging); study-tutor consumes
the winner. Sequencing: the bake-off should land **before or with** Lane 1's serving ruling
so Rich rules once, over the full candidate field (old fine-tune, base, refreshed tunes).
*Gate: Rich's word on the teacher-dataset option and the bake-off scope once the 2×Spark
standup and updated-base availability are confirmed.*

### Lane 5 — truth & hygiene *(moves S4; cheap, continuous)*
1. **✅ DONE 2026-08-01**: root `CLAUDE.md` now routes every session to the two sources of
   truth (this was the pair's own enforcement gap — closed the day the pair was drafted).
2. **Mostly DONE 2026-08-01** (commits `5102874`, `10cc802`, merge `5c1ddaa`): the
   Known-contradictions list above is five-of-eight burned down; known-issues.md
   refreshed into the repo-wide ledger (fixture-ordering artifact + mirror advisories
   adopted; the `whitestocks` failure was **fixed outright** rather than adopted —
   hermetic suite now fully green); ARCHITECTURE.md model identity + ADR-ARCH-030
   index row done; app/README `voiceTurnStream` note fixed. ~~Still open: the voice
   wave/gate ledger's formal closure~~ **✅ DONE 2026-08-07** (`c786f26` — 13 SHAs
   verified, TASK-STREAM-001 found already formally closed, iOS voice walk + robot
   re-point honestly left open with owners); ~~the live contract suite re-run~~
   **already receipted** (49/49 as `suite-runner`, 2026-08-04 — Suites row).
   **Lane 5 step 2 is now fully closed.**
3. ~~Push the local Stage-0-revert commits~~ **✅ DONE 2026-08-01** — `gh` CLI 2.97.0
   installed + authenticated on the spark; the 6-commit backlog (incl. `96baad2`)
   pushed (`dad738a..f056b5c`). The fleet-gateway re-point stays in Lane 6 step 1
   (confirmed outstanding, Rich 2026-08-01).

## Sequencing, in one line

~~Lane 2 step 1a~~ (**done 2026-08-01** — the receipt sits on ruling-queue item 2), Lane 1
step 1 (evals), and Lane 6 step 1 (the robot re-point — the one thing currently *broken*)
were the immediate parallel starts; of them the evals and the re-point remain; Lane 4's
ADR is **drafted, awaiting ratification** and **ratifies before Lane 3's residency ADR
does**; Lane 3 must not touch student data in the cloud before both are ratified; Lane 6's
app-distribution work waits on its design pass; Lane 7 runs in the sibling repos and lands
its receipts before Lane 1's serving ruling; Lane 5 runs continuously. The Study Room stays
a subsequent, optional phase (deferrals — agreed with Lilymay 2026-08-01).

## Rich's open ruling queue (the genuine owner acts, consolidated)

1. ~~Ratify the mission and this plan's lane order~~ **✅ BOTH RATIFIED 2026-08-01 (Rich,
   in-session — mission "happy to sign off"; plan "approved").**
2. ~~Lane 2: the `[rag]` extra go~~ **✅ GO GIVEN + 1b EXECUTED 2026-08-02 (Rich,
   in-session: "1b go")** — RAG is live in prod; receipts in
   [`RESULTS-lane2-rag-image-1a-2026-08-01.md`](runbooks/RESULTS-lane2-rag-image-1a-2026-08-01.md)
   incl. the 1b postscript.
3. Lane 1: the serving ruling once the subject evals land — over the full field including
   Lane 7's refreshed candidates. *(The fine-tune re-run itself is already ruled IN,
   2026-08-01.)* **2026-08-07: the eval estate now exists** (local `fleet-evals` seed —
   Lane 1 step 1 cell); ~~gate tap~~ **✅ TAPPED 2026-08-07** (PROTOCOL registered) and
   ~~the merge~~ **✅ MERGED to `guardkit/fleet-evals` main 2026-08-08 (Rich's merge
   word — direct merge, no PR, per the solo convention; `7cad33d`, 29 tests green
   post-merge)**; the scored run now needs only
   two operator acts (base-model seat on llama-swap; served-GGUF provenance resolution)
   and **the `fleet-evals` GitHub repo creation word** (seed is local-only by fence).
4. ~~Lane 4: the copyright posture ADR~~ **✅ RATIFIED 2026-08-02 (Rich, in-session:
   "ratify ADR-ARCH-031")** — Lane 4 is done; Lane 3's residency ADR is unblocked per
   the S3 ladder.
5. Lane 3: the residency/governance ADR + multi-user scope + upload vehicle (web vs in-app).
   **Drafts DELIVERED 2026-08-07** — ADR-ARCH-033 + ADR-ARCH-034 on main (Proposed), five
   consolidated ruling asks Q1–Q5, each with a recommendation. **Q1–Q5 ALL RULED
   (2026-08-07) and the pair RATIFIED (2026-08-13, hand-check done via Rich's
   primary-source exports) — the ADR halves of this item are DISCHARGED.** Remaining in
   this item: the upload vehicle (web vs in-app). **The blocking evidence is now IN** — the
   Mac's Flutter-web boot-claim leg (handoff `27bb0b5`) landed 2026-08-13:
   `RESULTS-mac-flutter-web-boot-2026-08-13.md`, recommending the **minimal separate
   same-origin page** with a four-point argument. **This is now a Rich ruling ask, not a
   blocked item.**
6. Lane 6: the robot app-distribution design pass (comes back to him before build).
   **DELIVERED 2026-08-07** — the design-pass doc's seven gate questions E1–E7 (see the
   Lane 6 step 2 cell). **✅ GATE CLOSED same day (Rich, in-session — all seven ruled,
   recorded in the design doc §E): standalone app on server-side voice; public Space;
   settings-UI bearer now / AUTH-004 after; ask_jarvis dropped; startup-app; step 1
   this weekend + hand-deploy path retired; fleet-gateway + RichWoollcott HF.** The
   build brief awaits Rich's want; it lands in fleet-gateway.
7. Lane 7: the teacher-dataset option + bake-off scope, once the 2×Spark DeepSeek standup
   and the updated Gemma 4 base availability are confirmed.
8. Housekeeping: ~~push the local commits~~ **✅ DONE 2026-08-01 (gh CLI installed +
   authenticated on the spark; backlog pushed)**; execute the fleet-gateway re-point
   (Lane 6 step 1 — runbook ready); ratify-or-revert the 90s deadlines;
   ~~the deploy word for the verifier fail-closed fix~~ **✅ GIVEN + EXECUTED
   2026-08-07 (Rich, in-session)** — both containers recreated (rollback
   `pre-track-a-20260807` kept), healthz 200 ×2, `rag_wired`/`voice_services_wired`,
   live suite-runner probe: quote stripped-with-hedge, 0 verifier exceptions;
   ~~the `fleet-evals` GitHub repo creation~~ **✅ RESOLVED 2026-08-07, corrected
   premise:** `guardkit/fleet-evals` already EXISTED (public — the factory's standing
   eval substrate, pushed 2026-07-25; the earlier absence check covered only the
   personal account). Rich re-ruled in-session: the seed lands as **branch
   `study-tutor-multisubject-seed` on the existing public repo**, additively — **and
   MERGED to its main 2026-08-08 on Rich's merge word (`7cad33d`; branch deleted; direct
   merge, no PR — the solo convention)**; **the weekend operator batch (Rich, ruled
   2026-08-07):** the fleet-gateway re-point + the `gemma4-base` llama-swap seat
   (~16GB download + config + restart) + the GGUF provenance checksum (Rich's origin
   word banked: fine-tuned on the Dell ProMax GB10, files on the GB10 and backed up to
   the whitestocks NAS — checksum the NAS copy against local sha `675424b0…3144`).

## Standing rules (how work runs here — already the convention, now written)

Orchestrated-build-playbook lanes with the owner's three acts (spec word / gate tap / merge
word); the builders' PREFLIGHT names the binding docs + fences verbatim; broker isolation
standing (build lanes never touch the NATS message broker — operators running runbooks may);
coaches verify by driving; coordinator review before anything is pushed; frozen-contract
discipline for anything app-facing (additive or re-pin, nothing else); evals blind and
pre-registered; claims carry receipts; sessions end by updating THIS doc.

## Named deferrals (parked on purpose — not silently)

**The Study Room — sequencing agreed with Lilymay, 2026-08-01 (Rich):** multi-subject + RAG
come first so the tutor is "usable for real"; the Study Room is a **subsequent phase and
optional** — AI-generated art won't suit everyone, and the room concept fits a particular
cohort (a different engagement angle for other cohorts, e.g. boys, is an open design
question). The design itself stands (Lilymay's own — coins/rooms/pets/shop; needs contract
Rev 3, a navigation shell, and the art pipeline; build order coins+shop+bedroom per the
designer);
Boss Battles / daily challenges / weekly quests (designed, promised by live unlock gates,
unbuilt) and the 7 content-gated achievements behind them; the ~150-word voice-mode reply
cap (Option C of the TTS investigation) + the 1.7B TTS trial; ~~the iOS attended walk~~
(**slice leg done 2026-08-02** — simulator walk via `integration_test`; the VOICE leg on
iOS still needs a human ear and stays deferred);
token-streaming ledger closure (voiceTurnStream is wired — close TASK-STREAM-001's record);
Reachy `celebrate_achievement` conformance confirmation; NATS fleet surface disposition
(live transport or formally dormant); the hackathon-era FEAT-PO roadmap IDs (historical
numbering only).

---

*Update rule: edit the lane step or cell in place, not the chat history. If this document is
stale at a session start, that is itself a Lane 5 finding. Grounded in a 2026-08-01
eight-area receipted review of this repo (docs, git history, code), adversarially critiqued
before commit; the named receipts above are the evidence trail.*
