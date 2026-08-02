"""Test suite for TASK-KC-003: Keycloak DB and role bootstrap.

Validates that deploy/keycloak/init-keycloak-db.sql:
- Creates the keycloak role with correct properties (non-superuser, login, etc.)
- Creates the keycloak database owned by the keycloak role
- Is idempotent (can be re-run without errors)
- Takes password from psql variable (never hard-coded)
- Enforces least-privilege isolation (keycloak cannot access study_tutor tables)
- Uses exact names per §4 KEYCLOAK_DB contract

This test suite requires Docker to be available for spinning up test containers.
"""

from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def postgres_container():
    """Start a PostgreSQL container for testing.

    Creates a test container on port 5435 (non-standard to avoid conflicts).
    The container persists for the entire test module to allow multiple tests.
    """
    if shutil.which("docker") is None:
        pytest.skip("docker unavailable — ephemeral Postgres required")
    container_name = "guardkit-test-pg-kc003"

    # Cleanup any existing container
    subprocess.run(
        ["docker", "rm", "-f", container_name],
        capture_output=True,
        check=False
    )

    # Start PostgreSQL container
    subprocess.run(
        [
            "docker", "run", "-d",
            "--name", container_name,
            "-e", "POSTGRES_PASSWORD=test",
            "-p", "5435:5432",
            "postgres:16-alpine"
        ],
        check=True,
        capture_output=True
    )

    # Wait for PostgreSQL to be ready
    max_attempts = 30
    for attempt in range(max_attempts):
        result = subprocess.run(
            ["docker", "exec", container_name, "pg_isready"],
            capture_output=True
        )
        if result.returncode == 0:
            break
        time.sleep(1)
    else:
        raise RuntimeError(f"PostgreSQL not ready after {max_attempts} seconds")

    # Create study_tutor database and role (prerequisite for keycloak isolation tests)
    subprocess.run(
        [
            "docker", "exec", container_name,
            "psql", "-U", "postgres", "-c",
            "CREATE ROLE study_tutor LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD 'test';"
        ],
        check=True,
        capture_output=True
    )

    subprocess.run(
        [
            "docker", "exec", container_name,
            "psql", "-U", "postgres", "-c",
            "CREATE DATABASE study_tutor OWNER study_tutor;"
        ],
        check=True,
        capture_output=True
    )

    yield container_name

    # Cleanup after all tests
    subprocess.run(
        ["docker", "rm", "-f", container_name],
        capture_output=True,
        check=False
    )


@pytest.fixture
def sql_file() -> Path:
    """Path to the init-keycloak-db.sql file."""
    return Path(__file__).parents[3] / "deploy" / "keycloak" / "init-keycloak-db.sql"


def run_psql(container: str, command: str, user: str = "postgres", database: str = "postgres") -> subprocess.CompletedProcess:
    """Execute a psql command in the container.

    Args:
        container: Docker container name
        command: SQL command or query to execute
        user: PostgreSQL user to connect as
        database: Database to connect to

    Returns:
        CompletedProcess with stdout/stderr
    """
    return subprocess.run(
        [
            "docker", "exec", container,
            "psql", "-U", user, "-d", database, "-tAc", command
        ],
        capture_output=True,
        text=True
    )


def apply_init_sql(container: str, sql_file: Path, password: str = "test_kc_password") -> subprocess.CompletedProcess:
    """Apply the init-keycloak-db.sql script to the container.

    Args:
        container: Docker container name
        sql_file: Path to the SQL file
        password: Password for the keycloak role

    Returns:
        CompletedProcess with stdout/stderr
    """
    sql_content = sql_file.read_text()

    return subprocess.run(
        [
            "docker", "exec", "-i", container,
            "psql", "-U", "postgres",
            "-v", f"kc_password={password}"
        ],
        input=sql_content,
        capture_output=True,
        text=True
    )


