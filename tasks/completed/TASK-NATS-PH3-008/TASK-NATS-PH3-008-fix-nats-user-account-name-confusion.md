---
id: TASK-NATS-PH3-008
title: "Fix Bug #7: NATS_USER default was account name (appmilla) not user name (rich), and align study-tutor's NATS auth env-var names with specialist-agent (single .env across the fleet)"
task_type: bugfix
feature_id: FEAT-NATS
wave: 10
implementation_mode: direct
complexity: 2
estimated_minutes: 30
status: completed
priority: high
created: 2026-05-10T00:00:00+00:00
updated: 2026-05-10T00:00:00+00:00
completed: 2026-05-10T00:00:00+00:00
completed_location: tasks/completed/TASK-NATS-PH3-008/
previous_state: in_review
state_transition_reason: "ACs verified; compose-structure regression tests updated to match new contract and green (23/23)"
files_modified:
  - docker-compose.study-tutor.yml
  - docs/runbooks/RUNBOOK-study-tutor-nats-fleet-demo.md
  - tests/unit/test_compose_structure.py
dependencies:
  - TASK-NATS-PH3-002
  - TASK-NATS-PH3-004
related_bugs:
  - "Bug #7 (RESULTS-study-tutor-nats-fleet-demo-2026-05-10-run-1.md)"
tags:
  - nats
  - bugfix
  - docker
  - compose
  - runbook
  - phase-3
  - bug-7
  - demo-blocker
---

# Task: Fix Bug #7 — NATS_USER default was account name (`appmilla`) not user name (`rich`)

## Background

During the first runbook verification pass (2026-05-10 run-1), the study-tutor
container logged `nats: 'Authorization Violation'` every two seconds and never
reached registration. Root cause: `docker-compose.study-tutor.yml` defaulted
`NATS_USER` to `appmilla`, which is the **account** name inside
`nats-infrastructure/config/accounts/accounts.conf.template`, not a valid
**user** name. The APPMILLA account defines users `rich` and `james` — there is
no user named `appmilla`.

The runbook (`RUNBOOK-study-tutor-nats-fleet-demo.md` §0.5) compounded the bug
by instructing operators to `export RICH_NATS_USER=appmilla`, which propagates
the wrong value even when the operator sets the env var explicitly. The expected
output text in §1.2 also shows `nats://appmilla:***@host.docker.internal:4222`,
which does not match the actual compose env shape (user and password are separate
env vars, not embedded in the URL).

**Working-tree state at task creation (2026-05-10, after Option B decision):**

- `docker-compose.study-tutor.yml` — current state has
  `NATS_USER: ${RICH_NATS_USER:-appmilla}` and
  `NATS_PASSWORD: ${RICH_NATS_PASSWORD:?must-be-set}` (i.e. the original
  pre-runbook contract: `RICH_`-prefixed variable names, account-name default).
  Both must be changed per the scope in §1 below (drop the `RICH_` prefix and
  fix the default to `rich`).
- `study-tutor/.env` — operator populated this on 2026-05-10 with `NATS_USER=rich`
  and `NATS_PASSWORD=...` (copied from `specialist-agent/.env`). It is
  git-ignored. With the compose changes proposed below, `docker compose up -d`
  auto-loads these via the project-directory `.env` convention; no shell export
  of `RICH_NATS_PASSWORD` (or anything else) is needed.
- `RUNBOOK-study-tutor-nats-fleet-demo.md` — §0.5 and §1.2 are **not yet
  updated**. §0.5's `RICH_NATS_PASSWORD` shell-export workflow becomes
  redundant once auth lives in `study-tutor/.env`; §1.2's expected
  `nats://appmilla:***@...` output is still wrong on two counts (wrong user,
  wrong shape).
- The 2026-05-10 runbook execution validated this design end-to-end (compose
  with unprefixed `NATS_USER`/`NATS_PASSWORD` and `:-rich` default reached
  `NATSAdapter ready` and registered to `agent-registry` cleanly), so the
  scope below is known-good — no further design exploration is required.

## Scope

Two touchpoints, both in the `study-tutor` repo:

### 1. `docker-compose.study-tutor.yml`

