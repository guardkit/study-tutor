# ADR-ARCH-031 — Copyright posture for the friends pilot: per-account private retrieval of user-owned scans, judged under UK law

## Status

**Accepted — RATIFIED by Rich, 2026-08-02 (in-session word: "ratify ADR-ARCH-031").**
The Lane 4 gate is passed; the owner has accepted the recorded risk posture (Option 2).
Lane 3's residency ADR is now unblocked to draft and ratify per the S3 ladder.

*(Was: Proposed — DRAFT for Rich's ratification, 2026-08-01.)*

Ratification ordering is load-bearing: per the mission's S3 ladder ("no rung skipped — the
copyright rung ratifies before the residency rung does"), this ADR must be **ratified before
Lane 3's residency/governance ADR** (the [ADR-ARCH-029](ADR-ARCH-029-phased-productionisation-local-first-cloud-native-target.md)
D4 surface) may ratify, and before any upload surface is built (mission law 5 makes this ADR
a build precondition).

**Date:** 2026-08-01 (Lane 4 of the plan of record)
**Supersedes-in-part / absorbs:**
[copyright-training-data-analysis.md](../../research/ideas/copyright-training-data-analysis.md)
(2026-04-12) **for pilot scope**. That analysis was UK-only, purchased-materials +
household-deployment only, and silent on uploads, cloud hosting, and multi-account tenancy —
the three things the friends pilot adds. It remains the record for the fine-tune's
training-data provenance; this ADR governs the pilot. A pointer note now sits at the top of
that doc.
**Related:** mission laws 4 & 5 and measurable S3
([study-tutor-mission-statement-2026-08-01.md](../../study-tutor-mission-statement-2026-08-01.md));
the plan's Lanes 3 & 4 ([study-tutor-plan-of-record.md](../../study-tutor-plan-of-record.md));
[ADR-ARCH-015](ADR-ARCH-015-uk-on-device-data-residency.md) (household residency — the
posture Lane 3's ADR will supersede);
[rag-grounding-design.md §1a](../../research/ideas/rag-grounding-design.md) (posture 2 —
"user-supplied text, cached per-student", deliberately deferred on 2026-04-21, now adopted);
[aws-production-hosting-research-2026-07-06.md](../../research/ideas/aws-production-hosting-research-2026-07-06.md)
§1 (the Hugging Face upload fact + licence conflict) and §6c;
[licensing.md](../../licensing.md) (corrected in the same pass as this ADR);
`src/study_tutor/knowledge/corpus.py` (`AQA_REFUSAL_PATTERN`) and
`src/study_tutor/knowledge/retrieval.py` (`AQA_FILENAME_PATTERN`) — the law-4 enforcement
this posture inherits.

## Context

The friends pilot (plan Lane 3) is the first move that takes user-supplied copyrighted
material beyond one household:

- **Uploads:** scans of **user-owned printed books and study guides** — concretely, the
  school-bought printed study guides the family owns across all Lilymay's subjects (Rich's
  2026-08-01 ruling, mission dated note 2), scanned via the proven docling path (standard +
  VLM modes, the architect-fine-tune precedent), and the equivalent materials each friend's
  family owns.
- **Tenancy:** multiple Keycloak accounts (Lilymay, Dulcie in prospect, Lilymay's close
  friends), each with **their own** uploaded corpus and **per-account private retrieval** —
  no cross-account sharing of corpora, ever.
- **Hosting:** AWS `eu-west-2` (London), per the costed 2026-07-06 research (EC2 g6.xlarge
  default) — so the copies sit on third-party infrastructure under the operator's control,
  not on the household spark.

Mission law 5 says user-supplied copyrighted material enters **only under a recorded
posture**, and names this ADR as that record. The prior record
(`copyright-training-data-analysis.md`, 2026-04-12) does not stretch to cover this: it
analysed purchased DRM-free PDFs feeding a household-only pipeline. Uploads, cloud, and
multi-account tenancy each change the question and need answering honestly.

One more piece of standing context this ADR must record rather than dodge: **the fine-tuned
Gemma 4 26B-A4B weights were uploaded to the Hugging Face Hub** — see D4.

## Decision

### D1 — Scope of this posture

This ADR covers the **knowledge layer of the pilot**: user-uploaded scans of user-owned
printed books/study guides, ingested into per-account retrieval corpora, hosted in AWS
`eu-west-2`, surfaced only inside that account's own tutoring turns. It does **not** reopen
the fine-tune's training-data provenance (that record stands in the 2026-04-12 analysis,
household scope), and it does not decide residency/encryption/consent mechanics (Lane 3's
residency ADR, which ratifies after this one).

### D2 — The legal ground, stated honestly: UK law governs, and no UK exception squarely covers this

