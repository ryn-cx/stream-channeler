# TODO: Validate
import time
import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from loguru import logger
from sqlmodel import col, select

from app.auth.dependencies import CurrentUser, SessionDep
from app.channels import service
from app.channels.dependencies import (
    ReadableChannel,
    UserChannel,
    UserChannelShow,
)
from app.channels.episode_selector import (
    EpisodeQueryBuilder,
)
from app.channels.models import (
    Channel,
    ChannelQueue,
)
from app.channels.schemas import (
    ChannelEpisodesOutput,
    ChannelMediaFilter,
    ChannelOutput,
    ChannelPatchInput,
    ChannelPostInput,
    ChannelQueuesListOutput,
    ChannelShowsOutput,
    ChannelsListOutput,
    EpisodeWithExtrasOutput,
    MultipleSortOptionOutputs,
    SortOptionOutput,
    WhitelistShowInput,
    WhitelistShowOutput,
)
from app.episodes.models import Episode
from app.episodes.schemas import EpisodeOutput
from app.media.service import delete_record, list_children, update_record
from app.models import Message
from app.plugins.models import Plugin
from app.plugins.schemas import PluginOutput
from app.seasons.models import Season
from app.seasons.schemas import SeasonOutput
from app.shows.models import Show
from app.shows.schemas import ShowOutput
from app.sources.models import Source
from app.sources.schemas import SourceOutput
from app.users.dependencies import OptionalUser

router = APIRouter(prefix="/channels", tags=["channels"])


@router.get("")
def get_user_channels(
    session: SessionDep,
    current_user: CurrentUser,
) -> ChannelsListOutput:
    """List all channels owned by the current user."""
    return list_children(
        session,
        Channel,
        "user_id",
        current_user.id,
        ChannelOutput,
        ChannelsListOutput,
    )


@router.get("/sort-options")
def get_sort_options() -> MultipleSortOptionOutputs:
    """Get a list of all possible sorting options."""
    # Random needs to be added by hand because it does not rely on a specific field.
    data: list[SortOptionOutput] = []

    # For simplicity all of the other possible values are dynamically generated from the
    # model fields.
    skip_fields = ("extra", "id", "description", "data_timestamp")
    for model in (Episode, Season, Show, Source, Plugin):
        for field in model.model_fields:
            if field.endswith(("key", "url", "_at", "_id")) or field in skip_fields:
                continue

            label = f"{model.__name__} - {field.replace('_', ' ').title()}"
            model_name = model.__name__.lower()
            data.append(
                SortOptionOutput(
                    label=label,
                    value=f"value.{model_name}.{field}",
                ),
            )

    # Manually created special cases that also have special cases when looking up the
    # data in the database.
    data.append(
        SortOptionOutput(
            label="Show - Remaining Duration",
            value="sum.show-episodes.duration",
        ),
    )
    data.append(
        SortOptionOutput(
            label="Show - Remaining Episodes",
            value="count.show-episodes.id",
        ),
    )
    data.append(
        SortOptionOutput(
            label="Show - Last Watched",
            value="max.show-episodes.last_watched",
        ),
    )
    data.append(
        SortOptionOutput(
            label="Show - Latest Episode Date",
            value="max.show-episodes.air_date",
        ),
    )
    data.append(
        SortOptionOutput(
            label="Show - Started",
            value="value.show.started",
        ),
    )
    data.append(
        SortOptionOutput(
            label="Show - Recently Aired (Last Month)",
            value="value.show.recently_aired_month",
        ),
    )
    data.append(
        SortOptionOutput(
            label="Show - Recently Aired (Last Week)",
            value="value.show.recently_aired_week",
        ),
    )
    data.append(
        SortOptionOutput(
            label="Episode - Random",
            value="value.episode.random",
        ),
    )
    data.append(
        SortOptionOutput(
            label="Show - Random",
            value="max.show-episodes.random",
        ),
    )

    # Sort everything by the label
    data.sort(key=lambda x: x.label)

    return MultipleSortOptionOutputs(data=data)


# FAST003 - Parameter is used by ReadableChannel.
@router.get("/{channel_id}", response_model=ChannelOutput)  # noqa: FAST003
def get_user_channel(channel: ReadableChannel) -> Channel:
    """Get a channel by its id."""
    return channel