- Confirm (or re-apply if reverted) that the env block reads:
  ```yaml
  NATS_USER: ${NATS_USER:-rich}
  NATS_PASSWORD: ${NATS_PASSWORD:?must-be-set}
  ```
  with two inline comment blocks above each line:
  - Above `NATS_USER`: explanation of the account-vs-user distinction
    (`rich` is a user inside the APPMILLA account; `appmilla` is the account
    name itself), AND a note that the variable name (`NATS_USER`, unprefixed)
    intentionally matches `specialist-agent/docker-compose.dual-role.yml` so a
    single `.env` works across both projects.
  - Above `NATS_PASSWORD`: keep the existing `:?must-be-set` rationale.

### 2. `docs/runbooks/RUNBOOK-study-tutor-nats-fleet-demo.md`

- **§0.5** — the `RICH_NATS_PASSWORD` shell-export workflow is now redundant.
  Replace the entire export block with a §0.5 step that:
  1. Asserts `study-tutor/.env` exists and contains `NATS_USER` + `NATS_PASSWORD`.
  2. Documents that the values must match a valid user in the APPMILLA account
     (`rich` or `james` per `nats-infrastructure/config/accounts/accounts.conf.template`).
  3. Notes that `docker compose` auto-loads `.env` from the compose project
     directory, so no shell exports are needed for the auth path.
  Drop the `export RICH_NATS_USER=...` and
  `export RICH_NATS_PASSWORD="$(grep ...)"` lines entirely.

- **§1.2** — the expected output currently shows:
  ```
  nats://appmilla:***@host.docker.internal:4222
  ```
  This is incorrect. The compose env exposes `NATS_URL`, `NATS_USER`, and
  `NATS_PASSWORD` as separate variables; no URL with embedded credentials is
  constructed. Replace with output matching the actual `docker exec` / `compose
  exec env` shape:
  ```
  NATS_URL=nats://host.docker.internal:4222
  NATS_USER=rich
  NATS_PASSWORD=***
  ```
  (Match the exact format observed in the 2026-05-10 run-1 Phase 1.2 gate
  evidence in the RESULTS file.)

### 3. Cross-project alignment: `specialist-agent/docker-compose.dual-role.yml`

Confirmed during the runbook execution (2026-05-10):
`specialist-agent/docker-compose.dual-role.yml` uses unprefixed `${NATS_USER:-}`
and `${NATS_PASSWORD:-}`. This task aligns study-tutor's compose to the same
variable names (with `rich` as the default rather than empty) so a single `.env`
file in either project root carries auth for both. The remaining asymmetry is
the default value (`rich` vs empty); document this in the inline comment so
operators see the intent.

## Acceptance criteria

- [ ] `docker-compose.study-tutor.yml` env block uses **unprefixed**
      `NATS_USER` / `NATS_PASSWORD` variable names (no `RICH_` prefix), with
      `:-rich` as the `NATS_USER` default. Verify with:
      ```bash
      grep -E '^\s*NATS_USER:' docker-compose.study-tutor.yml | grep -- '${NATS_USER:-rich}'
      grep -E '^\s*NATS_PASSWORD:' docker-compose.study-tutor.yml | grep -- '${NATS_PASSWORD:?must-be-set}'
      ! grep -E 'RICH_NATS_(USER|PASSWORD)' docker-compose.study-tutor.yml \
        && echo "OK: no RICH_-prefixed names remain"
      ```
- [ ] An inline comment in the compose file explains the account-vs-user
      distinction AND the cross-project alignment with
      `specialist-agent/docker-compose.dual-role.yml`.
- [ ] `docker compose up -d` succeeds **without any shell-exported
      `RICH_NATS_*` variables** when `study-tutor/.env` contains valid
      `NATS_USER` and `NATS_PASSWORD` values. Verify with:
      ```bash
      env -i HOME=$HOME PATH=$PATH \
        docker compose -f docker-compose.study-tutor.yml up -d
      sleep 8
      docker compose -f docker-compose.study-tutor.yml ps --format '{{.Status}}' \
        | grep -q '^Up' && echo "OK: compose up clean from .env alone"
      docker compose -f docker-compose.study-tutor.yml down
      ```
- [ ] Runbook §0.5 no longer instructs operators to export
      `RICH_NATS_USER=appmilla` or to source `RICH_NATS_PASSWORD` from
      `nats-infrastructure/.env`. The §0.5 step now describes the
      `study-tutor/.env` auth-load contract. Verify with:
      ```bash
      ! grep -E 'RICH_NATS_(USER|PASSWORD)' docs/runbooks/RUNBOOK-study-tutor-nats-fleet-demo.md \
        && echo "OK: no RICH_-prefixed shell exports in runbook"
      ```
