"""UploadConfig: defaults, the two env overrides, and loud parse failures."""

from __future__ import annotations

from pathlib import Path

import pytest

from study_tutor.ingest.config import (
    BYTES_PER_MB,
    DEFAULT_MAX_FILE_MB,
    DEFAULT_STAGING_ROOT,
    DEFAULT_SUBJECT_QUOTA_MB,
    ENABLED_ENV,
    MAX_FILE_MB_ENV,
    SUBJECT_QUOTA_MB_ENV,
    UploadConfig,
)


def test_defaults_are_the_spec_values() -> None:
    config = UploadConfig.from_env({})

    assert config.enabled is False
    assert DEFAULT_MAX_FILE_MB == 50
    assert DEFAULT_SUBJECT_QUOTA_MB == 500
    assert config.max_file_bytes == 50 * BYTES_PER_MB
    assert config.subject_quota_bytes == 500 * BYTES_PER_MB
    assert config.staging_root == DEFAULT_STAGING_ROOT
    assert DEFAULT_STAGING_ROOT == Path("data/uploads")


@pytest.mark.parametrize("raw", ["1", "true", "TRUE", "yes", "on"])
def test_enabled_truthy_forms(raw: str) -> None:
    assert UploadConfig.from_env({ENABLED_ENV: raw}).enabled is True


@pytest.mark.parametrize("raw", ["", "0", "false", "NO", "off"])
def test_enabled_falsy_forms(raw: str) -> None:
    assert UploadConfig.from_env({ENABLED_ENV: raw}).enabled is False


def test_enabled_rejects_ambiguous_value_naming_the_variable() -> None:
    with pytest.raises(ValueError) as exc:
        UploadConfig.from_env({ENABLED_ENV: "maybe"})

    assert ENABLED_ENV in str(exc.value)


def test_env_overrides_both_limits() -> None:
    config = UploadConfig.from_env(
        {MAX_FILE_MB_ENV: "5", SUBJECT_QUOTA_MB_ENV: "20"}
    )

    assert config.max_file_bytes == 5 * BYTES_PER_MB
    assert config.subject_quota_bytes == 20 * BYTES_PER_MB


@pytest.mark.parametrize("raw", ["nonsense", "5.5", "0", "-1"])
def test_bad_size_override_names_the_variable(raw: str) -> None:
    with pytest.raises(ValueError) as exc:
        UploadConfig.from_env({MAX_FILE_MB_ENV: raw})

    assert MAX_FILE_MB_ENV in str(exc.value)


def test_staging_root_override_is_explicit_not_environmental(tmp_path: Path) -> None:
    """The staging root is fixed by the spec; only a caller may move it."""
    config = UploadConfig.from_env({"STUDY_TUTOR_UPLOAD_DIR": "/somewhere/else"})
    assert config.staging_root == DEFAULT_STAGING_ROOT

    explicit = UploadConfig.from_env({}, staging_root=tmp_path)
    assert explicit.staging_root == tmp_path


def test_config_is_frozen() -> None:
    config = UploadConfig.from_env({})

    with pytest.raises(Exception):
        config.enabled = True  # type: ignore[misc]
