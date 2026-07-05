"""Token-table auth layer for HTTP adapter (TASK-APP1-02).

Implements interim single-user auth via static token→student_id config table
(contract §3 derivation with config instead of Keycloak). Resolves Bearer tokens
from the Authorization header ONLY; enforces the unseeded-student guard (ASSUM-001)
before any store write.

This is the auth resolution layer used by every route. It raises
:exc:`~study_tutor.session.errors.Unauthenticated` at the transport boundary —
never by SessionService (see session/errors.py docstring).

No Keycloak/JWT imports — table lookup only (AC-005).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Protocol

from study_tutor.session.errors import Unauthenticated

logger = logging.getLogger(__name__)


class StudentStore(Protocol):
    """StudentStore protocol for the unseeded-student guard.

    The auth layer only needs to check student existence; it never writes.
    """

    async def student_exists(self, student_id: str) -> bool:
        """Check if the student has an identity row in StudentStore.

        Returns:
            True if student is seeded (has a student identity row), False otherwise.
        """
        ...


@dataclass(frozen=True)
class HTTPAuthConfig:
    """HTTP auth configuration loaded from environment.

    Attributes:
        token_to_student: Static token→student_id mapping from STUDY_TUTOR_HTTP_TOKENS.
        dev_reset: STUDY_TUTOR_HTTP_DEV_RESET flag (consumed by TASK-APP1-05 seed logic).
    """

    token_to_student: dict[str, str]
    dev_reset: bool

    @classmethod
    def from_env(cls, tokens_json: str, dev_reset: str) -> HTTPAuthConfig:
        """Parse HTTP auth config from environment variables.

        Args:
            tokens_json: STUDY_TUTOR_HTTP_TOKENS JSON string (e.g. '{"token-lilymay": "lilymay"}').
            dev_reset: STUDY_TUTOR_HTTP_DEV_RESET flag string ("true"/"false"/"1"/"0" etc).

        Returns:
            Parsed HTTPAuthConfig.

        Raises:
            ValueError: On malformed/empty/non-dict JSON input with clear error message.

        Examples:
            >>> config = HTTPAuthConfig.from_env(
            ...     tokens_json='{"token-lilymay": "lilymay"}',
            ...     dev_reset="false",
            ... )
            >>> config.token_to_student
            {'token-lilymay': 'lilymay'}
            >>> config.dev_reset
            False
        """
        # AC-001: Clear failure on empty input
        if not tokens_json or tokens_json.strip() == "":
            raise ValueError(
                "STUDY_TUTOR_HTTP_TOKENS cannot be empty. "
                "Provide a JSON object mapping tokens to student_ids, e.g. "
                '{"token-lilymay": "lilymay"}'
            )

        # AC-001: Clear failure on malformed JSON
        try:
            parsed = json.loads(tokens_json)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Failed to parse STUDY_TUTOR_HTTP_TOKENS as JSON: {e}. "
                "Expected a JSON object like "
                '{"token-lilymay": "lilymay"}'
            ) from e

        # AC-001: Clear failure when not a dict
        if not isinstance(parsed, dict):
            raise ValueError(
                "STUDY_TUTOR_HTTP_TOKENS must be a JSON object (dict), not "
                f"{type(parsed).__name__}. "
                'Expected format: {"token-lilymay": "lilymay"}'
            )

        # Parse dev_reset flag
        dev_reset_bool = _parse_bool_flag(dev_reset)

        return cls(token_to_student=parsed, dev_reset=dev_reset_bool)


def _parse_bool_flag(value: str) -> bool:
    """Parse a boolean flag from string.

    Args:
        value: String value ("true", "false", "1", "0", "yes", "no", etc).

    Returns:
        Boolean interpretation.
    """
    if not value:
        return False
    normalized = value.lower().strip()
    return normalized in {"true", "1", "yes", "y", "on"}


async def resolve_student_from_token(
    authorization_header: str | None,
    config: HTTPAuthConfig,
    student_store: StudentStore,
) -> str:
    """Resolve student_id from Bearer token with unseeded-student guard.

    This is the auth resolution function used by every HTTP route. It:
    1. Extracts the Bearer token from the Authorization header ONLY (AC-002)
    2. Looks up the token in the static config table (AC-004 — server-side truth)
    3. Checks the unseeded-student guard (AC-003 — refuses before any store write)

    Args:
        authorization_header: Value of the Authorization HTTP header (or None if missing).
        config: HTTP auth config with token→student_id mapping.
        student_store: StudentStore instance for the unseeded-student guard.

    Returns:
        The resolved student_id (server-side truth from the token table).

    Raises:
        Unauthenticated: On missing/malformed/unknown token or unseeded student.

    Examples:
        >>> config = HTTPAuthConfig(
        ...     token_to_student={"token-lilymay": "lilymay"},
        ...     dev_reset=False,
        ... )
        >>> # In async context:
        >>> student_id = await resolve_student_from_token(
        ...     authorization_header="Bearer token-lilymay",
        ...     config=config,
        ...     student_store=fake_store,
        ... )
        >>> student_id
        'lilymay'
    """
    # AC-002: Missing Authorization header
    if authorization_header is None:
        logger.warning("Auth failed: Missing Authorization header")
        raise Unauthenticated("Missing Authorization header")

    # AC-002: Extract Bearer token (header-only extraction)
    # Format: "Bearer <token>"
    parts = authorization_header.split(maxsplit=1)
    if len(parts) != 2 or parts[0] != "Bearer":
        logger.warning(
            "Auth failed: Authorization header must use Bearer scheme, got: %s",
            authorization_header[:50],  # Truncate for logs
        )
        raise Unauthenticated(
            "Authorization header must use Bearer scheme (format: 'Bearer <token>')"
        )

    token = parts[1]

    # AC-002: Look up token in config table (unknown token → Unauthenticated)
    student_id = config.token_to_student.get(token)
    if student_id is None:
        logger.warning(
            "Auth failed: Unknown token: %s", token[:20]
        )  # Truncate for logs
        raise Unauthenticated("Unknown token")

    # AC-004: The student_id from the token table is server-side truth
    # (client-asserted student_id in request body is ignored by the caller)

    # AC-003: Unseeded-student guard (ASSUM-001)
    # Refuse authenticated-but-unseeded students BEFORE any store write
    student_seeded = await student_store.student_exists(student_id)
    if not student_seeded:
        logger.warning(
            "Auth failed: Student %s is authenticated but not seeded (no StudentStore identity row)",
            student_id,
        )
        raise Unauthenticated(
            f"Student {student_id} is not seeded. "
            "StudentStore seed is required before session access."
        )

    logger.info("Auth success: Resolved student_id=%s from token", student_id)
    return student_id


__all__ = [
    "HTTPAuthConfig",
    "StudentStore",
    "resolve_student_from_token",
]
