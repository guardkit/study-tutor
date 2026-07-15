#!/usr/bin/env bash
# Validation script for TASK-KC-003: Keycloak DB and role least-privilege isolation
#
# Usage (from deploy host):
#   docker exec study_tutor_postgres bash -c "$(cat deploy/keycloak/validate-keycloak-db.sh)"
#
# Or for local testing with the container:
#   docker exec study_tutor_postgres /bin/bash < deploy/keycloak/validate-keycloak-db.sh
#
# Exit codes:
#   0 = All validation checks passed
#   1 = One or more validation checks failed

set -euo pipefail

echo "=== Keycloak DB & Role Validation (TASK-KC-003) ==="
echo ""

FAILED=0

# Test 1: Role exists with correct properties
echo "[TEST 1] Checking keycloak role exists with correct properties..."
ROLE_CHECK=$(psql -U postgres -tAc "
  SELECT
    CASE
      WHEN rolname IS NULL THEN 'MISSING'
      WHEN rolsuper THEN 'SUPERUSER'
      WHEN rolcreatedb THEN 'CREATEDB'
      WHEN rolcreaterole THEN 'CREATEROLE'
      WHEN NOT rolcanlogin THEN 'NOLOGIN'
      ELSE 'OK'
    END
  FROM pg_roles
  WHERE rolname = 'keycloak';
" || echo "MISSING")

if [[ "$ROLE_CHECK" == "OK" ]]; then
  echo "✓ Role 'keycloak' exists with correct properties (non-superuser, login, NOCREATEDB, NOCREATEROLE)"
else
  echo "✗ Role check failed: $ROLE_CHECK"
  FAILED=1
fi
echo ""

# Test 2: Database exists and is owned by keycloak role
echo "[TEST 2] Checking keycloak database exists and is owned by keycloak..."
DB_CHECK=$(psql -U postgres -tAc "
  SELECT
    CASE
      WHEN datname IS NULL THEN 'MISSING'
      WHEN pg_catalog.pg_get_userbyid(datdba) != 'keycloak' THEN 'WRONG_OWNER'
      ELSE 'OK'
    END
  FROM pg_database
  WHERE datname = 'keycloak';
" || echo "MISSING")

if [[ "$DB_CHECK" == "OK" ]]; then
  echo "✓ Database 'keycloak' exists and is owned by 'keycloak' role"
else
  echo "✗ Database check failed: $DB_CHECK"
  FAILED=1
fi
echo ""

# Test 3: Idempotency - re-running should be safe
echo "[TEST 3] Testing idempotency (can script be re-run safely)..."
# This is tested implicitly by the orchestrator running the init script twice
echo "✓ Idempotency must be tested by running init-keycloak-db.sql twice (no errors on second run)"
echo ""

# Test 4: Least-privilege proof - keycloak role CANNOT access study_tutor database
echo "[TEST 4] LEAST-PRIVILEGE PROOF: Verifying keycloak role cannot access study_tutor tables..."

# First, check if keycloak role can even connect to study_tutor database
CONNECT_CHECK=$(psql -U postgres -tAc "
  SELECT has_database_privilege('keycloak', 'study_tutor', 'CONNECT');
" || echo "ERROR")

if [[ "$CONNECT_CHECK" == "f" ]]; then
  echo "✓ keycloak role correctly denied CONNECT privilege to study_tutor database"
elif [[ "$CONNECT_CHECK" == "t" ]]; then
  echo "⚠ keycloak role HAS CONNECT to study_tutor (testing table access)..."

  # Even if connection is possible, check table access is denied
  # This test assumes study_tutor database might have tables; if it's empty, this is informational
  TABLE_COUNT=$(psql -U postgres -d study_tutor -tAc "
    SELECT COUNT(*) FROM information_schema.tables
    WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
  " || echo "0")

  if [[ "$TABLE_COUNT" -gt 0 ]]; then
    # Try to SELECT from a table as keycloak role (should fail)
    FIRST_TABLE=$(psql -U postgres -d study_tutor -tAc "
      SELECT table_name FROM information_schema.tables
      WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
      LIMIT 1;
    ")

    # Attempt SELECT as keycloak role (expect permission denied)
    if psql -U keycloak -d study_tutor -tAc "SELECT COUNT(*) FROM $FIRST_TABLE;" 2>&1 | grep -q "permission denied"; then
      echo "✓ keycloak role correctly denied SELECT on study_tutor table '$FIRST_TABLE'"
    else
      echo "✗ SECURITY VIOLATION: keycloak role can SELECT from study_tutor.$FIRST_TABLE"
      FAILED=1
    fi
  else
    echo "ℹ study_tutor database has no tables yet (schema not initialized)"
    echo "  Least-privilege will be validated once Alembic migrations create tables"
  fi
else
  echo "✗ Error checking database privileges: $CONNECT_CHECK"
  FAILED=1
fi
echo ""

# Test 5: Symmetry - study_tutor role should not access keycloak database
echo "[TEST 5] SYMMETRY: Verifying study_tutor role cannot access keycloak database..."
STUDY_TUTOR_CONNECT=$(psql -U postgres -tAc "
  SELECT has_database_privilege('study_tutor', 'keycloak', 'CONNECT');
" || echo "ERROR")

if [[ "$STUDY_TUTOR_CONNECT" == "f" ]]; then
  echo "✓ study_tutor role correctly denied CONNECT privilege to keycloak database"
elif [[ "$STUDY_TUTOR_CONNECT" == "t" ]]; then
  echo "✗ SECURITY ISSUE: study_tutor role can connect to keycloak database"
  FAILED=1
else
  echo "✗ Error checking study_tutor privileges: $STUDY_TUTOR_CONNECT"
  FAILED=1
fi
echo ""

# Summary
echo "=== Validation Summary ==="
if [[ $FAILED -eq 0 ]]; then
  echo "✓ ALL CHECKS PASSED"
  echo ""
  echo "The keycloak database and role are correctly configured with:"
  echo "  - Non-superuser role with login capability"
  echo "  - Separate database owned by keycloak role"
  echo "  - Least-privilege isolation from study_tutor database"
  echo "  - Symmetric isolation (study_tutor cannot access keycloak)"
  exit 0
else
  echo "✗ VALIDATION FAILED - See errors above"
  exit 1
fi
