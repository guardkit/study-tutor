"""Unit tests for :mod:`study_tutor.roles.registry` (TASK-NATS-PH1-003).

Covers the acceptance criteria from the task spec:

* AC-001: ``get_role("tutor")`` returns a non-None role descriptor.
* AC-002: ``get_role("tutor").tool_to_command`` returns the canonical
  4-key alias map exactly.
* AC-003: ``_ensure_roles_registered()`` is idempotent.
* AC-004: ``get_role("nonexistent")`` raises a clear, named exception
  (:class:`UnknownRoleError`).
* AC-005: registry round-trip, mapping integrity, and re-registration
  semantics.
"""

from __future__ import annotations

from typing import Generator

import pytest

from study_tutor.roles import registry
from study_tutor.roles.registry import (
    RoleEntry,
    UnknownRoleError,
    _ensure_roles_registered,
    get_role,
    register_role,
)


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _restore_registry_state() -> Generator[None, None, None]:
    """Snapshot and restore registry state around every test.

    The registry is module-global, so tests that register additional
    fake roles or flip the ``_ROLES_REGISTERED`` flag must not leak that
    state to the next test. Snapshot/restore is cheaper than a full
    registry rebuild.
    """
    snapshot = dict(registry._ROLE_REGISTRY)
    flag_snapshot = registry._ROLES_REGISTERED
    yield
    registry._ROLE_REGISTRY.clear()
    registry._ROLE_REGISTRY.update(snapshot)
    registry._ROLES_REGISTERED = flag_snapshot


# ---------------------------------------------------------------------------
# AC-001: get_role("tutor") returns a non-None descriptor
# ---------------------------------------------------------------------------


class TestTutorRoleRegistration:
    """The tutor role must be available for lookup after registry import."""

    def test_get_role_tutor_returns_non_none_descriptor(self) -> None:
        # AC-001
        role = get_role("tutor")
        assert role is not None
        assert isinstance(role, RoleEntry)
        assert role.name == "tutor"

    def test_get_role_tutor_after_explicit_ensure_call(self) -> None:
        # _ensure_roles_registered() should not change the result.
        _ensure_roles_registered()
        role = get_role("tutor")
        assert role.name == "tutor"


# ---------------------------------------------------------------------------
# AC-002: tool_to_command map is exactly the canonical 4-key dict
# ---------------------------------------------------------------------------


CANONICAL_TUTOR_TOOL_TO_COMMAND = {
    "tutor_start_session": "start_session",
    "tutor_turn": "tutor_turn",
    "tutor_session_status": "session_status",
    "tutor_session_end": "end_session",
}


class TestTutorToolToCommandMapping:
    """The canonical alias map (Bug #2 fix data)."""

    def test_tool_to_command_is_exactly_four_keys(self) -> None:
        # AC-002 (cardinality)
        role = get_role("tutor")
        assert len(role.tool_to_command) == 4

    def test_tool_to_command_matches_canonical_table(self) -> None:
        # AC-002 (content)
        role = get_role("tutor")
        assert dict(role.tool_to_command) == CANONICAL_TUTOR_TOOL_TO_COMMAND

    @pytest.mark.parametrize(
        "tool_name,canonical_command",
        sorted(CANONICAL_TUTOR_TOOL_TO_COMMAND.items()),
    )
    def test_each_canonical_alias_present(
        self, tool_name: str, canonical_command: str
    ) -> None:
        # AC-002 per-row regression guard — if any single mapping drifts,
        # the failing parametrize case names the offending key directly.
        role = get_role("tutor")
        assert role.tool_to_command[tool_name] == canonical_command

    def test_tool_to_command_is_read_only(self) -> None:
        # Mapping integrity (AC-005): consumers cannot mutate the
        # registered alias map by accident.
        role = get_role("tutor")
        with pytest.raises(TypeError):
            role.tool_to_command["new_tool"] = "new_command"  # type: ignore[index]


# ---------------------------------------------------------------------------
# AC-003: _ensure_roles_registered() is idempotent
# ---------------------------------------------------------------------------


