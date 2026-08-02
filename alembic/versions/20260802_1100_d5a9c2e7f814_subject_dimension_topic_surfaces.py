"""subject_dimension_topic_surfaces

Revision ID: d5a9c2e7f814
Revises: c3f8a1b6d2e4
Create Date: 2026-08-02 11:00:00.000000+00:00

Lane 1 step 2 (plan of record) / ADR-ARCH-032 / study-room-cosy-progression
§14 ("multi-subject is a schema-day-one concern, not a later port"): the
subject dimension lands on every EXISTING mastery/topic surface in one
revision. Whole-student totals (XP, streaks, level — the `session` +
`achievement` aggregates) stay unscoped by design; the future Study Room
tables (`coin_txn`, chest counters, chain definitions) inherit the
dimension from THEIR first migration per the same §14 note.

Following the initial revision's conventions (constraint names
``<table>_..._pkey``; server defaults for backfill-in-place):

1. ``topic_confidence.subject TEXT NOT NULL DEFAULT 'english'`` — and the
   primary key widens ``(student_id, topic_name)`` →
   ``(student_id, subject, topic_name)`` so the same topic name can carry
   an independent confidence per subject. Every pre-existing row is
   English (the store predates multi-subject), so the default IS the
   backfill.
2. ``topic_confidence_history.subject TEXT NOT NULL DEFAULT 'english'`` —
   append-only audit trail gains the same dimension.
3. ``misconception.subject TEXT NOT NULL DEFAULT 'english'`` — topic-keyed
   observations follow their topics.
4. ``achievement.subject TEXT NULL`` — deliberately NULLable and NOT in
   the primary key: W1 achievements are whole-student (NULL, sticky once
   ever), while subject-pack catalogs (the live English W2 catalog is the
   first instance) will stamp their subject when the per-subject catalog
   refactor lands (Lane 1 step 3). Existing rows stay NULL until that
   catalog work attributes them — attribution needs the catalog mapping,
   which lives in code, not here.

The server defaults are kept after backfill (not dropped): the store's
write paths stamp an explicit subject, and the default keeps any
not-yet-threaded writer honest (English) rather than failing or writing
NULL.

``schema_reference.sql`` is a living reference kept in sync by hand;
``alembic upgrade head`` is the source of truth.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5a9c2e7f814'
down_revision: Union[str, None] = 'c3f8a1b6d2e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. topic_confidence — subject joins the primary key.
    op.add_column(
        "topic_confidence",
        sa.Column(
            "subject",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'english'"),
        ),
    )
    op.drop_constraint(
        "topic_confidence_pkey", "topic_confidence", type_="primary"
    )
    op.create_primary_key(
        "topic_confidence_pkey",
        "topic_confidence",
        ["student_id", "subject", "topic_name"],
    )

    # 2. topic_confidence_history — audit rows carry their subject.
    op.add_column(
        "topic_confidence_history",
        sa.Column(
            "subject",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'english'"),
        ),
    )

    # 3. misconception — topic-keyed observations follow their topics.
    op.add_column(
        "misconception",
        sa.Column(
            "subject",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'english'"),
        ),
    )

    # 4. achievement — NULL = whole-student (W1); subject-pack rows stamp
    # theirs when the per-subject catalog refactor lands.
    op.add_column(
        "achievement",
        sa.Column("subject", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("achievement", "subject")
    op.drop_column("misconception", "subject")
    op.drop_column("topic_confidence_history", "subject")
    op.drop_constraint(
        "topic_confidence_pkey", "topic_confidence", type_="primary"
    )
    op.drop_column("topic_confidence", "subject")
    op.create_primary_key(
        "topic_confidence_pkey",
        "topic_confidence",
        ["student_id", "topic_name"],
    )
