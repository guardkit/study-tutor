# Study Tutor — mission statement (source of truth #1 for this repo)
## 2026-08-01 · living · **RATIFIED — Rich, 2026-08-01 ("happy to sign off", in-session). This document is BINDING; amendments by dated note, never silent edits.**

> **THE TWO SOURCES OF TRUTH for study-tutor (read these first, every session; everything
> else in this repo is subordinate):**
> **(1) THIS mission — why the tutor exists, who it serves, the laws, the measurables.**
> **(2) THE PLAN — what to do next: [`study-tutor-plan-of-record.md`](study-tutor-plan-of-record.md).**
> Any other doc (ADRs, contracts, runbooks, research, handoffs) is INPUT to these two, not a
> substitute. If a decision isn't reflected here or in the plan, it will be overlooked —
> update THESE, don't write another orphan doc. The root `CLAUDE.md` points every session
> here. The software-factory side of this repo's life is governed by ai-transition's own pair
> (`software-factory-mission-statement-2026-07-25.md` + `software-factory-plan-of-record.md`);
> this mission governs the PRODUCT.

## The one-minute version

Study Tutor is a **private, self-hosted, Socratic GCSE tutor for a real student** — Lilymay,
AQA, Year 11 from September 2026 (exams summer 2027). It teaches by questioning, refuses to
just hand over answers, and keeps every word of a minor's data on hardware the family
controls. Private tutoring costs £25–50/hour and cloud AI tutors ship a child's data to
someone else's servers; this is the third way, and its marginal cost is the electricity.

**Receipted today:** cross-device tutoring sessions device-walked on Android with tap-to-talk
voice (live acceptance 2026-07-05; auth on a real device 2026-07-19); a gamification economy
settled by a real session (2026-07-26); the phone's live mirror of a robot-driven session
(2026-07-31). **Not yet real, said plainly:** daily habitual use is not yet established (one
receipted gamified session); retrieval — and with it live quote verification — is
code-complete but OFF in production; the robot's re-point to the current backend host is
unverified. The destination is daily use across phone, voice, and the Reachy Mini robot —
then **the same tutor across her other subjects, grounded in the family's own study
materials, piloted with her close friends**: each with their own account, their own uploaded
books, and the same privacy guarantees. "Every family should be able to have this" is the
long line; Lilymay's household and her friends are the proof.

Study Tutor is also **the software factory's destination of record** (Rich's word,
2026-07-31, ai-transition plan): the full-capability bar the factory builds, verifies, and
deploys against. The two identities reinforce: the factory ships this product; this product
proves the factory.

## Who it serves

- **Lilymay** — the student. Robert Blake School, AQA across all subjects (English Language
  8700 / Literature 8702, Maths, French 8652, Spanish 8692, History, Triple Science). Year 10
  in 2025/26, Year 11 from September 2026. Age 14–15: every surface is age-appropriate,
  encouraging, patient.
- **The pilot cohort** — Lilymay's close friends, each a Keycloak account with their own
  student model and their own study materials. Multi-user, never social: no leaderboards,
  no comparison, no visibility into each other's work — by design, forever.
- **Rich** — the operator and owner. Attended steps (deploys, ingests, gates) are his;
  the product must never require him mid-session.
- **The factory** — this repo is its proving ground (builds, contracts, gates, deploys land
  here first at full strength).

## What it is

One Python backend (`src/study_tutor/`) and one Flutter app (`app/`) in a monorepo, plus the
robot integration in the `fleet-gateway` repo (which lives on the robot's own host, not as a
checkout beside this one):

- **The tutor**: a locally-served tutor model behind a Player–Coach loop — an async coach
  reviews every turn, a deterministic planner picks the next weakest topic, and a quote
  verifier gates every citation against the ingested corpus (verifier: code-complete, off in
  production until retrieval is on — measurable S2). Current serving is the fine-tuned
  Gemma 4 26B-A4B; fine-tune-vs-base is an **open ruling** the plan's Lane 1 evals inform.
  Where it serves from is deployment posture (law 2), not identity.
