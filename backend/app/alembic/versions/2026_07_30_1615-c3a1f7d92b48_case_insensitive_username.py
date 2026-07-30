"""case insensitive username

Revision ID: c3a1f7d92b48
Revises: 69aee69a8619
Create Date: 2026-07-30 16:15:02.114927

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = 'c3a1f7d92b48'
down_revision = '69aee69a8619'
branch_labels = None
depends_on = None


def upgrade():
    # Usernames were only unique case sensitively, so names that differ by case can
    # already exist. Keep the oldest row's username and suffix every other one with
    # part of its id.
    op.execute(
        """
        WITH ranked AS (
            SELECT
                id,
                row_number() OVER (
                    PARTITION BY lower(username) ORDER BY created_at NULLS LAST, id
                ) AS position
            FROM "user"
        )
        UPDATE "user" AS target
        SET username = target.username || '-' || left(target.id::text, 8)
        FROM ranked
        WHERE ranked.id = target.id AND ranked.position > 1
        """
    )
    op.drop_index(op.f('ix_user_username'), table_name='user')
    op.create_index(
        'ix_user_username_lower',
        'user',
        [sa.text('lower(username)')],
        unique=True,
    )


def downgrade():
    op.drop_index('ix_user_username_lower', table_name='user')
    op.create_index(op.f('ix_user_username'), 'user', ['username'], unique=True)
