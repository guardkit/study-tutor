-- ============================================================================
-- Keycloak Database and Role Bootstrap (TASK-KC-003)
-- ============================================================================
--
-- PURPOSE:
--   Creates the 'keycloak' database and role inside the existing
--   'study_tutor_postgres' container on port 5434 with least-privilege
--   isolation from the 'study_tutor' learner database.
--
-- DESIGN:
--   - Co-located DB (KC-D1): Both databases in one Postgres 16 cluster
--   - D4 rule: Separates PROJECTS, not a project's own services
--   - Least-privilege: keycloak role CANNOT read study_tutor tables
--   - Idempotent: Safe to re-run (checks pg_roles/pg_database)
--
-- USAGE:
--   From deploy host (with KC_DB_PASSWORD set in environment):
--
--     export KC_DB_PASSWORD="your-secure-password-here"
--     docker exec -i study_tutor_postgres psql -U postgres -v kc_password="$KC_DB_PASSWORD" < deploy/keycloak/init-keycloak-db.sql
--
--   Or via docker-compose exec (if in deploy/postgres directory):
--
--     docker-compose exec -T postgres psql -U postgres -v kc_password="$KC_DB_PASSWORD" < ../keycloak/init-keycloak-db.sql
--
-- VALIDATION:
--   Run the validation script after applying this SQL:
--
--     docker exec study_tutor_postgres bash < deploy/keycloak/validate-keycloak-db.sh
--
-- SECURITY:
--   - Password MUST be provided via psql variable (-v kc_password="...")
--   - NEVER commit the password to version control
--   - Generate with: openssl rand -hex 24
--
-- REFERENCES:
--   - TASK-KC-003 acceptance criteria
--   - docs/design/keycloak-auth-user-management-design.md (KC-D1)
--   - ADR-ARCH-028 D1 (Keycloak IDP placement)
--   - docs/runbooks/RUNBOOK-study-tutor-postgres-deploy.md (DB bootstrap pattern)
--
-- ============================================================================

\set ON_ERROR_STOP on

-- ============================================================================
-- 1. CREATE ROLE 'keycloak' (IDEMPOTENT)
-- ============================================================================
--
-- Creates a dedicated, non-superuser login role with its own password.
-- Properties:
--   - LOGIN: Can connect to databases it has access to
--   - NOSUPERUSER: Cannot bypass security checks
--   - NOCREATEDB: Cannot create new databases
--   - NOCREATEROLE: Cannot create or modify roles
--
-- Idempotency: Checks pg_roles before creating
-- Password: Provided via psql variable :kc_password (substituted by psql client)
-- ============================================================================

-- Check if role exists and store result
SELECT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'keycloak') AS role_exists \gset

-- Conditionally create role using psql's \if
\if :role_exists
  \echo 'Role keycloak already exists (idempotent - skipping creation)'
\else
  \echo 'Creating role: keycloak'
  CREATE ROLE keycloak LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD :'kc_password';
  \echo 'Role keycloak created successfully'
\endif

-- ============================================================================
-- 2. CREATE DATABASE 'keycloak' (IDEMPOTENT)
-- ============================================================================
--
-- Creates a separate database owned by the keycloak role.
-- Keycloak will create its own schema/tables on first optimized start.
--
-- Idempotency: Checks pg_database before creating
-- ============================================================================

-- Check if database exists and store result
SELECT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'keycloak') AS db_exists \gset

-- Conditionally create database using psql's \if
\if :db_exists
  \echo 'Database keycloak already exists (idempotent - skipping creation)'
\else
  \echo 'Creating database: keycloak'
  CREATE DATABASE keycloak OWNER keycloak;
  \echo 'Database keycloak created successfully'
\endif

-- ============================================================================
-- 3. LEAST-PRIVILEGE ISOLATION
-- ============================================================================
--
-- Ensures keycloak role CANNOT access study_tutor database and vice versa.
--
-- Security Model:
--   - keycloak role: Can ONLY connect to 'keycloak' database
--   - study_tutor role: Can ONLY connect to 'study_tutor' database
--   - No cross-database access or grants
--
-- This is the LOAD-BEARING security acceptance criterion.
-- ============================================================================

\echo ''
\echo 'Configuring least-privilege isolation...'

-- 3a. Revoke any default PUBLIC privileges on both databases
REVOKE ALL ON DATABASE study_tutor FROM PUBLIC;
REVOKE ALL ON DATABASE keycloak FROM PUBLIC;

