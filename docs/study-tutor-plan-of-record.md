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

## Current state — the honest map (verified 2026-08-01, receipts named)

Hosts, cashed out once: **the spark** = the household DGX Spark inference/app box
(`spark-fcf6`); **the GB10** = the Dell DGX box, now returned to the software factory; **the
NAS** = the Synology box (`whitestocks`) holding durable state. All tailnet-only today.

| Piece | State | Receipt |
|---|---|---|
| Tutoring core (Player + async Coach + planner + quote verifier) | **LIVE** on the spark `:8100` (static-token "table" auth mode, **voice ON + VERIFIED STREAMING LIVE from 2026-08-03 (ADR-ARCH-027 as ratified — transcript 0.2s / first spoken sentence ~3s on the prod WS smoke)**: every voice turn had silently failed since the 2026-07-26 spark move because empty `STT_MODEL`/`TTS_MODEL` fell back to the GB10-era llama-swap aliases (`parakeet-tdt`/`qwen3-tts`) the spark does not register; found by the Mac live-suite run, fixed by pinning `parakeet-tdt-0.6b-v3`/`qwen3-tts-0.6b` in the deploy env + restart) and `:8101` (Keycloak auth mode, voice OFF pending the Keycloak phone-flow proof). **One-active (b) semantics LIVE 2026-08-04 (`19a0211`)**: `resume_if_active:false` = end-then-create (the implicit end rides the real end path and SETTLES), one-active-per-`(student, subject)` structural via partial unique index `session_one_active_idx` (migration head `346cd366b66e`, safety dump `pre-one-active-migration-20260804.sql`); the MCP door now RESUMES (a robot start joins, not ends, the active session) — this and the convergence-on-one-active concurrency-test rewrite were the build's two flagged beyond-the-letter judgment calls, **both BLESSED by Rich 2026-08-04** (interactive walk on the Mac; the flag is closed); dated in-place binding annotation, no re-pin; live-proven as `suite-runner` (second false-start ended+settled the first; lilymay's active untouched; zero leftovers) | `HANDOFF-study-tutor-full-encapsulation-spark.md` (2026-07-26); voice-fix restart receipt 2026-08-03 (this plan, Suites row live-suite note); (b) build receipt `19a0211` + `HANDOFF-spark-double-active-server-build.md` (2026-08-04) |
| Model serving | **LIVE** — `gemma4-tutor` (fine-tuned Gemma 4 26B-A4B) + coach + speech models + embedder on the spark's llama-swap `:9000`; the GB10 handed back to the factory (Reachy speech unit `:8765` excepted) | same handoff; `/opt/llama-swap/config/config.yaml` |
| Student model + gamification | **LIVE** — Postgres on the NAS `:5434`, nightly dumps; W1+W2 economy (33 achievements) settling per ADR-ARCH-030; real session receipted 2026-07-26 (`904ad0f`) | ADR-ARCH-030; `docs/gamification/design.md` §13.1 |
| App (Flutter, monorepo `app/`) | **Android device-walked** (sessions, voice tap-to-talk, streaming — **WS path FIXED 2026-08-03 `049f17c`** (client now opens binding §2.1's `/ws`; hermetic pin test drives the real `voiceTurnStream` at a local socket so the path can't silently drift; the 2026-08-03 attended Samsung walk re-proved voice end-to-end post-fix). **Client §7-conformant + strand-proof `fa8d95b`**: the adapter speaks contract §7's ratified frames verbatim (was a private dialect) and a voice turn can never strand — end-without-done and gone-silent both fall back to batch (the live three-dots hang is dead); ~~live STREAMING itself waits on the parked server branch~~ **VERIFIED STREAMING WALKED AND SIGNED OFF 2026-08-03 evening (Rich's ears, the arc's final receipt)**: with the server's ADR-027 composition deployed (`513bc70`) and the client's seq-ordered play queue (`ffc83c9`), attended Samsung turns streamed text sentence-by-sentence with CONTINUOUS audio — grounded turns on BOTH `macbeth` and `an_inspector_calls` (`turn_verifier_built … chunks=6` in prod logs: subject-scoped retrieval + per-sentence verification + streamed TTS, the whole weekend's stack in one turn), sign-in, history, live robot mirror, gamification UI, settings). **Attended live walk on the Samsung dev phone 2026-08-03 (Rich)**: real-transport APK installed; picker visible on-device; real gemma4 replies (long-form); voice+text turn audible ("what is a metaphor" — first working voice turn since the spark move). **iOS: slice SIMULATOR-WALKED 2026-08-02** (iPhone 17 / iOS 26.2 / Xcode 26.3 — `integration_test/slice_walk_test.dart` drives the real composition root through sign-in → picker → start → two turns → away → resume → end → celebration; **voice walk still pending**: mic permission + TTS audibility need human attendance). **Web: no boot claim** | `RESULTS-study-tutor-p2-live-acceptance-2026-07-05.md`; `app/README.md`; honest-iOS commit `29a320f`; walk commit `dd4bbed` (2026-08-02; re-walked green after the FEAT-FLV1 rebase) |
| Auth | **LIVE end-to-end** — Keycloak on the NAS `:8443`; server gate (KC-G2) and real-device gate (KC-G3) passed 2026-07-19; interim table mode retained for the robot | `HANDOFF-weekend-auth-voice-fable-window.md` §11 |
| Robot (Reachy "Scholar") | **⚠ CONFIRMED NOT re-pointed (Rich, 2026-08-01)** — the robot still targets the GB10, whose tutor stack was retired 2026-07-26, so the robot's `ask_tutor`/student-model path is presumed DOWN until the fleet-gateway URL flips to the spark `:8100` (same static bearer). The re-point is an operator act in the fleet-gateway repo/robot host | `HANDOFF-study-tutor-full-encapsulation-spark.md` operator item 3; Rich in-session 2026-08-01 |
| Live robot-session mirror | **SHIPPED 2026-07-31** — `turns?since=` delta read + SSE stream; `resume` stays active-only ("one verb per job"; the mirror lane's Stage-0 resume widening was reverted, `96baad2`) | `RESULTS-spark-live-robot-session-mirror-2026-07-31.md` |
| RAG / retrieval | **LIVE in prod as of 2026-08-02** (Rich's 1b go, executed same session): both spark containers boot with `event=rag_wired` (581-chunk `gcse-english-v1` re-embedded at 1024-dim to match llama-swap's `embed`, baked into the 1.4GB CPU-torch image); quote-retrieval smoke PASS 3/3 **inside the deployed container**; reranker instance-cached (~5.3s warm retrieval); rollback tags `pre-rag-20260802` kept. The Coach revise loop is un-idled. **Still open:** the fabrication-rate golden-quote eval (S2's bar — harness unbuilt, Lane 2 step 3), citation anchors (deferred), subject-scoping (Lane 2 step 2) | `RESULTS-lane2-rag-image-1a-2026-08-01.md` incl. the 1b postscript; deploy/http compose |
| Multi-subject | **Retrieval layer BUILT + LIVE 2026-08-02** (ADR-ARCH-032: per-subject collections, subject-keyed wiring/registry, closure coverage check, `--subject` ingest — deployed, `rag_subject_coverage` in prod boot logs); mechanism stays ADR-TUTOR-MULTI-SUBJECT (ONE fine-tune + per-subject prompts + corpora; 17/17 informal probes). **App picker + seams CLOSED 2026-08-02** (Lane 1 step 2 — `3a08bfa`: visible picker, `defaultSubject` now the fallback per SUBJECT_DEFAULT §4). **Still open for a real second subject:** content packs (Lane 1 step 3 — scans!), subject evals (Lane 1 step 1) | ADR-ARCH-032; the ADR; `multi-subject-validation-{prompts,results}.md` |
| Contracts | Six verbs frozen (Rev 2); additive addenda through 2026-07-31; `SUBJECT_DEFAULT='english'` (a default, not a pin) | `API-session-http-binding.md`; `SUBJECT_DEFAULT.md` |
| Suites | **Hermetic python suite FULLY GREEN — 1709 passed, 0 failures as of 2026-08-04 (was 1671 on 2026-08-02; +38 = server-queue pins then the ruled-(b) build: 7 start-fresh service pins incl. sweep-all-strays + legacy-`''`, MCP resume pin, index parity now asserts UNIQUE+predicate)** — the standing `whitestocks`-string scope-guard failure was closed by de-hostifying the auth-test fixtures (`10cc802`); **424 dart tests (2026-08-04: +1 ruled (b) pin PROMOTED into the shared s5 contract body — fake and deployed server now agree by test, live 49/49)**; **the live contract suite RE-RECEIPTED GREEN 2026-08-03 — 47/47, then 48/48 in ONE run post-verified-streaming-deploy (the +1 is a §7 VERIFIED-STREAMING case through the app's real adapter: transcript-first, token/audio_ref interleave, terminal done, chunk fetched)** (grown from 35 since 2026-07-05; the day's two runs before it were the diagnosis: 40/47 exposed voice dead since the spark move → env fix `1595b68`; 38/47 exposed the lying WAV-as-mp4 live fixture + phone/suite shared-student interference → honest spoken fixture in `049f17c`; final run with the phone idle). **Lane 5's suite debt is closed**; **the live suite is ISOLATED from 2026-08-04** (runs as dedicated `suite-runner`, scoped authed resets, zero-leftover per-file cleanup — re-receipted 48/48 in 6:44 with lilymay's rows byte-identical before/after, `bb5a4fa`; **49/49 on 2026-08-04 with the promoted (b) end-then-create pin asserting against the DEPLOYED `19a0211` build — zero leftovers**); the pre-2026-08-03 transcripts wiped by the old whole-store reset are an ACCEPTED LOSS (Rich, 2026-08-04 — learner state was never touched); **suite isolation server-half DEPLOYED 2026-08-04** (scoped authenticated `__dev__/reset` + suite identity `token-suite`→`suite-runner` live-proven; Mac re-point of test_live pending — until then the live suite stays operator-attended) | suite run 2026-08-01 (this session); mirror-lane run records 2026-07-31/08-01; p2 acceptance 2026-07-05 |

**Known contradictions to burn down (Lane 5) — five of eight burned down 2026-08-01
(the Lane 4 pass `5c1ddaa` + hygiene commits `5102874`/`10cc802`):**
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
- The 15s→90s turn-deadline change was never ratified against the contract's latency
  section. (Rich — ruling queue item 8.)
- Citation anchors broken on 581/581 corpus chunks since 2026-05-10 — **explicitly
  deferred again** by the Lane 2 1a receipt; Lane 2 step 3 owns fix-or-defer.

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
2. **The multi-user ADR**: pilot accounts on the existing `student_id` partition + Keycloak
   provisioning (both already multi-user-shaped); concurrency posture (the spark cannot
   serve a concurrent cohort — cloud sizing is part of this); voice-on-Keycloak-mode flip.
   **Consent is part of onboarding (Rich's 2026-08-01 direction):** the parental-consent
   record ADR-029 D4 names is captured in the pilot onboarding flow itself — a signed step
   before a friend's first session, not paperwork on the side — so the pilot is covered for
   friends' usage by construction.
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
   index row done; app/README `voiceTurnStream` note fixed. **Still open:** the voice
   wave/gate ledger's formal closure; the live contract suite re-run against the spark
   (operator-attended — the 35-green receipt is from 2026-07-05, pre-`turnsSince`).
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
   2026-08-01.)*
4. ~~Lane 4: the copyright posture ADR~~ **✅ RATIFIED 2026-08-02 (Rich, in-session:
   "ratify ADR-ARCH-031")** — Lane 4 is done; Lane 3's residency ADR is unblocked per
   the S3 ladder.
5. Lane 3: the residency/governance ADR + multi-user scope + upload vehicle (web vs in-app).
6. Lane 6: the robot app-distribution design pass (comes back to him before build).
7. Lane 7: the teacher-dataset option + bake-off scope, once the 2×Spark DeepSeek standup
   and the updated Gemma 4 base availability are confirmed.
8. Housekeeping: ~~push the local commits~~ **✅ DONE 2026-08-01 (gh CLI installed +
   authenticated on the spark; backlog pushed)**; execute the fleet-gateway re-point
   (Lane 6 step 1 — runbook ready); ratify-or-revert the 90s deadlines.

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
