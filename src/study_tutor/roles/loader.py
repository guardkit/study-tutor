"""Role manifest loader.

Reads ``roles/<role>/role.yaml`` at serve-time. Paths inside the manifest
are resolved **relative to the repo root** — the bash wrapper (SR-02)
guarantees CWD is the absolute repo path before ``study-tutor serve``
exec's, so ``Path.cwd()`` is the canonical anchor.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class RoleConfig:
    id: str
    name: str
    description: str
    player_prompt_path: Path
    criteria_path: Path | None

    def load_player_prompt(self) -> str:
        return self.player_prompt_path.read_text(encoding="utf-8")


def load_role(role: str, repo_root: Path | None = None) -> RoleConfig:
    """Load ``roles/<role>/role.yaml`` and resolve its paths.

    Args:
        role: Role identifier (e.g. ``"tutor"``).
        repo_root: Absolute repo root. Defaults to ``Path.cwd()`` — valid
            because the bash wrapper ``cd``'s here before exec'ing serve.

    Returns:
        Parsed ``RoleConfig`` with absolute paths resolved from ``repo_root``.
    """
    root = (repo_root or Path.cwd()).resolve()
    manifest_path = root / "roles" / role / "role.yaml"
    if not manifest_path.is_file():
        raise FileNotFoundError(
            f"Role manifest not found: {manifest_path}. "
            f"Ensure the bash wrapper cd's to the absolute repo root (SR-02)."
        )

    raw: dict[str, Any] = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    role_block = raw.get("role") or {}
    player_block = raw.get("player") or {}
    coach_block = raw.get("coach") or {}

    player_prompt_rel = player_block.get("prompt_file")
    if not player_prompt_rel:
        raise ValueError(
            f"role.yaml missing player.prompt_file: {manifest_path}"
        )

    criteria_rel = coach_block.get("criteria_file")

    return RoleConfig(
        id=role_block.get("id", role),
        name=role_block.get("name", role),
        description=role_block.get("description", ""),
        player_prompt_path=root / player_prompt_rel,
        criteria_path=(root / criteria_rel) if criteria_rel else None,
    )
