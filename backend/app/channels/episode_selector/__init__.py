# TODO: Validate
"""Choosing which episodes a channel offers, and in what order.

`query_builder` is the entry point; the rest are the pieces it reads a channel
through:

- `visibility` - whether a channel takes a given row for an episode
- `watch_filters` - what the `User` has watched
- `source_dedup` - which website's row for an episode stands for it
- `canonical_columns` - reading the canonical row from inside the query
- `sorting` - turning a sort key into the expression it orders by
- `show_counts` - narrowing the result down to a handful of shows
"""

from app.channels.episode_selector.query_builder import (
    EpisodeQueryBuilder,
    EpisodeResult,
)
from app.channels.episode_selector.source_dedup import (
    SourceDedupConfig,
    source_dedup_config,
)

__all__ = [
    "EpisodeQueryBuilder",
    "EpisodeResult",
    "SourceDedupConfig",
    "source_dedup_config",
]