class TestKeycloakRoleCreation:
    """AC-001: Role and database creation with correct properties."""

    def test_apply_init_sql_succeeds(self, postgres_container: str, sql_file: Path) -> None:
        """The init-keycloak-db.sql script applies without errors."""
        result = apply_init_sql(postgres_container, sql_file)

        assert result.returncode == 0, (
            f"SQL script failed to apply:\n"
            f"STDOUT: {result.stdout}\n"
            f"STDERR: {result.stderr}"
        )
        assert "Bootstrap Complete" in result.stdout or "keycloak created" in result.stdout.lower()

    def test_keycloak_role_exists(self, postgres_container: str) -> None:
        """Keycloak role exists in pg_roles."""
        result = run_psql(
            postgres_container,
            "SELECT COUNT(*) FROM pg_roles WHERE rolname = 'keycloak';"
        )

        assert result.returncode == 0
        assert result.stdout.strip() == "1", "keycloak role does not exist"

    def test_keycloak_role_is_not_superuser(self, postgres_container: str) -> None:
        """Keycloak role is NOT a superuser (NOSUPERUSER)."""
        result = run_psql(
            postgres_container,
            "SELECT rolsuper FROM pg_roles WHERE rolname = 'keycloak';"
        )

        assert result.returncode == 0
        assert result.stdout.strip() == "f", "keycloak role should not be superuser"

    def test_keycloak_role_cannot_create_databases(self, postgres_container: str) -> None:
        """Keycloak role cannot create databases (NOCREATEDB)."""
        result = run_psql(
            postgres_container,
            "SELECT rolcreatedb FROM pg_roles WHERE rolname = 'keycloak';"
        )

        assert result.returncode == 0
        assert result.stdout.strip() == "f", "keycloak role should not be able to create databases"

    def test_keycloak_role_cannot_create_roles(self, postgres_container: str) -> None:
        """Keycloak role cannot create roles (NOCREATEROLE)."""
        result = run_psql(
            postgres_container,
            "SELECT rolcreaterole FROM pg_roles WHERE rolname = 'keycloak';"
        )

        assert result.returncode == 0
        assert result.stdout.strip() == "f", "keycloak role should not be able to create roles"

    def test_keycloak_role_can_login(self, postgres_container: str) -> None:
        """Keycloak role has LOGIN capability."""
        result = run_psql(
            postgres_container,
            "SELECT rolcanlogin FROM pg_roles WHERE rolname = 'keycloak';"
        )

        assert result.returncode == 0
        assert result.stdout.strip() == "t", "keycloak role should be able to login"

    def test_keycloak_database_exists(self, postgres_container: str) -> None:
        """Keycloak database exists."""
        result = run_psql(
            postgres_container,
            "SELECT COUNT(*) FROM pg_database WHERE datname = 'keycloak';"
        )

        assert result.returncode == 0
        assert result.stdout.strip() == "1", "keycloak database does not exist"

    def test_keycloak_database_owned_by_keycloak_role(self, postgres_container: str) -> None:
        """Keycloak database is owned by the keycloak role."""
        result = run_psql(
            postgres_container,
            "SELECT pg_catalog.pg_get_userbyid(datdba) FROM pg_database WHERE datname = 'keycloak';"
        )

        assert result.returncode == 0
        assert result.stdout.strip() == "keycloak", "keycloak database should be owned by keycloak role"


class TestIdempotency:
    """AC-002: Creation is idempotent (can be re-run without errors)."""

    def test_second_application_succeeds(self, postgres_container: str, sql_file: Path) -> None:
        """Re-running the SQL script succeeds without errors."""
        # First application already happened in TestKeycloakRoleCreation
        # Apply a second time
        result = apply_init_sql(postgres_container, sql_file)

        assert result.returncode == 0, (
            f"Second SQL application failed:\n"
            f"STDOUT: {result.stdout}\n"
            f"STDERR: {result.stderr}"
        )

    def test_second_application_skips_creation(self, postgres_container: str, sql_file: Path) -> None:
        """Second application recognizes existing objects and skips creation."""
        result = apply_init_sql(postgres_container, sql_file)

        assert result.returncode == 0
        # Check for idempotent messages in output
        output_lower = result.stdout.lower()
        assert ("already exists" in output_lower or "idempotent" in output_lower), (
            "Expected idempotent skip message in output"
        )


class TestPasswordFromVariable:
    """AC-003: Password taken from psql variable/env, never hard-coded."""

    def test_sql_file_contains_no_hardcoded_passwords(self, sql_file: Path) -> None:
        """SQL file does not contain hard-coded password strings."""
        content = sql_file.read_text()

        # Password should be referenced as :kc_password (psql variable)
        assert ":kc_password" in content, "SQL should reference :kc_password variable"

        # Should not contain common password patterns
        forbidden_patterns = [
            "PASSWORD 'password'",
            "PASSWORD 'test'",
            "PASSWORD '123",
            'PASSWORD "',
        ]

        for pattern in forbidden_patterns:
            assert pattern not in content, f"SQL contains forbidden pattern: {pattern}"

    def test_role_has_password_set(self, postgres_container: str) -> None:
        """Keycloak role has a password configured (can authenticate)."""
        result = run_psql(
            postgres_container,
            "SELECT rolpassword IS NOT NULL FROM pg_authid WHERE rolname = 'keycloak';"
        )

        assert result.returncode == 0
        assert result.stdout.strip() == "t", "keycloak role should have a password set"


