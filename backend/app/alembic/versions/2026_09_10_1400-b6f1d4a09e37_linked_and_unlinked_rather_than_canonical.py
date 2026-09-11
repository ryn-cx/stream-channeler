# TODO: Validate
"""A row is linked or unlinked, and what it is linked to is TMDB's.

"Canonical" said only that a row stood for itself, which is the same fact as a
row having nothing linked to it and reads worse everywhere it is spoken. The
columns are renamed to say linked or unlinked, and the record on the other end
of a link is named for what it always is, which is TMDB's own.
"""

from typing import Any

from alembic import op

revision = "b6f1d4a09e37"
down_revision = "a1e7c93f52b4"
branch_labels = None
depends_on = None


OLD_WORDS: dict[str, Any] = {
    "link_table": "titlecanonicaltitle",
    "episode_link_table": "episodecanonicaltitle",
    "episode_episode_link_table": "episodecanonicalepisode",
    "tmdb_title_column": "canonical_title_id",
    "tmdb_episode_column": "canonical_episode_id",
    "flag_column": "is_canonical",
    "link_prefix": "TitleCanonicalTitle",
    "word": "canonical",
    "flag_word": "canonical",
}

NEW_WORDS: dict[str, Any] = {
    "link_table": "titletmdbtitle",
    "episode_link_table": "episodetmdbtitle",
    "episode_episode_link_table": "episodetmdbepisode",
    "tmdb_title_column": "tmdb_title_id",
    "tmdb_episode_column": "tmdb_episode_id",
    "flag_column": "is_unlinked",
    "link_prefix": "TitleTmdbTitle",
    "word": "tmdb",
    "flag_word": "unlinked",
}

TABLES = [
    ("titlecanonicaltitle", "titletmdbtitle"),
    ("episodecanonicalepisode", "episodetmdbepisode"),
    ("episodecanonicaltitle", "episodetmdbtitle"),
]

COLUMNS = [
    ("channelepisodefilter", "canonical_episode_id", "tmdb_episode_id"),
    ("channelepisodesourcefilter", "canonical_episode_id", "tmdb_episode_id"),
    ("channelsavedepisodeorder", "canonical_episode_id", "tmdb_episode_id"),
    ("channeltitle", "canonical_title_id", "tmdb_title_id"),
    ("episode", "canonical_episode_validated_at", "tmdb_episode_validated_at"),
    ("episode", "is_canonical", "is_unlinked"),
    ("episodecanonicalepisode", "canonical_episode_id", "tmdb_episode_id"),
    ("episodecanonicaltitle", "canonical_title_id", "tmdb_title_id"),
    ("title", "canonical_title_validated_at", "tmdb_title_validated_at"),
    ("title", "is_canonical", "is_unlinked"),
    ("titlecanonicaltitle", "canonical_title_id", "tmdb_title_id"),
    ("userepisodeurl", "canonical_episode_id", "tmdb_episode_id"),
]

INDEXES = [
    (
        "ChannelEpisodeFilter-canonical_episode_id-index",
        "ChannelEpisodeFilter-tmdb_episode_id-index",
    ),
    (
        "ChannelEpisodeSourceFilter-canonical_episode_id-index",
        "ChannelEpisodeSourceFilter-tmdb_episode_id-index",
    ),
    (
        "ChannelSavedEpisodeOrder-canonical_episode_id-index",
        "ChannelSavedEpisodeOrder-tmdb_episode_id-index",
    ),
    ("ChannelTitle-canonical_title_id-index", "ChannelTitle-tmdb_title_id-index"),
    ("Episode-canonical-key-index", "Episode-unlinked-key-index"),
    ("Episode-is_canonical-index", "Episode-is_unlinked-index"),
    (
        "EpisodeCanonicalEpisode-canonical_episode_id-index",
        "EpisodeTmdbEpisode-tmdb_episode_id-index",
    ),
    (
        "EpisodeCanonicalTitle-canonical_title_id-index",
        "EpisodeTmdbTitle-tmdb_title_id-index",
    ),
    ("Title-canonical-key-index", "Title-unlinked-key-index"),
    ("Title-is_canonical-index", "Title-is_unlinked-index"),
    (
        "TitleCanonicalTitle-canonical_title_id-index",
        "TitleTmdbTitle-tmdb_title_id-index",
    ),
]


# TODO: Validate
def _function_names(words: dict[str, Any]) -> dict[str, str]:
    word = words["word"]
    return {
        "refresh": f"refresh_episode_{word}_title",
        "refresh_of": f"refresh_episode_{word}_title_of_title",
        "episode": f"episode_{word}_title",
        "episode_link": f"{words['episode_episode_link_table']}_{word}_title",
        "season": f"season_{word}_title",
        "table": f"title_{word}_title",
        "link_table": f"{words['link_table']}_{word}_title",
        "flag": f"title_{words['flag_word']}_flag",
        "link_flag": f"{words['link_table']}_{words['flag_word']}_flag",
    }