class TestEnsureRolesRegisteredIdempotent:
    """Calling _ensure_roles_registered() repeatedly is a noop."""

    def test_double_call_does_not_raise(self) -> None:
        _ensure_roles_registered()
        _ensure_roles_registered()  # must not raise

    def test_double_call_does_not_duplicate_register(self) -> None:
        _ensure_roles_registered()
        snapshot = dict(registry._ROLE_REGISTRY)
        _ensure_roles_registered()
        _ensure_roles_registered()
        assert dict(registry._ROLE_REGISTRY) == snapshot

    def test_idempotent_after_flag_reset(self) -> None:
        # Even if the short-circuit boolean is reset (e.g. by tests
        # reaching into module state), re-running registration must
        # still leave the registry contents identical, because the
        # underlying register_role call is itself idempotent for
        # identical mappings.
        registry._ROLES_REGISTERED = False
        _ensure_roles_registered()
        first = dict(registry._ROLE_REGISTRY)
        registry._ROLES_REGISTERED = False
        _ensure_roles_registered()
        second = dict(registry._ROLE_REGISTRY)
        assert first == second
        # Identity-stable too — same RoleEntry object both times.
        assert first["tutor"] is second["tutor"]


# ---------------------------------------------------------------------------
# AC-004: unknown role lookup raises a clear, named exception
# ---------------------------------------------------------------------------


class TestUnknownRoleError:
    """get_role on an unregistered name surfaces UnknownRoleError."""

    def test_unknown_role_raises_unknown_role_error(self) -> None:
        # AC-004
        with pytest.raises(UnknownRoleError):
            get_role("nonexistent")

    def test_unknown_role_error_subclasses_keyerror(self) -> None:
        # KeyError compatibility: callers using the standard idiom
        # ``except KeyError:`` continue to work.
        assert issubclass(UnknownRoleError, KeyError)

    def test_unknown_role_error_message_names_role(self) -> None:
        with pytest.raises(UnknownRoleError) as excinfo:
            get_role("ghost-role")
        assert "ghost-role" in str(excinfo.value)

    def test_unknown_role_error_message_lists_registered(self) -> None:
        # Operators should be able to see which roles *are* registered
        # without dropping into a debugger.
        with pytest.raises(UnknownRoleError) as excinfo:
            get_role("ghost-role")
        assert "tutor" in str(excinfo.value)

    def test_unknown_role_error_carries_attributes(self) -> None:
        with pytest.raises(UnknownRoleError) as excinfo:
            get_role("ghost-role")
        assert excinfo.value.role_name == "ghost-role"
        assert "tutor" in excinfo.value.registered


# ---------------------------------------------------------------------------
# AC-005: registry round-trip + mapping integrity
# ---------------------------------------------------------------------------


class TestRegistryRoundTrip:
    """register_role + get_role round-trip + defensive copying."""

    def test_register_then_get_returns_same_entry(self) -> None:
        entry = register_role(
            "round-trip-role",
            {"alpha": "a", "beta": "b"},
        )
        looked_up = get_role("round-trip-role")
        assert looked_up is entry
        assert dict(looked_up.tool_to_command) == {"alpha": "a", "beta": "b"}

    def test_re_register_identical_mapping_returns_existing_entry(self) -> None:
        first = register_role("dup-role", {"x": "y"})
        second = register_role("dup-role", {"x": "y"})
        assert first is second

    def test_re_register_different_mapping_raises_value_error(self) -> None:
        register_role("conflict-role", {"x": "y"})
        with pytest.raises(ValueError, match="different tool_to_command"):
            register_role("conflict-role", {"x": "z"})

    def test_caller_mutation_does_not_leak_into_registry(self) -> None:
        # Mapping integrity (AC-005): if the caller hands us a dict and
        # then mutates it later, the registered entry must be unaffected.
        original = {"alpha": "a"}
        register_role("isolation-role", original)
        original["alpha"] = "MUTATED"
        original["new"] = "extra"
        looked_up = get_role("isolation-role")
        assert dict(looked_up.tool_to_command) == {"alpha": "a"}

    def test_role_entry_is_frozen_dataclass(self) -> None:
        entry = register_role("frozen-test", {})
        with pytest.raises(Exception):
            # frozen dataclass raises FrozenInstanceError (a subclass
            # of AttributeError); broad except keeps the assertion
            # robust to dataclass internals shifting.
            entry.name = "renamed"  # type: ignore[misc]