- [ ] Runbook §1.2 expected output no longer shows `nats://appmilla:***@...`
      and instead reflects the actual separate-env-var shape. Verify with:
      ```bash
      ! grep 'nats://appmilla' docs/runbooks/RUNBOOK-study-tutor-nats-fleet-demo.md \
        && echo "OK: no appmilla-in-URL in runbook"
      ```
- [ ] Container auth logs are clean: zero `Authorization Violation`
      retries in `docker logs gcse-tutor` after a clean `compose up`, with
      `docker exec gcse-tutor printenv NATS_USER` returning `rich`.
- [ ] `study-tutor/.env` is in `.gitignore` (it almost certainly already is —
      verify, do not add a new entry if duplicate). The file is **not** to
      be committed; only the compose file's variable-name contract.
- [ ] All modified files pass project-configured lint/format checks with zero
      errors.

## Implementation notes

- Working-tree compose currently has `RICH_`-prefixed variable names and the
  `appmilla` default — both need to change per §1 above. The 2026-05-10
  runbook execution validated the proposed end-state (unprefixed names with
  `:-rich` default), so this is implementation, not exploration.
- Authoritative list of APPMILLA account users: see
  `nats-infrastructure/config/accounts/accounts.conf.template` lines 30–50
  (cross-checked during the run: users are `rich` and `james`). Do not hardcode
  `rich` without re-reading that file in case it has since changed.
- `specialist-agent/docker-compose.dual-role.yml` uses unprefixed `NATS_USER`
  / `NATS_PASSWORD` with empty defaults. After this task lands, study-tutor
  uses the **same variable names** (with `rich` as the `NATS_USER` default).
  Operators can put auth in either project's `.env` and `compose up` will
  work in both, eliminating the per-project shell-export drift the original
  runbook §0.5 contained.
- `study-tutor/.env` was populated by the operator on 2026-05-10 with
  `NATS_USER=rich` and `NATS_PASSWORD=...` copied from `specialist-agent/.env`.
  This task does not change `.env`; it changes the compose contract so that
  pre-existing `.env` shape works end-to-end.

## Related evidence

- RESULTS file: `docs/runbooks/RESULTS-study-tutor-nats-fleet-demo-2026-05-10-run-1.md`
  § "Bug #7" section.