# TODO: Validate
def _drop(words: dict[str, Any]) -> None:
    functions = _function_names(words)
    word = words["word"]
    flag_word = words["flag_word"]
    op.execute(
        f'DROP TRIGGER "{words["link_prefix"]}-{flag_word}-flag" '
        f"ON {words['link_table']}",
    )
    op.execute(f"DROP FUNCTION {functions['link_flag']}()")
    op.execute(f'DROP TRIGGER "Title-{flag_word}-flag" ON title')
    op.execute(f"DROP FUNCTION {functions['flag']}()")
    op.execute(
        f'DROP TRIGGER "{words["link_prefix"]}-{word}-title" ON {words["link_table"]}',
    )
    op.execute(f"DROP FUNCTION {functions['link_table']}()")
    op.execute(f'DROP TRIGGER "Title-{word}-title" ON title')
    op.execute(f"DROP FUNCTION {functions['table']}()")
    op.execute(f'DROP TRIGGER "Season-{word}-title" ON season')
    op.execute(f"DROP FUNCTION {functions['season']}()")
    op.execute(
        f'DROP TRIGGER "{"EpisodeCanonicalEpisode" if word == "canonical" else "EpisodeTmdbEpisode"}-{word}-title" '
        f"ON {words['episode_episode_link_table']}",
    )
    op.execute(f"DROP FUNCTION {functions['episode_link']}()")
    op.execute(f'DROP TRIGGER "Episode-{word}-title" ON episode')
    op.execute(f"DROP FUNCTION {functions['episode']}()")
    op.execute(f"DROP FUNCTION {functions['refresh_of']}(uuid)")
    op.execute(f"DROP FUNCTION {functions['refresh']}(uuid[])")


# TODO: Validate
def _resolution(words: dict[str, Any]) -> str:
    return f"""
        SELECT DISTINCT
            episode.id AS episode_id,
            COALESCE(
                tmdb_season.title_id,
                {words["link_table"]}.{words["tmdb_title_column"]},
                CASE WHEN title.{words["flag_column"]} THEN title.id END
            ) AS {words["tmdb_title_column"]}
        FROM episode
        JOIN season ON season.id = episode.season_id
        JOIN title ON title.id = season.title_id
        LEFT JOIN {words["episode_episode_link_table"]} link
            ON link.episode_id = episode.id
        LEFT JOIN episode tmdb_episode
            ON tmdb_episode.id = link.{words["tmdb_episode_column"]}
            AND tmdb_episode.{words["flag_column"]}
        LEFT JOIN season tmdb_season
            ON tmdb_season.id = tmdb_episode.season_id
        LEFT JOIN {words["link_table"]}
            ON {words["link_table"]}.title_id = title.id
            AND episode.{words["flag_column"]}
    """


