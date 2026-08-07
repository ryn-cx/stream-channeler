"""put the media type in every TMDB identifier

Revision ID: d3b8e6c07a41
Revises: c8d5f2a94e17
Create Date: 2026-08-06 14:00:00.000000

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "d3b8e6c07a41"
down_revision = "c8d5f2a94e17"
branch_labels = None
depends_on = None


def upgrade():
    # TMDB numbers films, series, seasons and episodes in separate spaces, so a
    # bare "TMDB 550" made a film and a series that happen to share a number look
    # like the same media. The media type goes into the identifier to keep them
    # apart.

    # Which space a record's id came from is the media type of the show it
    # belongs to. The TMDB plugin stores that in its own show keys ("tv/1399"),
    # which is also where a show from another plugin reads it, by way of the TMDB
    # title it is linked to.
    op.execute(
        """
        CREATE TEMPORARY TABLE show_media_type AS
        SELECT
            show.id AS show_id,
            COALESCE(
                CASE
                    WHEN plugin.key = 'TMDB' THEN split_part(show.key, '/', 1)
                END,
                (
                    SELECT split_part(tmdb_show.key, '/', 1)
                    FROM show AS tmdb_show
                    JOIN source AS tmdb_source
                      ON tmdb_source.id = tmdb_show.source_id
                    JOIN plugin AS tmdb_plugin
                      ON tmdb_plugin.id = tmdb_source.plugin_id
                    WHERE tmdb_plugin.key = 'TMDB'
                      AND tmdb_show.tmdb_id = show.tmdb_id
                    LIMIT 1
                ),
                'tv'
            ) AS media_type
        FROM show
        JOIN source ON source.id = show.source_id
        JOIN plugin ON plugin.id = source.plugin_id
        WHERE show.tmdb_id IS NOT NULL
        """
    )

    # Only an identifier still in the old TMDB form is rewritten, so one a `User`
    # set for themselves is left as they set it.
    op.execute(
        """
        UPDATE show
        SET show_identifier = 'TMDB ' || show_media_type.media_type
                              || ' ' || show.tmdb_id
        FROM show_media_type
        WHERE show_media_type.show_id = show.id
          AND show.show_identifier = 'TMDB ' || show.tmdb_id
        """
    )
    op.execute(
        """
        UPDATE season
        SET season_identifier = 'TMDB ' || show_media_type.media_type
                                || ' ' || season.tmdb_id
        FROM show_media_type
        WHERE show_media_type.show_id = season.show_id
          AND season.tmdb_id IS NOT NULL
          AND season.season_identifier = 'TMDB ' || season.tmdb_id
        """
    )
    op.execute(
        """
        UPDATE episode
        SET episode_identifier = 'TMDB ' || show_media_type.media_type
                                 || ' ' || episode.tmdb_id
        FROM season, show_media_type
        WHERE season.id = episode.season_id
          AND show_media_type.show_id = season.show_id
          AND episode.tmdb_id IS NOT NULL
          AND episode.episode_identifier = 'TMDB ' || episode.tmdb_id
        """
    )

    # A watch keys on the identifier rather than on the episode, so it has to be
    # carried over with it or the watch stops counting.
    op.execute(
        """
        UPDATE watch
        SET episode_identifier = episode.episode_identifier
        FROM episode
        WHERE episode.id = watch.episode_id
          AND watch.episode_identifier <> episode.episode_identifier
        """
    )
    # A watch whose episode is gone has only the old identifier to go on, so it
    # follows whichever episode still carries the id that identifier was built
    # from. Every old identifier maps to exactly one new one, so no two watches
    # can be collapsed into the same key.
    op.execute(
        """
        UPDATE watch
        SET episode_identifier = mapping.new_identifier
        FROM (
            SELECT DISTINCT ON (old_identifier)
                'TMDB ' || episode.tmdb_id AS old_identifier,
                episode.episode_identifier AS new_identifier
            FROM episode
            WHERE episode.tmdb_id IS NOT NULL
              AND episode.episode_identifier LIKE 'TMDB %'
            ORDER BY old_identifier, episode.id
        ) AS mapping
        WHERE watch.episode_id IS NULL
          AND watch.episode_identifier = mapping.old_identifier
        """
    )

    op.execute("DROP TABLE show_media_type")


def downgrade():
    for table, column in (
        ("show", "show_identifier"),
        ("season", "season_identifier"),
        ("episode", "episode_identifier"),
        ("watch", "episode_identifier"),
    ):
        op.execute(
            f"""
            UPDATE {table}
            SET {column} = regexp_replace({column}, '^TMDB (movie|tv) ', 'TMDB ')
            WHERE {column} ~ '^TMDB (movie|tv) '
            """  # noqa: S608 - The table and column are from the tuple above.
        )
