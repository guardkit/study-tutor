"""settlement_and_confidence_history

Revision ID: b7d1e4f92a3c
Revises: 3c7cd4bca034
Create Date: 2026-07-12 12:00:00.000000+00:00

FEAT Phase E (S-E1) / gamification-engine-and-adaptive-loop-spec §3: the second
Alembic revision ever, adding the settlement + confidence-history surface.

Adds, following the initial revision's conventions exactly (TIMESTAMPTZ via
``sa.TIMESTAMP(timezone=True)``, ``<table>_<col>_check`` / ``_fkey`` / ``_pkey``
constraint names, ``<table>_<purpose>_idx`` index names):

1. ``session.settled_at TIMESTAMPTZ NULL`` — the settlement work-queue marker
   (§4 finalize stamps it; the sweep picks up ``status='ended' AND
   settled_at IS NULL``). NULL for every pre-existing row after upgrade.
2. ``session.text_name TEXT NULL`` — plan-fact captured at start (S-E4); the
   §4.2 finalize RETURNING reads it back.
3. ``achievement.session_id TEXT NULL REFERENCES session`` — replay support
   (D1): the settling session that first unlocked the achievement.
4. ``topic_confidence_history`` — modeled on ``misconception``; written by
   settlement from day one (D2 — unbackfillable).

Plan-fact ``planned_aos``: NOT added. Per the S-R3 dated builder note (spec
§2.1), per-turn AO capture lands on the EXISTING ``session_turn.ao_scaffolded``
column, so ``session.aos_scaffolded`` keeps its coherent dual start/end role and
no distinct ``planned_aos`` session column is needed. See the extended S-R3 note
in the spec.

``schema_reference.sql`` is a living reference kept in sync by hand; ``alembic
upgrade head`` is the source of truth.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7d1e4f92a3c'
down_revision: Union[str, None] = '3c7cd4bca034'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add settlement markers, plan-fact text_name, and confidence history."""

    # 1. session.settled_at — settlement work-queue marker (NULL until settled).
    op.add_column(
        'session',
        sa.Column('settled_at', sa.TIMESTAMP(timezone=True), nullable=True),
    )

    # 2. session.text_name — plan-fact captured at start (S-E4).
    op.add_column(
        'session',
        sa.Column('text_name', sa.Text(), nullable=True),
    )

    # 3. achievement.session_id — replay support (D1); FK to session.
    op.add_column(
        'achievement',
        sa.Column('session_id', sa.Text(), nullable=True),
    )
    op.create_foreign_key(
        'achievement_session_id_fkey',
        'achievement',
        'session',
        ['session_id'],
        ['session_id'],
    )

    # 4. topic_confidence_history — modeled on misconception; settlement-written.
    op.create_table(
        'topic_confidence_history',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('student_id', sa.Text(), nullable=False),
        sa.Column('topic_name', sa.Text(), nullable=False),
        sa.Column('percentage', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Text(), nullable=True),
        sa.Column('recorded_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('source', sa.Text(), nullable=False),
        sa.CheckConstraint(
            'percentage BETWEEN 0 AND 100',
            name='topic_confidence_history_percentage_check'
        ),
        sa.ForeignKeyConstraint(
            ['student_id'],
            ['student.student_id'],
            name='topic_confidence_history_student_id_fkey',
            ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('id', name='topic_confidence_history_pkey')
    )
    op.create_index(
        'topic_confidence_history_recent_idx',
        'topic_confidence_history',
        ['student_id', sa.text('recorded_at DESC')]
    )


def downgrade() -> None:
    """Reverse the settlement + confidence-history additions.

    Returns to the first revision's schema (7 tables). Everything added in
    ``upgrade()`` is removed in FK-safe order: the new table and its index
    first, then the achievement FK + column, then the session columns.
    """
    # 4. Drop topic_confidence_history (index before table).
    op.drop_index(
        'topic_confidence_history_recent_idx',
        table_name='topic_confidence_history',
    )
    op.drop_table('topic_confidence_history')

    # 3. Drop achievement.session_id (FK before column).
    op.drop_constraint(
        'achievement_session_id_fkey', 'achievement', type_='foreignkey'
    )
    op.drop_column('achievement', 'session_id')

    # 2. Drop session.text_name.
    op.drop_column('session', 'text_name')

    # 1. Drop session.settled_at.
    op.drop_column('session', 'settled_at')
