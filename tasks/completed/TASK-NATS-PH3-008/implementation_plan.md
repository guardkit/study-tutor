# Implementation Plan — TASK-NATS-PH3-008

## Summary

Fix Bug #7: align study-tutor's NATS auth env-var names with specialist-agent
(unprefixed `NATS_USER` / `NATS_PASSWORD`), correct the `NATS_USER` default
from the account name `appmilla` to the user name `rich`, and update the
runbook to match. Single `.env` file works across both projects after this.

## Files modified (2)

1. `docker-compose.study-tutor.yml` — rename env-var substitutions, update inline comments
2. `docs/runbooks/RUNBOOK-study-tutor-nats-fleet-demo.md` — rewrite §0.5, fix §1.2 expected output, global rename of `${RICH_NATS_PASSWORD}` → `${NATS_PASSWORD}` in 8 standalone `nats` CLI invocations, plus 2 failure-mode-table row updates

## Dependencies

None (text-only edits).

## Estimated effort

- Duration: 30 minutes
- LOC: ~60 lines changed (≈30 net additions, ≈30 deletions)
- Complexity: 2/10

## Risks

- 🟢 LOW — Text-only edits to compose YAML and Markdown. No code paths touched.
- 🟢 LOW — Runbook execution on 2026-05-10 (run-1) validated the proposed end
  state end-to-end (compose with unprefixed `NATS_USER` / `NATS_PASSWORD` and
  `:-rich` default reached `NATSAdapter ready` and registered cleanly).

## Test strategy

Verification is via the acceptance-criterion grep commands embedded in the
task file. No code tests added (no code changed). The compose-structure
regression guard (`tests/unit/test_compose_structure.py`) is asserted to
remain green.

Acceptance-criterion verification:

```bash
# Compose contract
grep -E '^\s*NATS_USER:'     docker-compose.study-tutor.yml | grep -- '${NATS_USER:-rich}'
grep -E '^\s*NATS_PASSWORD:' docker-compose.study-tutor.yml | grep -- '${NATS_PASSWORD:?must-be-set}'
! grep -E 'RICH_NATS_(USER|PASSWORD)' docker-compose.study-tutor.yml

# Runbook
! grep -E 'RICH_NATS_(USER|PASSWORD)' docs/runbooks/RUNBOOK-study-tutor-nats-fleet-demo.md
! grep 'nats://appmilla' docs/runbooks/RUNBOOK-study-tutor-nats-fleet-demo.md
```

## Implementation phases

1. Edit `docker-compose.study-tutor.yml` (5 minutes)
2. Edit runbook §0.5 / §1.2 (10 minutes)
3. Global rename `${RICH_NATS_PASSWORD}` → `${NATS_PASSWORD}` in runbook (5 minutes)
4. Update failure-mode-table rows (5 minutes)
5. Run AC verification grep commands + compose-structure regression test (5 minutes)