A UK pilot, run by a UK operator, for UK families, is judged under the Copyright, Designs
and Patents Act 1988 (CDPA). The honest reading:

1. **There is no fair-use doctrine in UK law.** The UK has **fair dealing** — a closed list
   of permitted purposes (non-commercial research and private study, s29; quotation,
   criticism/review, news reporting, s30; illustration for instruction, s32; parody, s30A),
   each subject to a "fairness" assessment that copying a **whole work** strains. Fair
   dealing is materially narrower than US fair use and cannot simply be assumed to apply.
2. **The text-and-data-mining exception (CDPA s29A) is non-commercial research only.** It
   permits copies for computational analysis of lawfully-accessed works, but the pilot's
   tutoring use is broader than "computational analysis for the sole purpose of
   non-commercial research", and s29A does not authorise making the copies available to
   others. It is the nearest statutory neighbour, not a safe harbour. (The government's
   Copyright and AI report of 18 March 2026 adopted "wait and see"; no broader TDM
   exception has been enacted — per the 2026-04-12 analysis §3.6.)
3. **The UK private-copying exception was quashed in 2015** (s28B, introduced 2014, quashed
   in *R (BASCA) v Secretary of State*) and never re-enacted. So the intuitive claim "we
   bought the book, we can digitise it for ourselves" is **not** the law in the UK. A scan
   of a purchased printed book is a copy of the whole work — a restricted act — with no
   squarely-applicable statutory exception.
4. **The US rulings Rich cites do not govern.** The 2025 US district-court rulings in the
   Anthropic and Meta book-training cases (*Bartz v Anthropic*; *Kadrey v Meta*) found
   training on lawfully-acquired books — including destructively-scanned purchased print
   copies — to be fair use. They are genuinely relevant **context**: they show a court
   weighing lawful acquisition, transformative purpose, and absence of market substitution
   in favour of the user, which is exactly the shape of this pilot. But they are US
   district-court decisions under a doctrine UK law does not have. They inform the risk
   assessment; they decide nothing here.

**Conclusion drawn plainly:** the pilot's uploads are unlicensed copies under UK law. This
posture is **risk management, not risk elimination** — the same honest register as the
2026-04-12 analysis ("no case law", "unsettled"), now applied to a slightly wider scope.

### D3 — The posture: five legs, each enforced in the build

The pilot proceeds because the residual risk is small, proportionate, and honestly carried
by these five legs — every one of which is a **build requirement** on Lane 3, not a hope:

