"""Unit tests for OIDC configuration module.

TASK-KCA2-001: All tests are hermetic (env pinned via monkeypatch).
"""
from __future__ import annotations

import pytest

from study_tutor.http.oidc_config import OIDCSettings


class TestOIDCSettingsFromEnv:
    """Test OIDCSettings.from_env() parsing and defaults."""

    def test_table_mode_defaults(self, monkeypatch):
        """AC-002: mode defaults to 'table', student-claim to 'student_id', leeway to 60."""
        monkeypatch.delenv("STUDY_TUTOR_AUTH_MODE", raising=False)
        monkeypatch.delenv("STUDY_TUTOR_OIDC_ISSUER", raising=False)
        monkeypatch.delenv("STUDY_TUTOR_OIDC_AUDIENCE", raising=False)
        monkeypatch.delenv("STUDY_TUTOR_OIDC_JWKS_URL", raising=False)
        monkeypatch.delenv("STUDY_TUTOR_OIDC_STUDENT_CLAIM", raising=False)
        monkeypatch.delenv("STUDY_TUTOR_OIDC_LEEWAY", raising=False)

        settings = OIDCSettings.from_env()

        assert settings.auth_mode == "table"
        assert settings.student_claim == "student_id"
        assert settings.leeway == 60
        assert settings.issuer is None
        assert settings.audience is None
        assert settings.jwks_url is None

    def test_keycloak_mode_with_full_config(self, monkeypatch):
        """AC-002: Parse all env vars when mode is 'keycloak'."""
        monkeypatch.setenv("STUDY_TUTOR_AUTH_MODE", "keycloak")
        monkeypatch.setenv("STUDY_TUTOR_OIDC_ISSUER", "https://keycloak.example.com/realms/study")
        monkeypatch.setenv("STUDY_TUTOR_OIDC_AUDIENCE", "study-tutor-app")
        monkeypatch.setenv("STUDY_TUTOR_OIDC_JWKS_URL", "https://192.168.1.100:8443/realms/study/protocol/openid-connect/certs")
        monkeypatch.setenv("STUDY_TUTOR_OIDC_STUDENT_CLAIM", "student_uid")
        monkeypatch.setenv("STUDY_TUTOR_OIDC_LEEWAY", "120")

        settings = OIDCSettings.from_env()

        assert settings.auth_mode == "keycloak"
        assert settings.issuer == "https://keycloak.example.com/realms/study"
        assert settings.audience == "study-tutor-app"
        assert settings.jwks_url == "https://192.168.1.100:8443/realms/study/protocol/openid-connect/certs"
        assert settings.student_claim == "student_uid"
        assert settings.leeway == 120

    def test_keycloak_mode_with_minimal_config(self, monkeypatch):
        """AC-002: Optional vars use defaults even in keycloak mode."""
        monkeypatch.setenv("STUDY_TUTOR_AUTH_MODE", "keycloak")
        monkeypatch.setenv("STUDY_TUTOR_OIDC_ISSUER", "https://keycloak.example.com/realms/study")
        monkeypatch.setenv("STUDY_TUTOR_OIDC_AUDIENCE", "study-tutor-app")
        monkeypatch.delenv("STUDY_TUTOR_OIDC_JWKS_URL", raising=False)
        monkeypatch.delenv("STUDY_TUTOR_OIDC_STUDENT_CLAIM", raising=False)
        monkeypatch.delenv("STUDY_TUTOR_OIDC_LEEWAY", raising=False)

        settings = OIDCSettings.from_env()

        assert settings.auth_mode == "keycloak"
        assert settings.issuer == "https://keycloak.example.com/realms/study"
        assert settings.audience == "study-tutor-app"
        assert settings.jwks_url is None  # Will be derived from issuer
        assert settings.student_claim == "student_id"
        assert settings.leeway == 60


