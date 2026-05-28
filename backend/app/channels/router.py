# TODO: Validate
import time
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query
from loguru import logger
from sqlmodel import col, select

from app.auth.dependencies import CurrentUser, SessionDep
from app.channels import service
from app.channels.dependencies import (
    OwnedChannel,
    OwnedChannelReadableShow,
    ReadableChannel,
)
from app.channels.episode_selector import EpisodeQueryBuilder
from app.channels.models import Channel, ChannelQueue
from app.channels.schemas import (
    ChannelCreate,
    ChannelEpisodesOutput,
    ChannelOptions,
    ChannelOutput,
    ChannelQueueOutput,
    ChannelShowsOutput,
    ChannelUpdate,
    EpisodeWithDetails,
    SortOptionOutput,
    WhitelistEpisodeOutput,
    WhitelistSeasonOutput,
    WhitelistShowInput,
    WhitelistShowOutput,
)
from app.media.service import delete_record
from app.plugins.schemas import PluginOutput
from app.schemas import Message
from app.seasons.schemas import SeasonOutput
from app.shows.schemas import ShowPublic
from app.sources.schemas import SourcePublic
from app.users.dependencies import OptionalUser

router = APIRouter(prefix="/channels", tags=["channels"])


@router.get("", response_model=list[ChannelOutput])
def get_channels(current_user: CurrentUser) -> list[Channel]:
    """List all `Channel`s owned by the current `User`."""
    return current_user.channels


@router.post("", response_model=ChannelOutput)
def create_channel(
    session: SessionDep,
    current_user: CurrentUser,
    channel_in: ChannelCreate,
) -> Channel:
    """Create a `Channel` owned by the current `User`."""
    channel = Channel.model_validate(channel_in, update={"user_id": current_user.id})
    session.add(channel)
    session.commit()
    return channel


@router.get("/sort-options")
def get_sort_options() -> list[SortOptionOutput]:
    """Get a list of all possible sorting options."""
    return service.get_sort_options()


@router.post("/bulk-import-queue")
def bulk_import_queue_urls(
    session: SessionDep,
    current_user: CurrentUser,
    entries: dict[uuid.UUID, list[str]],
) -> Message:
    """Add URLs to multiple channels' import queues at once."""
    channels_by_id = {
        channel.id: channel
        for channel in session.exec(
            select(Channel)
            .where(col(Channel.id).in_(entries.keys()))
            .where(Channel.user_id == current_user.id),
        ).all()
    }
    total_urls = 0
    for channel_id, urls in entries.items():
        if channel := channels_by_id.get(channel_id):
            service.add_urls_to_channel_import_queue(
                session=session,
                urls=urls,
                channel=channel,
            )
            total_urls += len(urls)
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Channel {channel_id} not found",
            )
    return Message(message=f"{total_urls} URLs added across {len(entries)} channels")


@router.get("/{channel_id}", response_model=ChannelOutput)  # noqa: FAST003 - Used by ReadableChannel
def get_channel(channel: ReadableChannel) -> Channel:
    """Get a `Channel` if it's readable by the current `User`."""
    return channel


@router.patch("/{channel_id}", response_model=ChannelOutput)  # noqa: FAST003 - Used by OwnedChannel.
def update_channel(
    session: SessionDep,
    channel: OwnedChannel,
    channel_in: ChannelUpdate,
) -> Channel:
    """Update a `Channel` if it's owned by the current `User`."""
    return channel_in.update(session, channel)


@router.delete("/{channel_id}")  # noqa: FAST003 - Used by OwnedChannel.
def delete_channel(session: SessionDep, channel: OwnedChannel) -> Message:
    """Delete a `Channel` if it's owned by the current `User`."""
    return delete_record(session, channel)


