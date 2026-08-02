"""Hermetic unit tests for KeycloakTokenResolver.

TASK-KCA2-003: All tests mint their own RSA keypair and monkeypatch PyJWKClient
to serve a fake JWKS. No live Keycloak realm, no network calls.
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from study_tutor.http.auth_keycloak import KeycloakTokenResolver
from study_tutor.http.oidc_config import OIDCSettings
from study_tutor.session.errors import Unauthenticated


# Test fixtures for RSA key generation and token minting
@pytest.fixture
def rsa_keypair():
    """Generate an RSA keypair for test token signing."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    public_key = private_key.public_key()

    # Serialize keys
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    return {
        "private_key": private_pem,
        "public_key": public_pem,
        "private_key_obj": private_key,
        "public_key_obj": public_key,
        "kid": "test-key-id-001"
    }


@pytest.fixture
def oidc_settings():
    """OIDC settings for testing."""
    return OIDCSettings(
        auth_mode="keycloak",
        issuer="https://idp-test.tail0000.ts.net:8443/realms/study-tutor",
        audience="study-tutor-app",
        jwks_url="https://100.100.100.100:8443/realms/study-tutor/protocol/openid-connect/certs",
        student_claim="student_id",
        leeway=60
    )


def mint_token(
    rsa_keypair: dict,
    issuer: str,
    audience: str,
    student_id: str | None = "alice",
    kid: str | None = None,
    algorithm: str = "RS256",
    exp_delta: timedelta | None = None,
    nbf_delta: timedelta | None = None,
    extra_claims: dict | None = None
) -> str:
    """Mint a JWT token for testing.

    Args:
        rsa_keypair: RSA keypair fixture
        issuer: Token issuer (iss claim)
        audience: Token audience (aud claim)
        student_id: Student ID to include (or None to omit)
        kid: Key ID header (defaults to rsa_keypair["kid"])
        algorithm: Signing algorithm
        exp_delta: Expiration time delta from now (defaults to +1 hour)
        nbf_delta: Not-before time delta from now (defaults to -1 minute)
        extra_claims: Additional claims to include

    Returns:
        Encoded JWT token string
    """
    now = datetime.now(timezone.utc)

    payload = {
        "iss": issuer,
        "aud": audience,
        "exp": int((now + (exp_delta or timedelta(hours=1))).timestamp()),
        "nbf": int((now + (nbf_delta or timedelta(minutes=-1))).timestamp()),
        "iat": int(now.timestamp()),
    }

    if student_id is not None:
        payload["student_id"] = student_id

    if extra_claims:
        payload.update(extra_claims)

    headers = {
        "kid": kid or rsa_keypair["kid"],
        "alg": algorithm
    }

    return jwt.encode(
        payload,
        rsa_keypair["private_key"],
        algorithm=algorithm,
        headers=headers
    )


@pytest.fixture
def mock_pyjwkclient(rsa_keypair):
    """Mock PyJWKClient to serve test public key without network calls."""
    def _mock_factory(jwks_url: str):
        mock_client = MagicMock()
        mock_signing_key = MagicMock()

        # The signing key's key property returns the public key
        mock_signing_key.key = rsa_keypair["public_key_obj"]

        # get_signing_key_from_jwt returns the signing key
        mock_client.get_signing_key_from_jwt.return_value = mock_signing_key

        return mock_client

    return _mock_factory


class TestKeycloakTokenResolverValid:
    """Test valid token scenarios."""

    @pytest.mark.asyncio
    async def test_valid_token_returns_student_id(
        self, oidc_settings, rsa_keypair, mock_pyjwkclient
    ):
        """AC-001/002: Valid token with all claims returns student_id."""
        with patch("study_tutor.http.auth_keycloak.PyJWKClient", side_effect=mock_pyjwkclient):
            resolver = KeycloakTokenResolver(oidc_settings)

            token = mint_token(
                rsa_keypair,
                issuer=oidc_settings.issuer,
                audience=oidc_settings.audience,
                student_id="alice"
            )

            student_id = await resolver.resolve(token)
            assert student_id == "alice"

    @pytest.mark.asyncio
    async def test_within_leeway_accepted(
        self, oidc_settings, rsa_keypair, mock_pyjwkclient
    ):
        """AC-001: Token within 60s leeway is accepted."""
        with patch("study_tutor.http.auth_keycloak.PyJWKClient", side_effect=mock_pyjwkclient):
            resolver = KeycloakTokenResolver(oidc_settings)

            # Token expired 30 seconds ago (within 60s leeway)
            token = mint_token(
                rsa_keypair,
                issuer=oidc_settings.issuer,
                audience=oidc_settings.audience,
                student_id="bob",
                exp_delta=timedelta(seconds=-30)
            )

            student_id = await resolver.resolve(token)
            assert student_id == "bob"


