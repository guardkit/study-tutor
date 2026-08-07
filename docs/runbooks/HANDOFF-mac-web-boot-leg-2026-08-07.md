# HANDOFF — the Flutter-web boot-claim leg (Mac session; from the spark master, 2026-08-07)

**Date:** 2026-08-07, written on the spark (the master session for today's parallel
build window, Rich's word in-session). **Division of labour (standing, 2026-08-03):**
spark = server side, Mac = `app/` client only. This leg is app-only.

## What the spark is doing today (so we don't collide)

Four lanes in parallel, all server-side or docs — none touches `app/`:

- Lane 2 step 3: the golden-quote fabrication eval harness + citation-anchors
  fix-or-defer (S2's bar).
- Lane 3 steps 1–2: the residency/governance ADR + multi-user ADR **drafts**
  (ratification stays Rich's).
- Lane 6 step 2: the robot app-distribution investigation/design doc (Rich's gate
  before build).
- Lane 1 step 1: the `fleet-evals` harness seed (local — the GitHub repo does not
  exist yet; creation is flagged to Rich, not unilateral).

**Zero contract edits are planned.** If anything contract-shaped emerges, the spark
stops and queues it for Rich — you will not see a re-pin today.

## Ground yourself first (non-negotiable)

1. Root [`CLAUDE.md`](../../CLAUDE.md) → the mission + THE PLAN
   ([`study-tutor-plan-of-record.md`](../study-tutor-plan-of-record.md)).
2. `git pull --ff-only` before anything; the spark pushes to the same main.
3. Fences: `app/` only; six-verb contract + §7 frozen (no shape edits); broker
   isolation standing; gates = `flutter analyze` clean + dart suite green
   (424/424 baseline, 2026-08-04).

## THE LEG: establish an honest Flutter-web boot claim

**Why:** the plan's App row says **"Web: no boot claim"**, and Lane 3 step 4's
upload-surface decision ("Flutter web vs a minimal separate web page" for scanned
study-guide uploads) is currently being made blind. The residency/multi-user ADR
drafts the spark is writing today will carry the vehicle question — your receipt is
the evidence that decision needs. This is the honest-iOS convention applied to web:
*compiles + boots + what actually works, stated plainly* (mission law 8).

**Do, in order (stop at the first hard wall and receipt it — a red receipt is a
valid receipt):**

1. `flutter build web` on the app — does it compile at all? Capture the first
   blocking error if not (conditional imports, plugin support, `dart:io` usage —
   record_platform/audio plugins are the likely suspects).
2. If it compiles: `flutter run -d chrome` against the LIVE spark `:8100`
   (table auth, `token-lilymay` — read-only walk, do NOT start real sessions as
   lilymay; use `token-alex` if you need a session receipt). Walk: sign-in →
   subject picker → one text turn → history. Voice is EXPECTED to be broken on
   web (record/audio plugins) — say so plainly rather than chasing it.
3. Note CORS/cleartext-HTTP behaviour — web hits the browser's rules the
   Android walk never did; a CORS block IS a finding (it feeds the Lane 3
   TLS/domain work).
4. Receipt: a short RESULTS note (`docs/runbooks/RESULTS-mac-flutter-web-boot-<date>.md`)
   — boots / doesn't, what worked, what broke and why, and your one-paragraph
   recommendation: is Flutter web a plausible upload-surface vehicle, or should
   Lane 3 step 4 plan a minimal separate page? Update the plan's App-row Web
   claim in the same commit ("no boot claim" → whatever is now true).

**Explicitly NOT this leg:** fixing web voice, adding web-specific plumbing,
touching contracts, any server file. If web needs client changes just to boot,
receipt the list — don't build it today without checking back.

## Interlock

Push your receipt to main; the spark master folds it into the Lane 3 ADR
evidence at its coordinator review (before ~21:00 UK tonight). If you finish
early, `git pull` — the spark may have queued a follow-up leg at the tail of
this file by then.

## Session-end ritual (standing)

Gates green → receipt named → plan cell updated in the same commit → push.
