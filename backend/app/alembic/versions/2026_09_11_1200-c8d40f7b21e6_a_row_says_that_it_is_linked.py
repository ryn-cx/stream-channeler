# TODO: Validate
"""A row says that it is linked, and the episode flag says it too."""

from typing import Any

from alembic import op

revision = "c8d40f7b21e6"
down_revision = "b6f1d4a09e37"
branch_labels = None
depends_on = None


OLD_WORDS: dict[str, Any] = {
    "flag_column": "is_unlinked",
    "flag_word": "unlinked",
    "negate": "",
    "unlinked_predicate": "is_unlinked IS TRUE",
    "flag_value": "NOT EXISTS",
    "episode_flag_word": "canonical",
    "episode_link_flag_prefix": "episodecanonicalepisode",
    "episode_link_flag_trigger": "EpisodeCanonicalEpisode",
}

NEW_WORDS: dict[str, Any] = {
    "flag_column": "is_linked",
    "flag_word": "linked",
    "negate": "NOT ",
    "unlinked_predicate": "is_linked IS FALSE",
    "flag_value": "EXISTS",
    "episode_flag_word": "linked",
    "episode_link_flag_prefix": "episodetmdbepisode",
    "episode_link_flag_trigger": "EpisodeTmdbEpisode",
}

PARTIAL_INDEXES = [
    ('"Episode-air_date-index"', "episode", "btree (air_date)", ""),
    (
        '"Episode-canonical-name-trigram-index"',
        "episode",
        "gist (name gist_trgm_ops)",
        " AND name IS NOT NULL",
    ),
    ('"Episode-duration-index"', "episode", "btree (duration)", ""),
    ('"Episode-episode_number-index"', "episode", "btree (episode_number)", ""),
    ('"Episode-name-index"', "episode", "btree (name)", ""),
    ('"Episode-sort_order-index"', "episode", "btree (sort_order)", ""),
    ('"Episode-unlinked-key-index"', "episode", "btree (key)", ""),
    ('"Title-media_type-index"', "title", "btree (media_type)", ""),
    ('"Title-name-index"', "title", "btree (name)", ""),
    ('"Title-unlinked-key-index"', "title", "btree (key)", ""),
]

FLAG_INDEXES = [
    ("Episode-is_unlinked-index", "Episode-is_linked-index"),
    ("Title-is_unlinked-index", "Title-is_linked-index"),
]


# TODO: Validate
def _resolution(words: dict[str, Any]) -> str:
    return f"""
        SELECT DISTINCT
            episode.id AS episode_id,
            COALESCE(
                tmdb_season.title_id,
                titletmdbtitle.tmdb_title_id,
                CASE WHEN {words["negate"]}title.{words["flag_column"]} THEN title.id END
            ) AS tmdb_title_id
        FROM episode
        JOIN season ON season.id = episode.season_id
        JOIN title ON title.id = season.title_id
        LEFT JOIN episodetmdbepisode link
            ON link.episode_id = episode.id
        LEFT JOIN episode tmdb_episode
            ON tmdb_episode.id = link.tmdb_episode_id
            AND {words["negate"]}tmdb_episode.{words["flag_column"]}
        LEFT JOIN season tmdb_season
            ON tmdb_season.id = tmdb_episode.season_id
        LEFT JOIN titletmdbtitle
            ON titletmdbtitle.title_id = title.id
            AND {words["negate"]}episode.{words["flag_column"]}
    """


# TODO: Validate
def _drop(words: dict[str, Any]) -> None:
    flag_word = words["flag_word"]
    episode_flag_word = words["episode_flag_word"]
    op.execute(
        f'DROP TRIGGER "{words["episode_link_flag_trigger"]}-{episode_flag_word}-flag"'
        " ON episodetmdbepisode",
    )
    op.execute(
        f"DROP FUNCTION {words['episode_link_flag_prefix']}_{episode_flag_word}_flag()",
    )
    op.execute(f'DROP TRIGGER "Episode-{episode_flag_word}-flag" ON episode')
    op.execute(f"DROP FUNCTION episode_{episode_flag_word}_flag()")
    op.execute(f'DROP TRIGGER "TitleTmdbTitle-{flag_word}-flag" ON titletmdbtitle')
    op.execute(f"DROP FUNCTION titletmdbtitle_{flag_word}_flag()")
    op.execute(f'DROP TRIGGER "Title-{flag_word}-flag" ON title')
    op.execute(f"DROP FUNCTION title_{flag_word}_flag()")
    op.execute('DROP TRIGGER "TitleTmdbTitle-tmdb-title" ON titletmdbtitle')
    op.execute("DROP FUNCTION titletmdbtitle_tmdb_title()")
    op.execute('DROP TRIGGER "Title-tmdb-title" ON title')
    op.execute("DROP FUNCTION title_tmdb_title()")
    op.execute('DROP TRIGGER "Season-tmdb-title" ON season')
    op.execute("DROP FUNCTION season_tmdb_title()")
    op.execute('DROP TRIGGER "EpisodeTmdbEpisode-tmdb-title" ON episodetmdbepisode')
    op.execute("DROP FUNCTION episodetmdbepisode_tmdb_title()")
    op.execute('DROP TRIGGER "Episode-tmdb-title" ON episode')
    op.execute("DROP FUNCTION episode_tmdb_title()")
    op.execute("DROP FUNCTION refresh_episode_tmdb_title_of_title(uuid)")
    op.execute("DROP FUNCTION refresh_episode_tmdb_title(uuid[])")
    for index, _table, _using, _extra in PARTIAL_INDEXES:
        op.execute(f"DROP INDEX {index}")