# FAST003 - Parameter is used by ReadableChannel.
@router.get("/{channel_id}/episodes")  # noqa: FAST003
def get_channel_episodes(
    channel: ReadableChannel,
    media_filter: Annotated[ChannelMediaFilter, Query()],
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

    builder = EpisodeQueryBuilder(session, channel, media_filter, user)
    episodes = builder.get_episodes()
    if media_filter.limit is not None:
        episodes = episodes[: media_filter.limit]
    logger.info("get_channel_episodes completed in %.3f seconds", time.time() - start)
    episode_channels = builder.get_episode_channels(episodes)
    logger.info("get_channel_episodes completed in %.3f seconds", time.time() - start)
    watches = builder.get_episode_latest_watch_date(episodes)

    logger.info("get_channel_episodes completed in %.3f seconds", time.time() - start)
    unique_channel_ids = set(episode_channels.values())
    channels = session.exec(
        select(Channel).where(col(Channel.id).in_(unique_channel_ids)),
    ).all()
    for channel_obj in channels:
        output.channels[channel_obj.id] = ChannelOutput.model_validate(channel_obj)

    logger.info("get_channel_episodes completed in %.3f seconds", time.time() - start)
    for episode in episodes:
        season = episode.season
        show = season.show
        source = show.source
        plugin = source.plugin

        # Add last watched information and channel_id to the episodes after finding
        # the episodes because it is much faster for channels with tens of thousands
        # of episodes.
        if watches.get(episode.id):
            output.episodes.append(
                EpisodeWithExtrasOutput(
                    **episode.model_dump(),
                    watch_date=watches[episode.id].watch_date,
                    verified=watches[episode.id].verified,
                    episode_watch_id=watches[episode.id].id,
                    channel_id=episode_channels[episode.id],
                ),
            )
        else:
            output.episodes.append(
                EpisodeWithExtrasOutput(
                    **episode.model_dump(),
                    channel_id=episode_channels[episode.id],
                ),
            )

        if episode.season_id not in output.seasons:
            output.seasons[episode.season_id] = SeasonOutput.model_validate(season)
        if season.show_id not in output.shows:
            output.shows[season.show_id] = ShowOutput.model_validate(show)
        if show.source_id not in output.sources:
            output.sources[show.source_id] = SourceOutput.model_validate(source)
        if source.plugin_id not in output.plugins:
            output.plugins[source.plugin_id] = PluginOutput.model_validate(plugin)

    logger.info("get_channel_episodes completed in %.3f seconds", time.time() - start)
    return output


# FAST003 - Parameter is used by ReadableChannel.
@router.get("/{channel_id}/shows")  # noqa: FAST003
def get_channel_shows(channel: ReadableChannel) -> ChannelShowsOutput:
    """Read all shows for a channel."""
    output = ChannelShowsOutput()

    for channel_show in channel.shows:
        show = channel_show.show
        source = show.source

        output.shows.append(ShowOutput.model_validate(show))

        if source.id not in output.sources:
            output.sources[source.id] = SourceOutput.model_validate(source)

    return output


# FAST003 - Parameter is used by UserChannelShow.
@router.get("/{channel_id}/whitelist/{show_id}")  # noqa: FAST003
def get_user_channel_whitelist(
    channel_show: UserChannelShow,
) -> WhitelistShowOutput:
    """Read the whitelist for a show in a channel."""
    seasons: list[SeasonOutput] = []
    episodes: list[EpisodeOutput] = []

    for season in channel_show.show.seasons:
        seasons.append(SeasonOutput.model_validate(season))

        episodes.extend(
            EpisodeOutput.model_validate(episode) for episode in season.episodes
        )

    return WhitelistShowOutput.model_validate(
        channel_show.show,
        update={
            "whitelist_mode": channel_show.white_list_mode,
            "enabled_season_ids": [x.season_id for x in channel_show.season_white_list],
            "enabled_episode_ids": [
                x.episode_id for x in channel_show.episode_white_list
            ],
            "seasons": seasons,
            "episodes": episodes,
        },
    )


# FAST003 - Parameter is used by UserChannelShow.
@router.patch("/{channel_id}/whitelist/{show_id}")  # noqa: FAST003
def update_user_channel_whitelist(
    session: SessionDep,
    whitelist_config: WhitelistShowInput,
    channel_show: UserChannelShow,
) -> WhitelistShowOutput:
    """Update the whitelist/blacklist for a show in a channel."""
    service.update_whitelist(session, channel_show, whitelist_config)
    return get_user_channel_whitelist(channel_show)


@router.post("", response_model=ChannelOutput)
def create_user_channel(
    session: SessionDep,
    current_user: CurrentUser,
    channel_in: ChannelPostInput,
) -> Channel:
    """Create a channel owned by the current user."""
    channel = Channel.model_validate(channel_in, update={"user_id": current_user.id})
    session.add(channel)
    session.commit()
    return channel


# FAST003 - Parameter is used by UserChannel.
@router.patch("/{channel_id}", response_model=ChannelOutput)  # noqa: FAST003
def update_user_channel(
    session: SessionDep,
    channel: UserChannel,
    channel_in: ChannelPatchInput,
) -> Channel:
    """Update a channel owned by the current user."""
    return update_record(session, channel, channel_in)


# FAST003 - Parameter is used by UserChannel.
@router.patch("/{channel_id}/default-order", response_model=ChannelOutput)  # noqa: FAST003
def update_user_channel_default_order(
    session: SessionDep,
    channel: UserChannel,
    media_filter: ChannelMediaFilter,
) -> Channel:
    """Update the default sort order for a channel."""
    channel.default_order = media_filter.model_dump_json(
        by_alias=True,
        exclude_defaults=True,
        exclude_unset=False,
    )
    session.commit()
    session.refresh(channel)
    return channel


# FAST003 - Parameter is used by UserChannel.
@router.delete("/{channel_id}")  # noqa: FAST003
def delete_user_channel(session: SessionDep, channel: UserChannel) -> Message:
    """Delete a channel owned by the current user."""
    return delete_record(session, channel)


# FAST003 - Parameter is used by UserChannel.
@router.delete("/{channel_id}/remove-show/{show_id}")  # noqa: FAST003
def delete_channel_show(
    channel: UserChannel,
    session: SessionDep,
    show_id: str,
) -> Message:
    """Remove a show from a channel."""
    if not (show := session.exec(select(Show).where(Show.id == show_id)).first()):
        raise HTTPException(status_code=404, detail="Show not found")

    # TODO: Benchmark performance options.
    for channel_show in channel.shows:
        if channel_show.show == show:
            session.delete(channel_show)
            session.commit()
            return Message(message=f"{show.name} removed from channel successfully")

    raise HTTPException(status_code=404, detail="Show not found in channel")


# FAST003 - Parameter is used by UserChannel.
@router.get("/{channel_id}/import-queue")  # noqa: FAST003
def get_user_channel_queue(
    session: SessionDep,
    channel: UserChannel,
) -> ChannelQueuesListOutput:
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

    return ChannelQueuesListOutput(
        data=channels,  # pyright: ignore[reportArgumentType] - Pydantic casting
    )


# FAST003 - Parameter is used by UserChannel.
@router.post("/{channel_id}/import-queue")  # noqa: FAST003
def create_user_channel_queue_urls(
    session: SessionDep,
    channel: UserChannel,
    urls: list[str],
) -> ChannelQueuesListOutput:
    """Add URLs to a channel's import queue."""
    data = service.add_urls_to_channel_import_queue(
        session=session,
        urls=urls,
        channel=channel,
    )
    return ChannelQueuesListOutput(data=data)  # pyright: ignore[reportArgumentType] - Pydantic casting


# FAST003 - Parameter is used by UserChannel.
@router.delete("/{channel_id}/import-queue/{url_id}")  # noqa: FAST003
def delete_user_channel_queue_url(
    session: SessionDep,
    channel: UserChannel,
    url_id: uuid.UUID,
) -> Message:
    """Delete url from a channel's import queue."""
    for existing_entry in channel.queue:
        if existing_entry.id == url_id:
            url = existing_entry.url
            session.delete(existing_entry)
            session.commit()
            return Message(message=f"{url} removed from import queue successfully")

    raise HTTPException(status_code=404, detail="URL not found")


# FAST003 - Parameter is used by UserChannel.
@router.delete("/{channel_id}/clear-completed-import-queue")  # noqa: FAST003
def clear_user_channel_completed_queue(
    session: SessionDep,
    channel: UserChannel,
) -> Message:
    """Clear a channel's import queue."""
    for existing_entry in channel.queue:
        if existing_entry.status == service.URLStatus.IMPORTED:
            session.delete(existing_entry)

    session.commit()
    return Message(message="Import queue cleared successfully")
