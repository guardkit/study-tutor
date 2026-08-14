"""No live credential may sit in this repo (2026-08-14).

Ported from ``fleet-gateway/tests/test_no_live_credentials.py`` after the
rotation. The occasion: ``guardkit/study-tutor`` and
``guardkit/fleet-gateway`` are both PUBLIC, and a bearer that authenticated
as a 14-year-old against her own tutoring backend sat in both — in
fleet-gateway's history, and in study-tutor's HEAD across 34 files
(``.env.example``, the test suites, and the Flutter app's compiled-in
identity constant). Rotation fixed the value; this fixes the habit.

Three fences:

1. A retired credential must never reappear, in any file, including tests
   — fixtures shaped like real tokens are how the last one spread.
2. No live-shaped token (the ``st_`` + high-entropy form the replacements
   take) may appear anywhere. Real tokens live in the gitignored
   ``deploy/http/.env`` and in the operator's ``~/.config/study-tutor``.
3. Every ``*TOKEN*`` / ``*PASSWORD*`` value in ``.env.example`` must still
   look like a placeholder.

Deliberately NOT scanned: ``docs/`` and ``tasks/``, which are dated
records of what was true at the time, and the SHA-pinned contract
``docs/design/contracts/API-session-http-binding.md`` — its §5.1 table
still names a retired token, and editing it re-pins a frozen contract
(root CLAUDE.md: "additive or re-pin, never silent edits"). That re-pin is
flagged in the plan, not smuggled in here. Retired values are inert once
the rotation window closes; the fence that matters going forward is #2.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]

#: Values retired on 2026-08-14. Split so this file does not itself
#: contain the literal it bans (it would match its own fence).
RETIRED_CREDENTIALS = ("token-" "lilymay", "token-" "alex", "token-" "suite")

#: Directories whose contents are executable or deployable — the surfaces
#: where a credential is a credential rather than a historical note.
SCANNED_DIRS = ("src", "tests", "features", "app/lib", "app/test_live", "deploy")

#: The shape the live replacements take: ``st_`` plus a urlsafe-base64
#: body. Long enough that no ordinary identifier trips it.
LIVE_TOKEN_RE = re.compile(r"\bst_[A-Za-z0-9_-]{30,}")

PLACEHOLDER_MARKERS = ("<", ">", "your", "example", "changeme", "placeholder", "random")


def _tracked_files() -> list[Path]:
    """Git-tracked files only: what is actually published."""
    out = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [REPO_ROOT / name for name in out.split("\0") if name]


def _readable_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None  # binary asset (fonts, images, wavs)


def _in_scanned_dirs(path: Path) -> bool:
    rel = path.relative_to(REPO_ROOT).as_posix()
    return any(rel == d or rel.startswith(f"{d}/") for d in SCANNED_DIRS)


def test_no_retired_credential_in_executable_surfaces() -> None:
    """A rotated-out bearer must not survive as a test fixture."""
    offenders: list[str] = []
    for path in _tracked_files():
        if not _in_scanned_dirs(path) or path.resolve() == Path(__file__).resolve():
            continue
        text = _readable_text(path)
        if text is None:
            continue
        for retired in RETIRED_CREDENTIALS:
            if retired in text:
                rel = path.relative_to(REPO_ROOT)
                offenders.append(f"{rel}: {retired}")
    assert not offenders, (
        "Retired credentials found. Use a self-evidently fake fixture "
        "(test-token-student-a) — a real-looking token in a test is how the "
        "2026-08-14 leak spread:\n  " + "\n  ".join(offenders)
    )


def test_no_live_shaped_token_anywhere_in_the_repo() -> None:
    """The current tokens' own shape, banned repo-wide."""
    offenders: list[str] = []
    for path in _tracked_files():
        if path.resolve() == Path(__file__).resolve():
            continue
        text = _readable_text(path)
        if text is None:
            continue
        for match in LIVE_TOKEN_RE.finditer(text):
            rel = path.relative_to(REPO_ROOT)
            offenders.append(f"{rel}: {match.group()[:9]}… ({len(match.group())} chars)")
    assert not offenders, (
        "Live-shaped bearer(s) committed. Rotate them NOW (they are public "
        "the moment this pushes), then keep values in the gitignored "
        "deploy/http/.env:\n  " + "\n  ".join(offenders)
    )


@pytest.mark.parametrize("env_example", [REPO_ROOT / ".env.example"])
def test_env_example_secrets_are_placeholders(env_example: Path) -> None:
    """Every secret-ish value in .env.example must still be a placeholder."""
    offenders: list[str] = []
    for lineno, line in enumerate(env_example.read_text().splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        if not any(word in key.upper() for word in ("TOKEN", "PASSWORD", "SECRET")):
            continue
        value = value.strip()
        if not value:
            continue  # deliberately blank (e.g. a flag left unset)
        if not any(marker in value.lower() for marker in PLACEHOLDER_MARKERS):
            offenders.append(f"{env_example.name}:{lineno} {key}={value[:24]}…")
    assert not offenders, (
        ".env.example carries something that does not look like a "
        "placeholder:\n  " + "\n  ".join(offenders)
    )
