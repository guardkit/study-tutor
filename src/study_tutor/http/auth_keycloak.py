"""Keycloak JWT token validation resolver.

TASK-KCA2-003 / FEAT-AUTH-002: KeycloakTokenResolver implements the TokenResolver
protocol by validating Keycloak access tokens via PyJWT + PyJWKClient. Design ref
KC-D6; security-critical JWKS validation with fail-closed error handling.

This module owns all PyJWT imports for the project (AC-005). All validation
failures raise Unauthenticated (never a 500) as per the fail-closed contract.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import jwt
from jwt import PyJWKClient

from study_tutor.http.oidc_config import OIDCSettings
from study_tutor.session.errors import Unauthenticated

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class KeycloakTokenResolver:
    """Keycloak JWT token resolver with JWKS-based signature validation.

    Implements the TokenResolver protocol from TASK-KCA2-002 by validating
    Keycloak access tokens according to the security contract (KC-D6):

    - Signature validation via PyJWKClient (cached JWKS, kid-rotation aware)
    - Issuer claim (iss) must match OIDCSettings.issuer (KC-D2 pinning)
    - Audience claim (aud) must include OIDCSettings.audience
    - Expiration (exp) and not-before (nbf) with 60s leeway (ASSUM-001)
    - Algorithm allowlist: RS256 only (rejects alg:none and symmetric HS256)
    - Student claim extraction only after successful validation
    - Fail-closed: all errors → Unauthenticated (never an unexpected 500)

    Attributes:
        settings: OIDC configuration from TASK-KCA2-001
        jwks_client: PyJWKClient instance for signature verification
        expected_issuer: Issuer URL for iss validation (pinned, not derived from JWKS URL)
    """

    settings: OIDCSettings
    jwks_client: PyJWKClient
    expected_issuer: str

    def __init__(self, settings: OIDCSettings):
        """Initialize resolver with OIDC settings.

        Args:
            settings: OIDC configuration from TASK-KCA2-001

        Note:
            Uses object.__setattr__ for frozen dataclass initialization.
            The jwks_client is constructed from get_effective_jwks_url(),
            but expected_issuer stays pinned to settings.issuer (KC-D2).
        """
        jwks_url = settings.get_effective_jwks_url()
        if not jwks_url:
            # In table mode or incomplete keycloak config, this would be None
            # The calling code (TASK-KCA2-004) validates completeness at boot,
            # but we handle it gracefully here
            raise ValueError(
                "Cannot initialize KeycloakTokenResolver: JWKS URL is not configured. "
                "Ensure STUDY_TUTOR_OIDC_ISSUER is set in keycloak mode."
            )

        # Frozen dataclass requires object.__setattr__
        object.__setattr__(self, "settings", settings)
        object.__setattr__(self, "jwks_client", PyJWKClient(jwks_url))
        object.__setattr__(self, "expected_issuer", settings.issuer)

    async def resolve(self, token: str) -> str:
        """Resolve Bearer token to student_id via Keycloak JWT validation.

        Validation pipeline (all failures → Unauthenticated):
        1. Decode token header to extract kid
        2. Fetch signing key from JWKS (cached, refetches on unknown kid)
        3. Verify signature with PyJWT.decode()
        4. Validate issuer, audience, exp, nbf, algorithm
        5. Extract student_id claim (missing claim → Unauthenticated)

        Args:
            token: JWT Bearer token from Authorization header

        Returns:
            Student ID from validated token claims

        Raises:
            Unauthenticated: On any validation failure (bad signature, wrong issuer,
                wrong audience, expired, not-yet-valid, alg:none, HS256, unreachable
                JWKS, missing student claim, malformed token, etc.)

        Examples:
            >>> settings = OIDCSettings(...)
            >>> resolver = KeycloakTokenResolver(settings)
            >>> student_id = await resolver.resolve(token)  # "alice"
        """
        try:
            # Step 1: Get signing key from JWKS (signature verification)
            # PyJWKClient handles kid extraction, JWKS fetch, caching, and rotation
            try:
                signing_key = self.jwks_client.get_signing_key_from_jwt(token)
            except jwt.exceptions.PyJWKClientError as e:
                # Unknown kid, JWKS fetch failure, etc.
                logger.warning("JWKS key fetch failed: %s", e)
                raise Unauthenticated(f"Unable to verify token signature: {e}") from e

            # Step 2: Decode and validate token
            # PyJWT.decode verifies signature, exp, nbf, iss, aud, and algorithm
            try:
                decoded = jwt.decode(
                    token,
                    signing_key.key,
                    algorithms=["RS256"],  # Explicit allowlist (rejects none/HS256)
                    issuer=self.expected_issuer,  # KC-D2: pinned to ts.net name
                    audience=self.settings.audience,
                    leeway=self.settings.leeway,  # 60s clock skew tolerance
                    options={
                        "verify_signature": True,
                        "verify_exp": True,
                        "verify_nbf": True,
                        "verify_iat": False,  # iat validation not required
                        "verify_aud": True,
                        "require_exp": True,
                        "require_iat": False,
                        "require_nbf": False,  # nbf is optional in OIDC
                    }
                )
            except jwt.exceptions.ExpiredSignatureError as e:
                logger.warning("Token expired: %s", e)
                raise Unauthenticated("Token has expired") from e
            except jwt.exceptions.ImmatureSignatureError as e:
                logger.warning("Token not yet valid: %s", e)
                raise Unauthenticated("Token is not yet valid") from e
            except jwt.exceptions.InvalidIssuerError as e:
                logger.warning("Invalid issuer: %s", e)
                raise Unauthenticated(f"Token issuer does not match expected issuer") from e
            except jwt.exceptions.InvalidAudienceError as e:
                logger.warning("Invalid audience: %s", e)
                raise Unauthenticated(f"Token audience does not match expected audience") from e
            except jwt.exceptions.InvalidAlgorithmError as e:
                logger.warning("Invalid algorithm: %s", e)
                raise Unauthenticated(f"Token algorithm not allowed: {e}") from e
            except jwt.exceptions.InvalidSignatureError as e:
                logger.warning("Invalid signature: %s", e)
                raise Unauthenticated("Token signature verification failed") from e
            except jwt.exceptions.DecodeError as e:
                # Malformed token, garbage input
                logger.warning("Token decode failed: %s", e)
                raise Unauthenticated(f"Token is malformed or invalid: {e}") from e
            except jwt.exceptions.InvalidTokenError as e:
                # Catch-all for other PyJWT validation errors
                logger.warning("Token validation failed: %s", e)
                raise Unauthenticated(f"Token validation failed: {e}") from e

            # Step 3: Extract student_id claim (AC-002)
            # A validly-signed token missing the claim is a clean 401, not a 500
            student_claim_name = self.settings.student_claim
            student_id = decoded.get(student_claim_name)

            if student_id is None or not isinstance(student_id, str) or student_id.strip() == "":
                logger.warning(
                    "Token missing or invalid '%s' claim. Token claims: %s",
                    student_claim_name,
                    list(decoded.keys())
                )
                raise Unauthenticated(
                    f"Token is missing required '{student_claim_name}' claim. "
                    "Ensure Keycloak client mapper is configured correctly."
                )

            logger.info(
                "Token validated successfully: student_id=%s, iss=%s",
                student_id,
                decoded.get("iss")
            )
            return student_id

        except Unauthenticated:
            # Re-raise Unauthenticated as-is (already logged above)
            raise
        except Exception as e:
            # Fail-closed: any unexpected error (network, infra, etc.) → Unauthenticated
            logger.error("Unexpected error during token validation: %s", e, exc_info=True)
            raise Unauthenticated(
                "Token validation failed due to an unexpected error. "
                "Please try again or contact support if the issue persists."
            ) from e


__all__ = ["KeycloakTokenResolver"]
