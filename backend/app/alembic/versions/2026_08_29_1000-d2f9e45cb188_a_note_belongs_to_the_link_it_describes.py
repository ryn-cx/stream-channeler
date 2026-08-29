import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from alembic import op

revision = "d2f9e45cb188"
down_revision = "f1c8d34ba077"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "showcanonicalshow",
        sa.Column("note", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )
    op.execute(
        """
        UPDATE showcanonicalshow
        SET note = show.canonical_show_note
        FROM show
        WHERE show.id = showcanonicalshow.show_id
          AND show.canonical_show_note IS NOT NULL
        """,
    )
    op.drop_column("show", "canonical_show_note")


def downgrade() -> None:
    op.add_column(
        "show",
        sa.Column("canonical_show_note", sa.VARCHAR(), nullable=True),
    )
    op.execute(
        """
        UPDATE show
        SET canonical_show_note = link.note
        FROM (
            SELECT DISTINCT ON (show_id) show_id, note
            FROM showcanonicalshow
            WHERE note IS NOT NULL
            ORDER BY show_id, created_at
        ) AS link
        WHERE link.show_id = show.id
        """,
    )
    op.drop_column("showcanonicalshow", "note")
