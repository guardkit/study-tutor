"""
Tests for Keycloak realm configuration (TASK-KC-002).

Validates the study-tutor-realm.json realm-as-code configuration:
- Realm structure with pinned IDs and https-only SSL
- Public clients (study-tutor-app with PKCE, reachy-robot with device grant)
- Realm roles (student, parent)
- student_id protocol mapper
- Absence of users, secrets, and live-suite client (prod-safe invariants)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest


# Path to the realm configuration file
REALM_CONFIG_PATH = Path(__file__).parent.parent.parent / "deploy" / "keycloak" / "realm" / "study-tutor-realm.json"


@pytest.fixture
def realm_config() -> dict[str, Any]:
    """Load and parse the realm configuration JSON."""
    if not REALM_CONFIG_PATH.exists():
        pytest.fail(f"Realm config file not found: {REALM_CONFIG_PATH}")

    with open(REALM_CONFIG_PATH, encoding="utf-8") as f:
        try:
            config = json.load(f)
        except json.JSONDecodeError as exc:
            pytest.fail(f"Invalid JSON in realm config: {exc}")

    return config


class TestRealmStructure:
    """AC-001: Realm structure with pinned IDs and https-only SSL."""

    def test_realm_name_is_study_tutor(self, realm_config: dict[str, Any]) -> None:
        """Realm name must be 'study-tutor'."""
        assert realm_config.get("realm") == "study-tutor", \
            "Realm name must be 'study-tutor'"

    def test_realm_id_is_pinned(self, realm_config: dict[str, Any]) -> None:
        """Realm ID must be pinned to prevent drift across restarts."""
        realm_id = realm_config.get("id")
        assert realm_id is not None, "Realm must have an 'id' field"
        assert isinstance(realm_id, str), "Realm ID must be a string"
        assert len(realm_id) > 0, "Realm ID must not be empty"
        # Verify it's a fixed value (not auto-generated UUID format)
        assert realm_id == "study-tutor-realm-001", \
            f"Realm ID should be pinned to 'study-tutor-realm-001', got: {realm_id}"

    def test_ssl_required_is_all(self, realm_config: dict[str, Any]) -> None:
        """SSL must be required for all connections (https-only realm)."""
        ssl_required = realm_config.get("sslRequired")
        assert ssl_required == "all", \
            f"sslRequired must be 'all' for https-only realm, got: {ssl_required}"

    def test_realm_is_enabled(self, realm_config: dict[str, Any]) -> None:
        """Realm must be enabled."""
        assert realm_config.get("enabled") is True, "Realm must be enabled"


class TestClients:
    """AC-002: Public clients with correct OAuth flows."""

    def test_study_tutor_app_client_exists(self, realm_config: dict[str, Any]) -> None:
        """study-tutor-app client must exist."""
        clients = realm_config.get("clients", [])
        app_client = next(
            (c for c in clients if c.get("clientId") == "study-tutor-app"),
            None
        )
        assert app_client is not None, "study-tutor-app client not found"

    def test_study_tutor_app_is_public_with_pkce(self, realm_config: dict[str, Any]) -> None:
        """study-tutor-app must be public with PKCE S256 enforced."""
        clients = realm_config.get("clients", [])
        app_client = next(
            (c for c in clients if c.get("clientId") == "study-tutor-app"),
            None
        )
        assert app_client is not None

        # Must be public client
        assert app_client.get("publicClient") is True, \
            "study-tutor-app must be a public client"

        # Must have PKCE S256 enforced
        attributes = app_client.get("attributes", {})
        pkce_method = attributes.get("pkce.code.challenge.method")
        assert pkce_method == "S256", \
            f"study-tutor-app must enforce PKCE S256, got: {pkce_method}"

        # Must support Authorization Code flow (standard flow)
        assert app_client.get("standardFlowEnabled") is True, \
            "study-tutor-app must have Authorization Code flow enabled"

    def test_study_tutor_app_has_offline_access(self, realm_config: dict[str, Any]) -> None:
        """study-tutor-app must include offline_access scope for refresh tokens."""
        clients = realm_config.get("clients", [])
        app_client = next(
            (c for c in clients if c.get("clientId") == "study-tutor-app"),
            None
        )
        assert app_client is not None

        default_scopes = app_client.get("defaultClientScopes", [])
        assert "offline_access" in default_scopes, \
            "study-tutor-app must include offline_access in default scopes"

    def test_study_tutor_app_has_pinned_id(self, realm_config: dict[str, Any]) -> None:
        """study-tutor-app client ID must be pinned."""
        clients = realm_config.get("clients", [])
        app_client = next(
            (c for c in clients if c.get("clientId") == "study-tutor-app"),
            None
        )
        assert app_client is not None

        client_id = app_client.get("id")
        assert client_id is not None, "study-tutor-app must have pinned 'id'"
        assert isinstance(client_id, str) and len(client_id) > 0

    def test_reachy_robot_client_exists(self, realm_config: dict[str, Any]) -> None:
        """reachy-robot client must exist."""
        clients = realm_config.get("clients", [])
        robot_client = next(
            (c for c in clients if c.get("clientId") == "reachy-robot"),
            None
        )
        assert robot_client is not None, "reachy-robot client not found"

    def test_reachy_robot_is_public_with_device_grant(self, realm_config: dict[str, Any]) -> None:
        """reachy-robot must be public with device authorization grant enabled."""
        clients = realm_config.get("clients", [])
        robot_client = next(
            (c for c in clients if c.get("clientId") == "reachy-robot"),
            None
        )
        assert robot_client is not None

        # Must be public client
        assert robot_client.get("publicClient") is True, \
            "reachy-robot must be a public client"

        # Must have device authorization grant enabled
        attributes = robot_client.get("attributes", {})
        device_grant = attributes.get("oauth2.device.authorization.grant.enabled")
        assert device_grant == "true", \
            f"reachy-robot must have device authorization grant enabled, got: {device_grant}"

    def test_reachy_robot_has_pinned_id(self, realm_config: dict[str, Any]) -> None:
        """reachy-robot client ID must be pinned."""
        clients = realm_config.get("clients", [])
        robot_client = next(
            (c for c in clients if c.get("clientId") == "reachy-robot"),
            None
        )
        assert robot_client is not None

        client_id = robot_client.get("id")
        assert client_id is not None, "reachy-robot must have pinned 'id'"
        assert isinstance(client_id, str) and len(client_id) > 0


class TestRealmRoles:
    """AC-003: Realm roles student and parent exist."""

    def test_student_role_exists(self, realm_config: dict[str, Any]) -> None:
        """Realm role 'student' must exist."""
        roles = realm_config.get("roles", {}).get("realm", [])
        student_role = next(
            (r for r in roles if r.get("name") == "student"),
            None
        )
        assert student_role is not None, "Realm role 'student' not found"

    def test_parent_role_exists(self, realm_config: dict[str, Any]) -> None:
        """Realm role 'parent' must exist (reserved for future use)."""
        roles = realm_config.get("roles", {}).get("realm", [])
        parent_role = next(
            (r for r in roles if r.get("name") == "parent"),
            None
        )
        assert parent_role is not None, "Realm role 'parent' not found"

    def test_student_role_has_pinned_id(self, realm_config: dict[str, Any]) -> None:
        """Student role must have a pinned ID."""
        roles = realm_config.get("roles", {}).get("realm", [])
        student_role = next(
            (r for r in roles if r.get("name") == "student"),
            None
        )
        assert student_role is not None

        role_id = student_role.get("id")
        assert role_id is not None, "Student role must have pinned 'id'"
        assert isinstance(role_id, str) and len(role_id) > 0

    def test_parent_role_has_pinned_id(self, realm_config: dict[str, Any]) -> None:
        """Parent role must have a pinned ID."""
        roles = realm_config.get("roles", {}).get("realm", [])
        parent_role = next(
            (r for r in roles if r.get("name") == "parent"),
            None
        )
        assert parent_role is not None

        role_id = parent_role.get("id")
        assert role_id is not None, "Parent role must have pinned 'id'"
        assert isinstance(role_id, str) and len(role_id) > 0


class TestStudentIdMapper:
    """AC-004: student_id user attribute to token claim mapper."""

    def test_study_tutor_app_has_student_id_mapper(self, realm_config: dict[str, Any]) -> None:
        """study-tutor-app must have student_id protocol mapper."""
        clients = realm_config.get("clients", [])
        app_client = next(
            (c for c in clients if c.get("clientId") == "study-tutor-app"),
            None
        )
        assert app_client is not None

        mappers = app_client.get("protocolMappers", [])
        student_id_mapper = next(
            (m for m in mappers if m.get("name") == "student_id"),
            None
        )
        assert student_id_mapper is not None, \
            "study-tutor-app must have student_id protocol mapper"

    def test_study_tutor_app_mapper_configuration(self, realm_config: dict[str, Any]) -> None:
        """student_id mapper must map user.attribute to student_id claim."""
        clients = realm_config.get("clients", [])
        app_client = next(
            (c for c in clients if c.get("clientId") == "study-tutor-app"),
            None
        )
        assert app_client is not None

        mappers = app_client.get("protocolMappers", [])
        student_id_mapper = next(
            (m for m in mappers if m.get("name") == "student_id"),
            None
        )
        assert student_id_mapper is not None

        config = student_id_mapper.get("config", {})
        assert config.get("user.attribute") == "student_id", \
            "Mapper must read from user.attribute 'student_id'"
        assert config.get("claim.name") == "student_id", \
            "Mapper must write to claim 'student_id'"
        assert config.get("access.token.claim") == "true", \
            "student_id must be included in access token"
        assert config.get("id.token.claim") == "true", \
            "student_id must be included in ID token"

    def test_reachy_robot_has_student_id_mapper(self, realm_config: dict[str, Any]) -> None:
        """reachy-robot must have student_id protocol mapper."""
        clients = realm_config.get("clients", [])
        robot_client = next(
            (c for c in clients if c.get("clientId") == "reachy-robot"),
            None
        )
        assert robot_client is not None

        mappers = robot_client.get("protocolMappers", [])
        student_id_mapper = next(
            (m for m in mappers if m.get("name") == "student_id"),
            None
        )
        assert student_id_mapper is not None, \
            "reachy-robot must have student_id protocol mapper"

    def test_reachy_robot_mapper_configuration(self, realm_config: dict[str, Any]) -> None:
        """reachy-robot student_id mapper must map user.attribute to student_id claim."""
        clients = realm_config.get("clients", [])
        robot_client = next(
            (c for c in clients if c.get("clientId") == "reachy-robot"),
            None
        )
        assert robot_client is not None

        mappers = robot_client.get("protocolMappers", [])
        student_id_mapper = next(
            (m for m in mappers if m.get("name") == "student_id"),
            None
        )
        assert student_id_mapper is not None

        config = student_id_mapper.get("config", {})
        assert config.get("user.attribute") == "student_id", \
            "Mapper must read from user.attribute 'student_id'"
        assert config.get("claim.name") == "student_id", \
            "Mapper must write to claim 'student_id'"
        assert config.get("access.token.claim") == "true", \
            "student_id must be included in access token"


class TestProdSafeInvariants:
    """AC-005: Prod-safe invariants - no users, no secrets, no live-suite."""

    def test_no_users_in_realm(self, realm_config: dict[str, Any]) -> None:
        """Realm must not contain any users (users are runbook-created, never committed)."""
        # Check for 'users' key
        assert "users" not in realm_config or realm_config.get("users") == [], \
            "Realm must not contain 'users' array (PII must not be committed)"

        # Also verify the JSON file content doesn't contain 'users' anywhere
        realm_json = REALM_CONFIG_PATH.read_text(encoding="utf-8")
        # Allow for the word 'users' in comments or field names like 'enabledEventTypes'
        # but not as a top-level array
        assert '"users"' not in realm_json or '"users": []' in realm_json, \
            "Realm JSON must not contain populated 'users' field"

    def test_no_client_secrets(self, realm_config: dict[str, Any]) -> None:
        """Clients must not contain secret values (public clients only)."""
        clients = realm_config.get("clients", [])

        for client in clients:
            client_id = client.get("clientId", "unknown")

            # No 'secret' field should exist
            assert "secret" not in client, \
                f"Client '{client_id}' must not have 'secret' field (public clients only)"

            # All clients must be public
            assert client.get("publicClient") is True, \
                f"Client '{client_id}' must be a public client (publicClient: true)"

    def test_no_live_suite_client(self, realm_config: dict[str, Any]) -> None:
        """live-suite client must not exist (dev-only, never committed to prod realm)."""
        clients = realm_config.get("clients", [])

        live_suite_client = next(
            (c for c in clients if c.get("clientId") == "live-suite"),
            None
        )
        assert live_suite_client is None, \
            "live-suite client must not be in committed realm (dev-only, runbook-created)"

        # Also verify the JSON file content doesn't contain 'live-suite' anywhere
        realm_json = REALM_CONFIG_PATH.read_text(encoding="utf-8")
        assert "live-suite" not in realm_json, \
            "Realm JSON must not reference 'live-suite' (dev-only client)"


class TestJsonValidity:
    """AC-006: JSON validity and formatting."""

    def test_json_is_valid(self, realm_config: dict[str, Any]) -> None:
        """Realm config must be valid JSON (already validated by fixture)."""
        # If we got here, the fixture successfully parsed the JSON
        assert realm_config is not None
        assert isinstance(realm_config, dict)

    def test_json_is_properly_formatted(self) -> None:
        """Realm JSON should be properly formatted (indented, readable)."""
        realm_json = REALM_CONFIG_PATH.read_text(encoding="utf-8")

        # Verify it's not minified (should have newlines and indentation)
        assert "\n" in realm_json, "JSON should be formatted with newlines"
        assert "  " in realm_json or "\t" in realm_json, \
            "JSON should be indented for readability"

        # Verify it can be re-parsed (round-trip test)
        try:
            parsed = json.loads(realm_json)
            assert parsed is not None
        except json.JSONDecodeError as exc:
            pytest.fail(f"JSON failed round-trip parsing: {exc}")

    def test_required_keycloak_fields_present(self, realm_config: dict[str, Any]) -> None:
        """Essential Keycloak realm fields must be present."""
        required_fields = [
            "id",
            "realm",
            "enabled",
            "sslRequired",
            "clients",
            "roles",
        ]

        for field in required_fields:
            assert field in realm_config, \
                f"Required field '{field}' missing from realm config"
