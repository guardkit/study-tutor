"""Realm-as-code invariants (FEAT-AUTH-004 R1, 2026-08-15).

The defect this fences: the ``reachy-robot`` client shipped with a
``student_id`` mapper and NO audience mapper, while the server hard-pins
``aud`` (``auth_keycloak.py`` decodes with ``audience=settings.audience``).
A device-grant token would have validated on signature, issuer, expiry and
``student_id`` — and still 401'd. Found textually by the FEAT-AUTH-004 spec
lane; nobody hit it live only because no robot had ever tried the flow.

The invariant, stated once and enforced for every future client: a client
whose tokens carry ``student_id`` exists to call the study-tutor API, so it
MUST also stamp the audience the API demands. Hermetic — reads the realm
JSON, talks to nothing.
"""
from __future__ import annotations

import json
from pathlib import Path

REALM_PATH = (
    Path(__file__).resolve().parents[3]
    / "deploy"
    / "keycloak"
    / "realm"
    / "study-tutor-realm.json"
)

#: The audience the server validates (deployed STUDY_TUTOR_OIDC_AUDIENCE —
#: see deploy/http/docker-compose.keycloak.yml and the KC-G3 evidence).
EXPECTED_AUDIENCE = "study-tutor-app"


def _clients() -> list[dict]:
    return json.loads(REALM_PATH.read_text())["clients"]


def _mapper_names(client: dict) -> dict[str, dict]:
    return {m["name"]: m for m in client.get("protocolMappers", [])}


def test_every_student_id_client_also_stamps_the_audience() -> None:
    """No client may mint a token the server is guaranteed to reject."""
    offenders = []
    for client in _clients():
        mappers = _mapper_names(client)
        if "student_id" not in mappers:
            continue
        audience_mappers = [
            m
            for m in mappers.values()
            if m.get("protocolMapper") == "oidc-audience-mapper"
            and m.get("config", {}).get("included.client.audience")
            == EXPECTED_AUDIENCE
            and m.get("config", {}).get("access.token.claim") == "true"
        ]
        if not audience_mappers:
            offenders.append(client.get("clientId"))
    assert not offenders, (
        f"Clients {offenders} carry a student_id mapper but no "
        f"'{EXPECTED_AUDIENCE}' audience mapper on the access token — their "
        "tokens would pass every check except aud and 401 at the server. "
        "Copy the aud-study-tutor-app mapper block."
    )


def test_the_robot_client_specifically_has_the_mapper() -> None:
    """The R1 fix itself, pinned by name so a realm regeneration cannot
    silently drop it."""
    robot = next(c for c in _clients() if c.get("clientId") == "reachy-robot")
    mappers = _mapper_names(robot)

    assert "aud-study-tutor-app" in mappers, (
        "reachy-robot lost its audience mapper — the FEAT-AUTH-004 R1 fix"
    )
    config = mappers["aud-study-tutor-app"]["config"]
    assert config["included.client.audience"] == EXPECTED_AUDIENCE
    assert config["access.token.claim"] == "true"


def test_the_robot_client_still_has_the_device_grant() -> None:
    """The other half of what pairing needs — present since the client was
    added, pinned so the pair of preconditions travels together."""
    robot = next(c for c in _clients() if c.get("clientId") == "reachy-robot")
    assert (
        robot.get("attributes", {}).get("oauth2.device.authorization.grant.enabled")
        == "true"
    )
