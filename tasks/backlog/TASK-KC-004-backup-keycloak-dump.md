---
id: TASK-KC-004
title: "backup.sh — second pg_dump -d keycloak block; nightly backup fails if EITHER dump fails"
task_type: feature
parent_review: TASK-REV-KCA1
feature_id: FEAT-AUTH-001
wave: 2
implementation_mode: task-work
complexity: 4
dependencies: [TASK-KC-003]
consumer_context:
  - task: TASK-KC-003
    consumes: KEYCLOAK_DB
    framework: "pg_dump custom-format (-Fc) via docker exec"
    driver: "postgresql-client in study_tutor_postgres container"
    format_note: "dump target DB name is exactly `keycloak`; dump as the keycloak role (`pg_dump -U keycloak -d keycloak -Fc`) since study_tutor role has no grants into the keycloak DB (KC-D3 isolation)"
---

## Description

Extend the existing nightly backup
([deploy/postgres/backup.sh](../../../deploy/postgres/backup.sh)) so it protects
the **realm/user state** alongside learner state (design KC-D1: realm/user state
is durable and non-reindexable, same class as learner data). Consumer of the §4
KEYCLOAK_DB contract.

Add a **second** logical dump for the `keycloak` database, keeping the file's
proven pattern intact: atomic temp-then-rename, `PGDMP`-magic validity check,
shared `RETENTION_DAYS=14` pruning (ASSUM-006), append to `backup.log`.

**The load-bearing behaviour (negative-path AC):** the routine must exit
**non-zero if EITHER dump fails** — a failed `keycloak` dump must make the whole
nightly backup report failure, never be silently ignored (spec edge/negative
scenario). Refactor the single-dump body into a helper invoked once per DB
(`study_tutor`, `keycloak`) so both share the atomic/validity/failure logic and
neither can partially succeed unnoticed. The `keycloak` dump runs as the
`keycloak` role against the `keycloak` DB (the `study_tutor` role has no access
to it — KC-D3 isolation).

**Do not** change retention, the backup dir, or the study_tutor dump's existing
behaviour beyond factoring it through the shared helper; both dumps land in the
same backed-up `backups/` share (Hyper Backup covers `pgdata` implicitly too).

## Acceptance Criteria

- [ ] `backup.sh` produces a separate `keycloak_<stamp>.dump` (custom-format `-Fc`) in addition to the existing `study_tutor_<stamp>.dump`
- [ ] Both dumps use the atomic temp-then-rename + `PGDMP`-magic validity check; a partial/empty dump never masquerades as good
- [ ] The routine exits **non-zero** if the `study_tutor` dump **or** the `keycloak` dump fails (verify by simulating a failing keycloak dump → non-zero exit + logged failure)
- [ ] Retention prunes both dump families at the shared `RETENTION_DAYS=14`; `backup.log` records both
- [ ] The keycloak dump targets DB `keycloak` per the §4 KEYCLOAK_DB contract
- [ ] All modified files pass project-configured lint/format checks with zero errors

## BDD Scenarios Served

- "The nightly backup captures both the learner store and the realm state"
- "A failed keycloak dump makes the nightly backup report failure"
- "A nightly backup taken during realm writes is still consistent"

## Seam Tests

Prompt-output only — emit as `tests/seam/test_backup_keycloak_contract.py` if implemented.

```python
"""Seam test: verify the KEYCLOAK_DB dump contract in backup.sh."""
import pathlib
import re
import pytest


@pytest.mark.seam
@pytest.mark.integration_contract("KEYCLOAK_DB")
def test_backup_dumps_keycloak_and_fails_on_error():
    """Contract: backup.sh dumps the `keycloak` DB and exits non-zero if either
    dump fails. Producer: TASK-KC-003; consumer: this task.
    """
    text = pathlib.Path("deploy/postgres/backup.sh").read_text()
    assert re.search(r"pg_dump[^\n]*-d\s+keycloak", text), \
        "backup.sh must dump the keycloak database"
    assert "set -euo pipefail" in text, "must retain fail-fast shell settings"
    # both dump families are pruned by the shared retention glob
    assert "keycloak_" in text and "study_tutor_" in text
```

## References

- design [KC-D1](../../../docs/design/keycloak-auth-user-management-design.md) (second pg_dump -d keycloak line) · existing [backup.sh](../../../deploy/postgres/backup.sh) (atomic pattern, 14-day retention) · postgres runbook [Phase 4](../../../docs/runbooks/RUNBOOK-study-tutor-postgres-deploy.md) · ASSUM-006 (shared 14-day retention) · IMPLEMENTATION-GUIDE §4 (KEYCLOAK_DB consumer)
