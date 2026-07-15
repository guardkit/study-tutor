"""Test suite for Keycloak realm-as-code configuration.

Validates TASK-KC-002 acceptance criteria:
- Realm study-tutor with pinned IDs and https-only sslRequired
- Public clients: study-tutor-app (PKCE) and reachy-robot (device grant)
- Realm roles: student and parent
- Protocol mapper: student_id attribute → claim
- Security invariants: no users, no secrets, no live-suite client
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def realm_file() -> Path:
    """Path to the realm-as-code JSON file."""
    return Path(__file__).parents[3] / "deploy" / "keycloak" / "realm" / "study-tutor-realm.json"


@pytest.fixture
def realm_data(realm_file: Path) -> dict:
    """Load and parse the realm JSON."""
    with realm_file.open() as f:
        return json.load(f)


class TestRealmStructure:
    """AC-001: Realm study-tutor with pinned IDs and https-only sslRequired."""

    def test_realm_exists_and_is_valid_json(self, realm_file: Path) -> None:
        """Realm JSON file exists and is valid JSON."""
        assert realm_file.exists(), f"Realm file not found at {realm_file}"
        with realm_file.open() as f:
            data = json.load(f)
        assert isinstance(data, dict), "Realm file must be a JSON object"

    def test_realm_name_and_id_pinned(self, realm_data: dict) -> None:
        """Realm name is 'study-tutor' and id field is pinned."""
        assert realm_data.get("realm") == "study-tutor", "Realm name must be 'study-tutor'"
        assert "id" in realm_data, "Realm must have a pinned 'id' field"
        assert isinstance(realm_data["id"], str), "Realm id must be a string"
        assert len(realm_data["id"]) > 0, "Realm id must not be empty"

    def test_realm_https_only(self, realm_data: dict) -> None:
        """Realm requires SSL/HTTPS (sslRequired configured)."""
        ssl_required = realm_data.get("sslRequired")
        assert ssl_required is not None, "sslRequired must be set"
        # Keycloak accepts: "all", "external", "none"
        # For https-only, we need "all" or "external" (not "none")
        assert ssl_required in ["all", "external"], \
            f"sslRequired must be 'all' or 'external' for https-only, got: {ssl_required}"


class TestClients:
    """AC-002: Clients study-tutor-app (PKCE) and reachy-robot (device grant)."""

    def test_clients_exist(self, realm_data: dict) -> None:
        """Clients array exists and contains expected clients."""
        clients = realm_data.get("clients", [])
        assert isinstance(clients, list), "clients must be an array"

        client_ids = {c.get("clientId") for c in clients}
        assert "study-tutor-app" in client_ids, "study-tutor-app client must exist"
        assert "reachy-robot" in client_ids, "reachy-robot client must exist"

    def test_study_tutor_app_config(self, realm_data: dict) -> None:
        """study-tutor-app is public, PKCE S256 enforced, offline_access enabled."""
        clients = realm_data.get("clients", [])
        app_client = next((c for c in clients if c.get("clientId") == "study-tutor-app"), None)

        assert app_client is not None, "study-tutor-app client must exist"

        # Pinned ID
        assert "id" in app_client, "Client must have pinned 'id' field"
        assert isinstance(app_client["id"], str) and len(app_client["id"]) > 0

        # Public client (not confidential)
        assert app_client.get("publicClient") is True, "Must be a public client"

        # PKCE S256 enforced
        pkce_challenge_method = app_client.get("attributes", {}).get("pkce.code.challenge.method")
        assert pkce_challenge_method == "S256", "PKCE code challenge method must be S256"

        # Authorization Code flow enabled (standardFlowEnabled)
        assert app_client.get("standardFlowEnabled") is True, "Authorization Code flow must be enabled"

        # offline_access scope
        # Check if offline_access is in defaultClientScopes or optionalClientScopes
        default_scopes = app_client.get("defaultClientScopes", [])
        optional_scopes = app_client.get("optionalClientScopes", [])
        all_scopes = default_scopes + optional_scopes
        assert "offline_access" in all_scopes, "offline_access scope must be available"

    def test_reachy_robot_config(self, realm_data: dict) -> None:
        """reachy-robot is public, OAuth 2.0 Device Authorization Grant enabled."""
        clients = realm_data.get("clients", [])
        robot_client = next((c for c in clients if c.get("clientId") == "reachy-robot"), None)

        assert robot_client is not None, "reachy-robot client must exist"

        # Pinned ID
        assert "id" in robot_client, "Client must have pinned 'id' field"
        assert isinstance(robot_client["id"], str) and len(robot_client["id"]) > 0

        # Public client
        assert robot_client.get("publicClient") is True, "Must be a public client"

        # Device Authorization Grant (OAuth2DeviceAuthorizationGrantEnabled)
        device_grant = robot_client.get("attributes", {}).get("oauth2.device.authorization.grant.enabled")
        assert device_grant == "true", "Device Authorization Grant must be enabled"


class TestRoles:
    """AC-003: Realm roles student and parent both exist."""

    def test_realm_roles_exist(self, realm_data: dict) -> None:
        """Realm roles 'student' and 'parent' are defined."""
        roles = realm_data.get("roles", {}).get("realm", [])
        assert isinstance(roles, list), "realm roles must be an array"

        role_names = {r.get("name") for r in roles}
        assert "student" in role_names, "student role must exist"
        assert "parent" in role_names, "parent role must exist"


class TestProtocolMapper:
    """AC-004: student_id user-attribute → student_id claim protocol mapper."""

    def test_student_id_mapper_on_study_tutor_app(self, realm_data: dict) -> None:
        """study-tutor-app has student_id protocol mapper."""
        clients = realm_data.get("clients", [])
        app_client = next((c for c in clients if c.get("clientId") == "study-tutor-app"), None)
        assert app_client is not None

        mappers = app_client.get("protocolMappers", [])
        student_id_mapper = next(
            (m for m in mappers if m.get("config", {}).get("claim.name") == "student_id"),
            None
        )

        assert student_id_mapper is not None, "student_id protocol mapper must exist"
        assert student_id_mapper.get("protocol") == "openid-connect"
        assert student_id_mapper.get("protocolMapper") == "oidc-usermodel-attribute-mapper"

        config = student_id_mapper.get("config", {})
        assert config.get("user.attribute") == "student_id", "Must map from student_id user attribute"
        assert config.get("claim.name") == "student_id", "Must map to student_id claim"
        assert config.get("jsonType.label") == "String", "Claim type must be String"

    def test_student_id_mapper_on_reachy_robot(self, realm_data: dict) -> None:
        """reachy-robot also has student_id protocol mapper."""
        clients = realm_data.get("clients", [])
        robot_client = next((c for c in clients if c.get("clientId") == "reachy-robot"), None)
        assert robot_client is not None

        mappers = robot_client.get("protocolMappers", [])
        student_id_mapper = next(
            (m for m in mappers if m.get("config", {}).get("claim.name") == "student_id"),
            None
        )

        assert student_id_mapper is not None, "student_id protocol mapper must exist on reachy-robot"


class TestSecurityInvariants:
    """AC-005: No users, no secrets, no live-suite client (grep-verifiable)."""

    def test_no_users_array(self, realm_data: dict) -> None:
        """Realm JSON must not contain a users array."""
        assert "users" not in realm_data, "Realm must not contain 'users' array"

    def test_no_client_secrets(self, realm_data: dict) -> None:
        """No client has a 'secret' field defined."""
        clients = realm_data.get("clients", [])
        for client in clients:
            assert "secret" not in client, \
                f"Client {client.get('clientId')} must not have 'secret' field"

    def test_no_live_suite_client(self, realm_data: dict) -> None:
        """The live-suite test client must not exist in this committed realm."""
        clients = realm_data.get("clients", [])
        client_ids = {c.get("clientId") for c in clients}
        assert "live-suite" not in client_ids, \
            "live-suite client must not exist in committed prod realm"

    def test_raw_json_grep_verification(self, realm_file: Path) -> None:
        """Raw JSON text does not contain forbidden strings."""
        content = realm_file.read_text()

        # These strings should never appear in the committed realm
        forbidden = [
            '"users"',  # users array key
            '"secret"',  # client secret field
            'live-suite',  # test-only client name
        ]

        for forbidden_str in forbidden:
            assert forbidden_str not in content, \
                f"Realm JSON must not contain '{forbidden_str}'"


class TestJsonValidity:
    """AC-006: Valid JSON that passes format checks."""

    def test_json_is_well_formed(self, realm_file: Path) -> None:
        """JSON is parseable and properly formatted."""
        content = realm_file.read_text()

        # Must be valid JSON
        data = json.loads(content)
        assert isinstance(data, dict)

        # Re-serialize and check it's consistent (basic format check)
        reserialized = json.dumps(data, indent=2, sort_keys=False)
        assert len(reserialized) > 0

    def test_required_top_level_fields(self, realm_data: dict) -> None:
        """Realm has all required top-level fields."""
        required_fields = ["realm", "id", "clients", "roles"]
        for field in required_fields:
            assert field in realm_data, f"Realm must have '{field}' field"
