# RESULTS — Overnight Fable Flutter run, 2026-07-04

**Runbook:** [RUNBOOK-overnight-fable-flutter.md](RUNBOOK-overnight-fable-flutter.md) (+ [launch procedure](RUNBOOK-overnight-fable-flutter-launch.md)).
**Branch:** `overnight/fable-flutter-2026-07-04`, HEAD `3a56897`, merged to `main` after the gate below.
**Contract pin:** `22791afbcdb3b71abbe6bd2f1b8e18218988942f`. **Model:** claude-fable-5[1m], `--dangerously-skip-permissions`, tmux+caffeinate, fully unattended.
**This is the Fable data point the runbook §6 pre-registered (second hype-ledger entry: attended-authored plan, unattended frontier execution, resumable by construction).**

## Headline numbers

| Metric | Value |
|---|---|
| Waves attempted (unattended) | 9 of 9 (waves 1–9; wave-0 was attended) |
| Waves completed green | **9** |
| Waves blocked | 0 |
| Interventions | 0 (by construction — nobody was watching) |
| In-run reds | 2, both fixed on first retry (wave-3 analyzer info; wave-8 test-finder artifact) |
| Tests at HEAD | 75 (contract suite §4 1–9, happy-path slice, 4 error handlings, skeleton, units) |
| Contract doubts / dependency wants | 0 / 0 |
| Wall clock | 2h 49m (≈23:5x–02:4x) · API time 26m 35s |
| Quota | **$18.63** · 112.4k output tokens · 9.4M cache read · 83% of the 5h session window |
| Code | +2,632 / −252 lines, one commit per wave |

## Morning gate (pre-registered in build plan §4) — ALL PASS

- **HEAD re-verifies green** ✅ — analyze clean, 75/75 tests, apk-debug built (attended re-run).
- **Emulator boot to checkpoints** ✅ — Pixel_9a, adb-driven walk with screenshots: boots to sign-in → home → start session → two turn round-trips render → back → home shows "maths · 2 turns" card → Resume reloads transcript in order → End session → "Session ended" banner, input disabled, End affordance gone → home drops the ended session. Zero crashes.
- **Blast radius** ✅ — merge-base diff (`main...HEAD`) touches `app/**` only. (The `git diff main` phantom-delete of the launch runbook is explained in QUESTIONS.md: main moved ahead post-branch.)
- **PROGRESS.md coherent** ✅ (per-wave log + honest red-count + HANDOFF) · **QUESTIONS.md triaged** ✅ (one note, verified correct, no action).

## Defects found in morning review

Adversarial multi-agent review of the full diff (4 dimensions, every finding independently verified with refute-first prompts; two proven by mutation testing): **10 confirmed, 0 refuted, 0 blockers** — 5 should-fix, 5 nit. None invalidate the slice; several are latent-only (bite when the real HTTP adapter replaces the fake).

Should-fix:
1. `fakes/fake_identity_provider.dart` — token invalidation is permanent and `signIn()` re-issues the same constant token, so the Unauthenticated → re-sign-in recovery path dead-ends (latent; no test attempts re-sign-in).
2. `test/errors/unauthenticated_test.dart` — "stack is cleared" assertions are vacuous (`find.text` skips offstage routes); **mutation-proven**: replacing `pushAndRemoveUntil` with plain `push` still passes.
3. `test/ui/walking_skeleton_test.dart` — "sign-in is replaced, not stacked" assertion vacuous for the same skipOffstage reason; **mutation-proven**.
4. `ui/home_screen.dart` — Start/Resume have no in-flight double-tap guard (the send path has one), so a jank double-tap creates two sessions/screens; window widens with a real adapter.
5. `ui/session_screen.dart` — transcript ListView never scrolls to bottom (no controller/`reverse`), so past ~6–8 turns new messages render below the fold and resume opens at the oldest message.

Nit: fake's `resumeIfActive` picks oldest-created on duplicate `(student,subject)` actives (contract §5 wording ambiguity — belongs in QUESTIONS.md); turn-order unit test is a tautology on a list literal; Principal §3 test can't fail if `studentId` is added; TextField `enabled:!_sending` will drop keyboard focus per send once latency is real (latent); README DoD item 1 was pre-ticked before the emulator boot that verifies it (boot has now happened — this run — so the item is retroactively true).

## Follow-up outcome (same day)

All 10 findings **fixed** in `wave-10: morning-review fix-wave [green]` (attended, 2026-07-04): 80 tests at HEAD (+6 regression tests covering the fixes, −1 removed tautology), analyze clean, apk-debug built. Both previously-vacuous assertions were re-verified by mutation after the fix — the mutations that used to pass now fail the suite. The `resume_if_active` duplicate-pick ambiguity is logged in `app/QUESTIONS.md` for the FEAT-SMP-003 contract work.

## Verdict

Gate **passed**; branch **merged**. The 10 review findings are follow-up work (a small attended fix-wave), not rollback grounds. Notable for the ledger: the two vacuous test assertions are exactly the failure class an unattended run can't catch about itself — the pre-registered morning review earned its place in the loop.

*Run artifacts: `app/PROGRESS.md` (per-wave log + HANDOFF), `app/QUESTIONS.md`, wave commits `c65cfef…3a56897`, full review transcript retained in session workflow `wf_4d1acd71-fe4`.*
