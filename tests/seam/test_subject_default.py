"""Seam test: the tutoring default subject is one source of truth (SUBJECT_DEFAULT).

Contract: one shared default subject; ``resume_if_active`` matches on
``(student, subject)``, so a divergent default silently forks the session and
defeats D8 cross-device pickup. Producer: TASK-VOX-R06 (FEAT-VOICE-004).
Documented in ``docs/design/contracts/SUBJECT_DEFAULT.md``.

The app leg is always asserted (the Dart file lives in this repo). The
fleet-gateway legs assert against the sibling checkout when present and
``pytest.skip`` cleanly when it is absent, so the default hermetic run stays
green anywhere.
"""

import pathlib
import re

import pytest

SHARED_DEFAULT_SUBJECT = "english"  # resolved value (ASSUM-001, 2026-07-07)

# tests/seam/<this file> -> parents[2] is the study-tutor repo root.
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_SIBLING_FLEET_GATEWAY = _REPO_ROOT.parent / "fleet-gateway"


@pytest.mark.seam
@pytest.mark.integration_contract("SUBJECT_DEFAULT")
def test_subject_default_is_single_source():
    """All consumers resolve to the same default subject string (``english``)."""
    # --- App leg (always present in this repo) -----------------------------
    home_screen = _REPO_ROOT / "app" / "lib" / "ui" / "home_screen.dart"
    dart = home_screen.read_text()
    assert re.search(r"""defaultSubject\s*=\s*['"]english['"]""", dart), (
        "app defaultSubject must be 'english' (app/lib/ui/home_screen.dart)"
    )

    # --- fleet-gateway legs (sibling checkout; skip cleanly if absent) ------
    if not _SIBLING_FLEET_GATEWAY.is_dir():
        pytest.skip("sibling fleet-gateway checkout not present — sibling legs skipped")

    subject_py = _SIBLING_FLEET_GATEWAY / "common" / "subject.py"
    if not subject_py.is_file():
        pytest.skip(f"fleet-gateway common/subject.py not found at {subject_py}")

    subject_src = subject_py.read_text()
    assert re.search(r"""DEFAULT_SUBJECT\s*=\s*['"]english['"]""", subject_src), (
        "fleet-gateway DEFAULT_SUBJECT must equal 'english' (common/subject.py)"
    )

    # Scholar persona consistency: an English tutor, not maths. The persona
    # instructions must reference English and must not name a rival default
    # subject. (The 'maths' vs 'math' British-spelling note is not a subject
    # default, so we assert on the AQA/English content, not raw substrings.)
    persona = (
        _SIBLING_FLEET_GATEWAY
        / "reachy"
        / "external_content"
        / "external_profiles"
        / "scholar"
        / "instructions.txt"
    )
    if persona.is_file():
        persona_text = persona.read_text().lower()
        assert "english" in persona_text, (
            "Scholar persona must be an English tutor consistent with "
            f"SUBJECT_DEFAULT={SHARED_DEFAULT_SUBJECT!r}"
        )


@pytest.mark.seam
@pytest.mark.integration_contract("SUBJECT_DEFAULT")
def test_backend_subject_constants_match_the_contract():
    """ADR-ARCH-032 D4: the backend's own copies of the default subject.

    ``session.service.SUBJECT_DEFAULT`` (boundary normalisation) and
    ``knowledge.retrieval.DEFAULT_SUBJECT`` (subject-keyed seams) are
    separate literals by layering design — this test is what keeps them
    from drifting apart or from the contract's one value.
    """
    from study_tutor.knowledge.retrieval import DEFAULT_SUBJECT
    from study_tutor.session.service import SUBJECT_DEFAULT

    assert SUBJECT_DEFAULT == SHARED_DEFAULT_SUBJECT
    assert DEFAULT_SUBJECT == SHARED_DEFAULT_SUBJECT
