"""Hermetic cover for the live-suite users surface.

`deploy/keycloak/provision-live-suite.sh` writes
`STUDY_TUTOR_LIVE_SUITE_USERS` as a comma list of usernames, deliberately
leaving passwords in `.env.deploy`. The contract module originally parsed the
value as a JSON username->password map, so sourcing the generated file alone
hard-failed with a JSONDecodeError and no live test could run.

These tests pin BOTH accepted shapes so the two halves cannot drift apart
again. No real credential appears here — the passwords are obvious fakes.
"""
from __future__ import annotations

import pytest

from tests.integration.test_keycloak_contract import _parse_live_suite_users

_USERS = "STUDY_TUTOR_LIVE_SUITE_USERS"


def test_unset_surface_is_empty_not_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(_USERS, raising=False)
    assert _parse_live_suite_users() == {}


def test_json_object_shape_is_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(_USERS, '{"lilymay": "not-a-real-password"}')
    assert _parse_live_suite_users() == {"lilymay": "not-a-real-password"}


def test_comma_list_resolves_passwords_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """The shape provision-live-suite.sh actually writes."""
    monkeypatch.setenv(_USERS, "lilymay,alex")
    monkeypatch.setenv("LILYMAY_PASSWORD", "fake-lilymay-pw")
    monkeypatch.setenv("ALEX_PASSWORD", "fake-alex-pw")
    assert _parse_live_suite_users() == {
        "lilymay": "fake-lilymay-pw",
        "alex": "fake-alex-pw",
    }


def test_single_username_no_commas(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default provisioning run writes exactly this."""
    monkeypatch.setenv(_USERS, "lilymay")
    monkeypatch.setenv("LILYMAY_PASSWORD", "fake-lilymay-pw")
    assert _parse_live_suite_users() == {"lilymay": "fake-lilymay-pw"}


def test_missing_password_names_the_variable_not_the_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(_USERS, "lilymay,alex")
    monkeypatch.setenv("LILYMAY_PASSWORD", "fake-lilymay-pw")
    monkeypatch.delenv("ALEX_PASSWORD", raising=False)
    with pytest.raises(ValueError) as exc:
        _parse_live_suite_users()
    message = str(exc.value)
    assert "ALEX_PASSWORD" in message
    assert "fake-lilymay-pw" not in message, "error text must never carry a value"


def test_malformed_json_raises_valueerror_not_jsondecodeerror(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(_USERS, '{"lilymay": ')
    with pytest.raises(ValueError, match="does not parse"):
        _parse_live_suite_users()


def test_json_array_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(_USERS, '["lilymay"]')
    with pytest.raises(ValueError, match="must be an object"):
        _parse_live_suite_users()
