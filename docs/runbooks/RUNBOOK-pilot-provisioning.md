# RUNBOOK — provision and deprovision a pilot student account

**Lane:** plan-of-record Lane 3, step 5 (`docs/study-tutor-plan-of-record.md`) ·
**Written:** 2026-08-14 · **Status: WRITTEN, NOT YET RUN — awaiting one attended walk.**
**Commissioned by:** [ADR-ARCH-034](../architecture/decisions/ADR-ARCH-034-pilot-multi-user-accounts.md)
D3 ("Lane 3 step 5 WRITES the one friend-provisioning runbook"), which also corrected the
plan's former "runbook exists" claim — this file is the thing that claim described and that
did not exist. The deprovisioning half is mandated by
[ADR-ARCH-033](../architecture/decisions/ADR-ARCH-033-pilot-residency-governance-eu-west-2.md)
D6.2 ("the Lane 3 step 5 provisioning runbook MUST carry a deprovisioning half").

**Where it runs:** attended, by Rich, from a host on the tailnet with admin access to the
identity server and a psql/CLI path to the tutor database. Not from a build session: every
command below touches a live host, live identity, or a child's data.

**The one-line summary:** one account = one consent record + one `student` row + one
identity-server user carrying a `student_id` attribute and the `student` role — created in
an order that leaves the account **unusable, not half-usable**, if any single step fails.

---

## 0. STOP — this runbook cannot be completed today, and why

> **BLOCKED for any external account until the consent record has somewhere to land.**
> ADR-033 D5 is unambiguous: *"every pilot account carries a parental-consent record before
> its first session, regardless of the student's age … No consent record, no session."*
> ADR-034 D6 makes that record step 1 of onboarding. **The table does not exist.** A repo-wide
> search for `consent` across `src/`, `alembic/` and `app/lib` returns **zero** occurrences
> (verified 2026-08-14, this worktree); the migration head is `346cd366b66e` and no revision
> creates a consent table. ADR-033 explicitly **rejected** the workaround — *"A paper consent
> form outside the product. Rejected by Rich's 2026-08-01 direction — consent is a signed step
> **in** onboarding"* — so there is no bridge to improvise here.
>
> **Consequence, stated plainly:** Part A below is complete and ready, but **step A1 has no
> mechanism**, so no external account may be provisioned until the consent table + gate land
> (ADR-034 D6, Lane 3). Everything else in this runbook is executable the day that ships.
> Deprovisioning (Part C) is **not** blocked — the erasure cascade exists today and would
> run against any account that exists.

Two further preconditions, both recorded rather than assumed:

