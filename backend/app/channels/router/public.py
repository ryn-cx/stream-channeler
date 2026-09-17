# TODO: Validate


import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from app.auth.dependencies import (
    SessionDep,
)
from app.channels.dependencies import (
    ReadableChannel,
    ReadableChannelTmdbTitle,
)
from app.channels.schemas import (
    ChannelEpisodesOutput,
    ChannelOptions,
    ChannelOutput,
    ChannelReadOptions,
    ChannelsPublic,
    ChannelTitlesOutput,
    CombinedChannelOutput,
    SortOptionOutput,
    WhitelistEpisodesOutput,
    WhitelistTitleOutput,
)
from app.channels.service import (
    channels,
    combined,
    episodes,
    ordering,
    sources,
    titles,
    whitelist,
)
from app.channels.service.titles import CHANNEL_TITLE_PAGE
from app.channels.service.whitelist import WHITELIST_EPISODE_PAGE
from app.sources.schemas import SourcePublic
from app.users.dependencies import OptionalUser
from app.video_store import service as video_store
from app.video_store.schemas import VideoStoreTitlesOutput

channels_router = APIRouter(prefix="/channels", tags=["channels"])


# TODO: Validate
@channels_router.get("")
def get_channels(
    session: SessionDep,
    current_user: OptionalUser,
    read_options: Annotated[ChannelReadOptions, Query()],
) -> ChannelsPublic:
    """Get `Channel`s."""
    return channels.scoped_channel_list_output(session, current_user, read_options)


# TODO: Validate
@channels_router.get("/sort-options")
def get_sort_options() -> list[SortOptionOutput]:
    """Return every sort option a `Channel` can be ordered by."""
    return ordering.get_sort_options()


# TODO: Validate
@channels_router.get(
    "/{channel_id}/combined-channels",  # noqa: FAST003 - Used by ReadableChannel.
)
def get_channel_combined_channels(
    channel: ReadableChannel,
    session: SessionDep,
) -> list[CombinedChannelOutput]:
    """Return a `Channel`'s `CombinedChannel`s."""
    return combined.combined_channels_output(channel, session)


# TODO: Validate
@channels_router.get("/{channel_id}/episodes")  # noqa: FAST003 - Used by ReadableChannel.
def get_channel_episodes(
    channel: ReadableChannel,
    channel_options: Annotated[ChannelOptions, Query()],
    user: OptionalUser,
    session: SessionDep,
) -> ChannelEpisodesOutput:
    """Read the episodes for a channel."""
    return episodes.channel_episodes_output(channel, channel_options, user, session)


# FAST003 - Parameter is used by ReadableChannel.
# TODO: Validate
@channels_router.get("/{channel_id}/store-titles")  # noqa: FAST003
def get_channel_store_titles(
    channel: ReadableChannel,
    user: OptionalUser,
    session: SessionDep,
) -> VideoStoreTitlesOutput:
    """Read every title a channel shelves in the video store."""
    return video_store.channel_titles(session, channel, user)


# FAST003 - Parameter is used by ReadableChannel.
# TODO: Validate
@channels_router.get("/{channel_id}/titles")  # noqa: FAST003
def get_channel_titles(  # noqa: PLR0913 - the listing is paged and searched
    channel: ReadableChannel,
    user: OptionalUser,
    session: SessionDep,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=CHANNEL_TITLE_PAGE)] = CHANNEL_TITLE_PAGE,
    query: Annotated[str | None, Query()] = None,
) -> ChannelTitlesOutput:
    """Read all titles for a channel, including those from its child channels."""
    return titles.channel_titles_output(channel, user, session, offset, limit, query)


# FAST003 - Parameter is used by ReadableChannel.
# TODO: Validate
@channels_router.get("/{channel_id}/sources")  # noqa: FAST003
def get_channel_sources(
    channel: ReadableChannel,
    session: SessionDep,
) -> list[SourcePublic]:
    """Read all unique sources for a channel."""
    return sources.channel_sources_output(channel, session)


# FAST003 - Parameter is used by ReadableChannelTmdbTitle.
# TODO: Validate
@channels_router.get("/{channel_id}/whitelist/{tmdb_title_id}")  # noqa: FAST003
def get_channel_whitelist(
    session: SessionDep,
    channel_title: ReadableChannelTmdbTitle,
) -> WhitelistTitleOutput:
    """Read the sites and seasons of a title's filters in a channel."""
    return whitelist.channel_whitelist_output(session, channel_title)


# FAST003 - Parameters are used by ReadableChannelTmdbTitle.
# TODO: Validate
@channels_router.get(
    "/{channel_id}/whitelist/{tmdb_title_id}/seasons/{season_id}/episodes",  # noqa: FAST003
)
def get_channel_whitelist_episodes(
    session: SessionDep,
    channel_title: ReadableChannelTmdbTitle,
    season_id: uuid.UUID,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=WHITELIST_EPISODE_PAGE)] = (
        WHITELIST_EPISODE_PAGE
    ),
) -> WhitelistEpisodesOutput:
    """Read one page of a season's episodes, as the filter page expands it."""
    return whitelist.channel_whitelist_episodes_output(
        session,
        channel_title,
        season_id,
        offset,
        limit,
    )


# TODO: Validate
@channels_router.get("/{channel_id}")  # noqa: FAST003 - Used by ReadableChannel
def get_channel(channel: ReadableChannel, user: OptionalUser) -> ChannelOutput:
    """Get a `Channel` if it's readable by the `User`."""
    return channels.channel_output(channel, user)


router = APIRouter()


router.include_router(channels_router)