@router.get("/{channel_id}/episodes")  # noqa: FAST003 - Used by ReadableChannel.
def get_channel_episodes(
    channel: ReadableChannel,
    channel_options: Annotated[ChannelOptions, Query()],
    user: OptionalUser,
    session: SessionDep,
) -> ChannelEpisodesOutput:
    """Read the episodes for a channel."""
    output = ChannelEpisodesOutput(
        episodes=[],
        seasons={},
        shows={},
        sources={},
        plugins={},
        channels={},
    )

    start = time.time()

    builder = EpisodeQueryBuilder(session, channel, channel_options, user)
    results = builder.get_episodes()

    unique_channel_ids = {result.channel_id for result in results}
    channels = session.exec(
        select(Channel).where(col(Channel.id).in_(unique_channel_ids)),
    ).all()
    for channel_obj in channels:
        output.channels[channel_obj.id] = ChannelOutput.model_validate(channel_obj)

    for result in results:
        episode = result.episode
        season = episode.season
        show = season.show
        source = show.source
        plugin = source.plugin

        extras: dict[str, Any] = {"channel_id": result.channel_id}
        if result.latest_watch:
            extras["watch_date"] = result.latest_watch.watch_date
            extras["verified"] = result.latest_watch.verified
            extras["episode_watch_id"] = result.latest_watch.id

        output.episodes.append(
            EpisodeWithDetails(**episode.model_dump(), **extras),
        )

        if episode.season_id not in output.seasons:
            output.seasons[episode.season_id] = SeasonOutput.model_validate(season)
        if season.show_id not in output.shows:
            output.shows[season.show_id] = ShowPublic.model_validate(show)
        if show.source_id not in output.sources:
            output.sources[show.source_id] = SourcePublic.model_validate(source)
        if source.plugin_id not in output.plugins:
            output.plugins[source.plugin_id] = PluginOutput.model_validate(plugin)

    logger.info("get_channel_episodes completed in {:.3f} seconds", time.time() - start)
    return output


# FAST003 - Parameter is used by ReadableChannel.
@router.get("/{channel_id}/shows")  # noqa: FAST003
def get_channel_shows(
    channel: ReadableChannel,
    user: OptionalUser,
    session: SessionDep,
) -> ChannelShowsOutput:
    """Read all shows for a channel."""
    output = ChannelShowsOutput()

    for channel_show in channel.shows:
        show = channel_show.show
        source = show.source
        plugin = source.plugin

        if not plugin.is_readable(session, user):
            continue

        output.shows.append(ShowPublic.model_validate(show))

        if source.id not in output.sources:
            output.sources[source.id] = SourcePublic.model_validate(source)

    return output


# FAST003 - Parameter is used by ReadableChannel.
@router.get("/{channel_id}/sources")  # noqa: FAST003
def get_channel_sources(
    channel: ReadableChannel,
    user: OptionalUser,
    session: SessionDep,
) -> list[SourcePublic]:
    """Read all unique sources for a channel."""
    sources: dict[uuid.UUID, SourcePublic] = {}
    for channel_show in channel.shows:
        source = channel_show.show.source
        plugin = source.plugin

        if not plugin.is_readable(session, user):
            continue

        if source.id not in sources:
            sources[source.id] = SourcePublic.model_validate(source)

    return list(sources.values())


# FAST003 - Parameter is used by UserChannelShow.
@router.get("/{channel_id}/whitelist/{show_id}")  # noqa: FAST003
def get_channel_whitelist(
    channel_show: OwnedChannelReadableShow,
) -> WhitelistShowOutput:
    """Read the whitelist for a show in a channel."""
    enabled_season_ids = {x.season_id for x in channel_show.season_filters}
    enabled_episode_ids = {x.episode_id for x in channel_show.episode_filters}

    seasons: list[WhitelistSeasonOutput] = []
    episodes: list[WhitelistEpisodeOutput] = []

    for season in channel_show.show.seasons:
        seasons.append(
            WhitelistSeasonOutput.model_validate(
                season,
                update={"filtered": season.id in enabled_season_ids},
            ),
        )
        episodes.extend(
            WhitelistEpisodeOutput.model_validate(
                episode,
                update={"filtered": episode.id in enabled_episode_ids},
            )
            for episode in season.episodes
        )

    return WhitelistShowOutput.model_validate(
        channel_show.show,
        update={
            "is_whitelist": channel_show.is_whitelist,
            "seasons": seasons,
            "episodes": episodes,
        },
    )


