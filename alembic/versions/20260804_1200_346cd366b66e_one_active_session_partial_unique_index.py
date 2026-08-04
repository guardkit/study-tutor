"""one_active_session_partial_unique_index

Revision ID: 346cd366b66e
Revises: d5a9c2e7f814
Create Date: 2026-08-04 12:00:00.000000+00:00

The DB backstop for the ruled (b) start-fresh semantics (Rich, 2026-08-04;
known-issues "Per-turn text-following" tail → the double-active server
build): ``start_session(resume_if_active=False)`` now normalises in the
service to end-then-create, so at most one ``active`` session ever exists
per ``(student_id, subject)`` — the invariant D8 cross-device pickup
(``last_activity DESC LIMIT 1``) relies on. This partial unique index makes
that invariant STRUCTURAL: silent in normal flow (the service ends the
active match before inserting), it fires only on a pathological concurrent
double-start, where losing one INSERT beats minting a second active.

Pre-flight (mandated by the build handoff): the index creation FAILS if
existing double-actives are present. Check, and end the older strays by
status flip, BEFORE upgrading:

    SELECT student_id, subject, count(*) FROM session
    WHERE status='active' GROUP BY 1,2 HAVING count(*)>1;

Also check for pre-ADR-032 legacy rows (``subject=''`` is semantically
english but a distinct index key — the service sweep normalises them, this
index cannot): ``SELECT session_id FROM session WHERE status='active' AND
subject='';`` — end any found the same way.

``schema_reference.sql`` is a living reference kept in sync by hand;
``alembic upgrade head`` is the source of truth.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '346cd366b66e'
down_revision: Union[str, None] = 'd5a9c2e7f814'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "session_one_active_idx",
        "session",
        ["student_id", "subject"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )


def downgrade() -> None:
    op.drop_index("session_one_active_idx", table_name="session")