class TestLeastPrivilegeIsolation:
    """AC-004: Least-privilege proof - keycloak cannot access study_tutor tables."""

    def test_keycloak_cannot_connect_to_study_tutor_database(self, postgres_container: str) -> None:
        """Keycloak role is denied CONNECT privilege to study_tutor database."""
        result = run_psql(
            postgres_container,
            "SELECT has_database_privilege('keycloak', 'study_tutor', 'CONNECT');"
        )

        assert result.returncode == 0
        assert result.stdout.strip() == "f", (
            "SECURITY VIOLATION: keycloak role can connect to study_tutor database"
        )

    def test_study_tutor_cannot_connect_to_keycloak_database(self, postgres_container: str) -> None:
        """Study_tutor role is denied CONNECT privilege to keycloak database (symmetry)."""
        result = run_psql(
            postgres_container,
            "SELECT has_database_privilege('study_tutor', 'keycloak', 'CONNECT');"
        )

        assert result.returncode == 0
        assert result.stdout.strip() == "f", (
            "SECURITY VIOLATION: study_tutor role can connect to keycloak database"
        )

    def test_keycloak_can_connect_to_own_database(self, postgres_container: str) -> None:
        """Keycloak role CAN connect to its own database."""
        result = run_psql(
            postgres_container,
            "SELECT has_database_privilege('keycloak', 'keycloak', 'CONNECT');"
        )

        assert result.returncode == 0
        assert result.stdout.strip() == "t", "keycloak role should be able to connect to keycloak database"

    def test_study_tutor_can_connect_to_own_database(self, postgres_container: str) -> None:
        """Study_tutor role CAN connect to its own database."""
        result = run_psql(
            postgres_container,
            "SELECT has_database_privilege('study_tutor', 'study_tutor', 'CONNECT');"
        )

        assert result.returncode == 0
        assert result.stdout.strip() == "t", "study_tutor role should be able to connect to study_tutor database"

    def test_negative_proof_keycloak_connection_fails(self, postgres_container: str) -> None:
        """Attempting to connect as keycloak to study_tutor database fails."""
        # Try to connect as keycloak role to study_tutor database
        result = subprocess.run(
            [
                "docker", "exec", postgres_container,
                "psql", "-U", "keycloak", "-d", "study_tutor", "-c", "\\dt"
            ],
            capture_output=True,
            text=True
        )

        # Connection should fail
        assert result.returncode != 0, "keycloak should not be able to connect to study_tutor"
        assert "permission denied" in result.stderr.lower() or "FATAL" in result.stderr, (
            f"Expected permission denied error, got: {result.stderr}"
        )


class TestNamingContract:
    """AC-005: Names match §4 KEYCLOAK_DB contract exactly."""

    def test_role_name_is_keycloak(self, postgres_container: str) -> None:
        """Role name is exactly 'keycloak'."""
        result = run_psql(
            postgres_container,
            "SELECT rolname FROM pg_roles WHERE rolname = 'keycloak';"
        )

        assert result.returncode == 0
        assert result.stdout.strip() == "keycloak", "Role name must be exactly 'keycloak'"

    def test_database_name_is_keycloak(self, postgres_container: str) -> None:
        """Database name is exactly 'keycloak'."""
        result = run_psql(
            postgres_container,
            "SELECT datname FROM pg_database WHERE datname = 'keycloak';"
        )

        assert result.returncode == 0
        assert result.stdout.strip() == "keycloak", "Database name must be exactly 'keycloak'"


class TestSQLFormat:
    """AC-006: SQL file passes format checks."""

    def test_sql_file_exists(self, sql_file: Path) -> None:
        """The init-keycloak-db.sql file exists."""
        assert sql_file.exists(), f"SQL file not found at {sql_file}"

    def test_sql_file_is_readable(self, sql_file: Path) -> None:
        """SQL file can be read and is not empty."""
        content = sql_file.read_text()
        assert len(content) > 0, "SQL file is empty"
        assert len(content) > 100, "SQL file seems too short to be complete"

    def test_sql_file_has_documentation(self, sql_file: Path) -> None:
        """SQL file includes header documentation."""
        content = sql_file.read_text()

        # Should have header comments
        assert "TASK-KC-003" in content, "SQL should reference TASK-KC-003"
        assert "PURPOSE" in content or "purpose" in content.lower()
        assert "USAGE" in content or "usage" in content.lower()

    def test_sql_file_documents_least_privilege_proof(self, sql_file: Path) -> None:
        """SQL file documents the least-privilege proof."""
        content = sql_file.read_text()

        # Should document how to verify least-privilege isolation
        assert "permission denied" in content.lower() or "negative proof" in content.lower()
        assert "study_tutor" in content, "Should reference study_tutor database in proof"


class TestValidationScript:
    """Bonus: Validate the companion validation script."""

    def test_validation_script_exists(self) -> None:
        """The validate-keycloak-db.sh script exists."""
        script_path = Path(__file__).parents[3] / "deploy" / "keycloak" / "validate-keycloak-db.sh"
        assert script_path.exists(), f"Validation script not found at {script_path}"

    def test_validation_script_is_executable(self) -> None:
        """The validation script has executable permissions."""
        script_path = Path(__file__).parents[3] / "deploy" / "keycloak" / "validate-keycloak-db.sh"
        assert script_path.stat().st_mode & 0o111, "Validation script should be executable"

    def test_validation_script_runs_successfully(self, postgres_container: str) -> None:
        """The validation script runs and passes all checks."""
        script_path = Path(__file__).parents[3] / "deploy" / "keycloak" / "validate-keycloak-db.sh"
        script_content = script_path.read_text()

        result = subprocess.run(
            ["docker", "exec", "-i", postgres_container, "bash"],
            input=script_content,
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, (
            f"Validation script failed:\n"
            f"STDOUT: {result.stdout}\n"
            f"STDERR: {result.stderr}"
        )
        # Check for success indicators
        assert ("ALL CHECKS PASSED" in result.stdout or
                "✓" in result.stdout or
                result.returncode == 0), "Validation script should pass all checks"
