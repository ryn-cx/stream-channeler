# TODO: Validate
import sqlalchemy as sa
from alembic import op

revision = "a1e7c93f52b4"
down_revision = "f4b93c208d71"
branch_labels = None
depends_on = None


# TODO: Validate
def upgrade() -> None:
    op.add_column(
        "titlecanonicaltitle",
        sa.Column(
            "manual_tmdb_link",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "episodecanonicalepisode",
        sa.Column(
            "manual_tmdb_link",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.execute(
        """
        UPDATE titlecanonicaltitle
        SET manual_tmdb_link = true
        WHERE note LIKE 'Manual: %'
        """,
    )
    op.execute(
        """
        UPDATE episodecanonicalepisode
        SET manual_tmdb_link = true
        WHERE note LIKE 'Manual: %'
        """,
    )
    op.alter_column("titlecanonicaltitle", "manual_tmdb_link", server_default=None)
    op.alter_column("episodecanonicalepisode", "manual_tmdb_link", server_default=None)


# TODO: Validate
def downgrade() -> None:
    op.drop_column("episodecanonicalepisode", "manual_tmdb_link")
    op.drop_column("titlecanonicaltitle", "manual_tmdb_link")