-- 3b. Explicitly grant CONNECT only to the owning roles
GRANT CONNECT ON DATABASE study_tutor TO study_tutor;
GRANT CONNECT ON DATABASE keycloak TO keycloak;

-- 3c. Ensure keycloak role has NO privileges on study_tutor database
REVOKE ALL ON DATABASE study_tutor FROM keycloak;

-- 3d. Ensure study_tutor role has NO privileges on keycloak database
REVOKE ALL ON DATABASE keycloak FROM study_tutor;

\echo 'Least-privilege isolation configured'

-- ============================================================================
-- 4. VERIFICATION QUERIES (FOR RUNBOOK/GATE)
-- ============================================================================
--
-- These queries prove the least-privilege isolation is working.
-- Run after applying this SQL to verify security posture.
-- ============================================================================

\echo ''
\echo '=== Verification: Role Properties ==='
SELECT
  rolname,
  rolsuper AS is_superuser,
  rolcreatedb AS can_create_db,
  rolcreaterole AS can_create_role,
  rolcanlogin AS can_login
FROM pg_roles
WHERE rolname IN ('keycloak', 'study_tutor')
ORDER BY rolname;

-- Expected output:
--  rolname     | is_superuser | can_create_db | can_create_role | can_login
-- -------------+--------------+---------------+-----------------+-----------
--  keycloak    | f            | f             | f               | t
--  study_tutor | f            | f             | f               | t

\echo ''
\echo '=== Verification: Database Ownership ==='
SELECT
  datname,
  pg_catalog.pg_get_userbyid(datdba) AS owner
FROM pg_database
WHERE datname IN ('keycloak', 'study_tutor')
ORDER BY datname;

-- Expected output:
--  datname     | owner
-- -------------+-------------
--  keycloak    | keycloak
--  study_tutor | study_tutor

\echo ''
\echo '=== Verification: Database Privileges (LEAST-PRIVILEGE PROOF) ==='
SELECT
  rolname,
  datname,
  has_database_privilege(rolname, datname, 'CONNECT') AS can_connect
FROM pg_roles, pg_database
WHERE rolname IN ('keycloak', 'study_tutor')
  AND datname IN ('keycloak', 'study_tutor')
ORDER BY rolname, datname;

-- Expected output (CRITICAL - this proves isolation):
--  rolname     | datname     | can_connect
-- -------------+-------------+-------------
--  keycloak    | keycloak    | t           ← OK: keycloak can access its own DB
--  keycloak    | study_tutor | f           ← REQUIRED: keycloak CANNOT access study_tutor
--  study_tutor | keycloak    | f           ← REQUIRED: study_tutor CANNOT access keycloak
--  study_tutor | study_tutor | t           ← OK: study_tutor can access its own DB

-- ============================================================================
-- 5. NEGATIVE PROOF (RUNBOOK GATE)
-- ============================================================================
--
-- The following command MUST fail with "permission denied":
--
--   docker exec study_tutor_postgres psql -U keycloak -d study_tutor -c '\dt'
--
-- Expected error:
--   FATAL: permission denied for database "study_tutor"
--   DETAIL: User does not have CONNECT privilege.
--
-- This proves the keycloak role cannot read learner tables.
-- ============================================================================

\echo ''
\echo '=== Bootstrap Complete ==='
\echo ''
\echo 'Created:'
\echo '  - Role: keycloak (login, non-superuser, NOCREATEDB, NOCREATEROLE)'
\echo '  - Database: keycloak (owner: keycloak)'
\echo ''
\echo 'Security:'
\echo '  - keycloak role can ONLY access keycloak database'
\echo '  - study_tutor role can ONLY access study_tutor database'
\echo '  - Cross-database access is DENIED'
\echo ''
\echo 'Next Steps:'
\echo '  1. Run validation: docker exec study_tutor_postgres bash < deploy/keycloak/validate-keycloak-db.sh'
\echo '  2. Configure Keycloak to use this database (TASK-KC-001)'
\echo '  3. Start Keycloak container (will create its own schema on first run)'
\echo ''
\echo 'Negative Proof (MUST fail):'
\echo '  docker exec study_tutor_postgres psql -U keycloak -d study_tutor -c "\\dt"'
\echo '  Expected: FATAL: permission denied for database "study_tutor"'
\echo ''
