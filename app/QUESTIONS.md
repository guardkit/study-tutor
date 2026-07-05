# QUESTIONS — overnight Flutter build

(no contract doubts, no dependency wants — the closed list in scope §6 was enough)

## Contract ambiguities (for FEAT-SMP-003 / next contract revision)

- **Contract §5 `resume_if_active` with duplicate `(student, subject)` actives.** The contract's wording is singular ("an active session … returns *it*") but nothing forbids duplicates — `start_session` without the flag always creates another active session (pinned by the contract test suite). Which one should the flag resume? The fake now picks the **most recently active** (aligned with `list_sessions`' "resume where you left off" ordering) and a contract test pins that choice; the real backend must either match it or the contract should gain a uniqueness rule. Raised by the 2026-07-04 morning-gate review.

## Binding-doc observations (phase 2 — for the GB10 adapter side)

- **Timestamp encoding is not explicitly pinned in the binding doc** (`API-session-http-binding.md` at BINDING_SHA `6eb7b88`). The table defers payload shapes to contract §5, which names the fields (`ts`, `started_at`, `last_activity`) but not their JSON encoding. p2-wave-3's `HttpSessionApi` assumes ISO-8601 strings (`DateTime.parse`) — the natural JSON encoding and almost certainly what the adapter emits, but it is an assumption, not a bound commitment. If the wave-7 live run disagrees, that's a binding-doc gap to close (add one line to the doc pinning **ISO-8601 with an explicit UTC offset** — an offset-less string would silently parse as device-local time on the app side), not an app bug. Raised 2026-07-05, p2-wave-3.

## Open decision for Rich (phase 2)

- **Fail-closed residency enforcement for `API_BASE_URL`?** The wave-5 review established (engine-verified) that Android's network-security-config does not govern the app's own `dart:io`/`package:http` traffic on current Flutter engines — cleartext is allow-all for the app's HTTP in debug AND release, so the NSC is hygiene for future platform-stack traffic, not an enforcement of ADR-ARCH-015. If fail-closed enforcement is wanted (a release build pointed at a non-household URL refusing to compose), the natural seam is a host allowlist in `composeSessionApi()` (`main.dart`) — e.g. RFC1918 + CGNAT (Tailscale 100.64/10) + `*.ts.net` + bare hostnames. Deliberately NOT implemented in p2-wave-5: it changes composition behaviour beyond the wave spec and risks over-blocking a legitimate household setup. Raised 2026-07-05.

## Notes for morning review (not questions)

- **`git diff main` shows a phantom deletion of `docs/runbooks/RUNBOOK-overnight-fable-flutter-launch.md`.** Not a blast-radius violation: `main` moved ahead after this branch was cut — commit `3d448ac` (on main only) added that file post-branch, so a plain diff against `main` reports it as "deleted" here. `git log main..HEAD -- docs/` confirms no overnight commit touched anything outside `app/**`. Diffing against the merge-base (`git diff 002a313 --stat`) shows `app/**` only.
