"""In-process role registry for NATS fleet integration (TASK-NATS-PH1-003).

This is deliberately leaner than :mod:`study_tutor.roles.loader`'s
``RoleConfig``: ``RoleConfig`` is the YAML-backed, prompt-resolving runtime
view used at serve time, while :class:`RoleEntry` here holds only the
fleet-routing metadata (name + ``tool_to_command`` alias map) that the
NATS ``CommandRouter`` (TASK-NATS-PH1-004) needs.

Mirrors the shape of
``specialist_agent.roles.registry`` so the wider Jarvis Ship's Computer
fleet can grow uniformly. study-tutor only ships one role today
(``tutor``), but keeping the registration pattern means adding a second
role later requires no router-side changes.

The ``tool_to_command`` map is the linchpin of the **Bug #2 fix**
(regression-guarded by TASK-NATS-PH1-004): it lives here so router tests
can assert against it independently of the dispatcher's resolution logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from types import MappingProxyType
from typing import Mapping


class UnknownRoleError(KeyError):
    """Raised by :func:`get_role` when the requested role is not registered.

    Subclasses :class:`KeyError` so callers using the standard
    ``except KeyError`` idiom still catch it; the dedicated subclass lets
    new code be more specific without breaking that contract.
    """

    def __init__(self, role_name: str, registered: list[str]) -> None:
        self.role_name = role_name
        self.registered = registered
        # KeyError stringifies its first arg with repr(); pass a
        # human-readable message as a single arg so str(exc) reads cleanly.
        super().__init__(f"Unknown role {role_name!r}. Registered roles: {registered}")


@dataclass(frozen=True)
class RoleEntry:
    """Lightweight registry entry for fleet command routing.

    ``tool_to_command`` is exposed as a read-only :class:`MappingProxyType`
    so consumers cannot mutate the registered alias map by accident — the
    single-source-of-truth invariant the router relies on.
    """

    name: str
    tool_to_command: Mapping[str, str]


# Module-level state. Kept underscore-prefixed because callers should
# go through register_role / get_role / _ensure_roles_registered.
_ROLE_REGISTRY: dict[str, RoleEntry] = {}
_REGISTRATION_LOCK = Lock()
_ROLES_REGISTERED = False


def register_role(
    name: str,
    tool_to_command: Mapping[str, str],
) -> RoleEntry:
    """Register a role for fleet command routing.

    Idempotent when called with an identical ``tool_to_command`` mapping:
    re-registration returns the existing entry. Re-registering ``name``
    with a *different* mapping raises :class:`ValueError` — that means
    two modules disagree on the canonical alias map, which is a bug.

    Args:
        name: Role identifier (e.g. ``"tutor"``).
        tool_to_command: Mapping from MCP tool names (e.g.
            ``"tutor_start_session"``) to canonical internal command names
            (e.g. ``"start_session"``). Copied defensively so later mutation
            of the caller's dict does not leak into the registry.

    Returns:
        The :class:`RoleEntry` that ends up in the registry. Identity-stable
        across idempotent re-registrations of the same name+mapping.
    """
    snapshot = dict(tool_to_command)
    existing = _ROLE_REGISTRY.get(name)
    if existing is not None:
        if dict(existing.tool_to_command) == snapshot:
            return existing
        raise ValueError(
            f"Role {name!r} already registered with a different "
            f"tool_to_command mapping; refusing to overwrite. "
            f"Existing: {dict(existing.tool_to_command)!r}, "
            f"new: {snapshot!r}."
        )
    entry = RoleEntry(
        name=name,
        tool_to_command=MappingProxyType(snapshot),
    )
    _ROLE_REGISTRY[name] = entry
    return entry


def get_role(name: str) -> RoleEntry:
    """Look up a registered role by name.

    Triggers :func:`_ensure_roles_registered` first so the lookup
    succeeds even if the caller imported :mod:`study_tutor.roles.registry`
    directly without first touching the role sub-packages.

    Raises:
        UnknownRoleError: When ``name`` has not been registered.
    """
    _ensure_roles_registered()
    if name not in _ROLE_REGISTRY:
        raise UnknownRoleError(name, sorted(_ROLE_REGISTRY))
    return _ROLE_REGISTRY[name]


def _ensure_roles_registered() -> None:
    """Import every built-in role package once, populating the registry.

    Idempotent: a module-level boolean short-circuits subsequent calls,
    and the underlying ``register_role`` call is itself idempotent for
    identical mappings, so even if the boolean were bypassed the registry
    would not duplicate-register.

    A :class:`Lock` guards the import so concurrent first-call races
    (e.g. two threads each calling :func:`get_role` before any role
    package has been imported) cannot trigger the role module's
    top-level ``register_role`` twice.
    """
    global _ROLES_REGISTERED
    if _ROLES_REGISTERED:
        return
    with _REGISTRATION_LOCK:
        if _ROLES_REGISTERED:
            return
        # Importing this sub-package runs its top-level register_role(...).
        # Imported lazily to keep registry.py free of role-specific deps.
        from study_tutor.roles import tutor  # noqa: F401

        _ROLES_REGISTERED = True


__all__ = [
    "RoleEntry",
    "UnknownRoleError",
    "_ensure_roles_registered",
    "get_role",
    "register_role",
]
