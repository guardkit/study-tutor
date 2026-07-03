# RUNBOOK — Overnight Fable build run (Flutter app)

**Status:** Ready pending gates G-P0…G-R1. **Date:** 2026-07-03. **Owner:** Rich.
**Purpose:** Run Claude Code (Fable) unattended overnight against a committed build plan, burning expiring flat-rate quota, with **zero morning-after dependence on the run having finished**. Generalise to `ai-transition` on second use.
**Decision frame:** Deliberate, bounded DF-003/DF-006 exception — expiring quota, nothing on the critical path depends on completion, fallback is *any other model + the same build plan*. Log one line in the frontier-exception ledger sense: attended-authored plan, unattended frontier execution, resumable by construction.

---

## 1. Gates before launch — ALL green, or the night's target flips to B2 (fleet-evals PO suite)

| Gate | Proves | How |
|---|---|---|
| **G-P0** | Session contract ratified + pinned | `/arch-refine` output committed; record `CONTRACT_SHA=$(git rev-parse HEAD)` |
| **G-P1** | Scope exists | `docs/research/ideas/flutter-app-scope.md` — brutal MVP cut, mock-backend strategy, ADR-ARCH-015 constraints, approved-dependency list |
| **G-P2** | Structure decided | Monorepo ADR filed (`app/` in study-tutor, extraction triggers named) |
| **G-P3** | Build plan exists | Wave structure; per-wave gates (§3); contract pinned to `CONTRACT_SHA`; morning gate (§6) written in as pre-registered |
| **G-F0** | Toolchain ready | `flutter doctor` clean **for the chosen build target**; `flutter create app` scaffold committed; `cd app && flutter test` green; the per-wave build gate succeeds once while attended. **Build-gate selection:** `flutter build apk --debug` if the Android SDK + licenses are ready; else `flutter build web` (Chrome only) or `flutter build macos --debug` (Xcode only) — record the choice in the build plan. **CHOSEN 2026-07-03: `flutter build apk --debug`** — doctor verified: Flutter 3.44.4 stable, Android SDK 36.1.0 ✓; sole warning was CocoaPods 1.12.0 — **resolved 2026-07-03** (orphaned gem binstubs removed; pod 1.16.2; doctor fully clean, all ✓) |
| **G-R0** | Run environment | Worktree + branch `overnight/fable-flutter-<date>`; tmux session; `caffeinate` armed; mains power; Claude Code model pinned to Fable; house permissions mode |
| **G-R1** | Instruments ready | `app/PROGRESS.md` initialised with wave list; empty `app/QUESTIONS.md` |

## 2. Hard rules for the run (encoded in the kickoff prompt — do not soften)

1. **Wave discipline.** At each wave start, re-read the build plan and `PROGRESS.md` — the plan on disk is the source of truth, not conversation memory. One wave at a time.
2. **Green means:** `flutter analyze` clean + `flutter test` green + the build-gate command from G-F0 succeeds. Then commit `wave-N: <name> [green]`, append PROGRESS.md, proceed. Never start wave N+1 on a red wave N.
3. **Blast radius:** write only under `app/**` and `docs/research/ideas/flutter-*`. Backend `src/**`, `deploy/**`, guardkit config, the contract docs: **read-only**. If the contract looks wrong, log it in QUESTIONS.md and continue against the pin — never redesign the contract overnight.
4. **Blocked protocol:** a wave failing twice → mark blocked in PROGRESS.md, move to the next *independent* wave. Two blocked waves → stop cleanly (rule 6).
5. **Dependencies:** nothing outside the scope's approved list; wants go in QUESTIONS.md.
6. **Stop cleanly** on quota/auth failure, systemic errors, or rule-4 exhaustion: commit green work, write a HANDOFF section in PROGRESS.md (state / next step / blockers), end the session. No retry loops. Long context → prefer finishing the current wave over starting another.
7. **Local commits only.** No pushes; morning review pushes.

## 3. Launch

```bash
cd ~/Projects/appmilla_github/study-tutor
git worktree add -b overnight/fable-flutter-$(date +%F) ../study-tutor-overnight
cd ../study-tutor-overnight
tmux new -s fable-night
caffeinate -dims &
claude   # model: Fable; house permissions mode
```

**Kickoff prompt (paste):**

> Read `docs/research/ideas/flutter-app-scope.md`, the build plan, `app/PROGRESS.md`, and the pinned session contract at CONTRACT_SHA=`<sha>`. Execute the build plan wave by wave under the hard rules in `docs/runbooks/RUNBOOK-overnight-fable-flutter.md` §2 — re-read plan + PROGRESS.md at every wave start; green = analyze + test + apk-debug; commit per wave; write only under `app/**`; contract is pinned, questions go to QUESTIONS.md; stop cleanly per rule 6 when quota ends or two waves block. The morning gate is pre-registered in the build plan — optimise for *waves that survive review*, not waves attempted.

## 4. What the night is NOT for

No backend code, no schema/Alembic, no guardkit config changes, no pushing, no contract edits, no dependency sprees, no simulator/integration tests (flaky unattended — `flutter test` only; simulator boot is a morning check).

## 5. Instruments

`PROGRESS.md` (per-wave log + HANDOFF) and `git log --oneline` are the morning interface. The full transcript is retained — gold trace, harvest-grade regardless of outcome.

## 6. Morning-after gate (pre-registered — write into the build plan before launch)

- Every commit at HEAD re-verifies green (spot-run analyze + test).
- App boots on simulator to the wave-defined checkpoint (attended, morning).
- `git diff main --stat` shows **zero** files outside `app/**` + allowed docs.
- PROGRESS.md coherent; QUESTIONS.md triaged.
- **Fable data point recorded:** waves attempted / completed / blocked, defects found in review, quota consumed. (Second entry in the hype ledger; interventions = 0 by construction.)
- Any red → `git worktree remove` + branch delete is the whole rollback; green commits survive regardless. Whatever didn't land is still in the build plan — Opus or local resumes from the same artifact.

---

*Second use of this pattern: promote a generalised copy to `ai-transition/docs/runbooks/` and parameterise the target repo/toolchain gates.*
