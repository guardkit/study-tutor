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
    """Resolved role manifest (one per ``roles/<role>/role.yaml``).

    ``coach_prompt_path`` is optional so legacy manifests authored
    before TASK-LCA-002 (which only declared ``player.prompt_file``)
    continue to load. Adapters that depend on the Coach prompt
    (:class:`study_tutor.tutoring.adapters.llm_coach_adapter.LLMCoachAdapter`)
    call :meth:`load_coach_prompt` and surface a clear FileNotFoundError
    when the manifest omits the field.
    """

    id: str
    name: str
    description: str
    player_prompt_path: Path
    criteria_path: Path | None
    coach_prompt_path: Path | None = None

    def load_player_prompt(self) -> str:
        return self.player_prompt_path.read_text(encoding="utf-8")

    def load_coach_prompt(self) -> str:
        """Return the contents of ``coach.prompt_file`` resolved at load time.

        Mirrors :meth:`load_player_prompt`'s shape — string in, string out,
        no caching — so the Coach adapter has a single, greppable read site.
        Read at construction time of the Coach adapter (per TASK-LCA-002),
        not at every ``evaluate(...)`` call: the prompt is static for the
        lifetime of the process.

        Raises:
            FileNotFoundError: When ``role.yaml`` did not declare
                ``coach.prompt_file`` (``coach_prompt_path`` is ``None``)
                or when the resolved file is missing on disk. Both
                branches surface a message that names the missing path
                so the operator can fix the manifest deterministically.
        """
        if self.coach_prompt_path is None:
            raise FileNotFoundError(
                "Coach prompt not configured: role.yaml is missing "
                "'coach.prompt_file'. Add it (e.g. "
                "'roles/tutor/prompts/coach.md') so LLMCoachAdapter can "
                "load its system prompt at construction time."
            )
        if not self.coach_prompt_path.is_file():
            raise FileNotFoundError(
                f"Coach prompt file not found: {self.coach_prompt_path}. "
                f"Check role.yaml's coach.prompt_file resolves against "
                f"the repo root."
            )
        return self.coach_prompt_path.read_text(encoding="utf-8")


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
    coach_prompt_rel = coach_block.get("prompt_file")

    return RoleConfig(
        id=role_block.get("id", role),
        name=role_block.get("name", role),
        description=role_block.get("description", ""),
        player_prompt_path=root / player_prompt_rel,
        criteria_path=(root / criteria_rel) if criteria_rel else None,
        coach_prompt_path=(root / coach_prompt_rel) if coach_prompt_rel else None,
    )
