# RUNBOOK — the base-in-the-loop trial (the last evidence step before the serving ruling)

**Written:** 2026-08-14 (Rich's word: "prepare it now") · **Lane:** plan Lane 1 step 1 →
ruling-queue item 3 (the serving ruling) · **Status: PREPARED, NOT YET RUN — tick each
step with a date as you go.**

## Why this trial exists (plainly)

The 2026-08-13 eval says the stock Gemma 4 base beats our fine-tune on every instrument
(single-turn 106–7, criterion 73.9 vs 67.0, multi-turn 20–0). But that eval judged the
BARE models. Nobody — including Rich — has ever experienced the base INSIDE the real
Player–Coach loop (retrieval, quote verification, the async coach, the planner, streamed
voice) that Lilymay actually uses. Four months of "it's brilliant" are evidence about the
system-with-fine-tune. This trial is the missing pair: the system-with-base, felt by the
same person, over the same kind of sessions. It converts the serving ruling from "trust
the harness" into "I felt the difference myself" — or "I felt none," which is equally
decisive.

## The mechanism (one line; reversible in one line)

The tutor container reads its Player model from `TUTOR_LOCAL_MODEL` (default
`gemma4-tutor`, `deploy/http/docker-compose.yml:58`). `gemma4-base` already serves on
llama-swap `:9000` (registered 2026-08-13, sha-verified, served with the tutor's jinja —
the parity caveat). The `:8101` Keycloak container is left on the fine-tune throughout
(untouched control; also the phone's Keycloak flavour if it's ever wanted mid-trial).

## 0. Fairness pre-registration (write BEFORE the flip; this is the whole point)

Rich writes down, in this file, BEFORE flipping, what "better" means to him in a session
— e.g. *did it draw me in? did I do the thinking? did it stay on my topic? did it slip on
a fact? did it feel like a tutor or a textbook? would Lilymay stick with it?* — as 4–6
one-line criteria. Then he scores EVERY trial session against exactly those lines and
nothing else. (This mirrors the eval's pre-registration discipline: no moving the goal
after seeing the answer.)

**Rich's criteria (fill in):**
1. …
2. …
3. …
4. …

**Blinding option (recommended if practical):** a second person (or a coin + a note in a
sealed envelope) sets `TUTOR_LOCAL_MODEL` per session so Rich does NOT know which model
he's talking to; the assignment is revealed only after all sessions are scored. If Rich
runs it alone, unblinded is honest too — say so in the receipt.

## 1. Flip (Rich attended; the standing deploy discipline)

```bash
# 0. Nobody mid-session (Lilymay uses this for real):
docker run --rm postgres:16 psql "$STUDY_TUTOR_PG_DSN" -tAc \
  "SELECT session_id,last_activity FROM session WHERE status='active' AND last_activity > now() - interval '10 minutes';"
# 1. Add ONE line to deploy/http/.env (gitignored; no repo change):
#    TUTOR_LOCAL_MODEL=gemma4-base
# 2. Recreate the table-mode container only:
cd deploy/http && docker compose up -d
# 3. Prove it took: the boot log's model line names gemma4-base; a healthz 200.
docker logs study_tutor_http --since 2m 2>&1 | grep -iE "model|LOCAL_MODEL" | head
```

Note the serving swap: requesting `gemma4-base` on llama-swap evicts `gemma4-tutor`; the
keepalive's `tutor` set will keep trying to revive it. For a clean trial either pause the
keepalive for the session (`sudo systemctl stop llama-swap-keepalive.timer`, restart
after) or accept one cold-load per session start. Whichever you choose, write it down.

## 2. The sessions (3–4, across subjects, over a day or two)

- Same kind of sessions Rich normally has with it: at least one English text session, at
  least one non-English (maths/science — the base's measured strengths were AO framing
  and scaffolding; see if that FEELS like anything), at least one voice session on the
  phone (streamed voice is where the fine-tune's short turns might have felt natural).
- Score each against the §0 criteria immediately after; note anything the criteria
  missed (that's a finding about the criteria, recorded separately).
- Phone receipts: session ids + a screenshot or two — the mirror/history is the log.

## 3. Rollback (any time, one line)

Delete the `TUTOR_LOCAL_MODEL` line from `deploy/http/.env`, `docker compose up -d`.
Verify the boot log names `gemma4-tutor` again.

## 4. Receipt → the ruling

Fold scores + notes here under a dated **RESULTS** heading, then the ruling is Rich's, over
the full field: the three-instrument eval + this felt trial. Outcomes and what each means:
- **Base feels as good or better** → serve the base (a permanent config default, no
  weights hosted ⇒ the ADR-031 D4.2 licence conflict is moot for serving); the Lane 7
  re-train becomes an unhurried experiment that must BEAT the base on all three
  instruments AND in the loop to ever ship.
- **Fine-tune feels better despite the eval** → that is a genuine, important finding:
  it means the eval instruments are missing something the loop surfaces — we go find
  what (candidate: the coach's revise loop interacting differently with the two styles)
  before ruling.
- **Can't tell them apart** → serve the base (simplicity + the eval's factual-accuracy
  edge decide it).
