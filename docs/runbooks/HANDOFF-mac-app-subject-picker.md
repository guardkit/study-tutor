# HANDOFF — the app subject picker (Mac checkout; the last Lane 1 step 2 seam)

**Date:** 2026-08-02 (written on the spark, where this leg is blocked: no Flutter toolchain).
**Method:** orchestrated-build-playbook
(`ai-transition/docs/ways-of-working/playbook/orchestrated-build-playbook.md`) — Rich's
spec word for Lane 1 step 2 was given in-session 2026-08-02 ("please proceed with Lane 1's
remaining seams"); this handoff is the design pass for the one leg that needs the Mac.
Coordinator review before push; nothing here changes the frozen contract.

## Ground yourself first (non-negotiable)

1. Root [`CLAUDE.md`](../../CLAUDE.md) → the two sources of truth:
   the mission ([`study-tutor-mission-statement-2026-08-01.md`](../study-tutor-mission-statement-2026-08-01.md))
   and THE PLAN ([`study-tutor-plan-of-record.md`](../study-tutor-plan-of-record.md)).
   Read the plan's **Lane 1 step 2** cell — it names this handoff and carries the
   session-end obligation: **you finish by updating that cell**, not by writing a new doc.
2. The binding contracts this leg touches (read, do NOT edit):
   [`SUBJECT_DEFAULT.md`](../design/contracts/SUBJECT_DEFAULT.md) — especially **§4**,
   which pre-designed exactly this change ("when a picker lands, `defaultSubject` becomes
   the *fallback* rather than a fixed value; no rework of the seam is required");
   [`API-session-http-binding.md`](../design/contracts/API-session-http-binding.md) §2.2
   (the 2026-08-02 dated annotation: `subject` now filters the student-model read).
3. `app/README.md` — the app's own gates and conventions (per-wave green gate =
   `flutter analyze` + `flutter test` + `flutter build apk --debug`).

## What already happened (2026-08-01/02, the spark weekend — receipts in the plan)

The backend is **fully ready** for a subject-sending app. Everything below is merged,
deployed on the spark, and live-proven — the app leg is the only remaining seam:

- **RAG is live and subject-scoped** (ADR-ARCH-031 ratified; ADR-ARCH-032 built +
  deployed): per-subject collections (`gcse-<subject>-v1`), retrieval keyed by
  `session.subject`, honest `no_corpus_for_subject` skip — never a cross-subject
  fallback.
- **All front doors share one `(student, subject)` resume key**: the server normalises
  omitted/empty subjects to `english`; the MCP `subject=student_id` quirk is dead.
- **The mastery schema is subject-dimensional** (migration `d5a9c2e7f814`, run against
  the live NAS store): `topic_confidence` keys on `(student, subject, topic)`;
  settlement banks confidence under the session's subject.
- **`GET /api/student-model?subject=` genuinely filters now** (live-proven:
  `english` → real rows; `french` → `{}`; whole-student XP identical across subjects).
  The app's `HttpStudentModelApi.fetch({required subject})` is already parameterised —
  nothing to change in the adapter.

Consequence for this leg: **whatever subject the app sends, the backend does the right
thing end-to-end** — session keying, retrieval scoping, mastery banking, progress reads.

## The task

Make the app's subject a piece of **selected state with `defaultSubject` as the
fallback**, sent on `startSession` and threaded into the progress read. Concretely:

### Current wiring (verified 2026-08-02 on the spark checkout)

- `app/lib/ui/home_screen.dart:29` — `const defaultSubject = 'english';`
  **Keep this constant's name and value verbatim** — the cross-repo seam test
  (`tests/seam/test_subject_default.py`) greps the file for
  `defaultSubject = 'english'` and fails the python suite if it disappears.
- `home_screen.dart:171` and `:178` — both `startSession` call sites pass
  `subject: defaultSubject` (the fixed value §4 designed away).
- `app/lib/ui/app.dart:53` — `ProgressStore(api: _studentModelApi, subject:
  defaultSubject)` — the progress read is pinned at the composition root.

### Design (right-sized — agree deltas with Rich before gold-plating)

1. **A `selectedSubject` state** (Home-owned or a tiny store — match the app's existing
   state idiom) initialised to `defaultSubject`. Both `startSession` call sites and the
   progress read consume `selectedSubject`; `defaultSubject` remains only the fallback
   and the seam-test anchor.
2. **The available-subjects list is a client-side constant for now** — today
   `['english']` only. Do NOT invent a server endpoint for it (that would be a contract
   addition — a later, additive decision once content packs exist; note it as an open
   question in the plan cell if you feel the pull).
3. **Render the picker only when the list has >1 entry.** With English alone the UI is
   unchanged (nothing to pick is not a picker), but the seam is genuinely closed: when
   French lands, adding one string to the list surfaces the picker with zero further
   plumbing. If Rich prefers a visible single-option control, that's his call — ask,
   don't assume.
4. **Progress follows the selection**: the `ProgressStore` subject should track
   `selectedSubject` (the backend filter is live, so a French selection will honestly
   show an empty mastery map until French content exists — that's correct, not a bug).
5. **Persistence of the selection** (nice-to-have, not required): the app has
   `secure_session_store.dart` / existing local-storage idioms; session-scoped state is
   acceptable for v1 of the seam.

### Fences (verbatim, per the playbook's PREFLIGHT discipline)

- **Frozen contract**: `subject` already rides `startSession` (binding §2.1) and
  `student-model` (§2.2) — this leg sends different *values*, it changes **no shapes,
  no routes, no status codes**. If you find yourself editing
  `docs/design/contracts/*`, stop — that's a smell.
- **Do not rename/remove `defaultSubject`** (seam test, above).
- **Broker isolation**: never connect to any NATS broker (standing rule; irrelevant to
  this leg but standing).
- **Hermetic-first**: the fake backend flavour must exercise the picker state; live
  flavours stay opt-in.

### Gates (the app's own green gate + the cross-repo seam)

```bash
cd app
flutter analyze              # clean
flutter test                 # hermetic suite (386+ tests) green, incl. your new ones
flutter build apk --debug    # G-F0 build gate
```

Add hermetic tests for: fallback behaviour (no selection → `defaultSubject` sent),
selection threading (picked subject reaches `startSession` AND the progress read), and
picker visibility (hidden at 1 subject, shown at >1 — drive with a test-injected list).
If the Mac has the python env: `uv run pytest tests/seam/test_subject_default.py -q`
confirms the seam pin still holds; otherwise the spark's next suite run will.

## Optional Mac-only extras (named in the plan — only with Rich's word, don't drift)

- **The iOS attended walk** (a named deferral): `cd app && pod install && flutter run`
  on a booted simulator — promotes iOS from "compiles + hermetic green" to a device
  claim. Separate act; separate plan update.
- **APK rebuild + install to Lilymay's phone** — the picker (even hidden) plus the
  weekend's backend work only reach her device via an attended build/install.
- **The live contract suite re-run** (Lane 5's still-open item; last green 2026-07-05,
  pre-`turnsSince`): `flutter test test_live --dart-define=API_BASE_URL=http://<spark
  tailnet name>:8100 --concurrency=1`. **Caution:** it drives the REAL deployment and
  writes real store rows — operator-attended, Rich's call, and the receipt goes in the
  plan's Suites row.

## Session-end ritual (the plan's standing rule)

1. Update THE PLAN's Lane 1 step 2 cell: mark the picker leg `✅ DONE <date>` with
   receipts (commit SHA, suite counts, apk gate), or record honestly what remains.
2. If the live suite or iOS walk ran, update their rows/deferrals likewise.
3. Commit per repo conventions (the co-author line), push, and note the push in the
   cell. The spark's sessions will pick it up from origin.

## State of the world as this handoff was written

- `main` at `9b00ddb` on origin (everything above is pushed; branches
  `lane2/subject-scoped-rag` + `lane1/subject-seams` published for archaeology).
- The spark serves `:8100` (table auth, voice ON) + `:8101` (Keycloak) on image
  `study-tutor:latest` (1.4GB, RAG live); NAS Postgres at migration head
  `d5a9c2e7f814`; a pre-migration safety dump sits at
  `/opt/study-tutor/backups/pre-subject-migration-20260802.sql` on the spark.
- Suites: python hermetic 1671/0 (2026-08-02); dart 386 (pre-picker).
- Still open elsewhere (NOT this handoff's scope): Lane 1 step 3 content packs (waiting
  on Rich's scans), Lane 1 step 1 evals (`fleet-evals` repo), Lane 6 step 1 robot
  re-point (fleet-gateway host runbook), Lane 3's residency ADR (unblocked by
  ADR-ARCH-031's ratification).
