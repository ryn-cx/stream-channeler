# TODO: Validate
"""Whether a channel takes a given row for an episode.

A `ChannelShow` stands for a canonical show rather than one website's row, and the
source, season and episode filters hanging off it are what narrow that down to
the rows and episodes the channel actually offers. These read the filter rows
the query already outer-joined, so they only make sense against a query built by
`EpisodeQueryBuilder`.
"""

from collections.abc import Collection
from datetime import datetime
from uuid import UUID

from sqlalchemy import literal_column
from sqlalchemy.orm import aliased
from sqlalchemy.sql.expression import ColumnElement
from sqlmodel import and_, col, or_, select

from app.channels.episode_selector.canonical_entities import episode_id
from app.channels.models import (
    ChannelEpisodeFilter,
    ChannelEpisodeSourceFilter,
    ChannelSeasonFilter,
    ChannelShow,
    ChannelSourceFilter,
)


# TODO: Validate
def source_access_condition() -> ColumnElement[bool]:
    """Whether this website's row for the show is one the channel takes.

    A `ChannelShow` covers every website the show is on, so a `User` who
    wants only some of them says so with `ChannelSourceFilter` entries. Saying
    nothing means every website, which is what a channel that was never told
    about websites at all wants.
    """
    # Aliased so the outer join to `ChannelSourceFilter` is not what this reads;
    # it asks whether the `ChannelShow` names any website at all.
    any_source_filter = aliased(ChannelSourceFilter)
    has_source_filters = (
        select(literal_column("1"))
        .select_from(any_source_filter)
        .where(col(any_source_filter.channel_show_id) == col(ChannelShow.id))
        .correlate(ChannelShow)
        .exists()
    )
    matched = col(ChannelSourceFilter.show_id).is_not(None)
    return or_(
        and_(
            col(ChannelShow.is_whitelist).is_(True),
            or_(~has_source_filters, matched),
        ),
        and_(col(ChannelShow.is_whitelist).is_(False), ~matched),
    )


# TODO: Validate
def _either_but_not_both(
    first: ColumnElement[bool],
    second: ColumnElement[bool],
) -> ColumnElement[bool]:
    """Whether exactly one of the two holds."""
    return or_(and_(first, ~second), and_(~first, second))


# TODO: Validate
def marked_by_filters_condition() -> ColumnElement[bool]:
    """Whether the filters name this website's link to this episode.

    An episode entry inverts what the season entry decided, which is what makes
    one episode an exception to a whitelisted or blacklisted season, and an
    episode source entry inverts that again for the one website it names, which
    is what leaves an episode taken from one site and left on another.
    """
    return _either_but_not_both(
        _either_but_not_both(
            col(ChannelSeasonFilter.season_id).is_not(None),
            col(ChannelEpisodeFilter.canonical_episode_id).is_not(None),
        ),
        col(ChannelEpisodeSourceFilter.canonical_episode_id).is_not(None),
    )


# TODO: Validate
def channel_access_condition() -> ColumnElement[bool]:
    """Whether the channel offers this episode, after every filter on it."""
    marked = marked_by_filters_condition()
    return and_(
        source_access_condition(),
        or_(
            and_(col(ChannelShow.is_whitelist).is_(True), marked),
            and_(col(ChannelShow.is_whitelist).is_(False), ~marked),
        ),
    )


# TODO: Validate
def blacklisted_on_channels_condition(
    channel_ids: Collection[UUID],
    now: datetime,
) -> ColumnElement[bool]:
    """Whether one of the channels hides this episode without holding its show.

    A show that is on the channel only to carry filters (`is_blacklist_only`)
    contributes no episodes of its own; its entries exist to hide episodes that
    another channel pulled in. An entry that has expired no longer hides anything.
    """
    filter_only_show = aliased(ChannelShow)
    filter_only_filter = aliased(ChannelEpisodeFilter)
    return (
        select(filter_only_filter.canonical_episode_id)
        .select_from(filter_only_filter)
        .join(
            filter_only_show,
            col(filter_only_filter.channel_show_id) == filter_only_show.id,
        )
        .where(
            col(filter_only_show.is_blacklist_only).is_(True),
            col(filter_only_show.channel_id).in_(channel_ids),
            col(filter_only_filter.canonical_episode_id) == episode_id(),
            or_(
                col(filter_only_filter.expires_at).is_(None),
                col(filter_only_filter.expires_at) > now,
            ),
        )
        .exists()
    )