class TestKeycloakTokenResolverSignature:
    """Test signature validation scenarios."""

    @pytest.mark.asyncio
    async def test_bad_signature_raises_unauthenticated(
        self, oidc_settings, rsa_keypair, mock_pyjwkclient
    ):
        """AC-003: Invalid signature raises Unauthenticated."""
        with patch("study_tutor.http.auth_keycloak.PyJWKClient", side_effect=mock_pyjwkclient):
            resolver = KeycloakTokenResolver(oidc_settings)

            # Mint valid token then corrupt it
            token = mint_token(
                rsa_keypair,
                issuer=oidc_settings.issuer,
                audience=oidc_settings.audience,
                student_id="alice"
            )
            corrupted_token = token[:-10] + "corrupted!"

            # Corrupted signature triggers malformed/padding error (which is correct)
            with pytest.raises(Unauthenticated, match="malformed|invalid|signature"):
                await resolver.resolve(corrupted_token)

    @pytest.mark.asyncio
    async def test_unknown_kid_raises_unauthenticated(
        self, oidc_settings, rsa_keypair, mock_pyjwkclient
    ):
        """AC-003: Token with unknown kid raises Unauthenticated."""
        def _failing_mock(jwks_url: str):
            mock_client = MagicMock()
            mock_client.get_signing_key_from_jwt.side_effect = jwt.exceptions.PyJWKClientError(
                "Unable to find a signing key that matches"
            )
            return mock_client

        with patch("study_tutor.http.auth_keycloak.PyJWKClient", side_effect=_failing_mock):
            resolver = KeycloakTokenResolver(oidc_settings)

            token = mint_token(
                rsa_keypair,
                issuer=oidc_settings.issuer,
                audience=oidc_settings.audience,
                student_id="alice",
                kid="unknown-key-999"
            )

            with pytest.raises(Unauthenticated, match="key"):
                await resolver.resolve(token)


class TestKeycloakTokenResolverClaims:
    """Test claim validation scenarios."""

    @pytest.mark.asyncio
    async def test_wrong_issuer_raises_unauthenticated(
        self, oidc_settings, rsa_keypair, mock_pyjwkclient
    ):
        """AC-001/004: Wrong issuer raises Unauthenticated."""
        with patch("study_tutor.http.auth_keycloak.PyJWKClient", side_effect=mock_pyjwkclient):
            resolver = KeycloakTokenResolver(oidc_settings)

            token = mint_token(
                rsa_keypair,
                issuer="https://evil.example.com/realms/fake",
                audience=oidc_settings.audience,
                student_id="alice"
            )

            with pytest.raises(Unauthenticated, match="issuer"):
                await resolver.resolve(token)

    @pytest.mark.asyncio
    async def test_wrong_audience_raises_unauthenticated(
        self, oidc_settings, rsa_keypair, mock_pyjwkclient
    ):
        """AC-001: Wrong audience raises Unauthenticated."""
        with patch("study_tutor.http.auth_keycloak.PyJWKClient", side_effect=mock_pyjwkclient):
            resolver = KeycloakTokenResolver(oidc_settings)

            token = mint_token(
                rsa_keypair,
                issuer=oidc_settings.issuer,
                audience="wrong-app",
                student_id="alice"
            )

            with pytest.raises(Unauthenticated, match="audience"):
                await resolver.resolve(token)

    @pytest.mark.asyncio
    async def test_missing_student_claim_raises_unauthenticated(
        self, oidc_settings, rsa_keypair, mock_pyjwkclient
    ):
        """AC-002: Missing student_id claim raises Unauthenticated, not 500."""
        with patch("study_tutor.http.auth_keycloak.PyJWKClient", side_effect=mock_pyjwkclient):
            resolver = KeycloakTokenResolver(oidc_settings)

            # Mint token WITHOUT student_id claim
            token = mint_token(
                rsa_keypair,
                issuer=oidc_settings.issuer,
                audience=oidc_settings.audience,
                student_id=None  # Omit the claim
            )

            with pytest.raises(Unauthenticated, match="student_id.*claim"):
                await resolver.resolve(token)

    @pytest.mark.asyncio
    async def test_expired_token_raises_unauthenticated(
        self, oidc_settings, rsa_keypair, mock_pyjwkclient
    ):
        """AC-001/003: Expired token (beyond leeway) raises Unauthenticated."""
        with patch("study_tutor.http.auth_keycloak.PyJWKClient", side_effect=mock_pyjwkclient):
            resolver = KeycloakTokenResolver(oidc_settings)

            # Token expired 2 minutes ago (beyond 60s leeway)
            token = mint_token(
                rsa_keypair,
                issuer=oidc_settings.issuer,
                audience=oidc_settings.audience,
                student_id="alice",
                exp_delta=timedelta(minutes=-2)
            )

            with pytest.raises(Unauthenticated, match="expired"):
                await resolver.resolve(token)

    @pytest.mark.asyncio
    async def test_not_yet_valid_raises_unauthenticated(
        self, oidc_settings, rsa_keypair, mock_pyjwkclient
    ):
        """AC-001/003: Not-yet-valid token (beyond leeway) raises Unauthenticated."""
        with patch("study_tutor.http.auth_keycloak.PyJWKClient", side_effect=mock_pyjwkclient):
            resolver = KeycloakTokenResolver(oidc_settings)

            # Token not valid until 2 minutes from now (beyond 60s leeway)
            token = mint_token(
                rsa_keypair,
                issuer=oidc_settings.issuer,
                audience=oidc_settings.audience,
                student_id="alice",
                nbf_delta=timedelta(minutes=2)
            )

            with pytest.raises(Unauthenticated, match="not.*valid|before"):
                await resolver.resolve(token)


