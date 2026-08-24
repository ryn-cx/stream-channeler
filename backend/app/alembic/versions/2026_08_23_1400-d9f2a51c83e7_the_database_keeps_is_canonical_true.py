from alembic import op

revision = "d9f2a51c83e7"
down_revision = "c8e1f42a7d36"
branch_labels = None
depends_on = None

_LEVELS = (
    ("show", "showcanonicalshow", "show_id", "Show", "ShowCanonicalShow"),
    (
        "episode",
        "episodecanonicalepisode",
        "episode_id",
        "Episode",
        "EpisodeCanonicalEpisode",
    ),
)


def upgrade() -> None:
    for table, link_table, link_column, prefix, link_prefix in _LEVELS:
        op.execute(
            f"""
            UPDATE {table}
            SET is_canonical = NOT EXISTS (
                SELECT 1 FROM {link_table}
                WHERE {link_table}.{link_column} = {table}.id
            )
            WHERE is_canonical IS DISTINCT FROM NOT EXISTS (
                SELECT 1 FROM {link_table}
                WHERE {link_table}.{link_column} = {table}.id
            )
            """,
        )

        op.execute(
            f"""
            CREATE FUNCTION {table}_canonical_flag() RETURNS trigger AS $$
            BEGIN
                NEW.is_canonical := NOT EXISTS (
                    SELECT 1 FROM {link_table}
                    WHERE {link_table}.{link_column} = NEW.id
                );
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql
            """,
        )
        op.execute(
            f"""
            CREATE TRIGGER "{prefix}-canonical-flag"
            BEFORE INSERT OR UPDATE OF is_canonical ON {table}
            FOR EACH ROW EXECUTE FUNCTION {table}_canonical_flag()
            """,
        )

        op.execute(
            f"""
            CREATE FUNCTION {link_table}_canonical_flag() RETURNS trigger AS $$
            BEGIN
                IF TG_OP <> 'INSERT' THEN
                    UPDATE {table} SET is_canonical = is_canonical
                    WHERE id = OLD.{link_column};
                END IF;
                IF TG_OP <> 'DELETE' THEN
                    UPDATE {table} SET is_canonical = is_canonical
                    WHERE id = NEW.{link_column};
                END IF;
                RETURN NULL;
            END;
            $$ LANGUAGE plpgsql
            """,
        )
        op.execute(
            f"""
            CREATE TRIGGER "{link_prefix}-canonical-flag"
            AFTER INSERT OR UPDATE OR DELETE ON {link_table}
            FOR EACH ROW EXECUTE FUNCTION {link_table}_canonical_flag()
            """,
        )


def downgrade() -> None:
    for table, link_table, _link_column, prefix, link_prefix in _LEVELS:
        op.execute(f'DROP TRIGGER "{link_prefix}-canonical-flag" ON {link_table}')
        op.execute(f"DROP FUNCTION {link_table}_canonical_flag()")
        op.execute(f'DROP TRIGGER "{prefix}-canonical-flag" ON {table}')
        op.execute(f"DROP FUNCTION {table}_canonical_flag()")