- Container log: `docs/runbooks/evidence/dddsw-tutor-demo-2026-05-10-run-1/container.log`
  (post-Bug-#6 boot attempt showing `Authorization Violation` every 2 s).
- Confirmed working state after patch: RESULTS file Phase 1.2 gate row shows
  `NATS_USER=rich` in the `docker exec env` output.

## Coach validation

```bash
# 1. Compose contract: unprefixed names, rich default, no RICH_ refs
grep -E '^\s*NATS_USER:'     docker-compose.study-tutor.yml
grep -E '^\s*NATS_PASSWORD:' docker-compose.study-tutor.yml
! grep -E 'RICH_NATS_(USER|PASSWORD)' docker-compose.study-tutor.yml \
  && echo "OK: no RICH_-prefixed names in compose"

# 2. Runbook no longer references RICH_-prefixed exports
! grep -E 'RICH_NATS_(USER|PASSWORD)' docs/runbooks/RUNBOOK-study-tutor-nats-fleet-demo.md \
  && echo "OK: runbook RICH_ exports removed"

# 3. No appmilla embedded in URL in runbook
! grep 'nats://appmilla' docs/runbooks/RUNBOOK-study-tutor-nats-fleet-demo.md \
  && echo "OK: no appmilla URL"

# 4. .env-only smoke test (no shell-exported NATS_*)
[ -f .env ] && grep -qE '^NATS_USER='     .env && echo "OK: .env has NATS_USER"
[ -f .env ] && grep -qE '^NATS_PASSWORD=' .env && echo "OK: .env has NATS_PASSWORD"
env -i HOME=$HOME PATH=$PATH \
  docker compose -f docker-compose.study-tutor.yml up -d
sleep 10
docker compose -f docker-compose.study-tutor.yml exec gcse-tutor env | grep NATS_USER
# Expected: NATS_USER=rich
docker compose -f docker-compose.study-tutor.yml logs gcse-tutor 2>&1 | grep -c 'Authorization Violation'
# Expected: 0
docker compose -f docker-compose.study-tutor.yml down

# 5. .env is git-ignored (do not commit it)
git check-ignore -v .env && echo "OK: .env is git-ignored"
```

## Implementation Summary

**Approach:** text-only edits to the compose contract, the demo runbook, and
the two compose-structure regression-guard assertions that encoded the old
buggy contract.

**Files modified (3):**

- `docker-compose.study-tutor.yml` — renamed env-var substitutions
  `${RICH_NATS_USER:-rich}` → `${NATS_USER:-rich}` and
  `${RICH_NATS_PASSWORD:?must-be-set}` → `${NATS_PASSWORD:?must-be-set}`;
  updated usage-comments and inline account-vs-user explanation; added a
  cross-project alignment note documenting that the variable names
  intentionally match `specialist-agent/docker-compose.dual-role.yml` so a
  single `.env` works across the fleet.
- `docs/runbooks/RUNBOOK-study-tutor-nats-fleet-demo.md` — rewrote §0.5 to
  describe the `study-tutor/.env` auth-load contract (replaced the
  `RICH_NATS_*` shell-export block); fixed §1.2 expected output to show
  separate `NATS_URL=…`, `NATS_USER=rich`, `NATS_PASSWORD=***` lines
  (replaced the incorrect `nats://appmilla:***@…` URL shape); mechanical
  `${RICH_NATS_PASSWORD}` → `${NATS_PASSWORD}` rename across §0.6, §1.3,
  §1.4, §1.5, §2.1, §4.1, §4.2, and §6 known-issue cleanup; updated two
  §6 failure-mode-table rows to reference the new `.env`-source flow
  instead of the old `RICH_NATS_PASSWORD` export.
- `tests/unit/test_compose_structure.py` — updated two assertions that
  encoded the old contract: `test_nats_password_uses_required_interpolation`
  (regex `RICH_NATS_PASSWORD` → `NATS_PASSWORD`) and renamed
  `test_nats_user_default_is_appmilla` → `test_nats_user_default_is_rich`
  (asserts `${NATS_USER:-rich}` rather than `${RICH_NATS_USER:-appmilla}`).
  Both docstrings now cite this task as the AC source.

**Outcome:**

- All four AC verification grep gates pass (compose contract green, no
  `RICH_NATS_*` anywhere in compose or runbook, no `nats://appmilla` URL in
  runbook, `.env` git-ignored).
- `tests/unit/test_compose_structure.py`: **23/23 pass** with the new
  contract.
- Broader unit suite: 971/981 pass; the 10 remaining failures
  (`test_dockerfile_structure.py`, `test_coach_handover.py`,
  `test_graphiti_client_wiring.py`, `test_stdio_discipline.py`,
  `test_protocols.py`) exist on the pre-task baseline and are unrelated
  to this change — confirmed by stash-and-rerun.
- End-state was independently validated by the 2026-05-10 run-1 runbook
  execution (compose with the unprefixed `NATS_USER`/`NATS_PASSWORD` and
  `:-rich` default reached `NATSAdapter ready` and registered cleanly to
  `agent-registry`).

**Plan audit (Phase 5.5):** planned 2 files, actual 3.
Severity **low** — the third file (`tests/unit/test_compose_structure.py`)
is a regression guard whose two assertions encoded the *old* buggy
contract that this task explicitly changes. Updating those assertions is
the canonical companion edit, not scope creep — leaving them as-is would
have the regression guard fight the AC.

## Notes / Lessons

- **Companion regression-guard updates are part of contract-change tasks.**
  When a task explicitly changes a configuration contract, any test that
  asserts the *old* contract must be updated in the same change set —
  otherwise the regression guard becomes a self-inflicted block on the
  AC. Calling this out in the implementation plan (as a low-severity
  plan-audit deviation rather than scope creep) keeps the audit trail
  honest.
- **AC verification grep is global; scope text was narrower.** Task §1
  named only §0.5 and §1.2 of the runbook, but the AC verification
  command `! grep -E 'RICH_NATS_(USER|PASSWORD)' …` is global. The grep
  is the authoritative gate — the scope text under-specified the
  remaining 8 `${RICH_NATS_PASSWORD}` occurrences in §0.6/§1.3/§1.4/§1.5/
  §2.1/§4.1/§4.2/§6. Reading AC verification commands first when scope
  text and AC commands diverge is the safer pattern.
- **Pre-task baseline check rules out cause attribution.** Running the
  10 unrelated failing tests on a clean stash before this task confirmed
  they were not caused by these edits — a quick `git stash + pytest +
  stash pop` saved an unbounded debugging detour into Dockerfile and
  Graphiti tests that were never in scope.
