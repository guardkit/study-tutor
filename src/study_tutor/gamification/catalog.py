"""W1 achievement catalog (spec §4.5) — the 16 session-computable achievements.

Every id is a stable snake_case string; every name and XP value is
``docs/gamification/design.md`` §5 **verbatim** (spec non-negotiable rule 4 — a
divergence is a contract breach). These are the achievements computable from
session rows alone (streaks, session start times, banked XP totals, level):

* **Consistency** — First Steps (R4: first settled ≥2-min session), the six
  streak milestones (design §4.2 / §13.1), and Morning Star / Evening Scholar
  (R3: 5 *settled* sessions started before 09:00 / after 19:00 London).
* **Milestone** — First Century / Kilo / Five Kilo / Ten Kilo (total-XP
  thresholds) and Scholar / Master / Grandmaster (level thresholds).

``no_weak_spots`` is **deferred to the W2 tranche** (R5: needs the
confidence-history capture and its ≥5-studied-topics guard); it is deliberately
absent here.

The catalog **order is the cascade order** (design §13.1 D7): Consistency
(streak → then the start-window pair) → XP milestones → level milestones. The
engine iterates this order to a fixed point so a milestone's own XP can unlock a
further one deterministically (e.g. First Century's +50 re-checked at 150).

Each definition carries a pure ``progress(ctx)`` → ``(progress, target)`` and a
static ``hint`` template with ``{progress}`` / ``{target}`` interpolation, so the
near-achievement projection needs no per-call branching.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AchievementKind(str, Enum):
    """Which banked signal an achievement's progress reads (drives ``progress``)."""

    FIRST_SESSION = "first_session"
    STREAK = "streak"
    MORNING = "morning"
    EVENING = "evening"
    TOTAL_XP = "total_xp"
    LEVEL = "level"


@dataclass(frozen=True)
class AchievementContext:
    """The banked signals an achievement is evaluated against, *including* the
    session being settled (design §13.1 — all counts are post-this-session)."""

    #: Consistency: current streak length in London-local credit days.
    streak_days: int
    #: Milestone: total banked XP (session + achievement XP), post-cascade.
    total_xp: int
    #: Level number derived from ``total_xp`` (1–15).
    level: int
    #: Count of qualifying (≥2-min) sessions started before 09:00 London.
    morning_count: int
    #: Count of qualifying sessions started after 19:00 London.
    evening_count: int
    #: Count of qualifying (XP > 0) sessions overall — First Steps reads this.
    qualifying_sessions: int


@dataclass(frozen=True)
class AchievementDef:
    """One catalog entry. ``kind`` + ``target`` drive the pure progress read.

    ``description`` is the static "what earns it" line (design §5 criterion),
    surfaced in the ``near_achievements`` enrichment (contract §2.2.1); ``hint``
    is the progress-interpolated nudge.
    """

    id: str
    name: str
    xp: int
    kind: AchievementKind
    target: int
    description: str
    hint: str

    def progress(self, ctx: AchievementContext) -> int:
        """Current progress toward :attr:`target` for ``ctx`` (never above target
        for the boolean kinds so the hint reads sensibly)."""
        if self.kind is AchievementKind.FIRST_SESSION:
            return min(ctx.qualifying_sessions, self.target)
        if self.kind is AchievementKind.STREAK:
            return ctx.streak_days
        if self.kind is AchievementKind.MORNING:
            return ctx.morning_count
        if self.kind is AchievementKind.EVENING:
            return ctx.evening_count
        if self.kind is AchievementKind.TOTAL_XP:
            return ctx.total_xp
        # LEVEL
        return ctx.level

    def is_unlocked(self, ctx: AchievementContext) -> bool:
        """Whether the criterion is met (progress has reached the target)."""
        return self.progress(ctx) >= self.target

    def rendered_hint(self, ctx: AchievementContext) -> str:
        """The static hint with live ``{progress}`` / ``{target}`` interpolation."""
        return self.hint.format(progress=self.progress(ctx), target=self.target)