class TestKeycloakTokenResolverAlgorithm:
    """Test algorithm validation scenarios (security-critical)."""

    @pytest.mark.asyncio
    async def test_alg_none_rejected(
        self, oidc_settings, rsa_keypair, mock_pyjwkclient
    ):
        """AC-001/003: alg:none tokens are rejected."""
        with patch("study_tutor.http.auth_keycloak.PyJWKClient", side_effect=mock_pyjwkclient):
            resolver = KeycloakTokenResolver(oidc_settings)

            # Create unsigned token (alg: none)
            now = datetime.now(timezone.utc)
            payload = {
                "iss": oidc_settings.issuer,
                "aud": oidc_settings.audience,
                "exp": int((now + timedelta(hours=1)).timestamp()),
                "nbf": int((now - timedelta(minutes=1)).timestamp()),
                "student_id": "alice"
            }

            # jwt.encode with algorithm="none" creates unsigned token
            unsigned_token = jwt.encode(payload, "", algorithm="none")

            with pytest.raises(Unauthenticated, match="algorithm"):
                await resolver.resolve(unsigned_token)

    @pytest.mark.asyncio
    async def test_hs256_symmetric_rejected(
        self, oidc_settings, rsa_keypair, mock_pyjwkclient
    ):
        """AC-001/003: HS256 (symmetric) tokens are rejected."""
        with patch("study_tutor.http.auth_keycloak.PyJWKClient", side_effect=mock_pyjwkclient):
            resolver = KeycloakTokenResolver(oidc_settings)

            # Create HS256 token (symmetric algorithm)
            now = datetime.now(timezone.utc)
            payload = {
                "iss": oidc_settings.issuer,
                "aud": oidc_settings.audience,
                "exp": int((now + timedelta(hours=1)).timestamp()),
                "nbf": int((now - timedelta(minutes=1)).timestamp()),
                "student_id": "alice"
            }

            hs256_token = jwt.encode(payload, "secret", algorithm="HS256")

            with pytest.raises(Unauthenticated, match="algorithm"):
                await resolver.resolve(hs256_token)


