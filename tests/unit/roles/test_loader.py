"""Unit tests for :class:`RoleConfig` (TASK-LCA-002 — coach-prompt support).

Covers the slice of behaviour added by TASK-LCA-002:

* :meth:`RoleConfig.load_coach_prompt` returns the file contents when
  the manifest declares ``coach.prompt_file`` and the file exists on
  disk.
* :meth:`load_coach_prompt` raises :class:`FileNotFoundError` when the
  manifest omits ``coach.prompt_file`` (``coach_prompt_path`` is
  ``None``) — the adapter surfaces this at construction time so the
  Phase-1 wiring fails loudly rather than silently.
* :meth:`load_coach_prompt` raises :class:`FileNotFoundError` when the
  manifest declares the path but the file is missing on disk.
* :func:`load_role` populates ``coach_prompt_path`` from
  ``coach.prompt_file`` (resolved against ``repo_root``) and leaves it
  ``None`` when absent.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from study_tutor.roles.loader import RoleConfig, load_role

pytestmark = pytest.mark.feat_lca


# ---------------------------------------------------------------------------
# load_coach_prompt
# ---------------------------------------------------------------------------


def test_load_coach_prompt_returns_file_contents(tmp_path: Path) -> None:
    coach_file = tmp_path / "coach_prompt.md"
    coach_file.write_text("COACH_BODY", encoding="utf-8")
    config = RoleConfig(
        id="tutor",
        name="Tutor",
        description="d",
        player_prompt_path=tmp_path / "player.md",
        criteria_path=None,
        coach_prompt_path=coach_file,
    )
    assert config.load_coach_prompt() == "COACH_BODY"


def test_load_coach_prompt_raises_when_path_unset(tmp_path: Path) -> None:
    config = RoleConfig(
        id="tutor",
        name="Tutor",
        description="d",
        player_prompt_path=tmp_path / "player.md",
        criteria_path=None,
        coach_prompt_path=None,
    )
    with pytest.raises(FileNotFoundError) as exc_info:
        config.load_coach_prompt()
    assert "coach.prompt_file" in str(exc_info.value)


def test_load_coach_prompt_raises_when_file_missing(tmp_path: Path) -> None:
    config = RoleConfig(
        id="tutor",
        name="Tutor",
        description="d",
        player_prompt_path=tmp_path / "player.md",
        criteria_path=None,
        coach_prompt_path=tmp_path / "missing.md",
    )
    with pytest.raises(FileNotFoundError) as exc_info:
        config.load_coach_prompt()
    assert "missing.md" in str(exc_info.value)


# ---------------------------------------------------------------------------
# load_role wiring of coach_prompt_path
# ---------------------------------------------------------------------------


def _write_manifest(repo_root: Path, manifest: dict[str, object]) -> Path:
    role_dir = repo_root / "roles" / "tutor"
    role_dir.mkdir(parents=True, exist_ok=True)
    (role_dir / "player.md").write_text("p", encoding="utf-8")
    manifest_path = role_dir / "role.yaml"
    manifest_path.write_text(yaml.safe_dump(manifest), encoding="utf-8")
    return manifest_path


def test_load_role_resolves_coach_prompt_path(tmp_path: Path) -> None:
    coach_path_rel = "roles/tutor/prompts/coach.md"
    (tmp_path / "roles" / "tutor" / "prompts").mkdir(parents=True)
    (tmp_path / coach_path_rel).write_text("COACH_BODY", encoding="utf-8")

    _write_manifest(
        tmp_path,
        {
            "role": {"id": "tutor", "name": "Tutor", "description": "d"},
            "player": {"prompt_file": "roles/tutor/player.md"},
            "coach": {"prompt_file": coach_path_rel},
        },
    )

    config = load_role("tutor", repo_root=tmp_path)
    assert config.coach_prompt_path == (tmp_path / coach_path_rel).resolve()
    assert config.load_coach_prompt() == "COACH_BODY"


def test_load_role_leaves_coach_prompt_path_none_when_absent(tmp_path: Path) -> None:
    _write_manifest(
        tmp_path,
        {
            "role": {"id": "tutor", "name": "Tutor", "description": "d"},
            "player": {"prompt_file": "roles/tutor/player.md"},
            "coach": {"criteria_file": "roles/tutor/criteria/definitions.yaml"},
        },
    )
    config = load_role("tutor", repo_root=tmp_path)
    assert config.coach_prompt_path is None
