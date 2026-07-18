# MacBook session prompt — A3 toolchain-of-record verify (paste into Claude Code on the Mac)

> You are the MacBook leg of the weekend auth+voice window (coordinator session runs
> on the GB10 — see `docs/runbooks/HANDOFF-weekend-auth-voice-fable-window.md` and
> `docs/runbooks/REVIEW-C1-weekend-auth.md` §A3 for full context; read both).
>
> **Your job is VERIFY + REPORT only. Do NOT merge, push, commit, run guardkit, or
> touch `.guardkit/` — the GB10 session owns the merge after Rich approves.**
>
> 1. `git fetch origin && git checkout autobuild/FEAT-AUTH-003`
> 2. `cd app && flutter analyze && flutter test` with this Mac's official Flutter
>    3.44.4 (this is the toolchain-of-record run; the branch was built and tested on
>    the GB10's arm64 git-bootstrap Flutter).
> 3. Expected: **analyze 0 issues, 338/338 tests pass.** Report the exact numbers and
>    ANY delta verbatim — a delta is signal (toolchain difference), not noise to fix.
>    Do not modify code to make a delta pass; report it.
> 4. Then support Rich's FULL_REQUIRED skim: walk him through
>    `git diff main -- app/lib/adapters/keycloak_identity_provider.dart` (KCA3-003,
>    cx-8 security core) — the review packet's fence table + the six adversarial-review
>    fixes (commit `2cb537f`) are the reading guide. Optionally also `app/lib/main.dart`
>    (flavour wiring + coherence guard) and `app/lib/adapters/secure_session_store.dart`.
> 5. When Rich is satisfied, have him tell the GB10 session **"A3 approved"** (plus your
>    verify numbers) — it merges, then Sunday's chain runs: C2 live-suite provisioning +
>    live realm redirect-URI patch → C3 keycloak-mode deploy + KC-G2 → C4 KC-G3.
>
> Stretch (prep only, do NOT run): draft the KC-G3 phone-build command for Sunday —
> `flutter build … --dart-define=KEYCLOAK_ISSUER=https://whitestocks.tailebf801.ts.net:8443/realms/study-tutor --dart-define=API_BASE_URL=<decided at C3: the keycloak-mode :8100/:8101 URL>`
> — the API_BASE_URL value is decided at C3 deploy time by the GB10 session.
