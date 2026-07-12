"""Ratified economy + adaptive-loop constants (single source of truth).

This is the **clean constants home** the Phase-E economy module
(``gamification/economy.py``, spec §4.4) lives beside. It holds the small,
cross-cutting values the gamification engine and the adaptive-loop planner both
depend on, so live settlement and the historical backfill resolve identically
(``docs/gamification/design.md`` §13.1).

Every value here is ratified in ``design.md`` §13.1 (2026-07-12) — do not change
one without the matching ``design.md`` edit in the same commit.

- :data:`CONFIDENCE_BASELINE_PERCENTAGE` — first-seen topics are created at this
  mid-Developing value **before** the session delta is applied (R12).
- :data:`LONDON_TZ` — Europe/London is the calendar for **all** day/week/cutoff
  arithmetic in the economy and the §6.3 planner spacing/rotation windows (D6).
- :func:`london_date` — the London-local calendar date of a moment, the shared
  helper both the planner (§6.3 spacing/anti-repetition) and the Phase-E
  projection use so every day computation agrees.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

#: First-seen-topic confidence baseline (mid-Developing on the 0–100 store scale
#: / 0.50 on the design §6.1 0–1 scale). ``build_session_completion`` creates a
#: ``ConfidenceUpdate`` at this value **before** applying the session delta so a
#: brand-new topic is neither flagged Struggling nor near Mastered (design §13.1
#: R12). Ratified 2026-07-12.
CONFIDENCE_BASELINE_PERCENTAGE: int = 50

#: The calendar for every day/week/cutoff computation in the economy and the
#: §6.3 planner windows (design §13.1 D6). BST/GMT follows the London clock.
LONDON_TZ: ZoneInfo = ZoneInfo("Europe/London")


def london_date(moment: datetime) -> date:
    """Return the Europe/London-local calendar date of ``moment`` (D6).

    A naive ``datetime`` is interpreted as UTC (the store persists UTC-aware
    everywhere, but callers may hand a naive value defensively). The shared
    helper the planner spacing/anti-repetition windows and the Phase-E
    projection both use, so every day computation resolves on the same clock.
    """
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(LONDON_TZ).date()


__all__ = [
    "CONFIDENCE_BASELINE_PERCENTAGE",
    "LONDON_TZ",
    "london_date",
]
