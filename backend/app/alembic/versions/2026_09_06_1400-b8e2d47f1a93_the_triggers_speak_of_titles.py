from typing import Any

from alembic import op

revision = "b8e2d47f1a93"
down_revision = "f4c81b7a92d5"
branch_labels = None
depends_on = None

TITLE_WORDS: dict[str, Any] = {
    "table": "title",
    "function_prefix": "title",
    "link_table": "titlecanonicaltitle",
    "episode_link_table": "episodecanonicaltitle",
    "id_column": "title_id",
    "canonical_column": "canonical_title_id",
    "prefix": "Title",
    "link_prefix": "TitleCanonicalTitle",
    "suffix": "title",
    "refresh": "refresh_episode_canonical_title",
    "refresh_of": "refresh_episode_canonical_title_of_title",
    "target": "target_title",
}

SHOW_WORDS: dict[str, Any] = {
    "table": '"show"',
    "function_prefix": "show",
    "link_table": "showcanonicalshow",
    "episode_link_table": "episodecanonicalshow",
    "id_column": "show_id",
    "canonical_column": "canonical_show_id",
    "prefix": "Show",
    "link_prefix": "ShowCanonicalShow",
    "suffix": "show",
    "refresh": "refresh_episode_canonical_show",
    "refresh_of": "refresh_episode_canonical_show_of_show",
    "target": "target_show",
}


def _function_names(words: dict[str, Any]) -> dict[str, str]:
    suffix = words["suffix"]
    return {
        "episode": f"episode_canonical_{suffix}",
        "episode_link": f"episodecanonicalepisode_canonical_{suffix}",
        "season": f"season_canonical_{suffix}",
        "table": f"{words['function_prefix']}_canonical_{suffix}",
        "link_table": f"{words['link_table']}_canonical_{suffix}",
        "flag": f"{words['function_prefix']}_canonical_flag",
        "link_flag": f"{words['link_table']}_canonical_flag",
    }


def _resolution(words: dict[str, Any]) -> str:
    return f"""
        SELECT DISTINCT
            episode.id AS episode_id,
            COALESCE(
                canonical_season.{words["id_column"]},
                {words["link_table"]}.{words["canonical_column"]},
                CASE WHEN {words["table"]}.is_canonical THEN {words["table"]}.id END
            ) AS {words["canonical_column"]}
        FROM episode
        JOIN season ON season.id = episode.season_id
        JOIN {words["table"]} ON {words["table"]}.id = season.{words["id_column"]}
        LEFT JOIN episodecanonicalepisode link ON link.episode_id = episode.id
        LEFT JOIN episode canonical_episode
            ON canonical_episode.id = link.canonical_episode_id
            AND canonical_episode.is_canonical
        LEFT JOIN season canonical_season
            ON canonical_season.id = canonical_episode.season_id
        LEFT JOIN {words["link_table"]}
            ON {words["link_table"]}.{words["id_column"]} = {words["table"]}.id
            AND episode.is_canonical
    """


