"""Structural validation of docker-compose.study-tutor.yml.

TASK-NATS-PH3-002 / FEAT-NATS — Build docker-compose.study-tutor.yml with
full env block (OPENAI_BASE_URL /v1).

Why structural-only?
--------------------
The acceptance criteria for TASK-NATS-PH3-002 include
``docker compose ... up -d`` against a running NATS server. That requires
a Docker daemon AND a running NATS instance — operator territory (the
GB10 runbook in TASK-NATS-PH3-004) and not reproducible inside the unit
test suite. What we verify here is the file-level contract that the
``compose up`` invocation depends on:

* The compose file is valid YAML and exposes a ``gcse-tutor`` service.
* The service references a buildable / runnable ``study-tutor:dev`` image.
* The env block is the FULL list spelled out in the task body — not a
  trimmed subset that omits the ``/v1`` suffix on ``OPENAI_BASE_URL``
  (Bug #3 regression guard) or drops the ``${VAR:?must-be-set}`` syntax
  on ``RICH_NATS_PASSWORD`` (so ``compose up`` fails loudly when the
  password is unset rather than starting with empty creds).

End-to-end ``docker compose config`` / ``docker compose up`` evidence
lives in the Phase-3 runbook (TASK-NATS-PH3-004) and the GB10 e2e smoke
(TASK-NATS-PH3-005). This module guards the file-level invariants so a
regression (e.g. someone drops ``/v1`` from the default, or replaces
``:?must-be-set`` with ``:-``) is caught fast and locally.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


PROJECT_ROOT = Path(__file__).resolve().parents[2]
COMPOSE_PATH = PROJECT_ROOT / "docker-compose.study-tutor.yml"

SERVICE_NAME = "gcse-tutor"


@pytest.fixture(scope="module")
def compose_text() -> str:
    """Load the compose file once per module.

    Raise a clear ``FileNotFoundError`` if the file is missing so the
    failure points at the actual problem (compose file absent) rather
    than surfacing as a confusing AttributeError further down.
    """
    if not COMPOSE_PATH.is_file():
        raise FileNotFoundError(
            f"Compose file not found at {COMPOSE_PATH}. "
            "TASK-NATS-PH3-002 requires docker-compose.study-tutor.yml at "
            "the project root."
        )
    return COMPOSE_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def compose_doc(compose_text: str) -> dict[str, Any]:
    """Parse the compose file as YAML.

    ``yaml.safe_load`` is sufficient — compose files do not need
    full-fidelity tag handling, and safe_load avoids arbitrary code
    execution from a malicious document.
    """
    doc = yaml.safe_load(compose_text)
    assert isinstance(doc, dict), (
        "Top level of docker-compose.study-tutor.yml must be a YAML "
        f"mapping; got {type(doc).__name__}."
    )
    return doc


@pytest.fixture(scope="module")
def tutor_service(compose_doc: dict[str, Any]) -> dict[str, Any]:
    """Resolve the gcse-tutor service mapping.

    All other tests in this module depend on this; isolating the lookup
    keeps assertion failures pinpointed (missing service vs malformed
    field).
    """
    services = compose_doc.get("services")
    assert isinstance(services, dict), (
        "docker-compose.study-tutor.yml must declare a top-level "
        "`services:` mapping."
    )
    service = services.get(SERVICE_NAME)
    assert isinstance(service, dict), (
        f"Compose file must declare a `{SERVICE_NAME}` service. The "
        f"acceptance criteria and the wrapper scripts (TASK-NATS-PH3-003) "
        f"refer to `{SERVICE_NAME}` by name."
    )
    return service


@pytest.fixture(scope="module")
def env_block(tutor_service: dict[str, Any]) -> dict[str, str]:
    """Resolve the service's environment mapping.

    Compose accepts both a list ("KEY=value") and a mapping form for the
    environment block. The task body specifies the mapping form, and
    parsing the list form into a dict here would mask a regression that
    swaps the two — so we assert the mapping form explicitly.
    """
    env = tutor_service.get("environment")
    assert isinstance(env, dict), (
        "`environment:` for the gcse-tutor service must be a YAML "
        "mapping (KEY: value), not the list form. The mapping form is "
        "what the task body specifies and what makes the regression "
        "tests below readable."
    )
    # Compose preserves scalar values as ints / floats when unquoted; we
    # coerce to str here so per-key regex checks below can run uniformly.
    return {key: str(value) for key, value in env.items()}


# ---------------------------------------------------------------------------
# Service-level shape
# ---------------------------------------------------------------------------


def test_compose_file_exists() -> None:
    """The compose file must live at the project root.

    The Coach validation invocations and the build wrapper script both
    assume ``docker-compose.study-tutor.yml`` is at the project root,
    not under docker/ or scripts/.
    """
    assert COMPOSE_PATH.is_file(), (
        f"Expected compose file at {COMPOSE_PATH}; not found."
    )


def test_service_uses_study_tutor_dev_image(tutor_service: dict[str, Any]) -> None:
    """The service must reference the ``study-tutor:dev`` image tag.

    The build wrapper (TASK-NATS-PH3-003) tags the image as
    ``study-tutor:dev``. Drift here means ``compose up`` either pulls
    from a registry (failing offline) or uses a stale tag.
    """
    image = tutor_service.get("image")
    assert image == "study-tutor:dev", (
        f"`{SERVICE_NAME}.image` must be `study-tutor:dev`; got {image!r}."
    )


def test_service_has_build_directive_with_named_context(
    tutor_service: dict[str, Any],
) -> None:
    """A ``build:`` directive must accompany the image tag.

    AC: "references study-tutor:dev (or builds it via build: directive
    pointing at the Dockerfile)". We require both: the image tag for
    fast subsequent runs, and the build block so a fresh checkout can
    ``compose up`` without a separate ``docker build`` step.

    The build block must declare the BuildKit named context for
    ``nats-core`` because the Dockerfile (TASK-NATS-PH3-001) uses
    ``COPY --from=nats-core``; without that, the build fails at the
    COPY step.
    """
    build = tutor_service.get("build")
    assert isinstance(build, dict), (
        "`gcse-tutor.build:` must be a mapping declaring context, "
        "dockerfile, and additional_contexts."
    )
    assert build.get("dockerfile") == "study-tutor/Dockerfile", (
        f"build.dockerfile must point at study-tutor/Dockerfile; got "
        f"{build.get('dockerfile')!r}."
    )
    additional = build.get("additional_contexts")
    assert isinstance(additional, dict), (
        "build.additional_contexts must be a mapping declaring the "
        "nats-core named context (the Dockerfile uses "
        "`COPY --from=nats-core ...`)."
    )
    assert "nats-core" in additional, (
        "build.additional_contexts must declare a `nats-core` entry so "
        "BuildKit can resolve `COPY --from=nats-core ...` in the "
        "Dockerfile."
    )


def test_extra_hosts_includes_host_gateway(tutor_service: dict[str, Any]) -> None:
    """``host.docker.internal`` must resolve to the host gateway.

    llama-swap (port 9000) and NATS (port 4222) typically run on the
    Docker host. Without ``host-gateway``, ``host.docker.internal`` does
    not resolve on Linux Docker, and every default URL in the env block
    breaks.
    """
    extra_hosts = tutor_service.get("extra_hosts")
    assert isinstance(extra_hosts, list), (
        "`extra_hosts:` must be a list (compose long form)."
    )
    assert "host.docker.internal:host-gateway" in extra_hosts, (
        "extra_hosts must include `host.docker.internal:host-gateway` so "
        "the container can reach llama-swap and NATS running on the "
        "Docker host."
    )


def test_restart_policy_is_unless_stopped(tutor_service: dict[str, Any]) -> None:
    """Restart policy must be ``unless-stopped``.

    Spec: "Restart policy: unless-stopped." This survives Docker daemon
    restarts but respects an explicit `docker compose down` from the
    operator, which matches how the GB10 stack is operated.
    """
    assert tutor_service.get("restart") == "unless-stopped", (
        "`gcse-tutor.restart` must be `unless-stopped`; got "
        f"{tutor_service.get('restart')!r}."
    )


# ---------------------------------------------------------------------------
# Environment block — full list contract
# ---------------------------------------------------------------------------


# The exact list of keys mandated by the task body. Maintained as a tuple
# (not a set) so the failure message includes the canonical ordering.
REQUIRED_ENV_KEYS: tuple[str, ...] = (
    "NATS_URL",
    "NATS_USER",
    "NATS_PASSWORD",
    "AGENT_ID",
    "OPENAI_BASE_URL",
    "LLM_BASE_URL",
    "LOCAL_MODEL",
    "OPENAI_API_KEY",
    "HEARTBEAT_INTERVAL_SECONDS",
)


def test_env_block_contains_all_required_keys(env_block: dict[str, str]) -> None:
    """Every key from the task's env block must be present.

    AC: "Environment block (full list, not just NATS)". Missing keys
    here mean the container starts but is missing config the runtime
    code expects (e.g. AGENT_ID drives the heartbeat subject).
    """
    missing = [key for key in REQUIRED_ENV_KEYS if key not in env_block]
    assert not missing, (
        f"environment block missing required keys: {missing}. The full "
        f"required list is: {list(REQUIRED_ENV_KEYS)}."
    )


def test_agent_id_is_gcse_tutor(env_block: dict[str, str]) -> None:
    """``AGENT_ID`` must be the literal string ``gcse-tutor``.

    The task body specifies a hardcoded value (not a template). The
    NATS subjects include the agent id, so a drift here desynchronises
    the heartbeat / command topics from the orchestrator's
    expectations.
    """
    assert env_block["AGENT_ID"] == "gcse-tutor", (
        f"AGENT_ID must be the literal `gcse-tutor`; got "
        f"{env_block['AGENT_ID']!r}."
    )


def test_heartbeat_interval_is_30_seconds(env_block: dict[str, str]) -> None:
    """``HEARTBEAT_INTERVAL_SECONDS`` must be 30.

    The task body specifies 30s as the cadence. A regression to a much
    larger value would silently degrade liveness detection by the
    orchestrator without any visible error.
    """
    assert env_block["HEARTBEAT_INTERVAL_SECONDS"] == "30", (
        "HEARTBEAT_INTERVAL_SECONDS must be 30; got "
        f"{env_block['HEARTBEAT_INTERVAL_SECONDS']!r}."
    )


# ---------------------------------------------------------------------------
# Bug #3 regression guard — OPENAI_BASE_URL must end with /v1
# ---------------------------------------------------------------------------


def test_openai_base_url_default_ends_with_v1(env_block: dict[str, str]) -> None:
    """The default value of ``OPENAI_BASE_URL`` must end with ``/v1``.

    Bug #3: langchain-openai's ChatOpenAI client constructs the chat
    completions URL by appending ``/chat/completions`` to
    ``OPENAI_BASE_URL``. If the base lacks ``/v1``, the POST goes to
    ``/chat/completions`` (404 from llama-swap) instead of
    ``/v1/chat/completions``. The 404 surfaces mid-``tutor_turn``, not
    at startup, so the only fast feedback is this regression test.
    """
    raw = env_block["OPENAI_BASE_URL"]
    # The compose interpolation form is `${VAR:-default}`; we extract
    # the default literal so the assertion is on the value the operator
    # gets when no override is set.
    match = re.match(r"\$\{[^:}]+:-(?P<default>[^}]+)\}$", raw)
    assert match, (
        "OPENAI_BASE_URL must use the `${VAR:-default}` interpolation "
        f"form so it can be overridden but defaults to /v1; got {raw!r}."
    )
    default = match.group("default")
    assert default.endswith("/v1"), (
        "OPENAI_BASE_URL default must end with `/v1` (Bug #3 regression "
        "guard — langchain-openai posts to <base>/chat/completions, so "
        "the base MUST be the /v1 path). Got default: "
        f"{default!r}."
    )


def test_openai_base_url_uses_overridable_var_name(env_block: dict[str, str]) -> None:
    """The override variable must be named ``TUTOR_OPENAI_BASE_URL``.

    The task body and the per-fleet env-prefix convention (TUTOR_*,
    RICH_*) require this name. Drift to a generic ``OPENAI_BASE_URL``
    override would clash with the specialist-agent stack's env when
    both run on the same host.
    """
    raw = env_block["OPENAI_BASE_URL"]
    assert raw.startswith("${TUTOR_OPENAI_BASE_URL:-"), (
        "OPENAI_BASE_URL must use the `${TUTOR_OPENAI_BASE_URL:-...}` "
        f"override prefix to namespace per-fleet config; got {raw!r}."
    )


# ---------------------------------------------------------------------------
# Required-or-fail-fast: RICH_NATS_PASSWORD
# ---------------------------------------------------------------------------


def test_nats_password_uses_required_interpolation(env_block: dict[str, str]) -> None:
    """``NATS_PASSWORD`` must use the ``${VAR:?msg}`` interpolation form.

    AC: "RICH_NATS_PASSWORD uses ${VAR:?must-be-set} syntax so the
    compose-up fails with a clear error if unset." This prevents the
    container starting with an empty password and silently failing
    NATS auth at first connect.
    """
    raw = env_block["NATS_PASSWORD"]
    pattern = re.compile(r"^\$\{RICH_NATS_PASSWORD:\?[^}]+\}$")
    assert pattern.match(raw), (
        "NATS_PASSWORD must use the `${RICH_NATS_PASSWORD:?<message>}` "
        "interpolation form so `compose up` fails fast when the password "
        f"is unset; got {raw!r}."
    )


# ---------------------------------------------------------------------------
# Other env-block defaults documented in the task body
# ---------------------------------------------------------------------------


def test_nats_url_default_targets_host_docker_internal(env_block: dict[str, str]) -> None:
    """``NATS_URL`` must default to ``host.docker.internal:4222``.

    The operator overrides ``NATS_HOST`` to point at a remote NATS
    (e.g. promaxgb10-41b1 over Tailscale); the default must be the
    local-development case so a fresh `compose up` works without
    extra env wiring.
    """
    raw = env_block["NATS_URL"]
    assert raw == "nats://${NATS_HOST:-host.docker.internal}:4222", (
        "NATS_URL must be `nats://${NATS_HOST:-host.docker.internal}:4222`; "
        f"got {raw!r}."
    )


def test_llm_base_url_default_has_no_v1_suffix(env_block: dict[str, str]) -> None:
    """``LLM_BASE_URL`` default must NOT end with ``/v1``.

    Counterpart to the OPENAI_BASE_URL test: ``LLM_BASE_URL`` is
    consumed by branches that hit llama.cpp / GBNF endpoints directly
    (no `/v1` in the path). Adding `/v1` here would break those code
    paths the same way OMITTING `/v1` from OPENAI_BASE_URL breaks
    langchain-openai. Keeping the two distinct is the whole point of
    declaring both variables.
    """
    raw = env_block["LLM_BASE_URL"]
    match = re.match(r"\$\{[^:}]+:-(?P<default>[^}]+)\}$", raw)
    assert match, (
        f"LLM_BASE_URL must use `${{VAR:-default}}` form; got {raw!r}."
    )
    default = match.group("default")
    assert not default.endswith("/v1"), (
        "LLM_BASE_URL default must NOT end with `/v1` — it is consumed "
        "by direct llama.cpp / GBNF code paths that expect the bare "
        f"host. Got default: {default!r}."
    )


def test_local_model_default_is_gemma4_tutor(env_block: dict[str, str]) -> None:
    """``LOCAL_MODEL`` must default to ``gemma4-tutor``.

    The model name is the llama-swap profile id; mismatch silently
    routes to the wrong checkpoint. Per the task body the default is
    ``gemma4-tutor``.
    """
    raw = env_block["LOCAL_MODEL"]
    assert raw == "${TUTOR_LOCAL_MODEL:-gemma4-tutor}", (
        "LOCAL_MODEL must be `${TUTOR_LOCAL_MODEL:-gemma4-tutor}`; got "
        f"{raw!r}."
    )


def test_openai_api_key_has_no_auth_sentinel_default(env_block: dict[str, str]) -> None:
    """``OPENAI_API_KEY`` must default to a no-auth sentinel value.

    llama-swap doesn't require auth, but langchain-openai refuses to
    construct a client with an empty / missing api_key. The task body
    specifies ``local-no-auth-required`` as the sentinel. Drift to
    empty string would re-introduce the construction error at runtime.
    """
    raw = env_block["OPENAI_API_KEY"]
    assert raw == "${TUTOR_OPENAI_API_KEY:-local-no-auth-required}", (
        "OPENAI_API_KEY must be "
        "`${TUTOR_OPENAI_API_KEY:-local-no-auth-required}`; got "
        f"{raw!r}."
    )


def test_nats_user_default_is_appmilla(env_block: dict[str, str]) -> None:
    """``NATS_USER`` must default to ``appmilla``.

    The default user matches the credential set provisioned by the
    nats-infrastructure repo for the home-lab stack. Drift here means
    the container starts but cannot authenticate without an explicit
    override.
    """
    raw = env_block["NATS_USER"]
    assert raw == "${RICH_NATS_USER:-appmilla}", (
        f"NATS_USER must be `${{RICH_NATS_USER:-appmilla}}`; got {raw!r}."
    )


# ---------------------------------------------------------------------------
# Negative assertions — guard against drift / scope creep
# ---------------------------------------------------------------------------


def test_compose_does_not_define_a_nats_service(compose_doc: dict[str, Any]) -> None:
    """This compose file MUST NOT declare a NATS service.

    Spec: "Do NOT define a NATS service in this compose file — NATS is
    provisioned elsewhere (nats-infrastructure/); this compose file
    only adds the tutor container." A stray `nats:` service would
    spawn a competing broker on the same host and confuse operators.
    """
    services = compose_doc.get("services") or {}
    forbidden = {"nats", "nats-server", "nats-core"}
    overlap = forbidden.intersection(services.keys())
    assert not overlap, (
        "docker-compose.study-tutor.yml must not declare NATS services "
        f"(found: {sorted(overlap)}). NATS is provisioned by the "
        "nats-infrastructure repo; this compose file only adds the "
        "tutor container."
    )


def test_no_healthcheck_block(tutor_service: dict[str, Any]) -> None:
    """Phase-3 spec defers healthcheck — heartbeat is the liveness signal.

    Spec: "Healthcheck: optional Phase 3+ — for now skip (the
    heartbeat *is* the liveness signal)." Adding a stray healthcheck
    here without coordinating with the heartbeat semantics would
    produce confusing dual-source liveness signals.
    """
    assert "healthcheck" not in tutor_service, (
        "Spec defers healthcheck; the NATS KV heartbeat is the "
        "liveness signal. Remove the `healthcheck:` block from "
        f"`{SERVICE_NAME}` or update the spec."
    )


def test_no_baked_secrets_in_environment(env_block: dict[str, str]) -> None:
    """No env-block value may bake a real-looking secret.

    Every secret-shaped value MUST come from a ``${VAR...}``
    interpolation. A literal API key or password committed to the
    compose file would leak when the file is checked in.
    """
    secret_keys = (
        "NATS_PASSWORD",
        "OPENAI_API_KEY",
    )
    for key in secret_keys:
        value = env_block[key]
        assert value.startswith("${") and value.endswith("}"), (
            f"`{key}` must be supplied via a ${{VAR...}} interpolation, "
            f"not a literal value; got {value!r}. Hardcoded secrets in "
            "compose files leak when the file is checked in."
        )
