"""Upload-surface configuration (Lane 3 step 4, A-core).

Boot-time snapshot configuration, mirroring
:class:`study_tutor.voice.config.VoiceConfig`: parsed once from a mapping the
caller supplies, no import-time environment access.

Three environment variables, all optional:

``STUDY_TUTOR_UPLOAD_ENABLED``
    Truthy to make the B-stage boot path construct an ``UploadService`` (and
    therefore mount the routes). Absent/false means the surface does not exist
    in that process — the same existence gate voice uses.
``STUDY_TUTOR_UPLOAD_MAX_FILE_MB``
    Per-file size cap. Default 50.
``STUDY_TUTOR_UPLOAD_SUBJECT_QUOTA_MB``
    Per-subject staging quota. Default 500.

The staging root is NOT environment-driven: the build spec fixes it at
``data/uploads`` and both sides of the contract (server, worker) resolve it the
same way. It stays a constructor argument so tests can point at ``tmp_path``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

#: Bytes per megabyte, binary — the same convention as the voice recording cap.
BYTES_PER_MB: int = 1024 * 1024

#: Per-file cap in MB when the environment says nothing.
DEFAULT_MAX_FILE_MB: int = 50

#: Per-subject staging quota in MB when the environment says nothing.
DEFAULT_SUBJECT_QUOTA_MB: int = 500

#: Where the staging tree lives, relative to the repo/working root.
DEFAULT_STAGING_ROOT: Path = Path("data/uploads")

ENABLED_ENV: str = "STUDY_TUTOR_UPLOAD_ENABLED"
MAX_FILE_MB_ENV: str = "STUDY_TUTOR_UPLOAD_MAX_FILE_MB"
SUBJECT_QUOTA_MB_ENV: str = "STUDY_TUTOR_UPLOAD_SUBJECT_QUOTA_MB"

_TRUTHY = {"1", "true", "yes", "on"}
_FALSY = {"", "0", "false", "no", "off"}


def _parse_bool_flag(raw: str) -> bool:
    """Parse a flag string; raise ``ValueError`` on anything ambiguous."""
    value = raw.strip().lower()
    if value in _TRUTHY:
        return True
    if value in _FALSY:
        return False
    raise ValueError(
        f"{raw!r} is not a boolean flag (use true/false, 1/0, yes/no, on/off)"
    )


def _parse_positive_mb(raw: str, *, env_name: str, default: int) -> int:
    """Parse a megabyte override; raise ``ValueError`` on junk or non-positive."""
    value = raw.strip()
    if not value:
        return default
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(
            f"Failed to parse {env_name}: {raw!r} is not a whole number of "
            "megabytes"
        ) from exc
    if parsed <= 0:
        raise ValueError(
            f"Failed to parse {env_name}: {parsed} must be greater than zero"
        )
    return parsed


@dataclass(frozen=True)
class UploadConfig:
    """Resolved upload-surface limits.

    Attributes:
        enabled: Whether this process should mount the upload surface.
        max_file_bytes: Per-file size cap in bytes.
        subject_quota_bytes: Per-subject staging quota in bytes.
        staging_root: Root of the staging tree (``data/uploads`` by default).
    """

    enabled: bool = False
    max_file_bytes: int = DEFAULT_MAX_FILE_MB * BYTES_PER_MB
    subject_quota_bytes: int = DEFAULT_SUBJECT_QUOTA_MB * BYTES_PER_MB
    staging_root: Path = field(default=DEFAULT_STAGING_ROOT)

    @classmethod
    def from_env(
        cls,
        env: Mapping[str, str],
        *,
        staging_root: Path | None = None,
    ) -> UploadConfig:
        """Build a config from an environment mapping.

        Args:
            env: Mapping to read the three upload variables from (pass
                ``os.environ`` at boot; pass a dict in tests).
            staging_root: Override for the staging tree root. Defaults to
                :data:`DEFAULT_STAGING_ROOT`.

        Returns:
            The resolved :class:`UploadConfig`.

        Raises:
            ValueError: On a malformed flag or a non-positive/junk MB override,
                with the offending variable named.

        Examples:
            >>> UploadConfig.from_env({"STUDY_TUTOR_UPLOAD_MAX_FILE_MB": "5"})
            ... # doctest: +ELLIPSIS
            UploadConfig(enabled=False, max_file_bytes=5242880, ...)
        """
        try:
            enabled = _parse_bool_flag(env.get(ENABLED_ENV, ""))
        except ValueError as exc:
            raise ValueError(f"Failed to parse {ENABLED_ENV}: {exc}") from exc

        max_file_mb = _parse_positive_mb(
            env.get(MAX_FILE_MB_ENV, ""),
            env_name=MAX_FILE_MB_ENV,
            default=DEFAULT_MAX_FILE_MB,
        )
        subject_quota_mb = _parse_positive_mb(
            env.get(SUBJECT_QUOTA_MB_ENV, ""),
            env_name=SUBJECT_QUOTA_MB_ENV,
            default=DEFAULT_SUBJECT_QUOTA_MB,
        )

        return cls(
            enabled=enabled,
            max_file_bytes=max_file_mb * BYTES_PER_MB,
            subject_quota_bytes=subject_quota_mb * BYTES_PER_MB,
            staging_root=(
                DEFAULT_STAGING_ROOT if staging_root is None else Path(staging_root)
            ),
        )