#: The catalog, in cascade order (design §13.1 D7): Consistency (First Steps →
#: streak milestones ascending → start-window pair) → XP milestones ascending →
#: level milestones ascending. Names + XP are design §5 verbatim.
CATALOG: tuple[AchievementDef, ...] = (
    # -- Consistency: First Steps + streak milestones (design §5.1) --------
    AchievementDef(
        "first_steps", "First Steps", 50, AchievementKind.FIRST_SESSION, 1,
        "Complete your first study session.",
        "Finish your first study session (2+ minutes) to get started.",
    ),
    AchievementDef(
        "three_day_run", "Three Day Run", 100, AchievementKind.STREAK, 3,
        "Study 3 days in a row.",
        "Study {progress}/{target} days in a row.",
    ),
    AchievementDef(
        "week_one", "Week One", 200, AchievementKind.STREAK, 7,
        "Study 7 days in a row.",
        "Study {progress}/{target} days in a row.",
    ),
    AchievementDef(
        "fortnight_force", "Fortnight Force", 400, AchievementKind.STREAK, 14,
        "Reach a 14-day study streak.",
        "Keep a {target}-day streak going — you're on {progress}.",
    ),
    AchievementDef(
        "thirty_days", "Thirty Days", 800, AchievementKind.STREAK, 30,
        "Reach a 30-day study streak.",
        "Keep a {target}-day streak going — you're on {progress}.",
    ),
    AchievementDef(
        "sixty_strong", "Sixty Strong", 1200, AchievementKind.STREAK, 60,
        "Reach a 60-day study streak.",
        "Keep a {target}-day streak going — you're on {progress}.",
    ),
    AchievementDef(
        "century", "Century", 2000, AchievementKind.STREAK, 100,
        "Reach a 100-day study streak.",
        "Keep a {target}-day streak going — you're on {progress}.",
    ),
    # -- Consistency: start-window pair (design §5.1, R3) ------------------
    AchievementDef(
        "morning_star", "Morning Star", 150, AchievementKind.MORNING, 5,
        "5 sessions started before 09:00.",
        "Start {progress}/{target} sessions before 09:00.",
    ),
    AchievementDef(
        "evening_scholar", "Evening Scholar", 150, AchievementKind.EVENING, 5,
        "5 sessions started after 19:00.",
        "Start {progress}/{target} sessions after 19:00.",
    ),
    # -- Milestone: total-XP thresholds (design §5.6) ---------------------
    AchievementDef(
        "first_century", "First Century", 50, AchievementKind.TOTAL_XP, 100,
        "Earn 100 XP in total.",
        "Earn {progress}/{target} XP.",
    ),
    AchievementDef(
        "kilo", "Kilo", 100, AchievementKind.TOTAL_XP, 1000,
        "Earn 1,000 XP in total.",
        "Earn {progress}/{target} XP.",
    ),
    AchievementDef(
        "five_kilo", "Five Kilo", 250, AchievementKind.TOTAL_XP, 5000,
        "Earn 5,000 XP in total.",
        "Earn {progress}/{target} XP.",
    ),
    AchievementDef(
        "ten_kilo", "Ten Kilo", 500, AchievementKind.TOTAL_XP, 10000,
        "Earn 10,000 XP in total.",
        "Earn {progress}/{target} XP.",
    ),
    # -- Milestone: level thresholds (design §5.6) ------------------------
    AchievementDef(
        "scholar", "Scholar", 300, AchievementKind.LEVEL, 6,
        "Reach Level 6.",
        "Reach level {target} (you're level {progress}).",
    ),
    AchievementDef(
        "master", "Master", 700, AchievementKind.LEVEL, 10,
        "Reach Level 10.",
        "Reach level {target} (you're level {progress}).",
    ),
    AchievementDef(
        "grandmaster", "Grandmaster", 2000, AchievementKind.LEVEL, 15,
        "Reach Level 15.",
        "Reach level {target} (you're level {progress}).",
    ),
)

#: Fast lookup by id (replay reads banked achievement rows → catalog name/xp).
CATALOG_BY_ID: dict[str, AchievementDef] = {a.id: a for a in CATALOG}

#: Catalog position by id — the deterministic sort key for the unlocked list and
#: the tie-break for near-achievement ordering (keeps live + replay identical).
CATALOG_ORDER: dict[str, int] = {a.id: i for i, a in enumerate(CATALOG)}


__all__ = [
    "CATALOG",
    "CATALOG_BY_ID",
    "CATALOG_ORDER",
    "AchievementContext",
    "AchievementDef",
    "AchievementKind",
]
