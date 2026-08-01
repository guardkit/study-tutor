# RUNBOOK — re-point the Reachy robot's tutor path from the GB10 to the spark

**Lane:** plan-of-record Lane 6, step 1 (`docs/study-tutor-plan-of-record.md`) ·
**Written:** 2026-08-01 · **Status: NOT YET RUN — mark each step ✅ with a date as you go**
**Why now:** the GB10's tutor stack was retired 2026-07-26 (spark encapsulation), but the
fleet-gateway config was never re-pointed (confirmed outstanding, Rich 2026-08-01) — so the
robot's `ask_tutor` / student-model path is presumed DOWN. This runbook is the recorded
operator item 3 of `HANDOFF-study-tutor-full-encapsulation-spark.md`, made executable.

**Where it runs:** on the **fleet-gateway host** (its own repo/box — the machine running the
Reachy s2s/persona services, alongside the s2s unit on the GB10 `:8765`, which is fenced and
does NOT move). Not runnable from the spark (spark→GB10 ssh is not authorized; the working
direction is GB10→spark).

**The one-line summary of the change:** fleet-gateway's `ask_tutor` + student-model base URL
moves from the GB10 `:8100` to **`http://spark-fcf6.tailebf801.ts.net:8100`** (or
`http://100.105.247.62:8100` if the gateway host doesn't resolve MagicDNS — prefer the name
so a future re-home is a DNS story). **The static bearer token is unchanged** — spark
`:8100` runs the same table-token auth mode; FEAT-AUTH-004 (device pairing) is untouched.

---

## 0. Preflight — prove the target is up, from the gateway host

```bash
# From the fleet-gateway host. Expect: {"status":"ok"}
curl -s http://spark-fcf6.tailebf801.ts.net:8100/healthz

# Prove the robot's existing bearer works against spark (expect 200 + JSON student model,
# NOT 401/403). $ROBOT_BEARER = the same static token the gateway already holds.
curl -s -H "Authorization: Bearer $ROBOT_BEARER" \
  "http://spark-fcf6.tailebf801.ts.net:8100/api/student-model?subject=english" | head -c 300
```

If either fails, STOP — fix reachability/token before touching config (the tailnet name
resolves via MagicDNS; fall back to `100.105.247.62`).

## 1. Find the pinned URL in the fleet-gateway repo

The consumer pin lives in fleet-gateway's `common/tutor_client.py` (the binding §2.2 names
`common.tutor_client.STUDENT_MODEL_PATH`; the base URL is beside it or in the service env).
Locate every occurrence — config may exist in both the repo and a deployed env file:

```bash
cd <fleet-gateway checkout>
grep -rn "8100\|promaxgb10\|100\.84\.90\.91" --include="*.py" --include="*.env*" --include="*.yaml" .
```

Expect hits in `common/tutor_client.py` (or its config source) for the `ask_tutor` +
`query_student_model` base URL. Note: the **Pi may carry a hand-edited clone** (recon delta
D7) — check the deployed copy on the robot host too, not just the repo.

## 2. Make the change

Change the base URL at its single source (constant or env var) from the GB10 value to
`http://spark-fcf6.tailebf801.ts.net:8100`. Do **not** touch: the bearer, the
`STUDENT_MODEL_PATH` path constant, `DEFAULT_SUBJECT` (`common/subject.py` — the
SUBJECT_DEFAULT seam), or anything about the s2s unit `:8765`. Commit in the fleet-gateway
repo with a message citing this runbook; redeploy/restart the gateway service the way that
repo's own runbook prescribes (if the Pi clone is hand-edited, prefer the clean re-clone
path over another hand edit).

## 3. Smoke — the robot path, end to end

1. **Direct, from the gateway process's host** (proves config took): trigger or replay one
   `query_student_model` call — expect a real student model, not the graceful
   "unavailable" fallback (that fallback is exactly what a dead URL produces, so
   "no error" is NOT success — look for real data).
2. **The real thing:** one spoken `ask_tutor` round-trip on the robot — the Scholar asks
   the tutor, a session lands on Lilymay's active `(lilymay, english)` session (or starts
   one), the reply is spoken. This is the recorded smoke from the handoff ("one ask_tutor
   call from the robot path").
3. **Cross-check on the phone:** the live robot-session mirror should show the robot's
   turns appear (the `turns?since=` poll — same session, D8 pickup). This confirms the
   robot is writing to the SAME backend the phone reads.

## 4. Rollback

Config back to the GB10 URL + service restart — **but note the GB10 `:8100` container is
DOWN** (retired). Real rollback is therefore: `docker compose -p study_tutor_http up -d` on
the GB10 first (both instances share the same NAS state, so nothing forks — the handoff's
own rollback note), then re-point back. In practice: if the spark smoke in step 0 passed,
rollback should never be needed.

## 5. Record completion (do not skip)

- Tick Lane 6 step 1 in `docs/study-tutor-plan-of-record.md` (✅ DONE + date + the smoke
  receipt), and update the Robot row of the current-state map.
- Strike operator item 3 in `HANDOFF-study-tutor-full-encapsulation-spark.md`.
- If the Pi clone was hand-edited: note the re-clone/dedup in the fleet-gateway repo.