# TODO: Validate
def _create(words: dict[str, Any]) -> None:
    functions = _function_names(words)
    episode_link_table = words["episode_link_table"]
    tmdb_title_column = words["tmdb_title_column"]
    word = words["word"]
    flag_word = words["flag_word"]
    link_prefix = words["link_prefix"]
    episode_link_prefix = (
        "EpisodeCanonicalEpisode" if word == "canonical" else "EpisodeTmdbEpisode"
    )
    op.execute(
        f"""
        CREATE FUNCTION {functions["refresh"]}(episode_ids uuid[])
        RETURNS void AS $$
        BEGIN
            DELETE FROM {episode_link_table}
            WHERE {episode_link_table}.episode_id = ANY(episode_ids);

            INSERT INTO {episode_link_table} (episode_id, {tmdb_title_column})
            SELECT resolved.episode_id, resolved.{tmdb_title_column}
            FROM (
                {_resolution(words)} WHERE episode.id = ANY(episode_ids)
            ) AS resolved
            WHERE resolved.{tmdb_title_column} IS NOT NULL
            ON CONFLICT DO NOTHING;
        END;
        $$ LANGUAGE plpgsql
        """,
    )
    op.execute(
        f"""
        CREATE FUNCTION {functions["refresh_of"]}(target_title uuid)
        RETURNS void AS $$
        BEGIN
            PERFORM {functions["refresh"]}(
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
        f"""
        CREATE FUNCTION {functions["episode"]}() RETURNS trigger AS $$
        BEGIN
            PERFORM {functions["refresh"]}(
                ARRAY(
                    SELECT NEW.id
                    UNION
                    SELECT link.episode_id
                    FROM {words["episode_episode_link_table"]} link
                    WHERE link.{words["tmdb_episode_column"]} = NEW.id
                )
            );
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql
        """,
    )
    op.execute(
        f"""
        CREATE TRIGGER "Episode-{word}-title"
        AFTER INSERT OR UPDATE OF season_id, {words["flag_column"]} ON episode
        FOR EACH ROW EXECUTE FUNCTION {functions["episode"]}()
        """,
    )
    op.execute(
        f"""
        CREATE FUNCTION {functions["episode_link"]}() RETURNS trigger AS $$
        BEGIN
            IF TG_OP <> 'INSERT' THEN
                PERFORM {functions["refresh"]}(ARRAY[OLD.episode_id]);
            END IF;
            IF TG_OP <> 'DELETE' THEN
                PERFORM {functions["refresh"]}(ARRAY[NEW.episode_id]);
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql
        """,
    )
    op.execute(
        f"""
        CREATE TRIGGER "{episode_link_prefix}-{word}-title"
        AFTER INSERT OR UPDATE OR DELETE ON {words["episode_episode_link_table"]}
        FOR EACH ROW EXECUTE FUNCTION {functions["episode_link"]}()
        """,
    )
    op.execute(
        f"""
        CREATE FUNCTION {functions["season"]}() RETURNS trigger AS $$
        BEGIN
            PERFORM {functions["refresh"]}(
                ARRAY(
                    SELECT episode.id FROM episode WHERE episode.season_id = NEW.id
                    UNION
                    SELECT link.episode_id
                    FROM {words["episode_episode_link_table"]} link
                    JOIN episode ON episode.id = link.{words["tmdb_episode_column"]}
                    WHERE episode.season_id = NEW.id
                )
            );
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql
        """,
    )
    op.execute(
        f"""
        CREATE TRIGGER "Season-{word}-title"
        AFTER UPDATE OF title_id ON season
        FOR EACH ROW EXECUTE FUNCTION {functions["season"]}()
        """,
    )
    op.execute(
        f"""
        CREATE FUNCTION {functions["table"]}() RETURNS trigger AS $$
        BEGIN
            PERFORM {functions["refresh_of"]}(NEW.id);
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql
        """,
    )
    op.execute(
        f"""
        CREATE TRIGGER "Title-{word}-title"
        AFTER UPDATE OF {words["flag_column"]} ON title
        FOR EACH ROW EXECUTE FUNCTION {functions["table"]}()
        """,
    )
    op.execute(
        f"""
        CREATE FUNCTION {functions["link_table"]}() RETURNS trigger AS $$
        BEGIN
            IF TG_OP <> 'INSERT' THEN
                PERFORM {functions["refresh_of"]}(OLD.title_id);
            END IF;
            IF TG_OP <> 'DELETE' THEN
                PERFORM {functions["refresh_of"]}(NEW.title_id);
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql
        """,
    )
    op.execute(
        f"""
        CREATE TRIGGER "{link_prefix}-{word}-title"
        AFTER INSERT OR UPDATE OR DELETE ON {words["link_table"]}
        FOR EACH ROW EXECUTE FUNCTION {functions["link_table"]}()
        """,
    )
    op.execute(
        f"""
        CREATE FUNCTION {functions["flag"]}() RETURNS trigger AS $$
        BEGIN
            NEW.{words["flag_column"]} := NOT EXISTS (
                SELECT 1 FROM {words["link_table"]}
                WHERE {words["link_table"]}.title_id = NEW.id
            );
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """,
    )
    op.execute(
        f"""
        CREATE TRIGGER "Title-{flag_word}-flag"
        BEFORE INSERT OR UPDATE OF {words["flag_column"]} ON title
        FOR EACH ROW EXECUTE FUNCTION {functions["flag"]}()
        """,
    )
    op.execute(
        f"""
        CREATE FUNCTION {functions["link_flag"]}() RETURNS trigger AS $$
        BEGIN
            IF TG_OP <> 'INSERT' THEN
                UPDATE title SET {words["flag_column"]} = {words["flag_column"]}
                WHERE id = OLD.title_id;
            END IF;
            IF TG_OP <> 'DELETE' THEN
                UPDATE title SET {words["flag_column"]} = {words["flag_column"]}
                WHERE id = NEW.title_id;
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql
        """,
    )
    op.execute(
        f"""
        CREATE TRIGGER "{link_prefix}-{flag_word}-flag"
        AFTER INSERT OR UPDATE OR DELETE ON {words["link_table"]}
        FOR EACH ROW EXECUTE FUNCTION {functions["link_flag"]}()
        """,
    )


# TODO: Validate
def upgrade() -> None:
    _drop(OLD_WORDS)
    for table, old_column, new_column in COLUMNS:
        op.alter_column(table, old_column, new_column_name=new_column)
    for old_table, new_table in TABLES:
        op.rename_table(old_table, new_table)
    for old_index, new_index in INDEXES:
        op.execute(f'ALTER INDEX "{old_index}" RENAME TO "{new_index}"')
    _create(NEW_WORDS)


# TODO: Validate
def downgrade() -> None:
    _drop(NEW_WORDS)
    for old_index, new_index in INDEXES:
        op.execute(f'ALTER INDEX "{new_index}" RENAME TO "{old_index}"')
    for old_table, new_table in TABLES:
        op.rename_table(new_table, old_table)
    for table, old_column, new_column in COLUMNS:
        op.alter_column(table, new_column, new_column_name=old_column)
    _create(OLD_WORDS)
