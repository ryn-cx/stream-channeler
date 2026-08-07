# TODO: Validate
"""Choosing which episodes a channel offers, and in what order.

`query_builder` is the entry point; the rest are the pieces it reads a channel
through:

- `channel_scope` - the channels a read covers and who may see them
- `visibility` - whether a channel takes a given copy of an episode
- `watch_filters` - what the `User` has watched
- `source_dedup` - which website's copy of an episode stands for it
- `tmdb_columns` - reading a record as TMDB has it from inside the query
- `sorting` - turning a sort key into the expression it orders by
- `show_counts` - narrowing the result down to a handful of shows
"""

from app.channels.episode_selector.channel_scope import (
    child_channel_ids,
    readable_channels,
    resolve_channel_ids,
)
from app.channels.episode_selector.query_builder import (
    MAX_EPISODES_RETURNED,
    EpisodeQueryBuilder,
    EpisodeResult,
)
from app.channels.episode_selector.source_dedup import (
    SourceDedupConfig,
    deduplicate_episodes,
    source_dedup_config,
)

__all__ = [
    "MAX_EPISODES_RETURNED",
    "EpisodeQueryBuilder",
    "EpisodeResult",
    "SourceDedupConfig",
    "child_channel_ids",
    "deduplicate_episodes",
    "readable_channels",
    "resolve_channel_ids",
    "source_dedup_config",
]
