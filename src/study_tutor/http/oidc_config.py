"""OIDC configuration settings for Keycloak authentication mode.

TASK-KCA2-001 / FEAT-AUTH-002: Frozen settings object that carries OIDC
configuration and validates completeness. Producer of the §4 OIDC_SETTINGS
contract (consumed by TASK-KCA2-003 and TASK-KCA2-004). Design ref: KC-D6.

This module is pure config — no PyJWT import here (the resolver owns that).
"""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class OIDCSettings:
    """OIDC configuration settings parsed from environment.

    Attributes:
        auth_mode: Authentication mode ('table' or 'keycloak')
        issuer: OIDC issuer URL (must match token 'iss' claim)
        audience: Expected token 'aud' claim
        jwks_url: JWKS fetch URL override (optional, derived from issuer if absent)
        student_claim: Token claim carrying the student ID
        leeway: Clock skew leeway in seconds for exp/nbf validation
    """

    auth_mode: str
    issuer: str | None
    audience: str | None
    jwks_url: str | None
    student_claim: str
    leeway: int

    @classmethod
    def from_env(cls) -> OIDCSettings:
        """Parse OIDC settings from environment variables.

        Environment variables read (hermetic contract - see task spec):
            STUDY_TUTOR_AUTH_MODE: 'table' | 'keycloak' (defaults to 'table')
            STUDY_TUTOR_OIDC_ISSUER: OIDC issuer URL (required in keycloak mode)
            STUDY_TUTOR_OIDC_AUDIENCE: Expected audience (required in keycloak mode)
            STUDY_TUTOR_OIDC_JWKS_URL: JWKS URL override (optional, derived if absent)
            STUDY_TUTOR_OIDC_STUDENT_CLAIM: Student ID claim name (defaults to 'student_id')
            STUDY_TUTOR_OIDC_LEEWAY: Clock skew leeway in seconds (defaults to '60')

        Returns:
            OIDCSettings instance with parsed configuration.
        """
        auth_mode = os.getenv("STUDY_TUTOR_AUTH_MODE", "table")
        issuer = os.getenv("STUDY_TUTOR_OIDC_ISSUER") or None
        audience = os.getenv("STUDY_TUTOR_OIDC_AUDIENCE") or None
        jwks_url = os.getenv("STUDY_TUTOR_OIDC_JWKS_URL") or None
        student_claim = os.getenv("STUDY_TUTOR_OIDC_STUDENT_CLAIM", "student_id")
        leeway_str = os.getenv("STUDY_TUTOR_OIDC_LEEWAY", "60")

        try:
            leeway = int(leeway_str)
        except ValueError:
            leeway = 60  # Fallback to default on invalid integer

        return cls(
            auth_mode=auth_mode,
            issuer=issuer,
            audience=audience,
            jwks_url=jwks_url,
            student_claim=student_claim,
            leeway=leeway,
        )

    def validate(self) -> list[str]:
        """Validate OIDC configuration completeness.

        Returns:
            List of error messages. Empty list indicates valid configuration.
            Caller (TASK-KCA2-004) turns non-empty list into boot SystemExit.

        Validation rules (ASSUM-002/005/007):
            - auth_mode must be 'table' or 'keycloak'
            - In keycloak mode: issuer and audience are required
            - In table mode: no OIDC validation needed
        """
        errors: list[str] = []

        # Validate auth_mode value
        if self.auth_mode not in ("table", "keycloak"):
            errors.append(
                f"Invalid STUDY_TUTOR_AUTH_MODE: '{self.auth_mode}'. "
                f"Must be 'table' or 'keycloak'."
            )

        # In keycloak mode, issuer and audience are required
        if self.auth_mode == "keycloak":
            if not self.issuer:
                errors.append(
                    "STUDY_TUTOR_OIDC_ISSUER is required when auth_mode is 'keycloak'."
                )
            if not self.audience:
                errors.append(
                    "STUDY_TUTOR_OIDC_AUDIENCE is required when auth_mode is 'keycloak'."
                )

        return errors

    def get_effective_jwks_url(self) -> str | None:
        """Get the effective JWKS URL for token verification.

        Returns:
            - Explicit jwks_url if set (KC-D2 tailnet-IP override)
            - Derived from issuer if issuer is set and jwks_url is not
            - None if no issuer (table mode or incomplete keycloak config)

        The issuer attribute remains unchanged for 'iss' claim validation.
        """
        if self.jwks_url:
            return self.jwks_url

        if self.issuer:
            # Derive standard OIDC JWKS endpoint from issuer
            return f"{self.issuer}/protocol/openid-connect/certs"

        return None
