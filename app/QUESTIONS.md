# QUESTIONS — overnight Flutter build

(no contract doubts, no dependency wants — the closed list in scope §6 was enough)

## Contract ambiguities (for FEAT-SMP-003 / next contract revision)

- **Contract §5 `resume_if_active` with duplicate `(student, subject)` actives.** The contract's wording is singular ("an active session … returns *it*") but nothing forbids duplicates — `start_session` without the flag always creates another active session (pinned by the contract test suite). Which one should the flag resume? The fake now picks the **most recently active** (aligned with `list_sessions`' "resume where you left off" ordering) and a contract test pins that choice; the real backend must either match it or the contract should gain a uniqueness rule. Raised by the 2026-07-04 morning-gate review.

## Binding-doc observations (phase 2 — for the GB10 adapter side)

- **Turn latency on the dev deployment exceeds the contract's own budget AND ceiling.** Measured from the Mac against `promaxgb10-41b1…:8100` (2026-07-05): ~66s with model cold-load, **~43s warm** — the contract pins `turn` at p95 < 10s with a 30s hard ceiling (API-tutoring SR-07; cross-device §5 keeps the budget "unchanged"). This is an adapter/deployment-side conformance gap (model choice, per-turn multi-call orchestration, or llama-swap sizing), not an app bug: the live harness deadline was raised to 120s (`test_live/live_contract_backend.dart`, loudly documented) so the FUNCTIONAL conformance run stays meaningful; the app's 15s product deadline is unchanged — meaning the real app UI would currently show "connection problem" on most turns against this deployment. Needs GB10-side triage before the app points at it for real use. Raised 2026-07-05, wave-7 Mac acceptance.

- **Timestamp encoding** — ~~not explicitly pinned in the binding doc~~ **RESOLVED by live probe 2026-07-05**: the adapter emits ISO-8601 with an explicit `+00:00` offset; `DateTime.parse` handles it. Still worth one binding-doc line at the next coordinated edit, but no longer a risk.

- **LIVE-RUN TRIAGE (wave-7 Mac acceptance, attempt 1 — 2026-07-05): 22/35 green; all 13 failures triaged to TWO adapter-side wire bugs + the perf tail below. Binding doc is the arbiter for both; app unchanged.**
  1. **Turn-entry field name: server sends `timestamp`, binding table + contract §5 say `ts`** (`turns:[{role,content,ts}]` — verbatim in the frozen binding §2 resume_session row). Every transcript-carrying response (resume, resume_if_active-with-turns) fails the app's §5 shape guard → 8 failures. Probe evidence: `GET /api/sessions/{id}/resume` → `{"role":"user","content":…,"timestamp":"2026-07-05T10:54:42.533379+00:00"}`. `role` values are correct (`user`/`tutor`).
  2. **`turn_count` counts transcript rows, not (user,tutor) pairs**: one turn → server reports `turn_count: 2`. Contract §5 bumps once per pair ("appends the (user, tutor) pair durably, bumps turn_count"); scope §3.6 pins `turn_count: 2` after TWO turns; the 35 contract tests pin pair-counting on both backends → 4 failures (s9 ended-status, s4 monotonic ×2-as-observed, s4 durability, s5 list ×2). Probe: status after 1 turn → `"turn_count": 2`.
  3. One failure was a >120s first-turn cold-load (deadline) — the latency item below; rerun-transient.
  
  Everything else passed live first-contact: §9 envelope ×4 (404/410/403/401), auth signed-out + stale-token, ownership on every session_id verb + partition, lifecycle terminality + status carve-out, list filters/limit/ordering, resume_if_active keying, reset isolation. Expected outcome after the two backend fixes: 35/35.

## Open decision for Rich (phase 2)

- **Fail-closed residency enforcement for `API_BASE_URL`?** The wave-5 review established (engine-verified) that Android's network-security-config does not govern the app's own `dart:io`/`package:http` traffic on current Flutter engines — cleartext is allow-all for the app's HTTP in debug AND release, so the NSC is hygiene for future platform-stack traffic, not an enforcement of ADR-ARCH-015. If fail-closed enforcement is wanted (a release build pointed at a non-household URL refusing to compose), the natural seam is a host allowlist in `composeSessionApi()` (`main.dart`) — e.g. RFC1918 + CGNAT (Tailscale 100.64/10) + `*.ts.net` + bare hostnames. Deliberately NOT implemented in p2-wave-5: it changes composition behaviour beyond the wave spec and risks over-blocking a legitimate household setup. Raised 2026-07-05.

## Notes for morning review (not questions)

- **`git diff main` shows a phantom deletion of `docs/runbooks/RUNBOOK-overnight-fable-flutter-launch.md`.** Not a blast-radius violation: `main` moved ahead after this branch was cut — commit `3d448ac` (on main only) added that file post-branch, so a plain diff against `main` reports it as "deleted" here. `git log main..HEAD -- docs/` confirms no overnight commit touched anything outside `app/**`. Diffing against the merge-base (`git diff 002a313 --stat`) shows `app/**` only.
