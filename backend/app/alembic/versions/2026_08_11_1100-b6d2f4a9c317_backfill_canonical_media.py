"""give every copy of a title, season and episode its canonical row

One canonical row per distinct identifier, at each of the three levels. Where
the identifier is one TMDB issued the row takes the media type and id off it as
real columns, and its metadata is read from the TMDB plugin's own copy, which is
the copy those values are supposed to come from. Where it is not, the identifier
belonged to a single website all along, so the row is that website's copy
promoted to standing for itself.

The identifiers are left in place and the pointers stay nullable. A later
revision makes them required and drops the identifiers, once the code writing
them has been changed over.

Revision ID: b6d2f4a9c317
Revises: a4c9e1f7b208
Create Date: 2026-08-11 11:00:00.000000

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "b6d2f4a9c317"
down_revision = "a4c9e1f7b208"
branch_labels = None
depends_on = None


# Only an identifier shaped exactly like this names a TMDB record. Anything else
# is a website's own, which is not a TMDB record with a bad id but one TMDB was
# never meant to have.
TMDB_SHAPE = "^TMDB (movie|tv) [0-9]+$"


def _tmdb_media_type(column):
    return f"CASE WHEN {column} ~ '{TMDB_SHAPE}' THEN split_part({column}, ' ', 2) END"


def _tmdb_id(column):
    return (
        f"CASE WHEN {column} ~ '{TMDB_SHAPE}' "
        f"THEN split_part({column}, ' ', 3)::integer END"
    )


def upgrade():
    # A mapping table rather than a correlated subquery so the generated uuid is
    # settled once and both the insert and the update read the same one.
    op.execute(
        """
        CREATE TEMPORARY TABLE canonical_show_map (
            show_identifier text PRIMARY KEY,
            canonical_show_id uuid NOT NULL
        )
        """,
    )
    op.execute(
        """
        INSERT INTO canonical_show_map (show_identifier, canonical_show_id)
        SELECT distinct_identifier.show_identifier, gen_random_uuid()
        FROM (SELECT DISTINCT show_identifier FROM show) AS distinct_identifier
        """,
    )
    # DISTINCT ON with the TMDB plugin sorted first: when a title is held by
    # several websites and TMDB, TMDB's copy is the one whose metadata stands.
    op.execute(
        f"""
        INSERT INTO canonicalshow (
            id, created_at, modified_at, tmdb_media_type, tmdb_id,
            name, media_type, description, image_url, icon
        )
        SELECT
            map.canonical_show_id, now(), now(),
            {_tmdb_media_type("chosen.show_identifier")},
            {_tmdb_id("chosen.show_identifier")},
            chosen.name, chosen.media_type, chosen.description,
            chosen.image_url, chosen.icon
        FROM canonical_show_map AS map
        JOIN (
            SELECT DISTINCT ON (show.show_identifier)
                show.show_identifier, show.name, show.media_type,
                show.description, show.image_url, show.icon
            FROM show
            JOIN source ON source.id = show.source_id
            JOIN plugin ON plugin.id = source.plugin_id
            ORDER BY show.show_identifier, (plugin.key = 'TMDB') DESC, show.id
        ) AS chosen ON chosen.show_identifier = map.show_identifier
        """,  # noqa: S608 - Built from the constants above, never from stored data.
    )
    op.execute(
        """
        UPDATE show SET canonical_show_id = map.canonical_show_id
        FROM canonical_show_map AS map
        WHERE map.show_identifier = show.show_identifier
        """,
    )

    op.execute(
        """
        CREATE TEMPORARY TABLE canonical_season_map (
            season_identifier text PRIMARY KEY,
            canonical_season_id uuid NOT NULL
        )
        """,
    )
    op.execute(
        """
        INSERT INTO canonical_season_map (season_identifier, canonical_season_id)
        SELECT distinct_identifier.season_identifier, gen_random_uuid()
        FROM (SELECT DISTINCT season_identifier FROM season) AS distinct_identifier
        """,
    )
    op.execute(
        f"""
        INSERT INTO canonicalseason (
            id, created_at, modified_at, canonical_show_id,
            tmdb_media_type, tmdb_id, name, season_number, image_url, sort_order
        )
        SELECT
            map.canonical_season_id, now(), now(), chosen.canonical_show_id,
            {_tmdb_media_type("chosen.season_identifier")},
            {_tmdb_id("chosen.season_identifier")},
            chosen.name, chosen.season_number, chosen.image_url, chosen.sort_order
        FROM canonical_season_map AS map
        JOIN (
            SELECT DISTINCT ON (season.season_identifier)
                season.season_identifier, season.name, season.season_number,
                season.image_url, season.sort_order, show.canonical_show_id
            FROM season
            JOIN show ON show.id = season.show_id
            JOIN source ON source.id = show.source_id
            JOIN plugin ON plugin.id = source.plugin_id
            ORDER BY season.season_identifier, (plugin.key = 'TMDB') DESC, season.id
        ) AS chosen ON chosen.season_identifier = map.season_identifier
        """,  # noqa: S608 - Built from the constants above, never from stored data.
    )
    op.execute(
        """
        UPDATE season SET canonical_season_id = map.canonical_season_id
        FROM canonical_season_map AS map
        WHERE map.season_identifier = season.season_identifier
        """,
    )

    op.execute(
        """
        CREATE TEMPORARY TABLE canonical_episode_map (
            episode_identifier text PRIMARY KEY,
            canonical_episode_id uuid NOT NULL
        )
        """,
    )
    op.execute(
        """
        INSERT INTO canonical_episode_map (episode_identifier, canonical_episode_id)
        SELECT distinct_identifier.episode_identifier, gen_random_uuid()
        FROM (SELECT DISTINCT episode_identifier FROM episode) AS distinct_identifier
        """,
    )
    # `url` is deliberately not carried over: it is the one field that says
    # where rather than what, and belongs to the copy alone.
    op.execute(
        f"""
        INSERT INTO canonicalepisode (
            id, created_at, modified_at, canonical_season_id,
            tmdb_media_type, tmdb_id, name, description, image_url,
            episode_number, duration, release_date, air_date, sort_order
        )
        SELECT
            map.canonical_episode_id, now(), now(), chosen.canonical_season_id,
            {_tmdb_media_type("chosen.episode_identifier")},
            {_tmdb_id("chosen.episode_identifier")},
            chosen.name, chosen.description, chosen.image_url,
            chosen.episode_number, chosen.duration, chosen.release_date,
            chosen.air_date, chosen.sort_order
        FROM canonical_episode_map AS map
        JOIN (
            SELECT DISTINCT ON (episode.episode_identifier)
                episode.episode_identifier, episode.name, episode.description,
                episode.image_url, episode.episode_number, episode.duration,
                episode.release_date, episode.air_date, episode.sort_order,
                season.canonical_season_id
            FROM episode
            JOIN season ON season.id = episode.season_id
            JOIN show ON show.id = season.show_id
            JOIN source ON source.id = show.source_id
            JOIN plugin ON plugin.id = source.plugin_id
            ORDER BY episode.episode_identifier, (plugin.key = 'TMDB') DESC, episode.id
        ) AS chosen ON chosen.episode_identifier = map.episode_identifier
        """,  # noqa: S608 - Built from the constants above, never from stored data.
    )
    op.execute(
        """
        UPDATE episode SET canonical_episode_id = map.canonical_episode_id
        FROM canonical_episode_map AS map
        WHERE map.episode_identifier = episode.episode_identifier
        """,
    )

    op.execute("DROP TABLE canonical_episode_map")
    op.execute("DROP TABLE canonical_season_map")
    op.execute("DROP TABLE canonical_show_map")


def downgrade():
    # The identifiers were never dropped, so unpicking this is only a matter of
    # letting go of the canonical rows.
    op.execute("UPDATE episode SET canonical_episode_id = NULL")
    op.execute("UPDATE season SET canonical_season_id = NULL")
    op.execute("UPDATE show SET canonical_show_id = NULL")
    op.execute("DELETE FROM canonicalepisode")
    op.execute("DELETE FROM canonicalseason")
    op.execute("DELETE FROM canonicalshow")
