# ADR-ARCH-025 — Flutter app lives at `app/` in the study-tutor repo

## Status

Accepted

**Date:** 2026-07-03
**Phase:** Mobile+voice slice (pre-FEAT-SMP-003)
**Related:** [API-session-cross-device.md](../../design/contracts/API-session-cross-device.md) (the contract the app consumes, pinned at `CONTRACT_SHA=22791afbcdb3b71abbe6bd2f1b8e18218988942f`), [flutter-app-scope.md](../../research/ideas/flutter-app-scope.md) (G-P1), [RUNBOOK-overnight-fable-flutter.md](../../runbooks/RUNBOOK-overnight-fable-flutter.md) (G-P2 requires this ADR), ADR-FLEET-003 (HTTP/WS surface for app clients).

## Context

The v1 Flutter client is a walking skeleton plus one contract-shaped
vertical slice against an in-process fake — no network, no backend
coupling at build time. Its only hard dependency on this repo is the
**contract document**: the fake and its contract tests are written
against `API-session-cross-device.md` at a pinned SHA. A separate repo
would turn every contract iteration into a cross-repo version dance
(publish, pin, bump) for a single developer and a document that lives
here. (Repo-wide policy ADRs — e.g. ADR-ARCH-015's no-telemetry rule —
also bind the app, but they'd bind it from any repo.) The overnight build pattern (runbook) also wants one worktree,
one blast radius, one diff to review in the morning.

## Decision

**The Flutter app lives at `app/` in the study-tutor monorepo.**

- `app/` is a self-contained Flutter project (`flutter create` layout);
  the backend never imports from it and it never imports backend code —
  the shared artifact is the contract doc, by SHA.
- Repo tooling stays split-brain by path: guardkit/Python quality gates
  do not apply under `app/**`; the app's gates are
  `flutter analyze` / `flutter test` / `flutter build apk --debug`
  (runbook §1 G-F0 choice + §2 rule 2).
- Overnight-run blast radius (`app/**` + `docs/research/ideas/flutter-*`,
  runbook §2 rule 3) maps 1:1 onto this placement.

**Extraction triggers — move `app/` to its own repo when ANY of:**

1. **A second backend** consumes the app (or the app targets a second
   backend) — the contract stops being a single in-repo document.
2. **A second developer** works primarily on the app — branch/review
   traffic on `app/**` starts colliding with backend work.
3. **Diverging release cadence** — app store releases need tags,
   changelogs, or CI cycles independent of backend deploys.
4. **Structural toolchain friction** — Flutter/Dart tooling (SDK pins,
   CI images, IDE config) materially degrades the Python workflow in
   this repo, or vice versa, beyond what path-scoping fixes.

Until a trigger fires, extraction is deliberately not on the roadmap.

## Alternatives considered

- **Separate `study-tutor-app` repo now.** Rejected: cross-repo
  contract pinning and duplicated runbook/instrument plumbing for zero
  present benefit — one developer, one backend, no independent release.
- **Monorepo tool (melos/workspace) or `packages/` split.** Rejected as
  premature structure; one Flutter project needs none of it.

## Consequences

**Positive:** contract, scope, build plan, and app sit in one worktree —
one pin, one diff, one morning review; the runbook's gates and blast
radius work unchanged.

**Negative:** repo carries two toolchains; mixed-language noise in
searches and CI-someday. Accepted — bounded by the extraction triggers
above, and `app/**` path-scoping keeps the gates disjoint.

## References

- RUNBOOK-overnight-fable-flutter §1 (G-P2), §2 rules 2–3.
- flutter-app-scope.md §8 (definition of done, per-wave gates).
