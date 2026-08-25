from alembic import op

revision = "f4b9d27ea518"
down_revision = "e3a8c46b19f5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm"')
    op.execute(
        """
        CREATE INDEX "Episode-canonical-name-trigram-index"
        ON episode
        USING gist (name gist_trgm_ops)
        WHERE is_canonical IS TRUE AND name IS NOT NULL
        """,
    )


def downgrade() -> None:
    op.execute('DROP INDEX "Episode-canonical-name-trigram-index"')
