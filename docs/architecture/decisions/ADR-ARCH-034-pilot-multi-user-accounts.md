# ADR-ARCH-034 — Pilot multi-user accounts: the friends cohort on the existing `student_id` partition, one provisioning runbook, cloud sizing, the voice flip, and consent-in-onboarding

## Status

**Accepted — RATIFIED by Rich, 2026-08-13 (in-session word: "ratify", the pair together
with ADR-ARCH-033), with both rulings banked 2026-08-07 as recorded in the ruling-asks
section (Q2 hold serving for Lane 1's evals — Branch A provisional; Q4 the D4 ceiling
confirmed, on-demand for anything a student touches).** ADR-033's hand-verification
receipt covers the consent-law facts this ADR's D6 leans on (see its status block).
*Drafted 2026-08-07.*

This is the multi-user half of the Lane 3 ADR pair. Its sibling,
[ADR-ARCH-033](ADR-ARCH-033-pilot-residency-governance-eu-west-2.md) (the residency/
governance posture), decides *where* pilot data lives and under what obligations; **this ADR
decides how multiple accounts exist at all** — tenancy, provisioning, concurrency/sizing,
voice, and the onboarding mechanics of the consent record ADR-033 D5 specifies. Ratification
is **Rich's act alone**. This draft decides everything the record already supports; the ONLY
items left open are the two ruling asks that belong here
([§The ruling asks](#the-ruling-asks-that-belong-here-only-rich-rules-these) — Q2 both
branches, and Q4; Q1/Q3/Q5 live in ADR-033), each presented with a recommendation. Nothing
else is asked of him — no file edits, no review pass; supersession of ADR-ARCH-014 lands via
the [on-ratification checklist](#on-ratification-checklist-performed-at-ratification-not-before)
inside this draft.

**Plan cell:** [study-tutor-plan-of-record.md](../../study-tutor-plan-of-record.md)
**Lane 3, step 2** ("The multi-user ADR") — per the mission's no-orphan-docs rule, this
draft attaches to that cell and the coordinator updates it at ratification. (This draft also
carries one honest **plan correction** — see D3 — folded at coordinator review.)
**Date:** 2026-08-07
**Supersedes (on ratification, runtime clause only):**
[ADR-ARCH-014](ADR-ARCH-014-single-user-scalability-posture.md) (single-user scalability
posture). Its **schema posture stands vindicated** — "multi-student-ready from day 1 …
no singleton current student" is exactly why this ADR needs no migration (D1). What dies is
its **runtime clause** ("single-user only through Phase 2") and its **inference scale-out
escape hatch** ("Bedrock already supports concurrent per-student inference; no new work"),
which is dead — see D4. Checklist, not an edit now.
**Related:** [ADR-ARCH-033](ADR-ARCH-033-pilot-residency-governance-eu-west-2.md) (sibling —
residency, encryption, the consent-record specification D6 implements, the erasure path D3's
runbook joins); [ADR-ARCH-031](ADR-ARCH-031-pilot-uploads-copyright-posture.md) (the
copyright legs D7's tenancy design enforces; its D4.2 open licence item is flagged in the
honest registers); [ADR-ARCH-028](ADR-ARCH-028-keycloak-idp-nas-placement-tailnet-tls.md)
(the Keycloak build this ADR extends to a cohort);
[ADR-ARCH-029](ADR-ARCH-029-phased-productionisation-local-first-cloud-native-target.md)
(D2's portability seams, which make D2/D5 below env-flips rather than builds);
[aws-production-hosting-research-2026-07-06.md](../../research/ideas/aws-production-hosting-research-2026-07-06.md)
(the costed sizing options in D4).

## Context

The friends pilot turns a one-student system into a small cohort: Lilymay, her sister Dulcie
in prospect, and Lilymay's close friends — each with their own account, their own student
model, their own uploaded books, and (mission, "Who it serves") **never any visibility into
each other's work**. The plan's Lane 3 step 2 commissions this ADR to settle four things:
whether the data layer needs tenancy work (it does not — D1), how accounts get provisioned
(one runbook that does not yet exist — D3), what concurrency the pilot can actually serve
and on what hardware (not the household box — D4), and how consent-in-onboarding works
(one step, two records — D6). Voice's Keycloak-mode flip (D5) and the robot's table-mode
tail (D8) are settled on the way.

Two standing facts frame everything:

1. **The system was built multi-user-shaped on purpose.** ADR-ARCH-014 (2026-04-18) ruled
   "multi-student-ready from day 1" at the schema level while keeping the runtime
   single-user; ADR-ARCH-023 replaced its mechanism (Graphiti group IDs → Postgres
   `student_id`) but kept the posture. The receipts in D1 show the bet paid off.
2. **The household serving box cannot serve a cohort.** The spark (the household NVIDIA DGX
   Spark machine currently running the backend and models) is memory-committed to within
   ~30 GB of its ceiling by a *single* student's stack — measured, not guessed (D4). The
   concurrency question is therefore a **cloud sizing question**, which the plan
   (plan:216–217) says belongs in this ADR.

## Decision

### D1 — Tenancy: the pilot rides the existing `student_id` partition, unchanged — no migration, no new tenancy layer

The data layer needs **zero structural work** for multiple accounts. Receipts:

- **Schema:** every student-owned table hangs off `student(student_id)`
  (`src/study_tutor/knowledge/store/schema_reference.sql`, head `346cd366b66e` — "multi-
  student is a partition key", :12–14). This is ADR-014's day-1 posture, mechanism updated
  by ADR-023.
- **Queries:** roughly **28 student-scoped call sites** in the Postgres store
  (`src/study_tutor/knowledge/store/postgres.py` — :272, :286, :305, :384, :407, :430, :443, :454,
  :640, :789, :797, :805, :848, :868, :894, :915, :962, :975, :991, :1054, :1125, :1634,
  :1670, :1784, :1794) all carry the `student_id` partition, including the whole
  gamification read path (`get_gamification_state` :938 and its sub-queries :962, :975,
  :991). **There is no cross-student aggregation anywhere in the codebase** — which is also
  mission law 7's no-leaderboards guarantee holding at the query layer, by construction.
- **Live isolation proof (2026-08-04):** the live contract suite ran as the `suite-runner`
  account with scoped resets, and **Lilymay's rows were byte-identical across the full
  run** (plan, Suites row). Multi-account isolation is not a design claim; it has a live
  receipt.
- **Concurrency shape:** the partial unique index `session_one_active_idx` ON
  `session(student_id, subject)` WHERE `status='active'` (schema :70–73) means one active
  session per student per subject — so "concurrent load" for this system is **N students ×
  1 session each**, never one student multiplied. D4's sizing uses exactly this shape.
- The live token table already proves plural accounts end-to-end in table mode:
  `<bearer-lilymay>` → lilymay, `<bearer-alex>` → alex, `<bearer-suite>` → suite-runner.

**Decision: pilot accounts are rows, not architecture.** Adding a friend = a Keycloak user
+ a `student` row + a consent record (D3, D6). Nothing else changes.

### D2 — Identity: friends are on Keycloak from day one; realm-as-code carries the cohort unchanged

Keycloak (the self-hosted login/identity server, ADR-ARCH-028) is the pilot's identity
system from the first external account — no friend ever gets a static table token. The
mechanisms are already built and receipted:

- **Realm-as-code:** `deploy/keycloak/realm/study-tutor-realm.json` — `registrationAllowed:
  false` (accounts exist only when the operator creates them — no open signup, which is
  also ADR-031's named-cohort leg holding at the identity layer), `sslRequired: all`,
  `bruteForceProtected: true`; roles `student` and `parent` (the latter "reserved for
  future use" — the natural carrier if consent is ever account-exercised, per ADR-033 D5);
  clients `study-tutor-app` (public, custom-scheme redirect) and `reachy-robot`. The
  `users` key is **absent**: users are hand-created and never in git (ADR-028 D1) — the
  deliberate PII posture, and the reason the cloud move has **no PII to migrate**
  (ADR-029 D2).
- **Realm import is non-overwriting** (`--import-realm` does not delete users — Keycloak
  standup runbook :202, :339), so friends' accounts and realm-as-code coexist: config
  redeploys never destroy the cohort.
- **The `student_id` claim** rides a protocol mapper from a user attribute
  (`deploy/keycloak/provision-live-suite.sh:87–99`). **Critical known behaviour:** if the
  attribute is missing, authentication *succeeds* and the API then *fails* — which is
  precisely why provisioning must be one atomic runbook (D3), not a set of steps someone
  might do partially.
- **The auth mode is a pure env flip:** `STUDY_TUTOR_AUTH_MODE ∈ {table, keycloak}`
  (`src/study_tutor/http/oidc_config.py:50, :86–100`), resolved through the `TokenResolver`
  seam (`src/study_tutor/http/auth.py:27–47`; table implementation :51–79; Keycloak
  implementation `src/study_tutor/http/auth_keycloak.py`) that ADR-029 D2 pinned
  deploy-agnostic. Both modes run side by side today (:8100 table, :8101 Keycloak, separate
  compose projects) — which is what makes D8's robot tail cheap.

### D3 — Provisioning: ONE runbook, which must be WRITTEN — the plan's "runbook exists" claim is corrected here

**Honest correction:** the plan's Lane 3 step 5 says "friends provisioned (runbook
exists)" (plan:233). **That claim is false.** No friend-provisioning runbook exists. What
exists is three partial pieces, none sufficient alone:

1. The **Keycloak standup runbook's Phase 4** — manual user creation in the admin console
   (`RUNBOOK-study-tutor-keycloak-standup.md:206–252`): creates the user, but nothing
   downstream.
2. The **`seed-students` CLI** (`src/study_tutor/cli/main.py:1221–1270`) — already
   multi-student, creates `student` rows: the database half, with no identity half.
3. **`provision-live-suite.sh`** (`deploy/keycloak/provision-live-suite.sh`) — the nearest
   thing to real provisioning automation (user + attribute + mapper, sops-secured), built
   for the suite-runner account: the obvious **template**, not the runbook.

**Decision: Lane 3 step 5 WRITES the one friend-provisioning runbook**, modelled on
`provision-live-suite.sh`, performing as a single attended procedure: Keycloak user →
`student_id` attribute (D2's critical fail-mode makes this non-optional) → `student` realm
role → `seed-students` row → consent + attestation record (D6). **A partial subset of these
steps produces a broken account by construction** (auth-succeeds-API-fails, or a session
with no consent record) — the runbook exists precisely so partial states cannot.

Per ADR-033 D6.2, the same runbook carries the **deprovisioning half**: Keycloak user
deletion paired with the one-statement Postgres cascade delete and (once D7 lands)
per-account corpus deletion. **The erasure surface decision ADR-033 delegated here is
decided: for the pilot, erasure is an attended operator runbook, not an API verb.** The
cohort is small and named, deprovisioning is inherently an operator act (mission: attended
steps are Rich's), and the only in-code deletion primitive today is a dev-flag tool that
deliberately spares gamification state (`knowledge/store/postgres.py:761–806`;
`http/app.py:591–618, :752–755`) — not an erasure path. If an erasure verb ever lands on
the API it lands **additive** per law 6; nothing about the six frozen verbs changes either
way. The plan-text correction to step 5 ("runbook exists" → "runbook to be written, this
ADR D3") is folded at coordinator review and finalised in the on-ratification checklist.

### D4 — Concurrency and sizing: the pilot does NOT run on the spark; default = EC2 g6.xlarge (London) with a stated cohort ceiling; ADR-014's runtime clause and dead Bedrock escape hatch are superseded

**Why the spark is out**, with receipts — this is measurement, not caution:

1. The backend is a **single uvicorn process** (uvicorn = the Python ASGI web server), no
   workers (`src/study_tutor/cli/main.py:1218`).
2. All models — tutor, coach, embeddings, speech-to-text, text-to-speech — share **one
   llama-swap server** on :9000 (llama-swap = a multiplexer that loads/unloads models on a
   single GPU host; loading one **evicts** another).
3. **The memory law, measured 2026-07-25:** base ~53 GB + audio ~9 GB + the tutor pair
   ~36 GB ≈ **98 GB of the spark's 128 GB** committed by ONE student's stack
   (`HANDOFF-study-tutor-full-encapsulation-spark.md:133–135`). There is no headroom for a
   second concurrent tutor context. The spark serves Lilymay; it cannot serve a cohort.
4. ADR-014 knew this day would come and pointed at its escape hatch: "Bedrock already
   supports concurrent per-student inference; no new work" (ADR-014). **That hatch is
   dead:** Bedrock Custom Model Import cannot serve the fine-tune, three ways (AWS research
   §2:27–46 — no Gemma architecture support + a 128K positional cap vs Gemma 4's 256K; no
   eu-west-2; no roadmap signal). This ADR supplies the replacement below — that is the
   concrete supersession this ADR performs on ADR-014 (checklist, not an edit now).

**The load shape** (from D1): N students × 1 active session each, turns arriving at human
conversation pace. A tutor turn occupies the GPU for seconds; concurrent sessions
**queue**, they do not parallelise, on a single-GPU host.

**The priced options** (AWS research §5, ~61 h/mo usage pattern, stop/start scheduled via
EventBridge — AWS's cron service):

| Option | Where | ~Cost/mo | Notes |
|---|---|---|---|
| **EC2 g6.xlarge + llama.cpp (GGUF)** — **recommended default** | London (eu-west-2) | **$70–75** (spot ~$30 — Q4) | 1× NVIDIA L4 24 GB; the GGUF quantized model file (~17 GB resident) + the llama-swap config port **verbatim** (research §4:66–71) |
| EC2 G7e (96 GB Blackwell) | London, since May 2026 | $3.36/hr on-demand, spot ~$1.84 | The scale-up step: room for tutor + coach + audio co-resident |
| HF Inference Endpoints (L4) | Ireland (EU, not UK) | ~$49 | Trips ADR-033 Q1 |
| SageMaker | Frankfurt ~$213 / London BF16 ~$445 | | Uneconomic for this shape |
| Stock Gemma 4 26B-A4B on Bedrock (serverless) | Frankfurt (not London) | ~$1–5 at pilot volumes | The Q2 stock branch — collapses into ADR-033's Q1 |
| Any 24/7 GPU | — | $2.5k–6.6k | Ruled out (research §5) |

**Sizing arithmetic on the default, stated honestly:** a g6.xlarge's single L4 (24 GB)
holds the ~17 GB tutor GGUF **and essentially nothing else** — no coach, no
text-to-speech/speech-to-text co-residency without llama-swap eviction churn. The default
therefore serves the **text tutoring loop** for a small cohort with queued turns; the coach
runs where it fits (a smaller/CPU path, or accepts swap latency) and **cloud voice sizing
is explicitly not solved by the default instance** — it arrives with the G7e step or split
endpoints, and is priced above. (Voice for Lilymay meanwhile keeps working from the
household deployment — D5/D8.)

**The cohort ceiling** (Rich's Q4 confirms the number): the recommended default is sized
for the **named close-friends cohort — up to ~6 accounts, expecting ~2–3 simultaneous
sessions worst case**, with turn queueing as the degradation mode (a busy evening means a
slower tutor, never a fallen-over one). This ceiling is **arithmetic from one GPU and the
D1 load shape, not a load-test receipt** (honest registers). Growth beyond it moves to G7e
or split endpoints — and independently trips ADR-031's scale tripwire and ADR-033's
"what would change this posture" item 2, so the ceiling is a governance line, not just a
capacity one.

### D5 — Voice on Keycloak mode: ruled IN, gated on ONE attended voice walk against :8101

Voice is currently **off** in the Keycloak-mode deployment
(`deploy/http/.env.kc:6` — `STUDY_TUTOR_VOICE_ENABLED` empty; that file is gitignored by
design (`.gitignore:149`) and lives only on the spark host, so this receipt is the
2026-08-07 design-pass inspection, not a repo file) for exactly one recorded
reason: "voice OFF pending the Keycloak phone-flow proof" (plan:32). The record now shows
the residual risk is one attended proof, not engineering:

- **The mechanism is an env flip.** Voice routes mount only when voice is enabled
  (`src/study_tutor/http/app.py:757–766, :788–791`; `src/study_tutor/voice/config.py:57`).
  Turning voice on in Keycloak mode = one env line + container recreate.
- **There is no voice-specific auth code to prove.** The voice WebSocket authenticates at
  connection upgrade through the **same `TokenResolver` seam** as every HTTP verb
  (`src/study_tutor/http/ws.py:4`) — the seam ADR-029 D2 pinned and D2 above relies on.
- **The phone-flow half is banked:** KC-G3, real-device Keycloak sign-in, GATE PASS
  2026-07-19 (`docs/runbooks/evidence/keycloak-kcg3-2026-07-19/EVIDENCE.md:10`).
- **What is NOT banked, said plainly:** an attended **voice** walk in Keycloak mode. The
  existing voice walk receipt (2026-08-03) is table-mode, against :8100.

**Decision: voice-on-Keycloak is ruled IN — the flip happens — gated on one attended voice
walk against :8101** (tap-to-talk round trip, authenticated as a Keycloak user). Pass =
flip stays; the pilot cohort gets voice. Fail = voice stays off in Keycloak mode and the
failure is brought to Rich (it would contradict the seam receipts above, which would be
worth knowing loudly). Per law 8 this ADR claims the mechanism, not the walk.

### D6 — Consent in onboarding: ONE step, TWO records, landing as an ADDITIVE contract change — the six frozen verbs untouched

ADR-033 D5 specifies the consent record (the table: `student_id`, consenting adult,
timestamp, notice-version, attestation flag, withdrawal timestamp; the uniform
every-account-regardless-of-age rule; the honest Article-8 framing). **This ADR carries the
onboarding mechanics**, per Rich's 2026-08-01 direction (plan:218–222):

- **One step, two records.** The pilot onboarding flow contains a single signed step,
  before a friend's first session, that captures **(a)** the parental-consent record and
  **(b)** the ADR-031 leg-1 ownership attestation ("we own the physical copy of what we
  upload"). One ceremony, two rows — coverage by construction, not filing cabinet.
- **A hard gate:** session start is refused for any account without a current consent
  record (withdrawal timestamp unset). In the pilot this is doubly enforced: the D3
  runbook cannot create an account without the consent record (procedural), and the
  backend checks at session start (mechanical) — so the gate holds even if provisioning is
  ever done wrong.
- **Law 6, spelled out:** the six frozen session verbs — their shapes and status codes —
  are **untouched**. The consent gate and any consent-recording surface land as **additive
  contract changes** per the frozen-contract discipline
  (`docs/design/contracts/API-session-http-binding.md` §7): a documented **addendum**
  naming the consent-required refusal on session start (reusing the existing
  authorisation-refusal surface with a machine-readable reason, or, if any shape change
  proves unavoidable, a §7 revision + re-pin — never a silent edit), and, if consent is
  ever captured through the API rather than the attended onboarding step, a **new additive
  verb**. Nothing about this decision requires touching an original verb's shape.
- **Nothing of this exists in code today** — no consent strings anywhere in `app/lib` or
  `src/`, no consent table, no gate (honest registers). This D specifies; Lane 3 builds.

### D7 — Per-account corpus tenancy: the subject-keyed registry gains a student dimension; deleting the account deletes the collection — SPECIFIED here, built in Lane 3 step 4

Today there is **one shared retrieval corpus**, baked into the 1.4 GB container image
(`deploy/http/docker-compose.yml:63–66`), with collections keyed by **subject, not
student** (`src/study_tutor/knowledge/retrieval.py:461, :464–478` — the ADR-032
subject-scoped design). Per-account corpora **do not exist**. ADR-031 legs 2 and 5 and
ADR-033 D6.3 all land on the same requirement, which this ADR turns into the tenancy
specification (Lane 3 step 4 builds it; this ADR does not):

1. **The registry gains a student dimension:** collection identity becomes
   (student, subject) for uploaded material — each account retrieves **only** against its
   own uploads plus the shared public-domain collections (which stay shared: they are
   nobody's personal data and nobody's infringement — ADR-031 leg 2's explicit carve-out).
   In-copyright material is never pooled across accounts, even when two families own the
   same book — each family scans its own copy (ADR-031's accepted inefficiency).
2. **Deletion deletes the collection:** account deletion removes every (student, *)
   collection and any stored upload artifacts — this is the D3 deprovisioning runbook's
   corpus step and ADR-033 D6.3's erasure requirement, one mechanism serving both.
3. **The AQA gates are inherited per account** (mission law 4; ADR-031 leg 4): the
   `AQA_REFUSAL_PATTERN` ingest gate (`src/study_tutor/knowledge/corpus.py`) and the
   `AQA_FILENAME_PATTERN` retrieval gate (`src/study_tutor/knowledge/retrieval.py`) bind
   inside **every** per-account pipeline, at both ingest and retrieval, with inheritance
   tests per account (ADR-031's build requirement, restated as part of this spec).
4. The upload surface itself (vehicle, quota/format guards, the docling scan pipeline as a
   service) is Lane 3 step 4's own decision set, gated on ADR-031 (ratified) and this
   pair — not decided here.

### D8 — Table mode stays on :8100 for the robot until Lane 6 step 1; no friend ever uses it

The Reachy robot currently authenticates via the static token table against the :8100
table-mode deployment. That stays exactly as-is until Lane 6 step 1 (the robot's re-point,
a separate lane with its own receipts) — the two compose projects already run side by side
(D2), so keeping the robot's door open costs nothing and blocks nothing. **The boundary is
absolute: table mode is Lilymay's-household-only.** Every external account exists only in
Keycloak mode (D2); no friend ever receives a static token. Retiring table mode entirely is
Lane 6's decision, not this one.

## Alternatives considered

- **A tenancy migration / new tenancy layer for the pilot.** Rejected — D1's receipts show
  the partition already exists, is enforced at every call site, and has a live byte-identical
  isolation proof. Building tenancy again would be work invented to feel thorough.
- **Static table tokens for friends (defer Keycloak).** Rejected flatly — table mode has no
  real credential ceremony, and handing a minor's account a shared-secret string contradicts
  the entire ADR-028 build. The env-flip seam makes Keycloak-from-day-one nearly free (D2).
- **Serve the cohort from the spark anyway (queue everything on the household box).**
  Rejected on the measured memory law (98 of 128 GB for one student) — and it would put
  friends' data on hardware ADR-033 has no governance posture for, invert the household/
  pilot boundary, and make Lilymay's daily tutor contend with her friends' sessions.
- **Automated provisioning (an admin API / self-service signup) instead of a runbook.**
  Rejected for the pilot — `registrationAllowed: false` is a posture, not a gap: accounts
  are a named-cohort, operator-attended act (ADR-031's proportionality argument depends on
  it). A runbook modelled on `provision-live-suite.sh` is proportionate; automation is a
  post-pilot question.
- **An erasure API verb now.** Rejected in favour of the attended runbook (D3) — the verb
  would need design, auth semantics, and contract work for an act that happens (at pilot
  scale) approximately never and always attended. Additive later if ever needed.
- **Voice stays off for the pilot.** Rejected — the record shows one attended walk is the
  entire residual risk (D5); leaving tap-to-talk off for friends would ship a worse product
  to protect against a risk the seam receipts say is retired.
- **Bigger default instance now (G7e).** Rejected as the default — ~$3.36/hr against the
  measured ~61 h/mo pattern buys capacity the D1 load shape doesn't need at ≤6 accounts;
  named as the scale-up step the ceiling points to.

## Consequences

**Positive:**

- The pilot's account model is **provably cheap**: a friend = one runbook execution. No
  migration, no tenancy build, no auth build — the 2026 spring/summer builds (Keycloak,
  seam, realm-as-code) pay out here.
- ADR-014's schema bet is honoured on the record: its day-1 partition is why D1 is short.
- The concurrency question gets an honest, measured answer with a priced default and a
  stated ceiling — and ADR-014's dead Bedrock escape hatch is replaced rather than left
  pointing at nothing.
- Voice for friends is one attended walk away, on receipts, not hope.
- Consent/attestation coverage is **by construction** (runbook + gate), and law 6's frozen
  contract survives untouched.

**Negative / accepted:**

- **Real work is commissioned, honestly named:** the provisioning/deprovisioning runbook
  (D3 — including correcting the plan's false claim), the consent table + gate + addendum
  (D6), the student-dimension registry + deletion + per-account AQA inheritance tests (D7),
  the attended voice walk (D5). None of it exists today.
- The pilot takes on **cloud money** (~$70–75/mo default; rulings Q2/Q4 swing it) where the
  household costs electricity.
- The default instance **does not solve cloud voice/coach co-residency** — stated rather
  than hidden; the G7e/split-endpoint step is priced and waiting.
- The cohort ceiling is arithmetic, not a load test — the first busy evening is the real
  receipt, and queueing is the designed degradation.
- Two deployments (household :8100/:8101 + cloud) run in parallel through the pilot — more
  surface for the operator until Lane 6 retires the robot's table-mode tail.

## The ruling asks that belong here (only Rich rules these)

> **RULINGS RECEIVED — Rich, 2026-08-07, in-session (both, as recommended):**
> **Q2: hold the default (Branch A provisional); rule serving once when Lane 1's evals
> land.** **Q4: the D4 ceiling confirmed (≤ ~6 accounts, ~2–3 simultaneous, queueing as
> degradation); on-demand for anything a student touches, spot only for spike/batch.**
> (Q1/Q3/Q5 ruled in ADR-033 the same session.) **Status remains Proposed** pending
> Rich's ICO/AWS hand-verification, then the pair ratifies together.

Everything above is decided on the record. These two are genuinely his; each carries this
draft's recommendation. (Q1, Q3 and Q5 are ADR-033's; ruling-queue item 5 is discharged by
ruling all five and ratifying the pair.)

- **Q2 — Fine-tune vs stock serving for the pilot** (already ruling-queue item 3; Lane 1's
  eval rerun is the evidence — rule once, over the full field). **Both branches, honestly:**
  - **Branch A — the fine-tune, self-hosted:** EC2 g6.xlarge London, $70–75/mo (spot ~$30).
    Keeps the fine-tune and UK residency together. **Blocked before deploy** (not before
    ruling) by ADR-031 D4.2: the base-model licence identity conflict must resolve before
    the fine-tuned weights are hosted off-premises (honest registers).
  - **Branch B — stock Gemma 4 26B-A4B on Bedrock serverless:** ~$1–5/mo at pilot volumes,
    no weights hosting (D4.2 becomes moot for serving), no GPU to operate — but it exists
    in **Frankfurt, not London**, so choosing it *is* choosing "EU-adequate over
    UK-resident", collapsing into ADR-033's Q1. Worth naming: the only scored blind eval
    (2026-05-18) favoured the base model — Branch B is not obviously the worse tutor.
  - **Recommendation: hold the default (Branch A) until Lane 1's evals land, then rule Q2
    and Q1 together, once.** D4's sizing is written so a Branch-B ruling changes the
    instance table, not this ADR's account model.
- **Q4 — The cohort ceiling + spot-vs-on-demand appetite.** Spot instances save ~$40–45/mo
  but can be interrupted mid-session — mid-homework, for a child, which law 7's
  "nothing that ends a session sad" weighs against. **Recommendation: confirm the D4
  ceiling (≤ ~6 accounts, ~2–3 simultaneous sessions, queueing as the degradation mode) and
  rule on-demand for anything a student touches; spot only for the spike and batch work.**
  Growth past the ceiling is a governance event (ADR-031 scale tripwire + ADR-033), not a
  quiet resize.

## On-ratification checklist (performed at ratification, not before)

Supersession lands via this checklist — no existing file is edited before Rich ratifies:

1. Flip this ADR's status to *Accepted — RATIFIED by Rich, {date}*, recording his rulings
   on Q2 and Q4 inline (and cross-recording Q1/Q3/Q5 outcomes from ADR-033's ratification —
   the pair ratifies as ruling-queue item 5).
2. **Dated note onto ADR-ARCH-014** (never a silent edit): "Runtime clause (single-user
   only) superseded by ADR-ARCH-034 D4 ({date}); the Bedrock inference scale-out escape
   hatch is retired as dead (Custom Model Import cannot serve the fine-tune — AWS research
   §2); the multi-student schema posture STANDS and is vindicated by ADR-034 D1's receipts."
3. **Plan updates:** mark Lane 3 step 2's cell moved; **correct plan:233's "runbook
   exists" to "runbook to be written — ADR-034 D3"**; strike the multi-user half of
   ruling-queue item 5; record the Q2/Q4 rulings where the plan tracks them.
4. Confirm ADR-033's checklist items that this ADR depends on are done in the same pass
   (the ADR-015/028 dated notes; the consent-record spec is ratified there).
5. State the S0–S4 effect per the mission's reporting rule (this ADR moves S3 rung 2's
   multi-user half; S0's pilot leg becomes reachable).

## What would change this posture

Any of these reopens this ADR (dated amendment or supersession — never silent edits):

1. **Scale** beyond the named close-friends cohort or the D4 ceiling — the sizing, the
   DPIA (ADR-033 D8), and ADR-031's scale tripwire all trigger together; open signup is
   forbidden outright (`registrationAllowed: false` is posture).
2. **A Q2 ruling for stock Bedrock serving** — D4's instance economics are replaced by
   managed serving, and the region consequence amends ADR-033 D2 *first* (its "what would
   change" item 3), never after the fact.
3. **A second concurrent tutor context becomes a real need** (the queueing degradation
   proves unacceptable in practice) — the G7e / split-endpoint step is taken as a dated
   amendment with new numbers.
4. **Any cross-account feature request** — sharing, comparison, visibility — is refused by
   mission law 7 and ADR-031 leg 3; this posture is void for that design, and the mission
   says never.
5. **The attended voice walk fails** (D5) — voice stays off in Keycloak mode and the
   contradiction with the seam receipts goes to Rich.
6. **The robot's Lane 6 re-point lands** — D8's table-mode tail retires by Lane 6's own
   decision, noted here so nobody mistakes the tail for permanent.
7. **Consent is withdrawn for any account** — the ADR-033 D6 erasure path runs via the D3
   deprovisioning runbook; recorded so the consequence is never a surprise.

## Honest registers

- **Not legal advice.** Same register as ADR-031 and ADR-033: a recorded, owner-ratified
  posture drafted by a non-lawyer for a free family pilot. The consent-law facts this ADR's
  D6 leans on live in ADR-033 (D5) and carry that ADR's **hand-verify-before-ratification**
  caveat: the ICO's own pages refused automated fetching in the 2026-08-07 design pass —
  Rich (or the session he attends) verifies them by hand before ratifying the pair.
- **Nothing-in-code-today, itemised so ratification is informed:** no consent table, no
  consent gate, no consent strings in app or backend (D6); no friend-provisioning or
  deprovisioning runbook (D3 — and the plan currently claims otherwise, corrected here);
  no per-account corpora, no student-dimension registry, no per-account AQA inheritance
  tests (D7); no Keycloak-mode voice walk receipt (D5); no erasure primitive beyond the
  dev-flag reset tool (D3). Ratifying this ADR commissions that work; it does not claim it.
- **The ADR-031 D4.2 licence conflict is UNRESOLVED and blocks the DEPLOY step.** The
  base-model licence identity conflict (hackathon writeup says Apache 2.0; `licensing.md`
  says Gemma Terms of Use — `licensing.md:92–93, :226`) is a logged Lane 3 precondition. It
  does **not** block drafting or ratifying this ADR, but it **does** block hosting the
  fine-tuned weights on AWS (Q2 Branch A's deploy step) until resolved. Q2 Branch B
  sidesteps it for serving — at the price of the Frankfurt residency consequence.
- **The cohort ceiling is arithmetic, not a receipt** (D4): derived from one L4's memory,
  the ~17 GB GGUF residency, and the N×1 load shape — no multi-user load test has run
  anywhere. Law 8 is satisfied by saying so, and by queueing being the designed failure
  mode rather than an outage.
- **Broker isolation was standing for this drafting pass** (no NATS connection of any
  kind); nothing in this ADR touches or requires a message broker.

## C4 diagram re-review status

No structural change **now** — this is a drafted posture; today's topology is untouched and
multi-user adds **no new container**: the same backend, identity server, database, and
model server serve more rows (D1). The C4 re-review gate is triggered by the Lane 3 step 3
cloud deployment (ADR-033 carries that inheritance from ADR-029 — L1/L2 regenerate for the
AWS topology); this ADR adds one requirement to that same regeneration: the two-deployment
transition state (household :8100 robot tail + cloud pilot, D8) must appear honestly until
Lane 6 retires it.

## References

- Mission: [study-tutor-mission-statement-2026-08-01.md](../../study-tutor-mission-statement-2026-08-01.md)
  — "Who it serves" (the cohort, never social); laws 4 (D7), 5 (D7), 6 (D6), 7 (D1, D4, Q4);
  measurables S0/S3; dated note 1 (Dulcie).
- Plan: [study-tutor-plan-of-record.md](../../study-tutor-plan-of-record.md) — Lane 3
  step 2 (this cell); :216–217 (concurrency belongs here); :218–222 (consent-in-onboarding
  direction); :233 (the corrected "runbook exists" claim); :32 (voice-off reason); Lane 6
  step 1 (the robot re-point D8 waits on).
- [ADR-ARCH-033](ADR-ARCH-033-pilot-residency-governance-eu-west-2.md) — sibling: D5 (the
  consent record this D6 implements), D6 (the erasure path D3/D7 join), Q1/Q3/Q5.
- [ADR-ARCH-014](ADR-ARCH-014-single-user-scalability-posture.md) — the superseded runtime
  clause + dead Bedrock hatch; the vindicated schema posture.
- [ADR-ARCH-028](ADR-ARCH-028-keycloak-idp-nas-placement-tailnet-tls.md) — the Keycloak
  build; users-never-in-git (D1 rule).
- [ADR-ARCH-029](ADR-ARCH-029-phased-productionisation-local-first-cloud-native-target.md)
  — D2 portability seams (env-driven config, deploy-agnostic `TokenResolver`,
  realm-as-code) that make D2/D5 flips.
- [ADR-ARCH-031](ADR-ARCH-031-pilot-uploads-copyright-posture.md) — legs 1 (D6), 2/5 (D7),
  3 (law-7 reinforcement), 4 (per-account AQA inheritance); the scale tripwire (Q4); the
  D4.2 licence precondition.
- [ADR-ARCH-032](ADR-ARCH-032-subject-scoped-rag-per-subject-collections.md) — the
  subject-keyed collection design D7 extends with the student dimension.
- [aws-production-hosting-research-2026-07-06.md](../../research/ideas/aws-production-hosting-research-2026-07-06.md)
  — §2 (Bedrock Custom Model Import dead ×3), §4–§5 (the D4 price table), §8.4 (the spike).
- Tenancy/isolation receipts: `src/study_tutor/knowledge/store/schema_reference.sql` (head
  `346cd366b66e` — partition :12–14, `session_one_active_idx` :70–73);
  `src/study_tutor/knowledge/store/postgres.py` (the ~28 student-scoped call sites; gamification
  :938, :962, :975, :991; the dev-only reset :761–806); the 2026-08-04 live isolation run
  (plan, Suites row).
- Identity/provisioning receipts: `deploy/keycloak/realm/study-tutor-realm.json`;
  `deploy/keycloak/provision-live-suite.sh` (:87–99 mapper; the D3 template);
  `RUNBOOK-study-tutor-keycloak-standup.md` (:202, :339 non-overwriting import; :206–252
  manual user creation); `src/study_tutor/cli/main.py` (:1218 single process; :1221–1270
  `seed-students`); `src/study_tutor/http/oidc_config.py` (:50, :86–100);
  `src/study_tutor/http/auth.py` (:27–47, :51–79); `src/study_tutor/http/auth_keycloak.py`.
- Voice receipts: `src/study_tutor/http/app.py` (:757–766, :788–791 mount gate);
  `src/study_tutor/voice/config.py` (:57); `deploy/http/.env.kc` (:6 — the off switch);
  `src/study_tutor/http/ws.py` (:4 — upgrade auth through the shared seam);
  `docs/runbooks/evidence/keycloak-kcg3-2026-07-19/EVIDENCE.md` (:10 — KC-G3 pass).
- Concurrency receipts: `HANDOFF-study-tutor-full-encapsulation-spark.md` (:133–135 — the
  measured memory law); `deploy/http/docker-compose.yml` (:63–66 — the baked corpus image).
- Contract: `docs/design/contracts/API-session-http-binding.md` §7 — the additive/addendum
  discipline D6 lands under.

---

*This ADR is not legal advice; it is the project's recorded multi-user posture for the
friends pilot, drafted 2026-08-07 for Lane 3 step 2 as the sibling of ADR-ARCH-033. Every
load-bearing claim names its in-repo receipt or is itemised in the honest registers as
not-yet-real. Ratification — and rulings Q2 and Q4 — are Rich's alone.*
