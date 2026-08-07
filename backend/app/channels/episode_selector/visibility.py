# TODO: Validate
"""Whether a channel takes a given copy of an episode.

A `ChannelShow` stands for a title rather than one website's copy of it, and the
source, season and episode filters hanging off it are what narrow that down to
the copies and episodes the channel actually offers. These read the filter rows
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

from app.channels.models import (
    ChannelEpisodeFilter,
    ChannelSeasonFilter,
    ChannelShow,
    ChannelSourceFilter,
)
from app.episodes.models import Episode


def source_access_condition() -> ColumnElement[bool]:
    """Whether this website's copy of the title is one the channel takes.

    A `ChannelShow` covers every website the title is on, so a `User` who
    wants only some of them says so with `ChannelSourceFilter` entries. Saying
    nothing means every copy, which is what a channel that was never told
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


def channel_access_condition() -> ColumnElement[bool]:
    """Whether the channel offers this episode, after every filter on it."""
    # An episode entry inverts what the season entry decided, which is what
    # makes one episode an exception to a whitelisted or blacklisted season.
    return and_(
        source_access_condition(),
        or_(
            and_(
                col(ChannelShow.is_whitelist).is_(True),
                or_(
                    and_(
                        col(ChannelSeasonFilter.season_identifier).is_not(None),
                        col(ChannelEpisodeFilter.episode_identifier).is_(None),
                    ),
                    and_(
                        col(ChannelSeasonFilter.season_identifier).is_(None),
                        col(ChannelEpisodeFilter.episode_identifier).is_not(None),
                    ),
                ),
            ),
            and_(
                col(ChannelShow.is_whitelist).is_(False),
                or_(
                    and_(
                        col(ChannelSeasonFilter.season_identifier).is_(None),
                        col(ChannelEpisodeFilter.episode_identifier).is_(None),
                    ),
                    and_(
                        col(ChannelSeasonFilter.season_identifier).is_not(None),
                        col(ChannelEpisodeFilter.episode_identifier).is_not(None),
                    ),
                ),
            ),
        ),
    )


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
        select(filter_only_filter.episode_identifier)
        .select_from(filter_only_filter)
        .join(
            filter_only_show,
            col(filter_only_filter.channel_show_id) == filter_only_show.id,
        )
        .where(
            col(filter_only_show.is_blacklist_only).is_(True),
            col(filter_only_show.channel_id).in_(channel_ids),
            col(filter_only_filter.episode_identifier)
            == col(Episode.episode_identifier),
            or_(
                col(filter_only_filter.expires_at).is_(None),
                col(filter_only_filter.expires_at) > now,
            ),
        )
        .exists()
    )
