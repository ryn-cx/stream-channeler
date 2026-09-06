from alembic import op

revision = "a1f7c93d20b8"
down_revision = "d3a6f19b8c47"
branch_labels = None
depends_on = None

TABLES = [
    ("show", "title"),
    ("showcanonicalshow", "titlecanonicaltitle"),
    ("channelshow", "channeltitle"),
    ("showissuereport", "titleissuereport"),
    ("episodecanonicalshow", "episodecanonicaltitle"),
]

COLUMNS = [
    ("channelepisodefilter", "channel_show_id", "channel_title_id"),
    ("channelepisodesourcefilter", "channel_show_id", "channel_title_id"),
    ("channelepisodesourcefilter", "show_id", "title_id"),
    ("channelseasonfilter", "channel_show_id", "channel_title_id"),
    ("channelsourcefilter", "channel_show_id", "channel_title_id"),
    ("channelsourcefilter", "show_id", "title_id"),
    ("channeltitle", "canonical_show_id", "canonical_title_id"),
    ("episodecanonicaltitle", "canonical_show_id", "canonical_title_id"),
    ("season", "show_id", "title_id"),
    ("title", "canonical_show_validated_at", "canonical_title_validated_at"),
    ("titlecanonicaltitle", "show_id", "title_id"),
    ("titlecanonicaltitle", "canonical_show_id", "canonical_title_id"),
    ("titleissuereport", "show_id", "title_id"),
    ("unmatchedsource", "show_id", "title_id"),
]

INDEXES = [
    (
        "ChannelEpisodeSourceFilter-show_id-index",
        "ChannelEpisodeSourceFilter-title_id-index",
    ),
    ("ChannelSourceFilter-show_id-index", "ChannelSourceFilter-title_id-index"),
    ("ChannelShow-canonical_show_id-index", "ChannelTitle-canonical_title_id-index"),
    (
        "EpisodeCanonicalShow-canonical_show_id-index",
        "EpisodeCanonicalTitle-canonical_title_id-index",
    ),
    ("Show-canonical-key-index", "Title-canonical-key-index"),
    ("Show-deleted_at-index", "Title-deleted_at-index"),
    ("Show-is_canonical-index", "Title-is_canonical-index"),
    ("Show-media_type-index", "Title-media_type-index"),
    ("Show-name-index", "Title-name-index"),
    (
        "ShowCanonicalShow-canonical_show_id-index",
        "TitleCanonicalTitle-canonical_title_id-index",
    ),
    ("ShowIssueReport-show_id-index", "TitleIssueReport-title_id-index"),
    ("ShowIssueReport-user_id-index", "TitleIssueReport-user_id-index"),
    ("UnmatchedSource-show_id-index", "UnmatchedSource-title_id-index"),
]

CONSTRAINTS = [
    (
        "unmatchedsource",
        "UnmatchedSource-show_id-provider_name-unique",
        "UnmatchedSource-title_id-provider_name-unique",
    ),
]

FILE_CLASS_KEYS = [
    ("ShowFile", "TitleFile"),
    ("ShowListing", "TitleListing"),
    ("ShowPage", "TitlePage"),
    ("ShowsPage", "TitlesPage"),
    ("ShowsSearch", "TitlesSearch"),
]

SORT_MODELS = [
    ('"model":"show"', '"model":"title"'),
    ('"model": "show"', '"model": "title"'),
]


def _rename_file_class_keys(pairs: list[tuple[str, str]]) -> None:
    for old_name, new_name in pairs:
        prefix = f"{old_name}/"
        op.execute(
            f"""
            UPDATE file
            SET key = '{new_name}/' || substring(key from {len(prefix) + 1})
            WHERE left(key, {len(prefix)}) = '{prefix}'
            """,
        )


def _rewrite_sort_models(pairs: list[tuple[str, str]]) -> None:
    for old_value, new_value in pairs:
        op.execute(
            f"""
            UPDATE channelorder
            SET config = replace(config, '{old_value}', '{new_value}')
            WHERE position('{old_value}' in config) > 0
            """,
        )


def upgrade() -> None:
    for old_name, new_name in TABLES:
        op.rename_table(old_name, new_name)
    for table, old_name, new_name in COLUMNS:
        op.alter_column(table, old_name, new_column_name=new_name)
    for old_name, new_name in INDEXES:
        op.execute(f'ALTER INDEX "{old_name}" RENAME TO "{new_name}"')
    for table, old_name, new_name in CONSTRAINTS:
        op.execute(
            f'ALTER TABLE {table} RENAME CONSTRAINT "{old_name}" TO "{new_name}"',
        )
    _rename_file_class_keys(FILE_CLASS_KEYS)
    _rewrite_sort_models(SORT_MODELS)


def downgrade() -> None:
    _rewrite_sort_models([(new, old) for old, new in SORT_MODELS])
    _rename_file_class_keys([(new, old) for old, new in FILE_CLASS_KEYS])
    for table, old_name, new_name in CONSTRAINTS:
        op.execute(
            f'ALTER TABLE {table} RENAME CONSTRAINT "{new_name}" TO "{old_name}"',
        )
    for old_name, new_name in INDEXES:
        op.execute(f'ALTER INDEX "{new_name}" RENAME TO "{old_name}"')
    for table, old_name, new_name in COLUMNS:
        op.alter_column(table, new_name, new_column_name=old_name)
    for old_name, new_name in TABLES:
        op.rename_table(new_name, old_name)
