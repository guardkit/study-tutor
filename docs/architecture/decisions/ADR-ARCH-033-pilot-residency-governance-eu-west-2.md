# ADR-ARCH-033 — Pilot residency & governance: UK cloud posture (AWS eu-west-2) for a minor's data, superseding the household-only scope

## Status

**Accepted — RATIFIED by Rich, 2026-08-13 (in-session word: "ratify"), with all five
rulings banked 2026-08-07 as recorded in the ruling-asks section (Q1 UK-only eu-west-2;
Q2 hold serving for Lane 1's evals; Q3 extend sops; Q4 ≤ ~6 accounts, on-demand for
students; Q5 documented backup-roll).** Hand-verification receipt: the five primary
sources were exported by Rich to `docs/research/ICO/` (2026-08-13) and verified against
this ADR's claims — four of five confirmed verbatim from the originals (age-13 consent,
one-month erasure + child-ISS ground, DUAA s81, the AWS UK Addendum's self-executing
applicability clause; AADC scope + 15 standards); the DPIA-mandatory leg (standard 2)
rests on secondary confirmation and was accepted knowingly in the ratify word — the DPIA
is commissioned regardless (D8). **Pending line RESOLVED same day (2026-08-13, Rich in
the DSM console, screenshot receipt): Hyper Backup is NOT INSTALLED on the NAS** — no
Snapshot Replication or cloud backup either. **The Q5 residual does not exist:** erasure
completes when the 14-day `pg_dump` retention rolls, full stop — cleaner than drafted
(D6.4 carries the dated correction in place). The flip side is a real durability gap —
the learner data's only copies live on one physical box — ledgered in
`known-issues.md` the same day. *Drafted 2026-08-07.*

