"""one word names which of tmdb's numberings a key came from

A TMDB key said the half of the catalogue and the level both: "TMDB tv show
1399", and for a film "TMDB movie season 27205", which reads as a thing that does
not exist. TMDB numbers four things apart from each other, so one word is all it
takes to say which of them a number came from: "TMDB movie 27205", "TMDB tv
1399", "TMDB season 3624", "TMDB episode 63056".

A film's three rows are all named "TMDB movie 27205", since a film is numbered
once and a season is named within its title and an episode within its season, so
the three never have to be told apart from one another.

The keys watches hold are rewritten with them, since a watch names its episode by
key and would otherwise be left naming an episode nothing is under any more.

A row already carrying the new key is one an import made while the old row was
still standing under the old one, so the two are the same record under two names
and the old one is what everything points at. Each pair is merged before the
rename, since the rename would otherwise leave two rows of one name.

Revision ID: a7e2c9b4f318
Revises: f3c8d5b2a417
Create Date: 2026-08-12 10:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "a7e2c9b4f318"
down_revision = "f3c8d5b2a417"
branch_labels = None
depends_on = None

# The word each level and half of the catalogue is named by now, against the two
# the key used to carry. A film keeps its own word at every level; a series
# record takes the word of the numbering its level is counted in.
_WORDS = [
    ("canonicalshow", "key", "movie", "show", "movie"),
    ("canonicalshow", "key", "tv", "show", "tv"),
    ("canonicalseason", "key", "movie", "season", "movie"),
    ("canonicalseason", "key", "tv", "season", "season"),
    ("canonicalepisode", "key", "movie", "episode", "movie"),
    ("canonicalepisode", "key", "tv", "episode", "episode"),
    ("watch", "canonical_episode_key", "movie", "episode", "movie"),
    ("watch", "canonical_episode_key", "tv", "episode", "episode"),
]

# What points at a canonical row, and the column a pairing of it is unique on.
# A reference the loser and the keeper both already have would be one row twice
# over, so the loser's is dropped rather than pointed at the keeper.
_CANONICAL_SHOW_REFERENCES = [
    ("show", "canonical_show_id", None),
    ("showcanonicalshow", "canonical_show_id", "show_id"),
    ("channelshow", "canonical_show_id", "channel_id"),
    ("canonicalseason", "canonical_show_id", None),
]
_CANONICAL_SEASON_REFERENCES = [
    ("season", "canonical_season_id", None),
    ("channelseasonfilter", "canonical_season_id", "channel_show_id"),
    ("canonicalepisode", "canonical_season_id", None),
]
_CANONICAL_EPISODE_REFERENCES = [
    ("episode", "canonical_episode_id", None),
    ("channelepisodefilter", "canonical_episode_id", "channel_show_id"),
    ("channelsavedepisodeorder", "canonical_episode_id", "channel_id"),
]

# Each canonical table, what its keys are unique within, and what points at it.
# Merged from the top down, since merging the titles is what puts two seasons
# under one title and merging those is what puts two episodes under one season.
_LEVELS = [
    ("canonicalshow", None, _CANONICAL_SHOW_REFERENCES),
    ("canonicalseason", "canonical_show_id", _CANONICAL_SEASON_REFERENCES),
    ("canonicalepisode", "canonical_season_id", _CANONICAL_EPISODE_REFERENCES),
]


def _renamed_key(table: str, alias: str) -> str:
    """Return the SQL rewriting `alias`'s key as the one word now names it."""
    branches = " ".join(
        f"WHEN {alias}.key LIKE 'TMDB {media_type} {level} %' "
        f"THEN 'TMDB {word} ' || split_part({alias}.key, ' ', 4)"
        for key_table, _column, media_type, level, word in _WORDS
        if key_table == table
    )
    return f"CASE {branches} END"


def _merge_duplicates(table: str, parent_column: str | None, references) -> None:
    """Point everything under a row's new name at the row that already held it."""
    parent_match = ""
    if parent_column:
        parent_match = f"AND duplicate.{parent_column} = keeper.{parent_column}"

    op.execute(
        f"CREATE TEMPORARY TABLE _merge AS "  # noqa: S608 - Table names are literals above.
        f"SELECT duplicate.id AS loser, keeper.id AS keeper "
        f"FROM {table} keeper "
        f"JOIN {table} duplicate "
        f"ON duplicate.key = {_renamed_key(table, 'keeper')} {parent_match}",
    )

    if table == "canonicalepisode":
        _release_clashing_episodes()

    for reference_table, column, partner_column in references:
        if partner_column:
            op.execute(
                f"DELETE FROM {reference_table} reference "  # noqa: S608 - Table names are literals above.
                f"USING _merge "
                f"WHERE reference.{column} = _merge.loser "
                f"AND EXISTS (SELECT 1 FROM {reference_table} other "
                f"WHERE other.{partner_column} = reference.{partner_column} "
                f"AND other.{column} = _merge.keeper)",
            )
        op.execute(
            f"UPDATE {reference_table} SET {column} = _merge.keeper "  # noqa: S608 - Table names are literals above.
            f"FROM _merge WHERE {reference_table}.{column} = _merge.loser",
        )

    op.execute(f"DELETE FROM {table} USING _merge WHERE {table}.id = _merge.loser")  # noqa: S608 - Table name is a literal above.
    op.execute("DROP TABLE _merge")


def _release_clashing_episodes() -> None:
    """Take the record off an episode whose season's own copy of it is kept.

    One season holds one episode of a record, so an episode pointing at the row
    being merged away is left pointing at nothing when the season already has an
    episode on the row being kept. It is unlocked with it, which is what leaves
    the next reconcile free to give it a row standing only for itself.
    """
    op.execute(
        "UPDATE episode SET canonical_episode_id = NULL, "
        "canonical_episode_locked = false "
        "FROM _merge WHERE episode.canonical_episode_id = _merge.loser "
        "AND episode.deleted_at IS NULL "
        "AND EXISTS (SELECT 1 FROM episode other "
        "WHERE other.season_id = episode.season_id "
        "AND other.canonical_episode_id = _merge.keeper "
        "AND other.deleted_at IS NULL)",
    )


def upgrade():
    for table, parent_column, references in _LEVELS:
        _merge_duplicates(table, parent_column, references)

    # The id is the fourth word of the old key and the third of the new one, so
    # each row is rewritten from the id alone rather than edited in place.
    for table, column, media_type, level, word in _WORDS:
        op.execute(
            f"UPDATE {table} SET {column} = "  # noqa: S608 - Table and column names are literals above.
            f"'TMDB {word} ' || split_part({column}, ' ', 4) "
            f"WHERE {column} LIKE 'TMDB {media_type} {level} %'",
        )


def downgrade():
    for table, column, media_type, level, word in _WORDS:
        op.execute(
            f"UPDATE {table} SET {column} = "  # noqa: S608 - Table and column names are literals above.
            f"'TMDB {media_type} {level} ' || split_part({column}, ' ', 3) "
            f"WHERE {column} LIKE 'TMDB {word} %'",
        )
