"""add issue_report to episode

Revision ID: f1b7d24c8e93
Revises: e7a2c93f5b64
Create Date: 2026-08-06 18:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = "f1b7d24c8e93"
down_revision = "e7a2c93f5b64"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "episode",
        sa.Column("issue_report", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )


def downgrade():
    op.drop_column("episode", "issue_report")