# TODO: Validate
def _create(words: dict[str, Any]) -> None:
    flag_column = words["flag_column"]
    flag_word = words["flag_word"]
    episode_flag_word = words["episode_flag_word"]
    for index, table, using, extra in PARTIAL_INDEXES:
        op.execute(
            f"CREATE INDEX {index} ON {table} USING {using}"
            f" WHERE {words['unlinked_predicate']}{extra}",
        )
    op.execute(
        f"""
        CREATE FUNCTION refresh_episode_tmdb_title(episode_ids uuid[])
        RETURNS void AS $$
        BEGIN
            DELETE FROM episodetmdbtitle
            WHERE episodetmdbtitle.episode_id = ANY(episode_ids);

            INSERT INTO episodetmdbtitle (episode_id, tmdb_title_id)
            SELECT resolved.episode_id, resolved.tmdb_title_id
            FROM (
                {_resolution(words)} WHERE episode.id = ANY(episode_ids)
            ) AS resolved
            WHERE resolved.tmdb_title_id IS NOT NULL
            ON CONFLICT DO NOTHING;
        END;
        $$ LANGUAGE plpgsql
        """,
    )
    op.execute(
        """
        CREATE FUNCTION refresh_episode_tmdb_title_of_title(target_title uuid)
        RETURNS void AS $$
        BEGIN
            PERFORM refresh_episode_tmdb_title(
                ARRAY(
                    SELECT episode.id
                    FROM episode
                    JOIN season ON season.id = episode.season_id
                    WHERE season.title_id = target_title
                )
            );
        END;
        $$ LANGUAGE plpgsql
        """,
    )
    op.execute(
        """
        CREATE FUNCTION episode_tmdb_title() RETURNS trigger AS $$
        BEGIN
            PERFORM refresh_episode_tmdb_title(
                ARRAY(
                    SELECT NEW.id
                    UNION
                    SELECT link.episode_id
                    FROM episodetmdbepisode link
                    WHERE link.tmdb_episode_id = NEW.id
                )
            );
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql
        """,
    )
    op.execute(
        f"""
        CREATE TRIGGER "Episode-tmdb-title"
        AFTER INSERT OR UPDATE OF season_id, {flag_column} ON episode
        FOR EACH ROW EXECUTE FUNCTION episode_tmdb_title()
        """,
    )
    op.execute(
        """
        CREATE FUNCTION episodetmdbepisode_tmdb_title() RETURNS trigger AS $$
        BEGIN
            IF TG_OP <> 'INSERT' THEN
                PERFORM refresh_episode_tmdb_title(ARRAY[OLD.episode_id]);
            END IF;
            IF TG_OP <> 'DELETE' THEN
                PERFORM refresh_episode_tmdb_title(ARRAY[NEW.episode_id]);
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql
        """,
    )
    op.execute(
        """
        CREATE TRIGGER "EpisodeTmdbEpisode-tmdb-title"
        AFTER INSERT OR UPDATE OR DELETE ON episodetmdbepisode
        FOR EACH ROW EXECUTE FUNCTION episodetmdbepisode_tmdb_title()
        """,
    )
    op.execute(
        """
        CREATE FUNCTION season_tmdb_title() RETURNS trigger AS $$
        BEGIN
            PERFORM refresh_episode_tmdb_title(
                ARRAY(
                    SELECT episode.id FROM episode WHERE episode.season_id = NEW.id
                    UNION
                    SELECT link.episode_id
                    FROM episodetmdbepisode link
                    JOIN episode ON episode.id = link.tmdb_episode_id
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
        CREATE TRIGGER "Season-tmdb-title"
        AFTER UPDATE OF title_id ON season
        FOR EACH ROW EXECUTE FUNCTION season_tmdb_title()
        """,
    )
    op.execute(
        """
        CREATE FUNCTION title_tmdb_title() RETURNS trigger AS $$
        BEGIN
            PERFORM refresh_episode_tmdb_title_of_title(NEW.id);
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql
        """,
    )
    op.execute(
        f"""
        CREATE TRIGGER "Title-tmdb-title"
        AFTER UPDATE OF {flag_column} ON title
        FOR EACH ROW EXECUTE FUNCTION title_tmdb_title()
        """,
    )
    op.execute(
        """
        CREATE FUNCTION titletmdbtitle_tmdb_title() RETURNS trigger AS $$
        BEGIN
            IF TG_OP <> 'INSERT' THEN
                PERFORM refresh_episode_tmdb_title_of_title(OLD.title_id);
            END IF;
            IF TG_OP <> 'DELETE' THEN
                PERFORM refresh_episode_tmdb_title_of_title(NEW.title_id);
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql
        """,
    )
    op.execute(
        """
        CREATE TRIGGER "TitleTmdbTitle-tmdb-title"
        AFTER INSERT OR UPDATE OR DELETE ON titletmdbtitle
        FOR EACH ROW EXECUTE FUNCTION titletmdbtitle_tmdb_title()
        """,
    )
    op.execute(
        f"""
        CREATE FUNCTION title_{flag_word}_flag() RETURNS trigger AS $$
        BEGIN
            NEW.{flag_column} := {words["flag_value"]} (
                SELECT 1 FROM titletmdbtitle
                WHERE titletmdbtitle.title_id = NEW.id
            );
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """,
    )
    op.execute(
        f"""
        CREATE TRIGGER "Title-{flag_word}-flag"
        BEFORE INSERT OR UPDATE OF {flag_column} ON title
        FOR EACH ROW EXECUTE FUNCTION title_{flag_word}_flag()
        """,
    )
    op.execute(
        f"""
        CREATE FUNCTION titletmdbtitle_{flag_word}_flag() RETURNS trigger AS $$
        BEGIN
            IF TG_OP <> 'INSERT' THEN
                UPDATE title SET {flag_column} = {flag_column}
                WHERE id = OLD.title_id;
            END IF;
            IF TG_OP <> 'DELETE' THEN
                UPDATE title SET {flag_column} = {flag_column}
                WHERE id = NEW.title_id;
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql
        """,
    )
    op.execute(
        f"""
        CREATE TRIGGER "TitleTmdbTitle-{flag_word}-flag"
        AFTER INSERT OR UPDATE OR DELETE ON titletmdbtitle
        FOR EACH ROW EXECUTE FUNCTION titletmdbtitle_{flag_word}_flag()
        """,
    )
    op.execute(
        f"""
        CREATE FUNCTION episode_{episode_flag_word}_flag() RETURNS trigger AS $$
        BEGIN
            NEW.{flag_column} := {words["flag_value"]} (
                SELECT 1 FROM episodetmdbepisode
                WHERE episodetmdbepisode.episode_id = NEW.id
            );
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """,
    )
    op.execute(
        f"""
        CREATE TRIGGER "Episode-{episode_flag_word}-flag"
        BEFORE INSERT OR UPDATE OF {flag_column} ON episode
        FOR EACH ROW EXECUTE FUNCTION episode_{episode_flag_word}_flag()
        """,
    )
    op.execute(
        f"""
        CREATE FUNCTION {words["episode_link_flag_prefix"]}_{episode_flag_word}_flag()
        RETURNS trigger AS $$
        BEGIN
            IF TG_OP <> 'INSERT' THEN
                UPDATE episode SET {flag_column} = {flag_column}
                WHERE id = OLD.episode_id;
            END IF;
            IF TG_OP <> 'DELETE' THEN
                UPDATE episode SET {flag_column} = {flag_column}
                WHERE id = NEW.episode_id;
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql
        """,
    )
    op.execute(
        f"""
        CREATE TRIGGER "{words["episode_link_flag_trigger"]}-{episode_flag_word}-flag"
        AFTER INSERT OR UPDATE OR DELETE ON episodetmdbepisode
        FOR EACH ROW EXECUTE FUNCTION
            {words["episode_link_flag_prefix"]}_{episode_flag_word}_flag()
        """,
    )


# TODO: Validate
def _rename_flag(old_column: str, new_column: str) -> None:
    for table in ("title", "episode"):
        op.alter_column(table, old_column, new_column_name=new_column)
        op.execute(f"UPDATE {table} SET {new_column} = NOT {new_column}")


# TODO: Validate
def upgrade() -> None:
    _drop(OLD_WORDS)
    _rename_flag("is_unlinked", "is_linked")
    for old_index, new_index in FLAG_INDEXES:
        op.execute(f'ALTER INDEX "{old_index}" RENAME TO "{new_index}"')
    _create(NEW_WORDS)


# TODO: Validate
def downgrade() -> None:
    _drop(NEW_WORDS)
    _rename_flag("is_linked", "is_unlinked")
    for old_index, new_index in FLAG_INDEXES:
        op.execute(f'ALTER INDEX "{new_index}" RENAME TO "{old_index}"')
    _create(OLD_WORDS)
