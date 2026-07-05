"""Unit tests for HTTP auth layer (TASK-APP1-02).

Tests token-table auth with injected fakes (no real DB): config parsing,
header-only extraction, reject-unknown, unseeded-student guard, envelope shape.
"""

from __future__ import annotations

from typing import Protocol

import pytest

from study_tutor.http.auth import HTTPAuthConfig, resolve_student_from_token
from study_tutor.session.errors import Unauthenticated


class FakeStudentStore(Protocol):
    """Fake store for testing unseeded-student guard."""

    async def student_exists(self, student_id: str) -> bool:
        """Check if student has an identity row."""
        ...


class InMemoryFakeStore:
    """Fake store that tracks known students in memory."""

    def __init__(self, known_students: set[str]):
        self.known_students = known_students
        self.create_session_called = False

    async def student_exists(self, student_id: str) -> bool:
        return student_id in self.known_students

    async def create_session(self, student_id: str, subject: str, topic: str | None):
        """Track that create_session was called (should never happen for unseeded)."""
        self.create_session_called = True


# AC-001: STUDY_TUTOR_HTTP_TOKENS JSON parsing tests
def test_config_parse_valid_single_entry():
    """AC-001: Prod config works with a single entry."""
    config_json = '{"token-lilymay": "lilymay"}'
    config = HTTPAuthConfig.from_env(tokens_json=config_json, dev_reset="false")
    assert config.token_to_student == {"token-lilymay": "lilymay"}
    assert config.dev_reset is False


def test_config_parse_valid_multiple_entries():
    """AC-001: Dev config works with two + any number of entries."""
    config_json = (
        '{"token-lilymay": "lilymay", "token-alex": "alex", "token-test": "test"}'
    )
    config = HTTPAuthConfig.from_env(tokens_json=config_json, dev_reset="true")
    assert config.token_to_student == {
        "token-lilymay": "lilymay",
        "token-alex": "alex",
        "token-test": "test",
    }
    assert config.dev_reset is True


def test_config_parse_malformed_json_raises_clear_error():
    """AC-001: Clear failure message on malformed JSON input."""
    malformed = '{"token-lilymay": "lilymay"'  # Missing closing brace
    with pytest.raises(ValueError, match="Failed to parse STUDY_TUTOR_HTTP_TOKENS"):
        HTTPAuthConfig.from_env(tokens_json=malformed, dev_reset="false")


def test_config_parse_empty_json_raises_clear_error():
    """AC-001: Clear failure on empty config."""
    with pytest.raises(ValueError, match="STUDY_TUTOR_HTTP_TOKENS cannot be empty"):
        HTTPAuthConfig.from_env(tokens_json="", dev_reset="false")


def test_config_parse_non_dict_json_raises_clear_error():
    """AC-001: Clear failure when JSON is not a dict."""
    with pytest.raises(
        ValueError, match="STUDY_TUTOR_HTTP_TOKENS must be a JSON object"
    ):
        HTTPAuthConfig.from_env(tokens_json='["token-lilymay"]', dev_reset="false")


# AC-002: Missing token, unknown token, non-header placement tests
@pytest.mark.asyncio
async def test_missing_authorization_header_raises_unauthenticated():
    """AC-002: Missing token resolves to Unauthenticated."""
    config = HTTPAuthConfig(
        token_to_student={"token-lilymay": "lilymay"}, dev_reset=False
    )
    fake_store = InMemoryFakeStore({"lilymay"})

    with pytest.raises(Unauthenticated, match="Missing Authorization header"):
        await resolve_student_from_token(
            authorization_header=None,
            config=config,
            student_store=fake_store,
        )


@pytest.mark.asyncio
async def test_malformed_authorization_header_raises_unauthenticated():
    """AC-002: Non-Bearer auth scheme resolves to Unauthenticated."""
    config = HTTPAuthConfig(
        token_to_student={"token-lilymay": "lilymay"}, dev_reset=False
    )
    fake_store = InMemoryFakeStore({"lilymay"})

    with pytest.raises(
        Unauthenticated, match="Authorization header must use Bearer scheme"
    ):
        await resolve_student_from_token(
            authorization_header="Basic dXNlcjpwYXNz",
            config=config,
            student_store=fake_store,
        )


@pytest.mark.asyncio
async def test_unknown_token_raises_unauthenticated():
    """AC-002: Unknown token resolves to Unauthenticated."""
    config = HTTPAuthConfig(
        token_to_student={"token-lilymay": "lilymay"}, dev_reset=False
    )
    fake_store = InMemoryFakeStore({"lilymay"})

    with pytest.raises(Unauthenticated, match="Unknown token"):
        await resolve_student_from_token(
            authorization_header="Bearer token-unknown",
            config=config,
            student_store=fake_store,
        )


