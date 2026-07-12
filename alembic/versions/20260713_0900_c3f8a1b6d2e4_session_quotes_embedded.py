"""session_quotes_embedded

Revision ID: c3f8a1b6d2e4
Revises: b7d1e4f92a3c
Create Date: 2026-07-13 09:00:00.000000+00:00

FEAT Phase E (S-E4) / gamification-engine-and-adaptive-loop-spec §2.3 note,
scope §4.3: the third Alembic revision, adding the per-session embedded-quote
counter the W2 Growth tranche (Quote Champion / Quote Master, R8) reads.

``session.quotes_embedded INTEGER NOT NULL DEFAULT 0`` — the cumulative count of
corpus-hit quotations the deterministic quote verifier confirmed across a
session's turns (``append_turn`` accumulates the per-turn count). Modeled on the
existing ``session.xp_awarded`` per-session counter: NOT NULL DEFAULT 0 with a
``>= 0`` check, so every pre-existing row reads 0 after upgrade (honest — no
verifier signal was captured before this wave).

``schema_reference.sql`` is a living reference kept in sync by hand; ``alembic
upgrade head`` is the source of truth.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3f8a1b6d2e4'
down_revision: Union[str, None] = 'b7d1e4f92a3c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add session.quotes_embedded — the per-session embedded-quote counter."""
    op.add_column(
        'session',
        sa.Column(
            'quotes_embedded',
            sa.Integer(),
            nullable=False,
            server_default='0',
        ),
    )
    op.create_check_constraint(
        'session_quotes_embedded_check',
        'session',
        'quotes_embedded >= 0',
    )


def downgrade() -> None:
    """Reverse the quotes_embedded addition (constraint before column)."""
    op.drop_constraint(
        'session_quotes_embedded_check', 'session', type_='check'
    )
    op.drop_column('session', 'quotes_embedded')