- **The student model**: study-tutor-owned Postgres — sessions, topic confidence,
  XP/levels/streaks/achievements, settled in one transaction at session end. One student
  model across every device: a session started on the phone resumes on the robot (the "D8"
  cross-device pickup, live-proven 2026-07-05).
- **The surfaces**: six frozen HTTP session verbs (+ voice, + the live robot-session mirror)
  consumed by the app at pinned contract SHAs; tap-to-talk voice; the Reachy "Scholar"
  speaking the same sessions; MCP (the Claude-Desktop tool surface) as a dev/ops console
  only.
- **The knowledge layer**: retrieval over the family's own purchased and (in the pilot)
  uploaded study materials — selective, never always-on, and the reason a quote can be
  verified rather than trusted. Today: one English corpus; subject-scoping is the plan's
  Lane 2.

## The laws (binding on every lane; each names its enforcement)

1. **Socratic, never answer-dispensing.** The tutor guides to answers; "just tell me the
   answer" is refused, in every subject, on every surface. *(Enforced: the tutor prompts +
   Coach rubric; any new subject ships with both.)*
2. **The student's data stays under family control.** Household infrastructure is the
   default posture; a cloud deployment is a **governed posture change, not a drift** — it
   requires its own ADR covering UK-minors data governance (residency region, encryption,
   consent record, erasure path) before any student data moves. *(Enforced: ADR-ARCH-015 →
   ADR-ARCH-029 D4; the plan's Lane 3 gate.)*
3. **Never an unverified quote.** Anything presented as quotation is verified against the
   corpus before the student sees or hears it; no corpus ⇒ analysis mode, not confident
   fabrication. *(Enforced: the quote verifier + chunk-boundary gate, ADR-ARCH-027.)*
4. **AQA assessment material is excluded absolutely** — past papers, mark schemes, examiner
   reports, specimen papers: never trained on, never ingested, never retrieved (AQA's policy
   prohibits it; the guard is also pedagogical: mark schemes short-circuit Socratic
   behaviour). Specification facts (paper structure, AO names) are fine. *(Enforced: ingest +
   retrieval refusal patterns in code. Known casualty, stated honestly: subjects whose only
   corpus would be specimen papers — French 8652 / Spanish 8692 today — have no compliant
   corpus path until other materials are acquired.)*
5. **User-supplied copyrighted material enters only under a recorded posture.** The standing
   stance is "pipeline open, data private". Pilot uploads (scanned study guides/books) are
   allowed only per-account, never shared across accounts, never redistributed — and only
   after the copyright posture doc for uploads exists (the plan's Lane 4). *(Enforced:
   tenancy design + the Lane 4 ADR as a build precondition.)*
6. **Frozen contracts, additive evolution.** The app consumes the session contract at pinned
   SHAs; the six verbs and their status codes are frozen; new capability lands as additive
   verbs/addenda; shape changes to an original verb force a revision and re-pin. *(Enforced:
   `docs/design/contracts/API-session-http-binding.md` §7 discipline + the seam/contract
   test suites.)*
7. **Kindness by design.** Gamification celebrates a solo learner's growth: no leaderboards,
   no punishment mechanics, nothing that can make a session end sad. *(Enforced: the design
   guardrails in `docs/gamification/design.md` + the Study Room's kindness rules.)*
8. **Receipts, not claims.** A capability claim carries a live receipt (the 2026-07-05
   acceptance walk, the on-device auth gate, the honest-iOS "compiles + hermetic-suite
   green, live walk pending" convention — *hermetic* = the no-network, no-live-services
   test run) or it isn't claimed. *(Enforced: pre-registered gates + RESULTS docs; the plan
   reports against the measurables below.)*

## The measurables (frozen definitions; baseline 2026-08-01)

**S0 — Real students, really studying.** Real tutoring sessions per week by real students on
the live system. Baseline: **~0–1 sessions/week** (one student — Lilymay; one receipted
gamified session, 2026-07-26). Direction: up and steady for Lilymay, then +pilot cohort.
*This is the headline number — a lane that ships machinery but no sessions has not moved the
mission.*

**S1 — Subjects at parity.** A subject counts when it has ALL of: a subject prompt + Coach
rubric, a curriculum seed, a live subject-scoped corpus, a scored blind eval green, and a
real session receipt. Baseline: **1 provisional** — English is grandfathered on prompt +
rubric + curriculum + session receipts, but does not yet meet its own bar (its corpus is off
in prod; the only scored blind eval, 2026-05-18, favoured the base model). The Lane 1 eval
rerun and Lane 2 switch-on make English the first full pass. Direction: up, one subject at a
time.

**S2 — Grounded answers.** Retrieval live in production with quote verification active
(today: `rag_disabled reason=chromadb_missing` — code-complete and OFF), and fabrication
**< 5%** on the golden-quote eval, per subject with a corpus. Baseline: **retrieval dead in
prod; fabrication unmeasured**. Direction: on, then subject-scoped, then measured under the
frozen bar.

**S3 — Pilot readiness.** The ladder: copyright-posture doc ratified → residency/governance
ADR ratified → cloud spike receipted → deployed stack green → upload flow live → **first
external student session**. Baseline: rung 0. Direction: up in order; no rung skipped —
in particular, the copyright rung ratifies before the residency rung does.

**S4 — Estate honesty.** The hermetic suite green (one named pre-existing failure allowed
until fixed), the live contract suite green against the deployed host, and the docs
describing the system truthfully (the plan's named stale surfaces burned down to zero, kept
there). Baseline: suites green; a named stale-docs list.

## What this mission forbids

No leaderboards or inter-student comparison, ever. No AQA assessment material in any
pipeline, ever. No cloud movement of student data without the governance ADR. No silent
contract edits (additive or re-pin, nothing else). No third-party analytics or data
monetisation — the product's economics are hardware + electricity. No claims without
receipts, including in this document. No new orphan planning docs — decisions land in THE
PLAN or they didn't happen. **Plain language everywhere** — any codename or shorthand gets
cashed out on first use in every document this mission governs (the factory phrase-book
rule, adopted here).

## Reporting

Every session that closes a lane updates the plan-of-record cell it moved and states its
effect on S0–S4 in one line each ("moved nothing" is a valid, required answer). **Two
consecutive "moved nothing" reports on the same lane = stop the lane and bring it to Rich.**
Factory lanes additionally file their §7/§8 notes in ai-transition per the standing
convention there.

---

*Drafted 2026-08-01 from a receipted eight-area review of this repo's docs, git history, and
code, then adversarially critiqued (three lenses) before commit; every load-bearing claim
above cites an in-repo receipt or is marked not-yet-real. **RATIFIED by Rich the same day.**
Amendments by dated note, never silent edits.*

---

**Dated note — 2026-08-01 (Rich, in-session, same day as ratification):**

1. **Dulcie joins "Who it serves"** as the second in-house student — Lilymay's sister,
   Year 8 from September 2026, with her own phone and her own Reachy Mini. Her content is
   KS3-level, so subject packs carry a level dimension when hers land. **Lilymay remains the
   primary use case**, and the outcome this product exists for, in Rich's words: that it
   helps her actually achieve better results and find the final school year more enjoyable.
2. **Law 4's named casualty softens:** the family owns printed study guides, bought from the
   school, across all Lilymay's subjects. Scanned via the proven docling path (the
   architect-fine-tune precedent), they give every subject — French and Spanish included — a
   law-4-compliant corpus. The specimen-paper gap now limits only assessment-style material,
   which law 4 excludes anyway.
3. **Study Room optionality (agreed with Lilymay today):** multi-subject + RAG come first so
   the tutor is usable for real; the Study Room is a subsequent, **optional** phase —
   AI-generated art won't suit everyone, and the room concept fits a particular cohort (a
   different engagement angle for other cohorts, e.g. boys, stays an open design question).
4. The Hugging Face weights upload was deliberate — the Kaggle Gemma 4 Good hackathon entry
   required it; the licensing.md fix (plan Lane 5) records the fact and reason rather than
   walking it back.
