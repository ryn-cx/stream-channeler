"""record why an episode identifier is locked beside the lock itself

Revision ID: e62f4c8d31ab
Revises: d51e6b3a2c47
Create Date: 2026-08-08 09:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "e62f4c8d31ab"
down_revision = "d51e6b3a2c47"
branch_labels = None
depends_on = None


def upgrade():
    # The column said only that an identifier was settled, never on what
    # grounds, so there is nothing in it to carry over and it is replaced rather
    # than converted. Every episode goes back to unsettled and is settled again
    # by the next import or by a `User`.
    op.drop_column("episode", "episode_identifier_locked")
    # An earlier draft of this revision made the column an enum, so the type is
    # dropped if it is there rather than left behind on a database that ran it.
    op.execute("DROP TYPE IF EXISTS identifierlock")
    op.add_column(
        "episode",
        sa.Column(
            "episode_identifier_locked",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "episode",
        sa.Column("episode_identifier_note", sa.String(), nullable=True),
    )


def downgrade():
    op.drop_column("episode", "episode_identifier_note")