1. **User-owns-the-source.** Uploads are scans of printed books the uploading family
   **bought** (school-bought study guides and their own set texts). The pilot onboarding
   flow (Lane 3 step 2, consent-in-onboarding per Rich's 2026-08-01 direction) captures an
   attestation to this alongside the parental-consent record: *we own the physical copy of
   what we upload*. No purchase, no upload. This also kills market substitution: the scan
   displaces no sale — the sale already happened, and the pilot's shape *requires* it.
2. **Per-account privacy.** Each account retrieves **only** against its own uploads —
   per-account collections, user-keyed registry (Lane 3 step 4 tenancy design). In-copyright
   material is never pooled. (Public-domain primary texts — the Standard Ebooks corpus —
   may remain a shared collection; the per-account rule binds everything in copyright.)
   This is `rag-grounding-design.md` §1a posture 2, deferred in April, adopted now.
3. **No redistribution.** Corpora never leave the account: no export surface, no
   cross-account sharing, no public access. Excerpts surface **only** inside that student's
   own tutoring turns (and law 3's quote verifier is what surfaces them). Nothing is
   "made available to the public" in the s20 sense; the operator hosting many accounts'
   islands does not communicate account A's scans to account B.
4. **AQA assessment material stays excluded absolutely** (mission law 4 — untouchable).
   Past papers, mark schemes, examiner reports, specimen papers: never ingested, never
   retrieved, in any account's pipeline. The existing refusal gates —
   `AQA_REFUSAL_PATTERN` at ingest (`corpus.py`) and `AQA_FILENAME_PATTERN` at retrieval
   (`retrieval.py`), intentionally independent — are **inherited into every per-account
   upload pipeline** at both ingest AND retrieval. This is a separate and harder rule than
   copyright: AQA's policy prohibits AI use outright, so no ownership attestation can admit
   AQA assessment material.
5. **Non-commercial, small, and removable.** The pilot is free, for a named small cohort
   (Lilymay's close friends), with no monetisation of any kind (the mission forbids it).
   Account deletion deletes the account's corpus (this joins the erasure path in Lane 3's
   residency ADR), and any rights-holder objection is honoured by removal — the posture is
   rights-holder-respecting, not defiant.

Cloud hosting changes the *governance* question (Lane 3's ADR), not the copyright one: a
private per-account copy in encrypted storage in `eu-west-2` is the same restricted-act
analysis as a copy on the spark, with the same five legs carrying it. Quota and format
guards on the upload surface (Lane 3 step 4) keep uploads shaped like study materials, not
a general file locker.

### D4 — The standing fact set, recorded honestly (not walked back)

1. **The fine-tuned Gemma 4 26B-A4B weights WERE uploaded to the Hugging Face Hub —
   deliberately.** The Kaggle "Gemma 4 Good" hackathon entry required it; the upload was
   executed per the agentic-dataset-factory HF-upload runbook and linked from the
   submission writeup (§11), and verified on the Hub in the 2026-07-06 AWS research (§1:
   `RichWoollcott/gcse-tutor-gemma4-26b-moe` + `-GGUF`; note the repo-id discrepancy with
   the eval runbook's `studytutor-gcse-26b-moe` — verify on the Hub before pinning).
   Rich's context recorded 2026-08-01 (mission dated note 4): the fix is to record the
   fact and the reason, not to walk it back. `licensing.md` §3/§4 are corrected in the
   same pass as this ADR. The 2026-04-12 analysis rated public weight distribution
   "Medium" risk (§7.2) with the mitigation that the weights are numerical behaviour, many
   transformative steps from any source text — that assessment stands; the decision to
   accept it was the hackathon entry.
2. **Open item carried, not resolved here:** the base-model licence identity conflict
   (writeup says Apache 2.0; `licensing.md` says Gemma Terms of Use) flagged by the AWS
   research §1/§6c must be resolved before any further weight hosting/distribution
   decision. That is a Lane 3 precondition, logged here so it is not lost.
3. **Model identity:** the fine-tune is Gemma 4 **26B-A4B** (MoE, ~27B total / ~4B active,
   base `unsloth/gemma-4-26b-a4b-it`). "31B Dense" in older docs is stale (AWS research
   §1); `licensing.md` is corrected in the same pass.

### D5 — Supersession mechanics

`copyright-training-data-analysis.md` gains a pointer note naming this ADR as governing for
pilot scope (the research doc is kept, not deleted — it remains the training-data
provenance record and the fuller legal survey). The four standing contradictions named by
the plan (licensing.md weights claim + model identity; the technical-writeup's false
RAG-store claim; the multi-subject ADR's RAG-source table; the sources README §3.2
deny-list ghost) are burned down in the same commit as this draft.

## Decision drivers

- **Mission line:** "grounded in the family's own study materials, piloted with her close
  friends" — the pilot without uploads is not the mission's pilot.
- **Law 5's precondition:** uploads are forbidden until this recorded posture exists;
  Lane 3's build is gated on it.
- **Honesty over comfort:** the repo's register (mission law 8) demands the UK legal
  position be stated as it is — unlicensed copies, managed risk — rather than borrowing a
  US doctrine that does not apply here.
- **Proportionality:** a free, named-cohort, non-commercial family pilot of scans of books
  those families bought, with no redistribution surface, sits at the lowest end of any
  realistic enforcement interest — and the 2015 quashing itself turned on *uncompensated
  harm to rights-holders*, which leg 1 and leg 3 are designed to keep at nil.
- **Precedent in-house:** the 2026-04-12 analysis already accepted the same shape of
  managed risk for the household (purchased guides → private ChromaDB copy), and 15 months
  of household operation have produced zero rights-holder friction.

## Options considered

### Option 1 — No-uploads pilot (public-domain corpora only)

Friends get accounts but retrieval runs only on Standard Ebooks public-domain texts.
**Rejected.** Legally the cleanest, but it guts the pilot: the family's school-bought study
guides are the ruled corpus path for every subject (mission dated note 2), most subjects
have no meaningful public-domain corpus, and the mission's own line — "grounded in their
own books" — is the thing being piloted. It also proves nothing Lane 3 needs proven about
the upload surface.

### Option 2 — Uploads under this recorded posture (CHOSEN)

Per-account private retrieval of user-owned scans, five enforced legs, honest UK-law
framing, rights-holder-respecting removal path. The residual risk is real, small, named,
and accepted by the owner at ratification.

### Option 3 — Wait for formal legal advice / publisher licences

Commission an IP opinion, or seek per-publisher licences (the "commercial path" noted in
`rag-grounding-design.md` §1a posture 3), before any upload.
**Rejected for the pilot** — the cost is disproportionate to a free family pilot; UK law is
explicitly in "wait and see" (no advice can conjure an exception that does not exist); and
it stalls S3 indefinitely. **Named as the trigger path**: if the product ever takes money
or scales beyond the close-friends cohort, this option stops being optional (see "What
would change this posture").

## Consequences

**Positive:**

- Lane 3's upload surface has its build precondition (law 5) satisfiable: ratify this, and
  the tenancy design + attestation step have their normative source.
- The S3 ladder's rung 1 is climbable, in order, with rung 2 (residency) explicitly queued
  behind it.
- The repo's copyright story becomes one document deep for the pilot, with the 2026-04-12
  analysis honestly repositioned rather than silently contradicted.
- The HF-upload fact stops being a contradiction and becomes a recorded decision with a
  reason.

**Negative / accepted:**

- The posture accepts unquantifiable-but-small legal risk on the operator (Rich), stated
  plainly rather than lawyered away. Ratification is the owner accepting it.
- Per-account isolation forgoes an obvious efficiency (one shared scan of a study guide
  many friends own) — deliberately: the sharing version is the redistribution this posture
  forbids. Each family scans its own copy.
- The attestation step adds friction to onboarding (a signed "we own this" alongside
  consent) — accepted as the cost of leg 1 being real rather than assumed.
- The build inherits five enforceable requirements (D3) that Lane 3 must receipt, including
  refusal-gate inheritance tests per account.

## What would change this posture

Any of these reopens this ADR (dated amendment or supersession — never silent edits):

1. **Money.** Any payment, subscription, or commercial offering — the non-commercial leg
   and the s29/s29A-adjacent framings collapse; Option 3 (advice/licences) becomes
   mandatory before the first paid account.
2. **Scale.** Growth beyond the named close-friends cohort (or any open signup) — the
   proportionality argument thins with every account.
3. **Sharing.** Any cross-account sharing of in-copyright corpora, however convenient —
   that is redistribution; this posture is void for that design.
4. **A rights-holder objects.** Honour it: remove the material, record the event, revisit
   the posture.
5. **The law moves.** A UK TDM/private-copying/AI-training legislative change or a UK
   ruling on RAG/AI ingestion of purchased works — revisit against the new ground
   (the "wait and see" report promised movement eventually).
6. **AQA material is found anywhere in any pipeline** — stop-the-line under law 4; that is
   not a copyright event but a mission-law breach, and it invalidates the claim this
   posture makes in D3 leg 4 until the gate is proven again.
7. **Further weight distribution** beyond the existing recorded HF upload — a separate
   decision, blocked on the D4.2 licence-identity resolution.

## References

- Mission: [study-tutor-mission-statement-2026-08-01.md](../../study-tutor-mission-statement-2026-08-01.md)
  — laws 4, 5, 8; measurable S3; dated notes 2 & 4.
- Plan: [study-tutor-plan-of-record.md](../../study-tutor-plan-of-record.md) — Lane 4 (this
  ADR), Lane 3 (the build this gates), Known contradictions list.
- [copyright-training-data-analysis.md](../../research/ideas/copyright-training-data-analysis.md)
  (2026-04-12) — absorbed for pilot scope; still the training-data provenance record and
  the fuller AQA/Mr Bruff analysis.
- [rag-grounding-design.md](../../research/ideas/rag-grounding-design.md) §1a — posture 2
  (per-student user-supplied text), deferred 2026-04-21, adopted here.
- [aws-production-hosting-research-2026-07-06.md](../../research/ideas/aws-production-hosting-research-2026-07-06.md)
  — §1 (verified artifact facts incl. the HF upload and licence conflict), §5 (eu-west-2
  cost basis), §6a/§6c (residency + licence decision points).
- [ADR-ARCH-029](ADR-ARCH-029-phased-productionisation-local-first-cloud-native-target.md)
  D4 — the Phase 3 data-governance surface (Lane 3's residency ADR, which ratifies after
  this one). [ADR-ARCH-015](ADR-ARCH-015-uk-on-device-data-residency.md) — the household
  posture it will supersede.
- Enforcement code: `src/study_tutor/knowledge/corpus.py` (`AQA_REFUSAL_PATTERN`, ingest);
  `src/study_tutor/knowledge/retrieval.py` (`AQA_FILENAME_PATTERN`, retrieval);
  deny-list removal `1f728bf` (2026-05-09, TASK-RAG-CC1) +
  `domains/gcse-english/sources/CONTRIBUTING-CORPUS.md` §3 (personal-use posture).
- Corrected in the same pass: [licensing.md](../../licensing.md),
  [docs/submission/technical-writeup.md](../../submission/technical-writeup.md),
  [ADR-TUTOR-MULTI-SUBJECT-single-finetune.md](ADR-TUTOR-MULTI-SUBJECT-single-finetune.md),
  [domains/gcse-english/sources/README.md](../../../domains/gcse-english/sources/README.md) §3.2.

---

*This ADR is not legal advice; it is the project's recorded, owner-ratified risk posture
(mission law 5). Drafted 2026-08-01 for Lane 4; every load-bearing claim names its in-repo
receipt.*