class TestKeycloakTokenResolverInfra:
    """Test infrastructure failure scenarios."""

    @pytest.mark.asyncio
    async def test_unreachable_jwks_raises_unauthenticated(
        self, oidc_settings, rsa_keypair
    ):
        """AC-003: Unreachable JWKS raises Unauthenticated, not 500."""
        def _network_error_mock(jwks_url: str):
            mock_client = MagicMock()
            mock_client.get_signing_key_from_jwt.side_effect = Exception("Network unreachable")
            return mock_client

        with patch("study_tutor.http.auth_keycloak.PyJWKClient", side_effect=_network_error_mock):
            resolver = KeycloakTokenResolver(oidc_settings)

            token = mint_token(
                rsa_keypair,
                issuer=oidc_settings.issuer,
                audience=oidc_settings.audience,
                student_id="alice"
            )

            with pytest.raises(Unauthenticated):
                await resolver.resolve(token)

    @pytest.mark.asyncio
    async def test_garbage_token_raises_unauthenticated(
        self, oidc_settings, mock_pyjwkclient
    ):
        """AC-003: Malformed token raises Unauthenticated."""
        with patch("study_tutor.http.auth_keycloak.PyJWKClient", side_effect=mock_pyjwkclient):
            resolver = KeycloakTokenResolver(oidc_settings)

            with pytest.raises(Unauthenticated):
                await resolver.resolve("not-a-jwt-token")


class TestKeycloakTokenResolverIssuerPinning:
    """Test issuer pinning behavior (KC-D2 gotcha)."""

    @pytest.mark.asyncio
    async def test_issuer_validation_uses_ts_net_name(
        self, rsa_keypair, mock_pyjwkclient
    ):
        """AC-004: Issuer validated against ts.net name, not JWKS URL."""
        # Settings with JWKS URL override (tailnet IP)
        settings = OIDCSettings(
            auth_mode="keycloak",
            issuer="https://idp-test.tail0000.ts.net:8443/realms/study-tutor",
            audience="study-tutor-app",
            jwks_url="https://100.100.100.100:8443/realms/study-tutor/protocol/openid-connect/certs",
            student_claim="student_id",
            leeway=60
        )

        with patch("study_tutor.http.auth_keycloak.PyJWKClient", side_effect=mock_pyjwkclient) as mock_cls:
            resolver = KeycloakTokenResolver(settings)

            # Verify PyJWKClient was instantiated with the JWKS URL (tailnet IP)
            assert mock_cls.call_count == 1
            call_args = mock_cls.call_args
            assert "100.100.100.100" in call_args[0][0]  # JWKS URL contains IP

            # Token with issuer as ts.net name (NOT the IP)
            token = mint_token(
                rsa_keypair,
                issuer=settings.issuer,  # ts.net name
                audience=settings.audience,
                student_id="alice"
            )

            # Should validate successfully (issuer pinned to ts.net name)
            student_id = await resolver.resolve(token)
            assert student_id == "alice"

            # Token with issuer as IP should FAIL
            token_with_ip_issuer = mint_token(
                rsa_keypair,
                issuer="https://100.100.100.100:8443/realms/study-tutor",  # IP, not ts.net
                audience=settings.audience,
                student_id="alice"
            )

            with pytest.raises(Unauthenticated, match="issuer"):
                await resolver.resolve(token_with_ip_issuer)


@pytest.mark.seam
@pytest.mark.integration_contract("OIDC_SETTINGS")
class TestOIDCSettingsIntegrationContract:
    """Seam test: verify OIDC_SETTINGS contract from TASK-KCA2-001."""

    def test_oidc_settings_issuer_pinning(self, mock_pyjwkclient):
        """Issuer stays pinned to ts.net name even under JWKS-URL override.

        Contract: STUDY_TUTOR_OIDC_JWKS_URL overrides only the fetch location
        (KC-D2 tailnet-IP gotcha); the issuer used for `iss` validation is the
        ts.net public name from STUDY_TUTOR_OIDC_ISSUER, never the fetch URL.
        Producer: TASK-KCA2-001
        """
        settings = OIDCSettings(
            auth_mode="keycloak",
            issuer="https://idp-test.tail0000.ts.net:8443/realms/study-tutor",
            audience="study-tutor-app",
            jwks_url="https://100.100.100.100:8443/realms/study-tutor/protocol/openid-connect/certs",
            student_claim="student_id",
            leeway=60
        )

        with patch("study_tutor.http.auth_keycloak.PyJWKClient", side_effect=mock_pyjwkclient):
            resolver = KeycloakTokenResolver(settings)

            # The issuer enforced during validation is the ts.net name, not the IP:
            assert resolver.expected_issuer == settings.issuer
            assert "ts.net" in resolver.expected_issuer
            assert resolver.expected_issuer != settings.jwks_url
