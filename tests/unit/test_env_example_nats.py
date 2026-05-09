"""Regression tests for .env.example NATS fleet wiring (TASK-NATS-PH1-007).

These tests guard against Bug #3 — OPENAI_BASE_URL missing the /v1 suffix
causes langchain-openai to POST /chat/completions instead of
/v1/chat/completions and receive a 404. See
docs/reviews/REVIEW-NATS-FLEET-PATTERNS-2026-05-08.md Bug #3.

The Coach validation command from the task spec is::

    test -f .env.example && grep -qE '^OPENAI_BASE_URL=.*\\/v1$' .env.example

These tests automate that check (AC-002) plus the surrounding presence
guarantees (AC-001, AC-003) so a future edit cannot silently break the
operator-facing config.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# Repo root is two levels up from tests/unit/
REPO_ROOT = Path(__file__).resolve().parents[2]
ENV_EXAMPLE = REPO_ROOT / ".env.example"

# Variables required by TASK-NATS-PH1-007 scope block.
REQUIRED_VARS = (
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


@pytest.fixture(scope="module")
def env_example_text() -> str:
    assert ENV_EXAMPLE.is_file(), f".env.example missing at {ENV_EXAMPLE}"
    return ENV_EXAMPLE.read_text(encoding="utf-8")


def test_env_example_exists() -> None:
    """AC-001: `.env.example` exists at the repo root."""
    assert ENV_EXAMPLE.is_file()


@pytest.mark.parametrize("var", REQUIRED_VARS)
def test_env_example_contains_required_var(env_example_text: str, var: str) -> None:
    """AC-001: every NATS/LLM variable from the task scope is present.

    A line beginning with ``VAR=`` (value may be empty for credentials).
    """
    pattern = rf"(?m)^{re.escape(var)}="
    assert re.search(pattern, env_example_text), (
        f"{var}= line missing from .env.example"
    )


def test_openai_base_url_ends_with_v1(env_example_text: str) -> None:
    """AC-002: OPENAI_BASE_URL value must end in ``/v1`` (Bug #3 guard).

    Equivalent to the task's coach-validation grep:
        grep -qE '^OPENAI_BASE_URL=.*\\/v1$' .env.example
    """
    match = re.search(r"(?m)^OPENAI_BASE_URL=(.*)$", env_example_text)
    assert match, "OPENAI_BASE_URL line not found"
    value = match.group(1).strip()
    assert value.endswith("/v1"), (
        f"OPENAI_BASE_URL must end in '/v1' to avoid Bug #3 "
        f"(langchain-openai 404 on /chat/completions); got {value!r}"
    )


def test_bug_3_comment_immediately_above_openai_base_url(env_example_text: str) -> None:
    """AC-003: the Bug #3 explanatory comment sits directly above OPENAI_BASE_URL.

    Allow comment lines (and only comment lines) between the explanatory
    block and the OPENAI_BASE_URL= line so multi-line comments stay legal,
    but reject any blank line or non-comment content in between.
    """
    lines = env_example_text.splitlines()
    base_url_idx = next(
        (i for i, line in enumerate(lines) if line.startswith("OPENAI_BASE_URL=")),
        None,
    )
    assert base_url_idx is not None, "OPENAI_BASE_URL= line not found"

    # Walk upward over contiguous comment lines.
    cursor = base_url_idx - 1
    comment_block: list[str] = []
    while cursor >= 0 and lines[cursor].lstrip().startswith("#"):
        comment_block.insert(0, lines[cursor])
        cursor -= 1

    assert comment_block, "Expected a comment block immediately above OPENAI_BASE_URL"
    joined = "\n".join(comment_block)
    assert "/v1" in joined, "Bug #3 comment must mention the /v1 suffix"
    assert "Bug #3" in joined, (
        "Comment must explicitly reference Bug #3 for traceability"
    )