class TestOIDCSettingsValidate:
    """Test OIDCSettings.validate() validation logic."""

    def test_table_mode_valid(self, monkeypatch):
        """AC-003: table mode with no OIDC config is valid (returns empty list)."""
        monkeypatch.delenv("STUDY_TUTOR_AUTH_MODE", raising=False)
        monkeypatch.delenv("STUDY_TUTOR_OIDC_ISSUER", raising=False)
        monkeypatch.delenv("STUDY_TUTOR_OIDC_AUDIENCE", raising=False)

        settings = OIDCSettings.from_env()
        errors = settings.validate()

        assert errors == []

    def test_keycloak_mode_valid_with_full_config(self, monkeypatch):
        """AC-003: keycloak mode with issuer and audience is valid."""
        monkeypatch.setenv("STUDY_TUTOR_AUTH_MODE", "keycloak")
        monkeypatch.setenv("STUDY_TUTOR_OIDC_ISSUER", "https://keycloak.example.com/realms/study")
        monkeypatch.setenv("STUDY_TUTOR_OIDC_AUDIENCE", "study-tutor-app")

        settings = OIDCSettings.from_env()
        errors = settings.validate()

        assert errors == []

    def test_keycloak_mode_missing_issuer(self, monkeypatch):
        """AC-003: keycloak mode without issuer returns error message."""
        monkeypatch.setenv("STUDY_TUTOR_AUTH_MODE", "keycloak")
        monkeypatch.delenv("STUDY_TUTOR_OIDC_ISSUER", raising=False)
        monkeypatch.setenv("STUDY_TUTOR_OIDC_AUDIENCE", "study-tutor-app")

        settings = OIDCSettings.from_env()
        errors = settings.validate()

        assert len(errors) == 1
        assert "issuer" in errors[0].lower()
        assert "required" in errors[0].lower()

    def test_keycloak_mode_missing_audience(self, monkeypatch):
        """AC-003: keycloak mode without audience returns error message."""
        monkeypatch.setenv("STUDY_TUTOR_AUTH_MODE", "keycloak")
        monkeypatch.setenv("STUDY_TUTOR_OIDC_ISSUER", "https://keycloak.example.com/realms/study")
        monkeypatch.delenv("STUDY_TUTOR_OIDC_AUDIENCE", raising=False)

        settings = OIDCSettings.from_env()
        errors = settings.validate()

        assert len(errors) == 1
        assert "audience" in errors[0].lower()
        assert "required" in errors[0].lower()

    def test_keycloak_mode_missing_both(self, monkeypatch):
        """AC-003: keycloak mode without issuer or audience returns both errors."""
        monkeypatch.setenv("STUDY_TUTOR_AUTH_MODE", "keycloak")
        monkeypatch.delenv("STUDY_TUTOR_OIDC_ISSUER", raising=False)
        monkeypatch.delenv("STUDY_TUTOR_OIDC_AUDIENCE", raising=False)

        settings = OIDCSettings.from_env()
        errors = settings.validate()

        assert len(errors) == 2
        assert any("issuer" in e.lower() for e in errors)
        assert any("audience" in e.lower() for e in errors)

    def test_unknown_auth_mode(self, monkeypatch):
        """AC-003: unknown auth_mode value returns error message."""
        monkeypatch.setenv("STUDY_TUTOR_AUTH_MODE", "invalid-mode")

        settings = OIDCSettings.from_env()
        errors = settings.validate()

        assert len(errors) == 1
        assert "auth_mode" in errors[0].lower() or "invalid" in errors[0].lower()


class TestOIDCSettingsJWKSDerivation:
    """Test JWKS URL derivation logic."""

    def test_jwks_url_derived_from_issuer(self, monkeypatch):
        """AC-004: When JWKS URL is absent, derive from issuer."""
        monkeypatch.setenv("STUDY_TUTOR_AUTH_MODE", "keycloak")
        monkeypatch.setenv("STUDY_TUTOR_OIDC_ISSUER", "https://keycloak.example.com/realms/study")
        monkeypatch.setenv("STUDY_TUTOR_OIDC_AUDIENCE", "study-tutor-app")
        monkeypatch.delenv("STUDY_TUTOR_OIDC_JWKS_URL", raising=False)

        settings = OIDCSettings.from_env()

        # The effective JWKS URL should be derived from issuer
        effective_jwks = settings.get_effective_jwks_url()
        assert effective_jwks == "https://keycloak.example.com/realms/study/protocol/openid-connect/certs"
        # But the issuer used for validation should remain unchanged
        assert settings.issuer == "https://keycloak.example.com/realms/study"

    def test_jwks_url_override_without_changing_issuer(self, monkeypatch):
        """AC-004: When JWKS URL is present, use it but keep original issuer for validation."""
        monkeypatch.setenv("STUDY_TUTOR_AUTH_MODE", "keycloak")
        monkeypatch.setenv("STUDY_TUTOR_OIDC_ISSUER", "https://keycloak.example.com/realms/study")
        monkeypatch.setenv("STUDY_TUTOR_OIDC_AUDIENCE", "study-tutor-app")
        monkeypatch.setenv("STUDY_TUTOR_OIDC_JWKS_URL", "https://192.168.1.100:8443/realms/study/protocol/openid-connect/certs")

        settings = OIDCSettings.from_env()

        # The effective JWKS URL should be the override
        effective_jwks = settings.get_effective_jwks_url()
        assert effective_jwks == "https://192.168.1.100:8443/realms/study/protocol/openid-connect/certs"
        # But the issuer used for validation should remain the original
        assert settings.issuer == "https://keycloak.example.com/realms/study"

    def test_jwks_url_none_in_table_mode(self, monkeypatch):
        """AC-004: In table mode with no issuer, effective JWKS URL is None."""
        monkeypatch.delenv("STUDY_TUTOR_AUTH_MODE", raising=False)
        monkeypatch.delenv("STUDY_TUTOR_OIDC_ISSUER", raising=False)
        monkeypatch.delenv("STUDY_TUTOR_OIDC_JWKS_URL", raising=False)

        settings = OIDCSettings.from_env()

        effective_jwks = settings.get_effective_jwks_url()
        assert effective_jwks is None