- **The pilot does not run on the household box.** ADR-034 D4 rules the cohort off the spark
  on a measured memory law (~98 GB of 128 GB committed by one student's stack). This runbook
  is written host-agnostically: `$KC_BASE` and `$API_BASE` are set to whichever deployment the
  account belongs to. Provisioning a friend against the household `:8101` is a *rehearsal*,
  not the pilot.
- **Table mode is not an option for anybody but the robot.** ADR-034 D8: *"The boundary is
  absolute: table mode is Lilymay's-household-only … no friend ever receives a static token."*
  Every account this runbook creates is an identity-server account.

---

## 1. The failure mode this runbook exists to prevent

ADR-034 D3: *"A partial subset of these steps produces a broken account by construction …
the runbook exists precisely so partial states cannot."* Named concretely, with receipts:

| # | Half-state | What the child sees | Receipt |
|---|---|---|---|
| H1 | Identity user exists, `student_id` attribute missing | Sign-in **succeeds**, then every API call 401s | `src/study_tutor/http/auth_keycloak.py:171–179` raises `Unauthenticated` when the claim is absent; the mapper that carries it is `deploy/keycloak/provision-live-suite.sh:87–99`; ADR-034 D2 calls this out as the reason atomicity is non-optional |
| H2 | Identity user complete, no `student` row | Sign-in **succeeds**, then every API call 401s | The unseeded-student guard, `src/study_tutor/http/auth.py:286–297` — mode-agnostic, it sits in `resolve_student_id` after the resolver, so it fires identically in table and identity-server modes |
| H3 | `student` row exists, no identity user | Nothing — the row is unreachable | `registrationAllowed: false` and no `users` key in `deploy/keycloak/realm/study-tutor-realm.json`: accounts exist only when the operator creates them (ADR-028 D1) |
| H4 | Account fully working, no consent record | A session that should never have started | ADR-033 D5; **no mechanical backstop exists today** (§0) — procedure is the only enforcement until the gate lands |

H1 and H2 are the dangerous pair: they are indistinguishable to a 14-year-old ("I signed in
and it's broken"), and both are *silent* to the operator who created the account and walked
away. H3 is inert. H4 is the one the machine will not catch.

**The ordering rule that follows:** do the step with no mechanical backstop first, make the
account's identity **disabled at birth**, and make *enabling it* the last, single, reversible
act — taken only after every other piece has been read back.

---

## 2. Preconditions (check all five before starting)

1. **Consent captured** — the signed onboarding step is done and its record exists (§0: today
   this is the blocker). You will need the record's identifier for A1.
2. **The student's details agreed with the family** — `student_id` slug, display name, year
   group (7–13, enforced by a schema CHECK: `schema_reference.sql:21`), target grade.
   The slug is what crosses the auth boundary; ADR-033 D7 requires it to be an **opaque ID,
   not a name**. Pick accordingly.
3. **Admin credentials to hand** — `KC_BOOTSTRAP_ADMIN_USERNAME` / `KC_BOOTSTRAP_ADMIN_PASSWORD`
   from the gitignored `deploy/keycloak/.env.deploy`, or the sops-encrypted equivalent at
   `${SECRETS_ROOT}/study-tutor/keycloak-env-deploy.enc.env` (the dual-mode load in
   `deploy/keycloak/provision-live-suite.sh:34–53`).
4. **A database path** — `STUDY_TUTOR_PG_DSN` for the deployment the account belongs to.
5. **A rollback window** — do not provision at bedtime. The verification block (Part B) is
   part of the procedure, not an optional follow-up.

**Naming and secrets discipline:** the student's password is typed at a prompt and never
written to a file, a command line, or this document. No token value belongs in the repo —
`tests/test_no_live_credentials.py` fences the whole repo, docs included, after the
2026-08-14 rotation.

---

## 3. Environment

```bash
# ATTENDED-ONLY — set for the deployment this account belongs to.
export KC_BASE="https://<identity-server-host>:8443"     # household default: the NAS, per the standup runbook
export API_BASE="https://<tutor-api-host>:<port>"        # the identity-server-mode deployment
export REALM="study-tutor"
export SID="<student-id-slug>"                           # e.g. a non-identifying slug
export UNAME="<login-username>"
```

The draft helper script `deploy/keycloak/provision-pilot-student.sh` performs A2–A6 with a
confirm prompt in front of every live call. It is **DRAFT and has never been executed** — the
attended walk is its first run, and the walk should follow the manual steps below with the
script open alongside, not the other way round. What has been checked: `bash -n` and an
`ast.parse` of every embedded Python block, both clean; `shellcheck` is **not installed** on
the authoring host, so lint it on the walk. The file is deliberately left **non-executable** —
`chmod +x` is a decision someone takes, not a default it arrives with.

---

## Part A — Provisioning (in order; do not reorder)

Each step states **what exists after it**, **whether the account is usable** (it is not, until
A6), and **its rollback**.

### A1 — Consent record + ownership attestation (ONE step, TWO records)

ADR-034 D6: *"a single signed step, before a friend's first session, that captures (a) the
parental-consent record and (b) the ADR-031 leg-1 ownership attestation."*

**Where the record lands:** a consent table in the **tutor database**, keyed by `student_id`,
carrying — per ADR-033 D5 — the consenting adult's name and relationship, the timestamp, the
privacy-notice version consented to, the ownership-attestation flag, and a nullable withdrawal
timestamp. Same database as the `student` row, which is what lets Part C stay one statement.

**Today:** the table does not exist (§0). Do not proceed past this line for an external
account. Record the consent reference you will use once it does.

- **After this step:** a consent record, no account, nothing reachable.
- **Rollback:** delete the consent record. Nothing else has been created.
- **Open design item this step depends on** — see Part D, Q1: whether the consent row
  cascades with the student (one-statement erasure) or deliberately outlives it (proof that
  consent was held). Both cannot be true; the answer changes Part C.

### A2 — Seed the `student` row

```bash
# ATTENDED-ONLY
STUDY_TUTOR_PG_DSN="$STUDY_TUTOR_PG_DSN" \
  uv run study-tutor seed-students --student-ids "$SID"
```

Idempotent by construction — `INSERT … ON CONFLICT DO NOTHING`
(`src/study_tutor/knowledge/store/postgres.py:645–700`), so a re-run is safe.

**Known limitation, do not skip:** the CLI hard-codes the profile fields —
`name = student_id.title()`, `year_group = 10`, `target_grade = "7"`
(`src/study_tutor/cli/main.py:1336–1341`). There is **no** flag for them, and there is **no**
`list-students` command in the CLI despite the Keycloak standup runbook citing one
(`RUNBOOK-study-tutor-keycloak-standup.md:245–247` — the CLI's commands are `serve-nats`,
`serve-http`, `seed-students`, `settle-sessions` and the role-manifest command; verified
2026-08-14). So for any student who is not Year 10 targeting grade 7, correct the row
immediately after seeding:

```bash
# ATTENDED-ONLY — psql against the tutor database. year_group must be 7–13 (schema CHECK).
UPDATE student
   SET name = '<display name>', year_group = <7-13>, target_grade = '<grade>'
 WHERE student_id = '<student-id-slug>';
```

- **After this step:** a `student` row and nothing else. **Unreachable** — half-state H3, which
  is inert: no identity exists that resolves to it, and self-registration is off.
- **Rollback:** `DELETE FROM student WHERE student_id = '<student-id-slug>';` — safe here
  because the row is brand new and carries no learner data yet. (This is the same statement
  Part C uses; it cascades, which at this point deletes nothing extra.)
- **Verify before moving on:** the row exists with the intended year group and target grade.

### A3 — Create the identity user **disabled**, with the attribute and the password in ONE call

This is the step where atomicity is bought. The `student_id` attribute and the credential go
in the **same create request** as the user, exactly as `provision-live-suite.sh:132–141` does
for the test account — so half-state H1 cannot exist as a *persistent* state: either the POST
succeeds and the attribute is there, or it fails and no user was created.

`enabled: false` is the deliberate difference from that template. The account is born switched
off; A6 is the only thing that turns it on.

```bash
# ATTENDED-ONLY — admin token, then create. The password is typed at a prompt, never echoed.
# The draft script deploy/keycloak/provision-pilot-student.sh does exactly this, with a
# confirm prompt in front of each call.
```

The user representation must carry:

| Field | Value | Why |
|---|---|---|
| `username` | `$UNAME` | login identity |
| `enabled` | **`false`** | the account cannot be signed into until A6 |
| `attributes.student_id` | `["$SID"]` | the claim the API derives identity from — its absence is H1 |
| `credentials` | one password entry, `temporary: false` | set now so A6 is a single flip, not a flip plus a credential step |

- **After this step:** a disabled identity user carrying the attribute, plus the `student` row.
  **Not usable** — a disabled user cannot obtain a token at all.
- **Rollback:** delete the user (`DELETE /admin/realms/$REALM/users/{id}`). The `student` row
  may stay for a retry, or be deleted per A2's rollback.
- **If the POST fails:** nothing was created. Re-run it; do not "fix it up" by adding the
  attribute afterwards — that is precisely the sequence this ordering exists to forbid.

### A4 — Assign the `student` realm role

The role must be a separate call (Keycloak's role-mapping endpoint), which is why the user is
still disabled. Roles `student` and `parent` exist in realm-as-code
(`deploy/keycloak/realm/study-tutor-realm.json`); `parent` is reserved and **not** assigned
here (ADR-033 D5 notes it as the future carrier if consent is ever account-exercised).

- **After this step:** disabled user + attribute + role + `student` row. Still **not usable**.
- **Rollback:** remove the role mapping, or delete the user (A3's rollback).

### A5 — Read back all four pieces BEFORE enabling

Do not skip this and do not do it from memory. Read back, in this order:

1. The `student` row exists with the right year group / target grade.
2. The identity user exists, is **still disabled**, and its `student_id` attribute equals
   `$SID` **exactly** (whitespace and case included — the claim is compared as a string).
3. The realm role `student` is mapped to that user.
4. The consent record from A1 exists and names this `student_id`.

If any read-back is wrong, fix it **before** A6. Everything is still switched off, so there is
no time pressure and no exposed account.

- **Rollback:** unchanged from A4 — nothing has been enabled.

### A6 — Enable the account (the single go-live act)

Set `enabled: true` on the user. This is the only step that makes the account reachable, it is
one field, and it is reversible in one field.

- **After this step:** a working account.
- **Rollback:** set `enabled: false`. Sign-in stops immediately for new tokens; see Part C,
  step C1 for the already-issued-token caveat.
- **Then:** run Part B. An account is not provisioned until it has been proven.

### The invariant, stated once

> Before A6, **every** failure leaves an account that cannot be signed into at all. After A6,
> everything has already been read back. There is no ordering in which a child ends up with an
> account that signs in and then fails — which is exactly ADR-034 D3's named failure mode.

---

## Part B — Verification (attended-only; the operator runs these, not this document)

> **ATTENDED-ONLY.** Every command in this part touches a live host and mints a real token for
> a real account. Nothing in this section may be run by a build session, and no output of it
> may be pasted back into the repo — token values are credentials
> (`tests/test_no_live_credentials.py`, and the 2026-08-14 rotation that occasioned it).

Prove the account in the order the failure modes fall out:

**B1 — the account can obtain a token.** Sign in as the new user through the direct-grant
client (`live-suite`, provisioned by `provision-live-suite.sh`) or through the app's sign-in
screen on a real device. *Fails if:* A6 was not done, or the password was set temporary.

**B2 — the token carries the `student_id` claim.** Decode the access token locally (offline —
do not post it anywhere) and confirm `student_id == $SID`. *This is the H1 check.* If the
claim is absent, the mapper or the user attribute is wrong; go back to A3/A5.

**B3 — the API answers.** `GET $API_BASE/api/student-model?subject=english` with that token.
Expect **200** and the student's (empty, new) model. *This is the H2 check:* a 401 here with a
valid claim means the unseeded guard fired — the `student` row is missing or the slug differs
from the claim by a character.

**B4 — the frozen six behave.** Start a session, take one turn, end it — the app-facing
contract's verbs, unchanged by any of this
(`docs/design/contracts/API-session-http-binding.md` §7; ADR-034 D6 keeps consent additive so
the six verbs stay untouched). *This is the receipt that the account is a real account and not
just an authenticated one.*

**B5 — isolation.** With the *new* account's token, confirm the student model contains only
this student's data. There is no cross-student aggregation anywhere in the store by
construction (ADR-034 D1, ~28 student-scoped call sites), and the 2026-08-04 live suite run
left Lilymay's rows byte-identical while running as a second account — but on the first real
friend account, look once with your own eyes.

**B6 — voice, if the deployment has it on.** ADR-034 D5 rules voice-on-identity-server-mode
**IN**, gated on one attended voice walk against the identity-server-mode deployment
(tap-to-talk round trip, authenticated as an identity-server user). That walk is its own gate
and its own receipt — if it has not happened yet, it is not this account's job to prove it;
note it and move on.

Record the run: date, who attended, which deployment, and the B1–B6 outcomes. A provisioning
without a receipt did not happen (mission: claims carry receipts).

---

## Part C — Deprovisioning / erasure

Triggered by: a verified erasure request, **or** consent withdrawal (ADR-033 D5: withdrawal
triggers the erasure path; ADR-034 "what would change this posture" item 7 says the same).
**Published SLA: complete erasure within 30 days** (ADR-033 D6). Erasure is an **attended
runbook, not an API verb** — ADR-034 D3 decided that explicitly, and the only deletion code in
the system today is a dev-flag reset tool that deliberately *spares* gamification state
(`src/study_tutor/knowledge/store/postgres.py:761–806`;
`src/study_tutor/http/app.py:591–618, :752–755`) and is **not** an erasure path.

### C0 — Start the clock, in writing

Record: the date and time of the request, who made it and how their authority was verified,
which account, and the 30-day deadline. This record is the SLA's evidence.

### C1 — Disable the identity user (first, and reversible)

Set `enabled: false`. New sign-ins stop immediately. **Caveat, honestly:** an access token
already issued remains valid until it expires — realm-as-code pins no `accessTokenLifespan`,
so the server default applies. Read the live value back on the walk (Part D, Q4) and record it,
because it is the width of the window between "disabled" and "cannot reach the API".

- **Rollback:** re-enable. This is the last reversible step; everything after it is not.

### C2 — Delete the identity user

`DELETE /admin/realms/$REALM/users/{id}`. Removes the login identity from the identity
server's own database (ADR-028 D1 — its users were never in git, so nothing in the repo needs
touching). ADR-033 D6.2 mandated exactly this step, noting it previously had **no runbook
step**; this is that step.

- **Rollback:** none. Re-provisioning is a new account (A1–A6), not a restore.

### C3 — Delete the student, in one statement

```sql
-- ATTENDED-ONLY — the tutor database. One statement; the cascade is the design.
DELETE FROM student WHERE student_id = '<student-id-slug>';
```

**What that one statement deletes**, with the schema as receipt
(`src/study_tutor/knowledge/store/schema_reference.sql`, head `346cd366b66e`):

| Table | How it goes | Line |
|---|---|---|
| `student` | the statement itself | :18 |
| `topic_confidence` | `REFERENCES student … ON DELETE CASCADE` | :29 |
| `misconception` | cascade | :40 |
| `session` | cascade | :51 |
| `session_turn` | cascades **via `session`** — the full verbatim transcript, turn by turn | :75 |
| `achievement` | cascade | :86 |
| `topic_confidence_history` | cascade | :99 |
| `quest` | cascade | :112 |

That is the complete Postgres footprint of a student. **XP, streaks, achievements and quests
go with it** — deliberately unlike the dev reset tool, which spares them. Erasure means
erasure.

### C4 — Per-account retrieval corpus

**Nothing to do today, and say why rather than tick it:** collections are keyed by **subject,
not student** (`src/study_tutor/knowledge/retrieval.py:461, :464–478` — the collection
providers are keyed by `subject`; ADR-032), and the corpus is baked into the container image
and wired at boot (`deploy/http/docker-compose.yml:73–78`), so no
per-account corpus exists to delete. When ADR-034 D7's student dimension lands (Lane 3 step 4),
this step becomes: delete every `(student, *)` collection and any stored upload artifacts.
**Shared public-domain collections are exempt and stay** — nobody's personal data, nobody's
infringement (ADR-031 leg 2's carve-out).

### C5 — Backups: erasure completes when the dumps roll

The nightly `pg_dump` covers **both** the tutor and identity databases with
`RETENTION_DAYS=14` (`deploy/postgres/backup.sh:22`, keycloak dump at `:69–80`). A deleted
student therefore persists in dumps for **at most 14 days** after C3 — inside the 30-day SLA,
and that arithmetic is the SLA's honest basis. **The Q5 residual is nil:** Synology Hyper
Backup was never installed (verified by Rich in the DSM console 2026-08-13; ADR-033 D6.4's
dated correction, and the plan's Lane 3 step 1 cell). Nothing else copies the backups.

*If this account lives in the cloud deployment:* ADR-033 D6.4 binds it — any managed backup
carries a documented retention of **at most 14 days**, or the SLA is recomputed and
republished. Check this before C0's deadline is quoted to anybody.

### C6 — Close the record

Note the completion date against C0's clock, and which of C1–C5 applied. If any step could not
be completed inside the SLA, that is a **stop-the-line** event, not a note (ADR-033 "what would
change this posture" item 6).

### What survives erasure, and why

Stated so it is never a surprise:

- **Backup dumps, for up to 14 days** (C5). Inherent to the design, documented, inside the SLA.
- **Shared public-domain retrieval collections** (C4) — not personal data.
- **Application log lines naming the `student_id`.** The auth path logs the resolved
  `student_id` on success (`src/study_tutor/http/auth.py:299–303`;
  `src/study_tutor/http/auth_keycloak.py:181–185`). That is an **opaque slug, not a name**
  (ADR-033 D7's minimisation posture, and the reason picking a non-identifying slug at A2
  matters), but the lines outlive the cascade. Log retention is not dated anywhere in this
  repo — Part D, Q3.
- **Identity-server login/admin event records**, *if* the live realm has them switched on.
  Realm-as-code sets `eventsEnabled: false` and `adminEventsEnabled: false`
  (`deploy/keycloak/realm/study-tutor-realm.json`), so by config there are none — but the live
  realm's current values are a read-back item (Part D, Q4), not an assumption.
- **Nothing of the child's voice, ever.** No recording is persisted anywhere: audio chunks live
  in an in-memory store with a TTL (`src/study_tutor/voice/service.py:154–186`) and the
  streaming design states the invariant outright (`src/study_tutor/voice/streaming_tts.py:10`).
  There is no voice step in this erasure path because there is nothing to erase.
- **The consent record — unresolved.** See Part D, Q1. Whether it cascades away with the
  student or is deliberately kept as proof that consent was held is a decision that has not
  been made, and this runbook will not quietly make it.

---

## Part D — Questions for the attended walk

Genuinely open; none of them are answerable from the repo.

**Q1 — Does the consent record cascade with the student, or outlive it?** If the consent table
carries `student_id … REFERENCES student(student_id) ON DELETE CASCADE`, then C3 stays one
statement and the record of consent is destroyed along with the account. If it does not
cascade, erasure stops being one statement (C3 gains a step) and a row naming a consenting
adult survives the erasure of the child's data — which is itself personal data. ADR-033 D5
specifies the fields and a **withdrawal timestamp**, which hints at "keep the row, mark it",
but does not decide it. **This must be settled before the consent table is built**, because the
migration encodes the answer.

**Q2 — Where does the consent record actually get captured for the very first friend?** §0
blocks on the table's absence, and ADR-033 rejected paper-outside-the-product. Is the first
account gated behind D6's build, or does Rich rule an interim in-product mechanism? Not a
runbook decision.

**Q3 — Log retention.** Application logs record `student_id` on every successful auth and
survive the cascade. Nothing in this repo dates their retention. What is it, and does it need
to be inside the 30-day SLA?

**Q4 — Two live read-backs the walk should capture:** (a) the realm's effective
`accessTokenLifespan` — the width of the C1 window between disabling and losing API reach;
(b) whether the live realm has login/admin events enabled, since realm-as-code says no but the
live realm has been imported and hand-edited over time.

**Q5 — The `seed-students` profile fields.** The CLI hard-codes name/year-group/target-grade
(A2). Is the follow-up `UPDATE` the accepted procedure, or should the CLI gain the flags before
the first friend is provisioned? A hand-written `UPDATE` against a live database, in a runbook,
is exactly the kind of step that gets fat-fingered.

**Q6 — Which deployment does the first friend's account live on?** ADR-034 D4 rules the cohort
off the household box; Lane 3 step 3 (the cloud deploy) has not landed. Rehearsing this runbook
against the household identity-server-mode deployment is useful; **provisioning a real friend
there would contradict D4** and would put a friend's data on hardware ADR-033 has no governance
posture for.

**Q7 — Does the account need the ADR-034 D5 voice walk to have passed first?** B6 treats it as
a separate gate. Confirm that reading.

---

## Receipts index

Everything this runbook claims, and where it comes from:

- **Commissioning + the atomicity requirement:** ADR-ARCH-034 D3 (the runbook, the five steps,
  the "partial subset produces a broken account" finding, and the honest correction of the
  plan's "runbook exists" claim); D2 (`provision-live-suite.sh:87–99` — the mapper, and
  "authentication *succeeds* and the API then *fails*"); D6 (one step, two records; additive
  contract change); D8 (no friend on table mode); D4 (not the household box).
- **Erasure:** ADR-ARCH-033 D6 (the one-statement cascade, the ≤30-day SLA, the mandated
  deprovisioning step, the backup arithmetic, the never-at-rest voice invariant, "an erasure
  primitive must exist"); D5 (the consent record's fields and the no-consent-no-session rule);
  D7 (minimisation — `student_id` is an opaque ID).
- **The template this is modelled on:** `deploy/keycloak/provision-live-suite.sh` — the
  dual-mode secret load (:34–53), the single-call user create with attribute + credential
  (:132–141), the role mapping (:143–144), the `student_id` mapper (:87–99).
- **The partial pieces it replaces:** `RUNBOOK-study-tutor-keycloak-standup.md:206–252`
  (manual console creation, and the `list-students` command that does not exist);
  `src/study_tutor/cli/main.py:1221–1270` (`seed-students`), :1336–1341 (the hard-coded profile
  fields).
- **The guards that make the ordering work:** `src/study_tutor/http/auth.py:286–297` (unseeded
  guard, mode-agnostic); `src/study_tutor/http/auth_keycloak.py:171–179` (missing-claim
  refusal); `deploy/keycloak/realm/study-tutor-realm.json` (`registrationAllowed: false`, roles
  `student`/`parent`, no `users` key, events off).
- **The schema:** `src/study_tutor/knowledge/store/schema_reference.sql` head `346cd366b66e`
  (the cascade table above; the year-group CHECK at :21;
  `session_one_active_idx` at :71).
- **Backups:** `deploy/postgres/backup.sh:22` (`RETENTION_DAYS=14`), :69–80 (the identity
  database dump).
- **Contract:** `docs/design/contracts/API-session-http-binding.md` §7 — additive or re-pin,
  never silent edits. Nothing in this runbook touches the frozen six.

---

*Written 2026-08-14 for Lane 3 step 5, against ADR-ARCH-034 D3 and ADR-ARCH-033 D6.2. Every
claim above was verified **textually, against files in this repo** — no live host, database,
identity server or port was contacted while writing it, and no command in it has been run.
The first execution is Rich's attended walk, which should also answer Part D.*