# FAST003 - Parameter is used by UserChannelShow.
@router.patch("/{channel_id}/whitelist/{show_id}")  # noqa: FAST003
def update_channel_whitelist(
    session: SessionDep,
    whitelist_config: WhitelistShowInput,
    channel_show: OwnedChannelReadableShow,
) -> WhitelistShowOutput:
    """Update the whitelist/blacklist for a show in a channel."""
    service.update_whitelist(session, channel_show, whitelist_config)
    return get_channel_whitelist(channel_show)


# FAST003 - Parameter is used by UserChannel.
@router.patch("/{channel_id}/default-order", response_model=ChannelOutput)  # noqa: FAST003
def update_channel_default_order(
    session: SessionDep,
    channel: OwnedChannel,
    channel_options: ChannelOptions,
) -> Channel:
    """Update the default sort order for a `Channel`."""
    exclude: set[str] = set()
    if "random_seed" not in channel_options.model_fields_set:
        exclude.add("random_seed")
    channel.default_order = channel_options.model_dump_json(
        by_alias=True,
        exclude_defaults=True,
        exclude_unset=False,
        exclude=exclude,
    )
    session.commit()
    session.refresh(channel)
    return channel


# FAST003 - Parameters are used by OwnedChannelReadableShow.
@router.delete("/{channel_id}/remove-show/{show_id}")  # noqa: FAST003
def delete_channel_show(
    session: SessionDep,
    channel_show: OwnedChannelReadableShow,
) -> Message:
    """Remove a `Show` from a `Channel`."""
    session.delete(channel_show)
    session.commit()
    return Message(
        message=f"{channel_show.show.name} removed from channel successfully",
    )


# FAST003 - Parameter is used by UserChannel.
@router.get("/{channel_id}/import-queue", response_model=list[ChannelQueueOutput])  # noqa: FAST003
def get_channel_queue(
    session: SessionDep,
    channel: OwnedChannel,
) -> list[ChannelQueue]:
    """Read the URLs in a channel's import queue."""
    statement = (
        select(ChannelQueue)
        .where(ChannelQueue.channel_id == channel.id)
        # Descending order works better on the frontend because new URLs are appended to the
        # top of the list making it possible to immediately see the new URLs after adding
        # them without having to scroll down.
        .order_by(col(ChannelQueue.created_at).desc())
    )

    channels = session.exec(statement).all()

    return list(channels)


# FAST003 - Parameter is used by UserChannel.
@router.post("/{channel_id}/import-queue", response_model=list[ChannelQueueOutput])  # noqa: FAST003
def create_channel_queue_urls(
    session: SessionDep,
    channel: OwnedChannel,
    urls: list[str],
) -> list[ChannelQueue]:
    """Add URLs to a channel's import queue."""
    data = service.add_urls_to_channel_import_queue(
        session=session,
        urls=urls,
        channel=channel,
    )
    return data  # noqa: RET504 - TODO: Remove unnecessary assignment before return


@router.delete("/{channel_id}/import-queue/{url_id}")  # noqa: FAST003 - Used by UserChannel.
def delete_channel_queue_url(
    session: SessionDep,
    channel: OwnedChannel,
    url_id: uuid.UUID,
) -> Message:
    """Delete url from a channel's import queue."""
    queue_entry = session.exec(
        select(ChannelQueue)
        .where(ChannelQueue.channel_id == channel.id)
        .where(ChannelQueue.id == url_id),
    ).first()
    if not queue_entry:
        raise HTTPException(status_code=404, detail="URL not found")
    url = queue_entry.url
    session.delete(queue_entry)
    session.commit()
    return Message(message=f"{url} removed from import queue successfully")


@router.delete("/{channel_id}/clear-completed-import-queue")  # noqa: FAST003 - Used by UserChannel.
def clear_channel_completed_queue(
    session: SessionDep,
    channel: OwnedChannel,
) -> Message:
    """Clear a channel's import queue."""
    for existing_record in channel.queue:
        if existing_record.status == service.URLStatus.IMPORTED:
            session.delete(existing_record)

    session.commit()
    return Message(message="Import queue cleared successfully")
