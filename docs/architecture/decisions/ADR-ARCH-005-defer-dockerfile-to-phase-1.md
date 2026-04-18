# ADR-ARCH-005 — Defer Dockerfile to Phase 1+; venv-only install for Phase 0

## Status

Accepted

**Date:** 2026-04-18
**Phase:** Phase 0
**Related:** ADR-ARCH-004, LES1 §3 (DKRX), CC-05, phase-0-scope.md §Do-Not-Change

## Context

LES1 §3 DKRX identified a failure mode in specialist-agent where the
Dockerfile used `pip install .` while the guide documented
`pip install -e '.[providers]'`, causing provider packages to be
missing at runtime. The prescription (SR-05 / CC-05) is that
Dockerfile install commands must be a literal match for the documented
venv install.

Study Tutor's Phase 0 target is a public-repo-ready skeleton
deployable on a clean MacBook via the README quickstart. Phase 0 is
**not** shipping a hosted service. Lilymay's usage today is MacBook
+ GB10 + Tailscale, all via local venv install. The hackathon
submission is a walkthrough, not a deployable artefact.

The Phase 0 scope's "Do-Not-Change" list explicitly states "No
Dockerfile in Phase 0. Venv-only install documented." The `/system-arch`
session honours this.

## Decision

Phase 0 ships **no Dockerfile**. All install instructions in the
README use `pip install -e '.[providers]'` in a venv.

CC-05 is **paused** for Phase 0 and reactivates when a Dockerfile is
first added (Phase 1 or later).

If a Dockerfile becomes desirable in Phase 1+ (e.g. for a Bedrock
Lambda wrapper or a Reachy Pi deployment), it will:

1. Reuse the literal venv install command (`pip install --no-cache-dir -e
   '.[providers]'`) — no variation.
2. Include a CI check grepping the Dockerfile for the `[providers]`
   substring.
3. Be approved via a new ADR (ADR-ARCH-NNN-dockerfile-parity-install).

## Alternatives considered

- **Ship a Dockerfile in Phase 0.** Rejected. Adds SR-05 compliance
  burden for no Phase 0 use case. Violates Do-Not-Change.
- **Ship a Dockerfile with Phase 0 as a stub.** Rejected. Half-done
  artefacts invite drift; either it's canonical or it doesn't exist.
- **Nix / Poetry / other packaging.** Rejected. venv + `pip install -e
  '.[providers]'` matches specialist-agent and is the clean-machine
  walkthrough audience's most-portable baseline.

## Consequences

**Positive:**
- Phase 0 scope stays small. Weekend build target is achievable.
- No risk of SR-05 regression (there's no Dockerfile to drift).
- README quickstart is simpler and aligns with what judges would run
  to reproduce the tutor.

**Negative:**
- Phase 1 may need a Dockerfile for Bedrock or Reachy-side deployment.
  Accepted — add it with a new ADR when the need is real, not now.
- `specialist-agent` ships a Dockerfile; Study Tutor not shipping one
  may look inconsistent. Accepted — context differs; this is a
  skeleton+library for now, not a deployable service.

## References

- `docs/research/ideas/phase-0-scope.md §Do-Not-Change`
- LES1 §3 DKRX evidence pointer.