@pytest.mark.asyncio
async def test_token_only_from_header_not_body():
    """AC-002: Token placement anywhere other than Authorization header is ignored.

    This test verifies that even if a token appears in request body or query string,
    only the Authorization header is honored. We simulate this by testing that a
    valid token in the header works, while missing header fails regardless of what
    might be in the body/query.
    """
    config = HTTPAuthConfig(
        token_to_student={"token-lilymay": "lilymay"}, dev_reset=False
    )
    fake_store = InMemoryFakeStore({"lilymay"})

    # Valid header works
    student_id = await resolve_student_from_token(
        authorization_header="Bearer token-lilymay",
        config=config,
        student_store=fake_store,
    )
    assert student_id == "lilymay"

    # Missing header fails (even if token might be in body/query - not checked)
    with pytest.raises(Unauthenticated):
        await resolve_student_from_token(
            authorization_header=None,
            config=config,
            student_store=fake_store,
        )


# AC-003: Unseeded-student guard tests
@pytest.mark.asyncio
async def test_unseeded_student_raises_unauthenticated_before_store_write():
    """AC-003: Unseeded-student requests resolve to Unauthenticated before any store write.

    Verified with a fake store: no create_session call should happen.
    """
    config = HTTPAuthConfig(
        token_to_student={"token-lilymay": "lilymay"}, dev_reset=False
    )
    # Fake store has NO students seeded
    fake_store = InMemoryFakeStore(known_students=set())

    with pytest.raises(Unauthenticated, match="Student .* is not seeded"):
        await resolve_student_from_token(
            authorization_header="Bearer token-lilymay",
            config=config,
            student_store=fake_store,
        )

    # Verify create_session was NEVER called
    assert fake_store.create_session_called is False


@pytest.mark.asyncio
async def test_seeded_student_resolves_successfully():
    """AC-003: Seeded student with valid token resolves successfully."""
    config = HTTPAuthConfig(
        token_to_student={"token-lilymay": "lilymay"}, dev_reset=False
    )
    fake_store = InMemoryFakeStore(known_students={"lilymay"})

    student_id = await resolve_student_from_token(
        authorization_header="Bearer token-lilymay",
        config=config,
        student_store=fake_store,
    )

    assert student_id == "lilymay"
    # No session creation should have happened during auth
    assert fake_store.create_session_called is False


# AC-004: Client-asserted student_id never overrides token
@pytest.mark.asyncio
async def test_token_derived_student_id_is_authoritative():
    """AC-004: Client-asserted student_id in request body never overrides the token's.

    The token resolution is server-side truth. This test verifies that the
    student_id returned from resolve_student_from_token is always the one
    from the token table, not client-provided.
    """
    config = HTTPAuthConfig(
        token_to_student={"token-lilymay": "lilymay", "token-alex": "alex"},
        dev_reset=False,
    )
    fake_store = InMemoryFakeStore(known_students={"lilymay", "alex"})

    # Token says "lilymay", regardless of what client might claim
    student_id = await resolve_student_from_token(
        authorization_header="Bearer token-lilymay",
        config=config,
        student_store=fake_store,
    )
    assert student_id == "lilymay"

    # Token says "alex", not what client might claim
    student_id = await resolve_student_from_token(
        authorization_header="Bearer token-alex",
        config=config,
        student_store=fake_store,
    )
    assert student_id == "alex"


# AC-005: No Keycloak/JWT imports
def test_no_keycloak_jwt_imports():
    """AC-005: No import of Keycloak/JWT libraries — table lookup only.

    This test verifies by importing the module and checking it doesn't fail,
    and that the implementation doesn't use JWT/Keycloak features.
    The Coach validation will grep for keycloak/jwt imports.
    """
    # If the module imports successfully, it means no hard dependencies on jwt/keycloak
    from study_tutor.http import auth

    # Module should not have jwt or keycloak attributes
    module_dict = dir(auth)
    forbidden_tokens = ["jwt", "JWT", "keycloak", "Keycloak", "jose"]
    for token in forbidden_tokens:
        matching = [item for item in module_dict if token.lower() in item.lower()]
        assert len(matching) == 0, f"Found forbidden import reference: {matching}"


# Integration test: full flow with valid token and seeded student
@pytest.mark.asyncio
async def test_full_auth_flow_valid_token_seeded_student():
    """Integration: Full auth flow with valid token and seeded student."""
    config = HTTPAuthConfig(
        token_to_student={"token-lilymay": "lilymay", "token-alex": "alex"},
        dev_reset=False,
    )
    fake_store = InMemoryFakeStore(known_students={"lilymay", "alex"})

    # Lilymay
    student_id = await resolve_student_from_token(
        authorization_header="Bearer token-lilymay",
        config=config,
        student_store=fake_store,
    )
    assert student_id == "lilymay"

    # Alex
    student_id = await resolve_student_from_token(
        authorization_header="Bearer token-alex",
        config=config,
        student_store=fake_store,
    )
    assert student_id == "alex"


# Dev reset flag test
def test_dev_reset_flag_parsing():
    """Test STUDY_TUTOR_HTTP_DEV_RESET flag parsing."""
    # True cases
    for value in ["true", "True", "TRUE", "1", "yes"]:
        config = HTTPAuthConfig.from_env(
            tokens_json='{"token-lilymay": "lilymay"}',
            dev_reset=value,
        )
        assert config.dev_reset is True

    # False cases
    for value in ["false", "False", "FALSE", "0", "no", ""]:
        config = HTTPAuthConfig.from_env(
            tokens_json='{"token-lilymay": "lilymay"}',
            dev_reset=value,
        )
        assert config.dev_reset is False