This is the residency/governance rung of the mission's S3 pilot-readiness ladder
(mission [S3](../../study-tutor-mission-statement-2026-08-01.md), lines 140–143):
copyright ratified (ADR-ARCH-031, 2026-08-02) → **this ADR ratified** → cloud spike →
deployed stack green → upload flow → first external session. The copyright rung is done, so
this rung is unblocked to draft and ratify (ADR-ARCH-031 status block). Ratification is
**Rich's act alone**. This draft decides everything the record already supports; the ONLY
items left open are the five ruling asks in [§The five ruling asks](#the-five-ruling-asks-only-rich-rules-these),
each presented with a recommendation. Nothing else is asked of him — no file edits, no
review pass; supersession notes land via the [on-ratification checklist](#on-ratification-checklist-performed-at-ratification-not-before)
inside this draft.

**Plan cell:** [study-tutor-plan-of-record.md](../../study-tutor-plan-of-record.md)
**Lane 3, step 1** ("The residency/governance ADR") — per the mission's no-orphan-docs rule,
this draft attaches to that cell and the coordinator updates it at ratification.
**Date:** 2026-08-07
**Commissioned by:** [ADR-ARCH-029](ADR-ARCH-029-phased-productionisation-local-first-cloud-native-target.md)
D4 (the Phase 3 data-governance surface, ADR-029:92–96) and mission **law 2** (cloud is a
governed posture change requiring exactly this ADR before any student data moves,
mission:84–89).
**Supersedes (on ratification, cloud/pilot scope only):**
[ADR-ARCH-015](ADR-ARCH-015-uk-on-device-data-residency.md) (UK on-device residency).
ADR-015 **remains the record for the household deployment while it runs** — the spark (the
household NVIDIA DGX Spark box currently serving the tutor) and the NAS (the family's
Synology network-attached-storage server, hostname `whitestocks`) keep their posture. The
supersession map is D1.
**Amends (on ratification):** [ADR-ARCH-028](ADR-ARCH-028-keycloak-idp-nas-placement-tailnet-tls.md)'s
"ADR-015 rules out any cloud IdP" reading (ADR-028:26–27, :105–106) — relaxed per D4 below;
ADR-029:33–35 already called that reading stricter than 015 requires.
**Related:** [ADR-ARCH-031](ADR-ARCH-031-pilot-uploads-copyright-posture.md) (the copyright
posture whose five legs D10 inherits, and whose D4.2 open licence item is flagged in the
honest registers); ADR-ARCH-034 (multi-user/tenancy — the sibling draft in this same pass;
consent-in-onboarding mechanics and the erasure API-verb decision land there);
[aws-production-hosting-research-2026-07-06.md](../../research/ideas/aws-production-hosting-research-2026-07-06.md)
(the costed research this ADR's numbers come from);
`src/study_tutor/knowledge/store/schema_reference.sql` (canonical database schema, head
`346cd366b66e` — the erasure-cascade receipt).

## Context

The friends pilot (plan Lane 3) moves a minor's tutoring data — full session transcripts,
topic-confidence history, misconceptions, gamification state — off household hardware and
onto AWS for the first time. Mission law 2 makes that a governed posture change: it
requires this ADR to cover **residency region, encryption, a consent record, and an erasure
path** before any student data moves. ADR-029 D4 commissioned exactly this surface and
named it the productionisation portfolio artifact: *"UK region residency (`eu-west-2`),
encryption at rest + in transit, a minimal parental-consent record, data minimisation …
and a documented data-subject-rights/erasure path. This surface IS the portfolio artifact"*
(ADR-029:92–96).

Two things changed since ADR-015 (2026-04-18) wrote the household posture:

1. **The product changed.** ADR-015 governed one student on household hardware. The pilot
   is multiple accounts (Lilymay, her sister Dulcie in prospect, close friends), each with
   uploaded scans of their own books, hosted on third-party infrastructure. ADR-031 settled
   the copyright half of that; this ADR settles the data-protection half. ADR-031's own
   division of labour: it "does not decide residency/encryption/consent mechanics" — this
   ADR does (ADR-031 D1).
2. **The law changed.** The Data (Use and Access) Act 2025 (DUAA, Royal Assent 2025-06-19,
   s81) amended UK GDPR Article 25 so that the higher protection of children in service
   design/default — previously the ICO's Age Appropriate Design Code ("Children's Code")
   as guidance — is now a statutory requirement; the ICO's children's guidance was updated
   2026-05-15. The relevant standards: best interests of the child; high privacy by
   default; profiling off by default; data minimisation; restraint in nudge techniques;
   child-comprehensible transparency; tools for children to exercise their rights. (These
   facts were web-confirmed via search and commentary in the Lane 3 design pass; the ICO's
   own pages refuse automated fetching — see the honest registers: **hand-verify before
   ratification**.)

The database makes the subject-matter unambiguous: the `student` table's `year_group`
column carries a CHECK constraint restricting it to years 7–13 (`schema_reference.sql`,
head `346cd366b66e`) — **every account in this system is a school-age minor's account by
construction**. This ADR is written for that fact, not around it.

## Decision

### D1 — Supersession map: what dies, what carries, what closes

ADR-015 is superseded **for cloud/pilot scope**; it remains in force for the household
deployment while that runs. Item by item:

1. **The residency table (ADR-015:45–53) is restated wholly by this ADR** — it no longer
   describes the system (FalkorDB is gone since ADR-023; the retrieval corpus — the
   ChromaDB vector store — is now baked into the deployed container image, not on a
   MacBook). D2 and D6 below are the current statement of where data lives and how it
   leaves.
2. **The Gemini exception (ADR-015:55–68) is CLOSED, not carried.** It existed for
   Graphiti entity extraction; [ADR-ARCH-023](ADR-ARCH-023-student-model-postgres-jsonb-drop-graphiti.md)
   dropped Graphiti and moved the student model to study-tutor-owned Postgres (ADR-023:83).
   No third-party model sees any student data today, and this ADR does not reopen that
   door.
3. **The Bedrock exception and its non-UK fallback (ADR-015:70–85) are DEAD.** Bedrock
   Custom Model Import cannot serve the fine-tune, three ways (AWS research §2:27–46): no
   Gemma of any generation on the supported-architecture list plus a 128K positional cap
   against Gemma 4's 256K; Custom Model Import exists only in us-east-1/2, us-west-2 and
   eu-central-1 — not eu-west-2; and no roadmap signal. The hackathon-era "us-east-1 as
   demo-week fallback" is withdrawn with it. The pilot posture is UK-only (D2; Rich's Q1).
4. **The no-third-party-telemetry clause CARRIES FORWARD VERBATIM:** "**No** telemetry,
   analytics, error reporting to any third-party service (Sentry, LogRocket, etc.) in any
   phase" (ADR-015:87–88). This clause
   survives the supersession word for word and binds the cloud deployment identically.
   (The mission independently forbids it, mission:154–155.)
5. **ADR-028's "rules out cloud IdP" reading is relaxed** — see D4.

### D2 — Residency: AWS eu-west-2 (London); UK-only, no non-UK fallback *(recommended; the region question is Rich's Q1)*

All pilot student data — the Postgres database (RDS, AWS's managed Postgres), the identity
server, the per-account retrieval corpora, model weights, backups — resides in **AWS
eu-west-2 (London)**, the UK region, per ADR-029 D1 (:54–56) and the costed research's
recommended default (EC2 g6.xlarge London + llama.cpp with stop/start scheduling, ~$70–75/mo
at ~61 h/mo, spot ~$30/mo — research §4–§5:66–71).

The research's §6a decision point is answered as a recommendation: **UK-resident is treated
as non-negotiable for the pilot**. EU-adequate regions (Hugging Face Endpoints in Ireland
~$49/mo; SageMaker or stock-Bedrock in Frankfurt) are lawful under the UK adequacy
arrangements but weaken the exact sentence this project wants to be able to say — *a UK
minor's tutoring transcripts never leave the UK* — for a saving on the order of $25/mo.
That trade is Rich's to rule (Q1); this draft recommends UK-only.

Deploy-time operational guards from the research §7 ride with this decision: a billing
alarm as a pre-flight, a per-phase registry of billable resources, and gate-verified
zero-orphan teardown after the spike (§8.4: one evening, ~$5).

### D3 — Encryption: TLS in transit everywhere; KMS-backed encryption at rest — an honestly NET-NEW commitment

Stated honestly, because the record demands it:

- **In transit today:** everything rides the tailnet (the household's private Tailscale
  mesh VPN, itself WireGuard-encrypted); Keycloak (the self-hosted login/identity server)
  has a real Let's Encrypt certificate on :8443 (ADR-028 D2); but the app API itself is
  **plain HTTP** on :8100/:8101 inside the tailnet. The plan already names the fix as new
  Lane 3 work: "TLS/domain (app base-URL rebuild, cleartext-HTTP fix)" (plan:223–224).
  **This ADR makes it binding:** the cloud deployment terminates TLS at an ALB (AWS's
  load balancer) with an ACM certificate (AWS Certificate Manager) — the ADR-029 D3
  replacement for the `tailscale cert` scaffolding — and **no student data crosses any
  network segment outside the household tailnet unencrypted, ever**.
- **At rest today: NONE.** No disk or database encryption exists anywhere in the current
  deployment — the Postgres runbook's only use of cryptography is generating a password.
  Encryption at rest is therefore a **net-new commitment**, not a port: the cloud
  deployment enables KMS-backed encryption (AWS Key Management Service, keys in
  eu-west-2) on **RDS** (the database), **EBS** (the compute host's disks, which hold the
  model weights and the baked corpus image), and **S3 with SSE-KMS** (any object storage:
  weights staging, uploaded scans, backups). This is a hard deploy gate for Lane 3 step 3:
  no student row lands on an unencrypted volume.

### D4 — Cloud OIDC unblocked; Keycloak remains the identity provider

Superseding ADR-015 for cloud scope mechanically removes the constraint ADR-028 leaned on:
ADR-028 rejected any cloud IdP *because* "ADR-015 rules out any cloud IdP" (ADR-028:26–27,
:105–106). ADR-029 already called that reading over-strict (:33–35) and marked it "the
Phase-2 posture, relaxed in Phase 3" (ADR-028 trajectory note). **This ADR says so
explicitly: cloud-hosted OIDC is now permitted** for the pilot, inside the D2/D3 posture
(eu-west-2, encrypted, no third-party telemetry).

The Cognito-vs-Keycloak choice ADR-029 deferred into this ADR (:109–111) is decided on
ADR-029's own recorded reasoning: **Keycloak stays** — Keycloak-on-cloud ports the
realm-as-code JSON unchanged, the users-never-in-git rule means **no PII to migrate**
(ADR-029 D2), the `TokenResolver` validation seam is already deploy-agnostic (swapping
issuer/JWKS URLs is pure config), and it tells the cleaner "same system, managed infra"
portfolio story. Cognito remains a recorded alternative, not the decision.

### D5 — The parental-consent record: consent captured in onboarding, for every pilot account, regardless of age

Per Rich's 2026-08-01 direction (plan:218–221): the parental-consent record ADR-029 D4
names is **captured in the pilot onboarding flow itself — a signed step before a friend's
first session, not paperwork on the side**. ADR-031 leg 1 puts the "we own the physical
copy of what we upload" attestation in the same step: **one onboarding step, two records**
(consent + ownership attestation).

The honest legal framing, recorded so nobody later mistakes policy for obligation:

- **The UK consent threshold is 13** (UK GDPR Article 8 as enacted): a child of 13 or over
  can consent to information-society services for themselves; under-13 requires consent
  from a holder of parental responsibility, with reasonable verification effort.
- **Lilymay and her close friends are over 13**, so parental consent is **not legally
  compelled** by Article 8 for them. Requiring it anyway is a deliberate above-the-minimum
  choice — which ADR-029 D4 and mission law 2 already committed to, and which the
  Children's Code's best-interests standard supports.
- **Dulcie (Year 8) may sit under the 13 line** when she joins, in which case parental
  consent stops being optional for her account. The uniform rule below absorbs both cases.

**The rule: every pilot account carries a parental-consent record before its first
session, regardless of the student's age.** No consent record, no session. Nothing of this
exists in code today — no consent strings in the app or backend, no consent table — so
this ADR specifies the record and the sibling multi-user draft (ADR-ARCH-034) carries the
onboarding mechanics as an **additive** contract change (mission law 6 — additive verbs or
addenda, never a shape change to the frozen six):

- A consent table keyed by `student_id`: the consenting adult's name and relationship,
  timestamp, the privacy-notice version consented to, the ADR-031 leg-1 ownership
  attestation flag, and a withdrawal timestamp (nullable).
- A hard gate: session start is refused for any account without a current consent record.
- Consent withdrawal triggers the D6 erasure path.
- The consent basis implies its counterpart deliverable: a **child-comprehensible privacy
  notice** (a Children's Code transparency standard), versioned so the consent record can
  name what was consented to.

The Keycloak realm already reserves a `parent` role ("reserved for future use",
`deploy/keycloak/realm/study-tutor-realm.json`) — the natural carrier if consent is ever
exercised through an account rather than a signed onboarding step; noted, not built.

### D6 — The erasure path, end to end, with a published SLA of 30 days or less

UK GDPR gives erasure one month (extendable in complex cases with notice), and Article
17(1)(f) singles out data collected from children using online services. **The published
SLA for this pilot: complete erasure within 30 days of a verified request or consent
withdrawal.** The path, component by component, with receipts:

1. **Postgres — one statement, by construction.** All eight tables hang off
   `student(student_id)`: `topic_confidence`, `misconception`, `session`, `achievement`,
   `topic_confidence_history`, and `quest` reference it with `ON DELETE CASCADE`, and
   `session_turn` (the full verbatim transcript, turn by turn) cascades via `session`
   (`schema_reference.sql`, head `346cd366b66e`). Therefore
   `DELETE FROM student WHERE student_id = :sid` **erases the entire Postgres footprint of
   a student in one statement** — the schema was built for this.
2. **Keycloak identity — mandated runbook step.** The identity server's users live in its
   own co-located database (ADR-028 D1), are hand-created and never in git; deletion today
   is a manual admin-console act with **no runbook step**. This ADR mandates one: the Lane 3
   step 5 provisioning runbook MUST carry a deprovisioning half — Keycloak user deletion
   paired with the Postgres delete.
3. **Per-account retrieval corpus — inherits ADR-031 legs 2 and 5.** Today there is one
   shared subject-keyed corpus baked into the container image; **per-account corpora do
   not yet exist** (collections are keyed by subject, not student —
   `src/study_tutor/knowledge/retrieval.py:461, :464–478`). ADR-031 legs 2 and 5 require
   per-account collections whose deletion deletes the account's corpus. This ADR binds the
   requirement into the erasure path: the Lane 3 step 4 tenancy design (specified in
   ADR-ARCH-034) MUST make "delete the account" delete that account's collections and any
   stored upload artifacts. (Shared public-domain texts are exempt — they are nobody's
   personal data.)
4. **Backups — erasure completes when backups roll.** The NAS nightly `pg_dump` covers
   both the study-tutor and Keycloak databases with **RETENTION_DAYS=14**
   (`deploy/postgres/backup.sh:21–22, :61, :79, :90–92`), so a deleted student persists in
   dumps for at most 14 days — comfortably inside the 30-day SLA; the arithmetic is the
   SLA's honest basis, and the cloud deployment MUST preserve it: any managed backup
   (RDS automated snapshots) carries a documented retention of at most 14 days, or the SLA
   is recomputed and republished. **Named residual:** Synology Hyper Backup (the NAS's
   volume-level backup tool) implicitly copies the backups directory too
   (ADR-028:79; `RUNBOOK-study-tutor-postgres-deploy.md:162–169`) — an additional copy
   whose own retention is not dated in this repo. That residual is Rich's **Q5**: accept
   "erasure completes when backup generations roll, documented" or require an active purge.
   > **Dated correction (2026-08-13, verified by Rich in the DSM console):** Hyper
   > Backup was NEVER INSTALLED (nor Snapshot Replication, nor any cloud backup) — the
   > "implicit volume-level copy" inherited from ADR-028 never existed. **The Q5
   > residual is nil**: the 14-day dump roll is the complete backup half of the erasure
   > story. The corresponding durability gap (no off-box copy of non-reindexable
   > learner data) is ledgered in `known-issues.md` with its exit path.
5. **Voice audio — nothing to erase, ever, and say it loudly:** no voice recording is
   persisted anywhere in this system. Audio chunks live in an in-memory store with a TTL
   (`src/study_tutor/voice/service.py:154–186`) and the streaming design states the
   invariant outright: "Never-at-rest … audio bytes flow only through memory"
   (`src/study_tutor/voice/streaming_tts.py:10`). A child's voice is the most identifying
   thing this system touches and it never touches a disk.
6. **An erasure primitive must exist.** Today the only deletion code is a dev tool —
   `PostgresStudentStore.delete_sessions_for_student` behind a dev-flag-only
   `POST /__dev__/reset` (`knowledge/store/postgres.py:761–806`; `http/app.py:591–618, :752–755`) —
   which spares XP/streak/confidence and is **not** an erasure path. This ADR mandates a
   real one before the first external account: at minimum an operator runbook executing
   steps 1–3 above; whether it also becomes an additive API verb is ADR-ARCH-034's surface
   decision (law 6 either way).

### D7 — Data minimisation: restated from what is already true

The system's minimisation posture is not aspiration; it is the current build, restated
here as binding (receipts in brackets):

- Identity crosses the auth boundary as a **`student_id` claim** — an opaque ID, not a
  name (the KC-D3 habit ADR-029 D4 cites; the protocol mapper in
  `deploy/keycloak/provision-live-suite.sh:87–99`).
- **No third-party telemetry, analytics, or error reporting** — the D1.4 carried clause.
- **Voice audio never at rest** (D6.5).
- **No cross-student reads anywhere**: every student-scoped query in the store carries the
  `student_id` partition; there is no cross-student aggregation in the codebase — which is
  also mission law 7's guarantee (no leaderboards, no comparison) and serves as this
  system's mitigation of the Children's Code's nudge-restraint standard: streaks and
  quests are nudge-adjacent, and law 7's kindness rules (no punishment mechanics, nothing
  that ends a session sad, no social comparison) are the recorded mitigation.
- The student model (topic confidence, misconceptions) exists **solely to deliver the
  tutoring the family signed up for** — it is never used for advertising, recommendation
  beyond the tutor's own next-topic planner, or any purpose outside the session loop, and
  is never shared between accounts.

### D8 — The DPIA is commissioned as a named deliverable

A Data Protection Impact Assessment (DPIA) is **mandatory** here — Children's Code
standard 2 requires one for online services likely to be accessed by children, and this
service is *for* children by construction (the year 7–13 CHECK). This ADR commissions it
as a **named Lane 3 deliverable**: drafted alongside the cloud spike, completed before the
first external student session, and kept in-repo. It is arguably the stronger portfolio
artifact than the deployment itself — ADR-029 D4's "this surface IS the portfolio
artifact" lands most concretely as a real DPIA for a real minors' service.

### D9 — Roles and the data-processing agreement: Rich is controller; AWS is processor; the AWS UK GDPR Addendum is the DPA

- **Rich is the data controller** — he determines purposes and means (a free family pilot
  of a tutoring service). ADR-029 already named Phase 3 as taking on "real data-controller
  responsibilities" (:127–128); this ADR is that name becoming a role.
- **AWS is a data processor** — infrastructure only; AWS does not access content.
- **The DPA requirement is satisfied by contract of adhesion:** the AWS UK GDPR Addendum
  applies automatically through the AWS Service Terms to UK-establishment customers — no
  negotiation, nothing to sign. Recorded here so the compliance story is one line, not a
  hunt. (Hand-verify the current Service Terms text at ratification — honest registers.)
- **Lawful basis: consent**, the cleanest fit for a free, named-cohort family pilot (ICO
  Children's Code Annex C territory), implemented as D5's record. Not legal advice; see
  the honest registers.

### D10 — ADR-031's five copyright-posture legs inherited by reference

The five enforced legs of [ADR-ARCH-031](ADR-ARCH-031-pilot-uploads-copyright-posture.md)
D3 bind this posture unchanged: (1) user-owns-the-source attestation in onboarding (joined
to D5's consent step); (2) per-account private retrieval, no pooling of in-copyright
material; (3) no redistribution — no export, no cross-account sharing, no public access;
(4) **AQA assessment material excluded absolutely** — the `AQA_REFUSAL_PATTERN` ingest
gate (`src/study_tutor/knowledge/corpus.py`) and `AQA_FILENAME_PATTERN` retrieval gate
(`src/study_tutor/knowledge/retrieval.py`) are inherited into every per-account pipeline
at both ingest and retrieval; (5) non-commercial, small, removable — account deletion
deletes the account's corpus, which is exactly D6.3 of the erasure path; rights-holder
objection honoured by removal. Cloud hosting changed the governance question this ADR
answers, not the copyright one ADR-031 answered (ADR-031:149–153).

### D11 — Secrets handling: extend the sops pattern *(default; the tooling question is Rich's Q3)*

The repo already has exactly one encrypted-secrets pattern: sops with age keys (sops = an
encrypted-config file tool; age = its keypair encryption), run from a custody root, used
by `deploy/keycloak/provision-live-suite.sh:34–51`. The plan says the cloud move should
"extend the `sops` encrypted-config pattern" (plan:225). **Default decision: extend sops**
for cloud secrets (database DSNs, Keycloak admin credentials, signing material), with the
age key itself protected by KMS as an implementation detail of the deploy. The alternative
— AWS Secrets Manager / SSM Parameter Store — is presented as Q3 if Rich wants to spend a
ruling on it; if not, the plan's wording stands. Either way, the current known gap is
named: `deploy/http/.env.kc` holds a production database DSN with a plaintext password
(0600; gitignored by design, `.gitignore:149`, so the file exists only on the spark host —
this receipt is the 2026-08-07 design-pass inspection, not a repo file) — precisely the
class of thing this decision exists to close before any cloud counterpart is created.

## Alternatives considered

- **Keep the pilot on household infrastructure (no cloud).** Rejected — the spark cannot
  serve a concurrent cohort (single process, one shared model server, ~98 GB of 128 GB
  committed — receipts in ADR-ARCH-034), friends' devices would need household-VPN access,
  and ADR-029 already rejected "on-device permanently" because the governance surface IS
  the productionisation deliverable.
- **EU-adequate hosting (Ireland / Frankfurt) instead of London.** Lawful, cheaper
  (~$25/mo), and rejected as the recommendation because it forfeits the UK-resident
  headline for a minor's transcripts. Presented honestly as Q1 — it is a real option, and
  the stock-Bedrock branch of Q2 would force it (stock Gemma 4 serving exists in Frankfurt,
  not London).
- **Cognito as the pilot IdP.** Considered per ADR-029's deferral; rejected in favour of
  Keycloak-on-cloud (D4) — realm-as-code ports unchanged, no PII migration, deploy-agnostic
  token validation already proven.
- **Ship without encryption at rest (tailnet-equivalent trust in AWS).** Rejected flatly —
  D3 is a hard gate; "we encrypt a minor's data at rest" must be a true sentence before
  the first external row lands.
- **Parental consent only where Article 8 compels it (under-13s).** Rejected — a
  two-track consent rule inside a six-account pilot buys complexity and a weaker story to
  parents; the uniform above-the-minimum rule (D5) is simpler and kinder.
- **A paper consent form outside the product.** Rejected by Rich's 2026-08-01 direction —
  consent is a signed step **in** onboarding, so coverage is by construction, not by
  filing cabinet.

## Consequences

**Positive:**

- Mission law 2's precondition becomes satisfiable: ratify this and the S3 ladder's rung 2
  is climbed in order; the cloud spike (rung 3) is unblocked with a ~$5 one-evening cost.
- The governance surface ADR-029 called the portfolio artifact exists as a real, receipted
  posture: UK residency, KMS encryption, a consent record, a one-statement erasure cascade
  with a published SLA, and a commissioned DPIA.
- ADR-028's cloud-IdP block dissolves without touching its Phase-2 record; the auth build
  ports by config (issuer/JWKS/DSN env values), as ADR-029 D2 designed.
- The erasure story is honest and mostly already built: the schema cascades by
  construction, voice never persists, and the two real gaps (Keycloak runbook step,
  per-account corpus deletion) are named build requirements, not surprises.

**Negative / accepted:**

- **New money:** ~$70–75/mo steady-state on the recommended default (spot ~$30, Q4), plus
  the ~$5 spike — against $0 marginal on household hardware.
- **New obligations:** Rich formally becomes a data controller for other families'
  children, with a published 30-day erasure SLA and a DPIA to write. Manageable at pilot
  scale; this is the real cost of rung 2 and it is accepted knowingly at ratification.
- **Net-new engineering** this posture binds onto Lane 3: TLS end-to-end (the
  cleartext-HTTP fix), KMS everywhere at rest, the consent table + gate, the
  deprovisioning runbook half, per-account corpus deletion, secrets extension. None of it
  is optional once ratified.
- **The 14-day backup residual is inherent** to the erasure design (documented, inside the
  SLA) and the Hyper Backup copy sits behind Q5 until ruled.
- ADR-015 becomes scope-split (household force + cloud supersession) — a reader must hold
  both until the household deployment retires.

## The five ruling asks (only Rich rules these)

> **RULINGS RECEIVED — Rich, 2026-08-07, in-session (all five, as recommended):**
> **Q1: UK-only, eu-west-2, no non-UK fallback** (D2 stands). **Q2: hold the default;
> rule serving once when Lane 1's evals land** (with Q1 already ruled, the stock-Bedrock
> branch is foreclosed unless Q1 is explicitly reopened). **Q3: extend sops** (D11
> stands). **Q4: ≤ ~6 accounts, on-demand for anything a student touches; spot only for
> the spike and batch work.** **Q5: accept the documented-roll posture** (Hyper Backup
> retention to be documented at ratification). **Status remains Proposed:** ratification
> itself lands after Rich's hand-verification of the ICO/AWS pages (his chosen sequence,
> same session) — the on-ratification checklist then executes.

Everything above is decided on the record. These five are genuinely his; each carries this
draft's recommendation. Ruling-queue item 5 is discharged by ruling them and ratifying.

- **Q1 — Is UK-resident non-negotiable, or is EU-adequate acceptable?** London costs
  ~$25/mo more than the cheapest EU option and keeps the headline "her transcripts never
  leave the UK". **Recommendation: UK-only (eu-west-2), no non-UK fallback** (D2).
- **Q2 — Fine-tune vs stock serving for the pilot** (already ruling-queue item 3, informed
  by Lane 1's evals — rule once, over the full field). Economics: self-hosted GPU for the
  fine-tune $70–450/mo depending on tier, vs stock Gemma 4 26B-A4B on Bedrock at roughly
  $1–5/mo for pilot volumes — but stock Bedrock serving is Frankfurt, not London, so this
  branch collapses into Q1. **Recommendation: hold the default (EC2 g6.xlarge London,
  fine-tune) until Lane 1's evals land, then rule both questions together.**
- **Q3 — Secrets tooling: extend sops+age (KMS-wrapped) vs AWS Secrets Manager/SSM.**
  **Recommendation: extend sops per the plan's existing wording** (D11) — no ruling needed
  unless Rich wants to override.
- **Q4 — Cohort ceiling and spot-vs-on-demand appetite.** Spot instances save ~$40–45/mo
  but can be interrupted mid-session — mid-homework, for a child. **Recommendation:
  on-demand for anything a student touches; spot only for the spike and batch work.** The
  cohort ceiling itself is sized in ADR-ARCH-034 (it is also ADR-031's scale tripwire —
  growth beyond the named close-friends cohort reopens the copyright posture).
- **Q5 — The backup-archive residual:** accept "erasure completes when backup generations
  roll, documented" (14-day dumps inside the 30-day SLA; Hyper Backup's volume copy named
  with its retention documented at ratification) vs an active purge of archives on every
  erasure. **Recommendation: accept the documented-roll posture** — an active archive
  purge is operationally painful and the SLA already tells the truth; revisit if any
  archive's retention is found to exceed the SLA window.

## On-ratification checklist (performed at ratification, not before)

Supersession lands via this checklist — no existing file is edited before Rich ratifies:

1. Flip this ADR's status to *Accepted — RATIFIED by Rich, {date}*, recording his rulings
   on Q1–Q5 inline.
2. **Dated note onto ADR-ARCH-015** (never a silent edit): "Superseded for cloud/pilot
   scope by ADR-ARCH-033 ({date}); remains the record for the household deployment while
   it runs; the no-third-party-telemetry clause carries forward verbatim."
3. **Dated note onto ADR-ARCH-028**: "The 'rules out cloud IdP' reading is relaxed by
   ADR-ARCH-033 D4 ({date}); Keycloak remains the IdP; NAS placement remains the Phase-2
   record."
4. **Plan update:** mark Lane 3 step 1's cell moved; strike the residency-ADR half of
   ruling-queue item 5; record the Q1–Q5 rulings where the plan tracks them.
5. Hand-verifications from the honest registers confirmed done (ICO pages, AWS Addendum
   text, Hyper Backup retention).
6. State the S0–S4 effect per the mission's reporting rule (this ADR moves S3 rung 2).

## What would change this posture

Any of these reopens this ADR (dated amendment or supersession — never silent edits):

1. **Money.** Any payment or commercial offering — the consent basis, the proportionality
   arguments, and ADR-031's posture all reset; formal legal advice stops being optional.
2. **Scale** beyond the named close-friends cohort — the DPIA, the sizing, and ADR-031's
   scale tripwire all trigger together.
3. **Region change** — any move of student data out of eu-west-2 (including a Q2 ruling
   for Frankfurt stock serving) must amend this ADR first, not after.
4. **A new third-party data recipient of any kind** — a managed LLM API seeing student
   text, an analytics service, anything — reopens D1.4/D7 by definition.
5. **The law moves** — further DUAA commencements, ICO Children's Code revisions, or an
   adequacy change; re-verify the D5/D6/D8 grounding against the new text.
6. **An erasure request cannot be honoured inside the SLA** — stop-the-line: fix the path,
   then republish the SLA honestly.
7. **Consent is withdrawn for any account** — not a posture change, but the D6 path runs
   and the account ends; recorded here so the consequence is never a surprise.

## Honest registers

- **Not legal advice.** Like ADR-031, this is the project's recorded, owner-ratified risk
  and governance posture — drafted from public guidance by a non-lawyer, for a free family
  pilot. If the pilot ever takes money or scales, professional advice becomes mandatory
  (ADR-031 Option 3's trigger, inherited).
- **Source verification caveat:** the UK-law facts in Context/D5/D6/D8/D9 (DUAA s81 and
  the Children's Code's statutory footing, the Article 8 age-13 threshold, DPIA
  requirement, the one-month erasure clock, the AWS UK GDPR Addendum mechanism) were
  confirmed in the 2026-08-07 design pass via web search and secondary commentary;
  **ico.org.uk refuses automated fetching, so the ICO pages themselves were not read by
  machine. Rich (or the session he attends) must hand-verify the ICO and AWS pages before
  ratification** — checklist item 5 exists for exactly this.
- **The ADR-031 D4.2 licence conflict is UNRESOLVED and blocks the DEPLOY step.** The
  base-model licence identity conflict (the hackathon writeup says Apache 2.0;
  `licensing.md` says Gemma Terms of Use — `licensing.md:92–93, :226`) was logged by
  ADR-031 as a Lane 3 precondition. It does **not** block drafting or ratifying this ADR,
  but it **does** block Lane 3 step 3's deployment of the fine-tuned weights onto AWS
  (hosting the weights off-premises is a distribution-adjacent act) until resolved.
- **Enforcement register, stated for completeness:** the ICO can fine up to £17.5m or 4%
  of turnover; for a free, consented, minimised, UK-resident family pilot the realistic
  exposure is nominal — but the register exists because the obligations are real even
  when the enforcement risk is not.
- **Known gaps this draft does not hide:** the app API is cleartext HTTP inside the
  tailnet until step 3's fix; there is no erasure verb, consent table, or deprovisioning
  runbook today — all are named build requirements above, not existing capabilities.

## C4 diagram re-review status

No structural change **now** — this is a drafted posture; today's topology is untouched.
Ratification alone does not move a container. The C4 re-review gate **is** triggered by the
Lane 3 step 3 deployment this ADR governs: ADR-029 already promised that Phase 3
regenerates L1/L2 for the AWS topology (ALB, ECS/EC2, RDS, cloud OIDC); that promise is
inherited here and lands with the deploy, not with this draft.

## References

- Mission: [study-tutor-mission-statement-2026-08-01.md](../../study-tutor-mission-statement-2026-08-01.md)
  — laws 2 (the commissioning law), 4, 5, 6, 7; measurable S3; the forbids list.
- Plan: [study-tutor-plan-of-record.md](../../study-tutor-plan-of-record.md) — Lane 3
  steps 1–5 (:207–233); ruling-queue item 5 (:311); the sops wording (:225).
- [ADR-ARCH-029](ADR-ARCH-029-phased-productionisation-local-first-cloud-native-target.md)
  — D4 (the commission, :92–96), D1 (:54–56), D2 (portability guardrails), D3 (transients),
  the Cognito deferral (:109–111).
- [ADR-ARCH-015](ADR-ARCH-015-uk-on-device-data-residency.md) — the superseded household
  posture; the carried telemetry clause (:87–88).
- [ADR-ARCH-028](ADR-ARCH-028-keycloak-idp-nas-placement-tailnet-tls.md) — the cloud-IdP
  reading relaxed by D4; the Hyper Backup implicit-copy receipt (:79).
- [ADR-ARCH-031](ADR-ARCH-031-pilot-uploads-copyright-posture.md) — the five inherited
  legs (D3), the division of labour (D1), the D4.2 licence precondition.
- [ADR-ARCH-023](ADR-ARCH-023-student-model-postgres-jsonb-drop-graphiti.md) — the Gemini
  exception's closure (:83).
- [aws-production-hosting-research-2026-07-06.md](../../research/ideas/aws-production-hosting-research-2026-07-06.md)
  — §2 (Bedrock Custom Model Import dead ×3), §4–§5 (costs), §6a (the Q1 decision point),
  §7 (operational guards), §8.4 (the spike).
- Erasure receipts: `src/study_tutor/knowledge/store/schema_reference.sql` (head
  `346cd366b66e`, the cascade + year-group CHECK); `deploy/postgres/backup.sh` (:21–22,
  :61, :79, :90–92); `src/study_tutor/voice/service.py` (:154–186) +
  `src/study_tutor/voice/streaming_tts.py` (:10); `src/study_tutor/knowledge/store/postgres.py`
  (:761–806) + `src/study_tutor/http/app.py` (:591–618, :752–755) — the dev-only reset;
  `src/study_tutor/knowledge/retrieval.py` (:461, :464–478) — subject-keyed collections.
- Secrets receipt: `deploy/keycloak/provision-live-suite.sh` (:34–51).
- ADR-ARCH-034 (sibling draft, same pass) — multi-user scope: onboarding mechanics,
  erasure-verb surface decision, cohort sizing.
- External (hand-verify before ratification — see honest registers): ICO Age Appropriate
  Design Code + children's-consent + right-to-erasure + DPIA standard-2 + Annex C pages;
  UK GDPR Article 8; DUAA 2025 s81; AWS UK GDPR Addendum + AWS Data Processing Addendum.

---

*This ADR is not legal advice; it is the project's recorded governance posture for moving
a minor's data to the cloud (mission law 2), drafted 2026-08-07 for Lane 3 step 1. Every
load-bearing claim names its in-repo receipt or is flagged for hand-verification in the
honest registers. Ratification — and the five rulings — are Rich's alone.*
