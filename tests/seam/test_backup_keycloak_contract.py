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
