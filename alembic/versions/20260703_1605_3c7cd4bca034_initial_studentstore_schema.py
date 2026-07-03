"""initial_studentstore_schema

Revision ID: 3c7cd4bca034
Revises:
Create Date: 2026-07-03 16:05:58.580121+00:00

TASK-SMP-02 / FEAT-SMP-001: First Alembic migration encoding the StudentStore schema.

This migration creates all 7 StudentStore tables (student, topic_confidence,
misconception, session, session_turn, achievement, quest) with their FKs,
CHECK constraints, composite PKs, and 3 named indexes, matching
src/study_tutor/knowledge/store/schema_reference.sql byte-for-byte.

Runbook gate G7: `alembic upgrade head` applies this migration to stand up
the learner-state schema on an empty Postgres database (no extensions).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '3c7cd4bca034'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the StudentStore schema: 7 tables + 3 named indexes."""

    # Table: student (parent of all child tables)
    op.create_table(
        'student',
        sa.Column('student_id', sa.Text(), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('year_group', sa.SmallInteger(), nullable=False),
        sa.Column('target_grade', sa.Text(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.CheckConstraint(
            'year_group BETWEEN 7 AND 13',
            name='student_year_group_check'
        ),
        sa.PrimaryKeyConstraint('student_id', name='student_pkey')
    )

    # Table: topic_confidence (composite PK, FK to student)
    op.create_table(
        'topic_confidence',
        sa.Column('student_id', sa.Text(), nullable=False),
        sa.Column('topic_name', sa.Text(), nullable=False),
        sa.Column('percentage', sa.SmallInteger(), nullable=False),
        sa.Column('band', sa.Text(), nullable=False),
        sa.Column('last_revised_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.CheckConstraint(
            'percentage BETWEEN 0 AND 100',
            name='topic_confidence_percentage_check'
        ),
        sa.ForeignKeyConstraint(
            ['student_id'],
            ['student.student_id'],
            name='topic_confidence_student_id_fkey',
            ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('student_id', 'topic_name', name='topic_confidence_pkey')
    )

    # Table: misconception (BIGSERIAL PK, FK to student, named index)
    op.create_table(
        'misconception',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('student_id', sa.Text(), nullable=False),
        sa.Column('topic_name', sa.Text(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('observed_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ['student_id'],
            ['student.student_id'],
            name='misconception_student_id_fkey',
            ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('id', name='misconception_pkey')
    )
    op.create_index(
        'misconception_recent_idx',
        'misconception',
        ['student_id', sa.text('observed_at DESC')]
    )

    # Table: session (FK to student, JSONB column, named index)
    op.create_table(
        'session',
        sa.Column('session_id', sa.Text(), nullable=False),
        sa.Column('student_id', sa.Text(), nullable=False),
        sa.Column('subject', sa.Text(), nullable=False),
        sa.Column('topic', sa.Text(), nullable=True),
        sa.Column('status', sa.Text(), nullable=False, server_default='active'),
        sa.Column('started_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('last_activity', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('turn_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('xp_awarded', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('aos_scaffolded', postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.CheckConstraint(
            'turn_count >= 0',
            name='session_turn_count_check'
        ),
        sa.CheckConstraint(
            'xp_awarded >= 0',
            name='session_xp_awarded_check'
        ),
        sa.ForeignKeyConstraint(
            ['student_id'],
            ['student.student_id'],
            name='session_student_id_fkey',
            ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('session_id', name='session_pkey')
    )
    op.create_index(
        'session_resume_idx',
        'session',
        ['student_id', 'status', sa.text('last_activity DESC')]
    )

    # Table: session_turn (composite PK, FK to session)
    op.create_table(
        'session_turn',
        sa.Column('session_id', sa.Text(), nullable=False),
        sa.Column('turn_index', sa.Integer(), nullable=False),
        sa.Column('role', sa.Text(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('ts', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('ao_scaffolded', sa.Text(), nullable=True),
        sa.CheckConstraint(
            'turn_index >= 0',
            name='session_turn_turn_index_check'
        ),
        sa.ForeignKeyConstraint(
            ['session_id'],
            ['session.session_id'],
            name='session_turn_session_id_fkey',
            ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('session_id', 'turn_index', name='session_turn_pkey')
    )

    # Table: achievement (composite PK, FK to student)
    op.create_table(
        'achievement',
        sa.Column('student_id', sa.Text(), nullable=False),
        sa.Column('achievement_id', sa.Text(), nullable=False),
        sa.Column('unlocked_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('xp_awarded', sa.Integer(), nullable=False),
        sa.CheckConstraint(
            'xp_awarded >= 0',
            name='achievement_xp_awarded_check'
        ),
        sa.ForeignKeyConstraint(
            ['student_id'],
            ['student.student_id'],
            name='achievement_student_id_fkey',
            ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('student_id', 'achievement_id', name='achievement_pkey')
    )

    # Table: quest (FK to student, named index)
    op.create_table(
        'quest',
        sa.Column('quest_id', sa.Text(), nullable=False),
        sa.Column('student_id', sa.Text(), nullable=False),
        sa.Column('shape', sa.Text(), nullable=False),
        sa.Column('status', sa.Text(), nullable=False, server_default='active'),
        sa.Column('started_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('expires_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('xp_reward', sa.Integer(), nullable=False),
        sa.CheckConstraint(
            'xp_reward >= 0',
            name='quest_xp_reward_check'
        ),
        sa.ForeignKeyConstraint(
            ['student_id'],
            ['student.student_id'],
            name='quest_student_id_fkey',
            ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('quest_id', name='quest_pkey')
    )
    op.create_index(
        'quest_active_idx',
        'quest',
        ['student_id', 'status']
    )


def downgrade() -> None:
    """Drop all StudentStore tables and indexes, returning to base.

    Tables are dropped in FK-safe order (children before parents).
    Named indexes are dropped explicitly before their tables.
    """
    # Drop indexes first
    op.drop_index('quest_active_idx', table_name='quest')
    op.drop_index('session_resume_idx', table_name='session')
    op.drop_index('misconception_recent_idx', table_name='misconception')

    # Drop tables in FK-safe order (children before parents)
    op.drop_table('session_turn')      # child of session
    op.drop_table('achievement')       # child of student
    op.drop_table('quest')             # child of student
    op.drop_table('misconception')     # child of student
    op.drop_table('topic_confidence')  # child of student
    op.drop_table('session')           # child of student
    op.drop_table('student')           # parent table