def _create(words: dict[str, Any]) -> None:
    functions = _function_names(words)
    episode_link_table = words["episode_link_table"]
    canonical_column = words["canonical_column"]
    op.execute(
        f"""
        CREATE FUNCTION {words["refresh"]}(episode_ids uuid[])
        RETURNS void AS $$
        BEGIN
            DELETE FROM {episode_link_table}
            WHERE {episode_link_table}.episode_id = ANY(episode_ids);

            INSERT INTO {episode_link_table} (episode_id, {canonical_column})
            SELECT resolved.episode_id, resolved.{canonical_column}
            FROM (
                {_resolution(words)} WHERE episode.id = ANY(episode_ids)
            ) AS resolved
            WHERE resolved.{canonical_column} IS NOT NULL
            ON CONFLICT DO NOTHING;
        END;
        $$ LANGUAGE plpgsql
        """,
    )
    op.execute(
        f"""
        CREATE FUNCTION {words["refresh_of"]}({words["target"]} uuid)
        RETURNS void AS $$
        BEGIN
            PERFORM {words["refresh"]}(
                ARRAY(
                    SELECT episode.id
                    FROM episode
                    JOIN season ON season.id = episode.season_id
                    WHERE season.{words["id_column"]} = {words["target"]}
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
            PERFORM {words["refresh"]}(
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
        f"""
        CREATE TRIGGER "Episode-canonical-{words["suffix"]}"
        AFTER INSERT OR UPDATE OF season_id, is_canonical ON episode
        FOR EACH ROW EXECUTE FUNCTION {functions["episode"]}()
        """,
    )

    op.execute(
        f"""
        CREATE FUNCTION {functions["episode_link"]}() RETURNS trigger AS $$
        BEGIN
            IF TG_OP <> 'INSERT' THEN
                PERFORM {words["refresh"]}(ARRAY[OLD.episode_id]);
            END IF;
            IF TG_OP <> 'DELETE' THEN
                PERFORM {words["refresh"]}(ARRAY[NEW.episode_id]);
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql
        """,
    )
    op.execute(
        f"""
        CREATE TRIGGER "EpisodeCanonicalEpisode-canonical-{words["suffix"]}"
        AFTER INSERT OR UPDATE OR DELETE ON episodecanonicalepisode
        FOR EACH ROW EXECUTE FUNCTION {functions["episode_link"]}()
        """,
    )

    op.execute(
        f"""
        CREATE FUNCTION {functions["season"]}() RETURNS trigger AS $$
        BEGIN
            PERFORM {words["refresh"]}(
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
        f"""
        CREATE TRIGGER "Season-canonical-{words["suffix"]}"
        AFTER UPDATE OF title_id ON season
        FOR EACH ROW EXECUTE FUNCTION {functions["season"]}()
        """,
    )

    op.execute(
        f"""
        CREATE FUNCTION {functions["table"]}() RETURNS trigger AS $$
        BEGIN
            PERFORM {words["refresh_of"]}(NEW.id);
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql
        """,
    )
    op.execute(
        f"""
        CREATE TRIGGER "{words["prefix"]}-canonical-{words["suffix"]}"
        AFTER UPDATE OF is_canonical ON title
        FOR EACH ROW EXECUTE FUNCTION {functions["table"]}()
        """,
    )

    op.execute(
        f"""
        CREATE FUNCTION {functions["link_table"]}() RETURNS trigger AS $$
        BEGIN
            IF TG_OP <> 'INSERT' THEN
                PERFORM {words["refresh_of"]}(OLD.{words["id_column"]});
            END IF;
            IF TG_OP <> 'DELETE' THEN
                PERFORM {words["refresh_of"]}(NEW.{words["id_column"]});
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql
        """,
    )
    op.execute(
        f"""
        CREATE TRIGGER "{words["link_prefix"]}-canonical-{words["suffix"]}"
        AFTER INSERT OR UPDATE OR DELETE ON titlecanonicaltitle
        FOR EACH ROW EXECUTE FUNCTION {functions["link_table"]}()
        """,
    )

    op.execute(
        f"""
        CREATE FUNCTION {functions["flag"]}() RETURNS trigger AS $$
        BEGIN
            NEW.is_canonical := NOT EXISTS (
                SELECT 1 FROM {words["link_table"]}
                WHERE {words["link_table"]}.{words["id_column"]} = NEW.id
            );
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """,
    )
    op.execute(
        f"""
        CREATE TRIGGER "{words["prefix"]}-canonical-flag"
        BEFORE INSERT OR UPDATE OF is_canonical ON title
        FOR EACH ROW EXECUTE FUNCTION {functions["flag"]}()
        """,
    )

    op.execute(
        f"""
        CREATE FUNCTION {functions["link_flag"]}() RETURNS trigger AS $$
        BEGIN
            IF TG_OP <> 'INSERT' THEN
                UPDATE {words["table"]} SET is_canonical = is_canonical
                WHERE id = OLD.{words["id_column"]};
            END IF;
            IF TG_OP <> 'DELETE' THEN
                UPDATE {words["table"]} SET is_canonical = is_canonical
                WHERE id = NEW.{words["id_column"]};
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql
        """,
    )
    op.execute(
        f"""
        CREATE TRIGGER "{words["link_prefix"]}-canonical-flag"
        AFTER INSERT OR UPDATE OR DELETE ON titlecanonicaltitle
        FOR EACH ROW EXECUTE FUNCTION {functions["link_flag"]}()
        """,
    )


def _drop(words: dict[str, Any]) -> None:
    functions = _function_names(words)
    suffix = words["suffix"]
    op.execute(
        f'DROP TRIGGER "{words["link_prefix"]}-canonical-flag" ON titlecanonicaltitle',
    )
    op.execute(f"DROP FUNCTION {functions['link_flag']}()")
    op.execute(f'DROP TRIGGER "{words["prefix"]}-canonical-flag" ON title')
    op.execute(f"DROP FUNCTION {functions['flag']}()")
    op.execute(
        f'DROP TRIGGER "{words["link_prefix"]}-canonical-{suffix}"'
        " ON titlecanonicaltitle",
    )
    op.execute(f"DROP FUNCTION {functions['link_table']}()")
    op.execute(f'DROP TRIGGER "{words["prefix"]}-canonical-{suffix}" ON title')
    op.execute(f"DROP FUNCTION {functions['table']}()")
    op.execute(f'DROP TRIGGER "Season-canonical-{suffix}" ON season')
    op.execute(f"DROP FUNCTION {functions['season']}()")
    op.execute(
        f'DROP TRIGGER "EpisodeCanonicalEpisode-canonical-{suffix}"'
        " ON episodecanonicalepisode",
    )
    op.execute(f"DROP FUNCTION {functions['episode_link']}()")
    op.execute(f'DROP TRIGGER "Episode-canonical-{suffix}" ON episode')
    op.execute(f"DROP FUNCTION {functions['episode']}()")
    op.execute(f"DROP FUNCTION {words['refresh_of']}(uuid)")
    op.execute(f"DROP FUNCTION {words['refresh']}(uuid[])")


def upgrade() -> None:
    _drop(SHOW_WORDS)
    _create(TITLE_WORDS)


def downgrade() -> None:
    _drop(TITLE_WORDS)
    _create(SHOW_WORDS)
