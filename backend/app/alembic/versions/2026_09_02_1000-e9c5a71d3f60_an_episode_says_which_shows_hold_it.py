import sqlalchemy as sa
from alembic import op

revision = "e9c5a71d3f60"
down_revision = "d8b3c62fa914"
branch_labels = None
depends_on = None

_RESOLUTION = """
    SELECT DISTINCT
        episode.id AS episode_id,
        COALESCE(
            canonical_season.show_id,
            showcanonicalshow.canonical_show_id,
            CASE WHEN "show".is_canonical THEN "show".id END
        ) AS canonical_show_id
    FROM episode
    JOIN season ON season.id = episode.season_id
    JOIN "show" ON "show".id = season.show_id
    LEFT JOIN episodecanonicalepisode link ON link.episode_id = episode.id
    LEFT JOIN episode canonical_episode
        ON canonical_episode.id = link.canonical_episode_id
        AND canonical_episode.is_canonical
    LEFT JOIN season canonical_season
        ON canonical_season.id = canonical_episode.season_id
    LEFT JOIN showcanonicalshow
        ON showcanonicalshow.show_id = "show".id
        AND episode.is_canonical
"""


def upgrade() -> None:
    op.create_table(
        "episodecanonicalshow",
        sa.Column("episode_id", sa.Uuid(), nullable=False),
        sa.Column("canonical_show_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["episode_id"], ["episode.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["canonical_show_id"], ["show.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("episode_id", "canonical_show_id"),
    )
    op.create_index(
        "EpisodeCanonicalShow-canonical_show_id-index",
        "episodecanonicalshow",
        ["canonical_show_id", "episode_id"],
    )

    op.execute(
        f"""
        INSERT INTO episodecanonicalshow (episode_id, canonical_show_id)
        SELECT resolved.episode_id, resolved.canonical_show_id
        FROM ({_RESOLUTION}) AS resolved
        WHERE resolved.canonical_show_id IS NOT NULL
        ON CONFLICT DO NOTHING
        """,
    )

    op.execute(
        f"""
        CREATE FUNCTION refresh_episode_canonical_show(episode_ids uuid[])
        RETURNS void AS $$
        BEGIN
            DELETE FROM episodecanonicalshow
            WHERE episodecanonicalshow.episode_id = ANY(episode_ids);

            INSERT INTO episodecanonicalshow (episode_id, canonical_show_id)
            SELECT resolved.episode_id, resolved.canonical_show_id
            FROM ({_RESOLUTION} WHERE episode.id = ANY(episode_ids)) AS resolved
            WHERE resolved.canonical_show_id IS NOT NULL
            ON CONFLICT DO NOTHING;
        END;
        $$ LANGUAGE plpgsql
        """,
    )

    op.execute(
        """
        CREATE FUNCTION refresh_episode_canonical_show_of_show(target_show uuid)
        RETURNS void AS $$
        BEGIN
            PERFORM refresh_episode_canonical_show(
                ARRAY(
                    SELECT episode.id
                    FROM episode
                    JOIN season ON season.id = episode.season_id
                    WHERE season.show_id = target_show
                )
            );
        END;
        $$ LANGUAGE plpgsql
        """,
    )

    op.execute(
        """
        CREATE FUNCTION episode_canonical_show() RETURNS trigger AS $$
        BEGIN
            PERFORM refresh_episode_canonical_show(
                ARRAY(
                    SELECT NEW.id
                    UNION
                    SELECT link.episode_id
                    FROM episodecanonicalepisode link
                    WHERE link.canonical_episode_id = NEW.id
                )
            );
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql
        """,
    )
    op.execute(
        """
        CREATE TRIGGER "Episode-canonical-show"
        AFTER INSERT OR UPDATE OF season_id, is_canonical ON episode
        FOR EACH ROW EXECUTE FUNCTION episode_canonical_show()
        """,
    )

    op.execute(
        """
        CREATE FUNCTION episodecanonicalepisode_canonical_show()
        RETURNS trigger AS $$
        BEGIN
            IF TG_OP <> 'INSERT' THEN
                PERFORM refresh_episode_canonical_show(ARRAY[OLD.episode_id]);
            END IF;
            IF TG_OP <> 'DELETE' THEN
                PERFORM refresh_episode_canonical_show(ARRAY[NEW.episode_id]);
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql
        """,
    )
    op.execute(
        """
        CREATE TRIGGER "EpisodeCanonicalEpisode-canonical-show"
        AFTER INSERT OR UPDATE OR DELETE ON episodecanonicalepisode
        FOR EACH ROW EXECUTE FUNCTION episodecanonicalepisode_canonical_show()
        """,
    )

    op.execute(
        """
        CREATE FUNCTION season_canonical_show() RETURNS trigger AS $$
        BEGIN
            PERFORM refresh_episode_canonical_show(
                ARRAY(
                    SELECT episode.id FROM episode WHERE episode.season_id = NEW.id
                    UNION
                    SELECT link.episode_id
                    FROM episodecanonicalepisode link
                    JOIN episode ON episode.id = link.canonical_episode_id
                    WHERE episode.season_id = NEW.id
                )
            );
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql
        """,
    )
    op.execute(
        """
        CREATE TRIGGER "Season-canonical-show"
        AFTER UPDATE OF show_id ON season
        FOR EACH ROW EXECUTE FUNCTION season_canonical_show()
        """,
    )

    op.execute(
        """
        CREATE FUNCTION show_canonical_show() RETURNS trigger AS $$
        BEGIN
            PERFORM refresh_episode_canonical_show_of_show(NEW.id);
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql
        """,
    )
    op.execute(
        """
        CREATE TRIGGER "Show-canonical-show"
        AFTER UPDATE OF is_canonical ON "show"
        FOR EACH ROW EXECUTE FUNCTION show_canonical_show()
        """,
    )

    op.execute(
        """
        CREATE FUNCTION showcanonicalshow_canonical_show() RETURNS trigger AS $$
        BEGIN
            IF TG_OP <> 'INSERT' THEN
                PERFORM refresh_episode_canonical_show_of_show(OLD.show_id);
            END IF;
            IF TG_OP <> 'DELETE' THEN
                PERFORM refresh_episode_canonical_show_of_show(NEW.show_id);
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql
        """,
    )
    op.execute(
        """
        CREATE TRIGGER "ShowCanonicalShow-canonical-show"
        AFTER INSERT OR UPDATE OR DELETE ON showcanonicalshow
        FOR EACH ROW EXECUTE FUNCTION showcanonicalshow_canonical_show()
        """,
    )


def downgrade() -> None:
    op.execute('DROP TRIGGER "ShowCanonicalShow-canonical-show" ON showcanonicalshow')
    op.execute("DROP FUNCTION showcanonicalshow_canonical_show()")
    op.execute('DROP TRIGGER "Show-canonical-show" ON "show"')
    op.execute("DROP FUNCTION show_canonical_show()")
    op.execute('DROP TRIGGER "Season-canonical-show" ON season')
    op.execute("DROP FUNCTION season_canonical_show()")
    op.execute(
        'DROP TRIGGER "EpisodeCanonicalEpisode-canonical-show" '
        "ON episodecanonicalepisode",
    )
    op.execute("DROP FUNCTION episodecanonicalepisode_canonical_show()")
    op.execute('DROP TRIGGER "Episode-canonical-show" ON episode')
    op.execute("DROP FUNCTION episode_canonical_show()")
    op.execute("DROP FUNCTION refresh_episode_canonical_show_of_show(uuid)")
    op.execute("DROP FUNCTION refresh_episode_canonical_show(uuid[])")
    op.drop_index(
        "EpisodeCanonicalShow-canonical_show_id-index",
        table_name="episodecanonicalshow",
    )
    op.drop_table("episodecanonicalshow")
